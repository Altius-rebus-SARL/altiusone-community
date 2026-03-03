# Data migration: backfill regime_fiscal=CH on existing rows + seed OHADA taux
from django.db import migrations


def backfill_and_seed(apps, schema_editor):
    RegimeFiscal = apps.get_model('tva', 'RegimeFiscal')
    TauxImposition = apps.get_model('fiscalite', 'TauxImposition')

    # --- Backfill existing Swiss rows ---
    regime_ch = RegimeFiscal.objects.filter(code='CH').first()
    if regime_ch:
        TauxImposition.objects.filter(regime_fiscal__isnull=True).update(
            regime_fiscal=regime_ch
        )

    # --- Seed OHADA taux (2025) ---
    regime_cm = RegimeFiscal.objects.filter(code='CM').first()
    regime_sn = RegimeFiscal.objects.filter(code='SN').first()
    regime_ci = RegimeFiscal.objects.filter(code='CI').first()

    seeds = []

    if regime_cm:
        seeds.extend([
            {
                'regime_fiscal': regime_cm,
                'type_impot': 'IS_CM',
                'annee': 2025,
                'taux_fixe': 33.00,
                'bareme': {},
            },
            {
                'regime_fiscal': regime_cm,
                'type_impot': 'IRPP',
                'annee': 2025,
                'taux_fixe': None,
                'bareme': {
                    'tranches': [
                        {'min': 0, 'max': 2000000, 'taux': 10},
                        {'min': 2000000, 'max': 3000000, 'taux': 15},
                        {'min': 3000000, 'max': 5000000, 'taux': 25},
                        {'min': 5000000, 'max': 99999999999, 'taux': 35},
                    ]
                },
            },
            {
                'regime_fiscal': regime_cm,
                'type_impot': 'PATENTE',
                'annee': 2025,
                'taux_fixe': None,
                'bareme': {},
            },
            {
                'regime_fiscal': regime_cm,
                'type_impot': 'TPF',
                'annee': 2025,
                'taux_fixe': 0.11,
                'bareme': {},
            },
        ])

    if regime_sn:
        seeds.extend([
            {
                'regime_fiscal': regime_sn,
                'type_impot': 'IS_SN',
                'annee': 2025,
                'taux_fixe': 30.00,
                'bareme': {},
            },
            {
                'regime_fiscal': regime_sn,
                'type_impot': 'IR',
                'annee': 2025,
                'taux_fixe': None,
                'bareme': {},
            },
            {
                'regime_fiscal': regime_sn,
                'type_impot': 'CFE',
                'annee': 2025,
                'taux_fixe': None,
                'bareme': {},
            },
        ])

    if regime_ci:
        seeds.extend([
            {
                'regime_fiscal': regime_ci,
                'type_impot': 'IS_SN',
                'annee': 2025,
                'taux_fixe': 25.00,
                'bareme': {},
            },
            {
                'regime_fiscal': regime_ci,
                'type_impot': 'IR',
                'annee': 2025,
                'taux_fixe': None,
                'bareme': {},
            },
            {
                'regime_fiscal': regime_ci,
                'type_impot': 'CFE',
                'annee': 2025,
                'taux_fixe': None,
                'bareme': {},
            },
        ])

    for seed in seeds:
        TauxImposition.objects.update_or_create(
            regime_fiscal=seed['regime_fiscal'],
            canton='',
            commune='',
            subdivision='',
            type_impot=seed['type_impot'],
            annee=seed['annee'],
            defaults={
                'taux_fixe': seed['taux_fixe'],
                'bareme': seed['bareme'],
                'actif': True,
            },
        )


def reverse_backfill(apps, schema_editor):
    TauxImposition = apps.get_model('fiscalite', 'TauxImposition')
    # Remove seeded OHADA rows
    TauxImposition.objects.filter(
        type_impot__in=['IS_CM', 'IRPP', 'PATENTE', 'TPF', 'IS_SN', 'IR', 'CFE']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0010_extend_type_impot'),
        ('tva', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_and_seed, reverse_backfill),
    ]
