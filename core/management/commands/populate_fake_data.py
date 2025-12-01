from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from decimal import Decimal
import random
from datetime import datetime, timedelta, date
from django.contrib.auth import get_user_model

# Import all models
from core.models import (
    User,
    Adresse,
    Client,
    Contact,
    Mandat,
    ExerciceComptable,
    AuditLog,
    Notification,
    Tache,
)
from comptabilite.models import (
    PlanComptable,
    Compte,
    Journal,
    EcritureComptable,
    PieceComptable,
    Lettrage,
)
from tva.models import (
    ConfigurationTVA,
    TauxTVA,
    CodeTVA,
    DeclarationTVA,
    LigneTVA,
    OperationTVA,
    CorrectionTVA,
)
from facturation.models import (
    Prestation,
    TimeTracking,
    Facture,
    LigneFacture,
    Paiement,
    Relance,
)
from salaires.models import (
    Employe,
    TauxCotisation,
    FicheSalaire,
    CertificatSalaire,
    DeclarationCotisations,
)
from documents.models import (
    Dossier,
    CategorieDocument,
    TypeDocument,
    Document,
    VersionDocument,
    TraitementDocument,
    RechercheDocument,
)
from fiscalite.models import (
    DeclarationFiscale,
    AnnexeFiscale,
    CorrectionFiscale,
    ReportPerte,
    UtilisationPerte,
    TauxImposition,
    ReclamationFiscale,
    OptimisationFiscale,
)
from analytics.models import (
    TableauBord,
    Indicateur,
    ValeurIndicateur,
    Rapport,
    PlanificationRapport,
    ComparaisonPeriode,
    AlerteMetrique,
    ExportDonnees,
)

fake = Faker("fr_CH")


class Command(BaseCommand):
    help = "Populate database with fake data"

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            self.stdout.write("Creating fake data...")

            # 1. Core models
            self.create_users()
            self.create_adresses()
            self.create_clients()
            self.create_contacts()
            self.create_mandats()
            self.create_exercices()
            self.create_notifications()
            self.create_taches()

            # 2. Comptabilité
            self.create_plans_comptables()
            self.create_comptes()
            self.create_journaux()
            self.create_ecritures()

            # 3. TVA
            self.create_config_tva()
            self.create_taux_tva()
            self.create_codes_tva()
            self.create_declarations_tva()

            # 4. Facturation
            self.create_prestations()
            self.create_time_tracking()
            self.create_factures()
            self.create_paiements()

            # 5. Salaires
            self.create_employes()
            self.create_taux_cotisations()
            self.create_fiches_salaire()

            # 6. Documents
            self.create_dossiers()
            self.create_categories_documents()
            self.create_types_documents()
            self.create_documents()

            # 7. Fiscalité
            self.create_declarations_fiscales()
            self.create_taux_imposition()

            # 8. Analytics
            self.create_tableaux_bord()
            self.create_indicateurs()
            self.create_rapports()

            self.stdout.write(self.style.SUCCESS("Data created successfully!"))

    def create_users(self):
        User = get_user_model()
        roles = ["ADMIN", "MANAGER", "COMPTABLE", "ASSISTANT", "CLIENT"]

        for i in range(10):
            User.objects.create_user(
                username=fake.user_name(),
                email=fake.email(),
                password="Test1234!",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role=random.choice(roles),
                phone=fake.phone_number(),
                mobile=fake.phone_number(),
            )
        self.stdout.write("✓ Users created")

    def create_adresses(self):
        cantons = ["GE", "VD", "BE", "ZH", "FR", "NE", "VS", "TI"]

        for i in range(20):
            Adresse.objects.create(
                rue=fake.street_name(),
                numero=str(fake.building_number()),
                npa=str(fake.random_int(1000, 9999)),
                localite=fake.city(),
                canton=random.choice(cantons),
                pays="CH",
            )
        self.stdout.write("✓ Adresses created")

    def create_clients(self):
        users = User.objects.filter(role__in=["ADMIN", "MANAGER"])
        adresses = list(Adresse.objects.all())
        formes = ["SA", "SARL", "EI", "ASSOC"]

        for i in range(15):
            client = Client.objects.create(
                raison_sociale=fake.company(),
                nom_commercial=fake.company_suffix(),
                forme_juridique=random.choice(formes),
                ide_number=f"CHE-{fake.random_int(100, 999)}.{fake.random_int(100, 999)}.{fake.random_int(100, 999)}",
                tva_number=f"CHE-{fake.random_int(100, 999)}.{fake.random_int(100, 999)}.{fake.random_int(100, 999)} TVA",
                rc_number=f"RC-{fake.random_int(10000, 99999)}",
                adresse_siege=random.choice(adresses),
                email=fake.company_email(),
                telephone=fake.phone_number(),
                site_web=fake.url(),
                date_creation=fake.date_between(start_date="-10y", end_date="-1y"),
                date_inscription_rc=fake.date_between(
                    start_date="-10y", end_date="-1y"
                ),
                date_debut_exercice=date(datetime.now().year, 1, 1),
                date_fin_exercice=date(datetime.now().year, 12, 31),
                statut=random.choice(["ACTIF", "PROSPECT"]),
                responsable=random.choice(users),
                notes=fake.text(),
            )
        self.stdout.write("✓ Clients created")

    def create_contacts(self):
        clients = Client.objects.all()

        for client in clients:
            for i in range(random.randint(1, 3)):
                Contact.objects.create(
                    client=client,
                    civilite=random.choice(["M", "MME"]),
                    nom=fake.last_name(),
                    prenom=fake.first_name(),
                    fonction=random.choice(["DIRECTEUR", "GERANT", "COMPTABLE"]),
                    email=fake.email(),
                    telephone=fake.phone_number(),
                    mobile=fake.phone_number(),
                    principal=(i == 0),
                )
        self.stdout.write("✓ Contacts created")

    def create_mandats(self):
        clients = Client.objects.all()
        users = User.objects.filter(role__in=["ADMIN", "MANAGER", "COMPTABLE"])
        types = ["COMPTA", "TVA", "SALAIRES", "FISCAL", "GLOBAL"]

        for client in clients:
            for i in range(random.randint(1, 3)):
                mandat = Mandat.objects.create(
                    client=client,
                    type_mandat=random.choice(types),
                    date_debut=fake.date_between(start_date="-2y", end_date="today"),
                    periodicite=random.choice(["MENSUEL", "TRIMESTRIEL", "ANNUEL"]),
                    type_facturation=random.choice(["FORFAIT", "HORAIRE"]),
                    montant_forfait=Decimal(str(random.randint(500, 5000))),
                    taux_horaire=Decimal(str(random.randint(100, 300))),
                    responsable=random.choice(users),
                    statut="ACTIF",
                    description=fake.text(),
                )
                mandat.equipe.add(*random.sample(list(users), k=random.randint(1, 3)))
        self.stdout.write("✓ Mandats created")

    def create_exercices(self):
        mandats = Mandat.objects.all()

        for mandat in mandats:
            for year in [2023, 2024, 2025]:
                ExerciceComptable.objects.create(
                    mandat=mandat,
                    annee=year,
                    date_debut=date(year, 1, 1),
                    date_fin=date(year, 12, 31),
                    statut="OUVERT" if year == 2025 else "CLOTURE_DEFINITIVE",
                    resultat_exercice=Decimal(str(random.randint(-50000, 200000))),
                )
        self.stdout.write("✓ Exercices created")

    def create_notifications(self):
        users = User.objects.all()
        mandats = Mandat.objects.all()

        for i in range(30):
            Notification.objects.create(
                destinataire=random.choice(users),
                type_notification=random.choice(["INFO", "SUCCESS", "WARNING"]),
                titre=fake.sentence(nb_words=4),
                message=fake.text(max_nb_chars=200),
                lue=random.choice([True, False]),
                mandat=random.choice(mandats) if random.random() > 0.3 else None,
            )
        self.stdout.write("✓ Notifications created")

    def create_taches(self):
        users = User.objects.all()
        mandats = Mandat.objects.all()

        for i in range(40):
            Tache.objects.create(
                titre=fake.sentence(nb_words=6),
                description=fake.text(),
                assigne_a=random.choice(users),
                cree_par=random.choice(users),
                mandat=random.choice(mandats),
                priorite=random.choice(["BASSE", "NORMALE", "HAUTE"]),
                date_echeance=fake.date_between(start_date="today", end_date="+30d"),
                statut=random.choice(["A_FAIRE", "EN_COURS", "TERMINEE"]),
                temps_estime_heures=Decimal(str(random.randint(1, 40))),
            )
        self.stdout.write("✓ Taches created")

    def create_plans_comptables(self):
        mandats = Mandat.objects.filter(type_mandat__in=["COMPTA", "GLOBAL"])

        for mandat in mandats[:5]:
            PlanComptable.objects.create(
                nom=f"Plan comptable {mandat.client.raison_sociale}",
                type_plan="PME",
                description=fake.text(),
                mandat=mandat,
            )
        self.stdout.write("✓ Plans comptables created")

    def create_comptes(self):
        plans = PlanComptable.objects.all()

        comptes_base = [
            ("1000", "Caisse", "ACTIF", 1),
            ("1020", "Banque", "ACTIF", 1),
            ("1100", "Créances clients", "ACTIF", 1),
            ("2000", "Dettes fournisseurs", "PASSIF", 2),
            ("2200", "TVA due", "PASSIF", 2),
            ("2800", "Capital", "PASSIF", 2),
            ("6000", "Charges de personnel", "CHARGE", 6),
            ("7000", "Ventes de marchandises", "PRODUIT", 7),
        ]

        for plan in plans:
            for numero, libelle, type_compte, classe in comptes_base:
                Compte.objects.create(
                    plan_comptable=plan,
                    numero=numero,
                    libelle=libelle,
                    type_compte=type_compte,
                    classe=classe,
                    imputable=True,
                    solde_debit=Decimal(str(random.randint(0, 10000))),
                    solde_credit=Decimal(str(random.randint(0, 10000))),
                )
        self.stdout.write("✓ Comptes created")

    def create_journaux(self):
        mandats = Mandat.objects.filter(type_mandat__in=["COMPTA", "GLOBAL"])

        for mandat in mandats:
            for code, libelle, type_j in [
                ("VTE", "Ventes", "VTE"),
                ("ACH", "Achats", "ACH"),
                ("BNQ", "Banque", "BNQ"),
            ]:
                Journal.objects.create(
                    mandat=mandat,
                    code=code,
                    libelle=libelle,
                    type_journal=type_j,
                    numerotation_auto=True,
                    prefixe_piece=code,
                )
        self.stdout.write("✓ Journaux created")

    def create_ecritures(self):
        mandats = Mandat.objects.filter(type_mandat__in=["COMPTA", "GLOBAL"])[:3]

        for mandat in mandats:
            journal = Journal.objects.filter(mandat=mandat).first()
            exercice = ExerciceComptable.objects.filter(
                mandat=mandat, statut="OUVERT"
            ).first()
            comptes = Compte.objects.filter(plan_comptable__mandat=mandat)

            if journal and exercice and comptes.exists():
                for i in range(20):
                    compte = random.choice(comptes)
                    montant = Decimal(str(random.randint(100, 5000)))

                    EcritureComptable.objects.create(
                        mandat=mandat,
                        exercice=exercice,
                        journal=journal,
                        numero_piece=f"{journal.prefixe_piece}{i + 1:05d}",
                        numero_ligne=1,
                        date_ecriture=fake.date_between(
                            start_date="-30d", end_date="today"
                        ),
                        compte=compte,
                        libelle=fake.sentence(nb_words=8),
                        montant_debit=montant
                        if random.random() > 0.5
                        else Decimal("0"),
                        montant_credit=Decimal("0")
                        if random.random() > 0.5
                        else montant,
                        statut="VALIDE",
                    )
        self.stdout.write("✓ Ecritures created")

    def create_config_tva(self):
        mandats = Mandat.objects.filter(type_mandat__in=["TVA", "COMPTA", "GLOBAL"])

        for mandat in mandats[:5]:
            ConfigurationTVA.objects.create(
                mandat=mandat,
                assujetti_tva=True,
                numero_tva=f"CHE-{fake.random_int(100, 999)}.{fake.random_int(100, 999)}.{fake.random_int(100, 999)} TVA",
                date_debut_assujettissement=fake.date_between(
                    start_date="-5y", end_date="-1y"
                ),
                methode_calcul="EFFECTIVE",
                periodicite="TRIMESTRIEL",
            )
        self.stdout.write("✓ Config TVA created")

    def create_taux_tva(self):
        taux = [
            ("NORMAL", Decimal("8.1"), "Taux normal"),
            ("REDUIT", Decimal("2.6"), "Taux réduit"),
            ("SPECIAL", Decimal("3.8"), "Taux hébergement"),
        ]

        for type_taux, valeur, description in taux:
            TauxTVA.objects.create(
                type_taux=type_taux,
                taux=valeur,
                date_debut=date(2024, 1, 1),
                description=description,
            )
        self.stdout.write("✓ Taux TVA created")

    def create_codes_tva(self):
        codes = [
            ("200", "Prestations imposables taux normal", "PRESTATIONS_IMPOSABLES"),
            ("205", "Prestations imposables taux réduit", "PRESTATIONS_IMPOSABLES"),
            ("400", "Impôt préalable matériel", "TVA_PREALABLE"),
            ("405", "Impôt préalable prestations", "TVA_PREALABLE"),
        ]

        for code, libelle, categorie in codes:
            CodeTVA.objects.create(
                code=code, libelle=libelle, categorie=categorie, actif=True
            )
        self.stdout.write("✓ Codes TVA created")

    def create_declarations_tva(self):
        mandats = Mandat.objects.filter(config_tva__isnull=False)[:3]
        
        for idx, mandat in enumerate(mandats):
            for trimestre in [1, 2, 3, 4]:
                # Ajouter l'index du mandat pour éviter les doublons
                DeclarationTVA.objects.create(
                    mandat=mandat,
                    numero_declaration=f'TVA-{mandat.id}-2024-T{trimestre}',  # Utiliser l'ID du mandat
                    annee=2024,
                    trimestre=trimestre,
                    periode_debut=date(2024, (trimestre-1)*3+1, 1),
                    periode_fin=date(2024, trimestre*3, 1),
                    type_decompte='NORMAL',
                    methode='EFFECTIVE',
                    chiffre_affaires_total=Decimal(str(random.randint(10000, 100000))),
                    chiffre_affaires_imposable=Decimal(str(random.randint(8000, 80000))),
                    tva_due_total=Decimal(str(random.randint(800, 8000))),
                    tva_prealable_total=Decimal(str(random.randint(500, 5000))),
                    statut='VALIDE'
                )
        self.stdout.write('✓ Déclarations TVA created')

    def create_prestations(self):
        types = ["COMPTABILITE", "TVA", "SALAIRES", "CONSEIL"]

        for i in range(10):
            Prestation.objects.create(
                code=f"PREST{i + 1:03d}",
                libelle=fake.sentence(nb_words=4),
                description=fake.text(),
                type_prestation=random.choice(types),
                prix_unitaire_ht=Decimal(str(random.randint(100, 500))),
                unite="heure",
                taux_horaire=Decimal(str(random.randint(100, 300))),
                soumis_tva=True,
                taux_tva_defaut=Decimal("8.1"),
                actif=True,
            )
        self.stdout.write("✓ Prestations created")

    def create_time_tracking(self):
        mandats = Mandat.objects.all()[:5]
        users = User.objects.filter(role__in=["COMPTABLE", "ASSISTANT"])
        prestations = Prestation.objects.all()

        for mandat in mandats:
            for i in range(10):
                TimeTracking.objects.create(
                    mandat=mandat,
                    utilisateur=random.choice(users),
                    prestation=random.choice(prestations),
                    date_travail=fake.date_between(start_date="-30d", end_date="today"),
                    duree_minutes=random.randint(15, 480),
                    description=fake.text(max_nb_chars=200),
                    facturable=True,
                    taux_horaire=Decimal(str(random.randint(100, 300))),
                    montant_ht=Decimal(str(random.randint(50, 1000))),
                )
        self.stdout.write("✓ Time tracking created")

    def create_factures(self):
        mandats = Mandat.objects.all()[:5]
        
        for mandat in mandats:
            for i in range(3):
                # Ne pas spécifier qr_reference car elle est blank=True et sera générée si besoin
                facture = Facture.objects.create(
                    mandat=mandat,
                    client=mandat.client,
                    type_facture='FACTURE',
                    date_emission=fake.date_between(start_date='-60d', end_date='today'),
                    date_echeance=fake.date_between(start_date='today', end_date='+30d'),
                    montant_ht=Decimal(str(random.randint(1000, 10000))),
                    montant_tva=Decimal(str(random.randint(80, 800))),
                    montant_ttc=Decimal(str(random.randint(1080, 10800))),
                    delai_paiement_jours=30,
                    statut=random.choice(['EMISE', 'PAYEE', 'BROUILLON']),
                    creee_par=mandat.responsable,
                    introduction=fake.sentence(),
                    conclusion='Nous vous remercions de votre confiance.'
                )
                
                # Créer des lignes de facture
                prestations = list(Prestation.objects.all())
                if prestations:
                    for j in range(random.randint(1, 4)):
                        quantite = Decimal(str(random.randint(1, 10)))
                        prix_unitaire = Decimal(str(random.randint(100, 500)))
                        prestation = random.choice(prestations)
                        
                        LigneFacture.objects.create(
                            facture=facture,
                            ordre=j+1,
                            prestation=prestation,
                            description=prestation.libelle + ' - ' + fake.sentence(),
                            quantite=quantite,
                            unite=prestation.unite,
                            prix_unitaire_ht=prix_unitaire,
                            montant_ht=quantite * prix_unitaire,
                            taux_tva=prestation.taux_tva_defaut,
                            remise_pourcent=Decimal('0')
                        )
                
                # Calculer les totaux après ajout des lignes
                facture.calculer_totaux()
                
        self.stdout.write('✓ Factures created')

    def create_paiements(self):
        factures = Facture.objects.filter(statut="PAYEE")

        for facture in factures[:10]:
            Paiement.objects.create(
                facture=facture,
                montant=facture.montant_ttc,
                date_paiement=fake.date_between(
                    start_date=facture.date_emission, end_date="today"
                ),
                mode_paiement="VIREMENT",
                reference=f"REF-{fake.random_int(10000, 99999)}",
                valide=True,
            )
        self.stdout.write("✓ Paiements created")

    def create_employes(self):
        mandats = Mandat.objects.filter(type_mandat__in=["SALAIRES", "GLOBAL"])[:3]
        adresses = Adresse.objects.all()
        
        fonctions = [
            'Comptable', 'Assistant comptable', 'Gestionnaire de paie',
            'Directeur financier', 'Contrôleur de gestion', 'Auditeur',
            'Analyste', 'Chef de projet', 'Secrétaire', 'RH'
        ]
        
        employe_counter = 0  # Compteur global pour matricules uniques
        
        for mandat in mandats:
            for i in range(5):
                employe_counter += 1
                Employe.objects.create(
                    mandat=mandat,
                    matricule=f"EMP{employe_counter:04d}",  # Matricule unique global
                    nom=fake.last_name(),
                    prenom=fake.first_name(),
                    date_naissance=fake.date_of_birth(minimum_age=20, maximum_age=65),
                    lieu_naissance=fake.city()[:100],
                    nationalite="CH",
                    sexe=random.choice(["M", "F"]),
                    avs_number=f"756.{fake.random_int(1000, 9999)}.{fake.random_int(1000, 9999)}.{fake.random_int(10, 99)}",
                    adresse=random.choice(adresses),
                    email=fake.email(),
                    telephone=fake.phone_number(),
                    etat_civil=random.choice(["CELIBATAIRE", "MARIE"]),
                    type_contrat="CDI",
                    date_entree=fake.date_between(start_date="-5y", end_date="-1m"),
                    fonction=random.choice(fonctions),
                    taux_occupation=Decimal("100"),
                    salaire_brut_mensuel=Decimal(str(random.randint(3000, 8000))),
                    nombre_heures_semaine=Decimal("42"),
                    jours_vacances_annuel=25,
                    treizieme_salaire=True,
                    iban=fake.iban(),
                    statut="ACTIF",
                )
        self.stdout.write("✓ Employés created")


    def create_taux_cotisations(self):
        cotisations = [
            ("AVS", "AVS/AI/APG", Decimal("8.7"), Decimal("4.35"), Decimal("4.35")),
            ("AC", "Assurance chômage", Decimal("2.2"), Decimal("1.1"), Decimal("1.1")),
            ("LPP", "LPP", Decimal("8"), Decimal("4"), Decimal("4")),  # Réduit de 14 à 8
            ("LAA", "LAA", Decimal("2"), Decimal("2"), Decimal("0")),
        ]

        for type_cot, libelle, total, employeur, employe in cotisations:
            TauxCotisation.objects.create(
                type_cotisation=type_cot,
                libelle=libelle,
                taux_total=total,
                taux_employeur=employeur,
                taux_employe=employe,
                repartition="PARTAGE" if employe > 0 else "EMPLOYEUR",
                date_debut=date(2024, 1, 1),
                actif=True,
            )
        self.stdout.write("✓ Taux cotisations created")

    def create_fiches_salaire(self):
        employes = Employe.objects.all()[:5]

        for employe in employes:
            for mois in range(1, 4):  # 3 derniers mois
                FicheSalaire.objects.create(
                    employe=employe,
                    periode=date(2025, mois, 1),
                    jours_travailles=Decimal("22"),
                    heures_travaillees=Decimal("176"),
                    salaire_base=employe.salaire_brut_mensuel,
                    salaire_brut_total=employe.salaire_brut_mensuel,
                    avs_employe=Decimal(str(random.randint(200, 400))),
                    ac_employe=Decimal(str(random.randint(50, 100))),
                    lpp_employe=Decimal(str(random.randint(300, 600))),
                    salaire_net=employe.salaire_brut_mensuel
                    - Decimal(str(random.randint(800, 1500))),
                    statut="VALIDE",
                )
        self.stdout.write("✓ Fiches salaire created")

    def create_dossiers(self):
        clients = Client.objects.all()
        mandats = Mandat.objects.all()[:5]
        users = User.objects.all()

        for client in clients[:5]:
            dossier_client = Dossier.objects.create(
                nom=f"Dossier {client.raison_sociale}",
                type_dossier="CLIENT",
                client=client,
                chemin_complet=f"/{client.raison_sociale}",
                proprietaire=client.responsable,
            )

            for sous_dossier in ["Comptabilité", "TVA", "Contrats"]:
                Dossier.objects.create(
                    parent=dossier_client,
                    nom=sous_dossier,
                    type_dossier="STANDARD",
                    client=client,
                    chemin_complet=f"/{client.raison_sociale}/{sous_dossier}",
                    proprietaire=client.responsable,
                )
        self.stdout.write("✓ Dossiers created")

    def create_categories_documents(self):
        categories = [
            ("Factures", "Documents de facturation"),
            ("Contrats", "Documents contractuels"),
            ("Comptabilité", "Documents comptables"),
            ("TVA", "Documents TVA"),
            ("Salaires", "Documents salariaux"),
        ]

        for nom, description in categories:
            CategorieDocument.objects.create(
                nom=nom, description=description, ordre=random.randint(1, 10)
            )
        self.stdout.write("✓ Catégories documents created")

    def create_types_documents(self):
        categories = CategorieDocument.objects.all()
        types = [
            ("FAC_VENTE", "Facture de vente", "FACTURE_VENTE"),
            ("FAC_ACHAT", "Facture d'achat", "FACTURE_ACHAT"),
            ("CONTRAT", "Contrat", "CONTRAT"),
            ("RELEVE", "Relevé bancaire", "RELEVE_BANQUE"),
        ]

        for code, libelle, type_doc in types:
            TypeDocument.objects.create(
                code=code,
                libelle=libelle,
                type_document=type_doc,
                categorie=random.choice(categories),
            )
        self.stdout.write("✓ Types documents created")

    def create_documents(self):
        mandats = Mandat.objects.all()[:5]
        dossiers = Dossier.objects.all()
        types_doc = TypeDocument.objects.all()
        categories = CategorieDocument.objects.all()

        for mandat in mandats:
            dossier = dossiers.filter(mandat=mandat).first() or dossiers.first()
            for i in range(5):
                Document.objects.create(
                    mandat=mandat,
                    dossier=dossier,
                    nom_fichier=f"document_{fake.random_int(1000, 9999)}.pdf",
                    nom_original=f"facture_{fake.random_int(1000, 9999)}.pdf",
                    extension=".pdf",
                    mime_type="application/pdf",
                    taille=random.randint(10000, 1000000),
                    path_storage=f"/storage/{mandat.id}/doc_{fake.random_int(1000, 9999)}.pdf",
                    hash_fichier=fake.sha256(),
                    type_document=random.choice(types_doc),
                    categorie=random.choice(categories),
                    date_document=fake.date_between(
                        start_date="-60d", end_date="today"
                    ),
                    statut_traitement="VALIDE",
                    description=fake.text(max_nb_chars=200),
                )
        self.stdout.write("✓ Documents created")

    def create_declarations_fiscales(self):
        mandats = Mandat.objects.filter(type_mandat__in=["FISCAL", "GLOBAL"])[:3]

        for mandat in mandats:
            exercice = ExerciceComptable.objects.filter(mandat=mandat).first()
            if exercice:
                DeclarationFiscale.objects.create(
                    mandat=mandat,
                    type_declaration="PERSONNE_MORALE",
                    type_impot="IFD",
                    exercice_comptable=exercice,
                    annee_fiscale=2024,
                    periode_debut=date(2024, 1, 1),
                    periode_fin=date(2024, 12, 31),
                    canton="GE",
                    numero_contribuable=f"CTB-{fake.random_int(10000, 99999)}",
                    benefice_avant_impots=Decimal(str(random.randint(50000, 500000))),
                    benefice_imposable=Decimal(str(random.randint(40000, 400000))),
                    impot_federal=Decimal(str(random.randint(5000, 50000))),
                    impot_cantonal=Decimal(str(random.randint(3000, 30000))),
                    impot_total=Decimal(str(random.randint(8000, 80000))),
                    statut="EN_PREPARATION",
                )
        self.stdout.write("✓ Déclarations fiscales created")

    def create_taux_imposition(self):
        cantons = ["GE", "VD", "ZH"]

        for canton in cantons:
            TauxImposition.objects.create(
                canton=canton,
                type_impot="IFD_BENEFICE",
                annee=2024,
                taux_fixe=Decimal("8.5"),
                actif=True,
            )
        self.stdout.write("✓ Taux imposition created")

    def create_tableaux_bord(self):
        users = User.objects.all()[:5]

        for user in users:
            TableauBord.objects.create(
                nom=f"Tableau de bord {fake.word()}",
                description=fake.text(max_nb_chars=200),
                proprietaire=user,
                visibilite="PRIVE",
                configuration={
                    "layout": "grid",
                    "widgets": [
                        {"type": "kpi_card", "metric": "ca_mensuel"},
                        {"type": "chart", "chart_type": "line"},
                    ],
                },
                auto_refresh=False,
                favori=random.choice([True, False]),
            )
        self.stdout.write("✓ Tableaux de bord created")

    def create_indicateurs(self):
        categories = ["FINANCIER", "OPERATIONNEL", "CLIENT"]

        for i in range(10):
            Indicateur.objects.create(
                code=f"KPI{i + 1:03d}",
                nom=fake.sentence(nb_words=3),
                description=fake.text(max_nb_chars=200),
                categorie=random.choice(categories),
                type_calcul=random.choice(["SOMME", "MOYENNE", "RATIO"]),
                periodicite="MOIS",
                objectif_cible=Decimal(str(random.randint(1000, 10000))),
                unite="CHF" if i % 2 == 0 else "%",
                actif=True,
            )
        self.stdout.write("✓ Indicateurs created")

    def create_rapports(self):
        mandats = Mandat.objects.all()[:5]
        users = User.objects.all()

        for mandat in mandats:
            for i in range(2):
                Rapport.objects.create(
                    nom=f"Rapport {fake.word()}",
                    type_rapport=random.choice(["BILAN", "COMPTE_RESULTATS", "TVA"]),
                    mandat=mandat,
                    date_debut=date(2024, 1, 1),
                    date_fin=date(2024, 12, 31),
                    genere_par=random.choice(users),
                    statut="TERMINE",
                    format_fichier="PDF",
                )
        self.stdout.write("✓ Rapports created")
