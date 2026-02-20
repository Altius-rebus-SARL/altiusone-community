# tva/migrations/0004_regime_not_null.py
# Make regime FK non-nullable on TauxTVA and CodeTVA
# ConfigurationTVA.regime stays nullable (mandats without TVA config)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tva', '0003_assign_swiss_regime'),
    ]

    operations = [
        # TauxTVA.regime: null=False
        migrations.AlterField(
            model_name='tauxtva',
            name='regime',
            field=models.ForeignKey(
                help_text='Régime fiscal auquel appartient ce taux',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='taux',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),

        # CodeTVA.regime: null=False
        migrations.AlterField(
            model_name='codetva',
            name='regime',
            field=models.ForeignKey(
                help_text='Régime fiscal auquel appartient ce code',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='codes',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),
    ]
