# Generated manually for multi-model support
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modelforms', '0001_initial'),
    ]

    operations = [
        # 1. First, remove the old unique_together constraint
        migrations.AlterUniqueTogether(
            name='modelfieldmapping',
            unique_together=set(),
        ),

        # 2. Add new fields to FormConfiguration
        migrations.AddField(
            model_name='formconfiguration',
            name='is_multi_model',
            field=models.BooleanField(default=False, help_text='Si coché, le formulaire peut collecter des données de plusieurs modèles', verbose_name='Formulaire multi-modèles'),
        ),
        migrations.AddField(
            model_name='formconfiguration',
            name='source_models',
            field=models.JSONField(blank=True, default=list, help_text='\n        Liste des modèles utilisés dans ce formulaire.\n        Format: ["core.Client", "tva.Declaration", "salaires.Employe"]\n        ', verbose_name='Modèles sources'),
        ),

        # 3. Make target_model optional
        migrations.AlterField(
            model_name='formconfiguration',
            name='target_model',
            field=models.CharField(blank=True, db_index=True, help_text='Modèle principal pour création (optionnel pour formulaires multi-modèles)', max_length=100, verbose_name='Modèle principal'),
        ),

        # 4. Add source_model field to ModelFieldMapping
        migrations.AddField(
            model_name='modelfieldmapping',
            name='source_model',
            field=models.CharField(default='', help_text="Modèle Django d'où provient le champ (ex: core.Client, tva.Declaration)", max_length=100, verbose_name='Modèle source'),
        ),

        # 5. Rename model_path to field_path
        migrations.RenameField(
            model_name='modelfieldmapping',
            old_name='model_path',
            new_name='field_path',
        ),

        # 6. Update field_path help_text
        migrations.AlterField(
            model_name='modelfieldmapping',
            name='field_path',
            field=models.CharField(blank=True, help_text='Pour les champs imbriqués via relation: adresse_siege.rue', max_length=200, verbose_name='Chemin du champ'),
        ),

        # 7. Add new unique_together constraint with source_model
        migrations.AlterUniqueTogether(
            name='modelfieldmapping',
            unique_together={('form_config', 'source_model', 'field_name', 'field_path')},
        ),
    ]
