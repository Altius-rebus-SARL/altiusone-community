# core/import_export/base.py
"""
Classes de base pour les Resources d'import/export.

Ces classes fournissent:
- Validation automatique des accès aux Mandats
- Logging dans AuditLog
- Gestion des identifiants naturels
- Mode dry-run (simulation)
"""

from typing import Any, Dict, List, Optional, Type
from decimal import Decimal
from datetime import datetime

from django.db import transaction
from django.db.models import Model, Q
from django.utils.translation import gettext_lazy as _, get_language
from django.contrib.auth import get_user_model

from import_export import resources, fields
from import_export.results import Result, RowResult

from .widgets import (
    NaturalKeyForeignKeyWidget,
    MandatAwareForeignKeyWidget,
    DateWidget,
    DecimalWidget,
    BooleanWidget,
)

User = get_user_model()


class MandatAwareResource(resources.ModelResource):
    """
    Resource qui valide l'accès au Mandat avant import.

    Vérifie que l'utilisateur a accès aux mandats référencés dans les
    données importées. Empêche les imports non autorisés.

    Usage:
        class EcritureResource(MandatAwareResource):
            class Meta:
                model = EcritureComptable
                mandat_field = 'mandat'  # Nom du champ FK vers Mandat
    """

    class Meta:
        # Nom du champ ForeignKey vers Mandat (à surcharger si nécessaire)
        mandat_field = 'mandat'
        # Nom de la colonne dans le fichier d'import
        mandat_column = 'reference_mandat'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = None
        self.accessible_mandats = None
        self.current_mandat = None  # Mandat du contexte actuel

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        """
        Appelé avant le début de l'import.
        Initialise l'utilisateur et charge ses mandats accessibles.
        """
        self.user = kwargs.get('user')
        self.current_mandat = kwargs.get('mandat')
        self._load_accessible_mandats()

        # Configurer les widgets MandatAware avec l'utilisateur
        self._configure_mandat_widgets()

        super().before_import(dataset, using_transactions, dry_run, **kwargs)

    def _load_accessible_mandats(self):
        """Charge la liste des mandats accessibles par l'utilisateur."""
        from core.models import Mandat

        if self.user is None:
            self.accessible_mandats = Mandat.objects.none()
            return

        if self.user.is_superuser:
            self.accessible_mandats = Mandat.objects.all()
        elif hasattr(self.user, 'is_manager') and self.user.is_manager():
            self.accessible_mandats = Mandat.objects.all()
        else:
            self.accessible_mandats = Mandat.objects.filter(
                Q(responsable=self.user) | Q(equipe=self.user)
            ).distinct()

    def _configure_mandat_widgets(self):
        """Configure les widgets MandatAware avec l'utilisateur."""
        for field_name, field in self.fields.items():
            if isinstance(field.widget, MandatAwareForeignKeyWidget):
                field.widget.set_user(self.user)

    def before_import_row(self, row, row_number, **kwargs):
        """
        Appelé avant l'import de chaque ligne.
        Vérifie l'accès au mandat si spécifié.
        """
        mandat_column = getattr(self._meta, 'mandat_column', 'reference_mandat')
        mandat_ref = row.get(mandat_column)

        if mandat_ref and self.accessible_mandats is not None:
            if not self.accessible_mandats.filter(reference=mandat_ref).exists():
                raise ValueError(
                    _("Ligne {row}: Vous n'avez pas accès au mandat '{mandat}'").format(
                        row=row_number,
                        mandat=mandat_ref
                    )
                )

        return super().before_import_row(row, row_number, **kwargs)

    def get_queryset(self):
        """
        Retourne le queryset filtré par les mandats accessibles.
        Utilisé pour l'export et la validation d'existence.
        """
        queryset = super().get_queryset()

        # Filtrer par mandats accessibles si le modèle a un champ mandat
        mandat_field = getattr(self._meta, 'mandat_field', 'mandat')
        if hasattr(self._meta.model, mandat_field) and self.accessible_mandats is not None:
            queryset = queryset.filter(**{
                f'{mandat_field}__in': self.accessible_mandats
            })

        return queryset


class AuditedResource(resources.ModelResource):
    """
    Resource qui log les imports dans AuditLog.

    Crée une entrée dans AuditLog après chaque import réussi,
    avec le détail des créations/modifications/erreurs.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = None
        self.ip_address = None
        self.user_agent = ''

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        """Capture les informations de l'utilisateur pour l'audit."""
        self.user = kwargs.get('user')
        self.ip_address = kwargs.get('ip_address')
        self.user_agent = kwargs.get('user_agent', '')

        super().before_import(dataset, using_transactions, dry_run, **kwargs)

    def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
        """
        Appelé après l'import.
        Crée une entrée dans AuditLog si l'import n'est pas en dry-run.
        """
        super().after_import(dataset, result, using_transactions, dry_run, **kwargs)

        if dry_run or self.user is None:
            return

        self._create_audit_log(result, kwargs.get('mandat'))

    def _create_audit_log(self, result: Result, mandat=None):
        """Crée l'entrée AuditLog pour l'import."""
        from core.models import AuditLog

        # Compter les résultats
        stats = self._compute_import_stats(result)

        AuditLog.objects.create(
            utilisateur=self.user,
            action='IMPORT',
            table_name=self._meta.model._meta.db_table,
            object_id='bulk_import',
            object_repr=_("Import de {total} lignes dans {model}").format(
                total=result.total_rows,
                model=self._meta.model._meta.verbose_name_plural
            ),
            changements={
                'total_rows': result.total_rows,
                'created': stats['created'],
                'updated': stats['updated'],
                'skipped': stats['skipped'],
                'errors': stats['errors'],
                'error_details': stats['error_details'][:10],  # Max 10 erreurs
            },
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            mandat=mandat,
        )

    def _compute_import_stats(self, result: Result) -> Dict[str, Any]:
        """Calcule les statistiques d'import."""
        created = 0
        updated = 0
        skipped = 0
        errors = 0
        error_details = []

        for row in result.rows:
            if row.import_type == RowResult.IMPORT_TYPE_NEW:
                created += 1
            elif row.import_type == RowResult.IMPORT_TYPE_UPDATE:
                updated += 1
            elif row.import_type == RowResult.IMPORT_TYPE_SKIP:
                skipped += 1

            if row.errors:
                errors += 1
                error_details.append({
                    'row': row.number,
                    'errors': [str(e.error) for e in row.errors]
                })

        return {
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'errors': errors,
            'error_details': error_details,
        }


class BaseImportExportResource(MandatAwareResource, AuditedResource):
    """
    Resource de base combinant validation Mandat et audit.

    C'est la classe de base recommandée pour toutes les Resources
    d'import/export dans l'application.

    Usage:
        class ClientResource(BaseImportExportResource):
            class Meta:
                model = Client
                import_id_fields = ['ide_number']
                fields = ['nom', 'ide_number', 'email', ...]

            # Définir les widgets pour les FK
            responsable = fields.Field(
                column_name='responsable',
                attribute='responsable',
                widget=NaturalKeyForeignKeyWidget(User, 'email')
            )
    """

    class Meta:
        # Utiliser les transactions pour rollback en cas d'erreur
        use_transactions = True
        # Ne pas mettre à jour les champs auto-générés
        skip_unchanged = True
        # Rapport d'erreurs détaillé
        report_skipped = True
        # Exclure les champs auto-générés
        exclude = ('id', 'created_at', 'updated_at', 'created_by')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Configuration des widgets par défaut
        self._setup_default_widgets()

    def _setup_default_widgets(self):
        """Configure les widgets par défaut pour les types de champs courants."""
        for field_name, field in self.fields.items():
            model_field = self._get_model_field(field_name)
            if model_field is None:
                continue

            # Appliquer les widgets par défaut selon le type
            field_type = model_field.__class__.__name__

            if field_type == 'DateField' and not isinstance(field.widget, DateWidget):
                field.widget = DateWidget()
            elif field_type == 'DecimalField' and not isinstance(field.widget, DecimalWidget):
                field.widget = DecimalWidget()
            elif field_type == 'BooleanField' and not isinstance(field.widget, BooleanWidget):
                field.widget = BooleanWidget()

    def _get_model_field(self, field_name: str):
        """Récupère le champ du modèle Django."""
        try:
            return self._meta.model._meta.get_field(field_name)
        except Exception:
            return None

    def get_export_headers(self):
        """
        Retourne les en-têtes d'export traduits.
        Utilise les verbose_name des champs si disponibles.
        """
        headers = []
        for field_name in self.get_export_fields():
            field = self.fields.get(field_name)
            if field and field.column_name:
                # Utiliser le column_name du field
                headers.append(str(field.column_name))
            else:
                # Essayer d'obtenir le verbose_name du modèle
                model_field = self._get_model_field(field_name)
                if model_field and hasattr(model_field, 'verbose_name'):
                    headers.append(str(model_field.verbose_name))
                else:
                    headers.append(field_name)
        return headers

    def get_export_fields(self):
        """Retourne la liste des champs à exporter."""
        return [f for f in self.fields.keys() if f not in self._meta.exclude]

    def before_save_instance(self, instance, using_transactions, dry_run):
        """
        Appelé avant la sauvegarde de chaque instance.
        Définit created_by si c'est une nouvelle instance.
        """
        if not instance.pk and hasattr(instance, 'created_by') and self.user:
            instance.created_by = self.user

        super().before_save_instance(instance, using_transactions, dry_run)

    @classmethod
    def get_template_data(cls) -> Dict[str, Any]:
        """
        Retourne les données pour générer un template vide.

        Returns:
            Dict avec:
            - headers: Liste des en-têtes de colonnes
            - example_row: Ligne d'exemple (optionnel)
            - descriptions: Description de chaque colonne
        """
        resource = cls()
        headers = []
        descriptions = {}
        example_row = {}

        for field_name, field in resource.fields.items():
            if field_name in resource._meta.exclude:
                continue

            column_name = field.column_name or field_name
            headers.append(column_name)

            # Description du champ
            model_field = resource._get_model_field(field_name)
            if model_field:
                desc = str(model_field.verbose_name)
                if model_field.help_text:
                    desc += f" - {model_field.help_text}"
                descriptions[column_name] = desc

                # Exemple de valeur
                example_row[column_name] = cls._get_example_value(model_field)

        return {
            'headers': headers,
            'descriptions': descriptions,
            'example_row': example_row,
        }

    @staticmethod
    def _get_example_value(model_field) -> str:
        """Retourne une valeur d'exemple pour un champ."""
        field_type = model_field.__class__.__name__

        examples = {
            'CharField': 'Exemple',
            'TextField': 'Description longue...',
            'EmailField': 'email@exemple.ch',
            'DateField': '31.12.2024',
            'DecimalField': '1234.56',
            'IntegerField': '42',
            'BooleanField': 'Oui',
            'ForeignKey': 'Référence',
        }

        return examples.get(field_type, '')
