# analytics/migrations/0007_fix_tableaux_bord_icons.py
from django.db import migrations


def fix_icons_to_duotone(apps, schema_editor):
    """Met à jour les icônes pour utiliser ph-duotone au lieu de ph."""
    TableauBord = apps.get_model('analytics', 'TableauBord')

    icon_mapping = {
        'ph ph-chart-pie-slice': 'ph-duotone ph-chart-pie-slice',
        'ph ph-receipt': 'ph-duotone ph-receipt',
        'ph ph-percent': 'ph-duotone ph-percent',
        'ph ph-users-three': 'ph-duotone ph-users-three',
        'ph ph-address-book': 'ph-duotone ph-address-book',
        'ph ph-trend-up': 'ph-duotone ph-trend-up',
        'ph ph-clock': 'ph-duotone ph-clock',
        'ph ph-calculator': 'ph-duotone ph-calculator',
    }

    for tableau in TableauBord.objects.all():
        if tableau.configuration and 'icon' in tableau.configuration:
            old_icon = tableau.configuration['icon']
            if old_icon in icon_mapping:
                tableau.configuration['icon'] = icon_mapping[old_icon]
                tableau.save()


def revert_icons(apps, schema_editor):
    """Revert les icônes vers ph."""
    TableauBord = apps.get_model('analytics', 'TableauBord')

    icon_mapping = {
        'ph-duotone ph-chart-pie-slice': 'ph ph-chart-pie-slice',
        'ph-duotone ph-receipt': 'ph ph-receipt',
        'ph-duotone ph-percent': 'ph ph-percent',
        'ph-duotone ph-users-three': 'ph ph-users-three',
        'ph-duotone ph-address-book': 'ph ph-address-book',
        'ph-duotone ph-trend-up': 'ph ph-trend-up',
        'ph-duotone ph-clock': 'ph ph-clock',
        'ph-duotone ph-calculator': 'ph ph-calculator',
    }

    for tableau in TableauBord.objects.all():
        if tableau.configuration and 'icon' in tableau.configuration:
            old_icon = tableau.configuration['icon']
            if old_icon in icon_mapping:
                tableau.configuration['icon'] = icon_mapping[old_icon]
                tableau.save()


class Migration(migrations.Migration):
    dependencies = [
        ('analytics', '0006_tableaux_bord_predefinis'),
    ]

    operations = [
        migrations.RunPython(
            fix_icons_to_duotone,
            revert_icons
        ),
    ]
