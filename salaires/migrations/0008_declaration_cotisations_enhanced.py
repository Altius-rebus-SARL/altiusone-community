# Generated migration for enhanced DeclarationCotisations
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0007_certificat_salaire_formulaire11'),
    ]

    operations = [
        # Add new fields to DeclarationCotisations
        migrations.AddField(
            model_name='declarationcotisations',
            name='nom_caisse',
            field=models.CharField(blank=True, help_text='Dénomination officielle de la caisse', max_length=200, verbose_name='Nom de la caisse'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='numero_affilie',
            field=models.CharField(blank=True, help_text="Numéro d'affiliation de l'employeur", max_length=50, verbose_name='N° affilié'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='numero_contrat',
            field=models.CharField(blank=True, help_text='Numéro de contrat ou police', max_length=50, verbose_name='N° contrat/police'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='periode_type',
            field=models.CharField(choices=[('MENSUEL', 'Mensuelle'), ('TRIMESTRIEL', 'Trimestrielle'), ('ANNUEL', 'Annuelle')], default='MENSUEL', help_text='Fréquence de déclaration', max_length=15, verbose_name='Type de période'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='annee',
            field=models.IntegerField(default=2025, help_text='Année de la déclaration', verbose_name='Année'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='mois',
            field=models.IntegerField(blank=True, help_text='Mois (1-12) pour déclaration mensuelle', null=True, verbose_name='Mois'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='trimestre',
            field=models.IntegerField(blank=True, help_text='Trimestre (1-4) pour déclaration trimestrielle', null=True, verbose_name='Trimestre'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='nombre_employes',
            field=models.IntegerField(default=0, help_text="Nombre d'employés déclarés", verbose_name="Nombre d'employés"),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='masse_salariale_brute',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Total des salaires bruts en CHF', max_digits=15, verbose_name='Masse salariale brute'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='masse_salariale_soumise',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Total des salaires soumis à cotisation en CHF', max_digits=15, verbose_name='Masse salariale soumise'),
        ),
        # AVS cotisations
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_avs',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Cotisation AVS (employeur + employé)', max_digits=12, verbose_name='AVS'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_ai',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Cotisation AI (employeur + employé)', max_digits=12, verbose_name='AI'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_apg',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Cotisation APG (employeur + employé)', max_digits=12, verbose_name='APG'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_ac',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Cotisation AC (employeur + employé)', max_digits=12, verbose_name='AC'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_ac_supp',
            field=models.DecimalField(decimal_places=2, default=0, help_text="AC sur salaires > 148'200 CHF", max_digits=12, verbose_name='AC supplémentaire'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='frais_administration',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Frais de gestion de la caisse', max_digits=12, verbose_name="Frais d'administration"),
        ),
        # LPP cotisations
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_lpp_employe',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Part employé LPP', max_digits=12, verbose_name='LPP employé'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_lpp_employeur',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Part employeur LPP', max_digits=12, verbose_name='LPP employeur'),
        ),
        # LAA cotisations
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_laa_pro',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Prime accidents professionnels', max_digits=12, verbose_name='LAA professionnelle'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_laa_non_pro',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Prime accidents non professionnels', max_digits=12, verbose_name='LAA non professionnelle'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_laac',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Assurance accidents complémentaire', max_digits=12, verbose_name='LAAC complémentaire'),
        ),
        # AF cotisations
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_af',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Cotisation allocations familiales', max_digits=12, verbose_name='Allocations familiales'),
        ),
        # IJM cotisations
        migrations.AddField(
            model_name='declarationcotisations',
            name='cotisation_ijm',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Prime indemnités journalières maladie', max_digits=12, verbose_name='IJM'),
        ),
        # Totaux
        migrations.AddField(
            model_name='declarationcotisations',
            name='total_cotisations_employe',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Total des cotisations part employé', max_digits=12, verbose_name='Total part employé'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='total_cotisations_employeur',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Total des cotisations part employeur', max_digits=12, verbose_name='Total part employeur'),
        ),
        # Statut et dates
        migrations.AddField(
            model_name='declarationcotisations',
            name='statut',
            field=models.CharField(choices=[('BROUILLON', 'Brouillon'), ('CALCULEE', 'Calculée'), ('VERIFIEE', 'Vérifiée'), ('TRANSMISE', 'Transmise'), ('PAYEE', 'Payée')], db_index=True, default='BROUILLON', help_text='État de la déclaration', max_length=15, verbose_name='Statut'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='date_transmission',
            field=models.DateField(blank=True, help_text="Date d'envoi à la caisse", null=True, verbose_name='Date de transmission'),
        ),
        # Références paiement
        migrations.AddField(
            model_name='declarationcotisations',
            name='numero_bvr',
            field=models.CharField(blank=True, help_text='Numéro de référence de paiement', max_length=50, verbose_name='N° BVR/QR'),
        ),
        migrations.AddField(
            model_name='declarationcotisations',
            name='iban_caisse',
            field=models.CharField(blank=True, help_text='IBAN pour le paiement', max_length=34, verbose_name='IBAN caisse'),
        ),
        # Remarques
        migrations.AddField(
            model_name='declarationcotisations',
            name='remarques',
            field=models.TextField(blank=True, help_text='Notes et observations', verbose_name='Remarques'),
        ),
        # Update existing fields
        migrations.AlterField(
            model_name='declarationcotisations',
            name='organisme',
            field=models.CharField(choices=[('AVS', 'Caisse AVS/AI/APG/AC'), ('LPP', 'Institution de prévoyance LPP'), ('LAA', 'Assurance accidents LAA/LAAC'), ('AF', 'Caisse allocations familiales'), ('IJM', 'Assurance indemnités journalières maladie')], help_text='Organisme destinataire de la déclaration', max_length=10, verbose_name='Organisme'),
        ),
        migrations.AlterField(
            model_name='declarationcotisations',
            name='date_declaration',
            field=models.DateField(blank=True, help_text='Date de création de la déclaration', null=True, verbose_name='Date de déclaration'),
        ),
        migrations.AlterField(
            model_name='declarationcotisations',
            name='date_echeance',
            field=models.DateField(blank=True, help_text='Date limite de paiement', null=True, verbose_name="Date d'échéance"),
        ),
        migrations.AlterField(
            model_name='declarationcotisations',
            name='montant_cotisations',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Total des cotisations dues en CHF', max_digits=12, verbose_name='Montant total'),
        ),
        # Add related_name to mandat
        migrations.AlterField(
            model_name='declarationcotisations',
            name='mandat',
            field=models.ForeignKey(help_text='Mandat employeur concerné', on_delete=django.db.models.deletion.CASCADE, related_name='declarations_cotisations', to='core.mandat', verbose_name='Mandat'),
        ),
        # Create DeclarationCotisationsLigne model
        migrations.CreateModel(
            name='DeclarationCotisationsLigne',
            fields=[
                ('id', models.UUIDField(default=None, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('salaire_brut', models.DecimalField(decimal_places=2, default=0, help_text='Total salaire brut sur la période', max_digits=12, verbose_name='Salaire brut')),
                ('salaire_soumis', models.DecimalField(decimal_places=2, default=0, help_text='Salaire soumis à cotisation', max_digits=12, verbose_name='Salaire soumis')),
                ('cotisation_employe', models.DecimalField(decimal_places=2, default=0, help_text='Part employé', max_digits=10, verbose_name='Cotisation employé')),
                ('cotisation_employeur', models.DecimalField(decimal_places=2, default=0, help_text='Part employeur', max_digits=10, verbose_name='Cotisation employeur')),
                ('cotisation_totale', models.DecimalField(decimal_places=2, default=0, help_text='Total (employé + employeur)', max_digits=10, verbose_name='Cotisation totale')),
                ('declaration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lignes', to='salaires.declarationcotisations', verbose_name='Déclaration')),
                ('employe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lignes_declarations', to='salaires.employe', verbose_name='Employé')),
            ],
            options={
                'verbose_name': 'Ligne de déclaration',
                'verbose_name_plural': 'Lignes de déclaration',
                'db_table': 'declarations_cotisations_lignes',
                'unique_together': {('declaration', 'employe')},
            },
        ),
        # Remove old masse_salariale field if it exists
        migrations.RemoveField(
            model_name='declarationcotisations',
            name='masse_salariale',
        ),
    ]
