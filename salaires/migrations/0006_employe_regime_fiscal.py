# salaires/migrations/0006_employe_regime_fiscal.py
"""
Add regime_fiscal FK to Employe (nullable).
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0005_alter_employe_salaire_brut_mensuel'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employe',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Régime fiscal pour le calcul des charges sociales',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employes',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
            ),
        ),
    ]
