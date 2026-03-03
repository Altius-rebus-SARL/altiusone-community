# tva/migrations/0007_populate_declarationtva_regime_devise.py
"""
Populate regime_fiscal and devise on DeclarationTVA from mandat.config_tva.regime.
Make ConfigurationTVA.regime NOT NULL.
"""
from django.db import migrations


def populate_declaration_tva_regime_devise(apps, schema_editor):
    """Populate regime_fiscal and devise from mandat.config_tva.regime"""
    DeclarationTVA = apps.get_model('tva', 'DeclarationTVA')
    ConfigurationTVA = apps.get_model('tva', 'ConfigurationTVA')

    for decl in DeclarationTVA.objects.select_related('mandat').all():
        try:
            config = ConfigurationTVA.objects.get(mandat=decl.mandat)
            if config.regime_id:
                decl.regime_fiscal_id = config.regime_id
                # Get devise from regime
                RegimeFiscal = apps.get_model('tva', 'RegimeFiscal')
                regime = RegimeFiscal.objects.get(pk=config.regime_id)
                decl.devise_id = regime.devise_defaut_id
                decl.save(update_fields=['regime_fiscal', 'devise'])
        except (ConfigurationTVA.DoesNotExist, Exception):
            pass


def populate_config_tva_regime(apps, schema_editor):
    """Populate ConfigurationTVA.regime from mandat.regime_fiscal where null"""
    ConfigurationTVA = apps.get_model('tva', 'ConfigurationTVA')
    Mandat = apps.get_model('core', 'Mandat')

    for config in ConfigurationTVA.objects.filter(regime__isnull=True):
        try:
            mandat = Mandat.objects.get(pk=config.mandat_id)
            if mandat.regime_fiscal_id:
                config.regime_id = mandat.regime_fiscal_id
                config.save(update_fields=['regime'])
        except Exception:
            pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tva', '0006_declarationtva_regime_devise_operationtva_fk'),
        ('core', '0007_mandat_regime_devise_not_null'),
    ]

    operations = [
        migrations.RunPython(populate_config_tva_regime, noop),
        migrations.RunPython(populate_declaration_tva_regime_devise, noop),
    ]
