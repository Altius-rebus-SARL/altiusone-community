# Generated manually to add additional periodicites for analytics module
# core/migrations/0009_add_additional_periodicites.py

from django.db import migrations


def add_additional_periodicites(apps, schema_editor):
    """Ajouter les périodicités supplémentaires pour analytics"""
    Periodicite = apps.get_model('core', 'Periodicite')

    # Périodicités additionnelles pour analytics
    additional_periodicites = [
        {'code': 'TEMPS_REEL', 'libelle': 'Temps réel', 'nombre_mois': 0, 'nombre_par_an': 0, 'ordre': 0,
         'description': 'Calcul en temps réel'},
        {'code': 'JOUR', 'libelle': 'Journalier', 'nombre_mois': 0, 'nombre_par_an': 365, 'ordre': 1,
         'description': 'Calcul quotidien'},
        {'code': 'SEMAINE', 'libelle': 'Hebdomadaire', 'nombre_mois': 0, 'nombre_par_an': 52, 'ordre': 2,
         'description': 'Calcul hebdomadaire'},
    ]

    for p in additional_periodicites:
        # Utiliser get_or_create pour éviter les doublons
        Periodicite.objects.get_or_create(
            code=p['code'],
            defaults=p
        )


def remove_additional_periodicites(apps, schema_editor):
    """Supprimer les périodicités additionnelles"""
    Periodicite = apps.get_model('core', 'Periodicite')
    Periodicite.objects.filter(code__in=['TEMPS_REEL', 'JOUR', 'SEMAINE']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_add_type_mandat_periodicite_type_facturation'),
    ]

    operations = [
        migrations.RunPython(add_additional_periodicites, remove_additional_periodicites),
    ]
