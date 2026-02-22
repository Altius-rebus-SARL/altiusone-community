# core/management/commands/generate_realistic_accounting_data.py
"""
Commande pour générer des données comptables réalistes en quantité suffisante
pour tester toutes les fonctionnalités d'analytics et de reporting.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from faker import Faker
from decimal import Decimal
import random
from datetime import date, timedelta

from core.models import Mandat, ExerciceComptable
from comptabilite.models import (
    PlanComptable,
    TypePlanComptable,
    Compte,
    Journal,
    EcritureComptable,
    PieceComptable,
)
from facturation.models import Facture, LigneFacture, Paiement, Prestation
from salaires.models import Employe, FicheSalaire, TauxCotisation


User = get_user_model()


class Command(BaseCommand):
    help = "Génère des données comptables réalistes pour tester les rapports et analytics"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fake = Faker("fr_CH")

    def add_arguments(self, parser):
        parser.add_argument(
            "--mandats",
            type=int,
            default=10,
            help="Nombre de mandats à enrichir avec des données comptables (défaut: 10)",
        )
        parser.add_argument(
            "--ecritures-par-mandat",
            type=int,
            default=200,
            help="Nombre d'écritures comptables par mandat (défaut: 200)",
        )
        parser.add_argument(
            "--factures-par-mandat",
            type=int,
            default=20,
            help="Nombre de factures par mandat (défaut: 20)",
        )
        parser.add_argument(
            "--employes-par-mandat",
            type=int,
            default=5,
            help="Nombre d'employés par mandat salaires (défaut: 5)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Seed pour reproductibilité",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Nettoyer les écritures existantes avant génération",
        )

    def handle(self, *args, **options):
        Faker.seed(options["seed"])
        random.seed(options["seed"])

        self.stdout.write(
            self.style.WARNING("🏭 Génération de données comptables réalistes...")
        )

        with transaction.atomic():
            # Sélectionner les mandats à enrichir
            mandats = list(
                Mandat.objects.filter(
                    type_mandat__in=["COMPTA", "GLOBAL"]
                ).select_related("client")[:options["mandats"]]
            )

            if not mandats:
                self.stdout.write(
                    self.style.ERROR("❌ Aucun mandat COMPTA ou GLOBAL trouvé. Exécutez d'abord populate_fake_data.")
                )
                return

            self.stdout.write(f"📋 {len(mandats)} mandats sélectionnés")

            if options["clean"]:
                self._clean_accounting_data(mandats)

            # 1. S'assurer que chaque mandat a un plan comptable complet
            self._ensure_complete_chart_of_accounts(mandats)

            # 2. S'assurer que chaque mandat a des journaux
            self._ensure_journals(mandats)

            # 3. Générer les écritures comptables équilibrées
            self._generate_accounting_entries(
                mandats,
                options["ecritures_par_mandat"]
            )

            # 4. Générer des factures avec lignes
            self._generate_invoices(mandats, options["factures_par_mandat"])

            # 5. Générer des paiements
            self._generate_payments()

            # 6. Générer des employés et fiches de salaire
            self._generate_payroll_data(mandats, options["employes_par_mandat"])

            self.stdout.write(self.style.SUCCESS("✅ Données générées avec succès!"))
            self._print_summary()

    def _clean_accounting_data(self, mandats):
        """Nettoie les données comptables existantes"""
        self.stdout.write("🧹 Nettoyage des données existantes...")

        mandat_ids = [m.id for m in mandats]

        EcritureComptable.objects.filter(mandat__in=mandat_ids).delete()
        PieceComptable.objects.filter(mandat__in=mandat_ids).delete()
        Paiement.objects.filter(facture__mandat__in=mandat_ids).delete()
        LigneFacture.objects.filter(facture__mandat__in=mandat_ids).delete()
        Facture.objects.filter(mandat__in=mandat_ids).delete()
        FicheSalaire.objects.filter(employe__mandat__in=mandat_ids).delete()

    def _ensure_complete_chart_of_accounts(self, mandats):
        """S'assure que chaque mandat a un plan comptable complet avec toutes les classes"""
        self.stdout.write("📊 Vérification des plans comptables...")

        # Plan comptable complet avec toutes les classes (1-9)
        comptes_complets = [
            # Classe 1 - Actifs
            ("1000", "Caisse", "ACTIF", 1, True),
            ("1020", "Banque PostFinance", "ACTIF", 1, True),
            ("1021", "Banque UBS", "ACTIF", 1, True),
            ("1100", "Débiteurs clients", "ACTIF", 1, True),
            ("1109", "Provision pour débiteurs douteux", "ACTIF", 1, True),
            ("1170", "Impôt préalable TVA", "ACTIF", 1, True),
            ("1200", "Stock marchandises", "ACTIF", 1, True),
            ("1300", "Actifs transitoires", "ACTIF", 1, True),
            ("1500", "Machines et appareils", "ACTIF", 1, True),
            ("1510", "Mobilier et installations", "ACTIF", 1, True),
            ("1520", "Matériel informatique", "ACTIF", 1, True),
            ("1600", "Immeubles d'exploitation", "ACTIF", 1, True),

            # Classe 2 - Passifs
            ("2000", "Créanciers fournisseurs", "PASSIF", 2, True),
            ("2100", "Banque (passif)", "PASSIF", 2, True),
            ("2200", "TVA due", "PASSIF", 2, True),
            ("2201", "TVA due taux normal", "PASSIF", 2, True),
            ("2202", "TVA due taux réduit", "PASSIF", 2, True),
            ("2270", "Impôts à payer", "PASSIF", 2, True),
            ("2300", "Passifs transitoires", "PASSIF", 2, True),
            ("2400", "Emprunts bancaires", "PASSIF", 2, True),
            ("2500", "Autres dettes à long terme", "PASSIF", 2, True),
            ("2600", "Provisions", "PASSIF", 2, True),

            # Classe 3 - Capitaux propres (pour sociétés)
            ("2800", "Capital-actions", "PASSIF", 2, True),
            ("2850", "Réserve légale issue du capital", "PASSIF", 2, True),
            ("2900", "Réserves libres", "PASSIF", 2, True),
            ("2970", "Report à nouveau", "PASSIF", 2, True),
            ("2979", "Bénéfice / Perte de l'exercice", "PASSIF", 2, True),

            # Classe 3 - Produits d'exploitation (alternatif suisse)
            ("3000", "Ventes de marchandises", "PRODUIT", 3, True),
            ("3200", "Ventes de produits fabriqués", "PRODUIT", 3, True),
            ("3400", "Prestations de services", "PRODUIT", 3, True),
            ("3600", "Autres produits d'exploitation", "PRODUIT", 3, True),
            ("3700", "Propres prestations activées", "PRODUIT", 3, True),
            ("3800", "Diminution de stocks", "PRODUIT", 3, True),
            ("3900", "Augmentation de stocks", "PRODUIT", 3, True),

            # Classe 4 - Charges de matières et marchandises
            ("4000", "Achats de marchandises", "CHARGE", 4, True),
            ("4200", "Achats de matières premières", "CHARGE", 4, True),
            ("4400", "Prestations de tiers", "CHARGE", 4, True),
            ("4500", "Frais d'énergie et carburants", "CHARGE", 4, True),
            ("4900", "Variation de stocks", "CHARGE", 4, True),

            # Classe 5 - Charges de personnel
            ("5000", "Salaires", "CHARGE", 5, True),
            ("5010", "Salaires des employés", "CHARGE", 5, True),
            ("5020", "Salaires de la direction", "CHARGE", 5, True),
            ("5200", "Charges sociales AVS/AI/APG", "CHARGE", 5, True),
            ("5210", "Charges sociales AC", "CHARGE", 5, True),
            ("5220", "Charges sociales LPP", "CHARGE", 5, True),
            ("5230", "Charges sociales LAA", "CHARGE", 5, True),
            ("5270", "Allocations familiales", "CHARGE", 5, True),
            ("5500", "Autres charges de personnel", "CHARGE", 5, True),
            ("5700", "Formation du personnel", "CHARGE", 5, True),
            ("5800", "Frais de déplacement", "CHARGE", 5, True),
            ("5900", "Charges sociales diverses", "CHARGE", 5, True),

            # Classe 6 - Autres charges d'exploitation
            ("6000", "Loyer", "CHARGE", 6, True),
            ("6100", "Entretien et réparations", "CHARGE", 6, True),
            ("6200", "Véhicules et transport", "CHARGE", 6, True),
            ("6300", "Assurances", "CHARGE", 6, True),
            ("6400", "Énergie et eau", "CHARGE", 6, True),
            ("6500", "Frais d'administration", "CHARGE", 6, True),
            ("6510", "Téléphone et internet", "CHARGE", 6, True),
            ("6520", "Fournitures de bureau", "CHARGE", 6, True),
            ("6530", "Comptabilité et révision", "CHARGE", 6, True),
            ("6540", "Frais juridiques", "CHARGE", 6, True),
            ("6570", "Frais informatiques", "CHARGE", 6, True),
            ("6600", "Publicité", "CHARGE", 6, True),
            ("6700", "Autres charges d'exploitation", "CHARGE", 6, True),
            ("6800", "Amortissements", "CHARGE", 6, True),
            ("6810", "Amortissements machines", "CHARGE", 6, True),
            ("6820", "Amortissements mobilier", "CHARGE", 6, True),
            ("6830", "Amortissements informatique", "CHARGE", 6, True),
            ("6900", "Charges financières", "CHARGE", 6, True),
            ("6910", "Intérêts bancaires", "CHARGE", 6, True),
            ("6940", "Différences de change", "CHARGE", 6, True),

            # Classe 7 - Produits hors exploitation
            ("7000", "Produits financiers", "PRODUIT", 7, True),
            ("7010", "Intérêts bancaires reçus", "PRODUIT", 7, True),
            ("7100", "Produits immobiliers", "PRODUIT", 7, True),
            ("7500", "Produits exceptionnels", "PRODUIT", 7, True),

            # Classe 8 - Charges hors exploitation
            ("8000", "Charges hors exploitation", "CHARGE", 8, True),
            ("8100", "Charges immobilières", "CHARGE", 8, True),
            ("8500", "Charges exceptionnelles", "CHARGE", 8, True),
            ("8900", "Impôts directs", "CHARGE", 8, True),
            ("8910", "Impôt fédéral direct", "CHARGE", 8, True),
            ("8920", "Impôt cantonal et communal", "CHARGE", 8, True),

            # Classe 9 - Clôture
            ("9000", "Compte de clôture", "BILAN", 9, False),
            ("9100", "Compte de résultat", "RESULTAT", 9, False),
        ]

        # Récupérer le type de plan PME
        type_plan_pme = TypePlanComptable.objects.filter(code="PME").first()
        if not type_plan_pme:
            type_plan_pme = TypePlanComptable.objects.first()

        for mandat in mandats:
            # Obtenir ou créer le plan comptable
            plan = PlanComptable.objects.filter(mandat=mandat).first()
            if not plan:
                plan = PlanComptable.objects.create(
                    mandat=mandat,
                    nom=f"Plan comptable PME - {mandat.client.raison_sociale}",
                    type_plan=type_plan_pme,
                )

            # Créer les comptes manquants
            existing_numeros = set(
                Compte.objects.filter(plan_comptable=plan).values_list("numero", flat=True)
            )

            comptes_crees = 0
            for numero, libelle, type_compte, classe, imputable in comptes_complets:
                if numero not in existing_numeros:
                    Compte.objects.create(
                        plan_comptable=plan,
                        numero=numero,
                        libelle=libelle,
                        type_compte=type_compte,
                        classe=classe,
                        niveau=len(numero),
                        imputable=imputable,
                        solde_debit=Decimal("0"),
                        solde_credit=Decimal("0"),
                    )
                    comptes_crees += 1

            if comptes_crees > 0:
                self.stdout.write(f"  ✓ {mandat.numero}: {comptes_crees} comptes créés")

    def _ensure_journals(self, mandats):
        """S'assure que chaque mandat a les journaux nécessaires"""
        self.stdout.write("📔 Vérification des journaux...")

        journaux_types = [
            ("VTE", "Ventes", "VTE"),
            ("ACH", "Achats", "ACH"),
            ("BNQ", "Banque", "BNQ"),
            ("CAS", "Caisse", "CAS"),
            ("SAL", "Salaires", "SAL"),
            ("OD", "Opérations diverses", "OD"),
            ("TVA", "TVA", "TVA"),
            ("AN", "À-nouveaux", "AN"),
        ]

        for mandat in mandats:
            existing_codes = set(
                Journal.objects.filter(mandat=mandat).values_list("code", flat=True)
            )

            for code, libelle, type_j in journaux_types:
                if code not in existing_codes:
                    Journal.objects.create(
                        mandat=mandat,
                        code=code,
                        libelle=libelle,
                        type_journal=type_j,
                        numerotation_auto=True,
                        prefixe_piece=code,
                    )

    def _generate_accounting_entries(self, mandats, ecritures_par_mandat):
        """Génère des écritures comptables équilibrées et réalistes"""
        self.stdout.write(f"📝 Génération de {ecritures_par_mandat} écritures par mandat...")

        total_ecritures = 0

        for mandat in mandats:
            # Récupérer les comptes et journaux
            plan = PlanComptable.objects.filter(mandat=mandat).first()
            if not plan:
                continue

            comptes = {c.numero: c for c in Compte.objects.filter(plan_comptable=plan)}
            journaux = {j.code: j for j in Journal.objects.filter(mandat=mandat)}

            # Récupérer ou créer l'exercice
            exercice = ExerciceComptable.objects.filter(
                mandat=mandat, statut="OUVERT"
            ).first()
            if not exercice:
                exercice = ExerciceComptable.objects.create(
                    mandat=mandat,
                    annee=2025,
                    date_debut=date(2025, 1, 1),
                    date_fin=date(2025, 12, 31),
                    statut="OUVERT",
                )

            # Générer des écritures pour chaque mois
            ecritures_par_mois = ecritures_par_mandat // 12

            for mois in range(1, 13):
                date_debut_mois = date(2025, mois, 1)
                if mois == 12:
                    date_fin_mois = date(2025, 12, 31)
                else:
                    date_fin_mois = date(2025, mois + 1, 1) - timedelta(days=1)

                # Générer des ventes
                total_ecritures += self._generate_sales_entries(
                    mandat, exercice, comptes, journaux.get("VTE"),
                    date_debut_mois, date_fin_mois, ecritures_par_mois // 4
                )

                # Générer des achats
                total_ecritures += self._generate_purchase_entries(
                    mandat, exercice, comptes, journaux.get("ACH"),
                    date_debut_mois, date_fin_mois, ecritures_par_mois // 4
                )

                # Générer des mouvements bancaires
                total_ecritures += self._generate_bank_entries(
                    mandat, exercice, comptes, journaux.get("BNQ"),
                    date_debut_mois, date_fin_mois, ecritures_par_mois // 4
                )

                # Générer des charges diverses
                total_ecritures += self._generate_expense_entries(
                    mandat, exercice, comptes, journaux.get("OD"),
                    date_debut_mois, date_fin_mois, ecritures_par_mois // 4
                )

            self.stdout.write(f"  ✓ {mandat.numero}: écritures générées")

        self.stdout.write(f"  → Total: {total_ecritures} écritures")

    def _generate_sales_entries(self, mandat, exercice, comptes, journal, date_debut, date_fin, count):
        """Génère des écritures de ventes"""
        if not journal:
            return 0

        created = 0
        for i in range(count):
            montant_ht = Decimal(str(random.randint(500, 50000)))
            tva = (montant_ht * Decimal("0.081")).quantize(Decimal("0.01"))
            montant_ttc = montant_ht + tva

            date_ecriture = self.fake.date_between(start_date=date_debut, end_date=date_fin)
            num_piece = f"VTE{date_ecriture.strftime('%Y%m')}{i+1:04d}"

            # Débit: Débiteurs clients (TTC)
            if "1100" in comptes:
                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=1,
                    date_ecriture=date_ecriture,
                    compte=comptes["1100"],
                    libelle=f"Facture client {self.fake.company()[:30]}",
                    montant_debit=montant_ttc,
                    montant_credit=Decimal("0"),
                    statut="VALIDE",
                )
                created += 1

            # Crédit: Ventes (HT)
            compte_vente = comptes.get("3400") or comptes.get("3000")
            if compte_vente:
                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=2,
                    date_ecriture=date_ecriture,
                    compte=compte_vente,
                    libelle=f"Vente - {self.fake.bs()[:30]}",
                    montant_debit=Decimal("0"),
                    montant_credit=montant_ht,
                    statut="VALIDE",
                )
                created += 1

            # Crédit: TVA due
            if "2200" in comptes:
                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=3,
                    date_ecriture=date_ecriture,
                    compte=comptes["2200"],
                    libelle="TVA collectée 8.1%",
                    montant_debit=Decimal("0"),
                    montant_credit=tva,
                    statut="VALIDE",
                )
                created += 1

        return created

    def _generate_purchase_entries(self, mandat, exercice, comptes, journal, date_debut, date_fin, count):
        """Génère des écritures d'achats"""
        if not journal:
            return 0

        created = 0
        charges_comptes = ["4000", "4200", "4400", "6500", "6570", "6600"]

        for i in range(count):
            montant_ht = Decimal(str(random.randint(200, 20000)))
            tva = (montant_ht * Decimal("0.081")).quantize(Decimal("0.01"))
            montant_ttc = montant_ht + tva

            date_ecriture = self.fake.date_between(start_date=date_debut, end_date=date_fin)
            num_piece = f"ACH{date_ecriture.strftime('%Y%m')}{i+1:04d}"

            compte_charge_num = random.choice(charges_comptes)
            compte_charge = comptes.get(compte_charge_num) or comptes.get("4000")

            # Débit: Charge (HT)
            if compte_charge:
                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=1,
                    date_ecriture=date_ecriture,
                    compte=compte_charge,
                    libelle=f"Achat {self.fake.company()[:30]}",
                    montant_debit=montant_ht,
                    montant_credit=Decimal("0"),
                    statut="VALIDE",
                )
                created += 1

            # Débit: TVA préalable
            if "1170" in comptes:
                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=2,
                    date_ecriture=date_ecriture,
                    compte=comptes["1170"],
                    libelle="TVA déductible 8.1%",
                    montant_debit=tva,
                    montant_credit=Decimal("0"),
                    statut="VALIDE",
                )
                created += 1

            # Crédit: Créanciers (TTC)
            if "2000" in comptes:
                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=3,
                    date_ecriture=date_ecriture,
                    compte=comptes["2000"],
                    libelle=f"Fournisseur {self.fake.company()[:30]}",
                    montant_debit=Decimal("0"),
                    montant_credit=montant_ttc,
                    statut="VALIDE",
                )
                created += 1

        return created

    def _generate_bank_entries(self, mandat, exercice, comptes, journal, date_debut, date_fin, count):
        """Génère des mouvements bancaires (encaissements et décaissements)"""
        if not journal:
            return 0

        created = 0
        compte_banque = comptes.get("1020") or comptes.get("1021")

        if not compte_banque:
            return 0

        for i in range(count):
            date_ecriture = self.fake.date_between(start_date=date_debut, end_date=date_fin)
            num_piece = f"BNQ{date_ecriture.strftime('%Y%m')}{i+1:04d}"

            if random.random() > 0.4:  # 60% encaissements
                # Encaissement client
                montant = Decimal(str(random.randint(1000, 80000)))

                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=1,
                    date_ecriture=date_ecriture,
                    compte=compte_banque,
                    libelle=f"Encaissement {self.fake.company()[:25]}",
                    montant_debit=montant,
                    montant_credit=Decimal("0"),
                    statut="VALIDE",
                )
                created += 1

                if "1100" in comptes:
                    EcritureComptable.objects.create(
                        mandat=mandat,
                        exercice=exercice,
                        journal=journal,
                        numero_piece=num_piece,
                        numero_ligne=2,
                        date_ecriture=date_ecriture,
                        compte=comptes["1100"],
                        libelle="Règlement client",
                        montant_debit=Decimal("0"),
                        montant_credit=montant,
                        statut="VALIDE",
                    )
                    created += 1
            else:
                # Paiement fournisseur
                montant = Decimal(str(random.randint(500, 30000)))

                if "2000" in comptes:
                    EcritureComptable.objects.create(
                        mandat=mandat,
                        exercice=exercice,
                        journal=journal,
                        numero_piece=num_piece,
                        numero_ligne=1,
                        date_ecriture=date_ecriture,
                        compte=comptes["2000"],
                        libelle="Paiement fournisseur",
                        montant_debit=montant,
                        montant_credit=Decimal("0"),
                        statut="VALIDE",
                    )
                    created += 1

                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=2,
                    date_ecriture=date_ecriture,
                    compte=compte_banque,
                    libelle=f"Règlement {self.fake.company()[:25]}",
                    montant_debit=Decimal("0"),
                    montant_credit=montant,
                    statut="VALIDE",
                )
                created += 1

        return created

    def _generate_expense_entries(self, mandat, exercice, comptes, journal, date_debut, date_fin, count):
        """Génère des charges diverses (loyer, salaires, etc.)"""
        if not journal:
            return 0

        created = 0

        charges_fixes = [
            ("6000", "Loyer mensuel", (3000, 8000)),
            ("6300", "Prime d'assurance", (500, 2000)),
            ("6400", "Électricité et eau", (200, 800)),
            ("6510", "Téléphone et internet", (100, 500)),
        ]

        for i in range(count):
            date_ecriture = self.fake.date_between(start_date=date_debut, end_date=date_fin)
            num_piece = f"OD{date_ecriture.strftime('%Y%m')}{i+1:04d}"

            charge = random.choice(charges_fixes)
            compte_num, libelle, (min_val, max_val) = charge
            montant = Decimal(str(random.randint(min_val, max_val)))

            compte_charge = comptes.get(compte_num)
            compte_banque = comptes.get("1020") or comptes.get("1021")

            if compte_charge and compte_banque:
                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=1,
                    date_ecriture=date_ecriture,
                    compte=compte_charge,
                    libelle=libelle,
                    montant_debit=montant,
                    montant_credit=Decimal("0"),
                    statut="VALIDE",
                )
                created += 1

                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    numero_piece=num_piece,
                    numero_ligne=2,
                    date_ecriture=date_ecriture,
                    compte=compte_banque,
                    libelle=f"Paiement {libelle.lower()}",
                    montant_debit=Decimal("0"),
                    montant_credit=montant,
                    statut="VALIDE",
                )
                created += 1

        return created

    def _generate_invoices(self, mandats, factures_par_mandat):
        """Génère des factures réalistes"""
        self.stdout.write(f"🧾 Génération de {factures_par_mandat} factures par mandat...")

        prestations = list(Prestation.objects.filter(actif=True))
        if not prestations:
            self.stdout.write("  ⚠ Aucune prestation trouvée, création de prestations par défaut...")
            self._create_default_prestations()
            prestations = list(Prestation.objects.filter(actif=True))

        total_factures = 0

        for mandat in mandats:
            for _ in range(factures_par_mandat):
                date_emission = self.fake.date_between(start_date="-180d", end_date="today")
                date_echeance = date_emission + timedelta(days=30)

                statut = random.choices(
                    ["BROUILLON", "EMISE", "PAYEE", "PARTIELLEMENT_PAYEE"],
                    weights=[10, 30, 50, 10]
                )[0]

                facture = Facture.objects.create(
                    mandat=mandat,
                    client=mandat.client,
                    type_facture="FACTURE",
                    date_emission=date_emission,
                    date_echeance=date_echeance,
                    montant_ht=Decimal("0"),
                    montant_tva=Decimal("0"),
                    montant_ttc=Decimal("0"),
                    delai_paiement_jours=30,
                    statut=statut,
                    creee_par=mandat.responsable,
                    introduction="Veuillez trouver ci-joint notre facture pour les prestations effectuées.",
                    conclusion="Nous vous remercions de votre confiance.",
                )

                # Ajouter des lignes
                nb_lignes = random.randint(1, 5)
                for j in range(nb_lignes):
                    prestation = random.choice(prestations)
                    quantite = Decimal(str(random.randint(1, 20)))
                    prix = prestation.prix_unitaire_ht

                    LigneFacture.objects.create(
                        facture=facture,
                        ordre=j + 1,
                        prestation=prestation,
                        description=f"{prestation.libelle} - {self.fake.sentence(nb_words=4)}",
                        quantite=quantite,
                        unite=prestation.unite or "heure",
                        prix_unitaire_ht=prix,
                        montant_ht=quantite * prix,
                        taux_tva=Decimal("8.1"),
                        remise_pourcent=Decimal("0"),
                    )

                facture.calculer_totaux()
                total_factures += 1

        self.stdout.write(f"  → {total_factures} factures créées")

    def _create_default_prestations(self):
        """Crée des prestations par défaut si elles n'existent pas"""
        prestations_default = [
            ("COMPTA-STD", "Comptabilité courante", "COMPTABILITE", Decimal("150")),
            ("TVA-DEC", "Décompte TVA", "TVA", Decimal("250")),
            ("SAL-CALC", "Calcul des salaires", "SALAIRES", Decimal("120")),
            ("CONSEIL", "Conseil", "CONSEIL", Decimal("200")),
        ]

        from facturation.models import TypePrestation

        for code, libelle, type_p, prix in prestations_default:
            type_obj = TypePrestation.objects.get(code=type_p)
            Prestation.objects.get_or_create(
                code=code,
                defaults={
                    "libelle": libelle,
                    "type_prestation": type_obj,
                    "prix_unitaire_ht": prix,
                    "unite": "heure",
                    "taux_horaire": prix,
                    "soumis_tva": True,
                    "taux_tva_defaut": Decimal("8.1"),
                    "actif": True,
                }
            )

    def _generate_payments(self):
        """Génère des paiements pour les factures payées"""
        self.stdout.write("💳 Génération des paiements...")

        factures_payees = Facture.objects.filter(
            statut__in=["PAYEE", "PARTIELLEMENT_PAYEE"]
        ).exclude(paiements__isnull=False)

        count = 0
        for facture in factures_payees:
            if facture.statut == "PAYEE":
                montant = facture.montant_ttc
            else:
                montant = facture.montant_ttc * Decimal(str(random.uniform(0.3, 0.8)))
                montant = montant.quantize(Decimal("0.01"))

            Paiement.objects.create(
                facture=facture,
                montant=montant,
                date_paiement=self.fake.date_between(
                    start_date=facture.date_emission, end_date="today"
                ),
                mode_paiement=random.choice(["VIREMENT", "QR_BILL"]),
                reference=f"REF-{random.randint(10000, 99999)}",
                valide=True,
            )
            count += 1

        self.stdout.write(f"  → {count} paiements créés")

    def _generate_payroll_data(self, mandats, employes_par_mandat):
        """Génère des employés et fiches de salaire"""
        self.stdout.write("👥 Génération des données de salaires...")

        salaires_mandats = [
            m for m in mandats
            if m.type_mandat in ["SALAIRES", "GLOBAL"]
        ]

        if not salaires_mandats:
            self.stdout.write("  ⚠ Aucun mandat salaires trouvé")
            return

        # Vérifier les taux de cotisation
        if not TauxCotisation.objects.exists():
            self._create_default_cotisations()

        adresses = list(Mandat.objects.exclude(
            client__adresse_siege__isnull=True
        ).values_list('client__adresse_siege', flat=True)[:10])

        from core.models import Adresse
        adresses_obj = list(Adresse.objects.filter(id__in=adresses))

        employe_count = 0
        fiche_count = 0

        for mandat in salaires_mandats[:5]:
            # Créer des employés
            for i in range(employes_par_mandat):
                salaire_base = Decimal(str(random.randint(4500, 12000)))

                employe = Employe.objects.create(
                    mandat=mandat,
                    matricule=f"EMP{mandat.id.hex[:4]}{i+1:03d}",
                    nom=self.fake.last_name(),
                    prenom=self.fake.first_name(),
                    date_naissance=self.fake.date_of_birth(minimum_age=22, maximum_age=60),
                    lieu_naissance=self.fake.city()[:100],
                    nationalite="CH",
                    sexe=random.choice(["M", "F"]),
                    avs_number=f"756.{random.randint(1000, 9999)}.{random.randint(1000, 9999)}.{random.randint(10, 99)}",
                    adresse=random.choice(adresses_obj) if adresses_obj else None,
                    email=self.fake.email(),
                    telephone=self.fake.phone_number(),
                    etat_civil=random.choice(["CELIBATAIRE", "MARIE", "DIVORCE"]),
                    type_contrat="CDI",
                    date_entree=self.fake.date_between(start_date="-5y", end_date="-1m"),
                    fonction="Employé",
                    taux_occupation=Decimal("100"),
                    salaire_brut_mensuel=salaire_base,
                    nombre_heures_semaine=Decimal("42"),
                    jours_vacances_annuel=25,
                    treizieme_salaire=True,
                    iban=self.fake.iban(),
                    statut="ACTIF",
                )
                employe_count += 1

                # Créer des fiches de salaire pour chaque mois de 2025
                for mois in range(1, 7):  # Janvier à Juin
                    avs = (salaire_base * Decimal("0.053")).quantize(Decimal("0.01"))
                    ac = (salaire_base * Decimal("0.011")).quantize(Decimal("0.01"))
                    lpp = (salaire_base * Decimal("0.075")).quantize(Decimal("0.01"))
                    total_deductions = avs + ac + lpp

                    FicheSalaire.objects.create(
                        employe=employe,
                        periode=date(2025, mois, 1),
                        jours_travailles=Decimal("22"),
                        heures_travaillees=Decimal("176"),
                        salaire_base=salaire_base,
                        salaire_brut_total=salaire_base,
                        avs_employe=avs,
                        ac_employe=ac,
                        lpp_employe=lpp,
                        total_cotisations_employe=total_deductions,
                        total_deductions=total_deductions,
                        salaire_net=salaire_base - total_deductions,
                        statut="VALIDE" if mois < 6 else "BROUILLON",
                    )
                    fiche_count += 1

        self.stdout.write(f"  → {employe_count} employés, {fiche_count} fiches de salaire")

    def _create_default_cotisations(self):
        """Crée les taux de cotisation par défaut"""
        cotisations = [
            ("AVS", "AVS/AI/APG", Decimal("0.106"), Decimal("0.053"), Decimal("0.053")),
            ("AC", "Assurance chômage", Decimal("0.022"), Decimal("0.011"), Decimal("0.011")),
            ("LPP", "Prévoyance professionnelle", Decimal("0.150"), Decimal("0.075"), Decimal("0.075")),
        ]

        for type_cot, libelle, total, employeur, employe in cotisations:
            TauxCotisation.objects.get_or_create(
                type_cotisation=type_cot,
                defaults={
                    "libelle": libelle,
                    "taux_total": total,
                    "taux_employeur": employeur,
                    "taux_employe": employe,
                    "repartition": "PARTAGE",
                    "date_debut": date(2024, 1, 1),
                    "actif": True,
                }
            )

    def _print_summary(self):
        """Affiche un résumé des données générées"""
        from comptabilite.models import EcritureComptable
        from facturation.models import Facture, Paiement
        from salaires.models import Employe, FicheSalaire
        from django.db.models import Sum, Count

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 RÉSUMÉ DES DONNÉES"))
        self.stdout.write("=" * 60)

        self.stdout.write(f"Écritures comptables: {EcritureComptable.objects.count()}")
        self.stdout.write(f"Factures: {Facture.objects.count()}")
        self.stdout.write(f"Paiements: {Paiement.objects.count()}")
        self.stdout.write(f"Employés: {Employe.objects.count()}")
        self.stdout.write(f"Fiches de salaire: {FicheSalaire.objects.count()}")

        self.stdout.write("\n📈 Répartition par classe comptable:")
        ecritures_par_classe = EcritureComptable.objects.values('compte__classe').annotate(
            count=Count('id'),
            total_debit=Sum('montant_debit'),
            total_credit=Sum('montant_credit')
        ).order_by('compte__classe')

        for e in ecritures_par_classe:
            classe = e['compte__classe']
            if classe:
                self.stdout.write(
                    f"  Classe {classe}: {e['count']:>5} écritures | "
                    f"Débit: {e['total_debit'] or 0:>12,.2f} CHF | "
                    f"Crédit: {e['total_credit'] or 0:>12,.2f} CHF"
                )
