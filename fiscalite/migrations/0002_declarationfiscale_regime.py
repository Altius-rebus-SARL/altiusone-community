# fiscalite/migrations/0002_declarationfiscale_regime.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0001_initial'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='declarationfiscale',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='declarations_fiscales',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
                help_text='Régime fiscal applicable',
            ),
        ),
    ]
