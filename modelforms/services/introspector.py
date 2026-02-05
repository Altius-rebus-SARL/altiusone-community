# apps/modelforms/services/introspector.py
"""
Service d'introspection des modèles Django.

Ce module permet d'extraire automatiquement les métadonnées des modèles Django
pour générer des schémas de formulaires dynamiques.

Supporte TOUS les modèles de TOUTES les applications Django installées.
"""
from typing import Dict, List, Optional, Any, Type
from django.db import models
from django.apps import apps
from django.db.models.fields import Field
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    MinLengthValidator,
    MaxLengthValidator,
    RegexValidator,
)


# Apps Django système à exclure de l'introspection
EXCLUDED_APPS = {
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'oauth2_provider',
    'oidc_provider',
    'debug_toolbar',
    'silk',
    'django_extensions',
    'celery',
    'django_celery_beat',
    'django_celery_results',
}

# Modèles système à toujours exclure
EXCLUDED_MODELS = {
    'contenttypes.ContentType',
    'sessions.Session',
    'admin.LogEntry',
    'auth.Permission',
    'auth.Group',
    'authtoken.Token',
    'authtoken.TokenProxy',
    'oauth2_provider.AccessToken',
    'oauth2_provider.Application',
    'oauth2_provider.Grant',
    'oauth2_provider.RefreshToken',
    'oauth2_provider.IDToken',
    'oidc_provider.Client',
    'oidc_provider.Code',
    'oidc_provider.Token',
    'oidc_provider.RSAKey',
    'oidc_provider.UserConsent',
    'django_celery_beat.ClockedSchedule',
    'django_celery_beat.CrontabSchedule',
    'django_celery_beat.IntervalSchedule',
    'django_celery_beat.PeriodicTask',
    'django_celery_beat.PeriodicTasks',
    'django_celery_beat.SolarSchedule',
    'django_celery_results.TaskResult',
    'django_celery_results.GroupResult',
}


# Mapping des types de champs Django vers les types de widgets
FIELD_TYPE_MAPPING = {
    # Champs texte
    'CharField': 'text',
    'TextField': 'textarea',
    'EmailField': 'email',
    'URLField': 'text',
    'SlugField': 'text',
    # Champs numériques
    'IntegerField': 'number',
    'PositiveIntegerField': 'number',
    'PositiveSmallIntegerField': 'number',
    'SmallIntegerField': 'number',
    'BigIntegerField': 'number',
    'FloatField': 'decimal',
    'DecimalField': 'decimal',
    # Dates et heures
    'DateField': 'date',
    'DateTimeField': 'datetime',
    'TimeField': 'time',
    # Booléen
    'BooleanField': 'checkbox',
    'NullBooleanField': 'checkbox',
    # Fichiers
    'FileField': 'file',
    'ImageField': 'image',
    # Relations
    'ForeignKey': 'autocomplete',
    'OneToOneField': 'autocomplete',
    'ManyToManyField': 'autocomplete',
    # JSON
    'JSONField': 'textarea',
    # UUID
    'UUIDField': 'text',
    # Spéciaux
    'CountryField': 'country',
}


# Groupes logiques suggérés basés sur les noms de champs
FIELD_GROUPS = {
    'identity': ['nom', 'prenom', 'raison_sociale', 'nom_commercial', 'civilite', 'sexe', 'matricule'],
    'contact': ['email', 'telephone', 'mobile', 'phone', 'fax', 'site_web'],
    'address': ['rue', 'numero', 'complement', 'code_postal', 'npa', 'localite', 'ville', 'canton', 'region', 'pays'],
    'dates': ['date_naissance', 'date_creation', 'date_debut', 'date_fin', 'date_entree', 'date_sortie'],
    'financial': ['iban', 'bic', 'salaire', 'montant', 'taux', 'prix'],
    'status': ['statut', 'status', 'is_active', 'actif'],
}


class ModelIntrospector:
    """
    Introspecteur de modèles Django.

    Extrait les métadonnées des modèles pour générer des schémas de formulaires.
    Supporte TOUS les modèles de l'application, pas seulement une whitelist.
    """

    def __init__(self, model_path: str, validate: bool = True):
        """
        Initialise l'introspecteur.

        Args:
            model_path: Chemin du modèle (ex: 'core.Client')
            validate: Si True, vérifie que le modèle n'est pas exclu
        """
        self.model_path = model_path
        self.validate = validate
        self.model_class = self._get_model_class()

    def _get_model_class(self) -> Type[models.Model]:
        """Récupère la classe du modèle."""
        if self.validate and self.model_path in EXCLUDED_MODELS:
            raise ValueError(f"Modèle système non autorisé: {self.model_path}")

        try:
            app_label, model_name = self.model_path.split('.')
            return apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as e:
            raise ValueError(f"Modèle introuvable: {self.model_path}") from e

    @classmethod
    def get_all_models(cls, include_system: bool = False) -> List[Dict[str, Any]]:
        """
        Retourne TOUS les modèles disponibles, groupés par application.

        Args:
            include_system: Si True, inclut les modèles système (auth, admin, etc.)

        Returns:
            Liste de dictionnaires avec les métadonnées des modèles
        """
        result = []

        for app_config in apps.get_app_configs():
            # Exclure les apps système si demandé
            if not include_system:
                if app_config.name in EXCLUDED_APPS:
                    continue
                # Exclure les apps Django internes
                if app_config.name.startswith('django.'):
                    continue

            app_models = []
            for model in app_config.get_models():
                model_path = f"{model._meta.app_label}.{model._meta.model_name}"

                # Exclure les modèles système
                if not include_system and model_path in EXCLUDED_MODELS:
                    continue

                # Capitaliser le nom du modèle
                model_name = model._meta.model_name
                model_name_display = model_name[0].upper() + model_name[1:] if model_name else model_name

                app_models.append({
                    'path': f"{model._meta.app_label}.{model_name_display}",
                    'app': model._meta.app_label,
                    'name': model_name_display,
                    'verbose_name': str(model._meta.verbose_name),
                    'verbose_name_plural': str(model._meta.verbose_name_plural),
                    'field_count': len([
                        f for f in model._meta.get_fields()
                        if not (f.auto_created and not f.concrete)
                    ]),
                })

            if app_models:
                result.append({
                    'app_label': app_config.label,
                    'app_name': app_config.verbose_name or app_config.label,
                    'models': sorted(app_models, key=lambda x: x['name']),
                })

        return sorted(result, key=lambda x: x['app_label'])

    @classmethod
    def get_allowed_models(cls) -> List[Dict[str, str]]:
        """
        Retourne la liste des modèles disponibles (format flat pour compatibilité).

        Cette méthode est conservée pour la compatibilité avec le code existant.
        """
        result = []
        for app_group in cls.get_all_models():
            for model_info in app_group['models']:
                result.append({
                    'path': model_info['path'],
                    'app': model_info['app'],
                    'name': model_info['name'],
                    'verbose_name': model_info['verbose_name'],
                    'verbose_name_plural': model_info['verbose_name_plural'],
                })
        return result

    @classmethod
    def search_models(cls, query: str) -> List[Dict[str, str]]:
        """
        Recherche de modèles par nom ou app.

        Args:
            query: Terme de recherche (recherche insensible à la casse)

        Returns:
            Liste de modèles correspondants
        """
        query_lower = query.lower()
        results = []

        for model_info in cls.get_allowed_models():
            # Recherche dans le nom, l'app, le verbose_name et le path
            searchable = ' '.join([
                model_info['name'],
                model_info['app'],
                model_info['verbose_name'],
                model_info['path'],
            ]).lower()

            if query_lower in searchable:
                results.append(model_info)

        return results

    def get_schema(self) -> Dict[str, Any]:
        """
        Retourne le schéma complet du modèle.
        """
        return {
            'model': self.model_path,
            'verbose_name': str(self.model_class._meta.verbose_name),
            'verbose_name_plural': str(self.model_class._meta.verbose_name_plural),
            'fields': self.get_fields(),
            'suggested_groups': self.get_suggested_groups(),
        }

    def get_fields(self, include_system: bool = False) -> List[Dict[str, Any]]:
        """
        Extrait les informations de tous les champs du modèle.

        Args:
            include_system: Si True, inclut les champs système (id, created_at, etc.)
        """
        fields = []
        system_fields = {'id', 'pk', 'created_at', 'updated_at', 'created_by', 'is_active'}

        for field in self.model_class._meta.get_fields():
            # Ignorer les relations inverses
            if field.auto_created and not field.concrete:
                continue

            # Ignorer certains champs système sauf si demandé
            if not include_system and field.name in system_fields:
                continue

            field_info = self._extract_field_info(field)
            if field_info:
                fields.append(field_info)

        return fields

    def search_fields(self, query: str) -> List[Dict[str, Any]]:
        """
        Recherche de champs par nom ou label.

        Args:
            query: Terme de recherche

        Returns:
            Liste de champs correspondants
        """
        query_lower = query.lower()
        results = []

        for field_info in self.get_fields(include_system=True):
            searchable = ' '.join([
                field_info['name'],
                field_info.get('label', ''),
                field_info.get('help_text', ''),
            ]).lower()

            if query_lower in searchable:
                results.append(field_info)

        return results

    def _extract_field_info(self, field: Field) -> Optional[Dict[str, Any]]:
        """
        Extrait les informations d'un champ.
        """
        field_type = field.__class__.__name__

        # Informations de base
        info = {
            'name': field.name,
            'type': field_type,
            'widget_type': self._get_widget_type(field),
            'label': str(field.verbose_name) if hasattr(field, 'verbose_name') else field.name,
            'help_text': str(field.help_text) if hasattr(field, 'help_text') and field.help_text else '',
            'required': not getattr(field, 'blank', True),
            'editable': getattr(field, 'editable', True),
        }

        # Valeur par défaut
        if hasattr(field, 'default') and field.default is not models.NOT_PROVIDED:
            if callable(field.default):
                info['has_default'] = True
            else:
                info['default'] = field.default

        # Longueur maximale
        if hasattr(field, 'max_length') and field.max_length:
            info['max_length'] = field.max_length

        # Choix (pour les champs avec choices)
        if hasattr(field, 'choices') and field.choices:
            info['choices'] = [
                {'value': choice[0], 'label': str(choice[1])}
                for choice in field.choices
            ]
            info['widget_type'] = 'select'

        # Relations
        if isinstance(field, (ForeignKey, OneToOneField)):
            related_model = field.related_model
            model_name = related_model._meta.model_name
            info['related_model'] = f"{related_model._meta.app_label}.{model_name[0].upper() + model_name[1:]}"
            info['related_verbose_name'] = str(related_model._meta.verbose_name)

        elif isinstance(field, ManyToManyField):
            related_model = field.related_model
            model_name = related_model._meta.model_name
            info['related_model'] = f"{related_model._meta.app_label}.{model_name[0].upper() + model_name[1:]}"
            info['related_verbose_name'] = str(related_model._meta.verbose_name_plural)
            info['multiple'] = True

        # Validations
        validators = self._extract_validators(field)
        if validators:
            info['validators'] = validators

        return info

    def _get_widget_type(self, field: Field) -> str:
        """
        Détermine le type de widget approprié pour un champ.
        """
        field_type = field.__class__.__name__

        # Vérifier d'abord si le champ a des choices
        if hasattr(field, 'choices') and field.choices:
            return 'select'

        # Détection spéciale pour certains noms de champs
        field_name = field.name.lower()

        # IBAN
        if 'iban' in field_name:
            return 'iban'

        # AVS
        if 'avs' in field_name:
            return 'avs'

        # IDE
        if 'ide' in field_name:
            return 'ide'

        # Téléphone
        if any(x in field_name for x in ['phone', 'telephone', 'mobile', 'fax']):
            return 'phone'

        # Montant/Prix
        if any(x in field_name for x in ['montant', 'prix', 'salaire', 'tarif', 'cout']):
            return 'currency'

        # Canton suisse
        if 'canton' in field_name:
            return 'canton'

        # Pays
        if field_type == 'CountryField' or 'pays' in field_name:
            return 'country'

        # Utiliser le mapping par défaut
        return FIELD_TYPE_MAPPING.get(field_type, 'text')

    def _extract_validators(self, field: Field) -> List[Dict[str, Any]]:
        """
        Extrait les informations des validateurs du champ.
        """
        validators = []

        if not hasattr(field, 'validators'):
            return validators

        for validator in field.validators:
            if isinstance(validator, MinValueValidator):
                validators.append({
                    'type': 'min_value',
                    'value': validator.limit_value,
                })
            elif isinstance(validator, MaxValueValidator):
                validators.append({
                    'type': 'max_value',
                    'value': validator.limit_value,
                })
            elif isinstance(validator, MinLengthValidator):
                validators.append({
                    'type': 'min_length',
                    'value': validator.limit_value,
                })
            elif isinstance(validator, MaxLengthValidator):
                validators.append({
                    'type': 'max_length',
                    'value': validator.limit_value,
                })
            elif isinstance(validator, RegexValidator):
                validators.append({
                    'type': 'regex',
                    'pattern': validator.regex.pattern,
                    'message': str(validator.message) if validator.message else None,
                })

        return validators

    def get_suggested_groups(self) -> List[Dict[str, Any]]:
        """
        Suggère des groupes logiques pour les champs du modèle.
        """
        fields = {f.name for f in self.model_class._meta.get_fields() if hasattr(f, 'name')}
        groups = []

        for group_id, group_fields in FIELD_GROUPS.items():
            matching_fields = [f for f in group_fields if f in fields]
            if matching_fields:
                groups.append({
                    'id': group_id,
                    'title': group_id.replace('_', ' ').title(),
                    'fields': matching_fields,
                })

        return groups

    def get_json_schema(self) -> Dict[str, Any]:
        """
        Génère un schéma JSON Schema pour le modèle.
        Utile pour la validation côté client.
        """
        properties = {}
        required = []

        for field_info in self.get_fields():
            field_name = field_info['name']

            # Type JSON Schema
            json_type = self._get_json_type(field_info)
            prop = {'type': json_type}

            # Label
            if field_info.get('label'):
                prop['title'] = field_info['label']

            # Description
            if field_info.get('help_text'):
                prop['description'] = field_info['help_text']

            # Énumérations
            if field_info.get('choices'):
                prop['enum'] = [c['value'] for c in field_info['choices']]
                prop['enumNames'] = [c['label'] for c in field_info['choices']]

            # Longueur
            if field_info.get('max_length'):
                prop['maxLength'] = field_info['max_length']

            # Validateurs
            for validator in field_info.get('validators', []):
                if validator['type'] == 'min_value':
                    prop['minimum'] = validator['value']
                elif validator['type'] == 'max_value':
                    prop['maximum'] = validator['value']
                elif validator['type'] == 'min_length':
                    prop['minLength'] = validator['value']
                elif validator['type'] == 'regex':
                    prop['pattern'] = validator['pattern']

            properties[field_name] = prop

            # Champs requis
            if field_info.get('required'):
                required.append(field_name)

        return {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            'type': 'object',
            'title': str(self.model_class._meta.verbose_name),
            'properties': properties,
            'required': required,
        }

    def _get_json_type(self, field_info: Dict[str, Any]) -> str:
        """
        Convertit le type Django en type JSON Schema.
        """
        widget_type = field_info.get('widget_type', 'text')
        django_type = field_info.get('type', '')

        # Booléens
        if widget_type == 'checkbox' or django_type == 'BooleanField':
            return 'boolean'

        # Nombres
        if widget_type in ('number', 'decimal', 'currency'):
            if 'Integer' in django_type:
                return 'integer'
            return 'number'

        # Tableaux (M2M)
        if field_info.get('multiple'):
            return 'array'

        # Objets (JSON)
        if django_type == 'JSONField':
            return 'object'

        # Par défaut: string
        return 'string'
