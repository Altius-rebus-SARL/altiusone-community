# facturation/migrations/0004_populate_facture_devise.py
from django.db import migrations


def populate_facture_devise(apps, schema_editor):
    """Assign CHF devise to all existing Factures without devise."""
    Facture = apps.get_model('facturation', 'Facture')
    Devise = apps.get_model('core', 'Devise')

    devise_chf = Devise.objects.filter(code='CHF').first()
    if devise_chf:
        Facture.objects.filter(devise__isnull=True).update(devise=devise_chf)


def reverse_populate(apps, schema_editor):
    Facture = apps.get_model('facturation', 'Facture')
    Facture.objects.all().update(devise=None)


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0003_facture_devise'),
        ('core', '0005_mandat_regime_devise_client_regime'),
    ]

    operations = [
        migrations.RunPython(populate_facture_devise, reverse_populate),
    ]
