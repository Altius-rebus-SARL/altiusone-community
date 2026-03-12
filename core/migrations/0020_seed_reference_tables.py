"""Seed initial data for TypeMandat, Periodicite, TypeFacturation."""

from django.db import migrations


def seed_data(apps, schema_editor):
    TypeMandat = apps.get_model('core', 'TypeMandat')
    Periodicite = apps.get_model('core', 'Periodicite')
    TypeFacturation = apps.get_model('core', 'TypeFacturation')

    # Périodicités
    periodicites = [
        {'code': 'MENSUEL', 'libelle': 'Mensuel', 'nombre_mois': 1, 'nombre_par_an': 12, 'ordre': 1},
        {'code': 'TRIMESTRIEL', 'libelle': 'Trimestriel', 'nombre_mois': 3, 'nombre_par_an': 4, 'ordre': 2},
        {'code': 'SEMESTRIEL', 'libelle': 'Semestriel', 'nombre_mois': 6, 'nombre_par_an': 2, 'ordre': 3},
        {'code': 'ANNUEL', 'libelle': 'Annuel', 'nombre_mois': 12, 'nombre_par_an': 1, 'ordre': 4},
    ]
    for p in periodicites:
        Periodicite.objects.get_or_create(code=p['code'], defaults=p)

    # Types de mandats
    types_mandats = [
        {'code': 'COMPTA', 'libelle': 'Comptabilité', 'description': 'Tenue de la comptabilité', 'icone': 'ph-calculator', 'couleur': 'primary', 'modules_actifs': ['compta'], 'ordre': 1},
        {'code': 'TVA', 'libelle': 'TVA', 'description': 'Déclarations et gestion TVA', 'icone': 'ph-percent', 'couleur': 'info', 'modules_actifs': ['tva'], 'ordre': 2},
        {'code': 'SALAIRES', 'libelle': 'Salaires', 'description': 'Gestion des salaires', 'icone': 'ph-users', 'couleur': 'success', 'modules_actifs': ['salaires'], 'ordre': 3},
        {'code': 'FISCAL', 'libelle': 'Conseil fiscal', 'description': 'Conseil et planification fiscale', 'icone': 'ph-scales', 'couleur': 'warning', 'modules_actifs': [], 'ordre': 4},
        {'code': 'REVISION', 'libelle': 'Révision', 'description': 'Contrôle et révision des comptes', 'icone': 'ph-magnifying-glass', 'couleur': 'danger', 'modules_actifs': ['compta', 'revision'], 'ordre': 5},
        {'code': 'CREATION', 'libelle': 'Création d\'entreprise', 'description': 'Accompagnement à la création', 'icone': 'ph-rocket', 'couleur': 'secondary', 'modules_actifs': [], 'ordre': 6},
        {'code': 'GLOBAL', 'libelle': 'Mandat global', 'description': 'Mandat complet (compta, TVA, salaires)', 'icone': 'ph-briefcase', 'couleur': 'primary', 'modules_actifs': ['compta', 'tva', 'salaires'], 'ordre': 7},
        {'code': 'CONSEIL', 'libelle': 'Conseil', 'description': 'Conseil et accompagnement', 'icone': 'ph-chat-circle', 'couleur': 'info', 'modules_actifs': [], 'ordre': 8},
    ]
    for t in types_mandats:
        TypeMandat.objects.get_or_create(code=t['code'], defaults=t)

    # Types de facturation
    types_facturation = [
        {'code': 'FORFAIT', 'libelle': 'Forfait', 'description': 'Montant fixe convenu', 'necessite_forfait': True, 'necessite_taux_horaire': False, 'ordre': 1},
        {'code': 'HORAIRE', 'libelle': 'Taux horaire', 'description': 'Facturation au temps passé', 'necessite_forfait': False, 'necessite_taux_horaire': True, 'ordre': 2},
        {'code': 'MIXTE', 'libelle': 'Mixte', 'description': 'Forfait de base + dépassement au taux horaire', 'necessite_forfait': True, 'necessite_taux_horaire': True, 'ordre': 3},
        {'code': 'ABONNEMENT', 'libelle': 'Abonnement', 'description': 'Montant récurrent périodique', 'necessite_forfait': True, 'necessite_taux_horaire': False, 'ordre': 4},
    ]
    for tf in types_facturation:
        TypeFacturation.objects.get_or_create(code=tf['code'], defaults=tf)


def reverse_seed(apps, schema_editor):
    # Ne pas supprimer les données en reverse — elles peuvent avoir été modifiées
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_alter_client_responsable_optional"),
    ]

    operations = [
        migrations.RunPython(seed_data, reverse_seed),
    ]
