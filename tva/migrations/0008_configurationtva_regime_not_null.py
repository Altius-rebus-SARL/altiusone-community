# tva/migrations/0008_configurationtva_regime_not_null.py
"""
Make ConfigurationTVA.regime NOT NULL after populating.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tva', '0007_populate_declarationtva_regime_devise'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configurationtva',
            name='regime',
            field=models.ForeignKey(
                help_text='Régime fiscal applicable à ce mandat',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='configurations',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),
    ]
