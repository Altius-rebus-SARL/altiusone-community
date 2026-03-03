# salaires/migrations/0003_populate_employe_devise_salaire.py
from django.db import migrations


def populate_employe_devise(apps, schema_editor):
    """Assign CHF devise to all existing Employes without devise_salaire."""
    Employe = apps.get_model('salaires', 'Employe')
    Devise = apps.get_model('core', 'Devise')

    devise_chf = Devise.objects.filter(code='CHF').first()
    if devise_chf:
        Employe.objects.filter(devise_salaire__isnull=True).update(
            devise_salaire=devise_chf
        )


def reverse_populate(apps, schema_editor):
    Employe = apps.get_model('salaires', 'Employe')
    Employe.objects.all().update(devise_salaire=None)


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0002_employe_devise_salaire'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        migrations.RunPython(populate_employe_devise, reverse_populate),
    ]
