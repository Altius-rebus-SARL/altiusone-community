# facturation/migrations/0007_prestation_taux_tva_ref.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0006_lignefacture_taux_code_tva'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='prestation',
            name='taux_tva_ref',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='prestations',
                to='tva.tauxtva',
                verbose_name='Taux TVA (référence)',
                help_text='Référence vers le taux TVA du régime fiscal',
            ),
        ),
    ]
