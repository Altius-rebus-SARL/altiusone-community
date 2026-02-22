from django.db import migrations


TYPES_PRESTATIONS = [
    {'code': 'COMPTABILITE', 'libelle': 'Comptabilité', 'icone': 'ph-calculator', 'ordre': 1},
    {'code': 'TVA', 'libelle': 'TVA', 'icone': 'ph-receipt', 'ordre': 2},
    {'code': 'SALAIRES', 'libelle': 'Salaires', 'icone': 'ph-users', 'ordre': 3},
    {'code': 'CONSEIL', 'libelle': 'Conseil', 'icone': 'ph-chat-circle', 'ordre': 4},
    {'code': 'AUDIT', 'libelle': 'Audit', 'icone': 'ph-magnifying-glass', 'ordre': 5},
    {'code': 'FISCALITE', 'libelle': 'Fiscalité', 'icone': 'ph-bank', 'ordre': 6},
    {'code': 'JURIDIQUE', 'libelle': 'Juridique', 'icone': 'ph-scales', 'ordre': 7},
    {'code': 'CREATION', 'libelle': 'Création entreprise', 'icone': 'ph-buildings', 'ordre': 8},
    {'code': 'AUTRE', 'libelle': 'Autre', 'icone': 'ph-dots-three', 'ordre': 9},
]


def populate_types_and_backfill(apps, schema_editor):
    TypePrestation = apps.get_model('facturation', 'TypePrestation')
    Prestation = apps.get_model('facturation', 'Prestation')

    # Create reference rows
    type_map = {}
    for tp in TYPES_PRESTATIONS:
        obj, _ = TypePrestation.objects.get_or_create(
            code=tp['code'],
            defaults={
                'libelle': tp['libelle'],
                'icone': tp['icone'],
                'ordre': tp['ordre'],
                'couleur': 'primary',
                'is_active': True,
            },
        )
        type_map[tp['code']] = obj

    # Backfill existing Prestation rows
    for prestation in Prestation.objects.all():
        old_code = prestation.type_prestation
        if old_code and old_code in type_map:
            prestation.type_prestation_ref = type_map[old_code]
        else:
            # Fallback to AUTRE
            prestation.type_prestation_ref = type_map['AUTRE']
        prestation.save(update_fields=['type_prestation_ref'])


def reverse_backfill(apps, schema_editor):
    Prestation = apps.get_model('facturation', 'Prestation')
    for prestation in Prestation.objects.select_related('type_prestation_ref').all():
        if prestation.type_prestation_ref:
            prestation.type_prestation = prestation.type_prestation_ref.code
            prestation.save(update_fields=['type_prestation'])


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0011_typeprestation'),
    ]

    operations = [
        migrations.RunPython(populate_types_and_backfill, reverse_backfill),
    ]
