# Generated migration for compte_produit on LigneFacture
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0018_prestation_types_mandats_m2m'),
        ('comptabilite', '0009_typepiececomptable_dossier_classement'),
    ]

    operations = [
        migrations.AddField(
            model_name='lignefacture',
            name='compte_produit',
            field=models.ForeignKey(
                blank=True,
                help_text='Compte comptable de produit (override la prestation)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lignes_facture',
                to='comptabilite.compte',
                verbose_name='Compte de produit',
            ),
        ),
    ]
