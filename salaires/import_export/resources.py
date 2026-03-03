# salaires/import_export/resources.py
"""
Resources d'import/export pour les modèles du module Salaires.
"""

from import_export import resources, fields
from django.utils.translation import gettext_lazy as _

from salaires.models import Employe
from core.models import Mandat
from core.import_export.base import BaseImportExportResource
from core.import_export.widgets import (
    MandatAwareForeignKeyWidget,
    DateWidget,
    DecimalWidget,
)
from core.import_export.views import register_resource


@register_resource('salaires', 'employe')
class EmployeResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Employés.

    Identifiant naturel: avs_number

    Colonnes du fichier d'import:
    - reference_mandat (requis)
    - avs_number (requis, unique): Format 756.1234.5678.90
    - matricule
    - nom (requis)
    - prenom (requis)
    - date_naissance (requis)
    - sexe: M, F, X
    - nationalite: Code pays (CH, FR, DE, IT, etc.)
    - email
    - telephone
    - iban
    - date_entree (requis)
    - type_contrat: CDI, CDD, APPRENTI, STAGE, TEMPORAIRE
    - taux_activite
    - salaire_mensuel
    - statut: ACTIF, SUSPENDU, CONGE, DEMISSION, LICENCIE, RETRAITE
    """

    mandat = fields.Field(
        column_name='reference_mandat',
        attribute='mandat',
        widget=MandatAwareForeignKeyWidget(Mandat, field='numero'),
    )

    class Meta:
        model = Employe
        import_id_fields = ['avs_number']
        skip_unchanged = True
        report_skipped = True
        mandat_field = 'mandat'
        mandat_column = 'reference_mandat'
        fields = [
            'mandat',
            'matricule',
            'nom',
            'prenom',
            'nom_naissance',
            'date_naissance',
            'lieu_naissance',
            'nationalite',
            'sexe',
            'avs_number',
            'numero_permis',
            'type_permis',
            'email',
            'telephone',
            'iban',
            'date_entree',
            'date_sortie',
            'type_contrat',
            'fonction',
            'taux_activite',
            'salaire_mensuel',
            'salaire_horaire',
            'statut',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by', 'adresse')

    def before_import_row(self, row, row_number, **kwargs):
        """Valide et normalise les données."""
        # Normaliser le numéro AVS
        avs = row.get('avs_number', '')
        if avs:
            avs = avs.strip()
            # Accepter format sans points
            digits = ''.join(c for c in avs if c.isdigit())
            if len(digits) == 13:
                avs = f"{digits[:3]}.{digits[3:7]}.{digits[7:11]}.{digits[11:13]}"
            row['avs_number'] = avs

        # Nationalité par défaut
        if not row.get('nationalite'):
            row['nationalite'] = 'CH'

        return super().before_import_row(row, row_number, **kwargs)

    @classmethod
    def get_template_data(cls):
        data = super().get_template_data()
        data['descriptions'].update({
            'reference_mandat': _('Référence du mandat'),
            'avs_number': _('Numéro AVS au format 756.1234.5678.90'),
            'matricule': _('Numéro matricule interne'),
            'sexe': _('Sexe: M, F, X'),
            'nationalite': _('Code pays: CH, FR, DE, IT, etc.'),
            'type_contrat': _('Type: CDI, CDD, APPRENTI, STAGE, TEMPORAIRE'),
            'taux_activite': _('Taux d\'activité en % (ex: 100, 80, 50)'),
            'statut': _('Statut: ACTIF, SUSPENDU, CONGE, DEMISSION, LICENCIE, RETRAITE'),
        })
        data['example_row'] = {
            'reference_mandat': 'M-2024-001',
            'matricule': 'EMP001',
            'nom': 'Dupont',
            'prenom': 'Jean',
            'date_naissance': '15.06.1985',
            'sexe': 'M',
            'nationalite': 'CH',
            'avs_number': '756.1234.5678.90',
            'email': 'jean.dupont@exemple.ch',
            'date_entree': '01.01.2024',
            'type_contrat': 'CDI',
            'taux_activite': '100',
            'salaire_mensuel': '6500.00',
            'statut': 'ACTIF',
        }
        return data
