# analytics/migrations/0009_graphiques_predefinis_data.py
"""
Migration de données pour créer les graphiques prédéfinis validés statistiquement.

Chaque graphique est conçu pour montrer des données cohérentes:
- Pas de mélange montants/comptages
- Visualisation appropriée au type de données
- Pertinence métier pour chaque type de rapport
"""

from django.db import migrations


def creer_graphiques_predefinis(apps, schema_editor):
    """Crée les graphiques prédéfinis pour chaque type de rapport."""
    TypeGraphiqueRapport = apps.get_model('analytics', 'TypeGraphiqueRapport')

    graphiques = [
        # =====================================================================
        # BILAN
        # =====================================================================
        {
            'code': 'BILAN_REPARTITION_ACTIF_PASSIF',
            'nom': 'Répartition Actif / Passif',
            'description': 'Comparaison visuelle du total des actifs et passifs',
            'types_rapport_compatibles': ['BILAN'],
            'type_graphique': 'donut',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'bilan',
                'agregation': 'sum',
                'grouper_par': 'type_bilan',
                'labels': ['Actifs', 'Passifs'],
            },
            'options_affichage': {
                'couleurs': ['#4680FF', '#2CA87F'],
                'afficher_legende': True,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 10,
        },
        {
            'code': 'BILAN_STRUCTURE_ACTIFS',
            'nom': 'Structure des actifs',
            'description': 'Répartition des actifs par catégorie (immobilisés, circulants)',
            'types_rapport_compatibles': ['BILAN'],
            'type_graphique': 'horizontal_bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'bilan_detail',
                'agregation': 'sum',
                'filtres': {'type': 'actif'},
                'grouper_par': 'categorie',
            },
            'options_affichage': {
                'couleurs': ['#4680FF', '#5B8DEF', '#7BA3F5', '#9CB9FA'],
                'afficher_legende': False,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 20,
        },
        {
            'code': 'BILAN_STRUCTURE_PASSIFS',
            'nom': 'Structure des passifs',
            'description': 'Répartition des passifs par catégorie (fonds propres, dettes)',
            'types_rapport_compatibles': ['BILAN'],
            'type_graphique': 'horizontal_bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'bilan_detail',
                'agregation': 'sum',
                'filtres': {'type': 'passif'},
                'grouper_par': 'categorie',
            },
            'options_affichage': {
                'couleurs': ['#2CA87F', '#4FBF9A', '#72D5B5', '#95EBD0'],
                'afficher_legende': False,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 30,
        },

        # =====================================================================
        # COMPTE DE RÉSULTATS
        # =====================================================================
        {
            'code': 'CR_REPARTITION_PRODUITS_CHARGES',
            'nom': 'Répartition Produits / Charges',
            'description': 'Vue d\'ensemble produits vs charges',
            'types_rapport_compatibles': ['COMPTE_RESULTATS'],
            'type_graphique': 'donut',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'compte_resultats',
                'agregation': 'sum',
                'grouper_par': 'type_cr',
                'labels': ['Produits', 'Charges'],
            },
            'options_affichage': {
                'couleurs': ['#2CA87F', '#DC2626'],
                'afficher_legende': True,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 10,
        },
        {
            'code': 'CR_TOP_PRODUITS',
            'nom': 'Top 10 postes de produits',
            'description': 'Les 10 principaux postes de revenus',
            'types_rapport_compatibles': ['COMPTE_RESULTATS'],
            'type_graphique': 'horizontal_bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'compte_resultats_detail',
                'agregation': 'sum',
                'filtres': {'type': 'produit'},
                'grouper_par': 'compte',
                'ordre': '-montant',
                'limite': 10,
            },
            'options_affichage': {
                'couleurs': ['#2CA87F'],
                'afficher_legende': False,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 20,
        },
        {
            'code': 'CR_TOP_CHARGES',
            'nom': 'Top 10 postes de charges',
            'description': 'Les 10 principaux postes de dépenses',
            'types_rapport_compatibles': ['COMPTE_RESULTATS'],
            'type_graphique': 'horizontal_bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'compte_resultats_detail',
                'agregation': 'sum',
                'filtres': {'type': 'charge'},
                'grouper_par': 'compte',
                'ordre': '-montant',
                'limite': 10,
            },
            'options_affichage': {
                'couleurs': ['#DC2626'],
                'afficher_legende': False,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 30,
        },
        {
            'code': 'CR_EVOLUTION_MENSUELLE',
            'nom': 'Évolution mensuelle du résultat',
            'description': 'Résultat net par mois sur la période',
            'types_rapport_compatibles': ['COMPTE_RESULTATS', 'RENTABILITE'],
            'type_graphique': 'area',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'compte_resultats',
                'agregation': 'sum_by_month',
                'champ_valeur': 'resultat_net',
            },
            'options_affichage': {
                'couleurs': ['#4680FF'],
                'afficher_legende': False,
                'afficher_valeurs': False,
                'format_valeur': 'currency',
            },
            'ordre': 40,
        },

        # =====================================================================
        # TRÉSORERIE
        # =====================================================================
        {
            'code': 'TRESORERIE_EVOLUTION',
            'nom': 'Évolution de la trésorerie',
            'description': 'Solde de trésorerie au fil du temps',
            'types_rapport_compatibles': ['TRESORERIE'],
            'type_graphique': 'area',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'tresorerie',
                'agregation': 'cumul_by_date',
                'champ_valeur': 'solde',
            },
            'options_affichage': {
                'couleurs': ['#4680FF'],
                'afficher_legende': False,
                'afficher_valeurs': False,
                'format_valeur': 'currency',
            },
            'ordre': 10,
        },
        {
            'code': 'TRESORERIE_ENCAISSEMENTS_DECAISSEMENTS',
            'nom': 'Encaissements vs Décaissements',
            'description': 'Comparaison mensuelle des entrées et sorties',
            'types_rapport_compatibles': ['TRESORERIE'],
            'type_graphique': 'bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'tresorerie',
                'agregation': 'sum_by_month',
                'series': ['encaissements', 'decaissements'],
            },
            'options_affichage': {
                'couleurs': ['#2CA87F', '#DC2626'],
                'afficher_legende': True,
                'afficher_valeurs': False,
                'format_valeur': 'currency',
            },
            'ordre': 20,
        },

        # =====================================================================
        # TVA
        # =====================================================================
        {
            'code': 'TVA_REPARTITION',
            'nom': 'Répartition TVA collectée / déductible',
            'description': 'Comparaison TVA collectée et TVA déductible',
            'types_rapport_compatibles': ['TVA'],
            'type_graphique': 'donut',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'tva',
                'agregation': 'sum',
                'grouper_par': 'type_tva',
                'labels': ['TVA collectée', 'TVA déductible'],
            },
            'options_affichage': {
                'couleurs': ['#4680FF', '#E58A00'],
                'afficher_legende': True,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 10,
        },
        {
            'code': 'TVA_EVOLUTION_MENSUELLE',
            'nom': 'Évolution mensuelle de la TVA',
            'description': 'TVA nette à payer/récupérer par mois',
            'types_rapport_compatibles': ['TVA'],
            'type_graphique': 'bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'tva',
                'agregation': 'sum_by_month',
                'champ_valeur': 'tva_nette',
            },
            'options_affichage': {
                'couleurs': ['#673AB7'],
                'afficher_legende': False,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 20,
        },

        # =====================================================================
        # SALAIRES
        # =====================================================================
        {
            'code': 'SALAIRES_REPARTITION_EMPLOYES',
            'nom': 'Répartition masse salariale',
            'description': 'Masse salariale brute par employé',
            'types_rapport_compatibles': ['SALAIRES'],
            'type_graphique': 'donut',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'salaires',
                'agregation': 'sum',
                'grouper_par': 'employe',
                'champ_valeur': 'salaire_brut',
            },
            'options_affichage': {
                'couleurs': ['#4680FF', '#2CA87F', '#DC2626', '#E58A00', '#673AB7', '#00BCD4'],
                'afficher_legende': True,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 10,
        },
        {
            'code': 'SALAIRES_EVOLUTION_MENSUELLE',
            'nom': 'Évolution mensuelle masse salariale',
            'description': 'Total des salaires bruts par mois',
            'types_rapport_compatibles': ['SALAIRES'],
            'type_graphique': 'bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'salaires',
                'agregation': 'sum_by_month',
                'champ_valeur': 'salaire_brut',
            },
            'options_affichage': {
                'couleurs': ['#4680FF'],
                'afficher_legende': False,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 20,
        },
        {
            'code': 'SALAIRES_REPARTITION_COTISATIONS',
            'nom': 'Répartition des cotisations',
            'description': 'Ventilation des cotisations sociales',
            'types_rapport_compatibles': ['SALAIRES'],
            'type_graphique': 'donut',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'salaires',
                'agregation': 'sum',
                'grouper_par': 'type_cotisation',
            },
            'options_affichage': {
                'couleurs': ['#4680FF', '#2CA87F', '#DC2626', '#E58A00', '#673AB7'],
                'afficher_legende': True,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 30,
        },

        # =====================================================================
        # ÉVOLUTION CA
        # =====================================================================
        {
            'code': 'CA_EVOLUTION_MENSUELLE',
            'nom': 'Évolution mensuelle du CA',
            'description': 'Chiffre d\'affaires mois par mois',
            'types_rapport_compatibles': ['EVOLUTION_CA'],
            'type_graphique': 'area',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'chiffre_affaires',
                'agregation': 'sum_by_month',
            },
            'options_affichage': {
                'couleurs': ['#4680FF'],
                'afficher_legende': False,
                'afficher_valeurs': False,
                'format_valeur': 'currency',
            },
            'ordre': 10,
        },
        {
            'code': 'CA_COMPARATIF_N1',
            'nom': 'Comparatif N vs N-1',
            'description': 'Comparaison du CA avec l\'année précédente',
            'types_rapport_compatibles': ['EVOLUTION_CA'],
            'type_graphique': 'bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'chiffre_affaires',
                'agregation': 'sum_by_month',
                'comparatif': True,
                'series': ['annee_n', 'annee_n1'],
            },
            'options_affichage': {
                'couleurs': ['#4680FF', '#B0C4DE'],
                'afficher_legende': True,
                'afficher_valeurs': False,
                'format_valeur': 'currency',
            },
            'ordre': 20,
        },

        # =====================================================================
        # RENTABILITÉ
        # =====================================================================
        {
            'code': 'RENTABILITE_MARGES',
            'nom': 'Analyse des marges',
            'description': 'Marge brute, marge opérationnelle, marge nette',
            'types_rapport_compatibles': ['RENTABILITE'],
            'type_graphique': 'bar',
            'unite_donnees': 'POURCENTAGE',
            'config_source': {
                'source': 'rentabilite',
                'agregation': 'ratio',
                'indicateurs': ['marge_brute', 'marge_operationnelle', 'marge_nette'],
            },
            'options_affichage': {
                'couleurs': ['#4680FF', '#2CA87F', '#673AB7'],
                'afficher_legende': True,
                'afficher_valeurs': True,
                'format_valeur': 'percent',
            },
            'ordre': 10,
        },
        {
            'code': 'RENTABILITE_EVOLUTION_MARGE',
            'nom': 'Évolution de la marge nette',
            'description': 'Marge nette mensuelle en pourcentage',
            'types_rapport_compatibles': ['RENTABILITE'],
            'type_graphique': 'line',
            'unite_donnees': 'POURCENTAGE',
            'config_source': {
                'source': 'rentabilite',
                'agregation': 'ratio_by_month',
                'indicateur': 'marge_nette',
            },
            'options_affichage': {
                'couleurs': ['#2CA87F'],
                'afficher_legende': False,
                'afficher_valeurs': False,
                'format_valeur': 'percent',
            },
            'ordre': 20,
        },

        # =====================================================================
        # BALANCE
        # =====================================================================
        {
            'code': 'BALANCE_REPARTITION_CLASSES',
            'nom': 'Répartition par classe de comptes',
            'description': 'Soldes totaux par classe comptable',
            'types_rapport_compatibles': ['BALANCE'],
            'type_graphique': 'bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'balance',
                'agregation': 'sum',
                'grouper_par': 'classe',
            },
            'options_affichage': {
                'couleurs': ['#4680FF', '#2CA87F', '#DC2626', '#E58A00', '#673AB7', '#00BCD4', '#8BC34A', '#FF5722', '#795548'],
                'afficher_legende': True,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 10,
        },
        {
            'code': 'BALANCE_TOP_COMPTES_DEBITEURS',
            'nom': 'Top 10 comptes débiteurs',
            'description': 'Les 10 comptes avec les plus gros soldes débiteurs',
            'types_rapport_compatibles': ['BALANCE'],
            'type_graphique': 'horizontal_bar',
            'unite_donnees': 'CHF',
            'config_source': {
                'source': 'balance',
                'agregation': 'top',
                'filtres': {'solde_type': 'debiteur'},
                'limite': 10,
            },
            'options_affichage': {
                'couleurs': ['#4680FF'],
                'afficher_legende': False,
                'afficher_valeurs': True,
                'format_valeur': 'currency',
            },
            'ordre': 20,
        },
    ]

    for graphique_data in graphiques:
        TypeGraphiqueRapport.objects.create(**graphique_data)


def supprimer_graphiques_predefinis(apps, schema_editor):
    """Supprime tous les graphiques prédéfinis."""
    TypeGraphiqueRapport = apps.get_model('analytics', 'TypeGraphiqueRapport')
    TypeGraphiqueRapport.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0008_sections_rapport_graphiques_predefinis'),
    ]

    operations = [
        migrations.RunPython(
            creer_graphiques_predefinis,
            supprimer_graphiques_predefinis
        ),
    ]
