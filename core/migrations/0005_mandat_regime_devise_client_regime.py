# core/migrations/0005_mandat_regime_devise_client_regime.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_tiers'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='mandat',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='mandats',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),
        migrations.AddField(
            model_name='mandat',
            name='devise',
            field=models.ForeignKey(
                blank=True, null=True,
                db_column='devise_mandat',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='mandats',
                to='core.devise',
                verbose_name='Devise',
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='regime_fiscal_defaut',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='clients',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal par défaut',
            ),
        ),
    ]
