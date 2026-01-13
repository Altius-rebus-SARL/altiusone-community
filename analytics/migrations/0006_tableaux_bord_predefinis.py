# analytics/migrations/0006_tableaux_bord_predefinis.py
from django.db import migrations


def create_tableaux_bord_predefinis(apps, schema_editor):
    """Crée les tableaux de bord prédéfinis pour le système."""
    TableauBord = apps.get_model('analytics', 'TableauBord')
    User = apps.get_model('core', 'User')

    # Récupérer le premier superuser ou admin
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()

    if not admin_user:
        # Pas d'utilisateur, on ne peut pas créer les tableaux
        return

    # Liste des tableaux de bord prédéfinis
    tableaux_predefinis = [
        {
            'nom': 'Tableau Financier',
            'description': 'Vue d\'ensemble des indicateurs financiers: chiffre d\'affaires, marges, rentabilité et trésorerie.',
            'visibilite': 'TOUS',
            'favori': True,
            'ordre': 1,
            'configuration': {
                'layout': 'grid',
                'system': True,
                'icon': 'ph ph-chart-pie-slice',
                'color': 'primary',
                'widgets': [
                    {'type': 'kpi_card', 'metric': 'ca_total', 'label': 'Chiffre d\'affaires', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'marge_brute', 'label': 'Marge brute', 'position': {'x': 3, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'resultat_net', 'label': 'Résultat net', 'position': {'x': 6, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'tresorerie', 'label': 'Trésorerie', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'chart', 'chart_type': 'area', 'metric': 'evolution_ca', 'label': 'Évolution CA', 'position': {'x': 0, 'y': 2, 'w': 8, 'h': 4}},
                    {'type': 'chart', 'chart_type': 'donut', 'metric': 'repartition_charges', 'label': 'Répartition charges', 'position': {'x': 8, 'y': 2, 'w': 4, 'h': 4}},
                ]
            },
        },
        {
            'nom': 'Tableau Facturation',
            'description': 'Suivi de la facturation: factures émises, encaissements, créances clients et délais de paiement.',
            'visibilite': 'TOUS',
            'favori': True,
            'ordre': 2,
            'configuration': {
                'layout': 'grid',
                'system': True,
                'icon': 'ph ph-receipt',
                'color': 'success',
                'widgets': [
                    {'type': 'kpi_card', 'metric': 'factures_emises', 'label': 'Factures émises', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'montant_facture', 'label': 'Montant facturé', 'position': {'x': 3, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'encaissements', 'label': 'Encaissements', 'position': {'x': 6, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'creances_ouvertes', 'label': 'Créances ouvertes', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'chart', 'chart_type': 'bar', 'metric': 'factures_par_mois', 'label': 'Factures par mois', 'position': {'x': 0, 'y': 2, 'w': 6, 'h': 4}},
                    {'type': 'chart', 'chart_type': 'horizontalBar', 'metric': 'aging_creances', 'label': 'Échéancier créances', 'position': {'x': 6, 'y': 2, 'w': 6, 'h': 4}},
                ]
            },
        },
        {
            'nom': 'Tableau TVA',
            'description': 'Suivi de la TVA: TVA collectée, TVA déductible, solde et échéances de déclaration.',
            'visibilite': 'TOUS',
            'favori': False,
            'ordre': 3,
            'configuration': {
                'layout': 'grid',
                'system': True,
                'icon': 'ph ph-percent',
                'color': 'warning',
                'widgets': [
                    {'type': 'kpi_card', 'metric': 'tva_collectee', 'label': 'TVA collectée', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'tva_deductible', 'label': 'TVA déductible', 'position': {'x': 3, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'tva_a_payer', 'label': 'TVA à payer', 'position': {'x': 6, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'prochaine_echeance', 'label': 'Prochaine échéance', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'chart', 'chart_type': 'line', 'metric': 'evolution_tva', 'label': 'Évolution TVA', 'position': {'x': 0, 'y': 2, 'w': 8, 'h': 4}},
                    {'type': 'table', 'metric': 'declarations_recentes', 'label': 'Déclarations récentes', 'position': {'x': 8, 'y': 2, 'w': 4, 'h': 4}},
                ]
            },
        },
        {
            'nom': 'Tableau Salaires',
            'description': 'Gestion des salaires: masse salariale, charges sociales, effectifs et coûts par employé.',
            'visibilite': 'TOUS',
            'favori': False,
            'ordre': 4,
            'configuration': {
                'layout': 'grid',
                'system': True,
                'icon': 'ph ph-users-three',
                'color': 'info',
                'widgets': [
                    {'type': 'kpi_card', 'metric': 'masse_salariale', 'label': 'Masse salariale', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'charges_sociales', 'label': 'Charges sociales', 'position': {'x': 3, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'effectif', 'label': 'Effectif', 'position': {'x': 6, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'cout_moyen', 'label': 'Coût moyen/employé', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'chart', 'chart_type': 'area', 'metric': 'evolution_masse_salariale', 'label': 'Évolution masse salariale', 'position': {'x': 0, 'y': 2, 'w': 8, 'h': 4}},
                    {'type': 'chart', 'chart_type': 'donut', 'metric': 'repartition_charges', 'label': 'Répartition charges', 'position': {'x': 8, 'y': 2, 'w': 4, 'h': 4}},
                ]
            },
        },
        {
            'nom': 'Tableau Clients',
            'description': 'Analyse clientèle: top clients, répartition CA, fidélité et évolution du portefeuille.',
            'visibilite': 'TOUS',
            'favori': True,
            'ordre': 5,
            'configuration': {
                'layout': 'grid',
                'system': True,
                'icon': 'ph ph-address-book',
                'color': 'secondary',
                'widgets': [
                    {'type': 'kpi_card', 'metric': 'nombre_clients', 'label': 'Nombre de clients', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'nouveaux_clients', 'label': 'Nouveaux clients', 'position': {'x': 3, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'ca_moyen_client', 'label': 'CA moyen/client', 'position': {'x': 6, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'taux_retention', 'label': 'Taux de rétention', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'chart', 'chart_type': 'horizontalBar', 'metric': 'top_clients', 'label': 'Top 10 clients', 'position': {'x': 0, 'y': 2, 'w': 6, 'h': 4}},
                    {'type': 'chart', 'chart_type': 'treemap', 'metric': 'repartition_ca_clients', 'label': 'Répartition CA', 'position': {'x': 6, 'y': 2, 'w': 6, 'h': 4}},
                ]
            },
        },
        {
            'nom': 'Tableau Rentabilité',
            'description': 'Analyse de la rentabilité: marges par prestation, rentabilité par client et par mandat.',
            'visibilite': 'TOUS',
            'favori': False,
            'ordre': 6,
            'configuration': {
                'layout': 'grid',
                'system': True,
                'icon': 'ph ph-trend-up',
                'color': 'danger',
                'widgets': [
                    {'type': 'kpi_card', 'metric': 'marge_moyenne', 'label': 'Marge moyenne', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'taux_rentabilite', 'label': 'Taux rentabilité', 'position': {'x': 3, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'heures_facturables', 'label': 'Heures facturables', 'position': {'x': 6, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'taux_facturation', 'label': 'Taux facturation', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'chart', 'chart_type': 'bar', 'metric': 'rentabilite_prestation', 'label': 'Rentabilité par prestation', 'position': {'x': 0, 'y': 2, 'w': 6, 'h': 4}},
                    {'type': 'chart', 'chart_type': 'line', 'metric': 'evolution_rentabilite', 'label': 'Évolution rentabilité', 'position': {'x': 6, 'y': 2, 'w': 6, 'h': 4}},
                ]
            },
        },
        {
            'nom': 'Tableau Time Tracking',
            'description': 'Suivi du temps: heures par collaborateur, par projet et par type d\'activité.',
            'visibilite': 'TOUS',
            'favori': False,
            'ordre': 7,
            'configuration': {
                'layout': 'grid',
                'system': True,
                'icon': 'ph ph-clock',
                'color': 'dark',
                'widgets': [
                    {'type': 'kpi_card', 'metric': 'heures_totales', 'label': 'Heures totales', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'heures_facturees', 'label': 'Heures facturées', 'position': {'x': 3, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'taux_utilisation', 'label': 'Taux utilisation', 'position': {'x': 6, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'heures_non_facturees', 'label': 'Heures non facturées', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'chart', 'chart_type': 'stackedBar', 'metric': 'heures_par_collaborateur', 'label': 'Heures par collaborateur', 'position': {'x': 0, 'y': 2, 'w': 6, 'h': 4}},
                    {'type': 'chart', 'chart_type': 'donut', 'metric': 'repartition_activites', 'label': 'Répartition activités', 'position': {'x': 6, 'y': 2, 'w': 6, 'h': 4}},
                ]
            },
        },
        {
            'nom': 'Tableau Comptabilité',
            'description': 'Vue comptable: balance, journaux, comptes clés et écritures récentes.',
            'visibilite': 'TOUS',
            'favori': False,
            'ordre': 8,
            'configuration': {
                'layout': 'grid',
                'system': True,
                'icon': 'ph ph-calculator',
                'color': 'primary',
                'widgets': [
                    {'type': 'kpi_card', 'metric': 'total_actif', 'label': 'Total actif', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'total_passif', 'label': 'Total passif', 'position': {'x': 3, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'ecritures_mois', 'label': 'Écritures du mois', 'position': {'x': 6, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'kpi_card', 'metric': 'comptes_desequilibres', 'label': 'Comptes déséquilibrés', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 2}},
                    {'type': 'chart', 'chart_type': 'bar', 'metric': 'mouvements_journaux', 'label': 'Mouvements par journal', 'position': {'x': 0, 'y': 2, 'w': 6, 'h': 4}},
                    {'type': 'table', 'metric': 'ecritures_recentes', 'label': 'Écritures récentes', 'position': {'x': 6, 'y': 2, 'w': 6, 'h': 4}},
                ]
            },
        },
    ]

    for tableau_data in tableaux_predefinis:
        # Vérifier si le tableau existe déjà
        if not TableauBord.objects.filter(nom=tableau_data['nom']).exists():
            TableauBord.objects.create(
                proprietaire=admin_user,
                **tableau_data
            )


def remove_tableaux_bord_predefinis(apps, schema_editor):
    """Supprime les tableaux de bord prédéfinis (système)."""
    TableauBord = apps.get_model('analytics', 'TableauBord')

    noms_tableaux = [
        'Tableau Financier',
        'Tableau Facturation',
        'Tableau TVA',
        'Tableau Salaires',
        'Tableau Clients',
        'Tableau Rentabilité',
        'Tableau Time Tracking',
        'Tableau Comptabilité',
    ]

    TableauBord.objects.filter(nom__in=noms_tableaux).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('analytics', '0005_indicateur_periodicite_ref_planificationrapport_frequence_ref'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_tableaux_bord_predefinis,
            remove_tableaux_bord_predefinis
        ),
    ]
