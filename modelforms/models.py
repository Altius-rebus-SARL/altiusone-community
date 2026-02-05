# apps/modelforms/models.py
"""
Model-Driven Form Builder Models.

Ce module définit les modèles pour la génération de formulaires dynamiques
basés sur les modèles Django existants (Client, Employe, Document, etc.).
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class FormConfiguration(BaseModel):
    """
    Configuration d'un formulaire lié à un modèle Django.

    Permet de définir:
    - Le modèle cible (ex: core.Client)
    - Les champs inclus et leur personnalisation
    - Les sections et l'ordre d'affichage
    - Les valeurs par défaut et règles de validation
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Brouillon')
        ACTIVE = 'ACTIVE', _('Actif')
        ARCHIVED = 'ARCHIVED', _('Archivé')

    class Category(models.TextChoices):
        CLIENT = 'CLIENT', _('Client/Prospect')
        EMPLOYE = 'EMPLOYE', _('Employé')
        FACTURATION = 'FACTURATION', _('Facturation')
        DOCUMENT = 'DOCUMENT', _('Document')
        WORKFLOW = 'WORKFLOW', _('Workflow')
        AUTRE = 'AUTRE', _('Autre')

    # Identification
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_('Code'),
        help_text=_('Code unique du formulaire (ex: CLIENT_RAPIDE, NOUVEL_EMPLOYE)')
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_('Nom'),
        help_text=_('Nom affiché du formulaire')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description détaillée du formulaire et de son usage')
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.AUTRE,
        db_index=True,
        verbose_name=_('Catégorie')
    )

    # Modèle cible
    target_model = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_('Modèle cible'),
        help_text=_('Chemin du modèle Django (ex: core.Client, salaires.Employe)')
    )

    # Modèles liés (pour les formulaires avec relations)
    related_models = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Modèles liés'),
        help_text=_("""
        Liste des modèles imbriqués à créer avec le formulaire.
        Format: [{"model": "core.Adresse", "field": "adresse_siege", "required": true}]
        """)
    )

    # Configuration du formulaire
    form_schema = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Schéma du formulaire'),
        help_text=_("""
        Configuration des sections et de l'ordre des champs.
        Format: {
            "sections": [
                {"id": "identity", "title": "Identité", "fields": ["nom", "prenom"]},
                {"id": "contact", "title": "Contact", "fields": ["email", "telephone"]}
            ]
        }
        """)
    )

    # Valeurs par défaut
    default_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Valeurs par défaut'),
        help_text=_("""
        Valeurs par défaut pour les champs.
        Supporte les variables: {{today}}, {{current_user}}, {{current_user.id}}
        Format: {"statut": "PROSPECT", "date_creation": "{{today}}"}
        """)
    )

    # Règles de validation
    validation_rules = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Règles de validation'),
        help_text=_("""
        Règles de validation personnalisées.
        Format: [
            {"type": "required_if", "field": "tva_number", "condition": "forme_juridique == 'SA'"},
            {"type": "regex", "field": "ide_number", "pattern": "^CHE-\\d{3}\\.\\d{3}\\.\\d{3}$"}
        ]
        """)
    )

    # Actions post-soumission
    post_actions = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Actions post-soumission'),
        help_text=_("""
        Actions à exécuter après la création réussie.
        Format: [
            {"type": "email", "template": "nouveau_client", "to": "{{responsable.email}}"},
            {"type": "task", "title": "Vérifier le client", "assign_to": "{{current_user}}"}
        ]
        """)
    )

    # Statut et workflow
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name=_('Statut')
    )
    require_validation = models.BooleanField(
        default=False,
        verbose_name=_('Nécessite validation'),
        help_text=_('Si coché, les soumissions doivent être validées avant création')
    )

    # Icône et apparence
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='ph-file-text',
        verbose_name=_('Icône'),
        help_text=_('Classe CSS de l\'icône (Phosphor Icons)')
    )

    class Meta:
        db_table = 'modelforms_configurations'
        verbose_name = _('Configuration de formulaire')
        verbose_name_plural = _('Configurations de formulaires')
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['target_model', 'status']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_target_model_class(self):
        """Retourne la classe du modèle cible."""
        from django.apps import apps
        app_label, model_name = self.target_model.split('.')
        return apps.get_model(app_label, model_name)


class ModelFieldMapping(models.Model):
    """
    Personnalisation d'un champ pour un formulaire spécifique.

    Permet de:
    - Définir le widget à utiliser
    - Personnaliser le label et l'aide
    - Ajouter des validations supplémentaires
    - Configurer la visibilité conditionnelle
    """

    class WidgetType(models.TextChoices):
        TEXT = 'text', _('Texte')
        TEXTAREA = 'textarea', _('Zone de texte')
        EMAIL = 'email', _('Email')
        PHONE = 'phone', _('Téléphone')
        NUMBER = 'number', _('Nombre')
        DECIMAL = 'decimal', _('Décimal')
        CURRENCY = 'currency', _('Montant')
        DATE = 'date', _('Date')
        DATETIME = 'datetime', _('Date et heure')
        TIME = 'time', _('Heure')
        SELECT = 'select', _('Liste déroulante')
        RADIO = 'radio', _('Boutons radio')
        CHECKBOX = 'checkbox', _('Case à cocher')
        AUTOCOMPLETE = 'autocomplete', _('Autocomplete')
        FILE = 'file', _('Fichier')
        IMAGE = 'image', _('Image')
        IBAN = 'iban', _('IBAN')
        AVS = 'avs', _('Numéro AVS')
        IDE = 'ide', _('Numéro IDE')
        COUNTRY = 'country', _('Pays')
        CANTON = 'canton', _('Canton')
        HIDDEN = 'hidden', _('Caché')

    id = models.AutoField(primary_key=True)

    # Relation avec la configuration
    form_config = models.ForeignKey(
        FormConfiguration,
        on_delete=models.CASCADE,
        related_name='field_mappings',
        verbose_name=_('Configuration')
    )

    # Identification du champ
    field_name = models.CharField(
        max_length=100,
        verbose_name=_('Nom du champ'),
        help_text=_('Nom du champ dans le modèle Django')
    )
    model_path = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Chemin du modèle'),
        help_text=_('Pour les champs imbriqués: adresse_siege.rue')
    )

    # Personnalisation de l'affichage
    widget_type = models.CharField(
        max_length=20,
        choices=WidgetType.choices,
        default=WidgetType.TEXT,
        verbose_name=_('Type de widget')
    )
    label = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Label'),
        help_text=_('Label personnalisé (laissez vide pour utiliser le verbose_name)')
    )
    help_text = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Texte d\'aide')
    )
    placeholder = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Placeholder')
    )

    # Validation
    required = models.BooleanField(
        default=None,
        null=True,
        verbose_name=_('Obligatoire'),
        help_text=_('Null = utiliser la valeur du modèle')
    )
    min_value = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Valeur minimum')
    )
    max_value = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Valeur maximum')
    )
    min_length = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Longueur minimum')
    )
    max_length = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Longueur maximum')
    )
    regex_pattern = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Pattern regex'),
        help_text=_('Expression régulière pour validation')
    )

    # Visibilité conditionnelle
    conditions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Conditions'),
        help_text=_("""
        Conditions de visibilité du champ.
        Format: {"visible_if": {"field": "forme_juridique", "operator": "in", "value": ["SA", "SARL"]}}
        """)
    )

    # Ordre et section
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Ordre d\'affichage')
    )
    section = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Section'),
        help_text=_('ID de la section dans form_schema')
    )

    # Options supplémentaires
    options = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Options'),
        help_text=_("""
        Options spécifiques au widget.
        Ex pour autocomplete: {"endpoint": "/api/v1/core/clients/", "display_field": "raison_sociale"}
        """)
    )

    class Meta:
        db_table = 'modelforms_field_mappings'
        verbose_name = _('Mapping de champ')
        verbose_name_plural = _('Mappings de champs')
        ordering = ['form_config', 'order', 'field_name']
        unique_together = [['form_config', 'field_name', 'model_path']]

    def __str__(self):
        if self.model_path:
            return f"{self.form_config.code}: {self.model_path}.{self.field_name}"
        return f"{self.form_config.code}: {self.field_name}"


class FormSubmission(BaseModel):
    """
    Soumission d'un formulaire avec suivi des enregistrements créés.

    Permet de:
    - Stocker les données soumises
    - Suivre le statut de traitement
    - Référencer les enregistrements créés
    - Gérer les workflows de validation
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        PROCESSING = 'PROCESSING', _('En traitement')
        COMPLETED = 'COMPLETED', _('Terminé')
        FAILED = 'FAILED', _('Échoué')
        REJECTED = 'REJECTED', _('Rejeté')

    # Relation avec la configuration
    form_config = models.ForeignKey(
        FormConfiguration,
        on_delete=models.PROTECT,
        related_name='submissions',
        verbose_name=_('Configuration')
    )

    # Données soumises
    submitted_data = models.JSONField(
        verbose_name=_('Données soumises'),
        help_text=_('Données du formulaire au format JSON')
    )

    # Métadonnées de soumission
    submitted_by = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        related_name='form_submissions',
        verbose_name=_('Soumis par')
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de soumission')
    )

    # Statut de traitement
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_('Statut')
    )

    # Enregistrements créés
    created_records = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Enregistrements créés'),
        help_text=_("""
        Liste des enregistrements créés.
        Format: [{"model": "core.Client", "id": "uuid-...", "repr": "Dupont SA"}]
        """)
    )

    # Erreurs éventuelles
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Message d\'erreur')
    )
    error_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Détails de l\'erreur')
    )

    # Validation (pour workflows)
    validated_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='form_validations',
        verbose_name=_('Validé par')
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date de validation')
    )
    validation_notes = models.TextField(
        blank=True,
        verbose_name=_('Notes de validation')
    )

    # Contexte
    mandat = models.ForeignKey(
        'core.Mandat',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='form_submissions',
        verbose_name=_('Mandat'),
        help_text=_('Mandat associé (si applicable)')
    )

    class Meta:
        db_table = 'modelforms_submissions'
        verbose_name = _('Soumission de formulaire')
        verbose_name_plural = _('Soumissions de formulaires')
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['form_config', 'status']),
            models.Index(fields=['submitted_by', 'submitted_at']),
            models.Index(fields=['status', 'submitted_at']),
        ]

    def __str__(self):
        return f"{self.form_config.code} - {self.submitted_by} ({self.submitted_at.strftime('%d/%m/%Y %H:%M')})"


class FormTemplate(models.Model):
    """
    Templates prédéfinis pour les cas d'usage courants.

    Permet de créer rapidement des configurations de formulaires
    à partir de modèles standards.
    """

    class Category(models.TextChoices):
        CLIENT = 'CLIENT', _('Client/Prospect')
        EMPLOYE = 'EMPLOYE', _('Employé')
        FACTURATION = 'FACTURATION', _('Facturation')
        DOCUMENT = 'DOCUMENT', _('Document')
        WORKFLOW = 'WORKFLOW', _('Workflow')

    id = models.AutoField(primary_key=True)

    # Identification
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Code'),
        help_text=_('Code unique du template (ex: CLIENT_RAPIDE)')
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_('Nom')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        verbose_name=_('Catégorie')
    )

    # Configuration complète
    template_config = models.JSONField(
        verbose_name=_('Configuration du template'),
        help_text=_("""
        Configuration complète du formulaire à créer.
        Inclut: target_model, related_models, form_schema, default_values, field_mappings
        """)
    )

    # Apparence
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='ph-file-text',
        verbose_name=_('Icône')
    )

    # Métadonnées
    is_system = models.BooleanField(
        default=False,
        verbose_name=_('Template système'),
        help_text=_('Les templates système ne peuvent pas être supprimés')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Actif')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de création')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Date de modification')
    )

    class Meta:
        db_table = 'modelforms_templates'
        verbose_name = _('Template de formulaire')
        verbose_name_plural = _('Templates de formulaires')
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"
