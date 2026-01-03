# core/import_export/resources.py
"""
Resources d'import/export pour les modèles du module core.

Ces Resources définissent comment importer/exporter:
- Client
- Contact
- Mandat
"""

from import_export import resources, fields
from django.utils.translation import gettext_lazy as _

from core.models import Client, Contact, Mandat, User, Adresse
from .base import BaseImportExportResource
from .widgets import (
    NaturalKeyForeignKeyWidget,
    MandatAwareForeignKeyWidget,
    DateWidget,
    DecimalWidget,
    BooleanWidget,
)
from .views import register_resource


# Registre global des Resources
RESOURCE_REGISTRY = {}


@register_resource('core', 'client')
class ClientResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Clients.

    Identifiant naturel: ide_number (CHE-XXX.XXX.XXX)

    Colonnes du fichier d'import:
    - raison_sociale (requis)
    - ide_number (requis, unique)
    - forme_juridique (requis): EI, SARL, SA, etc.
    - email (requis)
    - telephone (requis)
    - statut: PROSPECT, ACTIF, SUSPENDU, RESILIE, ARCHIVE
    - responsable: email du responsable
    - description, nom_commercial, tva_number, rc_number, site_web, notes

    Note: Les adresses sont créées séparément et liées par la suite.
    """

    # FK vers User par email
    responsable = fields.Field(
        column_name='responsable_email',
        attribute='responsable',
        widget=NaturalKeyForeignKeyWidget(User, field='email'),
    )

    class Meta:
        model = Client
        import_id_fields = ['ide_number']
        skip_unchanged = True
        report_skipped = True
        fields = [
            'raison_sociale',
            'nom_commercial',
            'forme_juridique',
            'ide_number',
            'tva_number',
            'rc_number',
            'email',
            'telephone',
            'site_web',
            'date_creation',
            'date_debut_exercice',
            'date_fin_exercice',
            'statut',
            'responsable',
            'description',
            'notes',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by',
                   'adresse_siege', 'adresse_correspondance', 'contact_principal')

    def before_import_row(self, row, row_number, **kwargs):
        """Valide les données avant import."""
        # Normaliser l'IDE number
        ide = row.get('ide_number', '')
        if ide:
            ide = ide.strip().upper()
            # Accepter format sans tirets
            if ide.startswith('CHE') and '-' not in ide:
                # Reformater: CHE123456789 -> CHE-123.456.789
                digits = ''.join(c for c in ide if c.isdigit())
                if len(digits) == 9:
                    ide = f"CHE-{digits[:3]}.{digits[3:6]}.{digits[6:9]}"
            row['ide_number'] = ide

        return super().before_import_row(row, row_number, **kwargs)

    @classmethod
    def get_template_data(cls):
        """Retourne les données pour le template."""
        data = super().get_template_data()

        # Descriptions enrichies
        data['descriptions'].update({
            'raison_sociale': _('Nom officiel de l\'entreprise'),
            'ide_number': _('Numéro IDE au format CHE-XXX.XXX.XXX'),
            'forme_juridique': _('Forme juridique: EI, SARL, SA, ASSOC, FOND, etc.'),
            'statut': _('Statut: PROSPECT, ACTIF, SUSPENDU, RESILIE, ARCHIVE'),
            'responsable_email': _('Email du responsable dans AltiusOne'),
            'date_creation': _('Date de création de l\'entreprise (JJ.MM.AAAA)'),
            'date_debut_exercice': _('Début de l\'exercice comptable (JJ.MM.AAAA)'),
            'date_fin_exercice': _('Fin de l\'exercice comptable (JJ.MM.AAAA)'),
        })

        # Exemple
        data['example_row'] = {
            'raison_sociale': 'Exemple SA',
            'nom_commercial': 'Exemple',
            'forme_juridique': 'SA',
            'ide_number': 'CHE-123.456.789',
            'tva_number': 'CHE-123.456.789 TVA',
            'email': 'info@exemple.ch',
            'telephone': '+41 21 123 45 67',
            'date_creation': '01.01.2020',
            'date_debut_exercice': '01.01.2024',
            'date_fin_exercice': '31.12.2024',
            'statut': 'ACTIF',
            'responsable_email': 'responsable@altiusone.ch',
        }

        return data


@register_resource('core', 'contact')
class ContactResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Contacts.

    Identifiant naturel: email + client

    Colonnes du fichier d'import:
    - client_ide (requis): IDE du client (CHE-XXX.XXX.XXX)
    - email (requis)
    - nom (requis)
    - prenom (requis)
    - civilite: M, MME, DR, PROF
    - fonction: DIRECTEUR, GERANT, ADMIN, COMPTABLE, RH, AUTRE
    - telephone, mobile
    - principal: Oui/Non
    """

    # FK vers Client par IDE
    client = fields.Field(
        column_name='client_ide',
        attribute='client',
        widget=NaturalKeyForeignKeyWidget(Client, field='ide_number'),
    )

    class Meta:
        model = Contact
        import_id_fields = ['email', 'client']
        skip_unchanged = True
        report_skipped = True
        fields = [
            'client',
            'civilite',
            'nom',
            'prenom',
            'fonction',
            'email',
            'telephone',
            'mobile',
            'principal',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by')

    @classmethod
    def get_template_data(cls):
        """Retourne les données pour le template."""
        data = super().get_template_data()

        data['descriptions'].update({
            'client_ide': _('Numéro IDE du client (CHE-XXX.XXX.XXX)'),
            'civilite': _('Civilité: M, MME, DR, PROF'),
            'fonction': _('Fonction: DIRECTEUR, GERANT, ADMIN, COMPTABLE, RH, AUTRE'),
            'principal': _('Contact principal? Oui/Non'),
        })

        data['example_row'] = {
            'client_ide': 'CHE-123.456.789',
            'civilite': 'M',
            'nom': 'Dupont',
            'prenom': 'Jean',
            'fonction': 'DIRECTEUR',
            'email': 'jean.dupont@exemple.ch',
            'telephone': '+41 21 123 45 67',
            'mobile': '+41 79 123 45 67',
            'principal': 'Oui',
        }

        return data


@register_resource('core', 'mandat')
class MandatResource(BaseImportExportResource):
    """
    Resource pour l'import/export des Mandats.

    Identifiant naturel: numero

    Colonnes du fichier d'import:
    - numero (requis, unique)
    - client_ide (requis): IDE du client
    - type_mandat (requis): COMPTA, TVA, SALAIRES, FISCAL, REVISION, CONSEIL, CREATION, GLOBAL
    - date_debut (requis)
    - periodicite (requis): MENSUEL, TRIMESTRIEL, SEMESTRIEL, ANNUEL, PONCTUEL
    - responsable_email (requis): email du responsable
    - statut: BROUILLON, EN_ATTENTE, ACTIF, SUSPENDU, TERMINE, RESILIE
    - type_facturation: FORFAIT, HORAIRE, MIXTE
    - montant_forfait, taux_horaire
    """

    # FK vers Client par IDE
    client = fields.Field(
        column_name='client_ide',
        attribute='client',
        widget=NaturalKeyForeignKeyWidget(Client, field='ide_number'),
    )

    # FK vers User par email
    responsable = fields.Field(
        column_name='responsable_email',
        attribute='responsable',
        widget=NaturalKeyForeignKeyWidget(User, field='email'),
    )

    class Meta:
        model = Mandat
        import_id_fields = ['numero']
        skip_unchanged = True
        report_skipped = True
        fields = [
            'numero',
            'client',
            'type_mandat',
            'date_debut',
            'date_fin',
            'periodicite',
            'type_facturation',
            'montant_forfait',
            'taux_horaire',
            'responsable',
            'statut',
        ]
        exclude = ('id', 'created_at', 'updated_at', 'created_by', 'equipe', 'configuration')

    @classmethod
    def get_template_data(cls):
        """Retourne les données pour le template."""
        data = super().get_template_data()

        data['descriptions'].update({
            'numero': _('Numéro unique du mandat (ex: M-2024-001)'),
            'client_ide': _('Numéro IDE du client (CHE-XXX.XXX.XXX)'),
            'type_mandat': _('Type: COMPTA, TVA, SALAIRES, FISCAL, REVISION, CONSEIL, CREATION, GLOBAL'),
            'periodicite': _('Périodicité: MENSUEL, TRIMESTRIEL, SEMESTRIEL, ANNUEL, PONCTUEL'),
            'type_facturation': _('Type de facturation: FORFAIT, HORAIRE, MIXTE'),
            'statut': _('Statut: BROUILLON, EN_ATTENTE, ACTIF, SUSPENDU, TERMINE, RESILIE'),
            'responsable_email': _('Email du responsable dans AltiusOne'),
        })

        data['example_row'] = {
            'numero': 'M-2024-001',
            'client_ide': 'CHE-123.456.789',
            'type_mandat': 'COMPTA',
            'date_debut': '01.01.2024',
            'date_fin': '31.12.2024',
            'periodicite': 'MENSUEL',
            'type_facturation': 'HORAIRE',
            'taux_horaire': '150.00',
            'responsable_email': 'responsable@altiusone.ch',
            'statut': 'ACTIF',
        }

        return data
