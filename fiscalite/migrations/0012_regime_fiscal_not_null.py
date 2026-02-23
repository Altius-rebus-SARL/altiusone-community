# Migration: make regime_fiscal NOT NULL
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0011_backfill_regime_fiscal'),
        ('tva', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tauximposition',
            name='regime_fiscal',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='taux_imposition',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
                help_text='Régime fiscal associé',
            ),
        ),
    ]
