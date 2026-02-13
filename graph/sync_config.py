# graph/sync_config.py
"""
Configuration du mapping entre modèles Django et le graphe relationnel.

Chaque entrée dans MODEL_GRAPH_CONFIG définit comment un modèle Django
se projette en Entite dans le graphe. RELATION_MAPPINGS définit quelles
FK deviennent des Relations.
"""

# Modèle Django → type d'entité dans le graphe
MODEL_GRAPH_CONFIG = {
    'core.Client': {
        'type_nom': 'Entreprise',
        'nom_field': 'raison_sociale',
        'description_field': None,
        'attributs_fields': ['ide_number', 'forme_juridique', 'canton_rc', 'statut'],
        'source': 'systeme',
    },
    'core.User': {
        'type_nom': 'Personne',
        'nom_field': 'get_full_name',  # callable
        'description_field': None,
        'attributs_fields': ['email', 'role__nom'],
        'source': 'systeme',
    },
    'core.Mandat': {
        'type_nom': 'Mandat',
        'nom_field': '__str__',
        'description_field': None,
        'attributs_fields': ['numero', 'type_mandat', 'statut'],
        'source': 'systeme',
    },
    'salaires.Employe': {
        'type_nom': 'Personne',
        'nom_field': '__str__',
        'description_field': None,
        'attributs_fields': ['matricule', 'avs_number', 'statut'],
        'source': 'systeme',
    },
    'facturation.Facture': {
        'type_nom': 'Facture',
        'nom_field': 'numero_facture',
        'description_field': None,
        'attributs_fields': ['montant_ttc', 'statut', 'date_emission'],
        'source': 'systeme',
    },
    'comptabilite.PieceComptable': {
        'type_nom': 'Pièce comptable',
        'nom_field': '__str__',
        'description_field': None,
        'attributs_fields': ['numero_piece', 'statut'],
        'source': 'systeme',
    },
    'documents.Document': {
        'type_nom': 'Document',
        'nom_field': 'nom_fichier',
        'description_field': None,
        'attributs_fields': ['extension', 'taille', 'statut_validation'],
        'source': 'systeme',
    },
    'projets.Position': {
        'type_nom': 'Projet',
        'nom_field': '__str__',
        'description_field': None,
        'attributs_fields': ['numero', 'budget_prevu'],
        'source': 'systeme',
    },
}

# FK fields sur chaque modèle → type de Relation dans le graphe
RELATION_MAPPINGS = {
    'core.Mandat': {
        'client': 'Client de',
        'responsable': 'Responsable de',
    },
    'salaires.Employe': {
        'mandat': 'Employé de',
    },
    'facturation.Facture': {
        'mandat': 'Facturé à',
        'client': 'Client de',
    },
    'comptabilite.PieceComptable': {
        'mandat': 'Écriture de',
    },
    'documents.Document': {
        'mandat': 'Document de',
        'facture': 'Document lié',
        'fiche_salaire': 'Document lié',
    },
    'projets.Position': {
        'mandat': 'Position de',
        'responsable': 'Responsable de',
    },
}
