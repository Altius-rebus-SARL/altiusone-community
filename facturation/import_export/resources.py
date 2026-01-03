# facturation/import_export/resources.py
"""
Resources d'import/export pour les modèles du module Facturation.
"""

from import_export import resources, fields
from django.utils.translation import gettext_lazy as _

from facturation.models import Prestation, Facture
from core.models import Mandat, Client, User
from core.import_export.base import BaseImportExportResource
from core.import_export.widgets import (
    NaturalKeyForeignKeyWidget,
    MandatAwareForeignKeyWidget,
    DateWidget,
    DecimalWidget,
)
from core.import_export.views import register_resource


@register_resource('facturation', 'prestation')
class PrestationResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Prestations.

    Identifiant naturel: code

    Colonnes du fichier d'import:
    - code (requis, unique)
    - libelle (requis)
    - type_prestation: COMPTABILITE, TVA, SALAIRES, CONSEIL, AUDIT, etc.
    - prix_unitaire_ht
    - taux_horaire
    - unite: heure, jour, forfait
    - soumis_tva: Oui/Non
    - taux_tva_defaut
    """

    class Meta:
        model = Prestation
        import_id_fields = ['code']
        skip_unchanged = True
        report_skipped = True
        fields = [
            'code',
            'libelle',
            'description',
            'type_prestation',
            'prix_unitaire_ht',
            'unite',
            'taux_horaire',
            'soumis_tva',
            'taux_tva_defaut',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by', 'compte_produit')

    @classmethod
    def get_template_data(cls):
        data = super().get_template_data()
        data['descriptions'].update({
            'code': _('Code unique de la prestation'),
            'type_prestation': _('Type: COMPTABILITE, TVA, SALAIRES, CONSEIL, AUDIT, FISCALITE'),
            'unite': _('Unité de facturation: heure, jour, forfait'),
            'soumis_tva': _('Soumis à TVA? Oui/Non'),
        })
        data['example_row'] = {
            'code': 'COMPTA-STD',
            'libelle': 'Comptabilité standard',
            'type_prestation': 'COMPTABILITE',
            'taux_horaire': '150.00',
            'unite': 'heure',
            'soumis_tva': 'Oui',
            'taux_tva_defaut': '8.1',
        }
        return data


@register_resource('facturation', 'facture')
class FactureResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Factures.

    Identifiant naturel: numero_facture

    Colonnes du fichier d'import:
    - numero_facture (requis, unique)
    - reference_mandat (requis)
    - client_ide (requis)
    - type_facture: FACTURE, AVOIR, ACOMPTE
    - date_emission (requis)
    - date_echeance (requis)
    - montant_ht
    - montant_tva
    - montant_ttc
    - statut: BROUILLON, EMISE, PAYEE, etc.
    """

    mandat = fields.Field(
        column_name='reference_mandat',
        attribute='mandat',
        widget=MandatAwareForeignKeyWidget(Mandat, field='numero'),
    )

    client = fields.Field(
        column_name='client_ide',
        attribute='client',
        widget=NaturalKeyForeignKeyWidget(Client, field='ide_number'),
    )

    class Meta:
        model = Facture
        import_id_fields = ['numero_facture']
        skip_unchanged = True
        report_skipped = True
        mandat_field = 'mandat'
        mandat_column = 'reference_mandat'
        fields = [
            'numero_facture',
            'mandat',
            'client',
            'type_facture',
            'date_emission',
            'date_echeance',
            'date_service_debut',
            'date_service_fin',
            'montant_ht',
            'montant_tva',
            'montant_ttc',
            'statut',
            'reference_client',
            'notes',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by',
                   'creee_par', 'validee_par', 'ecriture_comptable',
                   'facture_origine', 'date_paiement')

    @classmethod
    def get_template_data(cls):
        data = super().get_template_data()
        data['descriptions'].update({
            'numero_facture': _('Numéro unique de facture'),
            'reference_mandat': _('Référence du mandat'),
            'client_ide': _('Numéro IDE du client (CHE-XXX.XXX.XXX)'),
            'type_facture': _('Type: FACTURE, AVOIR, ACOMPTE'),
            'statut': _('Statut: BROUILLON, EMISE, ENVOYEE, PAYEE, ANNULEE'),
        })
        data['example_row'] = {
            'numero_facture': 'FA-2024-0001',
            'reference_mandat': 'M-2024-001',
            'client_ide': 'CHE-123.456.789',
            'type_facture': 'FACTURE',
            'date_emission': '15.01.2024',
            'date_echeance': '14.02.2024',
            'montant_ht': '1000.00',
            'montant_tva': '81.00',
            'montant_ttc': '1081.00',
            'statut': 'BROUILLON',
        }
        return data
