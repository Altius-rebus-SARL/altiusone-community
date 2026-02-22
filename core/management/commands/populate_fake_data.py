# core/management/commands/populate_fake_data.py

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.conf import settings
from faker import Faker
from decimal import Decimal
import random
from datetime import datetime, timedelta, date
import uuid
import os
import hashlib
import tempfile

# faker-file imports for document generation
try:
    from faker_file.providers.pdf_file import PdfFileProvider
    from faker_file.providers.docx_file import DocxFileProvider
    from faker_file.providers.xlsx_file import XlsxFileProvider
    from faker_file.providers.png_file import PngFileProvider
    from faker_file.providers.txt_file import TxtFileProvider
    FAKER_FILE_AVAILABLE = True
except ImportError:
    FAKER_FILE_AVAILABLE = False

# Import all models
from core.models import (
    User,
    Adresse,
    Client,
    Contact,
    Mandat,
    ExerciceComptable,
    Notification,
    Tache,
    TypeMandat,
    TypeFacturation,
    Periodicite,
)
from comptabilite.models import (
    PlanComptable,
    Compte,
    Journal,
    EcritureComptable,
    PieceComptable,
)
from tva.models import (
    ConfigurationTVA,
    TauxTVA,
    CodeTVA,
    DeclarationTVA,
    LigneTVA,
    OperationTVA,
)
from facturation.models import (
    Prestation,
    TimeTracking,
    Facture,
    LigneFacture,
    Paiement,
)
from salaires.models import (
    Employe,
    TauxCotisation,
    FicheSalaire,
)
from documents.models import (
    Dossier,
    CategorieDocument,
    TypeDocument,
    Document,
)
from fiscalite.models import (
    DeclarationFiscale,
    TauxImposition,
    OptimisationFiscale,
)
from analytics.models import (
    TableauBord,
    Indicateur,
    Rapport,
)


class Command(BaseCommand):
    help = (
        "Génère des données de test réalistes pour AltiusOne avec support multilingue"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fakers pour chaque langue
        self.fake_fr = Faker("fr_CH")
        self.fake_de = Faker("de_CH")
        self.fake_it = Faker("it_CH")
        self.fake_en = Faker("en_GB")
        self.fake = self.fake_fr  # Par défaut

        # Register faker-file providers if available
        if FAKER_FILE_AVAILABLE:
            self.fake.add_provider(PdfFileProvider)
            self.fake.add_provider(DocxFileProvider)
            self.fake.add_provider(XlsxFileProvider)
            self.fake.add_provider(PngFileProvider)
            self.fake.add_provider(TxtFileProvider)

    def add_arguments(self, parser):
        parser.add_argument(
            "--clients",
            type=int,
            default=50,
            help="Nombre de clients à créer",
        )
        parser.add_argument(
            "--skip-accounting",
            action="store_true",
            help="Ne pas générer les écritures comptables (plus rapide)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Supprime les données existantes avant création",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Seed pour reproductibilité",
        )
        parser.add_argument(
            "--with-files",
            action="store_true",
            help="Génère de vrais fichiers PDF/DOCX/XLSX pour les documents",
        )
        parser.add_argument(
            "--documents-count",
            type=int,
            default=50,
            help="Nombre de documents à créer (avec --with-files)",
        )
        parser.add_argument(
            "--only-documents",
            action="store_true",
            help="Ne génère que les documents (skip autres données)",
        )

    def handle(self, *args, **options):
        # Initialiser les seeds
        Faker.seed(options["seed"])
        random.seed(options["seed"])

        if options["clean"]:
            self._clean_data()

        # Mode documents uniquement
        if options["only_documents"]:
            self._generate_documents_only(options)
            return

        with transaction.atomic():
            self.stdout.write(
                self.style.WARNING("🏭 Génération des données AltiusOne...")
            )

            # 1. Core models
            users = self._create_users()
            adresses = self._create_adresses()
            clients = self._create_clients(options["clients"], users, adresses)
            self._create_contacts(clients)
            mandats = self._create_mandats(clients, users)
            self._create_exercices(mandats)
            self._create_notifications(users, mandats)
            self._create_taches(users, mandats)

            # 2. Comptabilité
            if not options["skip_accounting"]:
                self._create_plans_comptables(mandats)
                self._create_journaux(mandats)
                self._create_ecritures(mandats)

            # 3. TVA
            self._create_taux_tva()
            self._create_codes_tva()
            self._create_config_tva(mandats)
            self._create_declarations_tva(mandats)

            # 4. Facturation
            self._create_prestations()
            self._create_time_tracking(mandats, users)
            self._create_factures(mandats)
            self._create_paiements()

            # 5. Salaires
            self._create_taux_cotisations()
            self._create_employes(mandats, adresses)
            self._create_fiches_salaire()

            # 6. Documents
            self._create_categories_documents()
            self._create_types_documents()
            self._create_dossiers(clients)
            if options["with_files"]:
                self._create_documents_with_files(mandats, options["documents_count"])
            else:
                self._create_documents(mandats)

            # 7. Fiscalité
            self._create_taux_imposition()
            self._create_declarations_fiscales(mandats)
            self._create_optimisations_fiscales(mandats)

            # 8. Analytics
            self._create_tableaux_bord(users)
            self._create_indicateurs()
            self._create_rapports(mandats, users)

            self.stdout.write(self.style.SUCCESS("✅ Données générées avec succès!"))

    def _generate_documents_only(self, options):
        """Génère uniquement des documents avec fichiers réels"""
        if not FAKER_FILE_AVAILABLE:
            self.stdout.write(
                self.style.ERROR(
                    "❌ faker-file non installé. Installez avec: "
                    "pip install faker-file[common,pdf,docx,xlsx,images]"
                )
            )
            return

        self.stdout.write(
            self.style.WARNING("📄 Génération des documents uniquement...")
        )

        mandats = list(Mandat.objects.all())
        if not mandats:
            self.stdout.write(
                self.style.ERROR(
                    "❌ Aucun mandat trouvé. Exécutez d'abord sans --only-documents"
                )
            )
            return

        # S'assurer que les catégories et types existent
        self._create_categories_documents()
        self._create_types_documents()

        # Créer les dossiers si nécessaire
        from core.models import Client
        clients = list(Client.objects.all()[:10])
        if clients:
            self._create_dossiers(clients)

        # Générer les documents avec fichiers
        with transaction.atomic():
            self._create_documents_with_files(mandats, options["documents_count"])

        self.stdout.write(self.style.SUCCESS("✅ Documents générés avec succès!"))

    def _clean_data(self):
        """Supprime les données existantes"""
        from django.db import connection

        self.stdout.write("🧹 Nettoyage des données existantes...")

        # D'abord, supprimer les tables non-gérées (managed=False) qui bloquent les cascades
        unmanaged_tables = [
            'document_embeddings',
            'text_chunk_embeddings',
        ]
        with connection.cursor() as cursor:
            for table in unmanaged_tables:
                try:
                    cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                    self.stdout.write(f"  → {table}: truncated")
                except Exception:
                    pass  # Table n'existe pas, pas grave

        # Supprimer dans l'ordre inverse des dépendances
        models_to_clean = [
            Rapport,
            Indicateur,
            TableauBord,
            OptimisationFiscale,
            DeclarationFiscale,
            TauxImposition,
            Document,
            TypeDocument,
            CategorieDocument,
            Dossier,
            FicheSalaire,
            Employe,
            TauxCotisation,
            Paiement,
            LigneFacture,
            Facture,
            TimeTracking,
            Prestation,
            OperationTVA,
            LigneTVA,
            DeclarationTVA,
            CodeTVA,
            TauxTVA,
            ConfigurationTVA,
            EcritureComptable,
            PieceComptable,
            Journal,
            Compte,
            PlanComptable,
            Tache,
            Notification,
            ExerciceComptable,
            Mandat,
            Contact,
            Client,
            Adresse,
        ]

        for model in models_to_clean:
            try:
                deleted, _ = model.objects.all().delete()
                if deleted:
                    self.stdout.write(f"  → {model.__name__}: {deleted} supprimés")
            except Exception:
                # Fallback: TRUNCATE CASCADE si le delete ORM échoue
                table = model._meta.db_table
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                    self.stdout.write(f"  → {model.__name__}: truncated (cascade)")
                except Exception as e2:
                    self.stdout.write(f"  ⚠ {model.__name__}: {e2}")

    # =========================================================================
    # HELPERS POUR TRADUCTIONS
    # =========================================================================

    def _get_translated_text(self, base_text_fr, max_chars=None):
        """Génère un texte traduit dans les 4 langues"""
        texts = {
            "fr": base_text_fr,
            "de": self.fake_de.text(max_nb_chars=max_chars)
            if max_chars
            else self.fake_de.text(),
            "it": self.fake_it.text(max_nb_chars=max_chars)
            if max_chars
            else self.fake_it.text(),
            "en": self.fake_en.text(max_nb_chars=max_chars)
            if max_chars
            else self.fake_en.text(),
        }
        return texts

    def _get_translated_sentence(self, base_fr, nb_words=6):
        """Génère une phrase traduite"""
        return {
            "fr": base_fr,
            "de": self.fake_de.sentence(nb_words=nb_words),
            "it": self.fake_it.sentence(nb_words=nb_words),
            "en": self.fake_en.sentence(nb_words=nb_words),
        }

    # =========================================================================
    # CORE MODELS
    # =========================================================================

    def _create_users(self):
        """Crée les utilisateurs de la fiduciaire"""
        from core.models import Role
        UserModel = get_user_model()

        self.stdout.write("👥 Création des utilisateurs...")

        # Créer les rôles s'ils n'existent pas
        roles_data = [
            {'code': 'ADMIN', 'nom': 'Administrateur', 'niveau': 100, 'description': 'Accès complet'},
            {'code': 'MANAGER', 'nom': 'Chef de bureau', 'niveau': 80, 'description': 'Gestion des mandats'},
            {'code': 'COMPTABLE', 'nom': 'Comptable', 'niveau': 60, 'description': 'Comptabilité'},
            {'code': 'ASSISTANT', 'nom': 'Assistant', 'niveau': 40, 'description': 'Tâches administratives'},
            {'code': 'CLIENT', 'nom': 'Client', 'niveau': 10, 'description': 'Portail client'},
        ]
        for rd in roles_data:
            Role.objects.get_or_create(
                code=rd['code'],
                defaults={'nom': rd['nom'], 'niveau': rd['niveau'], 'description': rd['description'], 'actif': True}
            )

        # Pré-charger les rôles
        roles = {r.code: r for r in Role.objects.filter(actif=True)}

        users_data = [
            {
                "username": "admin",
                "role_code": "ADMIN",
                "first_name": "Admin",
                "last_name": "System",
            },
            {
                "username": "pierre.muller",
                "role_code": "MANAGER",
                "first_name": "Pierre",
                "last_name": "Müller",
            },
            {
                "username": "marie.dubois",
                "role_code": "COMPTABLE",
                "first_name": "Marie",
                "last_name": "Dubois",
            },
            {
                "username": "jean.favre",
                "role_code": "COMPTABLE",
                "first_name": "Jean",
                "last_name": "Favre",
            },
            {
                "username": "anna.schmid",
                "role_code": "ASSISTANT",
                "first_name": "Anna",
                "last_name": "Schmid",
            },
            {
                "username": "luca.rossi",
                "role_code": "ASSISTANT",
                "first_name": "Luca",
                "last_name": "Rossi",
            },
            {
                "username": "sophie.martin",
                "role_code": "COMPTABLE",
                "first_name": "Sophie",
                "last_name": "Martin",
            },
            {
                "username": "marco.bianchi",
                "role_code": "ASSISTANT",
                "first_name": "Marco",
                "last_name": "Bianchi",
            },
        ]

        users = []
        for data in users_data:
            role = roles.get(data["role_code"])
            user, created = UserModel.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": f"{data['username']}@altiusone.ch",
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "role": role,
                    "phone": self.fake.phone_number(),
                    "is_active": True,
                },
            )
            if created:
                user.set_password("Test1234!")
                user.save()
            elif user.role is None and role:
                # Mettre à jour le rôle si non défini
                user.role = role
                user.save(update_fields=['role'])
            users.append(user)

        self.stdout.write(f"  ✓ {len(users)} utilisateurs")
        return users

    def _create_adresses(self):
        """Crée des adresses suisses réalistes"""
        self.stdout.write("📍 Création des adresses...")

        swiss_cities = [
            ("1201", "Genève", "GE"),
            ("1003", "Lausanne", "VD"),
            ("1700", "Fribourg", "FR"),
            ("2000", "Neuchâtel", "NE"),
            ("1950", "Sion", "VS"),
            ("8001", "Zürich", "ZH"),
            ("3001", "Bern", "BE"),
            ("4001", "Basel", "BS"),
            ("6900", "Lugano", "TI"),
            ("9000", "St. Gallen", "SG"),
            ("1205", "Genève", "GE"),
            ("1004", "Lausanne", "VD"),
            ("3011", "Bern", "BE"),
            ("8002", "Zürich", "ZH"),
            ("6901", "Lugano", "TI"),
        ]

        adresses = []
        for _ in range(25):
            city = random.choice(swiss_cities)
            adresse = Adresse.objects.create(
                rue=self.fake.street_name(),
                numero=str(self.fake.building_number()),
                code_postal=city[0],
                localite=city[1],
                canton=city[2],
                pays="CH",
            )
            adresses.append(adresse)

        self.stdout.write(f"  ✓ {len(adresses)} adresses")
        return adresses

    def _create_clients(self, count, users, adresses):
        """Crée des clients suisses réalistes avec traductions"""
        self.stdout.write(f"🏢 Création de {count} clients...")

        company_types = [
            ("SA", ["AG", "SA"]),
            ("SARL", ["GmbH", "Sàrl"]),
            ("EI", []),
            ("SC", ["KG", "SC"]),
        ]

        business_sectors = {
            "consulting": {
                "fr": "Conseil et stratégie",
                "de": "Beratung und Strategie",
                "it": "Consulenza e strategia",
                "en": "Consulting and strategy",
            },
            "tech": {
                "fr": "Solutions technologiques",
                "de": "Technologielösungen",
                "it": "Soluzioni tecnologiche",
                "en": "Technology solutions",
            },
            "commerce": {
                "fr": "Commerce et négoce",
                "de": "Handel und Vertrieb",
                "it": "Commercio e negoziazione",
                "en": "Trade and commerce",
            },
            "immobilier": {
                "fr": "Gestion immobilière",
                "de": "Immobilienverwaltung",
                "it": "Gestione immobiliare",
                "en": "Real estate management",
            },
            "services": {
                "fr": "Services aux entreprises",
                "de": "Unternehmensdienstleistungen",
                "it": "Servizi alle imprese",
                "en": "Business services",
            },
        }

        clients = []
        managers = [u for u in users if u.is_comptable()]

        for _ in range(count):
            form_juridique = random.choice(company_types)
            sector_key = random.choice(list(business_sectors.keys()))
            sector = business_sectors[sector_key]

            base_name = self.fake.last_name()
            company_name = f"{base_name} {sector['fr'].split()[0]}"
            if form_juridique[0] in ["SA", "SARL"]:
                company_name += f" {form_juridique[0]}"

            ide_base = f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}"

            client = Client.objects.create(
                raison_sociale=company_name,
                nom_commercial=company_name,
                forme_juridique=form_juridique[0],
                ide_number=f"CHE-{ide_base}",
                tva_number=f"CHE-{ide_base} TVA" if random.random() > 0.2 else "",
                adresse_siege=random.choice(adresses),
                email=f"info@{base_name.lower()}.ch",
                telephone=self.fake.phone_number(),
                site_web=f"https://www.{base_name.lower()}.ch",
                date_creation=self.fake.date_between(start_date="-15y", end_date="-1y"),
                date_debut_exercice=date(datetime.now().year, 1, 1),
                date_fin_exercice=date(datetime.now().year, 12, 31),
                statut="ACTIF",
                responsable=random.choice(managers),
                description=sector["fr"],
                notes=f"Client depuis {self.fake.year()}. Secteur: {sector['fr']}",
            )
            clients.append(client)

        self.stdout.write(f"  ✓ {len(clients)} clients")
        return clients

    def _create_contacts(self, clients):
        """Crée des contacts pour chaque client"""
        self.stdout.write("👤 Création des contacts...")

        count = 0
        for client in clients:
            for i in range(random.randint(1, 3)):
                contact = Contact.objects.create(
                    client=client,
                    civilite=random.choice(["M", "MME"]),
                    nom=self.fake.last_name(),
                    prenom=self.fake.first_name(),
                    fonction=random.choice(
                        ["DIRECTEUR", "GERANT", "COMPTABLE", "ADMIN"]
                    ),
                    email=self.fake.email(),
                    telephone=self.fake.phone_number(),
                    mobile=self.fake.phone_number(),
                    principal=(i == 0),
                )
                if i == 0:
                    # Use update() to avoid modeltranslation bug with Django 6.0
                    from core.models import Client
                    Client.objects.filter(pk=client.pk).update(contact_principal=contact)
                count += 1

        self.stdout.write(f"  ✓ {count} contacts")

    def _create_mandats(self, clients, users):
        """Crée des mandats avec traductions"""
        self.stdout.write("📋 Création des mandats...")

        # Charger les tables de référence (créées par la migration)
        types_mandat = {t.code: t for t in TypeMandat.objects.all()}
        types_facturation = {t.code: t for t in TypeFacturation.objects.all()}
        periodicites = {p.code: p for p in Periodicite.objects.all()}

        mandat_types = {
            "GLOBAL": {
                "desc_fr": "Mandat global incluant comptabilité, TVA et salaires",
                "desc_de": "Globalmandat einschliesslich Buchhaltung, MWST und Löhne",
                "desc_it": "Mandato globale inclusa contabilità, IVA e salari",
                "desc_en": "Global mandate including accounting, VAT and payroll",
                "cond_fr": "Facturation mensuelle. Délai de paiement 30 jours.",
                "cond_de": "Monatliche Rechnungsstellung. Zahlungsfrist 30 Tage.",
                "cond_it": "Fatturazione mensile. Termine di pagamento 30 giorni.",
                "cond_en": "Monthly billing. Payment term 30 days.",
                "forfait": Decimal("2500"),
                "taux": Decimal("180"),
                "type_facturation": "FORFAIT",
            },
            "COMPTA": {
                "desc_fr": "Tenue de la comptabilité et établissement des comptes annuels",
                "desc_de": "Buchhaltung und Erstellung des Jahresabschlusses",
                "desc_it": "Tenuta della contabilità e redazione del bilancio annuale",
                "desc_en": "Bookkeeping and preparation of annual accounts",
                "cond_fr": "Remise des pièces avant le 10 du mois.",
                "cond_de": "Abgabe der Belege vor dem 10. des Monats.",
                "cond_it": "Consegna dei documenti entro il 10 del mese.",
                "cond_en": "Documents to be submitted before the 10th of the month.",
                "forfait": Decimal("1500"),
                "taux": Decimal("150"),
                "type_facturation": "FORFAIT",
            },
            "SALAIRES": {
                "desc_fr": "Gestion complète des salaires et déclarations sociales",
                "desc_de": "Komplette Lohnbuchhaltung und Sozialversicherungsabrechnungen",
                "desc_it": "Gestione completa dei salari e dichiarazioni sociali",
                "desc_en": "Complete payroll management and social declarations",
                "cond_fr": "Données salariales à fournir avant le 25 du mois.",
                "cond_de": "Lohndaten sind vor dem 25. des Monats zu liefern.",
                "cond_it": "Dati salariali da fornire entro il 25 del mese.",
                "cond_en": "Salary data to be provided before the 25th of the month.",
                "forfait": Decimal("800"),
                "taux": Decimal("120"),
                "type_facturation": "FORFAIT",
            },
            "TVA": {
                "desc_fr": "Établissement des décomptes TVA trimestriels",
                "desc_de": "Erstellung der vierteljährlichen MWST-Abrechnungen",
                "desc_it": "Preparazione dei conteggi IVA trimestrali",
                "desc_en": "Preparation of quarterly VAT returns",
                "cond_fr": "Pièces justificatives classées par période.",
                "cond_de": "Belege nach Zeitraum sortiert.",
                "cond_it": "Documenti giustificativi ordinati per periodo.",
                "cond_en": "Supporting documents sorted by period.",
                "forfait": Decimal("500"),
                "taux": Decimal("140"),
                "type_facturation": "FORFAIT",
            },
            "FISCAL": {
                "desc_fr": "Conseil fiscal et optimisation",
                "desc_de": "Steuerberatung und Optimierung",
                "desc_it": "Consulenza fiscale e ottimizzazione",
                "desc_en": "Tax consulting and optimization",
                "cond_fr": "Tarif horaire selon complexité du dossier.",
                "cond_de": "Stundensatz je nach Komplexität des Falls.",
                "cond_it": "Tariffa oraria secondo la complessità del caso.",
                "cond_en": "Hourly rate depending on case complexity.",
                "forfait": None,
                "taux": Decimal("200"),
                "type_facturation": "HORAIRE",
            },
        }

        mandats = []
        managers = [u for u in users if u.is_comptable()]

        for client in clients:
            num_mandats = random.randint(1, 2)
            selected_types = random.sample(
                list(mandat_types.keys()), min(num_mandats, len(mandat_types))
            )

            for type_key in selected_types:
                type_data = mandat_types[type_key]
                periodicite_code = random.choice(["MENSUEL", "TRIMESTRIEL"])

                mandat = Mandat.objects.create(
                    client=client,
                    # Nouveaux champs ForeignKey
                    type_mandat_ref=types_mandat.get(type_key),
                    periodicite_ref=periodicites.get(periodicite_code),
                    type_facturation_ref=types_facturation.get(type_data["type_facturation"]),
                    # Anciens champs pour compatibilité
                    type_mandat=type_key,
                    periodicite=periodicite_code,
                    type_facturation=type_data["type_facturation"],
                    # Autres champs
                    date_debut=self.fake.date_between(start_date="-3y", end_date="-6m"),
                    budget_prevu=type_data["forfait"],
                    taux_horaire=type_data["taux"],
                    responsable=random.choice(managers),
                    statut="ACTIF",
                    description=type_data["desc_fr"],
                    conditions_particulieres=type_data["cond_fr"],
                )

                team_size = random.randint(1, 3)
                mandat.equipe.add(*random.sample(users, min(team_size, len(users))))
                mandats.append(mandat)

        self.stdout.write(f"  ✓ {len(mandats)} mandats")
        return mandats

    def _create_exercices(self, mandats):
        """Crée des exercices comptables"""
        self.stdout.write("📅 Création des exercices...")

        count = 0
        for mandat in mandats:
            for year in [2023, 2024, 2025]:
                ExerciceComptable.objects.create(
                    mandat=mandat,
                    annee=year,
                    date_debut=date(year, 1, 1),
                    date_fin=date(year, 12, 31),
                    statut="OUVERT" if year >= 2024 else "CLOTURE_DEFINITIVE",
                    resultat_exercice=Decimal(str(random.randint(-10000, 100000)))
                    if year < 2025
                    else None,
                )
                count += 1

        self.stdout.write(f"  ✓ {count} exercices")

    def _create_notifications(self, users, mandats):
        """Crée des notifications avec traductions"""
        self.stdout.write("🔔 Création des notifications...")

        notification_templates = [
            {
                "type": "INFO",
                "titre_fr": "Nouvelle pièce comptable reçue",
                "titre_de": "Neuer Buchungsbeleg eingegangen",
                "titre_it": "Nuovo documento contabile ricevuto",
                "titre_en": "New accounting document received",
                "message_fr": "Une nouvelle pièce comptable a été ajoutée au dossier.",
                "message_de": "Ein neuer Buchungsbeleg wurde zur Akte hinzugefügt.",
                "message_it": "Un nuovo documento contabile è stato aggiunto al fascicolo.",
                "message_en": "A new accounting document has been added to the file.",
            },
            {
                "type": "WARNING",
                "titre_fr": "Échéance TVA proche",
                "titre_de": "MWST-Frist nähert sich",
                "titre_it": "Scadenza IVA imminente",
                "titre_en": "VAT deadline approaching",
                "message_fr": "Le décompte TVA doit être soumis dans 5 jours.",
                "message_de": "Die MWST-Abrechnung muss in 5 Tagen eingereicht werden.",
                "message_it": "Il conteggio IVA deve essere presentato entro 5 giorni.",
                "message_en": "VAT return must be submitted in 5 days.",
            },
            {
                "type": "SUCCESS",
                "titre_fr": "Paiement reçu",
                "titre_de": "Zahlung eingegangen",
                "titre_it": "Pagamento ricevuto",
                "titre_en": "Payment received",
                "message_fr": "Le paiement de la facture a été confirmé.",
                "message_de": "Die Zahlung der Rechnung wurde bestätigt.",
                "message_it": "Il pagamento della fattura è stato confermato.",
                "message_en": "Invoice payment has been confirmed.",
            },
        ]

        count = 0
        for _ in range(30):
            template = random.choice(notification_templates)
            Notification.objects.create(
                destinataire=random.choice(users),
                type_notification=template["type"],
                titre=template["titre_fr"],
                message=template["message_fr"],
                lue=random.choice([True, False]),
                mandat=random.choice(mandats) if random.random() > 0.3 else None,
            )
            count += 1

        self.stdout.write(f"  ✓ {count} notifications")

    def _create_taches(self, users, mandats):
        """Crée des tâches avec traductions"""
        self.stdout.write("✅ Création des tâches...")

        tache_templates = [
            {
                "titre_fr": "Saisie des écritures comptables",
                "titre_de": "Erfassung der Buchungen",
                "titre_it": "Registrazione delle scritture contabili",
                "titre_en": "Entry of accounting records",
                "desc_fr": "Saisir les écritures du mois dans le système comptable.",
                "desc_de": "Erfassen Sie die Buchungen des Monats im Buchhaltungssystem.",
                "desc_it": "Inserire le registrazioni del mese nel sistema contabile.",
                "desc_en": "Enter the month's entries into the accounting system.",
            },
            {
                "titre_fr": "Préparation du décompte TVA",
                "titre_de": "Vorbereitung der MWST-Abrechnung",
                "titre_it": "Preparazione del conteggio IVA",
                "titre_en": "Preparation of VAT return",
                "desc_fr": "Préparer le décompte TVA trimestriel pour soumission à l'AFC.",
                "desc_de": "Bereiten Sie die vierteljährliche MWST-Abrechnung für die ESTV vor.",
                "desc_it": "Preparare il conteggio IVA trimestrale per l'AFC.",
                "desc_en": "Prepare quarterly VAT return for submission to the FTA.",
            },
            {
                "titre_fr": "Rapprochement bancaire",
                "titre_de": "Bankabstimmung",
                "titre_it": "Riconciliazione bancaria",
                "titre_en": "Bank reconciliation",
                "desc_fr": "Effectuer le rapprochement des comptes bancaires.",
                "desc_de": "Führen Sie den Bankabgleich durch.",
                "desc_it": "Effettuare la riconciliazione dei conti bancari.",
                "desc_en": "Perform bank account reconciliation.",
            },
            {
                "titre_fr": "Calcul des salaires",
                "titre_de": "Lohnberechnung",
                "titre_it": "Calcolo dei salari",
                "titre_en": "Payroll calculation",
                "desc_fr": "Calculer les salaires du mois et préparer les fiches de paie.",
                "desc_de": "Berechnen Sie die Monatslöhne und erstellen Sie die Lohnabrechnungen.",
                "desc_it": "Calcolare i salari del mese e preparare le buste paga.",
                "desc_en": "Calculate monthly salaries and prepare pay slips.",
            },
        ]

        count = 0
        for _ in range(40):
            template = random.choice(tache_templates)
            Tache.objects.create(
                titre=template["titre_fr"],
                description=template["desc_fr"],
                assigne_a=random.choice(users),
                cree_par=random.choice(users),
                mandat=random.choice(mandats),
                priorite=random.choice(["BASSE", "NORMALE", "HAUTE", "URGENTE"]),
                date_echeance=self.fake.date_between(
                    start_date="today", end_date="+30d"
                ),
                statut=random.choice(["A_FAIRE", "EN_COURS", "TERMINEE"]),
                temps_estime_heures=Decimal(str(random.randint(1, 16))),
            )
            count += 1

        self.stdout.write(f"  ✓ {count} tâches")

    # =========================================================================
    # COMPTABILITÉ
    # =========================================================================

    def _create_plans_comptables(self, mandats):
        """Crée des plans comptables avec traductions"""
        self.stdout.write("📊 Création des plans comptables...")

        compta_mandats = [m for m in mandats if m.type_mandat in ["COMPTA", "GLOBAL"]]

        # Récupérer le type de plan PME
        from comptabilite.models import TypePlanComptable
        type_pme = TypePlanComptable.objects.filter(code="PME").first()

        for mandat in compta_mandats[:5]:
            plan = PlanComptable.objects.create(
                nom=f"Plan comptable PME - {mandat.client.raison_sociale}",
                description="Plan comptable selon le modèle PME suisse",
                type_plan=type_pme,
                mandat=mandat,
            )

            # Créer les comptes de base
            self._create_comptes_for_plan(plan)

        self.stdout.write(f"  ✓ {len(compta_mandats[:5])} plans comptables")

    def _create_comptes_for_plan(self, plan):
        """Crée les comptes de base pour un plan comptable"""
        comptes_base = [
            ("1000", "Caisse", "Kasse", "Cassa", "Cash", "ACTIF", 1),
            ("1020", "Banque", "Bank", "Banca", "Bank", "ACTIF", 1),
            ("1100", "Débiteurs", "Debitoren", "Debitori", "Debtors", "ACTIF", 1),
            (
                "1170",
                "Impôt préalable TVA",
                "Vorsteuer MWST",
                "IVA a credito",
                "Input VAT",
                "ACTIF",
                1,
            ),
            ("2000", "Créanciers", "Kreditoren", "Creditori", "Creditors", "PASSIF", 2),
            (
                "2200",
                "TVA due",
                "Geschuldete MWST",
                "IVA dovuta",
                "Output VAT",
                "PASSIF",
                2,
            ),
            ("2800", "Capital", "Kapital", "Capitale", "Capital", "PASSIF", 2),
            ("3000", "Ventes", "Verkäufe", "Vendite", "Sales", "PRODUIT", 7),
            (
                "3200",
                "Ventes marchandises",
                "Warenverkäufe",
                "Vendite merci",
                "Goods sales",
                "PRODUIT",
                7,
            ),
            (
                "4000",
                "Achats matières",
                "Materialeinkauf",
                "Acquisti materiali",
                "Material purchases",
                "CHARGE",
                6,
            ),
            ("5000", "Salaires", "Löhne", "Salari", "Wages", "CHARGE", 6),
            (
                "5700",
                "Charges sociales",
                "Sozialaufwand",
                "Oneri sociali",
                "Social charges",
                "CHARGE",
                6,
            ),
            ("6000", "Loyers", "Mieten", "Affitti", "Rent", "CHARGE", 6),
            (
                "6500",
                "Administration",
                "Verwaltung",
                "Amministrazione",
                "Administration",
                "CHARGE",
                6,
            ),
            (
                "6800",
                "Amortissements",
                "Abschreibungen",
                "Ammortamenti",
                "Depreciation",
                "CHARGE",
                6,
            ),
            (
                "6900",
                "Charges financières",
                "Finanzaufwand",
                "Oneri finanziari",
                "Financial expenses",
                "CHARGE",
                6,
            ),
        ]

        for numero, lib_fr, lib_de, lib_it, lib_en, type_compte, classe in comptes_base:
            Compte.objects.create(
                plan_comptable=plan,
                numero=numero,
                libelle=lib_fr,
                libelle_court=lib_fr,
                type_compte=type_compte,
                classe=classe,
                niveau=len(numero),
                imputable=True,
            )

    def _create_journaux(self, mandats):
        """Crée les journaux comptables"""
        self.stdout.write("📔 Création des journaux...")

        journaux_types = [
            ("VTE", "Ventes", "VTE"),
            ("ACH", "Achats", "ACH"),
            ("BNQ", "Banque", "BNQ"),
            ("CAS", "Caisse", "CAS"),
            ("OD", "Opérations diverses", "OD"),
        ]

        count = 0
        compta_mandats = [m for m in mandats if m.type_mandat in ["COMPTA", "GLOBAL"]]

        for mandat in compta_mandats:
            for code, libelle, type_j in journaux_types:
                Journal.objects.create(
                    mandat=mandat,
                    code=code,
                    libelle=libelle,
                    type_journal=type_j,
                    numerotation_auto=True,
                    prefixe_piece=code,
                )
                count += 1

        self.stdout.write(f"  ✓ {count} journaux")

    def _create_ecritures(self, mandats):
        """Crée des écritures comptables"""
        self.stdout.write("📝 Création des écritures...")

        count = 0
        compta_mandats = [m for m in mandats if m.type_mandat in ["COMPTA", "GLOBAL"]][
            :3
        ]

        for mandat in compta_mandats:
            journal = Journal.objects.filter(mandat=mandat, type_journal="VTE").first()
            exercice = ExerciceComptable.objects.filter(
                mandat=mandat, statut="OUVERT"
            ).first()
            comptes = Compte.objects.filter(plan_comptable__mandat=mandat)

            if journal and exercice and comptes.exists():
                for i in range(20):
                    compte = random.choice(list(comptes))
                    montant = Decimal(str(random.randint(100, 5000)))
                    is_debit = random.random() > 0.5

                    EcritureComptable.objects.create(
                        mandat=mandat,
                        exercice=exercice,
                        journal=journal,
                        numero_piece=f"{journal.prefixe_piece}{i + 1:05d}",
                        numero_ligne=1,
                        date_ecriture=self.fake.date_between(
                            start_date="-60d", end_date="today"
                        ),
                        compte=compte,
                        libelle=self.fake.sentence(nb_words=6),
                        montant_debit=montant if is_debit else Decimal("0"),
                        montant_credit=Decimal("0") if is_debit else montant,
                        statut="VALIDE",
                    )
                    count += 1

        self.stdout.write(f"  ✓ {count} écritures")

    # =========================================================================
    # TVA
    # =========================================================================

    def _create_taux_tva(self):
        """Crée les taux TVA suisses officiels"""
        self.stdout.write("💰 Création des taux TVA...")

        from tva.models import RegimeFiscal
        ch_regime = RegimeFiscal.objects.filter(code='CH').first()

        taux = [
            ("NORMAL", Decimal("8.1"), "Taux normal TVA Suisse"),
            ("REDUIT", Decimal("2.6"), "Taux réduit TVA Suisse"),
            ("SPECIAL", Decimal("3.8"), "Taux spécial hébergement"),
        ]

        for type_taux, valeur, description in taux:
            defaults = {
                "taux": valeur,
                "description": description,
            }
            lookup = {
                "type_taux": type_taux,
                "date_debut": date(2024, 1, 1),
            }
            if ch_regime:
                lookup["regime"] = ch_regime
            TauxTVA.objects.get_or_create(**lookup, defaults=defaults)

        self.stdout.write(f"  ✓ {len(taux)} taux TVA")

    def _create_codes_tva(self):
        """Crée les codes TVA avec traductions"""
        self.stdout.write("🏷️ Création des codes TVA...")

        from tva.models import RegimeFiscal
        ch_regime = RegimeFiscal.objects.filter(code='CH').first()

        codes = [
            {
                "code": "200",
                "libelle_fr": "Prestations au taux normal",
                "libelle_de": "Leistungen zum Normalsatz",
                "libelle_it": "Prestazioni all'aliquota normale",
                "libelle_en": "Services at standard rate",
                "categorie": "PRESTATIONS_IMPOSABLES",
            },
            {
                "code": "205",
                "libelle_fr": "Prestations au taux réduit",
                "libelle_de": "Leistungen zum reduzierten Satz",
                "libelle_it": "Prestazioni all'aliquota ridotta",
                "libelle_en": "Services at reduced rate",
                "categorie": "PRESTATIONS_IMPOSABLES",
            },
            {
                "code": "220",
                "libelle_fr": "Prestations d'hébergement",
                "libelle_de": "Beherbergungsleistungen",
                "libelle_it": "Prestazioni di alloggio",
                "libelle_en": "Accommodation services",
                "categorie": "PRESTATIONS_IMPOSABLES",
            },
            {
                "code": "400",
                "libelle_fr": "Impôt préalable sur matériel",
                "libelle_de": "Vorsteuer auf Material",
                "libelle_it": "Imposta precedente su materiale",
                "libelle_en": "Input tax on materials",
                "categorie": "TVA_PREALABLE",
            },
            {
                "code": "405",
                "libelle_fr": "Impôt préalable sur investissements",
                "libelle_de": "Vorsteuer auf Investitionen",
                "libelle_it": "Imposta precedente su investimenti",
                "libelle_en": "Input tax on investments",
                "categorie": "TVA_PREALABLE",
            },
        ]

        for code_data in codes:
            lookup = {"code": code_data["code"]}
            if ch_regime:
                lookup["regime"] = ch_regime
            CodeTVA.objects.get_or_create(
                **lookup,
                defaults={
                    "libelle": code_data["libelle_fr"],
                    "categorie": code_data["categorie"],
                    "actif": True,
                },
            )

        self.stdout.write(f"  ✓ {len(codes)} codes TVA")

    def _create_config_tva(self, mandats):
        """Crée les configurations TVA"""
        self.stdout.write("⚙️ Configuration TVA...")

        from tva.models import RegimeFiscal
        ch_regime = RegimeFiscal.objects.filter(code='CH').first()

        count = 0
        tva_mandats = [
            m for m in mandats if m.type_mandat in ["TVA", "COMPTA", "GLOBAL"]
        ]

        for mandat in tva_mandats[:5]:
            defaults = {
                "assujetti_tva": True,
                "numero_tva": f"CHE-{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)} TVA",
                "date_debut_assujettissement": self.fake.date_between(
                    start_date="-5y", end_date="-1y"
                ),
                "methode_calcul": "EFFECTIVE",
                "periodicite": "TRIMESTRIEL",
            }
            if ch_regime:
                defaults["regime"] = ch_regime
            ConfigurationTVA.objects.get_or_create(
                mandat=mandat,
                defaults=defaults,
            )
            count += 1

        self.stdout.write(f"  ✓ {count} configurations TVA")

    def _create_declarations_tva(self, mandats):
        """Crée des déclarations TVA"""
        self.stdout.write("📄 Création des déclarations TVA...")

        count = 0
        mandats_with_tva = Mandat.objects.filter(config_tva__isnull=False)[:3]

        for mandat in mandats_with_tva:
            for trimestre in [1, 2, 3, 4]:
                DeclarationTVA.objects.create(
                    mandat=mandat,
                    numero_declaration=f"TVA-{mandat.id}-2024-T{trimestre}",
                    annee=2024,
                    trimestre=trimestre,
                    periode_debut=date(2024, (trimestre - 1) * 3 + 1, 1),
                    periode_fin=date(2024, trimestre * 3, 28),
                    type_decompte="NORMAL",
                    methode="EFFECTIVE",
                    chiffre_affaires_total=Decimal(str(random.randint(50000, 200000))),
                    chiffre_affaires_imposable=Decimal(
                        str(random.randint(40000, 180000))
                    ),
                    tva_due_total=Decimal(str(random.randint(3000, 15000))),
                    tva_prealable_total=Decimal(str(random.randint(1000, 8000))),
                    statut="VALIDE" if trimestre < 4 else "BROUILLON",
                )
                count += 1

        self.stdout.write(f"  ✓ {count} déclarations TVA")

    # =========================================================================
    # FACTURATION
    # =========================================================================

    def _create_prestations(self):
        """Crée des prestations avec traductions"""
        self.stdout.write("🛠️ Création des prestations...")

        prestations = [
            {
                "code": "COMPTA-STD",
                "libelle_fr": "Comptabilité courante",
                "libelle_de": "Laufende Buchhaltung",
                "libelle_it": "Contabilità corrente",
                "libelle_en": "Current accounting",
                "desc_fr": "Saisie des écritures et tenue des comptes",
                "desc_de": "Erfassung der Buchungen und Kontenführung",
                "desc_it": "Registrazione delle scritture e tenuta dei conti",
                "desc_en": "Entry of records and account management",
                "type": "COMPTABILITE",
                "prix": Decimal("150"),
            },
            {
                "code": "TVA-DEC",
                "libelle_fr": "Décompte TVA trimestriel",
                "libelle_de": "MWST-Quartalsabrechnung",
                "libelle_it": "Conteggio IVA trimestrale",
                "libelle_en": "Quarterly VAT return",
                "desc_fr": "Préparation et soumission du décompte TVA",
                "desc_de": "Vorbereitung und Einreichung der MWST-Abrechnung",
                "desc_it": "Preparazione e presentazione del conteggio IVA",
                "desc_en": "Preparation and submission of VAT return",
                "type": "TVA",
                "prix": Decimal("250"),
            },
            {
                "code": "SAL-CALC",
                "libelle_fr": "Calcul des salaires",
                "libelle_de": "Lohnberechnung",
                "libelle_it": "Calcolo dei salari",
                "libelle_en": "Payroll calculation",
                "desc_fr": "Calcul mensuel des salaires et charges sociales",
                "desc_de": "Monatliche Lohn- und Sozialversicherungsberechnung",
                "desc_it": "Calcolo mensile dei salari e oneri sociali",
                "desc_en": "Monthly payroll and social charges calculation",
                "type": "SALAIRES",
                "prix": Decimal("120"),
            },
            {
                "code": "CONSEIL-FIS",
                "libelle_fr": "Conseil fiscal",
                "libelle_de": "Steuerberatung",
                "libelle_it": "Consulenza fiscale",
                "libelle_en": "Tax consulting",
                "desc_fr": "Conseil et optimisation fiscale",
                "desc_de": "Steuerberatung und -optimierung",
                "desc_it": "Consulenza e ottimizzazione fiscale",
                "desc_en": "Tax consulting and optimization",
                "type": "CONSEIL",
                "prix": Decimal("200"),
            },
            {
                "code": "AUDIT-REV",
                "libelle_fr": "Révision des comptes",
                "libelle_de": "Revision der Jahresrechnung",
                "libelle_it": "Revisione dei conti",
                "libelle_en": "Accounts audit",
                "desc_fr": "Révision et contrôle des comptes annuels",
                "desc_de": "Revision und Kontrolle der Jahresrechnung",
                "desc_it": "Revisione e controllo dei conti annuali",
                "desc_en": "Annual accounts review and audit",
                "type": "AUDIT",
                "prix": Decimal("180"),
            },
        ]

        from facturation.models import TypePrestation

        for p in prestations:
            type_obj = TypePrestation.objects.get(code=p["type"])
            Prestation.objects.get_or_create(
                code=p["code"],
                defaults={
                    "libelle": p["libelle_fr"],
                    "description": p["desc_fr"],
                    "type_prestation": type_obj,
                    "prix_unitaire_ht": p["prix"],
                    "unite": "heure",
                    "taux_horaire": p["prix"],
                    "soumis_tva": True,
                    "taux_tva_defaut": Decimal("8.1"),
                    "actif": True,
                },
            )

        self.stdout.write(f"  ✓ {len(prestations)} prestations")

    def _create_time_tracking(self, mandats, users):
        """Crée des entrées de suivi du temps"""
        self.stdout.write("⏱️ Création du time tracking...")

        count = 0
        prestations = list(Prestation.objects.all())
        comptables = [u for u in users if u.role and u.role.niveau >= 40]  # ASSISTANT and above

        for mandat in mandats[:5]:
            for _ in range(random.randint(5, 15)):
                prestation = random.choice(prestations)
                duree = random.randint(15, 480)
                taux = prestation.taux_horaire

                TimeTracking.objects.create(
                    mandat=mandat,
                    utilisateur=random.choice(comptables),
                    prestation=prestation,
                    date_travail=self.fake.date_between(
                        start_date="-60d", end_date="today"
                    ),
                    duree_minutes=duree,
                    description=f"Travail sur {prestation.libelle}",
                    facturable=True,
                    taux_horaire=taux,
                    montant_ht=(Decimal(duree) / Decimal("60") * taux).quantize(
                        Decimal("0.01")
                    ),
                )
                count += 1

        self.stdout.write(f"  ✓ {count} entrées time tracking")

    def _create_factures(self, mandats):
        """Crée des factures"""
        self.stdout.write("🧾 Création des factures...")

        count = 0
        prestations = list(Prestation.objects.all())

        for mandat in mandats[:5]:
            for _ in range(random.randint(2, 4)):
                facture = Facture.objects.create(
                    mandat=mandat,
                    client=mandat.client,
                    type_facture="FACTURE",
                    date_emission=self.fake.date_between(
                        start_date="-90d", end_date="today"
                    ),
                    date_echeance=self.fake.date_between(
                        start_date="today", end_date="+30d"
                    ),
                    montant_ht=Decimal("0"),
                    montant_tva=Decimal("0"),
                    montant_ttc=Decimal("0"),
                    delai_paiement_jours=30,
                    statut=random.choice(["EMISE", "PAYEE", "BROUILLON"]),
                    creee_par=mandat.responsable,
                    introduction="Nous vous prions de trouver ci-joint notre facture.",
                    conclusion="Nous vous remercions de votre confiance.",
                )

                # Créer les lignes
                for j in range(random.randint(1, 4)):
                    prestation = random.choice(prestations)
                    quantite = Decimal(str(random.randint(1, 10)))
                    prix = prestation.prix_unitaire_ht

                    LigneFacture.objects.create(
                        facture=facture,
                        ordre=j + 1,
                        prestation=prestation,
                        description=f"{prestation.libelle} - {self.fake.sentence(nb_words=4)}",
                        quantite=quantite,
                        unite=prestation.unite,
                        prix_unitaire_ht=prix,
                        montant_ht=quantite * prix,
                        taux_tva=prestation.taux_tva_defaut,
                        remise_pourcent=Decimal("0"),
                    )

                facture.calculer_totaux()
                count += 1

        self.stdout.write(f"  ✓ {count} factures")

    def _create_paiements(self):
        """Crée des paiements pour les factures payées"""
        self.stdout.write("💳 Création des paiements...")

        count = 0
        factures_payees = Facture.objects.filter(statut="PAYEE")

        for facture in factures_payees:
            Paiement.objects.create(
                facture=facture,
                montant=facture.montant_ttc,
                date_paiement=self.fake.date_between(
                    start_date=facture.date_emission, end_date="today"
                ),
                mode_paiement=random.choice(["VIREMENT", "QR_BILL"]),
                reference=f"REF-{random.randint(10000, 99999)}",
                valide=True,
            )
            count += 1

        self.stdout.write(f"  ✓ {count} paiements")

    # =========================================================================
    # SALAIRES
    # =========================================================================

    def _create_taux_cotisations(self):
        """Crée les taux de cotisations sociales suisses"""
        self.stdout.write("📊 Création des taux de cotisations...")

        # Taux exprimés en décimal (0.053 = 5.3%)
        cotisations = [
            ("AVS", "AVS/AI/APG", Decimal("0.106"), Decimal("0.053"), Decimal("0.053")),
            ("AC", "Assurance chômage", Decimal("0.022"), Decimal("0.011"), Decimal("0.011")),
            ("AC_SUPP", "AC supplément (>148'200)", Decimal("0.010"), Decimal("0.005"), Decimal("0.005")),
            ("LPP", "Prévoyance professionnelle", Decimal("0.150"), Decimal("0.075"), Decimal("0.075")),
            ("LAA", "Assurance accidents", Decimal("0.015"), Decimal("0.015"), Decimal("0.000")),
            ("IJM", "Indemnités journalières maladie", Decimal("0.014"), Decimal("0.007"), Decimal("0.007")),
            ("AF", "Allocations familiales", Decimal("0.020"), Decimal("0.020"), Decimal("0.000")),
        ]

        for type_cot, libelle, total, employeur, employe in cotisations:
            TauxCotisation.objects.get_or_create(
                type_cotisation=type_cot,
                defaults={
                    "libelle": libelle,
                    "taux_total": total,
                    "taux_employeur": employeur,
                    "taux_employe": employe,
                    "repartition": "PARTAGE" if employe > 0 else "EMPLOYEUR",
                    "date_debut": date(2024, 1, 1),
                    "actif": True,
                },
            )

        self.stdout.write(f"  ✓ {len(cotisations)} taux de cotisations")

    def _create_employes(self, mandats, adresses):
        """Crée des employés avec traductions"""
        self.stdout.write("👥 Création des employés...")

        fonctions = {
            "comptable": {
                "fr": "Comptable",
                "de": "Buchhalter/in",
                "it": "Contabile",
                "en": "Accountant",
            },
            "assistant": {
                "fr": "Assistant(e) comptable",
                "de": "Buchhaltungsassistent/in",
                "it": "Assistente contabile",
                "en": "Accounting assistant",
            },
            "directeur": {
                "fr": "Directeur financier",
                "de": "Finanzleiter/in",
                "it": "Direttore finanziario",
                "en": "Finance director",
            },
            "rh": {
                "fr": "Responsable RH",
                "de": "HR-Verantwortliche/r",
                "it": "Responsabile HR",
                "en": "HR Manager",
            },
            "secretaire": {
                "fr": "Secrétaire",
                "de": "Sekretär/in",
                "it": "Segretario/a",
                "en": "Secretary",
            },
        }

        count = 0
        salaires_mandats = [
            m for m in mandats if m.type_mandat in ["SALAIRES", "GLOBAL"]
        ][:3]
        employe_counter = 0

        for mandat in salaires_mandats:
            for _ in range(random.randint(3, 6)):
                employe_counter += 1
                fonction_key = random.choice(list(fonctions.keys()))
                fonction = fonctions[fonction_key]

                Employe.objects.create(
                    mandat=mandat,
                    matricule=f"EMP{employe_counter:04d}",
                    nom=self.fake.last_name(),
                    prenom=self.fake.first_name(),
                    date_naissance=self.fake.date_of_birth(
                        minimum_age=22, maximum_age=60
                    ),
                    lieu_naissance=self.fake.city()[:100],
                    nationalite="CH",
                    sexe=random.choice(["M", "F"]),
                    avs_number=f"756.{random.randint(1000, 9999)}.{random.randint(1000, 9999)}.{random.randint(10, 99)}",
                    adresse=random.choice(adresses),
                    email=self.fake.email(),
                    telephone=self.fake.phone_number(),
                    etat_civil=random.choice(["CELIBATAIRE", "MARIE", "DIVORCE"]),
                    type_contrat="CDI",
                    date_entree=self.fake.date_between(
                        start_date="-5y", end_date="-1m"
                    ),
                    fonction=fonction["fr"],
                    taux_occupation=Decimal("100"),
                    salaire_brut_mensuel=Decimal(str(random.randint(4500, 9000))),
                    nombre_heures_semaine=Decimal("42"),
                    jours_vacances_annuel=25,
                    treizieme_salaire=True,
                    iban=self.fake.iban(),
                    statut="ACTIF",
                )
                count += 1

        self.stdout.write(f"  ✓ {count} employés")

    def _create_fiches_salaire(self):
        """Crée des fiches de salaire"""
        self.stdout.write("💵 Création des fiches de salaire...")

        count = 0
        employes = Employe.objects.all()[:10]

        for employe in employes:
            for mois in range(1, 5):  # Janvier à Avril 2025
                salaire_base = employe.salaire_brut_mensuel
                avs = (salaire_base * Decimal("5.3") / 100).quantize(Decimal("0.01"))
                ac = (salaire_base * Decimal("1.1") / 100).quantize(Decimal("0.01"))
                lpp = (salaire_base * Decimal("7.5") / 100).quantize(Decimal("0.01"))
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
                    statut="VALIDE" if mois < 4 else "BROUILLON",
                )
                count += 1

        self.stdout.write(f"  ✓ {count} fiches de salaire")

    # =========================================================================
    # DOCUMENTS
    # =========================================================================

    def _create_categories_documents(self):
        """Crée les catégories de documents avec traductions"""
        self.stdout.write("📁 Création des catégories de documents...")

        categories = [
            {
                "nom_fr": "Factures",
                "nom_de": "Rechnungen",
                "nom_it": "Fatture",
                "nom_en": "Invoices",
                "desc_fr": "Documents de facturation clients et fournisseurs",
                "desc_de": "Rechnungsdokumente für Kunden und Lieferanten",
                "desc_it": "Documenti di fatturazione clienti e fornitori",
                "desc_en": "Customer and supplier invoicing documents",
            },
            {
                "nom_fr": "Contrats",
                "nom_de": "Verträge",
                "nom_it": "Contratti",
                "nom_en": "Contracts",
                "desc_fr": "Documents contractuels",
                "desc_de": "Vertragsdokumente",
                "desc_it": "Documenti contrattuali",
                "desc_en": "Contractual documents",
            },
            {
                "nom_fr": "Comptabilité",
                "nom_de": "Buchhaltung",
                "nom_it": "Contabilità",
                "nom_en": "Accounting",
                "desc_fr": "Documents comptables et pièces justificatives",
                "desc_de": "Buchhaltungsunterlagen und Belege",
                "desc_it": "Documenti contabili e giustificativi",
                "desc_en": "Accounting documents and supporting evidence",
            },
            {
                "nom_fr": "TVA",
                "nom_de": "MWST",
                "nom_it": "IVA",
                "nom_en": "VAT",
                "desc_fr": "Documents relatifs à la TVA",
                "desc_de": "MWST-bezogene Dokumente",
                "desc_it": "Documenti relativi all'IVA",
                "desc_en": "VAT-related documents",
            },
            {
                "nom_fr": "Salaires",
                "nom_de": "Löhne",
                "nom_it": "Salari",
                "nom_en": "Payroll",
                "desc_fr": "Fiches de salaire et déclarations sociales",
                "desc_de": "Lohnabrechnungen und Sozialversicherungsmeldungen",
                "desc_it": "Buste paga e dichiarazioni sociali",
                "desc_en": "Pay slips and social declarations",
            },
        ]

        for i, cat in enumerate(categories):
            CategorieDocument.objects.get_or_create(
                nom=cat["nom_fr"],
                defaults={
                    "description": cat["desc_fr"],
                    "ordre": i + 1,
                },
            )

        self.stdout.write(f"  ✓ {len(categories)} catégories")

    def _create_types_documents(self):
        """Crée les types de documents avec traductions"""
        self.stdout.write("📑 Création des types de documents...")

        types = [
            {
                "code": "FAC_VENTE",
                "libelle_fr": "Facture de vente",
                "libelle_de": "Verkaufsrechnung",
                "libelle_it": "Fattura di vendita",
                "libelle_en": "Sales invoice",
                "type": "FACTURE_VENTE",
            },
            {
                "code": "FAC_ACHAT",
                "libelle_fr": "Facture d'achat",
                "libelle_de": "Einkaufsrechnung",
                "libelle_it": "Fattura di acquisto",
                "libelle_en": "Purchase invoice",
                "type": "FACTURE_ACHAT",
            },
            {
                "code": "RELEVE",
                "libelle_fr": "Relevé bancaire",
                "libelle_de": "Kontoauszug",
                "libelle_it": "Estratto conto",
                "libelle_en": "Bank statement",
                "type": "RELEVE_BANQUE",
            },
            {
                "code": "CONTRAT",
                "libelle_fr": "Contrat",
                "libelle_de": "Vertrag",
                "libelle_it": "Contratto",
                "libelle_en": "Contract",
                "type": "CONTRAT",
            },
        ]

        categories = list(CategorieDocument.objects.all())

        for t in types:
            TypeDocument.objects.get_or_create(
                code=t["code"],
                defaults={
                    "libelle": t["libelle_fr"],
                    "type_document": t["type"],
                    "categorie": random.choice(categories) if categories else None,
                },
            )

        self.stdout.write(f"  ✓ {len(types)} types")

    def _create_dossiers(self, clients):
        """Crée des dossiers pour les clients"""
        self.stdout.write("📂 Création des dossiers...")

        count = 0
        for client in clients[:5]:
            dossier_client = Dossier.objects.create(
                nom=f"Dossier {client.raison_sociale}",
                type_dossier="CLIENT",
                client=client,
                chemin_complet=f"/{client.raison_sociale}",
                proprietaire=client.responsable,
            )
            count += 1

            for sous_dossier in ["Comptabilité", "TVA", "Contrats", "Salaires"]:
                Dossier.objects.create(
                    parent=dossier_client,
                    nom=sous_dossier,
                    type_dossier="STANDARD",
                    client=client,
                    chemin_complet=f"/{client.raison_sociale}/{sous_dossier}",
                    proprietaire=client.responsable,
                )
                count += 1

        self.stdout.write(f"  ✓ {count} dossiers")

    def _create_documents(self, mandats):
        """Crée des documents avec traductions"""
        self.stdout.write("📄 Création des documents...")

        count = 0
        dossiers = list(Dossier.objects.all())
        types_doc = list(TypeDocument.objects.all())
        categories = list(CategorieDocument.objects.all())

        descriptions = {
            "facture": {
                "fr": "Facture du mois",
                "de": "Monatsrechnung",
                "it": "Fattura del mese",
                "en": "Monthly invoice",
            },
            "releve": {
                "fr": "Relevé de compte",
                "de": "Kontoauszug",
                "it": "Estratto conto",
                "en": "Account statement",
            },
            "contrat": {
                "fr": "Document contractuel",
                "de": "Vertragsdokument",
                "it": "Documento contrattuale",
                "en": "Contractual document",
            },
        }

        for mandat in mandats[:5]:
            dossier = next(
                (d for d in dossiers if d.client == mandat.client),
                dossiers[0] if dossiers else None,
            )
            if not dossier:
                continue

            for _ in range(random.randint(3, 8)):
                desc_key = random.choice(list(descriptions.keys()))
                desc = descriptions[desc_key]

                Document.objects.create(
                    mandat=mandat,
                    dossier=dossier,
                    nom_fichier=f"document_{random.randint(1000, 9999)}.pdf",
                    nom_original=f"facture_{random.randint(1000, 9999)}.pdf",
                    extension=".pdf",
                    mime_type="application/pdf",
                    taille=random.randint(10000, 1000000),
                    hash_fichier=self.fake.sha256(),
                    type_document=random.choice(types_doc) if types_doc else None,
                    categorie=random.choice(categories) if categories else None,
                    date_document=self.fake.date_between(
                        start_date="-60d", end_date="today"
                    ),
                    statut_traitement="VALIDE",
                )
                count += 1

        self.stdout.write(f"  ✓ {count} documents")

    def _create_documents_with_files(self, mandats, count=50):
        """
        Crée des documents avec de vrais fichiers PDF/DOCX/XLSX.
        Les fichiers contiennent du texte métier suisse réaliste pour la vectorisation.
        """
        if not FAKER_FILE_AVAILABLE:
            self.stdout.write(
                self.style.ERROR(
                    "❌ faker-file non disponible, création de documents sans fichiers"
                )
            )
            self._create_documents(mandats)
            return

        self.stdout.write(f"📄 Création de {count} documents avec fichiers réels...")

        dossiers = list(Dossier.objects.all())
        types_doc = list(TypeDocument.objects.all())
        categories = list(CategorieDocument.objects.all())

        if not dossiers:
            self.stdout.write(self.style.WARNING("⚠ Aucun dossier trouvé"))
            return

        # Templates de contenu métier suisse
        document_templates = self._get_document_templates()

        created = 0
        for i in range(count):
            mandat = random.choice(mandats)
            dossier = next(
                (d for d in dossiers if d.client == mandat.client),
                random.choice(dossiers)
            )

            # Choisir un type de document et son template
            doc_type = random.choice(list(document_templates.keys()))
            template = document_templates[doc_type]

            # Générer le contenu personnalisé
            content = self._generate_document_content(template, mandat)

            # Choisir le format de fichier
            file_format = random.choice(template.get("formats", ["pdf"]))

            try:
                # Générer le fichier réel
                file_data = self._generate_file(content, file_format, template)
                if not file_data:
                    continue

                file_content, filename, mime_type, extension = file_data

                # Calculer le hash
                file_hash = hashlib.sha256(file_content).hexdigest()

                # Vérifier si le hash existe déjà
                if Document.objects.filter(hash_fichier=file_hash).exists():
                    file_hash = hashlib.sha256(
                        file_content + str(uuid.uuid4()).encode()
                    ).hexdigest()

                # Créer le document (sans ocr_text pour tester le pipeline OCR)
                doc = Document.objects.create(
                    mandat=mandat,
                    dossier=dossier,
                    nom_fichier=filename,
                    nom_original=filename,
                    extension=extension,
                    mime_type=mime_type,
                    taille=len(file_content),
                    hash_fichier=file_hash,
                    type_document=random.choice(types_doc) if types_doc else None,
                    categorie=random.choice(categories) if categories else None,
                    date_document=self.fake.date_between(
                        start_date="-180d", end_date="today"
                    ),
                    statut_traitement="UPLOAD",  # En attente de traitement OCR
                    # ocr_text et ocr_confidence seront remplis par le pipeline OCR
                )

                # Sauvegarder le fichier
                doc.fichier.save(filename, ContentFile(file_content), save=True)

                created += 1

                if created % 10 == 0:
                    self.stdout.write(f"  → {created}/{count} documents créés...")

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Erreur création document: {e}")
                )
                continue

        self.stdout.write(f"  ✓ {created} documents avec fichiers réels")

    def _get_document_templates(self):
        """Retourne les templates de documents métier suisses"""
        return {
            "facture_vente": {
                "titre": "Facture",
                "formats": ["pdf", "docx"],
                "content_generator": self._generate_facture_content,
            },
            "facture_achat": {
                "titre": "Facture fournisseur",
                "formats": ["pdf"],
                "content_generator": self._generate_facture_fournisseur_content,
            },
            "releve_bancaire": {
                "titre": "Relevé bancaire",
                "formats": ["pdf"],
                "content_generator": self._generate_releve_bancaire_content,
            },
            "contrat_travail": {
                "titre": "Contrat de travail",
                "formats": ["pdf", "docx"],
                "content_generator": self._generate_contrat_travail_content,
            },
            "fiche_salaire": {
                "titre": "Fiche de salaire",
                "formats": ["pdf"],
                "content_generator": self._generate_fiche_salaire_content,
            },
            "declaration_tva": {
                "titre": "Déclaration TVA",
                "formats": ["pdf"],
                "content_generator": self._generate_declaration_tva_content,
            },
            "bilan": {
                "titre": "Bilan comptable",
                "formats": ["pdf"],
                "content_generator": self._generate_bilan_content,
            },
            "rapport_annuel": {
                "titre": "Rapport annuel",
                "formats": ["pdf", "docx"],
                "content_generator": self._generate_rapport_annuel_content,
            },
            "pv_assemblee": {
                "titre": "PV Assemblée générale",
                "formats": ["pdf", "docx"],
                "content_generator": self._generate_pv_assemblee_content,
            },
            "attestation_domicile": {
                "titre": "Attestation de domicile",
                "formats": ["pdf"],
                "content_generator": self._generate_attestation_content,
            },
            "courrier_afc": {
                "titre": "Correspondance AFC",
                "formats": ["pdf"],
                "content_generator": self._generate_courrier_afc_content,
            },
            "decompte_avs": {
                "titre": "Décompte AVS",
                "formats": ["pdf"],
                "content_generator": self._generate_decompte_avs_content,
            },
        }

    def _generate_document_content(self, template, mandat):
        """Génère le contenu texte d'un document"""
        generator = template.get("content_generator")
        if generator:
            return generator(mandat)
        return self._generate_generic_content(mandat)

    def _generate_file(self, content, file_format, template):
        """Génère un fichier réel avec le contenu"""
        try:
            titre = template.get("titre", "Document")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"{titre.replace(' ', '_')}_{timestamp}_{random.randint(1000, 9999)}"

            if file_format == "pdf":
                # Générer un PDF avec texte
                file_obj = self.fake.pdf_file(
                    content=content,
                    max_nb_pages=random.randint(1, 5),
                    wrap_chars_after=80,
                )
                filename = f"{base_name}.pdf"
                mime_type = "application/pdf"
                extension = ".pdf"

            elif file_format == "docx":
                # Générer un DOCX
                file_obj = self.fake.docx_file(
                    content=content,
                    max_nb_pages=random.randint(1, 3),
                    wrap_chars_after=80,
                )
                filename = f"{base_name}.docx"
                mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                extension = ".docx"

            elif file_format == "xlsx":
                # Générer un XLSX avec données tabulaires
                file_obj = self.fake.xlsx_file(
                    content=content,
                )
                filename = f"{base_name}.xlsx"
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                extension = ".xlsx"

            else:
                # Fallback en TXT
                file_obj = self.fake.txt_file(
                    content=content,
                )
                filename = f"{base_name}.txt"
                mime_type = "text/plain"
                extension = ".txt"

            # Lire le contenu du fichier
            with open(file_obj.data["filename"], "rb") as f:
                file_content = f.read()

            # Nettoyer le fichier temporaire
            os.unlink(file_obj.data["filename"])

            return file_content, filename, mime_type, extension

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Erreur génération fichier {file_format}: {e}")
            )
            return None

    # =========================================================================
    # GÉNÉRATEURS DE CONTENU MÉTIER SUISSE
    # =========================================================================

    def _generate_facture_content(self, mandat):
        """Génère le contenu d'une facture de vente"""
        client = mandat.client
        montant = Decimal(str(random.randint(500, 50000)))
        tva = (montant * Decimal("8.1") / 100).quantize(Decimal("0.01"))

        return f"""
FACTURE N° {random.randint(10000, 99999)}

AltiusOne Fiduciaire SA
Rue du Marché 15
1204 Genève
Suisse
CHE-123.456.789 TVA

Facturé à:
{client.raison_sociale}
{client.adresse_siege.rue} {client.adresse_siege.numero}
{client.adresse_siege.code_postal} {client.adresse_siege.localite}
{client.ide_number if client.ide_number else ''}

Date: {self.fake.date_between(start_date="-60d", end_date="today")}
Échéance: {self.fake.date_between(start_date="today", end_date="+30d")}

Description des prestations:
---------------------------------------------------------------------------
Tenue de la comptabilité - {self.fake.month_name()} 2024
Services de conseil fiscal
Établissement des décomptes TVA trimestriels
Révision des comptes annuels
Préparation de la déclaration d'impôt

Montant HT:                                          CHF {montant:,.2f}
TVA 8.1%:                                            CHF {tva:,.2f}
---------------------------------------------------------------------------
TOTAL TTC:                                           CHF {montant + tva:,.2f}

Conditions de paiement: 30 jours net
IBAN: CH93 0076 2011 6238 5295 7
Référence QR: {random.randint(100000000000000000000000000, 999999999999999999999999999)}

Merci de votre confiance.
"""

    def _generate_facture_fournisseur_content(self, mandat):
        """Génère le contenu d'une facture fournisseur"""
        fournisseur = self.fake.company()
        montant = Decimal(str(random.randint(100, 15000)))
        tva = (montant * Decimal("8.1") / 100).quantize(Decimal("0.01"))

        return f"""
FACTURE FOURNISSEUR

{fournisseur}
{self.fake.street_address()}
{random.choice(['1200', '1003', '8001', '3000'])} {random.choice(['Genève', 'Lausanne', 'Zürich', 'Bern'])}
CHE-{random.randint(100,999)}.{random.randint(100,999)}.{random.randint(100,999)} TVA

Facture N°: {random.randint(1000, 9999)}
Date: {self.fake.date_between(start_date="-30d", end_date="today")}

Client:
{mandat.client.raison_sociale}

Articles / Services:
---------------------------------------------------------------------------
{self.fake.sentence(nb_words=6)}
{self.fake.sentence(nb_words=4)}
Frais de livraison

Sous-total HT:                                       CHF {montant:,.2f}
TVA 8.1%:                                            CHF {tva:,.2f}
---------------------------------------------------------------------------
Total à payer:                                       CHF {montant + tva:,.2f}

Paiement à 30 jours
IBAN: CH{random.randint(10,99)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(0,9)}
"""

    def _generate_releve_bancaire_content(self, mandat):
        """Génère le contenu d'un relevé bancaire"""
        solde_initial = Decimal(str(random.randint(10000, 500000)))
        operations = []
        solde = solde_initial

        for _ in range(random.randint(10, 25)):
            is_credit = random.random() > 0.4
            montant = Decimal(str(random.randint(100, 25000)))
            if is_credit:
                solde += montant
                operations.append(f"+ {montant:>12,.2f}   {self.fake.sentence(nb_words=4)}")
            else:
                solde -= montant
                operations.append(f"- {montant:>12,.2f}   {self.fake.sentence(nb_words=4)}")

        operations_text = "\n".join(operations)

        return f"""
RELEVÉ DE COMPTE

Banque Cantonale de Genève
{mandat.client.raison_sociale}
Compte: CH{random.randint(10,99)} 0076 {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(0,9)}

Période: du {self.fake.date_between(start_date="-60d", end_date="-30d")} au {self.fake.date_between(start_date="-30d", end_date="today")}

Solde initial:                                       CHF {solde_initial:,.2f}

MOUVEMENTS
---------------------------------------------------------------------------
{operations_text}
---------------------------------------------------------------------------

Solde final:                                         CHF {solde:,.2f}

Ce document est établi automatiquement et ne nécessite pas de signature.
"""

    def _generate_contrat_travail_content(self, mandat):
        """Génère le contenu d'un contrat de travail"""
        employe_nom = self.fake.name()
        salaire = random.randint(4500, 12000)
        date_debut = self.fake.date_between(start_date="-2y", end_date="-1m")

        return f"""
CONTRAT DE TRAVAIL

Entre
{mandat.client.raison_sociale}
{mandat.client.adresse_siege.rue} {mandat.client.adresse_siege.numero}
{mandat.client.adresse_siege.code_postal} {mandat.client.adresse_siege.localite}
(ci-après "l'Employeur")

Et
{employe_nom}
{self.fake.street_address()}
{random.choice(['1200', '1003', '8001'])} {random.choice(['Genève', 'Lausanne', 'Zürich'])}
(ci-après "l'Employé")

Article 1 - Engagement
L'Employeur engage l'Employé en qualité de {random.choice(['Comptable', 'Assistant administratif', 'Chef de projet', 'Analyste financier'])}.

Article 2 - Durée
Le présent contrat est conclu pour une durée indéterminée.
Date d'entrée en fonction: {date_debut}

Article 3 - Temps de travail
Taux d'occupation: {random.choice([80, 100])}%
Horaire hebdomadaire: {random.choice([40, 42])} heures

Article 4 - Rémunération
Salaire mensuel brut: CHF {salaire:,}.-
13ème salaire: Oui
Versement: fin de mois sur compte bancaire

Article 5 - Vacances
L'Employé bénéficie de {random.choice([20, 25])} jours de vacances par année civile.

Article 6 - Assurances sociales
- AVS/AI/APG: selon dispositions légales
- LPP: affiliation à la caisse de pension de l'entreprise
- LAA: assurance accidents professionnels et non professionnels

Article 7 - Délai de résiliation
Pendant la période d'essai (3 mois): 7 jours
Après la période d'essai: 1 mois pour la fin d'un mois

Fait en deux exemplaires à {mandat.client.adresse_siege.localite}, le {self.fake.date_between(start_date=date_debut - timedelta(days=30), end_date=date_debut)}

L'Employeur                                          L'Employé
_____________________                                _____________________
"""

    def _generate_fiche_salaire_content(self, mandat):
        """Génère le contenu d'une fiche de salaire"""
        employe_nom = self.fake.name()
        salaire_brut = Decimal(str(random.randint(5000, 12000)))
        avs = (salaire_brut * Decimal("5.3") / 100).quantize(Decimal("0.01"))
        ac = (salaire_brut * Decimal("1.1") / 100).quantize(Decimal("0.01"))
        lpp = (salaire_brut * Decimal("7.5") / 100).quantize(Decimal("0.01"))
        total_deductions = avs + ac + lpp
        net = salaire_brut - total_deductions

        return f"""
FICHE DE SALAIRE

{mandat.client.raison_sociale}
{mandat.client.adresse_siege.rue} {mandat.client.adresse_siege.numero}
{mandat.client.adresse_siege.code_postal} {mandat.client.adresse_siege.localite}

Employé: {employe_nom}
N° AVS: 756.{random.randint(1000,9999)}.{random.randint(1000,9999)}.{random.randint(10,99)}
Période: {self.fake.month_name()} 2024

---------------------------------------------------------------------------
GAINS
Salaire de base                                      CHF {salaire_brut:,.2f}
---------------------------------------------------------------------------
Total brut                                           CHF {salaire_brut:,.2f}

DÉDUCTIONS
AVS/AI/APG (5.3%)                                   -CHF {avs:,.2f}
Assurance chômage AC (1.1%)                         -CHF {ac:,.2f}
LPP Prévoyance professionnelle                      -CHF {lpp:,.2f}
---------------------------------------------------------------------------
Total déductions                                    -CHF {total_deductions:,.2f}

---------------------------------------------------------------------------
SALAIRE NET À PAYER                                  CHF {net:,.2f}
---------------------------------------------------------------------------

Versement sur: IBAN CH{random.randint(10,99)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(0,9)}
Date de versement: {self.fake.date_between(start_date="-5d", end_date="today")}
"""

    def _generate_declaration_tva_content(self, mandat):
        """Génère le contenu d'une déclaration TVA"""
        ca = Decimal(str(random.randint(50000, 500000)))
        tva_due = (ca * Decimal("8.1") / 100).quantize(Decimal("0.01"))
        tva_prealable = (Decimal(str(random.randint(5000, 50000))) * Decimal("8.1") / 100).quantize(Decimal("0.01"))
        tva_nette = tva_due - tva_prealable

        return f"""
DÉCLARATION TVA

Administration fédérale des contributions AFC
Division principale de la taxe sur la valeur ajoutée

Contribuable: {mandat.client.raison_sociale}
N° TVA: {mandat.client.tva_number if mandat.client.tva_number else f'CHE-{random.randint(100,999)}.{random.randint(100,999)}.{random.randint(100,999)} TVA'}

Période: T{random.randint(1,4)} 2024
Méthode: Effective

---------------------------------------------------------------------------
CHIFFRE D'AFFAIRES

200 - Prestations au taux normal (8.1%)             CHF {ca:,.2f}
205 - Prestations au taux réduit (2.6%)             CHF {Decimal(str(random.randint(0, 50000))):,.2f}
220 - Prestations exonérées                         CHF {Decimal(str(random.randint(0, 20000))):,.2f}

Total chiffre d'affaires                            CHF {ca:,.2f}

---------------------------------------------------------------------------
TVA DUE

300 - TVA sur prestations imposables                CHF {tva_due:,.2f}

---------------------------------------------------------------------------
IMPÔT PRÉALABLE

400 - Impôt préalable sur achats                    CHF {tva_prealable:,.2f}

---------------------------------------------------------------------------
DÉCOMPTE

TVA due                                             CHF {tva_due:,.2f}
./. Impôt préalable                                -CHF {tva_prealable:,.2f}
---------------------------------------------------------------------------
Montant dû à l'AFC                                  CHF {tva_nette:,.2f}

Date limite de paiement: {self.fake.date_between(start_date="+10d", end_date="+30d")}
"""

    def _generate_bilan_content(self, mandat):
        """Génère le contenu d'un bilan comptable"""
        actifs_circulants = Decimal(str(random.randint(50000, 500000)))
        actifs_immobilises = Decimal(str(random.randint(100000, 1000000)))
        total_actif = actifs_circulants + actifs_immobilises

        fonds_propres = Decimal(str(random.randint(50000, 300000)))
        fonds_etrangers = total_actif - fonds_propres

        return f"""
BILAN AU 31 DÉCEMBRE 2024

{mandat.client.raison_sociale}
{mandat.client.ide_number}

---------------------------------------------------------------------------
ACTIF                                                          CHF
---------------------------------------------------------------------------

ACTIFS CIRCULANTS
Liquidités                                          {Decimal(str(random.randint(10000, 100000))):>15,.2f}
Débiteurs                                           {Decimal(str(random.randint(20000, 200000))):>15,.2f}
Stock marchandises                                  {Decimal(str(random.randint(10000, 150000))):>15,.2f}
Actifs transitoires                                 {Decimal(str(random.randint(5000, 50000))):>15,.2f}
                                                   ----------------
Total actifs circulants                             {actifs_circulants:>15,.2f}

ACTIFS IMMOBILISÉS
Machines et outillage                               {Decimal(str(random.randint(50000, 300000))):>15,.2f}
Mobilier et installations                           {Decimal(str(random.randint(20000, 100000))):>15,.2f}
Véhicules                                           {Decimal(str(random.randint(10000, 80000))):>15,.2f}
Immobilisations financières                         {Decimal(str(random.randint(10000, 200000))):>15,.2f}
                                                   ----------------
Total actifs immobilisés                            {actifs_immobilises:>15,.2f}

---------------------------------------------------------------------------
TOTAL ACTIF                                         {total_actif:>15,.2f}
---------------------------------------------------------------------------

---------------------------------------------------------------------------
PASSIF                                                         CHF
---------------------------------------------------------------------------

FONDS ÉTRANGERS
Créanciers fournisseurs                             {Decimal(str(random.randint(20000, 150000))):>15,.2f}
Dettes bancaires court terme                        {Decimal(str(random.randint(10000, 100000))):>15,.2f}
Passifs transitoires                                {Decimal(str(random.randint(5000, 30000))):>15,.2f}
Emprunts hypothécaires                              {Decimal(str(random.randint(50000, 500000))):>15,.2f}
Provisions                                          {Decimal(str(random.randint(10000, 80000))):>15,.2f}
                                                   ----------------
Total fonds étrangers                               {fonds_etrangers:>15,.2f}

FONDS PROPRES
Capital-actions                                     {Decimal(str(random.randint(50000, 200000))):>15,.2f}
Réserves légales                                    {Decimal(str(random.randint(10000, 50000))):>15,.2f}
Bénéfice reporté                                    {Decimal(str(random.randint(5000, 30000))):>15,.2f}
Résultat de l'exercice                              {Decimal(str(random.randint(-20000, 100000))):>15,.2f}
                                                   ----------------
Total fonds propres                                 {fonds_propres:>15,.2f}

---------------------------------------------------------------------------
TOTAL PASSIF                                        {total_actif:>15,.2f}
---------------------------------------------------------------------------

Établi conformément au Code des obligations suisse (CO).
"""

    def _generate_rapport_annuel_content(self, mandat):
        """Génère le contenu d'un rapport annuel"""
        return f"""
RAPPORT ANNUEL 2024

{mandat.client.raison_sociale}
{mandat.client.adresse_siege.rue} {mandat.client.adresse_siege.numero}
{mandat.client.adresse_siege.code_postal} {mandat.client.adresse_siege.localite}
{mandat.client.ide_number}

═══════════════════════════════════════════════════════════════════════════

MESSAGE DU CONSEIL D'ADMINISTRATION

Chers actionnaires,

L'année 2024 a été marquée par {random.choice(['une croissance soutenue', 'une consolidation de nos activités', 'des défis économiques importants', 'une transformation digitale réussie'])}.
Notre entreprise a su {random.choice(['maintenir sa position sur le marché', 's\'adapter aux nouvelles conditions du marché', 'développer de nouveaux services', 'renforcer ses partenariats stratégiques'])}.

FAITS MARQUANTS DE L'EXERCICE

• Chiffre d'affaires: CHF {random.randint(500000, 5000000):,}.-
• Résultat net: CHF {random.randint(50000, 500000):,}.-
• Effectif moyen: {random.randint(5, 50)} collaborateurs
• Investissements: CHF {random.randint(50000, 500000):,}.-

PERSPECTIVES 2025

Pour l'année à venir, nous prévoyons de {random.choice(['poursuivre notre stratégie de développement', 'investir dans la digitalisation', 'renforcer notre présence en Suisse romande', 'développer notre offre de services'])}.
Le marché suisse reste porteur et nous sommes confiants quant à nos perspectives de croissance.

GOUVERNANCE D'ENTREPRISE

Conseil d'administration:
• Président: {self.fake.name()}
• Vice-président: {self.fake.name()}
• Administrateur: {self.fake.name()}

Direction:
• Directeur général: {self.fake.name()}
• Directeur financier: {self.fake.name()}

RAPPORT DE L'ORGANE DE RÉVISION

En notre qualité d'organe de révision, nous avons effectué l'audit des comptes annuels de {mandat.client.raison_sociale} pour l'exercice arrêté au 31 décembre 2024.

Notre audit a été effectué conformément aux Normes d'audit suisses (NAS). Ces normes requièrent que l'audit soit planifié et réalisé de façon à obtenir une assurance raisonnable que les comptes annuels ne contiennent pas d'anomalies significatives.

Sur la base de nos travaux d'audit, nous recommandons d'approuver les comptes annuels présentés.

{self.fake.city()}, le {self.fake.date_between(start_date="-30d", end_date="today")}

L'organe de révision
{self.fake.company()} SA
"""

    def _generate_pv_assemblee_content(self, mandat):
        """Génère le contenu d'un PV d'assemblée générale"""
        return f"""
PROCÈS-VERBAL DE L'ASSEMBLÉE GÉNÉRALE ORDINAIRE

{mandat.client.raison_sociale}
{mandat.client.ide_number}

Date: {self.fake.date_between(start_date="-90d", end_date="-30d")}
Lieu: {mandat.client.adresse_siege.localite}
Heure: {random.choice(['10h00', '14h00', '17h00'])}

═══════════════════════════════════════════════════════════════════════════

PRÉSENCES

Actionnaires présents ou représentés détenant {random.randint(70, 100)}% du capital-actions.
Le quorum étant atteint, l'assemblée peut valablement délibérer.

Président de séance: {self.fake.name()}
Secrétaire: {self.fake.name()}

ORDRE DU JOUR

1. Approbation du procès-verbal de la dernière assemblée
2. Approbation du rapport annuel et des comptes 2024
3. Affectation du résultat
4. Décharge aux organes
5. Élections statutaires
6. Divers

DÉLIBÉRATIONS

1. APPROBATION DU PROCÈS-VERBAL
Le procès-verbal de la dernière assemblée générale est approuvé à l'unanimité.

2. RAPPORT ANNUEL ET COMPTES 2024
Le président présente le rapport annuel et les comptes de l'exercice 2024.
L'organe de révision recommande l'approbation des comptes.
L'assemblée approuve les comptes annuels à l'unanimité.

Résultat de l'exercice: CHF {random.randint(10000, 200000):,}.-

3. AFFECTATION DU RÉSULTAT
L'assemblée décide d'affecter le bénéfice comme suit:
• Attribution aux réserves légales: CHF {random.randint(5000, 20000):,}.-
• Dividende: CHF {random.randint(5000, 100000):,}.-
• Report à nouveau: le solde

4. DÉCHARGE AUX ORGANES
L'assemblée donne décharge aux membres du conseil d'administration et à l'organe de révision pour leur gestion durant l'exercice écoulé.

5. ÉLECTIONS
Le conseil d'administration et l'organe de révision sont reconduits pour une nouvelle période d'un an.

6. DIVERS
Aucune question n'étant soulevée sous ce point, le président clôt la séance.

L'ordre du jour étant épuisé, la séance est levée à {random.choice(['11h30', '15h30', '18h30'])}.

Le Président                                         Le Secrétaire
_____________________                                _____________________
"""

    def _generate_attestation_content(self, mandat):
        """Génère le contenu d'une attestation"""
        return f"""
ATTESTATION DE DOMICILE FISCAL

Je soussigné(e), responsable de la fiduciaire AltiusOne SA,

ATTESTE PAR LA PRÉSENTE

que la société:

{mandat.client.raison_sociale}
{mandat.client.ide_number}

est domiciliée à l'adresse suivante:

{mandat.client.adresse_siege.rue} {mandat.client.adresse_siege.numero}
{mandat.client.adresse_siege.code_postal} {mandat.client.adresse_siege.localite}
Canton: {mandat.client.adresse_siege.canton}
Suisse

Cette société est inscrite au Registre du commerce du canton de {mandat.client.adresse_siege.canton} et est soumise à l'impôt en Suisse.

La présente attestation est délivrée pour servir et valoir ce que de droit.

Fait à Genève, le {self.fake.date_between(start_date="-30d", end_date="today")}

AltiusOne Fiduciaire SA

_____________________
Signature autorisée
"""

    def _generate_courrier_afc_content(self, mandat):
        """Génère le contenu d'un courrier de l'AFC"""
        return f"""
Confédération suisse
Administration fédérale des contributions AFC
Division principale de la taxe sur la valeur ajoutée

{mandat.client.raison_sociale}
{mandat.client.adresse_siege.rue} {mandat.client.adresse_siege.numero}
{mandat.client.adresse_siege.code_postal} {mandat.client.adresse_siege.localite}

Berne, le {self.fake.date_between(start_date="-60d", end_date="-10d")}

N° de référence: {random.randint(100000, 999999)}
N° TVA: {mandat.client.tva_number if mandat.client.tva_number else f'CHE-{random.randint(100,999)}.{random.randint(100,999)}.{random.randint(100,999)} TVA'}

Objet: {random.choice(['Confirmation de votre inscription au registre TVA', 'Rappel de paiement - Décompte TVA', 'Demande de renseignements', 'Notification de contrôle TVA'])}

Madame, Monsieur,

{random.choice([
'Nous accusons réception de votre demande d\'inscription au registre des assujettis à la TVA. Après examen de votre dossier, nous avons le plaisir de vous informer que votre inscription a été validée.',
'Nous nous référons à votre décompte TVA pour la période mentionnée ci-dessus. Nous constatons que le montant dû n\'a pas encore été réglé.',
'Dans le cadre de nos contrôles réguliers, nous vous prions de bien vouloir nous faire parvenir les justificatifs relatifs à vos opérations TVA.',
'Nous avons le plaisir de vous informer que votre demande a été traitée favorablement.'
])}

{random.choice([
'Veuillez prendre note que le taux normal de TVA est de 8.1% depuis le 1er janvier 2024.',
'Nous vous rappelons que les décomptes TVA doivent être soumis dans les 60 jours suivant la fin de la période.',
'Pour tout renseignement complémentaire, vous pouvez nous contacter au numéro indiqué ci-dessous.',
'Nous restons à votre disposition pour toute question concernant vos obligations TVA.'
])}

Avec nos salutations distinguées,

Administration fédérale des contributions
Division principale de la TVA

Contact: tva@estv.admin.ch
Téléphone: 058 465 22 22
"""

    def _generate_decompte_avs_content(self, mandat):
        """Génère le contenu d'un décompte AVS"""
        masse_salariale = Decimal(str(random.randint(200000, 2000000)))
        taux_avs = Decimal("10.6")
        cotisation_avs = (masse_salariale * taux_avs / 100).quantize(Decimal("0.01"))

        return f"""
DÉCOMPTE DE COTISATIONS AVS/AI/APG

Caisse de compensation AVS
Case postale
1211 Genève 26

Employeur:
{mandat.client.raison_sociale}
{mandat.client.adresse_siege.rue} {mandat.client.adresse_siege.numero}
{mandat.client.adresse_siege.code_postal} {mandat.client.adresse_siege.localite}

N° affilié: {random.randint(100, 999)}.{random.randint(1000, 9999)}
Période: Année 2024

═══════════════════════════════════════════════════════════════════════════

CALCUL DES COTISATIONS

Masse salariale brute                               CHF {masse_salariale:>15,.2f}

Cotisations:
AVS/AI/APG (10.6%)                                  CHF {cotisation_avs:>15,.2f}
  - Part employeur (5.3%)                           CHF {(cotisation_avs/2):>15,.2f}
  - Part employé (5.3%)                             CHF {(cotisation_avs/2):>15,.2f}

Contribution frais d'administration (3%)            CHF {(cotisation_avs * Decimal('0.03')).quantize(Decimal('0.01')):>15,.2f}

---------------------------------------------------------------------------
TOTAL DÛ                                            CHF {(cotisation_avs * Decimal('1.03')).quantize(Decimal('0.01')):>15,.2f}
---------------------------------------------------------------------------

Acomptes versés                                    -CHF {(cotisation_avs * Decimal('0.9')).quantize(Decimal('0.01')):>15,.2f}
---------------------------------------------------------------------------
SOLDE À PAYER                                       CHF {(cotisation_avs * Decimal('0.13')).quantize(Decimal('0.01')):>15,.2f}

Délai de paiement: {self.fake.date_between(start_date="+10d", end_date="+30d")}
IBAN: CH{random.randint(10,99)} 0076 {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(0,9)}
Référence: {random.randint(100000000000000, 999999999999999)}

Les cotisations sont dues conformément à la LAVS et ses ordonnances d'application.
"""

    def _generate_generic_content(self, mandat):
        """Génère du contenu générique pour un document"""
        return f"""
DOCUMENT

{mandat.client.raison_sociale}
{mandat.client.adresse_siege.rue} {mandat.client.adresse_siege.numero}
{mandat.client.adresse_siege.code_postal} {mandat.client.adresse_siege.localite}

Date: {self.fake.date_between(start_date="-60d", end_date="today")}

{self.fake.text(max_nb_chars=2000)}

Ce document est la propriété de {mandat.client.raison_sociale}.
Tous droits réservés.
"""

    # =========================================================================
    # FISCALITÉ
    # =========================================================================

    def _create_taux_imposition(self):
        """Crée les taux d'imposition par canton"""
        self.stdout.write("📈 Création des taux d'imposition...")

        cantons = ["GE", "VD", "ZH", "BE", "TI", "FR"]

        count = 0
        for canton in cantons:
            TauxImposition.objects.get_or_create(
                canton=canton,
                type_impot="IFD_BENEFICE",
                annee=2024,
                defaults={
                    "taux_fixe": Decimal("8.5"),
                    "multiplicateur_cantonal": Decimal(
                        str(random.randint(90, 120) / 100)
                    ),
                    "actif": True,
                },
            )
            count += 1

        self.stdout.write(f"  ✓ {count} taux d'imposition")

    def _create_declarations_fiscales(self, mandats):
        """Crée des déclarations fiscales"""
        self.stdout.write("📋 Création des déclarations fiscales...")

        count = 0
        fiscal_mandats = [m for m in mandats if m.type_mandat in ["FISCAL", "GLOBAL"]][
            :3
        ]

        for mandat in fiscal_mandats:
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
                    canton=mandat.client.adresse_siege.canton,
                    numero_contribuable=f"CTB-{random.randint(10000, 99999)}",
                    benefice_avant_impots=Decimal(str(random.randint(50000, 500000))),
                    benefice_imposable=Decimal(str(random.randint(40000, 400000))),
                    impot_federal=Decimal(str(random.randint(5000, 50000))),
                    impot_cantonal=Decimal(str(random.randint(3000, 30000))),
                    impot_communal=Decimal(str(random.randint(1000, 10000))),
                    statut="EN_PREPARATION",
                )
                count += 1

        self.stdout.write(f"  ✓ {count} déclarations fiscales")

    def _create_optimisations_fiscales(self, mandats):
        """Crée des opportunités d'optimisation fiscale avec traductions"""
        self.stdout.write("💡 Création des optimisations fiscales...")

        optimisations = [
            {
                "titre_fr": "Amortissement accéléré des actifs",
                "titre_de": "Beschleunigte Abschreibung von Vermögenswerten",
                "titre_it": "Ammortamento accelerato dei beni",
                "titre_en": "Accelerated depreciation of assets",
                "desc_fr": "Augmenter les amortissements pour réduire le bénéfice imposable",
                "desc_de": "Erhöhung der Abschreibungen zur Reduzierung des steuerbaren Gewinns",
                "desc_it": "Aumentare gli ammortamenti per ridurre l'utile imponibile",
                "desc_en": "Increase depreciation to reduce taxable profit",
                "categorie": "AMORTISSEMENT",
            },
            {
                "titre_fr": "Constitution de provisions",
                "titre_de": "Bildung von Rückstellungen",
                "titre_it": "Costituzione di accantonamenti",
                "titre_en": "Creation of provisions",
                "desc_fr": "Constituer des provisions pour risques et charges futures",
                "desc_de": "Rückstellungen für zukünftige Risiken und Aufwendungen bilden",
                "desc_it": "Costituire accantonamenti per rischi e oneri futuri",
                "desc_en": "Create provisions for future risks and expenses",
                "categorie": "PROVISION",
            },
        ]

        count = 0
        fiscal_mandats = [m for m in mandats if m.type_mandat in ["FISCAL", "GLOBAL"]][
            :2
        ]

        for mandat in fiscal_mandats:
            for opt in optimisations:
                OptimisationFiscale.objects.create(
                    mandat=mandat,
                    categorie=opt["categorie"],
                    titre=opt["titre_fr"],
                    description=opt["desc_fr"],
                    economie_estimee=Decimal(str(random.randint(5000, 50000))),
                    annee_application=2025,
                    niveau_risque="FAIBLE",
                    statut="IDENTIFIEE",
                )
                count += 1

        self.stdout.write(f"  ✓ {count} optimisations fiscales")

    # =========================================================================
    # ANALYTICS
    # =========================================================================

    def _create_tableaux_bord(self, users):
        """Crée des tableaux de bord avec traductions"""
        self.stdout.write("📊 Création des tableaux de bord...")

        tableaux = [
            {
                "nom_fr": "Vue d'ensemble financière",
                "nom_de": "Finanzübersicht",
                "nom_it": "Panoramica finanziaria",
                "nom_en": "Financial overview",
                "desc_fr": "Tableau de bord principal avec les KPIs financiers",
                "desc_de": "Hauptdashboard mit finanziellen KPIs",
                "desc_it": "Dashboard principale con KPI finanziari",
                "desc_en": "Main dashboard with financial KPIs",
            },
            {
                "nom_fr": "Suivi des mandats",
                "nom_de": "Mandatsübersicht",
                "nom_it": "Monitoraggio dei mandati",
                "nom_en": "Mandate tracking",
                "desc_fr": "Suivi de l'avancement des mandats et de la facturation",
                "desc_de": "Verfolgung des Mandatsfortschritts und der Fakturierung",
                "desc_it": "Monitoraggio dell'avanzamento dei mandati e della fatturazione",
                "desc_en": "Tracking of mandate progress and billing",
            },
        ]

        count = 0
        for user in users[:3]:
            for tb in tableaux:
                TableauBord.objects.create(
                    nom=tb["nom_fr"],
                    description=tb["desc_fr"],
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
                count += 1

        self.stdout.write(f"  ✓ {count} tableaux de bord")

    def _create_indicateurs(self):
        """Crée des indicateurs avec traductions"""
        self.stdout.write("📈 Création des indicateurs...")

        indicateurs = [
            {
                "code": "CA_MENSUEL",
                "nom_fr": "Chiffre d'affaires mensuel",
                "nom_de": "Monatlicher Umsatz",
                "nom_it": "Fatturato mensile",
                "nom_en": "Monthly revenue",
                "desc_fr": "Total du chiffre d'affaires réalisé sur le mois",
                "desc_de": "Gesamtumsatz des Monats",
                "desc_it": "Fatturato totale realizzato nel mese",
                "desc_en": "Total revenue for the month",
                "categorie": "FINANCIER",
                "unite": "CHF",
            },
            {
                "code": "MARGE_BRUTE",
                "nom_fr": "Marge brute",
                "nom_de": "Bruttogewinnmarge",
                "nom_it": "Margine lordo",
                "nom_en": "Gross margin",
                "desc_fr": "Pourcentage de marge brute sur les ventes",
                "desc_de": "Prozentsatz der Bruttogewinnmarge",
                "desc_it": "Percentuale di margine lordo sulle vendite",
                "desc_en": "Gross margin percentage on sales",
                "categorie": "FINANCIER",
                "unite": "%",
            },
            {
                "code": "TAUX_RECOUVREMENT",
                "nom_fr": "Taux de recouvrement",
                "nom_de": "Einziehungsquote",
                "nom_it": "Tasso di recupero",
                "nom_en": "Collection rate",
                "desc_fr": "Pourcentage des factures payées dans les délais",
                "desc_de": "Prozentsatz der fristgerecht bezahlten Rechnungen",
                "desc_it": "Percentuale delle fatture pagate nei termini",
                "desc_en": "Percentage of invoices paid on time",
                "categorie": "OPERATIONNEL",
                "unite": "%",
            },
        ]

        for ind in indicateurs:
            Indicateur.objects.get_or_create(
                code=ind["code"],
                defaults={
                    "nom": ind["nom_fr"],
                    "description": ind["desc_fr"],
                    "categorie": ind["categorie"],
                    "type_calcul": "SOMME",
                    "periodicite": "MOIS",
                    "objectif_cible": Decimal(str(random.randint(10000, 100000))),
                    "unite": ind["unite"],
                    "actif": True,
                },
            )

        self.stdout.write(f"  ✓ {len(indicateurs)} indicateurs")

    def _create_rapports(self, mandats, users):
        """Crée des rapports avec traductions"""
        self.stdout.write("📝 Création des rapports...")

        rapports = [
            {
                "nom_fr": "Bilan annuel",
                "nom_de": "Jahresbilanz",
                "nom_it": "Bilancio annuale",
                "nom_en": "Annual balance sheet",
                "type": "BILAN",
            },
            {
                "nom_fr": "Compte de résultat",
                "nom_de": "Erfolgsrechnung",
                "nom_it": "Conto economico",
                "nom_en": "Income statement",
                "type": "COMPTE_RESULTATS",
            },
            {
                "nom_fr": "Rapport TVA trimestriel",
                "nom_de": "MWST-Quartalsbericht",
                "nom_it": "Rapporto IVA trimestrale",
                "nom_en": "Quarterly VAT report",
                "type": "TVA",
            },
        ]

        count = 0
        for mandat in mandats[:5]:
            for rap in rapports:
                Rapport.objects.create(
                    nom=rap["nom_fr"],
                    type_rapport=rap["type"],
                    mandat=mandat,
                    date_debut=date(2024, 1, 1),
                    date_fin=date(2024, 12, 31),
                    genere_par=random.choice(users),
                    statut="TERMINE",
                    format_fichier="PDF",
                )
                count += 1

        self.stdout.write(f"  ✓ {count} rapports")
