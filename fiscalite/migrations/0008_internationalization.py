# fiscalite/migrations/0008_internationalization.py
"""
Make DeclarationFiscale.canton blank=True.
Add DeclarationFiscale.subdivision.
Make TauxImposition.canton blank=True.
Add TauxImposition.subdivision.
Update TauxImposition unique_together.
Extend TYPE_IMPOT_CHOICES.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscalite', '0007_declarationfiscale_devise_not_null'),
    ]

    operations = [
        # DeclarationFiscale: make canton blank=True
        migrations.AlterField(
            model_name='declarationfiscale',
            name='canton',
            field=models.CharField(
                blank=True, max_length=2,
                choices=[
                    ('AG', 'Argovie'), ('AI', 'Appenzell Rhodes-Intérieures'),
                    ('AR', 'Appenzell Rhodes-Extérieures'), ('BE', 'Berne'),
                    ('BL', 'Bâle-Campagne'), ('BS', 'Bâle-Ville'),
                    ('FR', 'Fribourg'), ('GE', 'Genève'),
                    ('GL', 'Glaris'), ('GR', 'Grisons'),
                    ('JU', 'Jura'), ('LU', 'Lucerne'),
                    ('NE', 'Neuchâtel'), ('NW', 'Nidwald'),
                    ('OW', 'Obwald'), ('SG', 'Saint-Gall'),
                    ('SH', 'Schaffhouse'), ('SO', 'Soleure'),
                    ('SZ', 'Schwyz'), ('TG', 'Thurgovie'),
                    ('TI', 'Tessin'), ('UR', 'Uri'),
                    ('VD', 'Vaud'), ('VS', 'Valais'),
                    ('ZG', 'Zoug'), ('ZH', 'Zurich'),
                ],
                help_text='Canton de taxation (Suisse uniquement)',
                verbose_name='Canton',
            ),
        ),
        # DeclarationFiscale: add subdivision
        migrations.AddField(
            model_name='declarationfiscale',
            name='subdivision',
            field=models.CharField(
                blank=True, default='', max_length=100,
                help_text='Région, département ou subdivision fiscale (régimes non-suisses)',
                verbose_name='Subdivision',
            ),
            preserve_default=False,
        ),
        # DeclarationFiscale: extend TYPE_IMPOT_CHOICES
        migrations.AlterField(
            model_name='declarationfiscale',
            name='type_impot',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('IFD', 'Impôt fédéral direct (IFD)'),
                    ('ICC', 'Impôt cantonal et communal (ICC)'),
                    ('FORTUNE', 'Impôt sur la fortune'),
                    ('BENEFICE', 'Impôt sur le bénéfice'),
                    ('CAPITAL', 'Impôt sur le capital'),
                    ('IS_CM', 'Impôt sur les sociétés (IS)'),
                    ('IRPP', 'Impôt sur le revenu des personnes physiques (IRPP)'),
                    ('PATENTE', 'Patente'),
                    ('TPF', 'Taxe sur la propriété foncière (TPF)'),
                    ('IS_SN', 'Impôt sur les sociétés (IS)'),
                    ('IR', 'Impôt sur le revenu (IR)'),
                    ('CFE', 'Contribution foncière des entreprises (CFE)'),
                    ('AUTRE', 'Autre impôt'),
                ],
                help_text="Nature de l'impôt concerné",
                verbose_name="Type d'impôt",
            ),
        ),
        # TauxImposition: make canton blank=True
        migrations.AlterField(
            model_name='tauximposition',
            name='canton',
            field=models.CharField(
                blank=True, max_length=2,
                choices=[
                    ('AG', 'Argovie'), ('AI', 'Appenzell Rhodes-Intérieures'),
                    ('AR', 'Appenzell Rhodes-Extérieures'), ('BE', 'Berne'),
                    ('BL', 'Bâle-Campagne'), ('BS', 'Bâle-Ville'),
                    ('FR', 'Fribourg'), ('GE', 'Genève'),
                    ('GL', 'Glaris'), ('GR', 'Grisons'),
                    ('JU', 'Jura'), ('LU', 'Lucerne'),
                    ('NE', 'Neuchâtel'), ('NW', 'Nidwald'),
                    ('OW', 'Obwald'), ('SG', 'Saint-Gall'),
                    ('SH', 'Schaffhouse'), ('SO', 'Soleure'),
                    ('SZ', 'Schwyz'), ('TG', 'Thurgovie'),
                    ('TI', 'Tessin'), ('UR', 'Uri'),
                    ('VD', 'Vaud'), ('VS', 'Valais'),
                    ('ZG', 'Zoug'), ('ZH', 'Zurich'),
                ],
                help_text='Canton suisse concerné (Suisse uniquement)',
                verbose_name='Canton',
            ),
        ),
        # TauxImposition: add subdivision
        migrations.AddField(
            model_name='tauximposition',
            name='subdivision',
            field=models.CharField(
                blank=True, default='', max_length=100,
                help_text='Région ou subdivision fiscale (régimes non-suisses)',
                verbose_name='Subdivision',
            ),
            preserve_default=False,
        ),
        # TauxImposition: update unique_together
        migrations.AlterUniqueTogether(
            name='tauximposition',
            unique_together={('canton', 'commune', 'subdivision', 'type_impot', 'annee')},
        ),
    ]
