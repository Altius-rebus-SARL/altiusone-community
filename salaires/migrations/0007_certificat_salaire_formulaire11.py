# Generated migration for CertificatSalaire - Formulaire 11 suisse

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0006_add_employe_user_link'),
    ]

    operations = [
        # === Section F-G: Occupation et transport ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='type_occupation',
            field=models.CharField(
                choices=[
                    ('PLEIN_TEMPS', 'Plein temps'),
                    ('TEMPS_PARTIEL', 'Temps partiel'),
                    ('HORAIRE', "Travail à l'heure"),
                ],
                default='PLEIN_TEMPS',
                help_text='Section F: Type de rapport de travail',
                max_length=20,
                verbose_name="Type d'occupation",
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='taux_occupation',
            field=models.DecimalField(
                decimal_places=2,
                default=100,
                help_text='Section F: Taux d\'occupation en pourcentage',
                max_digits=5,
                verbose_name="Taux d'occupation (%)",
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='transport_public_disponible',
            field=models.BooleanField(
                default=True,
                help_text='Section G: Des transports publics sont disponibles pour le trajet domicile-travail',
                verbose_name='Transport public disponible',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='transport_gratuit_fourni',
            field=models.BooleanField(
                default=False,
                help_text="Section G: L'employeur fournit un transport gratuit",
                verbose_name='Transport gratuit fourni',
            ),
        ),

        # === Chiffre 1: Salaire ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_1_salaire',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Salaire, rente (y.c. allocations pour perte de gain)',
                max_digits=12,
                verbose_name='1. Salaire / Rente',
            ),
        ),

        # === Chiffre 2: Prestations en nature ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_2_1_repas',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Valeur des repas gratuits (CHF 180/mois midi, CHF 180/mois soir)',
                max_digits=10,
                verbose_name='2.1 Repas',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='repas_midi_gratuit',
            field=models.BooleanField(
                default=False,
                help_text="Case 2.1: L'employé bénéficie de repas de midi gratuits",
                verbose_name='Repas de midi gratuit',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='repas_soir_gratuit',
            field=models.BooleanField(
                default=False,
                help_text="Case 2.1: L'employé bénéficie de repas du soir gratuits",
                verbose_name='Repas du soir gratuit',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_2_2_voiture',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Valeur de l'utilisation privée du véhicule (0.9% par mois du prix d'achat)",
                max_digits=10,
                verbose_name='2.2 Véhicule de service',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='voiture_disponible',
            field=models.BooleanField(
                default=False,
                help_text='Case 2.2: Un véhicule de service est mis à disposition pour usage privé',
                verbose_name='Voiture de service disponible',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='voiture_prix_achat',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Prix d'achat du véhicule (hors TVA) pour calcul de la part privée",
                max_digits=12,
                verbose_name="Prix d'achat du véhicule",
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_2_3_autres',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Autres prestations en nature (logement, etc.)',
                max_digits=10,
                verbose_name='2.3 Autres prestations en nature',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='autres_prestations_nature_detail',
            field=models.TextField(
                blank=True,
                help_text='Description des autres prestations en nature',
                verbose_name='Détail autres prestations',
            ),
        ),

        # === Chiffre 3: Prestations irrégulières ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_3_irregulier',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Bonus, gratifications, 13ème salaire, indemnités de vacances non prises',
                max_digits=12,
                verbose_name='3. Prestations irrégulières',
            ),
        ),

        # === Chiffre 4: Prestations en capital ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_4_capital',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Indemnités de départ, prestations provenant d'institutions de prévoyance",
                max_digits=12,
                verbose_name='4. Prestations en capital',
            ),
        ),

        # === Chiffre 5: Participations ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_5_participations',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Actions de collaborateurs, options, etc.',
                max_digits=12,
                verbose_name='5. Droits de participation',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='participations_detail',
            field=models.TextField(
                blank=True,
                help_text='Description des participations (type, nombre, valeur)',
                verbose_name='Détail participations',
            ),
        ),

        # === Chiffre 6: Conseil d'administration ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_6_ca',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Indemnités de membre d'organe de direction",
                max_digits=12,
                verbose_name="6. Conseil d'administration",
            ),
        ),

        # === Chiffre 7: Autres prestations ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_7_autres',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Toutes autres prestations non mentionnées ailleurs',
                max_digits=12,
                verbose_name='7. Autres prestations',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='autres_prestations_detail',
            field=models.TextField(
                blank=True,
                help_text='Description des autres prestations',
                verbose_name='Détail autres prestations',
            ),
        ),

        # === Chiffre 8: Total brut (calculé) ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_8_total_brut',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Total des chiffres 1 à 7 (calculé automatiquement)',
                max_digits=12,
                verbose_name='8. Salaire brut total',
            ),
        ),

        # === Chiffre 9: Cotisations AVS/AI/APG/AC/AANP ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_9_cotisations',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Cotisations employé aux assurances sociales obligatoires',
                max_digits=10,
                verbose_name='9. Cotisations AVS/AI/APG/AC/AANP',
            ),
        ),

        # === Chiffre 10: Prévoyance professionnelle ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_10_1_lpp_ordinaire',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Cotisations ordinaires à la prévoyance professionnelle',
                max_digits=10,
                verbose_name='10.1 LPP cotisations ordinaires',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_10_2_lpp_rachat',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Rachats d'années de cotisation LPP",
                max_digits=10,
                verbose_name='10.2 LPP rachats',
            ),
        ),

        # === Chiffre 11: Salaire net (calculé) ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_11_net',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Chiffre 8 moins chiffres 9 et 10 (calculé automatiquement)',
                max_digits=12,
                verbose_name='11. Salaire net',
            ),
        ),

        # === Chiffre 12: Frais de transport ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_12_transport',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Frais de déplacement domicile-lieu de travail remboursés',
                max_digits=10,
                verbose_name='12. Frais effectifs de transport',
            ),
        ),

        # === Chiffre 13: Frais de repas et nuitées ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_13_1_1_repas_effectif',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Frais de repas effectifs pour travail en dehors',
                max_digits=10,
                verbose_name='13.1.1 Frais de repas effectifs',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_13_1_2_repas_forfait',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Indemnité forfaitaire pour repas de midi',
                max_digits=10,
                verbose_name='13.1.2 Frais de repas forfaitaires',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_13_2_nuitees',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Frais d\'hébergement pour déplacements professionnels',
                max_digits=10,
                verbose_name='13.2 Nuitées',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_13_3_repas_externes',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Frais de repas lors de déplacements externes',
                max_digits=10,
                verbose_name="13.3 Repas à l'extérieur",
            ),
        ),

        # === Chiffre 14: Autres frais ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_14_autres_frais',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Autres frais professionnels remboursés',
                max_digits=10,
                verbose_name='14. Autres frais',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='autres_frais_detail',
            field=models.TextField(
                blank=True,
                help_text='Description des autres frais professionnels',
                verbose_name='Détail autres frais',
            ),
        ),

        # === Chiffre 15: Jours de travail avec déplacement ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='chiffre_15_jours_transport',
            field=models.IntegerField(
                default=0,
                help_text='Nombre de jours de travail avec déplacement domicile-travail',
                verbose_name='15. Jours avec déplacement',
            ),
        ),

        # === Section I: Remarques ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='remarques',
            field=models.TextField(
                blank=True,
                help_text='Section I: Remarques diverses (expatriés, détachés, etc.)',
                verbose_name='Remarques',
            ),
        ),

        # === Signature ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='lieu_signature',
            field=models.CharField(
                blank=True,
                help_text='Lieu où le certificat est signé',
                max_length=100,
                verbose_name='Lieu de signature',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='date_signature',
            field=models.DateField(
                blank=True,
                help_text='Date de signature du certificat',
                null=True,
                verbose_name='Date de signature',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='nom_signataire',
            field=models.CharField(
                blank=True,
                help_text='Nom de la personne autorisée à signer',
                max_length=200,
                verbose_name='Nom du signataire',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='telephone_signataire',
            field=models.CharField(
                blank=True,
                help_text='Numéro de téléphone pour questions',
                max_length=50,
                verbose_name='Téléphone du signataire',
            ),
        ),
        migrations.AddField(
            model_name='certificatsalaire',
            name='est_signe',
            field=models.BooleanField(
                default=False,
                help_text='Indique si le certificat a été signé',
                verbose_name='Signé',
            ),
        ),

        # === Statut ===
        migrations.AddField(
            model_name='certificatsalaire',
            name='statut',
            field=models.CharField(
                choices=[
                    ('BROUILLON', 'Brouillon'),
                    ('CALCULE', 'Calculé'),
                    ('VERIFIE', 'Vérifié'),
                    ('SIGNE', 'Signé'),
                    ('ENVOYE', 'Envoyé'),
                ],
                default='BROUILLON',
                help_text='État actuel du certificat',
                max_length=20,
                verbose_name='Statut',
            ),
        ),
    ]
