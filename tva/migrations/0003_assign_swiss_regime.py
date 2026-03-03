# tva/migrations/0003_assign_swiss_regime.py
# Data migration: create CH regime and assign it to existing TauxTVA/CodeTVA/ConfigurationTVA

from decimal import Decimal
from django.db import migrations


def forwards(apps, schema_editor):
    Devise = apps.get_model('core', 'Devise')
    RegimeFiscal = apps.get_model('tva', 'RegimeFiscal')
    TauxTVA = apps.get_model('tva', 'TauxTVA')
    CodeTVA = apps.get_model('tva', 'CodeTVA')
    ConfigurationTVA = apps.get_model('tva', 'ConfigurationTVA')

    # 1. Ensure CHF devise exists
    chf, _ = Devise.objects.get_or_create(
        code='CHF',
        defaults={
            'nom': 'Franc suisse',
            'symbole': 'Fr.',
            'decimales': 2,
            'separateur_milliers': "'",
            'separateur_decimal': '.',
            'symbole_avant': False,
            'taux_change': Decimal('1'),
            'est_devise_base': True,
            'actif': True,
        }
    )

    # 2. Create RegimeFiscal CH
    ch_regime, _ = RegimeFiscal.objects.get_or_create(
        code='CH',
        defaults={
            'nom': 'Suisse',
            'pays': 'CH',
            'devise_defaut': chf,
            'nom_taxe': 'TVA',
            'taux_normal': Decimal('8.1'),
            'a_taux_reduit': True,
            'a_taux_special': True,
            'format_numero_tva': r'^CHE-\d{3}\.\d{3}\.\d{3}\s?TVA$',
            'supporte_xml': True,
            'methodes_disponibles': [
                'EFFECTIVE', 'TAUX_DETTE', 'TAUX_FORFAITAIRE', 'FORFAIT_BRANCHE'
            ],
        }
    )

    # 3. Assign CH regime to all existing TauxTVA without a regime
    TauxTVA.objects.filter(regime__isnull=True).update(regime=ch_regime)

    # 4. Assign CH regime to all existing CodeTVA without a regime
    CodeTVA.objects.filter(regime__isnull=True).update(regime=ch_regime)

    # 5. Assign CH regime to all existing ConfigurationTVA without a regime
    ConfigurationTVA.objects.filter(regime__isnull=True).update(regime=ch_regime)


def backwards(apps, schema_editor):
    # Reverse: set regime to NULL
    TauxTVA = apps.get_model('tva', 'TauxTVA')
    CodeTVA = apps.get_model('tva', 'CodeTVA')
    ConfigurationTVA = apps.get_model('tva', 'ConfigurationTVA')

    TauxTVA.objects.all().update(regime=None)
    CodeTVA.objects.all().update(regime=None)
    ConfigurationTVA.objects.all().update(regime=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tva', '0002_add_regime_fiscal'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
