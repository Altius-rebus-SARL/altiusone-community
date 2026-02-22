# facturation/migrations/0009_populate_facture_regime_timetracking_devise.py
"""
Populate regime_fiscal on Facture from mandat.regime_fiscal.
Populate devise on TimeTracking from mandat.devise.
"""
from django.db import migrations


def populate_facture_regime(apps, schema_editor):
    """Populate Facture.regime_fiscal from mandat.regime_fiscal"""
    Facture = apps.get_model('facturation', 'Facture')
    Mandat = apps.get_model('core', 'Mandat')

    for facture in Facture.objects.all():
        try:
            mandat = Mandat.objects.get(pk=facture.mandat_id)
            if mandat.regime_fiscal_id:
                facture.regime_fiscal_id = mandat.regime_fiscal_id
                facture.save(update_fields=['regime_fiscal'])
        except Exception:
            pass


def populate_timetracking_devise(apps, schema_editor):
    """Populate TimeTracking.devise from mandat.devise"""
    TimeTracking = apps.get_model('facturation', 'TimeTracking')
    Mandat = apps.get_model('core', 'Mandat')

    for tt in TimeTracking.objects.all():
        try:
            mandat = Mandat.objects.get(pk=tt.mandat_id)
            if mandat.devise_id:
                tt.devise_id = mandat.devise_id
                tt.save(update_fields=['devise'])
        except Exception:
            pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0008_facture_regime_exercice_timetracking_devise'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        migrations.RunPython(populate_facture_regime, noop),
        migrations.RunPython(populate_timetracking_devise, noop),
    ]
