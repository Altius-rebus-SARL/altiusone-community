# comptabilite/management/commands/load_swiss_chart_of_accounts.py
"""
Commande pour charger les plans comptables standards.

Usage:
    python manage.py load_swiss_chart_of_accounts --type PME
    python manage.py load_swiss_chart_of_accounts --type OHADA
    python manage.py load_swiss_chart_of_accounts --type SWISSGAAP
    python manage.py load_swiss_chart_of_accounts --mandat-id <uuid> --type PME
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from comptabilite.models import TypePlanComptable, ClasseComptable, PlanComptable, Compte


class Command(BaseCommand):
    help = "Charge un plan comptable standard avec traductions (FR/DE/IT/EN)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mandat-id",
            type=str,
            help="UUID du mandat auquel rattacher le plan (optionnel, crée un template si omis)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force la recréation même si le plan existe déjà",
        )
        parser.add_argument(
            "--type",
            type=str,
            default="PME",
            choices=["PME", "GENERAL", "OHADA", "SWISSGAAP"],
            help="Type de plan comptable à charger",
        )

    def handle(self, *args, **options):
        plan_type_code = options["type"]

        self.stdout.write(
            self.style.WARNING(f"📊 Chargement du plan comptable {plan_type_code}...")
        )

        with transaction.atomic():
            # Récupérer le type de plan
            type_plan = self._get_or_create_type_plan(plan_type_code)

            # Créer ou récupérer le plan comptable
            plan = self._get_or_create_plan(options, type_plan)

            # Charger les données du plan comptable
            accounts_data = self._get_accounts_data(plan_type_code)

            # Créer les comptes
            created_count, updated_count = self._create_accounts(
                plan, type_plan, accounts_data, options["force"]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Plan "{plan.nom}" : {created_count} comptes créés, {updated_count} mis à jour'
                )
            )

            return str(plan.id)

    def _get_or_create_type_plan(self, code):
        """Récupère ou crée le type de plan comptable."""
        try:
            return TypePlanComptable.objects.get(code=code)
        except TypePlanComptable.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Type de plan {code} non trouvé, création...")
            )

            # Créer le type de plan avec la définition par défaut
            type_plans_config = self._get_type_plans_config()
            if code not in type_plans_config:
                raise ValueError(f"Configuration non trouvée pour le type {code}")

            config = type_plans_config[code]
            type_plan = TypePlanComptable.objects.create(
                code=code,
                nom=config['nom'],
                description=config['description'],
                pays=config['pays'],
                region=config['region'],
                norme_comptable=config['norme_comptable'],
                version=config['version'],
                ordre=config['ordre'],
            )

            # Créer les classes
            for classe_data in config['classes']:
                ClasseComptable.objects.create(
                    type_plan=type_plan,
                    numero=classe_data['numero'],
                    libelle=classe_data['libelle'],
                    type_compte=classe_data['type_compte'],
                    numero_debut=classe_data.get('numero_debut', ''),
                    numero_fin=classe_data.get('numero_fin', ''),
                )

            self.stdout.write(self.style.SUCCESS(f"  ✓ Type de plan {code} créé"))
            return type_plan

    def _get_type_plans_config(self):
        """Configuration des types de plans comptables."""
        return {
            'PME': {
                'nom': 'Plan Comptable PME Suisse',
                'description': 'Plan comptable standard pour les PME suisses selon le Code des obligations',
                'pays': 'Suisse',
                'region': 'Europe',
                'norme_comptable': 'CO (Code des obligations)',
                'version': '2023',
                'ordre': 1,
                'classes': [
                    {'numero': 1, 'libelle': 'Actifs', 'type_compte': 'ACTIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                    {'numero': 2, 'libelle': 'Passifs', 'type_compte': 'PASSIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                    {'numero': 3, 'libelle': 'Produits d\'exploitation', 'type_compte': 'PRODUIT', 'numero_debut': '3000', 'numero_fin': '3999'},
                    {'numero': 4, 'libelle': 'Charges de matériel', 'type_compte': 'CHARGE', 'numero_debut': '4000', 'numero_fin': '4999'},
                    {'numero': 5, 'libelle': 'Charges de personnel', 'type_compte': 'CHARGE', 'numero_debut': '5000', 'numero_fin': '5999'},
                    {'numero': 6, 'libelle': 'Autres charges d\'exploitation', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                    {'numero': 7, 'libelle': 'Résultats des activités annexes', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                    {'numero': 8, 'libelle': 'Résultats extraordinaires', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
                    {'numero': 9, 'libelle': 'Clôture', 'type_compte': 'RESULTAT', 'numero_debut': '9000', 'numero_fin': '9999'},
                ]
            },
            'OHADA': {
                'nom': 'Plan Comptable OHADA',
                'description': 'Système comptable OHADA pour les pays de la zone OHADA',
                'pays': 'Zone OHADA',
                'region': 'Afrique',
                'norme_comptable': 'SYSCOHADA révisé',
                'version': '2017',
                'ordre': 2,
                'classes': [
                    {'numero': 1, 'libelle': 'Comptes de ressources durables', 'type_compte': 'PASSIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                    {'numero': 2, 'libelle': 'Comptes d\'actif immobilisé', 'type_compte': 'ACTIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                    {'numero': 3, 'libelle': 'Comptes de stocks', 'type_compte': 'ACTIF', 'numero_debut': '3000', 'numero_fin': '3999'},
                    {'numero': 4, 'libelle': 'Comptes de tiers', 'type_compte': 'ACTIF', 'numero_debut': '4000', 'numero_fin': '4999'},
                    {'numero': 5, 'libelle': 'Comptes de trésorerie', 'type_compte': 'ACTIF', 'numero_debut': '5000', 'numero_fin': '5999'},
                    {'numero': 6, 'libelle': 'Comptes de charges des activités ordinaires', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                    {'numero': 7, 'libelle': 'Comptes de produits des activités ordinaires', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                    {'numero': 8, 'libelle': 'Comptes des autres charges et produits', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
                ]
            },
            'SWISSGAAP': {
                'nom': 'Plan Comptable Swiss GAAP RPC',
                'description': 'Plan comptable selon les recommandations relatives à la présentation des comptes',
                'pays': 'Suisse',
                'region': 'Europe',
                'norme_comptable': 'Swiss GAAP RPC',
                'version': '2023',
                'ordre': 3,
                'classes': [
                    {'numero': 1, 'libelle': 'Actifs', 'type_compte': 'ACTIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                    {'numero': 2, 'libelle': 'Passifs', 'type_compte': 'PASSIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                    {'numero': 3, 'libelle': 'Produits d\'exploitation', 'type_compte': 'PRODUIT', 'numero_debut': '3000', 'numero_fin': '3999'},
                    {'numero': 4, 'libelle': 'Charges de matériel', 'type_compte': 'CHARGE', 'numero_debut': '4000', 'numero_fin': '4999'},
                    {'numero': 5, 'libelle': 'Charges de personnel', 'type_compte': 'CHARGE', 'numero_debut': '5000', 'numero_fin': '5999'},
                    {'numero': 6, 'libelle': 'Autres charges d\'exploitation', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                    {'numero': 7, 'libelle': 'Résultats des activités annexes', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                    {'numero': 8, 'libelle': 'Résultats extraordinaires', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
                    {'numero': 9, 'libelle': 'Clôture', 'type_compte': 'RESULTAT', 'numero_debut': '9000', 'numero_fin': '9999'},
                ]
            },
            'GENERAL': {
                'nom': 'Plan Comptable Général',
                'description': 'Plan comptable général standard',
                'pays': '',
                'region': '',
                'norme_comptable': 'Standard',
                'version': '2023',
                'ordre': 4,
                'classes': [
                    {'numero': 1, 'libelle': 'Actifs', 'type_compte': 'ACTIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                    {'numero': 2, 'libelle': 'Passifs', 'type_compte': 'PASSIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                    {'numero': 3, 'libelle': 'Produits', 'type_compte': 'PRODUIT', 'numero_debut': '3000', 'numero_fin': '3999'},
                    {'numero': 4, 'libelle': 'Charges', 'type_compte': 'CHARGE', 'numero_debut': '4000', 'numero_fin': '4999'},
                    {'numero': 5, 'libelle': 'Charges de personnel', 'type_compte': 'CHARGE', 'numero_debut': '5000', 'numero_fin': '5999'},
                    {'numero': 6, 'libelle': 'Autres charges', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                    {'numero': 7, 'libelle': 'Autres produits', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                    {'numero': 8, 'libelle': 'Résultats', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
                    {'numero': 9, 'libelle': 'Clôture', 'type_compte': 'RESULTAT', 'numero_debut': '9000', 'numero_fin': '9999'},
                ]
            },
        }

    def _get_or_create_plan(self, options, type_plan):
        """Crée ou récupère le plan comptable"""
        from core.models import Mandat

        mandat = None
        if options["mandat_id"]:
            mandat = Mandat.objects.get(pk=options["mandat_id"])

        plan_names = {
            "PME": {
                "nom_fr": "Plan Comptable PME Suisse",
                "nom_de": "Schweizer KMU-Kontenrahmen",
                "nom_it": "Piano Contabile PMI Svizzero",
                "nom_en": "Swiss SME Chart of Accounts",
            },
            "GENERAL": {
                "nom_fr": "Plan Comptable Général",
                "nom_de": "Allgemeiner Kontenrahmen",
                "nom_it": "Piano Contabile Generale",
                "nom_en": "General Chart of Accounts",
            },
            "OHADA": {
                "nom_fr": "Plan Comptable OHADA",
                "nom_de": "OHADA-Kontenrahmen",
                "nom_it": "Piano Contabile OHADA",
                "nom_en": "OHADA Chart of Accounts",
            },
            "SWISSGAAP": {
                "nom_fr": "Plan Comptable Swiss GAAP RPC",
                "nom_de": "Swiss GAAP FER Kontenrahmen",
                "nom_it": "Piano Contabile Swiss GAAP RPC",
                "nom_en": "Swiss GAAP FER Chart of Accounts",
            },
        }

        names = plan_names.get(type_plan.code, plan_names["PME"])

        defaults = {
            "nom_fr": names["nom_fr"],
            "nom_de": names["nom_de"],
            "nom_it": names["nom_it"],
            "nom_en": names["nom_en"],
            "description_fr": f"Plan comptable standard {type_plan.code}",
            "description_de": f"Standard-Kontenrahmen {type_plan.code}",
            "description_it": f"Piano contabile standard {type_plan.code}",
            "description_en": f"Standard {type_plan.code} chart of accounts",
            "type_plan": type_plan,
            "is_template": mandat is None,
            "mandat": mandat,
        }

        if mandat:
            plan, created = PlanComptable.objects.get_or_create(
                mandat=mandat, type_plan=type_plan, defaults=defaults
            )
        else:
            plan, created = PlanComptable.objects.get_or_create(
                is_template=True, type_plan=type_plan, defaults=defaults
            )

        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Plan créé: {plan.nom}"))
        else:
            self.stdout.write(f"  → Plan existant: {plan.nom}")
            if options["force"]:
                # Mettre à jour les traductions
                for key, value in defaults.items():
                    if key != 'type_plan':  # Ne pas écraser le type_plan
                        setattr(plan, key, value)
                plan.save()
                self.stdout.write("  → Traductions mises à jour")

        return plan

    def _get_accounts_data(self, plan_type):
        """Retourne les données du plan comptable selon le type."""
        if plan_type == "OHADA":
            return self._get_ohada_accounts()
        else:
            # PME, SWISSGAAP, GENERAL utilisent la structure suisse
            return self._get_swiss_pme_accounts()

    def _get_swiss_pme_accounts(self):
        """Retourne les données du plan comptable suisse PME avec traductions"""

        # Structure complète du plan comptable suisse PME
        return [
            # ═══════════════════════════════════════════════════════════════
            # CLASSE 1 - ACTIFS
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "1",
                "labels": {
                    "fr": "Actifs",
                    "de": "Aktiven",
                    "it": "Attivi",
                    "en": "Assets",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": None,
            },
            # 10 - Actifs circulants
            {
                "code": "10",
                "labels": {
                    "fr": "Actifs circulants",
                    "de": "Umlaufvermögen",
                    "it": "Attivo circolante",
                    "en": "Current assets",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "1",
            },
            # 100 - Liquidités
            {
                "code": "100",
                "labels": {
                    "fr": "Liquidités",
                    "de": "Flüssige Mittel",
                    "it": "Liquidità",
                    "en": "Cash and cash equivalents",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "10",
            },
            {
                "code": "1000",
                "labels": {
                    "fr": "Caisse",
                    "de": "Kasse",
                    "it": "Cassa",
                    "en": "Cash on hand",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "100",
                "imputable": True,
            },
            {
                "code": "1020",
                "labels": {
                    "fr": "Banque (avoir)",
                    "de": "Bank (Guthaben)",
                    "it": "Banca (avere)",
                    "en": "Bank (credit balance)",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "100",
                "imputable": True,
            },
            # 110 - Créances clients
            {
                "code": "110",
                "labels": {
                    "fr": "Créances résultant de livraisons et prestations",
                    "de": "Forderungen aus Lieferungen und Leistungen",
                    "it": "Crediti da forniture e prestazioni",
                    "en": "Trade receivables",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "10",
            },
            {
                "code": "1100",
                "labels": {
                    "fr": "Créances clients (Débiteurs)",
                    "de": "Forderungen aus Lieferungen und Leistungen (Debitoren)",
                    "it": "Crediti verso clienti (Debitori)",
                    "en": "Trade receivables (Debtors)",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "110",
                "imputable": True,
                "lettrable": True,
            },
            {
                "code": "1170",
                "labels": {
                    "fr": "Impôt préalable TVA",
                    "de": "Vorsteuer MWST",
                    "it": "Imposta precedente IVA",
                    "en": "Input VAT",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "110",
                "imputable": True,
                "soumis_tva": True,
            },
            # 120 - Stocks
            {
                "code": "120",
                "labels": {
                    "fr": "Stocks",
                    "de": "Vorräte",
                    "it": "Scorte",
                    "en": "Inventories",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "10",
            },
            {
                "code": "1200",
                "labels": {
                    "fr": "Marchandises",
                    "de": "Handelswaren",
                    "it": "Merci",
                    "en": "Goods",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "120",
                "imputable": True,
            },
            # 14 - Actifs immobilisés
            {
                "code": "14",
                "labels": {
                    "fr": "Actifs immobilisés",
                    "de": "Anlagevermögen",
                    "it": "Attivo fisso",
                    "en": "Fixed assets",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "1",
            },
            {
                "code": "1500",
                "labels": {
                    "fr": "Machines et appareils",
                    "de": "Maschinen und Apparate",
                    "it": "Macchine e apparecchi",
                    "en": "Machinery and equipment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "14",
                "imputable": True,
            },
            {
                "code": "1510",
                "labels": {
                    "fr": "Mobilier et installations",
                    "de": "Mobiliar und Einrichtungen",
                    "it": "Mobili e installazioni",
                    "en": "Furniture and fixtures",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "14",
                "imputable": True,
            },
            {
                "code": "1530",
                "labels": {
                    "fr": "Véhicules",
                    "de": "Fahrzeuge",
                    "it": "Veicoli",
                    "en": "Vehicles",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "14",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 2 - PASSIF
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "2",
                "labels": {
                    "fr": "Passif",
                    "de": "Passiven",
                    "it": "Passivi",
                    "en": "Liabilities and equity",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": None,
            },
            # 20 - Dettes à court terme
            {
                "code": "20",
                "labels": {
                    "fr": "Dettes à court terme",
                    "de": "Kurzfristiges Fremdkapital",
                    "it": "Debiti a breve termine",
                    "en": "Short-term liabilities",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "2",
            },
            {
                "code": "2000",
                "labels": {
                    "fr": "Dettes fournisseurs (Créanciers)",
                    "de": "Verbindlichkeiten (Kreditoren)",
                    "it": "Debiti verso fornitori (Creditori)",
                    "en": "Trade payables (Creditors)",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "20",
                "imputable": True,
                "lettrable": True,
            },
            {
                "code": "2200",
                "labels": {
                    "fr": "TVA due",
                    "de": "Geschuldete MWST",
                    "it": "IVA dovuta",
                    "en": "VAT payable",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "20",
                "imputable": True,
                "soumis_tva": True,
            },
            # 28 - Fonds propres
            {
                "code": "28",
                "labels": {
                    "fr": "Fonds propres",
                    "de": "Eigenkapital",
                    "it": "Capitale proprio",
                    "en": "Equity",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "2",
            },
            {
                "code": "2800",
                "labels": {
                    "fr": "Capital social",
                    "de": "Aktienkapital",
                    "it": "Capitale sociale",
                    "en": "Share capital",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "28",
                "imputable": True,
            },
            {
                "code": "2970",
                "labels": {
                    "fr": "Bénéfice reporté",
                    "de": "Gewinnvortrag",
                    "it": "Utile riportato",
                    "en": "Retained earnings",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "28",
                "imputable": True,
            },
            {
                "code": "2979",
                "labels": {
                    "fr": "Bénéfice / perte de l'exercice",
                    "de": "Jahresgewinn/-verlust",
                    "it": "Utile/perdita dell'esercizio",
                    "en": "Net income/loss",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "28",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 3 - PRODUITS D'EXPLOITATION
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "3",
                "labels": {
                    "fr": "Produits d'exploitation",
                    "de": "Betriebsertrag",
                    "it": "Ricavi d'esercizio",
                    "en": "Operating revenue",
                },
                "type": "PRODUIT",
                "classe": 3,
                "parent": None,
            },
            {
                "code": "3000",
                "labels": {
                    "fr": "Ventes de produits",
                    "de": "Produktionserlöse",
                    "it": "Vendite di prodotti",
                    "en": "Sales of products",
                },
                "type": "PRODUIT",
                "classe": 3,
                "parent": "3",
                "imputable": True,
                "soumis_tva": True,
            },
            {
                "code": "3200",
                "labels": {
                    "fr": "Ventes de marchandises",
                    "de": "Handelserlöse",
                    "it": "Vendite di merci",
                    "en": "Sales of goods",
                },
                "type": "PRODUIT",
                "classe": 3,
                "parent": "3",
                "imputable": True,
                "soumis_tva": True,
            },
            {
                "code": "3400",
                "labels": {
                    "fr": "Ventes de prestations de services",
                    "de": "Dienstleistungserlöse",
                    "it": "Vendite di servizi",
                    "en": "Sales of services",
                },
                "type": "PRODUIT",
                "classe": 3,
                "parent": "3",
                "imputable": True,
                "soumis_tva": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 4 - CHARGES DE MATÉRIEL
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "4",
                "labels": {
                    "fr": "Charges de matériel",
                    "de": "Materialaufwand",
                    "it": "Costi del materiale",
                    "en": "Material costs",
                },
                "type": "CHARGE",
                "classe": 4,
                "parent": None,
            },
            {
                "code": "4000",
                "labels": {
                    "fr": "Achats de matériel",
                    "de": "Materialeinkauf",
                    "it": "Acquisti di materiale",
                    "en": "Material purchases",
                },
                "type": "CHARGE",
                "classe": 4,
                "parent": "4",
                "imputable": True,
            },
            {
                "code": "4200",
                "labels": {
                    "fr": "Achats de marchandises",
                    "de": "Einkauf Handelswaren",
                    "it": "Acquisti di merci",
                    "en": "Purchase of goods",
                },
                "type": "CHARGE",
                "classe": 4,
                "parent": "4",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 5 - CHARGES DE PERSONNEL
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "5",
                "labels": {
                    "fr": "Charges de personnel",
                    "de": "Personalaufwand",
                    "it": "Costi del personale",
                    "en": "Personnel expenses",
                },
                "type": "CHARGE",
                "classe": 5,
                "parent": None,
            },
            {
                "code": "5000",
                "labels": {
                    "fr": "Salaires",
                    "de": "Löhne",
                    "it": "Salari",
                    "en": "Wages and salaries",
                },
                "type": "CHARGE",
                "classe": 5,
                "parent": "5",
                "imputable": True,
            },
            {
                "code": "5700",
                "labels": {
                    "fr": "Charges sociales",
                    "de": "Sozialversicherungsaufwand",
                    "it": "Oneri sociali",
                    "en": "Social security expenses",
                },
                "type": "CHARGE",
                "classe": 5,
                "parent": "5",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 6 - AUTRES CHARGES D'EXPLOITATION
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "6",
                "labels": {
                    "fr": "Autres charges d'exploitation",
                    "de": "Übriger betrieblicher Aufwand",
                    "it": "Altri costi d'esercizio",
                    "en": "Other operating expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": None,
            },
            {
                "code": "6000",
                "labels": {
                    "fr": "Charges de locaux",
                    "de": "Raumaufwand",
                    "it": "Costi dei locali",
                    "en": "Occupancy costs",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6500",
                "labels": {
                    "fr": "Charges d'administration",
                    "de": "Verwaltungsaufwand",
                    "it": "Costi amministrativi",
                    "en": "Administrative expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6800",
                "labels": {
                    "fr": "Amortissements",
                    "de": "Abschreibungen",
                    "it": "Ammortamenti",
                    "en": "Depreciation",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6900",
                "labels": {
                    "fr": "Charges financières",
                    "de": "Finanzaufwand",
                    "it": "Oneri finanziari",
                    "en": "Financial expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 8 - RÉSULTATS EXTRAORDINAIRES
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "8",
                "labels": {
                    "fr": "Résultats extraordinaires",
                    "de": "Ausserordentlicher Erfolg",
                    "it": "Risultato straordinario",
                    "en": "Extraordinary results",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": None,
            },
            {
                "code": "8500",
                "labels": {
                    "fr": "Charges extraordinaires",
                    "de": "Ausserordentlicher Aufwand",
                    "it": "Costi straordinari",
                    "en": "Extraordinary expenses",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": "8",
                "imputable": True,
            },
            {
                "code": "8510",
                "labels": {
                    "fr": "Produits extraordinaires",
                    "de": "Ausserordentlicher Ertrag",
                    "it": "Proventi straordinari",
                    "en": "Extraordinary income",
                },
                "type": "PRODUIT",
                "classe": 8,
                "parent": "8",
                "imputable": True,
            },
            {
                "code": "8900",
                "labels": {
                    "fr": "Impôts",
                    "de": "Steuern",
                    "it": "Imposte",
                    "en": "Taxes",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": "8",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 9 - CLÔTURE
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "9",
                "labels": {
                    "fr": "Clôture",
                    "de": "Abschluss",
                    "it": "Chiusura",
                    "en": "Closing",
                },
                "type": "CHARGE",
                "classe": 9,
                "parent": None,
            },
            {
                "code": "9200",
                "labels": {
                    "fr": "Résultat de l'exercice",
                    "de": "Jahresergebnis",
                    "it": "Risultato dell'esercizio",
                    "en": "Annual result",
                },
                "type": "CHARGE",
                "classe": 9,
                "parent": "9",
                "imputable": True,
            },
        ]

    def _get_ohada_accounts(self):
        """Retourne les données du plan comptable OHADA."""
        return [
            # ═══════════════════════════════════════════════════════════════
            # CLASSE 1 - COMPTES DE RESSOURCES DURABLES
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "1",
                "labels": {
                    "fr": "Comptes de ressources durables",
                    "en": "Long-term resources accounts",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": None,
            },
            {
                "code": "10",
                "labels": {
                    "fr": "Capital",
                    "en": "Capital",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "1",
            },
            {
                "code": "101",
                "labels": {
                    "fr": "Capital social",
                    "en": "Share capital",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "10",
                "imputable": True,
            },
            {
                "code": "11",
                "labels": {
                    "fr": "Réserves",
                    "en": "Reserves",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "1",
            },
            {
                "code": "111",
                "labels": {
                    "fr": "Réserve légale",
                    "en": "Legal reserve",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "11",
                "imputable": True,
            },
            {
                "code": "12",
                "labels": {
                    "fr": "Report à nouveau",
                    "en": "Retained earnings",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "1",
            },
            {
                "code": "121",
                "labels": {
                    "fr": "Report à nouveau créditeur",
                    "en": "Retained earnings (credit)",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "12",
                "imputable": True,
            },
            {
                "code": "13",
                "labels": {
                    "fr": "Résultat net de l'exercice",
                    "en": "Net result",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "1",
            },
            {
                "code": "131",
                "labels": {
                    "fr": "Résultat net: bénéfice",
                    "en": "Net result: profit",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "13",
                "imputable": True,
            },
            {
                "code": "16",
                "labels": {
                    "fr": "Emprunts et dettes assimilées",
                    "en": "Borrowings and similar debts",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "1",
            },
            {
                "code": "161",
                "labels": {
                    "fr": "Emprunts obligataires",
                    "en": "Bond loans",
                },
                "type": "PASSIF",
                "classe": 1,
                "parent": "16",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 2 - COMPTES D'ACTIF IMMOBILISÉ
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "2",
                "labels": {
                    "fr": "Comptes d'actif immobilisé",
                    "en": "Fixed assets accounts",
                },
                "type": "ACTIF",
                "classe": 2,
                "parent": None,
            },
            {
                "code": "21",
                "labels": {
                    "fr": "Immobilisations incorporelles",
                    "en": "Intangible assets",
                },
                "type": "ACTIF",
                "classe": 2,
                "parent": "2",
            },
            {
                "code": "211",
                "labels": {
                    "fr": "Frais de développement",
                    "en": "Development costs",
                },
                "type": "ACTIF",
                "classe": 2,
                "parent": "21",
                "imputable": True,
            },
            {
                "code": "22",
                "labels": {
                    "fr": "Terrains",
                    "en": "Land",
                },
                "type": "ACTIF",
                "classe": 2,
                "parent": "2",
            },
            {
                "code": "221",
                "labels": {
                    "fr": "Terrains agricoles et forestiers",
                    "en": "Agricultural and forest land",
                },
                "type": "ACTIF",
                "classe": 2,
                "parent": "22",
                "imputable": True,
            },
            {
                "code": "23",
                "labels": {
                    "fr": "Bâtiments, installations techniques et agencements",
                    "en": "Buildings, technical installations and fixtures",
                },
                "type": "ACTIF",
                "classe": 2,
                "parent": "2",
            },
            {
                "code": "231",
                "labels": {
                    "fr": "Bâtiments industriels",
                    "en": "Industrial buildings",
                },
                "type": "ACTIF",
                "classe": 2,
                "parent": "23",
                "imputable": True,
            },
            {
                "code": "24",
                "labels": {
                    "fr": "Matériel",
                    "en": "Equipment",
                },
                "type": "ACTIF",
                "classe": 2,
                "parent": "2",
            },
            {
                "code": "241",
                "labels": {
                    "fr": "Matériel et outillage industriel",
                    "en": "Industrial equipment and tools",
                },
                "type": "ACTIF",
                "classe": 2,
                "parent": "24",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 3 - COMPTES DE STOCKS
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "3",
                "labels": {
                    "fr": "Comptes de stocks",
                    "en": "Inventory accounts",
                },
                "type": "ACTIF",
                "classe": 3,
                "parent": None,
            },
            {
                "code": "31",
                "labels": {
                    "fr": "Marchandises",
                    "en": "Goods",
                },
                "type": "ACTIF",
                "classe": 3,
                "parent": "3",
            },
            {
                "code": "311",
                "labels": {
                    "fr": "Marchandises A",
                    "en": "Goods A",
                },
                "type": "ACTIF",
                "classe": 3,
                "parent": "31",
                "imputable": True,
            },
            {
                "code": "32",
                "labels": {
                    "fr": "Matières premières et fournitures liées",
                    "en": "Raw materials and related supplies",
                },
                "type": "ACTIF",
                "classe": 3,
                "parent": "3",
            },
            {
                "code": "321",
                "labels": {
                    "fr": "Matières premières",
                    "en": "Raw materials",
                },
                "type": "ACTIF",
                "classe": 3,
                "parent": "32",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 4 - COMPTES DE TIERS
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "4",
                "labels": {
                    "fr": "Comptes de tiers",
                    "en": "Third-party accounts",
                },
                "type": "ACTIF",
                "classe": 4,
                "parent": None,
            },
            {
                "code": "40",
                "labels": {
                    "fr": "Fournisseurs et comptes rattachés",
                    "en": "Suppliers and related accounts",
                },
                "type": "PASSIF",
                "classe": 4,
                "parent": "4",
            },
            {
                "code": "401",
                "labels": {
                    "fr": "Fournisseurs, dettes en compte",
                    "en": "Suppliers, account payables",
                },
                "type": "PASSIF",
                "classe": 4,
                "parent": "40",
                "imputable": True,
                "lettrable": True,
            },
            {
                "code": "41",
                "labels": {
                    "fr": "Clients et comptes rattachés",
                    "en": "Customers and related accounts",
                },
                "type": "ACTIF",
                "classe": 4,
                "parent": "4",
            },
            {
                "code": "411",
                "labels": {
                    "fr": "Clients",
                    "en": "Customers",
                },
                "type": "ACTIF",
                "classe": 4,
                "parent": "41",
                "imputable": True,
                "lettrable": True,
            },
            {
                "code": "44",
                "labels": {
                    "fr": "État et collectivités publiques",
                    "en": "Government and public entities",
                },
                "type": "PASSIF",
                "classe": 4,
                "parent": "4",
            },
            {
                "code": "443",
                "labels": {
                    "fr": "État, TVA collectée",
                    "en": "State, VAT collected",
                },
                "type": "PASSIF",
                "classe": 4,
                "parent": "44",
                "imputable": True,
                "soumis_tva": True,
            },
            {
                "code": "445",
                "labels": {
                    "fr": "État, TVA récupérable",
                    "en": "State, recoverable VAT",
                },
                "type": "ACTIF",
                "classe": 4,
                "parent": "44",
                "imputable": True,
                "soumis_tva": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 5 - COMPTES DE TRÉSORERIE
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "5",
                "labels": {
                    "fr": "Comptes de trésorerie",
                    "en": "Cash accounts",
                },
                "type": "ACTIF",
                "classe": 5,
                "parent": None,
            },
            {
                "code": "52",
                "labels": {
                    "fr": "Banques",
                    "en": "Banks",
                },
                "type": "ACTIF",
                "classe": 5,
                "parent": "5",
            },
            {
                "code": "521",
                "labels": {
                    "fr": "Banques locales",
                    "en": "Local banks",
                },
                "type": "ACTIF",
                "classe": 5,
                "parent": "52",
                "imputable": True,
            },
            {
                "code": "57",
                "labels": {
                    "fr": "Caisse",
                    "en": "Cash on hand",
                },
                "type": "ACTIF",
                "classe": 5,
                "parent": "5",
            },
            {
                "code": "571",
                "labels": {
                    "fr": "Caisse siège social",
                    "en": "Head office cash",
                },
                "type": "ACTIF",
                "classe": 5,
                "parent": "57",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 6 - COMPTES DE CHARGES DES ACTIVITÉS ORDINAIRES
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "6",
                "labels": {
                    "fr": "Comptes de charges des activités ordinaires",
                    "en": "Operating expense accounts",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": None,
            },
            {
                "code": "60",
                "labels": {
                    "fr": "Achats et variations de stocks",
                    "en": "Purchases and inventory changes",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
            },
            {
                "code": "601",
                "labels": {
                    "fr": "Achats de marchandises",
                    "en": "Purchase of goods",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "60",
                "imputable": True,
            },
            {
                "code": "66",
                "labels": {
                    "fr": "Charges de personnel",
                    "en": "Personnel expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
            },
            {
                "code": "661",
                "labels": {
                    "fr": "Rémunérations directes",
                    "en": "Direct compensation",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "66",
                "imputable": True,
            },
            {
                "code": "68",
                "labels": {
                    "fr": "Dotations aux amortissements",
                    "en": "Depreciation charges",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
            },
            {
                "code": "681",
                "labels": {
                    "fr": "Dotations aux amortissements d'exploitation",
                    "en": "Operating depreciation charges",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "68",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 7 - COMPTES DE PRODUITS DES ACTIVITÉS ORDINAIRES
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "7",
                "labels": {
                    "fr": "Comptes de produits des activités ordinaires",
                    "en": "Operating income accounts",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": None,
            },
            {
                "code": "70",
                "labels": {
                    "fr": "Ventes",
                    "en": "Sales",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "7",
            },
            {
                "code": "701",
                "labels": {
                    "fr": "Ventes de marchandises",
                    "en": "Sales of goods",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "70",
                "imputable": True,
                "soumis_tva": True,
            },
            {
                "code": "706",
                "labels": {
                    "fr": "Services vendus",
                    "en": "Services sold",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "70",
                "imputable": True,
                "soumis_tva": True,
            },
            {
                "code": "71",
                "labels": {
                    "fr": "Subventions d'exploitation",
                    "en": "Operating subsidies",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "7",
            },
            {
                "code": "711",
                "labels": {
                    "fr": "Subventions d'exploitation reçues",
                    "en": "Operating subsidies received",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "71",
                "imputable": True,
            },

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 8 - COMPTES DES AUTRES CHARGES ET PRODUITS
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "8",
                "labels": {
                    "fr": "Comptes des autres charges et produits",
                    "en": "Other charges and income accounts",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": None,
            },
            {
                "code": "81",
                "labels": {
                    "fr": "Valeurs comptables des cessions d'immobilisations",
                    "en": "Book values of asset disposals",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": "8",
            },
            {
                "code": "811",
                "labels": {
                    "fr": "Valeurs comptables des cessions d'immobilisations incorporelles",
                    "en": "Book values of intangible asset disposals",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": "81",
                "imputable": True,
            },
            {
                "code": "82",
                "labels": {
                    "fr": "Produits des cessions d'immobilisations",
                    "en": "Proceeds from asset disposals",
                },
                "type": "PRODUIT",
                "classe": 8,
                "parent": "8",
            },
            {
                "code": "821",
                "labels": {
                    "fr": "Produits des cessions d'immobilisations incorporelles",
                    "en": "Proceeds from intangible asset disposals",
                },
                "type": "PRODUIT",
                "classe": 8,
                "parent": "82",
                "imputable": True,
            },
            {
                "code": "89",
                "labels": {
                    "fr": "Impôts sur le résultat",
                    "en": "Income taxes",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": "8",
            },
            {
                "code": "891",
                "labels": {
                    "fr": "Impôts sur les bénéfices de l'exercice",
                    "en": "Income tax expense",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": "89",
                "imputable": True,
            },
        ]

    def _create_accounts(self, plan, type_plan, accounts_data, force_update=False):
        """Crée les comptes avec hiérarchie et traductions"""

        # Récupérer les classes pour ce type de plan
        classes_map = {
            c.numero: c for c in ClasseComptable.objects.filter(type_plan=type_plan)
        }

        # Créer d'abord une map code -> account pour la hiérarchie
        code_to_account = {}
        created_count = 0
        updated_count = 0

        # Trier par longueur de code pour créer les parents d'abord
        sorted_accounts = sorted(accounts_data, key=lambda x: len(x["code"]))

        for account_data in sorted_accounts:
            code = account_data["code"]
            labels = account_data["labels"]
            parent_code = account_data.get("parent")

            # Trouver le parent
            parent_account = code_to_account.get(parent_code) if parent_code else None

            # Trouver la classe comptable
            classe_num = account_data.get("classe", int(code[0]) if code else 1)
            classe_comptable = classes_map.get(classe_num)

            # Préparer les données
            defaults = {
                "libelle_fr": labels.get("fr", ""),
                "libelle_de": labels.get("de", labels.get("fr", "")),
                "libelle_it": labels.get("it", labels.get("fr", "")),
                "libelle_en": labels.get("en", labels.get("fr", "")),
                "libelle_court_fr": labels.get("fr", "")[:100],
                "libelle_court_de": labels.get("de", labels.get("fr", ""))[:100],
                "libelle_court_it": labels.get("it", labels.get("fr", ""))[:100],
                "libelle_court_en": labels.get("en", labels.get("fr", ""))[:100],
                "type_compte": account_data.get("type", "ACTIF"),
                "classe": classe_num,
                "classe_comptable": classe_comptable,
                "niveau": len(code),
                "compte_parent": parent_account,
                "est_collectif": len(code) <= 2,
                "imputable": account_data.get("imputable", len(code) >= 3),
                "lettrable": account_data.get("lettrable", False),
                "soumis_tva": account_data.get("soumis_tva", False),
                "code_tva_defaut": account_data.get("code_tva_defaut", ""),
            }

            account, created = Compte.objects.update_or_create(
                plan_comptable=plan, numero=code, defaults=defaults
            )

            code_to_account[code] = account

            if created:
                created_count += 1
                self.stdout.write(f"  ✓ {code} - {labels.get('fr', '')}")
            elif force_update:
                updated_count += 1
                self.stdout.write(f"  ↻ {code} - {labels.get('fr', '')}")

        return created_count, updated_count
