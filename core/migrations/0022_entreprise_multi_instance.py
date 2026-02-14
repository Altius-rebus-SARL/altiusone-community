"""
Migration: Entreprise multi-instance.

- Ajoute est_defaut sur Entreprise + UniqueConstraint
- Ajoute entreprise FK + logo sur Client
- Ajoute entreprise FK sur CompteBancaire
- Remplace unique_compte_principal par unique_compte_principal_par_entreprise
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_modele_document_pdf'),
    ]

    operations = [
        # 1. Ajouter est_defaut sur Entreprise
        migrations.AddField(
            model_name='entreprise',
            name='est_defaut',
            field=models.BooleanField(
                default=False,
                help_text="Entreprise utilisée par défaut (une seule autorisée)",
                verbose_name='Entreprise par défaut',
            ),
        ),
        # 2. UniqueConstraint sur est_defaut
        migrations.AddConstraint(
            model_name='entreprise',
            constraint=models.UniqueConstraint(
                condition=models.Q(('est_defaut', True)),
                fields=('est_defaut',),
                name='unique_entreprise_defaut',
            ),
        ),
        # 3. Ajouter entreprise FK nullable sur Client
        migrations.AddField(
            model_name='client',
            name='entreprise',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='clients',
                to='core.entreprise',
                verbose_name='Entreprise',
            ),
        ),
        # 4. Ajouter logo ImageField sur Client
        migrations.AddField(
            model_name='client',
            name='logo',
            field=models.ImageField(
                blank=True,
                help_text='Logo du client (utilisé sur les documents)',
                null=True,
                upload_to='clients/logos/',
                verbose_name='Logo',
            ),
        ),
        # 5. Ajouter entreprise FK nullable sur CompteBancaire
        migrations.AddField(
            model_name='comptebancaire',
            name='entreprise',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='comptes_bancaires',
                to='core.entreprise',
                verbose_name='Entreprise',
            ),
        ),
        # 6. Supprimer ancien constraint unique_compte_principal
        migrations.RemoveConstraint(
            model_name='comptebancaire',
            name='unique_compte_principal',
        ),
        # 7. Ajouter nouveau constraint par entreprise
        migrations.AddConstraint(
            model_name='comptebancaire',
            constraint=models.UniqueConstraint(
                condition=models.Q(('est_compte_principal', True)),
                fields=('entreprise', 'est_compte_principal'),
                name='unique_compte_principal_par_entreprise',
            ),
        ),
    ]
