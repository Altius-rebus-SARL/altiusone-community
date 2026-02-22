# salaires/migrations/0007_populate_employe_regime_fiscal.py
"""
Populate Employe.regime_fiscal from mandat.regime_fiscal.
"""
from django.db import migrations


def populate_employe_regime(apps, schema_editor):
    """Populate Employe.regime_fiscal from mandat.regime_fiscal"""
    Employe = apps.get_model('salaires', 'Employe')
    Mandat = apps.get_model('core', 'Mandat')

    for employe in Employe.objects.filter(regime_fiscal__isnull=True):
        try:
            mandat = Mandat.objects.get(pk=employe.mandat_id)
            if mandat.regime_fiscal_id:
                employe.regime_fiscal_id = mandat.regime_fiscal_id
                employe.save(update_fields=['regime_fiscal'])
        except Exception:
            pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0006_employe_regime_fiscal'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        migrations.RunPython(populate_employe_regime, noop),
    ]
