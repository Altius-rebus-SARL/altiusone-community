# core/migrations/0006_populate_mandat_regime_devise.py
from django.db import migrations


def populate_mandat_regime_devise(apps, schema_editor):
    """Assign default regime_fiscal and devise to existing Mandats and Clients."""
    Mandat = apps.get_model('core', 'Mandat')
    Client = apps.get_model('core', 'Client')
    RegimeFiscal = apps.get_model('tva', 'RegimeFiscal')
    ConfigurationTVA = apps.get_model('tva', 'ConfigurationTVA')
    Devise = apps.get_model('core', 'Devise')

    regime_ch = RegimeFiscal.objects.filter(code='CH').first()
    devise_chf = Devise.objects.filter(code='CHF').first()

    # Mandats: regime_fiscal
    for mandat in Mandat.objects.filter(regime_fiscal__isnull=True):
        regime = None
        # Try to get regime from config_tva
        try:
            config = ConfigurationTVA.objects.get(mandat=mandat)
            if config.regime_id:
                regime = config.regime
        except ConfigurationTVA.DoesNotExist:
            pass
        if not regime:
            regime = regime_ch
        if regime:
            mandat.regime_fiscal = regime
            mandat.save(update_fields=['regime_fiscal'])

    # Mandats: devise
    if devise_chf:
        Mandat.objects.filter(devise__isnull=True).update(devise=devise_chf)

    # Clients: regime_fiscal_defaut
    if regime_ch:
        Client.objects.filter(regime_fiscal_defaut__isnull=True).update(
            regime_fiscal_defaut=regime_ch
        )


def reverse_populate(apps, schema_editor):
    """Reverse: set all to null."""
    Mandat = apps.get_model('core', 'Mandat')
    Client = apps.get_model('core', 'Client')
    Mandat.objects.all().update(regime_fiscal=None, devise=None)
    Client.objects.all().update(regime_fiscal_defaut=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_mandat_regime_devise_client_regime'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_mandat_regime_devise, reverse_populate),
    ]
