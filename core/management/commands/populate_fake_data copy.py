# core/management/commands/populate_fake_data.py

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from faker import Faker
from decimal import Decimal
import random
from datetime import datetime, timedelta, date
import uuid

# Imports des modèles...

fake_fr = Faker("fr_CH")
fake_de = Faker("de_CH")
fake = fake_fr  # Par défaut


class Command(BaseCommand):
    help = "Génère des données de test réalistes pour AltiusFidu"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clients",
            type=int,
            default=10,
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

    def handle(self, *args, **options):
        Faker.seed(options["seed"])
        random.seed(options["seed"])

        if options["clean"]:
            self._clean_data()

        with transaction.atomic():
            self.stdout.write(
                self.style.WARNING("🏭 Génération des données AltiusFidu...")
            )

            # 1. Utilisateurs
            users = self._create_users()

            # 2. Adresses et Clients
            clients = self._create_clients(options["clients"], users)

            # 3. Mandats et configuration
            mandats = self._create_mandats(clients, users)

            # 4. Plan comptable (si pas déjà chargé)
            self._ensure_chart_of_accounts(mandats)

            # 5. Comptabilité (si demandé)
            if not options["skip_accounting"]:
                self._create_accounting_data(mandats)

            # 6. Facturation
            self._create_invoicing_data(mandats, users)

            # 7. Salaires
            self._create_payroll_data(mandats, users)

            # 8. TVA
            self._create_vat_data(mandats)

            # 9. Documents
            self._create_documents(mandats, users)

            self.stdout.write(self.style.SUCCESS("✅ Données générées avec succès!"))

    def _clean_data(self):
        """Supprime les données de test existantes"""
        self.stdout.write("🧹 Nettoyage des données existantes...")
        # Supprimer dans l'ordre inverse des dépendances
        # ...

    def _create_users(self):
        """Crée les utilisateurs de la fiduciaire"""
        User = get_user_model()

        self.stdout.write("👥 Création des utilisateurs...")

        users_data = [
            {
                "username": "admin",
                "role": "ADMIN",
                "first_name": "Admin",
                "last_name": "System",
            },
            {
                "username": "pierre.muller",
                "role": "MANAGER",
                "first_name": "Pierre",
                "last_name": "Müller",
            },
            {
                "username": "marie.dubois",
                "role": "COMPTABLE",
                "first_name": "Marie",
                "last_name": "Dubois",
            },
            {
                "username": "jean.favre",
                "role": "COMPTABLE",
                "first_name": "Jean",
                "last_name": "Favre",
            },
            {
                "username": "anna.schmid",
                "role": "ASSISTANT",
                "first_name": "Anna",
                "last_name": "Schmid",
            },
            {
                "username": "luca.rossi",
                "role": "ASSISTANT",
                "first_name": "Luca",
                "last_name": "Rossi",
            },
        ]

        users = []
        for data in users_data:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": f"{data['username']}@altiusfidu.ch",
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "role": data["role"],
                    "phone": fake.phone_number(),
                    "is_active": True,
                },
            )
            if created:
                user.set_password("Test1234!")
                user.save()
            users.append(user)

        self.stdout.write(f"  ✓ {len(users)} utilisateurs")
        return users

    def _create_clients(self, count, users):
        """Crée des clients suisses réalistes"""
        from core.models import Client, Contact, Adresse

        self.stdout.write(f"🏢 Création de {count} clients...")

        # Données suisses réalistes
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
        ]

        company_types = [
            ("SA", "Société anonyme", ["AG", "SA"]),
            ("SARL", "Société à responsabilité limitée", ["GmbH", "Sàrl"]),
            ("EI", "Entreprise individuelle", []),
            ("SC", "Société en commandite", ["KG", "SC"]),
        ]

        business_sectors = [
            ("consulting", ["Conseil", "Consulting", "Beratung"]),
            ("tech", ["Technologies", "Solutions", "Systems"]),
            ("commerce", ["Trading", "Commerce", "Import-Export"]),
            ("immobilier", ["Immobilier", "Immobilien", "Real Estate"]),
            ("services", ["Services", "Dienstleistungen"]),
        ]

        clients = []
        managers = [u for u in users if u.role in ["ADMIN", "MANAGER", "COMPTABLE"]]

        for i in range(count):
            # Choix aléatoire
            city_data = random.choice(swiss_cities)
            form_juridique = random.choice(company_types)
            sector = random.choice(business_sectors)

            # Génération nom entreprise
            base_name = fake.last_name()
            suffix = random.choice(sector[1])
            company_name = f"{base_name} {suffix}"
            if form_juridique[0] in ["SA", "SARL"]:
                company_name += f" {form_juridique[0]}"

            # Adresse
            adresse = Adresse.objects.create(
                rue=fake.street_name(),
                numero=str(fake.building_number()),
                npa=city_data[0],
                localite=city_data[1],
                canton=city_data[2],
                pays="CH",
            )

            # IDE et TVA
            ide_base = f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}"

            client = Client.objects.create(
                raison_sociale=company_name,
                nom_commercial=company_name,
                forme_juridique=form_juridique[0],
                ide_number=f"CHE-{ide_base}",
                tva_number=f"CHE-{ide_base} TVA" if random.random() > 0.2 else "",
                adresse_siege=adresse,
                email=f"info@{base_name.lower()}.ch",
                telephone=fake.phone_number(),
                site_web=f"https://www.{base_name.lower()}.ch",
                date_creation=fake.date_between(start_date="-15y", end_date="-1y"),
                date_debut_exercice=date(datetime.now().year, 1, 1),
                date_fin_exercice=date(datetime.now().year, 12, 31),
                statut="ACTIF",
                responsable=random.choice(managers),
            )

            # Contact principal
            contact = Contact.objects.create(
                client=client,
                civilite=random.choice(["M", "MME"]),
                nom=fake.last_name(),
                prenom=fake.first_name(),
                fonction=random.choice(["DIRECTEUR", "GERANT", "ADMIN"]),
                email=f"direction@{base_name.lower()}.ch",
                telephone=fake.phone_number(),
                mobile=fake.phone_number(),
                principal=True,
            )

            client.contact_principal = contact
            client.save()

            clients.append(client)

        self.stdout.write(f"  ✓ {len(clients)} clients créés")
        return clients

    def _create_mandats(self, clients, users):
        """Crée des mandats pour chaque client"""
        from core.models import Mandat, ExerciceComptable

        self.stdout.write("📋 Création des mandats...")

        mandats = []
        managers = [u for u in users if u.role in ["ADMIN", "MANAGER", "COMPTABLE"]]

        mandat_types = [
            ("GLOBAL", "Mandat global", Decimal("2500"), Decimal("180")),
            ("COMPTA", "Comptabilité", Decimal("1500"), Decimal("150")),
            ("SALAIRES", "Gestion des salaires", Decimal("800"), Decimal("120")),
            ("TVA", "Déclarations TVA", Decimal("500"), Decimal("140")),
            ("FISCAL", "Conseil fiscal", None, Decimal("200")),
        ]

        for client in clients:
            # Chaque client a entre 1 et 3 mandats
            num_mandats = random.randint(1, 3)
            selected_types = random.sample(
                mandat_types, min(num_mandats, len(mandat_types))
            )

            for type_data in selected_types:
                mandat = Mandat.objects.create(
                    client=client,
                    type_mandat=type_data[0],
                    date_debut=fake.date_between(start_date="-3y", end_date="-6m"),
                    periodicite=random.choice(["MENSUEL", "TRIMESTRIEL"]),
                    type_facturation="FORFAIT" if type_data[2] else "HORAIRE",
                    montant_forfait=type_data[2],
                    taux_horaire=type_data[3],
                    responsable=random.choice(managers),
                    statut="ACTIF",
                    description=f"Mandat {type_data[1]} pour {client.raison_sociale}",
                )

                # Ajouter équipe
                team_size = random.randint(1, 3)
                mandat.equipe.add(*random.sample(users, min(team_size, len(users))))

                # Créer exercices comptables
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

                mandats.append(mandat)

        self.stdout.write(f"  ✓ {len(mandats)} mandats créés")
        return mandats

    def _ensure_chart_of_accounts(self, mandats):
        """S'assure que le plan comptable existe"""
        from comptabilite.models import PlanComptable
        from django.core.management import call_command

        self.stdout.write("📊 Vérification du plan comptable...")

        # Vérifier si un template existe
        if not PlanComptable.objects.filter(is_template=True).exists():
            self.stdout.write("  → Chargement du plan comptable suisse...")
            call_command("load_swiss_chart_of_accounts", verbosity=0)

        # Associer aux mandats comptables
        template = PlanComptable.objects.filter(
            is_template=True, type_plan="PME"
        ).first()

        if template:
            compta_mandats = [
                m for m in mandats if m.type_mandat in ["COMPTA", "GLOBAL"]
            ]
            for mandat in compta_mandats:
                if not PlanComptable.objects.filter(mandat=mandat).exists():
                    # Créer une copie du plan pour ce mandat
                    self._duplicate_chart_for_mandat(template, mandat)

        self.stdout.write("  ✓ Plans comptables configurés")

    def _duplicate_chart_for_mandat(self, template, mandat):
        """Duplique le plan comptable template pour un mandat"""
        from comptabilite.models import PlanComptable, Compte

        # Créer le plan
        new_plan = PlanComptable.objects.create(
            nom_fr=f"Plan comptable - {mandat.client.raison_sociale}",
            nom_de=template.nom_de,
            nom_it=template.nom_it,
            nom_en=template.nom_en,
            type_plan=template.type_plan,
            mandat=mandat,
            is_template=False,
            base_sur=template,
        )

        # Copier les comptes (en préservant la hiérarchie)
        code_to_new = {}

        for compte in template.comptes.all().order_by("numero"):
            parent = (
                code_to_new.get(compte.compte_parent.numero)
                if compte.compte_parent
                else None
            )

            new_compte = Compte.objects.create(
                plan_comptable=new_plan,
                numero=compte.numero,
                libelle_fr=compte.libelle_fr,
                libelle_de=compte.libelle_de,
                libelle_it=compte.libelle_it,
                libelle_en=compte.libelle_en,
                libelle_court_fr=compte.libelle_court_fr,
                libelle_court_de=compte.libelle_court_de,
                libelle_court_it=compte.libelle_court_it,
                libelle_court_en=compte.libelle_court_en,
                type_compte=compte.type_compte,
                classe=compte.classe,
                niveau=compte.niveau,
                compte_parent=parent,
                est_collectif=compte.est_collectif,
                imputable=compte.imputable,
                lettrable=compte.lettrable,
                soumis_tva=compte.soumis_tva,
                code_tva_defaut=compte.code_tva_defaut,
            )
            code_to_new[compte.numero] = new_compte

    # ... autres méthodes _create_accounting_data, _create_invoicing_data, etc.
