# fiscalite/migrations/0004_declarationfiscale_regime_not_null.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0003_populate_declarationfiscale_regime'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='declarationfiscale',
            name='regime_fiscal',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='declarations_fiscales',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
                help_text='Régime fiscal applicable',
            ),
        ),
    ]
