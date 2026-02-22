# facturation/migrations/0006_lignefacture_taux_code_tva.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0005_facture_devise_not_null'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lignefacture',
            name='taux_tva_ref',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lignes_facture',
                to='tva.tauxtva',
                verbose_name='Taux TVA (référence)',
                help_text='Référence vers le taux TVA du régime fiscal',
            ),
        ),
        migrations.AddField(
            model_name='lignefacture',
            name='code_tva',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lignes_facture',
                to='tva.codetva',
                verbose_name='Code TVA',
                help_text='Code TVA applicable',
            ),
        ),
    ]
