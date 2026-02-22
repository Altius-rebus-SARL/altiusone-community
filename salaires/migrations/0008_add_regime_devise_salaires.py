# salaires/migrations/0008_add_regime_devise_salaires.py
"""
Add regime_fiscal and devise FK to TauxCotisation, FicheSalaire,
CertificatSalaire, DeclarationCotisations, CertificatTravail.
Extend TYPE_COTISATION_CHOICES. Remove unique on type_cotisation.
Remove defaults from Employe (nationalite, nombre_heures_semaine, jours_vacances_annuel).
"""
from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0007_populate_employe_regime_fiscal'),
        ('tva', '0002_add_regime_fiscal'),
        ('core', '0001_initial'),
    ]

    operations = [
        # === TauxCotisation ===
        # Remove unique constraint on type_cotisation
        migrations.AlterField(
            model_name='tauxcotisation',
            name='type_cotisation',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('AVS', 'AVS/AI/APG'),
                    ('AC', 'Assurance chômage'),
                    ('AC_SUPP', 'AC supplément (>seuil plafond)'),
                    ('LPP', 'LPP (2e pilier)'),
                    ('LAA', 'LAA Accidents'),
                    ('LAAC', 'LAAC Accidents complémentaire'),
                    ('IJM', 'Indemnités journalières maladie'),
                    ('AF', 'Allocations familiales'),
                    ('CNPS_VIE', 'CNPS Assurance vieillesse'),
                    ('CNPS_AF', 'CNPS Allocations familiales'),
                    ('CNPS_AT', 'CNPS Accidents du travail'),
                    ('CSS', 'CSS Sécurité sociale'),
                    ('IPRES_GEN', 'IPRES Régime général'),
                    ('IPRES_CAD', 'IPRES Régime cadre'),
                    ('IPM', 'IPM Maladie'),
                    ('CFCE', 'CFCE Formation professionnelle'),
                    ('CNPS_CI_RET', 'CNPS-CI Retraite'),
                    ('CNPS_CI_PF', 'CNPS-CI Prestations familiales'),
                    ('CNPS_CI_AT', 'CNPS-CI Accidents du travail'),
                    ('FNE', 'FNE Emploi'),
                    ('AUTRE', 'Autre cotisation'),
                ],
                verbose_name='Type de cotisation',
                help_text='Nature de la cotisation sociale',
            ),
        ),
        # Add regime_fiscal FK (nullable)
        migrations.AddField(
            model_name='tauxcotisation',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='taux_cotisations',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
                help_text='Régime fiscal applicable pour ce taux',
            ),
        ),
        # Add devise FK (nullable)
        migrations.AddField(
            model_name='tauxcotisation',
            name='devise',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='taux_cotisations',
                to='core.devise',
                verbose_name='Devise',
                help_text='Devise des seuils de salaire',
            ),
        ),

        # === FicheSalaire ===
        migrations.AddField(
            model_name='fichesalaire',
            name='devise',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='fiches_salaire',
                to='core.devise',
                verbose_name='Devise',
                help_text='Devise de la fiche de salaire',
            ),
        ),

        # === CertificatSalaire ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='certificats_salaire',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
                help_text='Régime fiscal applicable',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='devise',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='certificats_salaire',
                to='core.devise',
                verbose_name='Devise',
                help_text='Devise du certificat',
            ),
        ),

        # === DeclarationCotisations ===
        migrations.AddField(
            model_name='declarationcotisations',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='declarations_cotisations',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
                help_text='Régime fiscal applicable',
            ),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='devise',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='declarations_cotisations',
                to='core.devise',
                verbose_name='Devise',
                help_text='Devise de la déclaration',
            ),
        ),

        # === CertificatTravail ===
        migrations.AddField(
            model_name='certificattravail',
            name='regime_fiscal',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='certificats_travail',
                to='tva.regimefiscal',
                verbose_name='Régime fiscal',
                help_text='Régime fiscal applicable',
            ),
        ),

        # === Employe defaults removal ===
        migrations.AlterField(
            model_name='employe',
            name='nationalite',
            field=django_countries.fields.CountryField(
                max_length=2,
                verbose_name='Nationalité',
                help_text="Nationalité de l'employé",
            ),
        ),
        migrations.AlterField(
            model_name='employe',
            name='nombre_heures_semaine',
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                verbose_name='Heures par semaine',
                help_text="Nombre d'heures de travail hebdomadaires",
            ),
        ),
        migrations.AlterField(
            model_name='employe',
            name='jours_vacances_annuel',
            field=models.IntegerField(
                verbose_name='Jours de vacances',
                help_text='Nombre de jours de vacances annuels',
            ),
        ),
    ]
