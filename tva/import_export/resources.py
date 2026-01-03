# tva/import_export/resources.py
"""
Resources d'import/export pour les modèles du module TVA.
"""

from import_export import resources, fields
from django.utils.translation import gettext_lazy as _

from tva.models import OperationTVA, CodeTVA
from core.models import Mandat
from core.import_export.base import BaseImportExportResource
from core.import_export.widgets import (
    NaturalKeyForeignKeyWidget,
    MandatAwareForeignKeyWidget,
    DateWidget,
    DecimalWidget,
)
from core.import_export.views import register_resource


@register_resource('tva', 'operationtva')
class OperationTVAResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Opérations TVA.

    Identifiant naturel: numero_facture + date_operation + mandat

    Colonnes du fichier d'import:
    - reference_mandat (requis)
    - date_operation (requis)
    - type_operation: VENTE, ACHAT, IMPORT, EXPORT, INTRA_COM, AUTRE
    - code_tva_code (requis): Code TVA (200, 205, 211, etc.)
    - montant_ht (requis)
    - taux_tva (requis)
    - montant_tva
    - montant_ttc
    - tiers
    - numero_facture
    - libelle (requis)
    """

    mandat = fields.Field(
        column_name='reference_mandat',
        attribute='mandat',
        widget=MandatAwareForeignKeyWidget(Mandat, field='numero'),
    )

    code_tva = fields.Field(
        column_name='code_tva_code',
        attribute='code_tva',
        widget=NaturalKeyForeignKeyWidget(CodeTVA, field='code'),
    )

    class Meta:
        model = OperationTVA
        import_id_fields = ['numero_facture', 'date_operation', 'mandat']
        skip_unchanged = True
        report_skipped = True
        mandat_field = 'mandat'
        mandat_column = 'reference_mandat'
        fields = [
            'mandat',
            'date_operation',
            'type_operation',
            'montant_ht',
            'code_tva',
            'taux_tva',
            'montant_tva',
            'montant_ttc',
            'tiers',
            'numero_tva_tiers',
            'numero_facture',
            'libelle',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by',
                   'declaration_tva', 'ecriture_comptable',
                   'integre_declaration', 'date_integration')

    def before_import_row(self, row, row_number, **kwargs):
        """Calcule montant_tva et montant_ttc si non fournis."""
        montant_ht = row.get('montant_ht')
        taux_tva = row.get('taux_tva')

        if montant_ht and taux_tva:
            try:
                ht = float(str(montant_ht).replace(',', '.'))
                taux = float(str(taux_tva).replace(',', '.'))

                if not row.get('montant_tva'):
                    row['montant_tva'] = str(round(ht * taux / 100, 2))

                if not row.get('montant_ttc'):
                    montant_tva = float(row.get('montant_tva', 0))
                    row['montant_ttc'] = str(round(ht + montant_tva, 2))
            except (ValueError, TypeError):
                pass

        return super().before_import_row(row, row_number, **kwargs)

    @classmethod
    def get_template_data(cls):
        data = super().get_template_data()
        data['descriptions'].update({
            'reference_mandat': _('Référence du mandat'),
            'date_operation': _('Date de l\'opération (JJ.MM.AAAA)'),
            'type_operation': _('Type: VENTE, ACHAT, IMPORT, EXPORT, INTRA_COM'),
            'code_tva_code': _('Code TVA (200, 205, 211, 220, etc.)'),
            'montant_ht': _('Montant hors taxes'),
            'taux_tva': _('Taux TVA en % (ex: 8.1, 2.6, 0)'),
            'montant_tva': _('Montant TVA (calculé automatiquement si vide)'),
            'montant_ttc': _('Montant TTC (calculé automatiquement si vide)'),
            'tiers': _('Nom du client ou fournisseur'),
        })
        data['example_row'] = {
            'reference_mandat': 'M-2024-001',
            'date_operation': '15.01.2024',
            'type_operation': 'VENTE',
            'code_tva_code': '200',
            'montant_ht': '1000.00',
            'taux_tva': '8.1',
            'montant_tva': '81.00',
            'montant_ttc': '1081.00',
            'tiers': 'Client ABC SA',
            'numero_facture': 'FA-2024-0001',
            'libelle': 'Vente de services',
        }
        return data
