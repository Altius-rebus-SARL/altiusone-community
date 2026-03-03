# facturation/management/commands/generer_facture_test.py
"""
Commande Django pour générer des factures de test avec plusieurs pages.

Usage:
    python manage.py generer_facture_test --lignes 50  # Facture avec 50 lignes
    python manage.py generer_facture_test --lignes 30 --qr-bill  # Avec QR-Bill
    python manage.py generer_facture_test --pages 3  # Environ 3 pages
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Génère une facture de test avec plusieurs lignes pour tester la pagination PDF'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lignes',
            type=int,
            default=30,
            help='Nombre de lignes de facture à créer (default: 30)'
        )
        parser.add_argument(
            '--pages',
            type=int,
            help='Nombre approximatif de pages souhaitées (override --lignes, ~20 lignes/page)'
        )
        parser.add_argument(
            '--qr-bill',
            action='store_true',
            help='Générer le PDF avec QR-Bill suisse'
        )
        parser.add_argument(
            '--iban',
            type=str,
            default='CH93 0076 2011 6238 5295 7',
            help='IBAN pour le QR-Bill (default: CH93 0076 2011 6238 5295 7)'
        )
        parser.add_argument(
            '--mandat-id',
            type=str,
            help='UUID du mandat à utiliser (sinon prend le premier disponible)'
        )
        parser.add_argument(
            '--client-id',
            type=str,
            help='UUID du client facturé (sinon prend le premier disponible)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait créé sans créer réellement'
        )

    def handle(self, *args, **options):
        from facturation.models import Facture, LigneFacture
        from core.models import Mandat, Client, User

        nb_lignes = options['lignes']
        if options['pages']:
            # Environ 20 lignes par page
            nb_lignes = options['pages'] * 20

        avec_qr_bill = options['qr_bill']
        iban = options['iban'].replace(' ', '')
        dry_run = options['dry_run']

        self.stdout.write(self.style.NOTICE(
            f"Création d'une facture de test avec {nb_lignes} lignes..."
        ))

        # Trouver un mandat
        if options['mandat_id']:
            try:
                mandat = Mandat.objects.get(pk=options['mandat_id'])
            except Mandat.DoesNotExist:
                raise CommandError(f"Mandat {options['mandat_id']} non trouvé")
        else:
            mandat = Mandat.objects.filter(is_active=True).first()
            if not mandat:
                raise CommandError(
                    "Aucun mandat actif trouvé. Créez d'abord un mandat ou spécifiez --mandat-id"
                )

        # Trouver un client à facturer
        if options['client_id']:
            try:
                client = Client.objects.get(pk=options['client_id'])
            except Client.DoesNotExist:
                raise CommandError(f"Client {options['client_id']} non trouvé")
        else:
            # Prendre un client différent du client du mandat si possible
            client = Client.objects.filter(is_active=True).exclude(pk=mandat.client_id).first()
            if not client:
                client = mandat.client  # Fallback sur le même client

        # Trouver un utilisateur pour created_by
        user = User.objects.filter(is_active=True, is_staff=True).first()
        if not user:
            user = User.objects.filter(is_active=True).first()

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN - Aucune donnée créée ==="))
            self.stdout.write(f"Mandat: {mandat}")
            self.stdout.write(f"Client facturé: {client}")
            self.stdout.write(f"Nombre de lignes: {nb_lignes}")
            self.stdout.write(f"Avec QR-Bill: {avec_qr_bill}")
            self.stdout.write(f"IBAN: {iban}")
            return

        # Données de test pour les lignes
        prestations_test = [
            ("Analyse et conseil stratégique", 150.00, "heure"),
            ("Développement application web", 120.00, "heure"),
            ("Maintenance système informatique", 95.00, "heure"),
            ("Formation utilisateurs", 180.00, "heure"),
            ("Audit de sécurité", 200.00, "jour"),
            ("Rédaction documentation technique", 80.00, "heure"),
            ("Support technique niveau 2", 110.00, "heure"),
            ("Intégration API externe", 130.00, "heure"),
            ("Optimisation base de données", 140.00, "heure"),
            ("Migration de données", 160.00, "heure"),
            ("Conception UX/UI", 125.00, "heure"),
            ("Tests et validation", 100.00, "heure"),
            ("Déploiement production", 150.00, "forfait"),
            ("Sauvegarde et restauration", 90.00, "heure"),
            ("Configuration serveur", 110.00, "heure"),
            ("Révision comptable mensuelle", 250.00, "forfait"),
            ("Déclaration TVA trimestrielle", 180.00, "forfait"),
            ("Établissement des salaires", 45.00, "employé"),
            ("Clôture annuelle", 500.00, "forfait"),
            ("Conseil fiscal", 200.00, "heure"),
        ]

        try:
            with transaction.atomic():
                # Créer la facture
                facture = Facture(
                    mandat=mandat,
                    client=client,
                    date_emission=date.today(),
                    date_echeance=date.today() + timedelta(days=30),
                    date_service_debut=date.today() - timedelta(days=30),
                    date_service_fin=date.today(),
                    statut='BROUILLON',
                    introduction=f"Facture de test générée automatiquement avec {nb_lignes} lignes pour tester la pagination PDF.",
                    conclusion="Merci de votre confiance. Cette facture est un test.",
                    conditions_paiement="Payable dans les 30 jours. Passé ce délai, un intérêt de 5% sera appliqué.",
                    creee_par=user,
                )

                # Ajouter l'IBAN pour le QR-Bill
                if avec_qr_bill:
                    facture.qr_iban = iban

                facture.save()

                self.stdout.write(f"Facture créée: {facture.numero_facture}")

                # Créer les lignes
                montant_total_ht = Decimal('0')
                montant_total_tva = Decimal('0')

                for i in range(nb_lignes):
                    # Choisir une prestation aléatoire
                    desc, prix_base, unite = random.choice(prestations_test)

                    # Varier un peu les données
                    quantite = Decimal(str(round(random.uniform(0.5, 8.0), 2)))
                    prix_unitaire = Decimal(str(prix_base)) * Decimal(str(round(random.uniform(0.9, 1.1), 2)))
                    prix_unitaire = prix_unitaire.quantize(Decimal('0.01'))
                    taux_tva = Decimal('8.1') if random.random() > 0.2 else Decimal('2.6')

                    montant_ht = (quantite * prix_unitaire).quantize(Decimal('0.01'))
                    montant_tva = (montant_ht * taux_tva / 100).quantize(Decimal('0.01'))

                    ligne = LigneFacture(
                        facture=facture,
                        ordre=i + 1,
                        description=f"{desc} - Intervention #{i+1}",
                        quantite=quantite,
                        unite=unite,
                        prix_unitaire_ht=prix_unitaire,
                        taux_tva=taux_tva,
                        montant_ht=montant_ht,
                        montant_tva=montant_tva,
                    )
                    ligne.save()

                    montant_total_ht += montant_ht
                    montant_total_tva += montant_tva

                # Mettre à jour les totaux de la facture
                facture.montant_ht = montant_total_ht
                facture.montant_tva = montant_total_tva
                facture.montant_ttc = montant_total_ht + montant_total_tva
                facture.montant_restant = facture.montant_ttc
                facture.save()

                self.stdout.write(self.style.SUCCESS(
                    f"✓ {nb_lignes} lignes créées"
                ))
                self.stdout.write(f"  Montant HT: {facture.montant_ht} CHF")
                self.stdout.write(f"  Montant TVA: {facture.montant_tva} CHF")
                self.stdout.write(f"  Montant TTC: {facture.montant_ttc} CHF")

                # Générer le PDF
                self.stdout.write(self.style.NOTICE("Génération du PDF..."))

                try:
                    fichier_pdf = facture.generer_pdf(avec_qr_bill=avec_qr_bill)
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ PDF généré: {fichier_pdf.name}"
                    ))

                    if avec_qr_bill:
                        self.stdout.write(self.style.SUCCESS("✓ QR-Bill inclus"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"✗ Erreur génération PDF: {e}"
                    ))

                # Résumé
                self.stdout.write("")
                self.stdout.write(self.style.SUCCESS("=" * 50))
                self.stdout.write(self.style.SUCCESS("FACTURE DE TEST CRÉÉE AVEC SUCCÈS"))
                self.stdout.write(self.style.SUCCESS("=" * 50))
                self.stdout.write(f"Numéro: {facture.numero_facture}")
                self.stdout.write(f"ID: {facture.pk}")
                self.stdout.write(f"Lignes: {nb_lignes}")
                self.stdout.write(f"Pages estimées: {max(1, nb_lignes // 20)}")
                self.stdout.write(f"URL: /fr/facturation/factures/{facture.pk}/")
                self.stdout.write("")
                self.stdout.write("Pour télécharger le PDF:")
                self.stdout.write(f"  Standard: /fr/facturation/factures/{facture.pk}/generer-pdf/")
                self.stdout.write(f"  QR-Bill:  /fr/facturation/factures/{facture.pk}/generer-pdf/?qr_bill=1")

        except Exception as e:
            raise CommandError(f"Erreur lors de la création: {e}")
