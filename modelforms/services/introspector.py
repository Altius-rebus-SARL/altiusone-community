# apps/modelforms/services/introspector.py
"""
Service d'introspection des modèles Django.

Ce module permet d'extraire automatiquement les métadonnées des modèles Django
pour générer des schémas de formulaires dynamiques.
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


# Whitelist des modèles autorisés pour l'introspection (sécurité)
ALLOWED_MODELS = {
    # Core
    'core.Client',
    'core.Contact',
    'core.Adresse',
    'core.Mandat',
    'core.CompteBancaire',
    'core.Tache',
    # Salaires
    'salaires.Employe',
    # Facturation (si existants)
    'facturation.Facture',
    'facturation.LigneFacture',
    'facturation.Prestation',
    'facturation.TimeTracking',
    # Documents
    'documents.Document',
    # Comptabilité
    'comptabilite.Ecriture',
    'comptabilite.CompteComptable',
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
    """

    def __init__(self, model_path: str):
        """
        Initialise l'introspecteur.

        Args:
            model_path: Chemin du modèle (ex: 'core.Client')
        """
        self.model_path = model_path
        self.model_class = self._get_model_class()

    def _get_model_class(self) -> Type[models.Model]:
        """Récupère la classe du modèle."""
        if self.model_path not in ALLOWED_MODELS:
            raise ValueError(f"Modèle non autorisé: {self.model_path}")

        try:
            app_label, model_name = self.model_path.split('.')
            return apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as e:
            raise ValueError(f"Modèle introuvable: {self.model_path}") from e

    @classmethod
    def get_allowed_models(cls) -> List[Dict[str, str]]:
        """
        Retourne la liste des modèles autorisés avec leurs métadonnées.
        """
        result = []
        for model_path in sorted(ALLOWED_MODELS):
            try:
                app_label, model_name = model_path.split('.')
                model_class = apps.get_model(app_label, model_name)
                result.append({
                    'path': model_path,
                    'app': app_label,
                    'name': model_name,
                    'verbose_name': str(model_class._meta.verbose_name),
                    'verbose_name_plural': str(model_class._meta.verbose_name_plural),
                })
            except LookupError:
                # Le modèle n'existe pas dans cette installation
                pass
        return result

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

    def get_fields(self) -> List[Dict[str, Any]]:
        """
        Extrait les informations de tous les champs du modèle.
        """
        fields = []
        for field in self.model_class._meta.get_fields():
            # Ignorer les relations inverses
            if field.auto_created and not field.concrete:
                continue

            # Ignorer certains champs système
            if field.name in ('id', 'pk', 'created_at', 'updated_at', 'created_by', 'is_active'):
                continue

            field_info = self._extract_field_info(field)
            if field_info:
                fields.append(field_info)

        return fields

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
            info['related_model'] = f"{related_model._meta.app_label}.{related_model._meta.model_name}"
            info['related_verbose_name'] = str(related_model._meta.verbose_name)

        elif isinstance(field, ManyToManyField):
            related_model = field.related_model
            info['related_model'] = f"{related_model._meta.app_label}.{related_model._meta.model_name}"
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
