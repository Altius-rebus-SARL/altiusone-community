# core/migrations/0007_mandat_regime_devise_not_null.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_populate_mandat_regime_devise'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mandat',
            name='regime_fiscal',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='mandats',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),
        migrations.AlterField(
            model_name='mandat',
            name='devise',
            field=models.ForeignKey(
                db_column='devise_mandat',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='mandats',
                to='core.devise',
                verbose_name='Devise',
            ),
        ),
    ]
