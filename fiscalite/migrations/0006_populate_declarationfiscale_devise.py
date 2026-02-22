# fiscalite/migrations/0006_populate_declarationfiscale_devise.py
from django.db import migrations


def populate_devise_and_regime(apps, schema_editor):
    """Populate DeclarationFiscale.devise with CHF and TauxImposition.regime_fiscal with CH."""
    DeclarationFiscale = apps.get_model('fiscalite', 'DeclarationFiscale')
    TauxImposition = apps.get_model('fiscalite', 'TauxImposition')
    Devise = apps.get_model('core', 'Devise')
    RegimeFiscal = apps.get_model('tva', 'RegimeFiscal')

    devise_chf = Devise.objects.filter(code='CHF').first()
    regime_ch = RegimeFiscal.objects.filter(code='CH').first()

    if devise_chf:
        DeclarationFiscale.objects.filter(devise__isnull=True).update(devise=devise_chf)

    if regime_ch:
        TauxImposition.objects.filter(regime_fiscal__isnull=True).update(
            regime_fiscal=regime_ch
        )


def reverse_populate(apps, schema_editor):
    DeclarationFiscale = apps.get_model('fiscalite', 'DeclarationFiscale')
    TauxImposition = apps.get_model('fiscalite', 'TauxImposition')
    DeclarationFiscale.objects.all().update(devise=None)
    TauxImposition.objects.all().update(regime_fiscal=None)


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0005_declarationfiscale_devise_tauximposition_regime'),
        ('core', '0007_mandat_regime_devise_not_null'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_devise_and_regime, reverse_populate),
    ]
