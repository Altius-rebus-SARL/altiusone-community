# apps/modelforms/services/submission_handler.py
"""
Service de gestion des soumissions de formulaires.

Ce module gère le traitement des données soumises via les formulaires dynamiques:
- Application des valeurs par défaut
- Validation des données
- Création des enregistrements (objets liés puis principal)
- Exécution des post-actions (email, task, notification, create_object)
- Gestion des transactions et rollback
"""
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import date, datetime
from decimal import Decimal
from django.apps import apps
from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.models import User, AuditLog


logger = logging.getLogger(__name__)


class SubmissionHandler:
    """
    Gestionnaire de soumissions de formulaires.

    Traite les données soumises et crée les enregistrements correspondants
    de manière atomique.
    """

    # Variables supportées dans les valeurs par défaut
    VARIABLE_PATTERN = re.compile(r'\{\{(\w+(?:\.\w+)*)\}\}')

    def __init__(
        self,
        form_config: 'FormConfiguration',
        submitted_data: Dict[str, Any],
        user: User,
        mandat=None,
    ):
        """
        Initialise le handler.

        Args:
            form_config: Configuration du formulaire
            submitted_data: Données soumises
            user: Utilisateur qui soumet
            mandat: Mandat associé (optionnel)
        """
        self.form_config = form_config
        self.submitted_data = submitted_data.copy()
        self.user = user
        self.mandat = mandat
        self.created_records: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        # Erreurs non-bloquantes levees lors des post_actions. Les callers
        # peuvent les recuperer via handler.post_action_errors et les
        # stocker dans FormSubmission.error_details pour debug.
        self.post_action_errors: List[Dict[str, Any]] = []

    def process(self) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
        """
        Traite la soumission.

        Returns:
            Tuple (success, created_records, errors)
        """
        try:
            with transaction.atomic():
                # 1. Appliquer les valeurs par défaut
                self._apply_default_values()

                # 2. Valider les données
                if not self._validate_data():
                    return False, [], self.errors

                # 3. Créer les objets liés d'abord (ex: Adresse)
                related_ids = self._create_related_objects()
                if self.errors:
                    raise ValidationError(self.errors)

                # 4. Créer l'objet principal
                main_record = self._create_main_object(related_ids)
                if not main_record:
                    raise ValidationError(self.errors)

                # 5. Exécuter les post-actions
                self._execute_post_actions(main_record)

                # 6. Créer l'entrée d'audit
                self._create_audit_log(main_record)

                return True, self.created_records, []

        except ValidationError as e:
            return False, [], self.errors if self.errors else [str(e)]
        except Exception as e:
            return False, [], [f"Erreur inattendue: {str(e)}"]

    def _apply_default_values(self):
        """
        Applique les valeurs par défaut configurées.

        Supporte les variables:
        - {{today}}: Date du jour
        - {{now}}: Date et heure actuelles
        - {{current_user}}: ID de l'utilisateur courant
        - {{current_user.id}}: ID de l'utilisateur
        - {{current_user.email}}: Email de l'utilisateur
        """
        default_values = self.form_config.default_values or {}

        for field_name, default_value in default_values.items():
            # Ne pas écraser les valeurs déjà fournies
            if field_name in self.submitted_data and self.submitted_data[field_name] not in (None, '', []):
                continue

            # Résoudre les variables
            if isinstance(default_value, str) and '{{' in default_value:
                resolved = self._resolve_variable(default_value)
                self.submitted_data[field_name] = resolved
            else:
                self.submitted_data[field_name] = default_value

    def _resolve_variable(self, value: str) -> Any:
        """
        Résout les variables dans une chaîne.
        """
        def replace_var(match):
            var_path = match.group(1)

            if var_path == 'today':
                return date.today().isoformat()

            if var_path == 'now':
                return timezone.now().isoformat()

            if var_path == 'current_user':
                return str(self.user.id)

            if var_path.startswith('current_user.'):
                attr = var_path.split('.', 1)[1]
                if hasattr(self.user, attr):
                    return str(getattr(self.user, attr))
                return ''

            return match.group(0)  # Retourner tel quel si non reconnu

        result = self.VARIABLE_PATTERN.sub(replace_var, value)

        # Si le résultat est identique à une variable résolue simple, retourner directement
        if result != value and not self.VARIABLE_PATTERN.search(result):
            return result

        return result

    def _validate_data(self) -> bool:
        """
        Valide les données selon les règles configurées.
        """
        validation_rules = self.form_config.validation_rules or []

        for rule in validation_rules:
            rule_type = rule.get('type')
            field = rule.get('field')

            if rule_type == 'required':
                if not self.submitted_data.get(field):
                    self.errors.append(f"Le champ '{field}' est obligatoire")

            elif rule_type == 'required_if':
                condition = rule.get('condition', '')
                if self._evaluate_condition(condition):
                    if not self.submitted_data.get(field):
                        self.errors.append(f"Le champ '{field}' est obligatoire dans ce cas")

            elif rule_type == 'regex':
                pattern = rule.get('pattern', '')
                value = self.submitted_data.get(field, '')
                if value and not re.match(pattern, str(value)):
                    message = rule.get('message', f"Le format du champ '{field}' est invalide")
                    self.errors.append(message)

            elif rule_type == 'min_value':
                min_val = rule.get('value')
                value = self.submitted_data.get(field)
                if value is not None and value < min_val:
                    self.errors.append(f"Le champ '{field}' doit être >= {min_val}")

            elif rule_type == 'max_value':
                max_val = rule.get('value')
                value = self.submitted_data.get(field)
                if value is not None and value > max_val:
                    self.errors.append(f"Le champ '{field}' doit être <= {max_val}")

        return len(self.errors) == 0

    def _evaluate_condition(self, condition: str) -> bool:
        """
        Évalue une condition simple.

        Supporte:
        - field == 'value'
        - field != 'value'
        - field in ['val1', 'val2']
        """
        if '==' in condition:
            parts = condition.split('==')
            if len(parts) == 2:
                field = parts[0].strip()
                expected = parts[1].strip().strip("'\"")
                return str(self.submitted_data.get(field, '')) == expected

        if '!=' in condition:
            parts = condition.split('!=')
            if len(parts) == 2:
                field = parts[0].strip()
                expected = parts[1].strip().strip("'\"")
                return str(self.submitted_data.get(field, '')) != expected

        if ' in ' in condition:
            parts = condition.split(' in ')
            if len(parts) == 2:
                field = parts[0].strip()
                values_str = parts[1].strip()
                # Parser la liste simple
                if values_str.startswith('[') and values_str.endswith(']'):
                    values = [v.strip().strip("'\"") for v in values_str[1:-1].split(',')]
                    return str(self.submitted_data.get(field, '')) in values

        return False

    def _create_related_objects(self) -> Dict[str, Any]:
        """
        Crée les objets liés (ex: Adresse pour un Client).

        Returns:
            Dictionnaire {field_name: created_instance}
        """
        related_ids = {}
        related_models = self.form_config.related_models or []

        for related_config in related_models:
            model_path = related_config.get('model')
            field_name = related_config.get('field')
            required = related_config.get('required', False)

            # Extraire les données pour ce modèle lié
            related_data = self._extract_related_data(field_name)

            if not related_data:
                if required:
                    self.errors.append(f"Les données pour '{field_name}' sont obligatoires")
                continue

            try:
                # Obtenir la classe du modèle
                app_label, model_name = model_path.split('.')
                model_class = apps.get_model(app_label, model_name)

                # Créer l'instance
                instance = model_class(**related_data)
                instance.full_clean()
                instance.save()

                related_ids[field_name] = instance

                self.created_records.append({
                    'model': model_path,
                    'id': str(instance.pk),
                    'repr': str(instance),
                })

            except Exception as e:
                self.errors.append(f"Erreur création '{field_name}': {str(e)}")

        return related_ids

    def _extract_related_data(self, prefix: str) -> Dict[str, Any]:
        """
        Extrait les données pour un modèle lié à partir du préfixe.

        Ex: prefix='adresse_siege' extraira 'adresse_siege.rue' -> 'rue'
        """
        data = {}
        prefix_dot = f"{prefix}."

        for key, value in self.submitted_data.items():
            if key.startswith(prefix_dot):
                field_name = key[len(prefix_dot):]
                data[field_name] = value
            elif key == prefix and isinstance(value, dict):
                # Format alternatif: données imbriquées
                data = value

        return data

    def _create_main_object(self, related_ids: Dict[str, Any]) -> Optional[models.Model]:
        """
        Crée l'objet principal du formulaire.
        """
        try:
            model_class = self.form_config.get_target_model_class()

            # Préparer les données
            data = self._prepare_main_data(model_class, related_ids)

            # Ajouter created_by si le modèle le supporte
            if hasattr(model_class, 'created_by'):
                data['created_by'] = self.user

            # Créer l'instance
            instance = model_class(**data)
            instance.full_clean()
            instance.save()

            self.created_records.insert(0, {
                'model': self.form_config.target_model,
                'id': str(instance.pk),
                'repr': str(instance),
            })

            return instance

        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    self.errors.append(f"{field}: {error}")
            return None
        except Exception as e:
            self.errors.append(f"Erreur création: {str(e)}")
            return None

    def _prepare_main_data(
        self,
        model_class: type,
        related_ids: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prépare les données pour l'objet principal.
        """
        data = {}
        model_fields = {f.name: f for f in model_class._meta.get_fields() if hasattr(f, 'name')}

        for key, value in self.submitted_data.items():
            # Ignorer les champs imbriqués (ex: adresse_siege.rue)
            if '.' in key:
                continue

            # Ignorer si pas un champ du modèle
            if key not in model_fields:
                continue

            field = model_fields[key]

            # Remplacer par l'instance liée si applicable
            if key in related_ids:
                data[key] = related_ids[key]
                continue

            # Conversion de type selon le champ
            data[key] = self._convert_value(field, value)

        return data

    def _convert_value(self, field: models.Field, value: Any) -> Any:
        """
        Convertit une valeur selon le type de champ Django.
        """
        if value is None or value == '':
            return None if field.null else value

        field_type = field.__class__.__name__

        # Dates
        if field_type == 'DateField':
            if isinstance(value, str):
                return datetime.strptime(value, '%Y-%m-%d').date()
            return value

        # DateTimes
        if field_type == 'DateTimeField':
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            return value

        # Décimaux
        if field_type == 'DecimalField':
            return Decimal(str(value))

        # Entiers
        if 'Integer' in field_type:
            return int(value)

        # Booléens
        if field_type == 'BooleanField':
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'oui')
            return bool(value)

        # ForeignKey - résoudre l'ID
        if field_type in ('ForeignKey', 'OneToOneField'):
            if isinstance(value, str):
                related_model = field.related_model
                try:
                    return related_model.objects.get(pk=value)
                except related_model.DoesNotExist:
                    return None
            return value

        return value

    def _execute_post_actions(self, main_record: models.Model):
        """
        Exécute les actions post-soumission configurées.

        Les erreurs de post-actions ne bloquent JAMAIS la creation de l'objet
        principal (qui est deja persiste a ce stade). Elles sont loggees et
        exposees via `self.post_action_errors` pour que le caller puisse les
        stocker dans `FormSubmission.error_details`.

        Types d'actions supportes:
        - ``email``: envoie un email (template ou inline) via mailing.EmailService
        - ``task``: cree une core.Tache assignee a un utilisateur
        - ``notification``: cree une core.Notification
        - ``create_object``: cree un objet Django arbitraire (ex: Facture liee
          au Client qui vient d'etre cree)
        """
        post_actions = self.form_config.post_actions or []

        for idx, action in enumerate(post_actions):
            action_type = action.get('type')

            try:
                if action_type == 'email':
                    self._send_email_action(action, main_record)
                elif action_type == 'task':
                    self._create_task_action(action, main_record)
                elif action_type == 'notification':
                    self._create_notification_action(action, main_record)
                elif action_type == 'create_object':
                    self._create_object_action(action, main_record)
                else:
                    logger.warning(
                        "modelforms post_action inconnue: type=%s (form=%s, idx=%d)",
                        action_type, self.form_config.code, idx,
                    )
                    self.post_action_errors.append({
                        'index': idx,
                        'type': action_type,
                        'error': f"Type d'action inconnu: {action_type}",
                    })
            except Exception as e:
                logger.error(
                    "modelforms post_action #%d (%s) pour form %s: %s",
                    idx, action_type, self.form_config.code, e,
                    exc_info=True,
                )
                self.post_action_errors.append({
                    'index': idx,
                    'type': action_type,
                    'error': str(e),
                })

    def _resolve_action_variables(
        self, value: Any, record: Optional[models.Model] = None,
    ) -> Any:
        """
        Resout les variables dans une valeur d'action.

        Etend `_resolve_variable()` avec le support de `{{record.<attr>}}`
        pour faire reference a l'objet principal qui vient d'etre cree.

        Ex: `{{record.id}}`, `{{record.email}}`, `{{record.raison_sociale}}`

        Les variables `{{current_user.*}}`, `{{today}}`, `{{now}}` restent
        supportees comme avant.
        """
        if not isinstance(value, str) or '{{' not in value:
            return value

        def replace_var(match):
            var_path = match.group(1)

            # {{record.*}} — nouveau dans PR1
            if var_path.startswith('record.') and record is not None:
                attr_chain = var_path.split('.', 1)[1]
                obj: Any = record
                for attr in attr_chain.split('.'):
                    if obj is None:
                        return ''
                    obj = getattr(obj, attr, None)
                return str(obj) if obj is not None else ''

            if var_path == 'today':
                return date.today().isoformat()
            if var_path == 'now':
                return timezone.now().isoformat()
            if var_path == 'current_user':
                return str(self.user.id) if self.user else ''
            if var_path.startswith('current_user.'):
                attr = var_path.split('.', 1)[1]
                if self.user and hasattr(self.user, attr):
                    return str(getattr(self.user, attr))
                return ''

            return match.group(0)

        return self.VARIABLE_PATTERN.sub(replace_var, value)

    def _send_email_action(self, action: Dict, record: models.Model):
        """
        Envoie un email suite a la creation de l'objet principal.

        Formats supportes:

        1) Template par code (recommande):
        ``{"type": "email", "template": "NOUVEAU_CLIENT", "to": "{{record.email}}"}``

        2) Email inline (pas de template):
        ``{"type": "email", "to": "{{current_user.email}}",
           "subject": "Nouveau {{record.raison_sociale}}",
           "body": "..."}``

        Le destinataire, le sujet et le corps supportent les variables
        ``{{record.*}}``, ``{{current_user.*}}``, ``{{today}}``, ``{{now}}``.
        """
        from mailing.services import EmailService

        to_expr = action.get('to', '')
        destinataire = self._resolve_action_variables(to_expr, record)
        if not destinataire:
            raise ValueError(
                "post_action email: 'to' non defini ou resolution vide"
            )

        svc = EmailService()
        template_code = action.get('template')

        if template_code:
            # Mode template: passer le record et l'user dans le contexte pour
            # que le template puisse utiliser ses propres variables.
            context = {
                'record': record,
                'user': self.user,
                'mandat': self.mandat,
                'form_code': self.form_config.code,
                'form_name': self.form_config.name,
            }
            # Ajouter aussi les champs du record pour acces direct
            if record is not None:
                for field in record._meta.fields:
                    fname = field.name
                    try:
                        context[fname] = getattr(record, fname)
                    except Exception:
                        pass
            context.update(action.get('context', {}))

            email_envoye = svc.send_template_email(
                destinataire=destinataire,
                template_code=template_code,
                context=context,
                utilisateur=self.user,
                mandat=self.mandat,
                content_type='modelforms_submission',
                object_id=str(record.pk) if record else '',
            )
            if email_envoye is None:
                raise ValueError(
                    f"Template email '{template_code}' introuvable ou inactif"
                )
            return

        # Mode inline
        subject = self._resolve_action_variables(
            action.get('subject', f"Nouvelle soumission: {self.form_config.name}"),
            record,
        )
        body_html = self._resolve_action_variables(
            action.get('body', action.get('body_html', '')),
            record,
        )
        if not body_html:
            raise ValueError(
                "post_action email inline: 'body' ou 'template' requis"
            )

        svc.send_email(
            destinataire=destinataire,
            sujet=subject,
            corps_html=body_html,
            utilisateur=self.user,
            mandat=self.mandat,
            content_type='modelforms_submission',
            object_id=str(record.pk) if record else '',
        )

    def _create_object_action(self, action: Dict, record: models.Model):
        """
        Cree un objet Django arbitraire a partir d'un mapping.

        Format:
        ``{
            "type": "create_object",
            "model": "facturation.Facture",
            "field_mapping": {
                "client_id": "{{record.id}}",
                "montant_ht": "100.00",
                "mandat_id": "{{mandat_id}}"
            }
        }``

        Les valeurs du field_mapping supportent les variables
        ``{{record.*}}``, ``{{current_user.*}}``, ``{{mandat_id}}``,
        ``{{today}}``, ``{{now}}``.

        L'objet cree est ajoute a `self.created_records`.
        """
        model_path = action.get('model')
        if not model_path:
            raise ValueError("post_action create_object: 'model' requis")

        try:
            app_label, model_name = model_path.split('.')
            model_class = apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as e:
            raise ValueError(
                f"post_action create_object: modele '{model_path}' introuvable: {e}"
            )

        field_mapping = action.get('field_mapping', {})
        if not isinstance(field_mapping, dict):
            raise ValueError(
                "post_action create_object: 'field_mapping' doit etre un dict"
            )

        # Resoudre les variables dans les valeurs
        resolved_data: Dict[str, Any] = {}
        for field_name, raw_value in field_mapping.items():
            if isinstance(raw_value, str):
                # Cas special {{mandat_id}}
                if raw_value == '{{mandat_id}}':
                    resolved_data[field_name] = (
                        str(self.mandat.pk) if self.mandat else None
                    )
                    continue
                resolved_data[field_name] = self._resolve_action_variables(
                    raw_value, record,
                )
            else:
                resolved_data[field_name] = raw_value

        # Creer l'instance
        instance = model_class(**resolved_data)
        instance.full_clean()
        instance.save()

        self.created_records.append({
            'model': model_path,
            'id': str(instance.pk),
            'repr': str(instance),
            'source': 'post_action',
        })

    def _create_task_action(self, action: Dict, record: models.Model):
        """
        Crée une tâche suite à la création.
        """
        from core.models import Tache

        title = action.get('title', f"Nouvelle soumission: {record}")
        assign_to_expr = action.get('assign_to', '{{current_user}}')

        # Résoudre l'assignation
        if assign_to_expr == '{{current_user}}':
            assign_to = self.user
        else:
            # Tenter de résoudre comme un ID utilisateur
            try:
                assign_to = User.objects.get(pk=assign_to_expr)
            except (User.DoesNotExist, ValueError):
                assign_to = self.user

        tache = Tache.objects.create(
            titre=title,
            description=f"Créé automatiquement suite à la soumission du formulaire {self.form_config.code}",
            cree_par=self.user,
            mandat=self.mandat,
            priorite='NORMALE',
        )
        tache.assignes.add(assign_to)

    def _create_notification_action(self, action: Dict, record: models.Model):
        """
        Crée une notification suite à la création.
        """
        from core.models import Notification

        message = action.get('message', f"Nouvel enregistrement créé: {record}")
        recipient_expr = action.get('to', '{{current_user}}')

        # Résoudre le destinataire
        if recipient_expr == '{{current_user}}':
            recipient = self.user
        else:
            try:
                recipient = User.objects.get(pk=recipient_expr)
            except (User.DoesNotExist, ValueError):
                return

        Notification.objects.create(
            destinataire=recipient,
            type_notification='INFO',
            titre=f"Formulaire soumis: {self.form_config.name}",
            message=message,
            mandat=self.mandat,
        )

    def _create_audit_log(self, record: models.Model):
        """
        Crée une entrée dans le log d'audit.
        """
        AuditLog.objects.create(
            utilisateur=self.user,
            action='SUBMIT',
            table_name=self.form_config.target_model,
            object_id=str(record.pk),
            object_repr=str(record)[:255],
            changements={
                'form_config': self.form_config.code,
                'submitted_data': self.submitted_data,
            },
            mandat=self.mandat,
        )
