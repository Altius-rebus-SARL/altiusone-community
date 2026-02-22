# fiscalite/migrations/0003_populate_declarationfiscale_regime.py
from django.db import migrations


def populate_declarationfiscale_regime(apps, schema_editor):
    """Assign CH regime to all existing DeclarationFiscale without regime_fiscal."""
    DeclarationFiscale = apps.get_model('fiscalite', 'DeclarationFiscale')
    RegimeFiscal = apps.get_model('tva', 'RegimeFiscal')

    regime_ch = RegimeFiscal.objects.filter(code='CH').first()
    if regime_ch:
        DeclarationFiscale.objects.filter(regime_fiscal__isnull=True).update(
            regime_fiscal=regime_ch
        )


def reverse_populate(apps, schema_editor):
    DeclarationFiscale = apps.get_model('fiscalite', 'DeclarationFiscale')
    DeclarationFiscale.objects.all().update(regime_fiscal=None)


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0002_declarationfiscale_regime'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.RunPython(
            populate_declarationfiscale_regime, reverse_populate
        ),
    ]
