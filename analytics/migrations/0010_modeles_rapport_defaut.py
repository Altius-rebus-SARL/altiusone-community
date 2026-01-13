# analytics/migrations/0010_modeles_rapport_defaut.py
"""
Migration de données pour créer les modèles de rapports par défaut.

Chaque type de rapport a un modèle avec des sections prédéfinies optimales.
"""

from django.db import migrations


def creer_modeles_defaut(apps, schema_editor):
    """Crée les modèles de rapports par défaut pour chaque type."""
    ModeleRapport = apps.get_model('analytics', 'ModeleRapport')

    modeles = [
        # =====================================================================
        # BILAN
        # =====================================================================
        {
            'nom': 'Bilan standard',
            'description': 'Modèle de bilan avec graphiques et tableau détaillé',
            'type_rapport': 'BILAN',
            'sections_defaut': [
                {
                    'type': 'titre',
                    'contenu': '<h1>Bilan au {date_fin}</h1>',
                },
                {
                    'type': 'texte',
                    'contenu': '<p>Bilan comptable de <strong>{mandat_nom}</strong> pour la période du {date_debut} au {date_fin}.</p>',
                },
                {
                    'type': 'kpi',
                    'config': {
                        'indicateurs': ['total_actif', 'total_passif', 'fonds_propres']
                    },
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'BILAN_REPARTITION_ACTIF_PASSIF',
                },
                {
                    'type': 'tableau',
                    'config': {
                        'source': 'bilan_actif',
                        'titre': 'Actifs',
                    },
                },
                {
                    'type': 'tableau',
                    'config': {
                        'source': 'bilan_passif',
                        'titre': 'Passifs',
                    },
                },
            ],
            'ordre': 10,
        },

        # =====================================================================
        # COMPTE DE RÉSULTATS
        # =====================================================================
        {
            'nom': 'Compte de résultats standard',
            'description': 'Modèle de compte de résultats avec analyse des produits et charges',
            'type_rapport': 'COMPTE_RESULTATS',
            'sections_defaut': [
                {
                    'type': 'titre',
                    'contenu': '<h1>Compte de résultats</h1>',
                },
                {
                    'type': 'texte',
                    'contenu': '<p>Compte de résultats de <strong>{mandat_nom}</strong> du {date_debut} au {date_fin}.</p>',
                },
                {
                    'type': 'kpi',
                    'config': {
                        'indicateurs': ['total_produits', 'total_charges', 'resultat_net']
                    },
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'CR_REPARTITION_PRODUITS_CHARGES',
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'CR_TOP_PRODUITS',
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'CR_TOP_CHARGES',
                },
                {
                    'type': 'tableau',
                    'config': {
                        'source': 'compte_resultats',
                        'titre': 'Détail du compte de résultats',
                    },
                },
            ],
            'ordre': 10,
        },

        # =====================================================================
        # BALANCE
        # =====================================================================
        {
            'nom': 'Balance générale',
            'description': 'Balance des comptes avec analyse par classe',
            'type_rapport': 'BALANCE',
            'sections_defaut': [
                {
                    'type': 'titre',
                    'contenu': '<h1>Balance générale</h1>',
                },
                {
                    'type': 'texte',
                    'contenu': '<p>Balance générale de <strong>{mandat_nom}</strong> au {date_fin}.</p>',
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'BALANCE_REPARTITION_CLASSES',
                },
                {
                    'type': 'tableau',
                    'config': {
                        'source': 'balance',
                        'titre': 'Balance des comptes',
                        'colonnes': ['numero', 'libelle', 'debit', 'credit', 'solde'],
                    },
                },
            ],
            'ordre': 10,
        },

        # =====================================================================
        # TRÉSORERIE
        # =====================================================================
        {
            'nom': 'Tableau de trésorerie',
            'description': 'Analyse de la trésorerie avec flux et évolution',
            'type_rapport': 'TRESORERIE',
            'sections_defaut': [
                {
                    'type': 'titre',
                    'contenu': '<h1>Tableau de trésorerie</h1>',
                },
                {
                    'type': 'texte',
                    'contenu': '<p>Analyse de la trésorerie de <strong>{mandat_nom}</strong> du {date_debut} au {date_fin}.</p>',
                },
                {
                    'type': 'kpi',
                    'config': {
                        'indicateurs': ['solde_initial', 'encaissements', 'decaissements', 'solde_final']
                    },
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'TRESORERIE_EVOLUTION',
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'TRESORERIE_ENCAISSEMENTS_DECAISSEMENTS',
                },
                {
                    'type': 'tableau',
                    'config': {
                        'source': 'tresorerie_detail',
                        'titre': 'Détail des mouvements',
                    },
                },
            ],
            'ordre': 10,
        },

        # =====================================================================
        # TVA
        # =====================================================================
        {
            'nom': 'Rapport TVA',
            'description': 'Déclaration TVA avec ventilation',
            'type_rapport': 'TVA',
            'sections_defaut': [
                {
                    'type': 'titre',
                    'contenu': '<h1>Rapport TVA</h1>',
                },
                {
                    'type': 'texte',
                    'contenu': '<p>Rapport TVA de <strong>{mandat_nom}</strong> pour la période du {date_debut} au {date_fin}.</p>',
                },
                {
                    'type': 'kpi',
                    'config': {
                        'indicateurs': ['tva_collectee', 'tva_deductible', 'tva_nette']
                    },
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'TVA_REPARTITION',
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'TVA_EVOLUTION_MENSUELLE',
                },
                {
                    'type': 'tableau',
                    'config': {
                        'source': 'tva_detail',
                        'titre': 'Détail TVA par taux',
                    },
                },
            ],
            'ordre': 10,
        },

        # =====================================================================
        # SALAIRES
        # =====================================================================
        {
            'nom': 'Rapport salaires',
            'description': 'Synthèse des salaires et cotisations',
            'type_rapport': 'SALAIRES',
            'sections_defaut': [
                {
                    'type': 'titre',
                    'contenu': '<h1>Rapport des salaires</h1>',
                },
                {
                    'type': 'texte',
                    'contenu': '<p>Récapitulatif des salaires de <strong>{mandat_nom}</strong> du {date_debut} au {date_fin}.</p>',
                },
                {
                    'type': 'kpi',
                    'config': {
                        'indicateurs': ['masse_salariale_brute', 'cotisations_totales', 'salaires_nets']
                    },
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'SALAIRES_REPARTITION_EMPLOYES',
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'SALAIRES_EVOLUTION_MENSUELLE',
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'SALAIRES_REPARTITION_COTISATIONS',
                },
                {
                    'type': 'tableau',
                    'config': {
                        'source': 'salaires_detail',
                        'titre': 'Détail par employé',
                    },
                },
            ],
            'ordre': 10,
        },

        # =====================================================================
        # ÉVOLUTION CA
        # =====================================================================
        {
            'nom': 'Évolution du chiffre d\'affaires',
            'description': 'Analyse de l\'évolution du CA',
            'type_rapport': 'EVOLUTION_CA',
            'sections_defaut': [
                {
                    'type': 'titre',
                    'contenu': '<h1>Évolution du chiffre d\'affaires</h1>',
                },
                {
                    'type': 'texte',
                    'contenu': '<p>Analyse du chiffre d\'affaires de <strong>{mandat_nom}</strong> du {date_debut} au {date_fin}.</p>',
                },
                {
                    'type': 'kpi',
                    'config': {
                        'indicateurs': ['ca_total', 'ca_moyen_mensuel', 'variation_ca']
                    },
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'CA_EVOLUTION_MENSUELLE',
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'CA_COMPARATIF_N1',
                },
                {
                    'type': 'tableau',
                    'config': {
                        'source': 'ca_mensuel',
                        'titre': 'CA mensuel détaillé',
                    },
                },
            ],
            'ordre': 10,
        },

        # =====================================================================
        # RENTABILITÉ
        # =====================================================================
        {
            'nom': 'Analyse de rentabilité',
            'description': 'Analyse des marges et de la rentabilité',
            'type_rapport': 'RENTABILITE',
            'sections_defaut': [
                {
                    'type': 'titre',
                    'contenu': '<h1>Analyse de rentabilité</h1>',
                },
                {
                    'type': 'texte',
                    'contenu': '<p>Analyse de la rentabilité de <strong>{mandat_nom}</strong> du {date_debut} au {date_fin}.</p>',
                },
                {
                    'type': 'kpi',
                    'config': {
                        'indicateurs': ['marge_brute_pct', 'marge_operationnelle_pct', 'marge_nette_pct']
                    },
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'RENTABILITE_MARGES',
                },
                {
                    'type': 'graphique',
                    'code_graphique': 'CR_EVOLUTION_MENSUELLE',
                },
                {
                    'type': 'tableau',
                    'config': {
                        'source': 'rentabilite_detail',
                        'titre': 'Analyse détaillée',
                    },
                },
            ],
            'ordre': 10,
        },
    ]

    for modele_data in modeles:
        ModeleRapport.objects.create(**modele_data)


def supprimer_modeles_defaut(apps, schema_editor):
    """Supprime les modèles par défaut (sans propriétaire)."""
    ModeleRapport = apps.get_model('analytics', 'ModeleRapport')
    ModeleRapport.objects.filter(proprietaire__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0009_graphiques_predefinis_data'),
    ]

    operations = [
        migrations.RunPython(
            creer_modeles_defaut,
            supprimer_modeles_defaut
        ),
    ]
