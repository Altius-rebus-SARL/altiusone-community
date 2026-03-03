# graph/management/commands/init_ontologie.py
"""
Charge les types d'ontologie par défaut.

Usage:
    python manage.py init_ontologie
    python manage.py init_ontologie --force
"""
from django.core.management.base import BaseCommand
from django.db import transaction


ENTITY_TYPES = [
    {
        'nom': 'Personne',
        'nom_pluriel': 'Personnes',
        'description': 'Personne physique',
        'icone': 'ph-user',
        'couleur': '#6366f1',
        'ordre_affichage': 1,
        'schema_attributs': {
            'prenom': {'type': 'text', 'label': 'Prénom'},
            'date_naissance': {'type': 'date', 'label': 'Date de naissance'},
            'nationalite': {'type': 'text', 'label': 'Nationalité'},
            'telephone': {'type': 'text', 'label': 'Téléphone'},
            'email': {'type': 'text', 'label': 'Email'},
        },
    },
    {
        'nom': 'Entreprise',
        'nom_pluriel': 'Entreprises',
        'description': 'Personne morale / société',
        'icone': 'ph-building',
        'couleur': '#10b981',
        'ordre_affichage': 2,
        'schema_attributs': {
            'ide': {'type': 'text', 'label': 'IDE (CHE-xxx.xxx.xxx)'},
            'forme_juridique': {
                'type': 'select', 'label': 'Forme juridique',
                'choices': ['SA', 'Sàrl', 'RI', 'SNC', 'SC', 'Fondation', 'Association'],
            },
            'siege': {'type': 'text', 'label': 'Siège'},
            'secteur': {'type': 'text', 'label': 'Secteur d\'activité'},
        },
    },
    {
        'nom': 'Terrain',
        'nom_pluriel': 'Terrains',
        'description': 'Bien immobilier / parcelle',
        'icone': 'ph-map-trifold',
        'couleur': '#f59e0b',
        'ordre_affichage': 3,
        'schema_attributs': {
            'commune': {'type': 'text', 'label': 'Commune'},
            'numero_parcelle': {'type': 'text', 'label': 'N° de parcelle'},
            'surface_m2': {'type': 'number', 'label': 'Surface (m²)', 'min': 0},
            'zone': {'type': 'text', 'label': 'Zone d\'affectation'},
        },
    },
    {
        'nom': 'Compte bancaire',
        'nom_pluriel': 'Comptes bancaires',
        'description': 'Compte bancaire ou financier',
        'icone': 'ph-bank',
        'couleur': '#3b82f6',
        'ordre_affichage': 4,
        'schema_attributs': {
            'iban': {'type': 'text', 'label': 'IBAN'},
            'banque': {'type': 'text', 'label': 'Banque'},
            'devise': {'type': 'text', 'label': 'Devise'},
        },
    },
    {
        'nom': 'Document',
        'nom_pluriel': 'Documents',
        'description': 'Document importé',
        'icone': 'ph-file-text',
        'couleur': '#8b5cf6',
        'ordre_affichage': 5,
        'schema_attributs': {
            'type_document': {'type': 'text', 'label': 'Type'},
            'date_document': {'type': 'date', 'label': 'Date du document'},
        },
    },
    {
        'nom': 'Adresse',
        'nom_pluriel': 'Adresses',
        'description': 'Adresse physique',
        'icone': 'ph-map-pin',
        'couleur': '#ef4444',
        'ordre_affichage': 6,
        'schema_attributs': {
            'rue': {'type': 'text', 'label': 'Rue'},
            'npa': {'type': 'text', 'label': 'NPA'},
            'localite': {'type': 'text', 'label': 'Localité'},
            'canton': {'type': 'text', 'label': 'Canton'},
            'pays': {'type': 'text', 'label': 'Pays'},
        },
    },
    {
        'nom': 'Mandat',
        'nom_pluriel': 'Mandats',
        'description': 'Mandat de gestion',
        'icone': 'ph-briefcase',
        'couleur': '#8b5cf6',
        'ordre_affichage': 7,
        'schema_attributs': {
            'numero': {'type': 'text', 'label': 'Numéro'},
            'type_mandat': {'type': 'text', 'label': 'Type de mandat'},
            'statut': {'type': 'text', 'label': 'Statut'},
        },
    },
    {
        'nom': 'Facture',
        'nom_pluriel': 'Factures',
        'description': 'Facture émise',
        'icone': 'ph-receipt',
        'couleur': '#f59e0b',
        'ordre_affichage': 8,
        'schema_attributs': {
            'montant_ttc': {'type': 'number', 'label': 'Montant TTC'},
            'statut': {'type': 'text', 'label': 'Statut'},
            'date_emission': {'type': 'date', 'label': 'Date d\'émission'},
        },
    },
    {
        'nom': 'Écriture comptable',
        'nom_pluriel': 'Écritures comptables',
        'description': 'Écriture comptable',
        'icone': 'ph-book-open',
        'couleur': '#6366f1',
        'ordre_affichage': 9,
        'schema_attributs': {
            'numero_piece': {'type': 'text', 'label': 'N° pièce'},
            'statut': {'type': 'text', 'label': 'Statut'},
        },
    },
    {
        'nom': 'Pièce comptable',
        'nom_pluriel': 'Pièces comptables',
        'description': 'Pièce comptable justificative',
        'icone': 'ph-file-text',
        'couleur': '#0ea5e9',
        'ordre_affichage': 10,
        'schema_attributs': {
            'numero_piece': {'type': 'text', 'label': 'N° pièce'},
            'statut': {'type': 'text', 'label': 'Statut'},
        },
    },
    {
        'nom': 'Fiche de salaire',
        'nom_pluriel': 'Fiches de salaire',
        'description': 'Fiche de salaire mensuelle',
        'icone': 'ph-money',
        'couleur': '#10b981',
        'ordre_affichage': 11,
        'schema_attributs': {},
    },
    {
        'nom': 'Projet',
        'nom_pluriel': 'Projets',
        'description': 'Position / projet budgétaire',
        'icone': 'ph-kanban',
        'couleur': '#ec4899',
        'ordre_affichage': 12,
        'schema_attributs': {
            'numero': {'type': 'text', 'label': 'Numéro'},
            'budget_prevu': {'type': 'number', 'label': 'Budget prévu'},
        },
    },
    {
        'nom': 'Conversation',
        'nom_pluriel': 'Conversations',
        'description': 'Conversation de messagerie',
        'icone': 'ph-chat-circle',
        'couleur': '#64748b',
        'ordre_affichage': 13,
        'schema_attributs': {},
    },
]

RELATION_TYPES = [
    {
        'nom': 'Emploi',
        'description': 'Relation d\'emploi',
        'icone': 'ph-briefcase',
        'couleur': '#6366f1',
        'verbe': 'emploie',
        'verbe_inverse': 'est employé par',
        'source_types': ['Entreprise'],
        'cible_types': ['Personne'],
        'ordre_affichage': 1,
    },
    {
        'nom': 'Propriété',
        'description': 'Relation de propriété',
        'icone': 'ph-key',
        'couleur': '#f59e0b',
        'verbe': 'possède',
        'verbe_inverse': 'appartient à',
        'source_types': ['Personne', 'Entreprise'],
        'cible_types': ['Terrain', 'Entreprise'],
        'ordre_affichage': 2,
    },
    {
        'nom': 'Direction',
        'description': 'Membre du conseil / direction',
        'icone': 'ph-crown',
        'couleur': '#10b981',
        'verbe': 'dirige',
        'verbe_inverse': 'est dirigé par',
        'source_types': ['Personne'],
        'cible_types': ['Entreprise'],
        'ordre_affichage': 3,
    },
    {
        'nom': 'Domicile',
        'description': 'Adresse de domicile ou siège',
        'icone': 'ph-house',
        'couleur': '#ef4444',
        'verbe': 'est domicilié à',
        'verbe_inverse': 'est le domicile de',
        'source_types': ['Personne', 'Entreprise'],
        'cible_types': ['Adresse'],
        'ordre_affichage': 4,
    },
    {
        'nom': 'Titulaire de compte',
        'description': 'Titulaire d\'un compte bancaire',
        'icone': 'ph-credit-card',
        'couleur': '#3b82f6',
        'verbe': 'est titulaire de',
        'verbe_inverse': 'appartient à',
        'source_types': ['Personne', 'Entreprise'],
        'cible_types': ['Compte bancaire'],
        'ordre_affichage': 5,
    },
    {
        'nom': 'Transaction',
        'description': 'Transaction financière',
        'icone': 'ph-arrows-left-right',
        'couleur': '#8b5cf6',
        'verbe': 'paie',
        'verbe_inverse': 'reçoit de',
        'source_types': ['Compte bancaire'],
        'cible_types': ['Compte bancaire'],
        'ordre_affichage': 6,
    },
    {
        'nom': 'Lien familial',
        'description': 'Lien de parenté',
        'icone': 'ph-users-three',
        'couleur': '#ec4899',
        'verbe': 'est lié à',
        'verbe_inverse': 'est lié à',
        'bidirectionnel': True,
        'source_types': ['Personne'],
        'cible_types': ['Personne'],
        'ordre_affichage': 7,
    },
    {
        'nom': 'Document lié',
        'description': 'Document associé à une entité',
        'icone': 'ph-paperclip',
        'couleur': '#64748b',
        'verbe': 'concerne',
        'verbe_inverse': 'est concerné par',
        'source_types': ['Document'],
        'cible_types': ['Personne', 'Entreprise', 'Terrain', 'Compte bancaire',
                        'Mandat', 'Facture', 'Fiche de salaire'],
        'ordre_affichage': 8,
    },
    {
        'nom': 'Client de',
        'description': 'Relation client',
        'icone': 'ph-handshake',
        'couleur': '#10b981',
        'verbe': 'est client de',
        'verbe_inverse': 'a pour client',
        'source_types': ['Mandat', 'Facture'],
        'cible_types': ['Entreprise'],
        'ordre_affichage': 9,
    },
    {
        'nom': 'Responsable de',
        'description': 'Responsable d\'un mandat ou projet',
        'icone': 'ph-user-circle',
        'couleur': '#6366f1',
        'verbe': 'est responsable de',
        'verbe_inverse': 'a pour responsable',
        'source_types': ['Mandat', 'Projet'],
        'cible_types': ['Personne'],
        'ordre_affichage': 10,
    },
    {
        'nom': 'Employé de',
        'description': 'Relation d\'emploi via mandat',
        'icone': 'ph-identification-badge',
        'couleur': '#8b5cf6',
        'verbe': 'travaille pour',
        'verbe_inverse': 'emploie',
        'source_types': ['Personne'],
        'cible_types': ['Mandat'],
        'ordre_affichage': 11,
    },
    {
        'nom': 'Facturé à',
        'description': 'Facture liée à un mandat',
        'icone': 'ph-receipt',
        'couleur': '#f59e0b',
        'verbe': 'est facturé à',
        'verbe_inverse': 'a reçu facture',
        'source_types': ['Facture'],
        'cible_types': ['Mandat'],
        'ordre_affichage': 12,
    },
    {
        'nom': 'Document de',
        'description': 'Document rattaché à un mandat',
        'icone': 'ph-file-arrow-up',
        'couleur': '#0ea5e9',
        'verbe': 'est document de',
        'verbe_inverse': 'a pour document',
        'source_types': ['Document'],
        'cible_types': ['Mandat'],
        'ordre_affichage': 13,
    },
    {
        'nom': 'Écriture de',
        'description': 'Pièce comptable liée à un mandat',
        'icone': 'ph-book-open',
        'couleur': '#6366f1',
        'verbe': 'est écriture de',
        'verbe_inverse': 'contient écriture',
        'source_types': ['Pièce comptable'],
        'cible_types': ['Mandat'],
        'ordre_affichage': 14,
    },
    {
        'nom': 'Salaire de',
        'description': 'Fiche de salaire liée',
        'icone': 'ph-money',
        'couleur': '#10b981',
        'verbe': 'est fiche salaire de',
        'verbe_inverse': 'a pour fiche salaire',
        'source_types': ['Fiche de salaire'],
        'cible_types': ['Personne'],
        'ordre_affichage': 15,
    },
    {
        'nom': 'Position de',
        'description': 'Position budgétaire liée à un mandat',
        'icone': 'ph-kanban',
        'couleur': '#ec4899',
        'verbe': 'est position de',
        'verbe_inverse': 'contient position',
        'source_types': ['Projet'],
        'cible_types': ['Mandat'],
        'ordre_affichage': 16,
    },
]


class Command(BaseCommand):
    help = 'Charge les types d\'ontologie par défaut pour le graphe relationnel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la recréation même si les types existent déjà',
        )

    def handle(self, *args, **options):
        from graph.models import OntologieType

        force = options['force']
        self.stdout.write(self.style.WARNING('Chargement des types d\'ontologie...'))

        with transaction.atomic():
            entity_map = {}

            # Create entity types
            for data in ENTITY_TYPES:
                obj, created = OntologieType.objects.update_or_create(
                    nom=data['nom'],
                    categorie='entity',
                    defaults={
                        'nom_pluriel': data.get('nom_pluriel', ''),
                        'description': data.get('description', ''),
                        'icone': data.get('icone', 'ph-circle'),
                        'couleur': data.get('couleur', '#6366f1'),
                        'schema_attributs': data.get('schema_attributs', {}),
                        'ordre_affichage': data.get('ordre_affichage', 0),
                        'is_active': True,
                    },
                ) if force else (
                    OntologieType.objects.get_or_create(
                        nom=data['nom'],
                        categorie='entity',
                        defaults={
                            'nom_pluriel': data.get('nom_pluriel', ''),
                            'description': data.get('description', ''),
                            'icone': data.get('icone', 'ph-circle'),
                            'couleur': data.get('couleur', '#6366f1'),
                            'schema_attributs': data.get('schema_attributs', {}),
                            'ordre_affichage': data.get('ordre_affichage', 0),
                        },
                    )
                )
                entity_map[data['nom']] = obj
                status = 'MAJ' if not created and force else ('CREE' if created else 'EXISTE')
                self.stdout.write(f'  [{status}] Entité: {data["nom"]}')

            # Create relation types
            for data in RELATION_TYPES:
                defaults = {
                    'description': data.get('description', ''),
                    'icone': data.get('icone', 'ph-arrows-left-right'),
                    'couleur': data.get('couleur', '#6366f1'),
                    'verbe': data.get('verbe', ''),
                    'verbe_inverse': data.get('verbe_inverse', ''),
                    'bidirectionnel': data.get('bidirectionnel', False),
                    'ordre_affichage': data.get('ordre_affichage', 0),
                    'is_active': True,
                }

                if force:
                    obj, created = OntologieType.objects.update_or_create(
                        nom=data['nom'], categorie='relation', defaults=defaults,
                    )
                else:
                    obj, created = OntologieType.objects.get_or_create(
                        nom=data['nom'], categorie='relation', defaults=defaults,
                    )

                # Set M2M for source/cible types
                source_types = [
                    entity_map[n] for n in data.get('source_types', []) if n in entity_map
                ]
                cible_types = [
                    entity_map[n] for n in data.get('cible_types', []) if n in entity_map
                ]
                if source_types:
                    obj.source_types_autorises.set(source_types)
                if cible_types:
                    obj.cible_types_autorises.set(cible_types)

                status = 'MAJ' if not created and force else ('CREE' if created else 'EXISTE')
                self.stdout.write(f'  [{status}] Relation: {data["nom"]}')

        self.stdout.write(self.style.SUCCESS(
            f'Types d\'ontologie chargés: {len(ENTITY_TYPES)} entités, {len(RELATION_TYPES)} relations'
        ))
