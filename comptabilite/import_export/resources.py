# comptabilite/import_export/resources.py
"""
Resources d'import/export pour les modèles du module Comptabilité.

Ces Resources définissent comment importer/exporter:
- Compte
- EcritureComptable
- Journal
"""

from import_export import resources, fields
from django.utils.translation import gettext_lazy as _

from comptabilite.models import Compte, EcritureComptable, Journal, PlanComptable, ExerciceComptable
from core.models import Mandat, User
from core.import_export.base import BaseImportExportResource
from core.import_export.widgets import (
    NaturalKeyForeignKeyWidget,
    MandatAwareForeignKeyWidget,
    DateWidget,
    DecimalWidget,
    BooleanWidget,
)
from core.import_export.views import register_resource


@register_resource('comptabilite', 'compte')
class CompteResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Comptes.

    Identifiant naturel: numero + plan_comptable

    Colonnes du fichier d'import:
    - plan_comptable_nom (requis): Nom du plan comptable
    - numero (requis): Numéro du compte (ex: 1000, 6000)
    - libelle (requis)
    - type_compte (requis): ACTIF, PASSIF, CHARGE, PRODUIT
    - classe (requis): 1 à 9
    - compte_parent_numero: Numéro du compte parent
    - imputable: Oui/Non (peut recevoir des écritures)
    - soumis_tva: Oui/Non
    """

    # FK vers PlanComptable par nom
    plan_comptable = fields.Field(
        column_name='plan_comptable_nom',
        attribute='plan_comptable',
        widget=NaturalKeyForeignKeyWidget(PlanComptable, field='nom'),
    )

    # FK vers Compte parent par numéro (optionnel)
    compte_parent = fields.Field(
        column_name='compte_parent_numero',
        attribute='compte_parent',
        widget=NaturalKeyForeignKeyWidget(Compte, field='numero'),
    )

    class Meta:
        model = Compte
        import_id_fields = ['numero', 'plan_comptable']
        skip_unchanged = True
        report_skipped = True
        fields = [
            'plan_comptable',
            'numero',
            'libelle',
            'libelle_court',
            'type_compte',
            'classe',
            'niveau',
            'compte_parent',
            'est_collectif',
            'imputable',
            'lettrable',
            'soumis_tva',
            'code_tva_defaut',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by',
                   'solde_debit', 'solde_credit', 'obligatoire_tiers')

    @classmethod
    def get_template_data(cls):
        """Retourne les données pour le template."""
        data = super().get_template_data()

        data['descriptions'].update({
            'plan_comptable_nom': _('Nom du plan comptable'),
            'numero': _('Numéro du compte (ex: 1000, 1100, 6000)'),
            'libelle': _('Libellé complet du compte'),
            'type_compte': _('Type: ACTIF, PASSIF, CHARGE, PRODUIT'),
            'classe': _('Classe comptable: 1 à 9'),
            'compte_parent_numero': _('Numéro du compte parent (optionnel)'),
            'imputable': _('Peut recevoir des écritures? Oui/Non'),
            'soumis_tva': _('Soumis à TVA? Oui/Non'),
        })

        data['example_row'] = {
            'plan_comptable_nom': 'Plan PME 2023',
            'numero': '1000',
            'libelle': 'Caisse',
            'libelle_court': 'Caisse',
            'type_compte': 'ACTIF',
            'classe': '1',
            'niveau': '1',
            'imputable': 'Oui',
            'soumis_tva': 'Non',
        }

        return data


@register_resource('comptabilite', 'journal')
class JournalResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Journaux.

    Identifiant naturel: code + mandat

    Colonnes du fichier d'import:
    - reference_mandat (requis): Référence du mandat
    - code (requis): Code du journal (ex: ACH, VTE, BQ1)
    - nom (requis): Nom du journal
    - type_journal (requis): ACHAT, VENTE, BANQUE, CAISSE, OD, SALAIRE, TVA
    """

    # FK vers Mandat par référence
    mandat = fields.Field(
        column_name='reference_mandat',
        attribute='mandat',
        widget=MandatAwareForeignKeyWidget(Mandat, field='numero'),
    )

    class Meta:
        model = Journal
        import_id_fields = ['code', 'mandat']
        skip_unchanged = True
        report_skipped = True
        mandat_field = 'mandat'
        mandat_column = 'reference_mandat'
        fields = [
            'mandat',
            'code',
            'nom',
            'type_journal',
            'description',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by', 'compte_contrepartie_defaut')

    @classmethod
    def get_template_data(cls):
        """Retourne les données pour le template."""
        data = super().get_template_data()

        data['descriptions'].update({
            'reference_mandat': _('Référence du mandat'),
            'code': _('Code du journal (ex: ACH, VTE, BQ1)'),
            'nom': _('Nom complet du journal'),
            'type_journal': _('Type: ACHAT, VENTE, BANQUE, CAISSE, OD, SALAIRE, TVA'),
        })

        data['example_row'] = {
            'reference_mandat': 'M-2024-001',
            'code': 'ACH',
            'nom': 'Journal des achats',
            'type_journal': 'ACHAT',
        }

        return data


@register_resource('comptabilite', 'ecriturecomptable')
class EcritureComptableResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Écritures Comptables.

    Identifiant naturel: numero_piece + numero_ligne + mandat + date_ecriture

    Colonnes du fichier d'import:
    - reference_mandat (requis): Référence du mandat
    - code_journal (requis): Code du journal
    - numero_compte (requis): Numéro du compte
    - numero_piece (requis): Numéro de pièce
    - numero_ligne: Numéro de ligne (défaut: 1)
    - date_ecriture (requis): Date de l'écriture (JJ.MM.AAAA)
    - libelle (requis): Libellé de l'écriture
    - montant_debit: Montant au débit
    - montant_credit: Montant au crédit
    - code_tva: Code TVA (optionnel)

    Note: Une écriture équilibrée nécessite plusieurs lignes avec
    le même numero_piece et des montants débit/crédit équilibrés.
    """

    # FK vers Mandat par référence
    mandat = fields.Field(
        column_name='reference_mandat',
        attribute='mandat',
        widget=MandatAwareForeignKeyWidget(Mandat, field='numero'),
    )

    # FK vers Journal par code
    journal = fields.Field(
        column_name='code_journal',
        attribute='journal',
        widget=NaturalKeyForeignKeyWidget(Journal, field='code'),
    )

    # FK vers Compte par numéro
    compte = fields.Field(
        column_name='numero_compte',
        attribute='compte',
        widget=NaturalKeyForeignKeyWidget(Compte, field='numero'),
    )

    # FK vers ExerciceComptable par année
    exercice = fields.Field(
        column_name='annee_exercice',
        attribute='exercice',
        widget=NaturalKeyForeignKeyWidget(ExerciceComptable, field='annee'),
    )

    class Meta:
        model = EcritureComptable
        import_id_fields = ['numero_piece', 'numero_ligne', 'mandat']
        skip_unchanged = True
        report_skipped = True
        mandat_field = 'mandat'
        mandat_column = 'reference_mandat'
        fields = [
            'mandat',
            'exercice',
            'journal',
            'numero_piece',
            'numero_ligne',
            'date_ecriture',
            'date_valeur',
            'compte',
            'libelle',
            'libelle_complement',
            'montant_debit',
            'montant_credit',
            'devise',
            'code_tva',
            'montant_tva',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by',
                   'statut', 'valide_par', 'date_validation',
                   'piece_justificative', 'ecriture_extournee',
                   'code_lettrage', 'date_lettrage', 'compte_auxiliaire',
                   'date_echeance', 'taux_change')

    def before_import_row(self, row, row_number, **kwargs):
        """Valide et prépare les données avant import."""
        # Définir le numéro de ligne par défaut
        if not row.get('numero_ligne'):
            row['numero_ligne'] = 1

        # Définir la devise par défaut
        if not row.get('devise'):
            row['devise'] = 'CHF'

        # Convertir les montants vides en 0
        if not row.get('montant_debit'):
            row['montant_debit'] = '0'
        if not row.get('montant_credit'):
            row['montant_credit'] = '0'

        return super().before_import_row(row, row_number, **kwargs)

    def after_import_row(self, row, row_result, row_number, **kwargs):
        """
        Vérifie l'équilibre des écritures après import.
        Note: Cette vérification est faite à la fin de l'import complet.
        """
        return super().after_import_row(row, row_result, row_number, **kwargs)

    @classmethod
    def get_template_data(cls):
        """Retourne les données pour le template."""
        data = super().get_template_data()

        data['descriptions'].update({
            'reference_mandat': _('Référence du mandat'),
            'annee_exercice': _('Année de l\'exercice comptable (ex: 2024)'),
            'code_journal': _('Code du journal (ex: ACH, VTE)'),
            'numero_compte': _('Numéro du compte (ex: 1000, 6000)'),
            'numero_piece': _('Numéro de pièce (ex: FA-2024-001)'),
            'numero_ligne': _('Numéro de ligne (1, 2, 3...)'),
            'date_ecriture': _('Date de l\'écriture (JJ.MM.AAAA)'),
            'libelle': _('Libellé de l\'écriture'),
            'montant_debit': _('Montant au débit (0.00 si crédit)'),
            'montant_credit': _('Montant au crédit (0.00 si débit)'),
            'code_tva': _('Code TVA (ex: 200, 205, 211)'),
        })

        # Exemple: une écriture équilibrée (2 lignes)
        data['example_row'] = {
            'reference_mandat': 'M-2024-001',
            'annee_exercice': '2024',
            'code_journal': 'ACH',
            'numero_compte': '6000',
            'numero_piece': 'FA-2024-001',
            'numero_ligne': '1',
            'date_ecriture': '15.01.2024',
            'libelle': 'Achat fournitures bureau',
            'montant_debit': '150.00',
            'montant_credit': '0.00',
            'devise': 'CHF',
        }

        return data
