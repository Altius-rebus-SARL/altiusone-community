# fiscalite/migrations/0005_declarationfiscale_devise_tauximposition_regime.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0004_declarationfiscale_regime_not_null'),
        ('core', '0007_mandat_regime_devise_not_null'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='declarationfiscale',
            name='devise',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='declarations_fiscales',
                to='core.devise',
                verbose_name='Devise',
                help_text='Devise de la déclaration fiscale',
            ),
        ),
        migrations.AddField(
            model_name='tauximposition',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='taux_imposition',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
                help_text='Régime fiscal associé',
            ),
        ),
    ]
