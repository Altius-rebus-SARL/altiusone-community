"""
Migration de données: lier les clients et comptes bancaires existants à l'entreprise par défaut.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Entreprise = apps.get_model('core', 'Entreprise')
    Client = apps.get_model('core', 'Client')
    CompteBancaire = apps.get_model('core', 'CompteBancaire')

    entreprise = Entreprise.objects.first()
    if entreprise:
        # Marquer comme entreprise par défaut
        if not entreprise.est_defaut:
            entreprise.est_defaut = True
            entreprise.save(update_fields=['est_defaut'])

        # Lier tous les clients orphelins
        Client.objects.filter(entreprise__isnull=True).update(entreprise=entreprise)

        # Lier les comptes principaux orphelins
        CompteBancaire.objects.filter(
            est_compte_principal=True, entreprise__isnull=True
        ).update(entreprise=entreprise)


def backwards(apps, schema_editor):
    Client = apps.get_model('core', 'Client')
    CompteBancaire = apps.get_model('core', 'CompteBancaire')
    Entreprise = apps.get_model('core', 'Entreprise')

    # Détacher les clients et comptes
    Client.objects.all().update(entreprise=None)
    CompteBancaire.objects.all().update(entreprise=None)

    # Enlever le flag est_defaut
    Entreprise.objects.all().update(est_defaut=False)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_entreprise_multi_instance'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
