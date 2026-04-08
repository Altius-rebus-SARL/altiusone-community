# apps/modelforms/services/step_executor.py
"""
Moteur d'execution des processus metiers (PR3).

Orchestre l'execution d'une ProcessInstance step par step. Chaque type de
step est gere par un executor dedie (FormFillStepExecutor, CreateObjectStepExecutor,
SendEmailStepExecutor, HumanApprovalStepExecutor).

Execution synchrone en ligne dans la requete HTTP pour Phase 1. Celery viendra
en Phase 2 pour les steps longs (webhooks, calculs lourds) et les retries
automatiques.

Flow typique:

    executor = ProcessExecutor(instance)
    executor.start()  # declenche la chaine depuis le START step
    # Si l'instance tombe sur un HUMAN_APPROVAL ou FORM_FILL, elle passe en
    # WAITING et attend un advance(trigger_data) externe.
    executor.advance({'approved': True})

Les step_executors retournent un tuple (new_status, output_dict) ou
(new_status, output_dict, next_step_override). Le ProcessExecutor s'occupe
de persister StepExecution, mettre a jour les variables et suivre les
transitions.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import date
from decimal import Decimal

from django.apps import apps
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..models import (
    ProcessDefinition,
    ProcessStep,
    ProcessTransition,
    ProcessInstance,
    StepExecution,
    FormConfiguration,
    FormSubmission,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Evaluateur de conditions JSON (whitelist securisee)
# =============================================================================

SUPPORTED_OPERATORS = {
    '==', '!=', '>', '<', '>=', '<=',
    'in', 'not_in', 'contains',
    'is_null', 'is_not_null',
}


def evaluate_condition(condition: Dict[str, Any], variables: Dict[str, Any]) -> bool:
    """
    Evalue une condition JSON contre un dict de variables.

    Formats supportes:

    Condition atomique:
        {"variable": "x", "operator": "==", "value": "y"}

    Conditions composees:
        {"and": [cond1, cond2, ...]}
        {"or": [cond1, cond2, ...]}
        {"not": cond}

    Condition vide/null = True (transition inconditionnelle).

    SECURITE: PAS d'eval(), PAS d'exec(). Tout est parse et evalue
    explicitement via ce code. Les operateurs sont dans une whitelist.

    Args:
        condition: Dict representant la condition (ou dict vide).
        variables: Dict des variables accumulees dans ProcessInstance.

    Returns:
        True si la condition est satisfaite.
    """
    if not condition:
        return True

    if not isinstance(condition, dict):
        logger.warning("Condition invalide (pas un dict): %r", condition)
        return False

    # Conditions composees
    if 'and' in condition:
        sub_conditions = condition['and']
        if not isinstance(sub_conditions, list):
            return False
        return all(evaluate_condition(c, variables) for c in sub_conditions)

    if 'or' in condition:
        sub_conditions = condition['or']
        if not isinstance(sub_conditions, list):
            return False
        return any(evaluate_condition(c, variables) for c in sub_conditions)

    if 'not' in condition:
        return not evaluate_condition(condition['not'], variables)

    # Condition atomique
    variable = condition.get('variable')
    operator = condition.get('operator', '==')
    expected = condition.get('value')

    if variable is None:
        logger.warning("Condition atomique sans 'variable': %r", condition)
        return False

    if operator not in SUPPORTED_OPERATORS:
        logger.warning("Operateur non supporte: %s", operator)
        return False

    actual = variables.get(variable)

    try:
        if operator == '==':
            return actual == expected
        if operator == '!=':
            return actual != expected
        if operator == '>':
            return actual is not None and actual > expected
        if operator == '<':
            return actual is not None and actual < expected
        if operator == '>=':
            return actual is not None and actual >= expected
        if operator == '<=':
            return actual is not None and actual <= expected
        if operator == 'in':
            return actual in (expected or [])
        if operator == 'not_in':
            return actual not in (expected or [])
        if operator == 'contains':
            return expected in (actual or '')
        if operator == 'is_null':
            return actual is None
        if operator == 'is_not_null':
            return actual is not None
    except (TypeError, ValueError) as e:
        logger.warning("Erreur evaluation condition %r: %s", condition, e)
        return False

    return False


# =============================================================================
# Resolution des variables dans les valeurs de configuration
# =============================================================================

def resolve_value(value: Any, variables: Dict[str, Any], user=None, mandat=None) -> Any:
    """
    Resout les variables {{x}} dans une valeur de configuration.

    Supporte:
    - `{{variable_name}}` → variables[variable_name]
    - `{{current_user}}`, `{{current_user.email}}` → attributs de l'user
    - `{{mandat_id}}` → mandat.pk
    - `{{today}}`, `{{now}}` → date/datetime actuel
    - Chaines sans {{}} → retournees telles quelles
    - Listes/dicts → recursive
    """
    if isinstance(value, dict):
        return {k: resolve_value(v, variables, user, mandat) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_value(v, variables, user, mandat) for v in value]
    if not isinstance(value, str) or '{{' not in value:
        return value

    import re
    pattern = re.compile(r'\{\{(\w+(?:\.\w+)*)\}\}')

    def replace(match):
        var_path = match.group(1)

        if var_path == 'today':
            return date.today().isoformat()
        if var_path == 'now':
            return timezone.now().isoformat()
        if var_path == 'mandat_id':
            return str(mandat.pk) if mandat else ''
        if var_path == 'current_user':
            return str(user.pk) if user else ''
        if var_path.startswith('current_user.'):
            attr = var_path.split('.', 1)[1]
            if user and hasattr(user, attr):
                return str(getattr(user, attr))
            return ''

        # Variable simple ou dotted path dans variables dict
        if '.' in var_path:
            parts = var_path.split('.')
            obj: Any = variables.get(parts[0])
            for part in parts[1:]:
                if obj is None:
                    return ''
                if isinstance(obj, dict):
                    obj = obj.get(part)
                else:
                    obj = getattr(obj, part, None)
            return str(obj) if obj is not None else ''

        val = variables.get(var_path)
        return str(val) if val is not None else ''

    return pattern.sub(replace, value)


# =============================================================================
# BaseStepExecutor et executors specifiques
# =============================================================================

class StepExecutorError(Exception):
    """Erreur levee par un step executor (execution echouee)."""


class BaseStepExecutor:
    """
    Classe de base pour tous les executors de steps.

    Chaque sous-classe implemente `execute(self, execution)` qui retourne:
        (new_status, output_dict)
    ou
        (new_status, output_dict, variables_update_dict)

    `new_status` est une valeur de StepExecution.Status.
    `output_dict` est persiste dans StepExecution.output.
    `variables_update_dict` est merge dans ProcessInstance.variables.
    """

    step_type: Optional[str] = None

    def __init__(self, execution: StepExecution):
        self.execution = execution
        self.step = execution.step
        self.instance = execution.instance
        self.config = self.step.configuration or {}
        self.variables = dict(self.instance.variables or {})

    def execute(self) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        raise NotImplementedError

    def _resolve(self, value: Any) -> Any:
        return resolve_value(
            value,
            self.variables,
            user=self.instance.triggered_by,
            mandat=self.instance.mandat,
        )


class StartStepExecutor(BaseStepExecutor):
    """Step START: point d'entree, no-op, passe direct a COMPLETED."""
    step_type = ProcessStep.StepType.START

    def execute(self):
        return StepExecution.Status.COMPLETED, {'started': True}, {}


class EndStepExecutor(BaseStepExecutor):
    """
    Step END: marque le step comme COMPLETED. Le ProcessExecutor voit
    qu'il n'y a plus de transition sortante et met l'instance en COMPLETED.
    """
    step_type = ProcessStep.StepType.END

    def execute(self):
        return StepExecution.Status.COMPLETED, {'ended': True}, {}


class FormFillStepExecutor(BaseStepExecutor):
    """
    Step FORM_FILL: cree une FormSubmission PENDING et passe en WAITING.

    Le user doit aller remplir le formulaire via /modelforms/formulaires/{pk}/.
    Quand la submission est marquee COMPLETED, le trigger externe (typiquement
    un signal post_save) doit appeler `ProcessExecutor.advance()` avec les
    donnees de la submission pour faire continuer le processus.

    Configuration attendue:
        {
            "form_config_code": "CLIENT_RAPIDE",
            "assignee": "{{current_user}}",   # optionnel
            "title": "Remplir le formulaire"  # optionnel
        }
    """
    step_type = ProcessStep.StepType.FORM_FILL

    def execute(self):
        form_code = self.config.get('form_config_code')
        if not form_code:
            raise StepExecutorError(
                "FORM_FILL step: 'form_config_code' manquant dans la configuration"
            )

        try:
            form_config = FormConfiguration.objects.get(code=form_code)
        except FormConfiguration.DoesNotExist:
            raise StepExecutorError(
                f"FORM_FILL step: FormConfiguration '{form_code}' introuvable"
            )

        # Creer une FormSubmission PENDING, liee au step_execution via FK
        submission = FormSubmission.objects.create(
            form_config=form_config,
            submitted_data={},
            submitted_by=self.instance.triggered_by,
            mandat=self.instance.mandat,
            status=FormSubmission.Status.PENDING,
        )
        self.execution.form_submission = submission
        self.execution.save(update_fields=['form_submission', 'updated_at'])

        return (
            StepExecution.Status.WAITING,
            {
                'form_submission_id': str(submission.pk),
                'form_config_code': form_code,
                'waiting_for': 'form_submission',
            },
            {},
        )


class HumanApprovalStepExecutor(BaseStepExecutor):
    """
    Step HUMAN_APPROVAL: cree une core.Tache et passe en WAITING.

    L'humain doit ensuite appeler advance() avec {"approved": true/false}
    depuis l'interface d'execution.

    Configuration:
        {
            "title": "Valider le nouveau client: {{record.raison_sociale}}",
            "assignee_user_id": "{{current_user}}",
            "deadline_days": 5
        }
    """
    step_type = ProcessStep.StepType.HUMAN_APPROVAL

    def execute(self):
        from core.models import Tache, User

        title = self._resolve(
            self.config.get('title', f'Validation: {self.step.name}')
        )
        assignee_expr = self.config.get('assignee_user_id', '{{current_user}}')
        assignee_id = self._resolve(assignee_expr)

        try:
            assignee = User.objects.get(pk=assignee_id)
        except (User.DoesNotExist, ValueError):
            assignee = self.instance.triggered_by

        description = self._resolve(
            self.config.get(
                'description',
                f"Tache automatique du processus {self.instance.process_def.code}",
            )
        )

        tache = Tache.objects.create(
            titre=title[:255],
            description=description,
            cree_par=self.instance.triggered_by,
            created_by=self.instance.triggered_by,
            mandat=self.instance.mandat,
            priorite=self.config.get('priorite', 'NORMALE'),
        )
        if assignee:
            tache.assignes.add(assignee)

        return (
            StepExecution.Status.WAITING,
            {
                'tache_id': str(tache.pk),
                'assignee_id': str(assignee.pk) if assignee else None,
                'waiting_for': 'human_approval',
            },
            {'approval_tache_id': str(tache.pk)},
        )


class CreateObjectStepExecutor(BaseStepExecutor):
    """
    Step CREATE_OBJECT: cree un objet Django arbitraire.

    Reutilise la logique de _create_object_action du submission_handler.

    Configuration:
        {
            "model": "core.Client",
            "field_mapping": {
                "raison_sociale": "{{nom_societe}}",
                "email": "{{email}}",
                "mandat_id": "{{mandat_id}}"
            },
            "output_variable": "client"  # optionnel: stocke l'instance dans variables
        }
    """
    step_type = ProcessStep.StepType.CREATE_OBJECT

    def execute(self):
        model_path = self.config.get('model')
        if not model_path:
            raise StepExecutorError(
                "CREATE_OBJECT step: 'model' manquant dans la configuration"
            )

        try:
            app_label, model_name = model_path.split('.')
            model_class = apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as e:
            raise StepExecutorError(
                f"CREATE_OBJECT step: modele '{model_path}' introuvable: {e}"
            )

        field_mapping = self.config.get('field_mapping', {})
        if not isinstance(field_mapping, dict):
            raise StepExecutorError(
                "CREATE_OBJECT step: 'field_mapping' doit etre un dict"
            )

        # Resoudre les variables dans chaque valeur
        resolved_data = {}
        for field_name, raw_value in field_mapping.items():
            resolved_data[field_name] = self._resolve(raw_value)

        try:
            instance = model_class(**resolved_data)
            instance.full_clean()
            instance.save()
        except ValidationError as e:
            raise StepExecutorError(f"CREATE_OBJECT step: validation - {e}")

        output = {
            'model': model_path,
            'id': str(instance.pk),
            'repr': str(instance),
        }

        # Variable dedicace pour que les steps suivants puissent referencer
        # l'objet cree (ex: {{client.id}})
        output_var = self.config.get('output_variable')
        variables_update = {}
        if output_var:
            # Serialiser les champs principaux pour utilisation dans resolve_value
            obj_dict = {'id': str(instance.pk)}
            for field in instance._meta.fields:
                try:
                    val = getattr(instance, field.name)
                    if hasattr(val, 'pk'):
                        obj_dict[field.name] = str(val.pk)
                    elif isinstance(val, (str, int, float, bool)) or val is None:
                        obj_dict[field.name] = val
                    else:
                        obj_dict[field.name] = str(val)
                except Exception:
                    pass
            variables_update[output_var] = obj_dict

        return StepExecution.Status.COMPLETED, output, variables_update


class SendEmailStepExecutor(BaseStepExecutor):
    """
    Step SEND_EMAIL: envoie un email via mailing.EmailService.

    Configuration:
        Mode template:
            {"template": "NOUVEAU_CLIENT", "to": "{{client.email}}"}

        Mode inline:
            {"to": "{{email}}", "subject": "Bienvenue", "body": "..."}
    """
    step_type = ProcessStep.StepType.SEND_EMAIL

    def execute(self):
        from mailing.services import EmailService

        to_expr = self.config.get('to', '')
        destinataire = self._resolve(to_expr)
        if not destinataire:
            raise StepExecutorError(
                "SEND_EMAIL step: 'to' non defini ou resolution vide"
            )

        svc = EmailService()
        template_code = self.config.get('template')

        if template_code:
            # Mode template
            context = {
                'user': self.instance.triggered_by,
                'mandat': self.instance.mandat,
                'process_code': self.instance.process_def.code,
            }
            context.update(self.variables)
            context.update(self.config.get('context', {}))

            email_envoye = svc.send_template_email(
                destinataire=destinataire,
                template_code=template_code,
                context=context,
                utilisateur=self.instance.triggered_by,
                mandat=self.instance.mandat,
                content_type='process_execution',
                object_id=str(self.instance.pk),
            )
            if email_envoye is None:
                raise StepExecutorError(
                    f"Template email '{template_code}' introuvable ou inactif"
                )
            return (
                StepExecution.Status.COMPLETED,
                {
                    'email_id': str(email_envoye.pk),
                    'destinataire': destinataire,
                    'template': template_code,
                },
                {},
            )

        # Mode inline
        subject = self._resolve(self.config.get('subject', 'Notification'))
        body = self._resolve(self.config.get('body', ''))
        if not body:
            raise StepExecutorError(
                "SEND_EMAIL step: 'body' ou 'template' requis"
            )

        email_envoye = svc.send_email(
            destinataire=destinataire,
            sujet=subject,
            corps_html=body,
            utilisateur=self.instance.triggered_by,
            mandat=self.instance.mandat,
            content_type='process_execution',
            object_id=str(self.instance.pk),
        )
        return (
            StepExecution.Status.COMPLETED,
            {
                'email_id': str(email_envoye.pk),
                'destinataire': destinataire,
                'subject': subject,
            },
            {},
        )


# =============================================================================
# Dispatcher
# =============================================================================

STEP_EXECUTORS: Dict[str, type] = {
    ProcessStep.StepType.START: StartStepExecutor,
    ProcessStep.StepType.END: EndStepExecutor,
    ProcessStep.StepType.FORM_FILL: FormFillStepExecutor,
    ProcessStep.StepType.HUMAN_APPROVAL: HumanApprovalStepExecutor,
    ProcessStep.StepType.CREATE_OBJECT: CreateObjectStepExecutor,
    ProcessStep.StepType.SEND_EMAIL: SendEmailStepExecutor,
}


def get_executor_class(step_type: str) -> Optional[type]:
    return STEP_EXECUTORS.get(step_type)


# =============================================================================
# ProcessExecutor — orchestrateur principal
# =============================================================================

class ProcessExecutor:
    """
    Orchestre l'execution complete d'une ProcessInstance.

    Utilisation:
        executor = ProcessExecutor(instance)
        executor.start()                    # declenche depuis le START step
        executor.advance({'approved': True}) # apres un step WAITING
    """

    # Limite de securite: nombre max de steps consecutifs synchrones pour
    # eviter une boucle infinie via mauvaises transitions.
    MAX_STEPS_PER_CALL = 50

    def __init__(self, instance: ProcessInstance):
        self.instance = instance

    # --- API publique ---

    def start(self) -> ProcessInstance:
        """
        Demarre l'execution de l'instance.

        Trouve le step START (ou le step avec order minimal si pas de START
        explicite) et enchaine les executions jusqu'a tomber sur un step
        WAITING, FAILED, ou END.
        """
        if self.instance.status != ProcessInstance.Status.PENDING:
            raise ValueError(
                f"Impossible de demarrer une instance en statut {self.instance.status}"
            )

        start_step = self._find_start_step()
        if start_step is None:
            self._fail("Aucun step de demarrage trouve dans le processus")
            return self.instance

        self.instance.status = ProcessInstance.Status.RUNNING
        self.instance.current_step = start_step
        self.instance.started_at = timezone.now()
        self.instance.save(update_fields=[
            'status', 'current_step', 'started_at', 'updated_at',
        ])

        self._run_from(start_step)
        return self.instance

    def advance(self, trigger_data: Optional[Dict[str, Any]] = None) -> ProcessInstance:
        """
        Fait avancer une instance qui etait en WAITING (HUMAN_APPROVAL, FORM_FILL).

        `trigger_data` est merge dans les variables avant de suivre les
        transitions (ex: `{'approved': True}` ou `{'form_data': {...}}`).
        """
        if self.instance.status not in (
            ProcessInstance.Status.WAITING,
            ProcessInstance.Status.RUNNING,
        ):
            raise ValueError(
                f"Impossible d'avancer une instance en statut {self.instance.status}"
            )

        if trigger_data:
            new_vars = dict(self.instance.variables or {})
            new_vars.update(trigger_data)
            self.instance.variables = new_vars
            self.instance.save(update_fields=['variables', 'updated_at'])

        # Completer le StepExecution courant si il etait WAITING
        current_exec = self.instance.step_executions.filter(
            step=self.instance.current_step,
            status=StepExecution.Status.WAITING,
        ).order_by('-created_at').first()
        if current_exec:
            current_exec.status = StepExecution.Status.COMPLETED
            current_exec.completed_at = timezone.now()
            if trigger_data:
                out = dict(current_exec.output or {})
                out['trigger_data'] = trigger_data
                current_exec.output = out
            current_exec.save(update_fields=[
                'status', 'completed_at', 'output', 'updated_at',
            ])

        self.instance.status = ProcessInstance.Status.RUNNING
        self.instance.save(update_fields=['status', 'updated_at'])

        # Suivre les transitions depuis le step courant
        next_step = self._find_next_step(self.instance.current_step)
        if next_step is None:
            self._complete()
            return self.instance

        self._run_from(next_step)
        return self.instance

    def cancel(self, reason: str = '') -> ProcessInstance:
        """Annule une instance en cours."""
        self.instance.status = ProcessInstance.Status.CANCELLED
        if reason:
            self.instance.error_message = f"Annule: {reason}"
        self.instance.completed_at = timezone.now()
        self.instance.save(update_fields=[
            'status', 'error_message', 'completed_at', 'updated_at',
        ])
        return self.instance

    # --- Internals ---

    def _find_start_step(self) -> Optional[ProcessStep]:
        start = self.instance.process_def.steps.filter(
            step_type=ProcessStep.StepType.START,
        ).first()
        if start:
            return start
        return self.instance.process_def.steps.order_by('order', 'code').first()

    def _find_next_step(self, current_step: Optional[ProcessStep]) -> Optional[ProcessStep]:
        if current_step is None:
            return None

        # END → plus de suite
        if current_step.step_type == ProcessStep.StepType.END:
            return None

        transitions = current_step.outgoing_transitions.select_related(
            'to_step',
        ).order_by('order')

        if not transitions.exists():
            # Fallback: prendre le step avec order +1 dans le meme processus
            next_by_order = current_step.process.steps.filter(
                order__gt=current_step.order,
            ).order_by('order').first()
            return next_by_order

        for trans in transitions:
            if evaluate_condition(trans.condition or {}, self.instance.variables or {}):
                return trans.to_step

        # Aucune condition ne matche
        return None

    def _run_from(self, first_step: ProcessStep):
        """
        Execute une chaine de steps synchrones en partant de `first_step`,
        jusqu'a tomber sur un step WAITING, un END, ou une erreur.

        Protege contre les boucles infinies via MAX_STEPS_PER_CALL.
        """
        current = first_step
        steps_executed = 0

        while current is not None and steps_executed < self.MAX_STEPS_PER_CALL:
            steps_executed += 1
            execution, status = self._execute_step(current)

            if status == StepExecution.Status.FAILED:
                self._fail(execution.error_message or 'Step failed')
                return

            if status == StepExecution.Status.WAITING:
                self.instance.status = ProcessInstance.Status.WAITING
                self.instance.current_step = current
                self.instance.save(update_fields=[
                    'status', 'current_step', 'updated_at',
                ])
                return

            # Step COMPLETED. Si c'est END, on a termine.
            if current.step_type == ProcessStep.StepType.END:
                self._complete()
                return

            # Trouver le prochain step
            next_step = self._find_next_step(current)
            if next_step is None:
                # Plus de transition → considere comme termine
                self._complete()
                return

            current = next_step
            self.instance.current_step = current
            self.instance.save(update_fields=['current_step', 'updated_at'])

        # Boucle max atteinte
        if steps_executed >= self.MAX_STEPS_PER_CALL:
            self._fail(
                f"Limite de {self.MAX_STEPS_PER_CALL} steps consecutifs atteinte "
                "(boucle potentielle)"
            )

    def _execute_step(self, step: ProcessStep) -> Tuple[StepExecution, str]:
        """
        Execute un step unique.

        Cree le StepExecution, instancie l'executor adequat, execute, et
        persiste le resultat. Retourne (execution, status).
        """
        execution = StepExecution.objects.create(
            instance=self.instance,
            step=step,
            status=StepExecution.Status.RUNNING,
            input=dict(self.instance.variables or {}),
            started_at=timezone.now(),
        )

        # Evaluer les conditions de visibilite du step lui-meme
        if step.conditions and not evaluate_condition(
            step.conditions, self.instance.variables or {},
        ):
            execution.status = StepExecution.Status.SKIPPED
            execution.completed_at = timezone.now()
            execution.output = {'skipped_reason': 'step conditions not met'}
            execution.save(update_fields=[
                'status', 'completed_at', 'output', 'updated_at',
            ])
            return execution, StepExecution.Status.SKIPPED

        executor_cls = get_executor_class(step.step_type)
        if executor_cls is None:
            execution.status = StepExecution.Status.FAILED
            execution.completed_at = timezone.now()
            execution.error_message = (
                f"Pas d'executor pour step_type={step.step_type}"
            )
            execution.save(update_fields=[
                'status', 'completed_at', 'error_message', 'updated_at',
            ])
            return execution, StepExecution.Status.FAILED

        try:
            executor = executor_cls(execution)
            result = executor.execute()
            if len(result) == 2:
                new_status, output = result
                variables_update = {}
            else:
                new_status, output, variables_update = result
        except StepExecutorError as e:
            logger.warning(
                "Step %s FAILED (expected): %s", step.code, e,
            )
            execution.status = StepExecution.Status.FAILED
            execution.completed_at = timezone.now()
            execution.error_message = str(e)
            execution.save(update_fields=[
                'status', 'completed_at', 'error_message', 'updated_at',
            ])
            return execution, StepExecution.Status.FAILED
        except Exception as e:
            logger.error(
                "Step %s FAILED (unexpected): %s", step.code, e,
                exc_info=True,
            )
            execution.status = StepExecution.Status.FAILED
            execution.completed_at = timezone.now()
            execution.error_message = f"Erreur inattendue: {e}"
            execution.save(update_fields=[
                'status', 'completed_at', 'error_message', 'updated_at',
            ])
            return execution, StepExecution.Status.FAILED

        # Mettre a jour execution
        execution.status = new_status
        execution.output = output
        if new_status != StepExecution.Status.WAITING:
            execution.completed_at = timezone.now()
        execution.save(update_fields=[
            'status', 'output', 'completed_at', 'updated_at',
        ])

        # Merger les variables dans l'instance
        if variables_update:
            new_vars = dict(self.instance.variables or {})
            new_vars.update(variables_update)
            self.instance.variables = new_vars
            self.instance.save(update_fields=['variables', 'updated_at'])

        return execution, new_status

    def _complete(self):
        self.instance.status = ProcessInstance.Status.COMPLETED
        self.instance.completed_at = timezone.now()
        self.instance.current_step = None
        self.instance.save(update_fields=[
            'status', 'completed_at', 'current_step', 'updated_at',
        ])

    def _fail(self, message: str):
        self.instance.status = ProcessInstance.Status.FAILED
        self.instance.error_message = message
        self.instance.completed_at = timezone.now()
        self.instance.save(update_fields=[
            'status', 'error_message', 'completed_at', 'updated_at',
        ])
