# Generated manually to add periodicite_ref to ConfigurationTVA
# tva/migrations/0004_configurationtva_periodicite_ref.py

from django.db import migrations, models
import django.db.models.deletion


def migrate_configurations_periodicite(apps, schema_editor):
    """Migrer les périodicités des configurations TVA vers la table de référence"""
    ConfigurationTVA = apps.get_model('tva', 'ConfigurationTVA')
    Periodicite = apps.get_model('core', 'Periodicite')

    periodicite_cache = {p.code: p for p in Periodicite.objects.all()}

    for config in ConfigurationTVA.objects.all():
        if config.periodicite and config.periodicite in periodicite_cache:
            config.periodicite_ref = periodicite_cache[config.periodicite]
            config.save(update_fields=['periodicite_ref'])


def reverse_configurations(apps, schema_editor):
    """Reverse migration pour configurations TVA"""
    ConfigurationTVA = apps.get_model('tva', 'ConfigurationTVA')

    for config in ConfigurationTVA.objects.select_related('periodicite_ref').all():
        if config.periodicite_ref:
            config.periodicite = config.periodicite_ref.code
            config.save(update_fields=['periodicite'])


class Migration(migrations.Migration):

    dependencies = [
        ('tva', '0003_alter_codetva_created_at_alter_codetva_created_by_and_more'),
        ('core', '0008_add_type_mandat_periodicite_type_facturation'),
    ]

    operations = [
        # 1. Ajouter le champ periodicite_ref à ConfigurationTVA
        migrations.AddField(
            model_name='configurationtva',
            name='periodicite_ref',
            field=models.ForeignKey(
                blank=True,
                help_text='Périodicité de déclaration TVA',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='configurations_tva',
                to='core.periodicite',
                verbose_name='Périodicité'
            ),
        ),

        # 2. Modifier l'ancien champ periodicite pour le rendre optionnel
        migrations.AlterField(
            model_name='configurationtva',
            name='periodicite',
            field=models.CharField(
                blank=True,
                choices=[
                    ('TRIMESTRIEL', 'Trimestriel'),
                    ('SEMESTRIEL', 'Semestriel'),
                ],
                default='TRIMESTRIEL',
                max_length=20,
                verbose_name='Périodicité (ancien)'
            ),
        ),

        # 3. Migrer les données existantes
        migrations.RunPython(migrate_configurations_periodicite, reverse_configurations),
    ]
