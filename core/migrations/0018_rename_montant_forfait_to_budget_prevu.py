# Generated manually — rename montant_forfait → budget_prevu + add budget_reel on Mandat

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_remove_collaborateurfiduciaire_unique_collaborateur_mandat_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='mandat',
            old_name='montant_forfait',
            new_name='budget_prevu',
        ),
        migrations.AlterField(
            model_name='mandat',
            name='budget_prevu',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=15, null=True,
                verbose_name='Budget prévu',
            ),
        ),
        migrations.AddField(
            model_name='mandat',
            name='budget_reel',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=15,
                verbose_name='Budget réel',
            ),
        ),
    ]
