# Migration: extend TYPE_IMPOT_CHOICES + update unique_together
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0009_alter_correctionfiscale_montant_comptable_and_more'),
        ('tva', '0001_initial'),
    ]

    operations = [
        # Drop old unique_together first
        migrations.AlterUniqueTogether(
            name='tauximposition',
            unique_together=set(),
        ),
        # Extend type_impot max_length + choices
        migrations.AlterField(
            model_name='tauximposition',
            name='type_impot',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('IFD_BENEFICE', 'IFD Bénéfice'),
                    ('ICC_BENEFICE', 'ICC Bénéfice'),
                    ('ICC_CAPITAL', 'ICC Capital'),
                    ('IS_CM', 'Impôt sur les sociétés (IS)'),
                    ('IRPP', 'Impôt sur le revenu (IRPP)'),
                    ('PATENTE', 'Patente'),
                    ('TPF', 'Taxe propriété foncière (TPF)'),
                    ('IS_SN', 'Impôt sur les sociétés (IS)'),
                    ('IR', 'Impôt sur le revenu (IR)'),
                    ('CFE', 'Contribution foncière entreprises (CFE)'),
                    ('AUTRE', 'Autre impôt'),
                ],
                help_text="Nature de l'impôt (IFD, ICC bénéfice ou capital)",
                verbose_name="Type d'impôt",
            ),
        ),
        # Set new unique_together including regime_fiscal
        migrations.AlterUniqueTogether(
            name='tauximposition',
            unique_together={('regime_fiscal', 'canton', 'commune', 'subdivision', 'type_impot', 'annee')},
        ),
    ]
