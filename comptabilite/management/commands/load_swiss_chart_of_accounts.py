# comptabilite/management/commands/load_swiss_chart_of_accounts.py

from django.core.management.base import BaseCommand
from django.db import transaction
from comptabilite.models import PlanComptable, Compte
import json
from pathlib import Path


class Command(BaseCommand):
    help = "Charge le plan comptable suisse PME standard avec traductions (FR/DE/IT/EN)"

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
        self.stdout.write(
            self.style.WARNING("🇨🇭 Chargement du plan comptable suisse...")
        )

        plan_type = options["type"]

        with transaction.atomic():
            # Créer ou récupérer le plan comptable
            plan = self._get_or_create_plan(options, plan_type)

            # Charger les données du plan comptable
            accounts_data = self._get_accounts_data(plan_type)

            # Créer les comptes
            created_count, updated_count = self._create_accounts(
                plan, accounts_data, options["force"]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Plan "{plan.nom}" : {created_count} comptes créés, {updated_count} mis à jour'
                )
            )

            return str(plan.id)

    def _get_or_create_plan(self, options, plan_type):
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
                "nom_fr": "Plan Comptable Général Suisse",
                "nom_de": "Schweizer Allgemeiner Kontenrahmen",
                "nom_it": "Piano Contabile Generale Svizzero",
                "nom_en": "Swiss General Chart of Accounts",
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

        names = plan_names.get(plan_type, plan_names["PME"])

        defaults = {
            "nom_fr": names["nom_fr"],
            "nom_de": names["nom_de"],
            "nom_it": names["nom_it"],
            "nom_en": names["nom_en"],
            "description_fr": f"Plan comptable standard {plan_type} selon les normes suisses",
            "description_de": f"Standard-Kontenrahmen {plan_type} nach Schweizer Normen",
            "description_it": f"Piano contabile standard {plan_type} secondo le norme svizzere",
            "description_en": f"Standard {plan_type} chart of accounts according to Swiss standards",
            "type_plan": plan_type,
            "is_template": mandat is None,
            "mandat": mandat,
        }

        if mandat:
            plan, created = PlanComptable.objects.get_or_create(
                mandat=mandat, type_plan=plan_type, defaults=defaults
            )
        else:
            plan, created = PlanComptable.objects.get_or_create(
                is_template=True, type_plan=plan_type, defaults=defaults
            )

        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Plan créé: {plan.nom}"))
        else:
            self.stdout.write(f"  → Plan existant: {plan.nom}")
            if options["force"]:
                # Mettre à jour les traductions
                for key, value in defaults.items():
                    setattr(plan, key, value)
                plan.save()
                self.stdout.write("  → Traductions mises à jour")

        return plan

    def _get_accounts_data(self, plan_type):
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
                "code": "1010",
                "labels": {
                    "fr": "Caisse en monnaie étrangère",
                    "de": "Kasse Fremdwährung",
                    "it": "Cassa in valuta estera",
                    "en": "Foreign currency cash",
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
            {
                "code": "1021",
                "labels": {
                    "fr": "Compte postal",
                    "de": "Postkonto",
                    "it": "Conto postale",
                    "en": "Postal account",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "100",
                "imputable": True,
            },
            {
                "code": "1022",
                "labels": {
                    "fr": "Banque EUR",
                    "de": "Bank EUR",
                    "it": "Banca EUR",
                    "en": "Bank EUR",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "100",
                "imputable": True,
            },
            {
                "code": "1023",
                "labels": {
                    "fr": "Banque USD",
                    "de": "Bank USD",
                    "it": "Banca USD",
                    "en": "Bank USD",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "100",
                "imputable": True,
            },
            # 106 - Titres
            {
                "code": "106",
                "labels": {
                    "fr": "Avoirs à court terme cotés en bourse",
                    "de": "Kurzfristige kotierte Wertschriften",
                    "it": "Titoli a breve termine quotati",
                    "en": "Short-term listed securities",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "10",
            },
            {
                "code": "1060",
                "labels": {
                    "fr": "Titres",
                    "de": "Wertschriften",
                    "it": "Titoli",
                    "en": "Securities",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "106",
                "imputable": True,
            },
            {
                "code": "1069",
                "labels": {
                    "fr": "Ajustement de la valeur des titres",
                    "de": "Wertberichtigung Wertschriften",
                    "it": "Rettifica valore titoli",
                    "en": "Securities value adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "106",
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
                "code": "1101",
                "labels": {
                    "fr": "Effets à recevoir",
                    "de": "Wechselforderungen",
                    "it": "Effetti attivi",
                    "en": "Bills receivable",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "110",
                "imputable": True,
            },
            {
                "code": "1109",
                "labels": {
                    "fr": "Ducroire (Provision pour créances douteuses)",
                    "de": "Delkredere (Wertberichtigung Forderungen)",
                    "it": "Delcredere (Fondo svalutazione crediti)",
                    "en": "Allowance for doubtful accounts",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "110",
                "imputable": True,
            },
            {
                "code": "1110",
                "labels": {
                    "fr": "Créances envers sociétés du groupe",
                    "de": "Forderungen gegenüber Konzerngesellschaften",
                    "it": "Crediti verso società del gruppo",
                    "en": "Receivables from group companies",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "110",
                "imputable": True,
            },
            # 114 - Autres créances à court terme
            {
                "code": "114",
                "labels": {
                    "fr": "Autres créances à court terme",
                    "de": "Übrige kurzfristige Forderungen",
                    "it": "Altri crediti a breve termine",
                    "en": "Other short-term receivables",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "10",
            },
            {
                "code": "1140",
                "labels": {
                    "fr": "Avances et prêts à court terme",
                    "de": "Kurzfristige Vorschüsse und Darlehen",
                    "it": "Anticipi e prestiti a breve termine",
                    "en": "Short-term advances and loans",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "114",
                "imputable": True,
            },
            {
                "code": "1149",
                "labels": {
                    "fr": "Ajustement avances et prêts",
                    "de": "Wertberichtigung Vorschüsse und Darlehen",
                    "it": "Rettifica anticipi e prestiti",
                    "en": "Advances and loans adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "114",
                "imputable": True,
            },
            {
                "code": "1170",
                "labels": {
                    "fr": "Impôt préalable TVA sur matériel et prestations",
                    "de": "Vorsteuer MWST auf Material und Dienstleistungen",
                    "it": "Imposta precedente IVA su materiale e prestazioni",
                    "en": "Input VAT on materials and services",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "114",
                "imputable": True,
                "soumis_tva": True,
                "code_tva_defaut": "400",
            },
            {
                "code": "1171",
                "labels": {
                    "fr": "Impôt préalable TVA sur investissements",
                    "de": "Vorsteuer MWST auf Investitionen",
                    "it": "Imposta precedente IVA su investimenti",
                    "en": "Input VAT on investments",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "114",
                "imputable": True,
                "soumis_tva": True,
                "code_tva_defaut": "405",
            },
            {
                "code": "1176",
                "labels": {
                    "fr": "Impôt anticipé à récupérer",
                    "de": "Verrechnungssteuer",
                    "it": "Imposta preventiva da recuperare",
                    "en": "Withholding tax receivable",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "114",
                "imputable": True,
            },
            {
                "code": "1180",
                "labels": {
                    "fr": "Créances envers assurances sociales",
                    "de": "Forderungen gegenüber Sozialversicherungen",
                    "it": "Crediti verso assicurazioni sociali",
                    "en": "Receivables from social insurance",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "114",
                "imputable": True,
            },
            {
                "code": "1189",
                "labels": {
                    "fr": "Impôt à la source à récupérer",
                    "de": "Quellensteuer",
                    "it": "Imposta alla fonte da recuperare",
                    "en": "Withholding tax receivable",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "114",
                "imputable": True,
            },
            {
                "code": "1190",
                "labels": {
                    "fr": "Autres créances à court terme diverses",
                    "de": "Übrige kurzfristige Forderungen",
                    "it": "Altri crediti a breve termine diversi",
                    "en": "Other miscellaneous short-term receivables",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "114",
                "imputable": True,
            },
            # 120 - Stocks
            {
                "code": "120",
                "labels": {
                    "fr": "Stocks et prestations non facturées",
                    "de": "Vorräte und nicht fakturierte Dienstleistungen",
                    "it": "Scorte e prestazioni non fatturate",
                    "en": "Inventories and unbilled services",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "10",
            },
            {
                "code": "1200",
                "labels": {
                    "fr": "Marchandises commerciales",
                    "de": "Handelswaren",
                    "it": "Merci commerciali",
                    "en": "Trade goods",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "120",
                "imputable": True,
            },
            {
                "code": "1210",
                "labels": {
                    "fr": "Matières premières",
                    "de": "Rohstoffe",
                    "it": "Materie prime",
                    "en": "Raw materials",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "120",
                "imputable": True,
            },
            {
                "code": "1220",
                "labels": {
                    "fr": "Matières auxiliaires",
                    "de": "Hilfsstoffe",
                    "it": "Materiali ausiliari",
                    "en": "Auxiliary materials",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "120",
                "imputable": True,
            },
            {
                "code": "1230",
                "labels": {
                    "fr": "Matières consommables",
                    "de": "Betriebsstoffe",
                    "it": "Materiali di consumo",
                    "en": "Consumables",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "120",
                "imputable": True,
            },
            {
                "code": "1250",
                "labels": {
                    "fr": "Marchandises en consignation",
                    "de": "Waren in Konsignation",
                    "it": "Merci in consegna",
                    "en": "Consignment goods",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "120",
                "imputable": True,
            },
            {
                "code": "1260",
                "labels": {
                    "fr": "Produits finis",
                    "de": "Fertige Erzeugnisse",
                    "it": "Prodotti finiti",
                    "en": "Finished goods",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "120",
                "imputable": True,
            },
            {
                "code": "1270",
                "labels": {
                    "fr": "Produits semi-finis",
                    "de": "Unfertige Erzeugnisse",
                    "it": "Prodotti semilavorati",
                    "en": "Work in progress",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "120",
                "imputable": True,
            },
            {
                "code": "1280",
                "labels": {
                    "fr": "Travaux en cours",
                    "de": "Angefangene Arbeiten",
                    "it": "Lavori in corso",
                    "en": "Work in progress",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "120",
                "imputable": True,
            },
            # 130 - Comptes de régularisation actif
            {
                "code": "130",
                "labels": {
                    "fr": "Comptes de régularisation actif",
                    "de": "Aktive Rechnungsabgrenzung",
                    "it": "Ratei e risconti attivi",
                    "en": "Prepaid expenses and accrued income",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "10",
            },
            {
                "code": "1300",
                "labels": {
                    "fr": "Charges payées d'avance",
                    "de": "Vorausbezahlte Aufwendungen",
                    "it": "Spese pagate in anticipo",
                    "en": "Prepaid expenses",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "130",
                "imputable": True,
            },
            {
                "code": "1301",
                "labels": {
                    "fr": "Produits à recevoir",
                    "de": "Noch nicht erhaltene Erträge",
                    "it": "Proventi da ricevere",
                    "en": "Accrued income",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "130",
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
            # 140 - Immobilisations financières
            {
                "code": "140",
                "labels": {
                    "fr": "Immobilisations financières",
                    "de": "Finanzanlagen",
                    "it": "Immobilizzazioni finanziarie",
                    "en": "Financial assets",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "14",
            },
            {
                "code": "1400",
                "labels": {
                    "fr": "Titres à long terme",
                    "de": "Langfristige Wertschriften",
                    "it": "Titoli a lungo termine",
                    "en": "Long-term securities",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "140",
                "imputable": True,
            },
            {
                "code": "1409",
                "labels": {
                    "fr": "Ajustement titres à long terme",
                    "de": "Wertberichtigung langfristige Wertschriften",
                    "it": "Rettifica titoli a lungo termine",
                    "en": "Long-term securities adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "140",
                "imputable": True,
            },
            {
                "code": "1440",
                "labels": {
                    "fr": "Prêts à long terme",
                    "de": "Langfristige Darlehen",
                    "it": "Prestiti a lungo termine",
                    "en": "Long-term loans",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "140",
                "imputable": True,
            },
            {
                "code": "1441",
                "labels": {
                    "fr": "Hypothèques",
                    "de": "Hypotheken",
                    "it": "Ipoteche",
                    "en": "Mortgages",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "140",
                "imputable": True,
            },
            # 148 - Participations
            {
                "code": "148",
                "labels": {
                    "fr": "Participations",
                    "de": "Beteiligungen",
                    "it": "Partecipazioni",
                    "en": "Participations",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "14",
            },
            {
                "code": "1480",
                "labels": {
                    "fr": "Participations",
                    "de": "Beteiligungen",
                    "it": "Partecipazioni",
                    "en": "Participations",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "148",
                "imputable": True,
            },
            {
                "code": "1489",
                "labels": {
                    "fr": "Ajustement participations",
                    "de": "Wertberichtigung Beteiligungen",
                    "it": "Rettifica partecipazioni",
                    "en": "Participations adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "148",
                "imputable": True,
            },
            # 150 - Immobilisations corporelles meubles
            {
                "code": "150",
                "labels": {
                    "fr": "Immobilisations corporelles meubles",
                    "de": "Mobile Sachanlagen",
                    "it": "Immobilizzazioni materiali mobili",
                    "en": "Movable tangible assets",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "14",
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
                "parent": "150",
                "imputable": True,
            },
            {
                "code": "1509",
                "labels": {
                    "fr": "Ajustement machines et appareils",
                    "de": "Wertberichtigung Maschinen und Apparate",
                    "it": "Rettifica macchine e apparecchi",
                    "en": "Machinery adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "150",
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
                "parent": "150",
                "imputable": True,
            },
            {
                "code": "1519",
                "labels": {
                    "fr": "Ajustement mobilier et installations",
                    "de": "Wertberichtigung Mobiliar und Einrichtungen",
                    "it": "Rettifica mobili e installazioni",
                    "en": "Furniture adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "150",
                "imputable": True,
            },
            {
                "code": "1520",
                "labels": {
                    "fr": "Machines de bureau et informatique",
                    "de": "Büromaschinen und EDV",
                    "it": "Macchine ufficio e informatica",
                    "en": "Office equipment and IT",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "150",
                "imputable": True,
            },
            {
                "code": "1529",
                "labels": {
                    "fr": "Ajustement machines de bureau",
                    "de": "Wertberichtigung Büromaschinen",
                    "it": "Rettifica macchine ufficio",
                    "en": "Office equipment adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "150",
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
                "parent": "150",
                "imputable": True,
            },
            {
                "code": "1539",
                "labels": {
                    "fr": "Ajustement véhicules",
                    "de": "Wertberichtigung Fahrzeuge",
                    "it": "Rettifica veicoli",
                    "en": "Vehicles adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "150",
                "imputable": True,
            },
            {
                "code": "1540",
                "labels": {
                    "fr": "Outillage et appareils",
                    "de": "Werkzeuge und Geräte",
                    "it": "Utensili e attrezzi",
                    "en": "Tools and equipment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "150",
                "imputable": True,
            },
            {
                "code": "1549",
                "labels": {
                    "fr": "Ajustement outillage",
                    "de": "Wertberichtigung Werkzeuge",
                    "it": "Rettifica utensili",
                    "en": "Tools adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "150",
                "imputable": True,
            },
            # 160 - Immobilisations corporelles immeubles
            {
                "code": "160",
                "labels": {
                    "fr": "Immobilisations corporelles immeubles",
                    "de": "Immobile Sachanlagen",
                    "it": "Immobilizzazioni materiali immobili",
                    "en": "Real estate",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "14",
            },
            {
                "code": "1600",
                "labels": {
                    "fr": "Immeubles d'exploitation",
                    "de": "Geschäftsliegenschaften",
                    "it": "Immobili d'esercizio",
                    "en": "Business properties",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "160",
                "imputable": True,
            },
            {
                "code": "1609",
                "labels": {
                    "fr": "Ajustement immeubles d'exploitation",
                    "de": "Wertberichtigung Geschäftsliegenschaften",
                    "it": "Rettifica immobili d'esercizio",
                    "en": "Business properties adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "160",
                "imputable": True,
            },
            # 170 - Immobilisations incorporelles
            {
                "code": "170",
                "labels": {
                    "fr": "Immobilisations incorporelles",
                    "de": "Immaterielle Anlagen",
                    "it": "Immobilizzazioni immateriali",
                    "en": "Intangible assets",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "14",
            },
            {
                "code": "1700",
                "labels": {
                    "fr": "Brevets, licences, droits",
                    "de": "Patente, Lizenzen, Rechte",
                    "it": "Brevetti, licenze, diritti",
                    "en": "Patents, licenses, rights",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "170",
                "imputable": True,
            },
            {
                "code": "1709",
                "labels": {
                    "fr": "Ajustement brevets et licences",
                    "de": "Wertberichtigung Patente und Lizenzen",
                    "it": "Rettifica brevetti e licenze",
                    "en": "Patents and licenses adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "170",
                "imputable": True,
            },
            {
                "code": "1770",
                "labels": {
                    "fr": "Goodwill",
                    "de": "Goodwill",
                    "it": "Avviamento",
                    "en": "Goodwill",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "170",
                "imputable": True,
            },
            {
                "code": "1779",
                "labels": {
                    "fr": "Ajustement goodwill",
                    "de": "Wertberichtigung Goodwill",
                    "it": "Rettifica avviamento",
                    "en": "Goodwill adjustment",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "170",
                "imputable": True,
            },
            # 180 - Capital non versé
            {
                "code": "180",
                "labels": {
                    "fr": "Capital non versé",
                    "de": "Nicht einbezahltes Kapital",
                    "it": "Capitale non versato",
                    "en": "Unpaid capital",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "14",
            },
            {
                "code": "1850",
                "labels": {
                    "fr": "Capital-actions non versé",
                    "de": "Nicht einbezahltes Aktienkapital",
                    "it": "Capitale azionario non versato",
                    "en": "Unpaid share capital",
                },
                "type": "ACTIF",
                "classe": 1,
                "parent": "180",
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
            # 200 - Dettes fournisseurs
            {
                "code": "200",
                "labels": {
                    "fr": "Dettes résultant d'achats et de prestations",
                    "de": "Verbindlichkeiten aus Lieferungen und Leistungen",
                    "it": "Debiti per forniture e prestazioni",
                    "en": "Trade payables",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "20",
            },
            {
                "code": "2000",
                "labels": {
                    "fr": "Dettes fournisseurs (Créanciers)",
                    "de": "Verbindlichkeiten aus Lieferungen und Leistungen (Kreditoren)",
                    "it": "Debiti verso fornitori (Creditori)",
                    "en": "Trade payables (Creditors)",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "200",
                "imputable": True,
                "lettrable": True,
            },
            {
                "code": "2030",
                "labels": {
                    "fr": "Acomptes de clients",
                    "de": "Kundenvorauszahlungen",
                    "it": "Anticipi da clienti",
                    "en": "Customer advances",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "200",
                "imputable": True,
            },
            {
                "code": "2050",
                "labels": {
                    "fr": "Dettes envers sociétés du groupe",
                    "de": "Verbindlichkeiten gegenüber Konzerngesellschaften",
                    "it": "Debiti verso società del gruppo",
                    "en": "Payables to group companies",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "200",
                "imputable": True,
            },
            # 210 - Dettes à court terme rémunérées
            {
                "code": "210",
                "labels": {
                    "fr": "Dettes à court terme rémunérées",
                    "de": "Kurzfristige verzinsliche Verbindlichkeiten",
                    "it": "Debiti a breve termine con interessi",
                    "en": "Short-term interest-bearing liabilities",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "20",
            },
            {
                "code": "2100",
                "labels": {
                    "fr": "Dettes bancaires à court terme",
                    "de": "Kurzfristige Bankverbindlichkeiten",
                    "it": "Debiti bancari a breve termine",
                    "en": "Short-term bank debt",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "210",
                "imputable": True,
            },
            {
                "code": "2120",
                "labels": {
                    "fr": "Engagements de leasing à court terme",
                    "de": "Kurzfristige Leasingverbindlichkeiten",
                    "it": "Impegni di leasing a breve termine",
                    "en": "Short-term lease liabilities",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "210",
                "imputable": True,
            },
            # 220 - Autres dettes à court terme
            {
                "code": "220",
                "labels": {
                    "fr": "Autres dettes à court terme",
                    "de": "Übrige kurzfristige Verbindlichkeiten",
                    "it": "Altri debiti a breve termine",
                    "en": "Other short-term liabilities",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "20",
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
                "parent": "220",
                "imputable": True,
                "soumis_tva": True,
                "code_tva_defaut": "200",
            },
            {
                "code": "2201",
                "labels": {
                    "fr": "Décompte TVA",
                    "de": "MWST-Abrechnung",
                    "it": "Conteggio IVA",
                    "en": "VAT settlement",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "220",
                "imputable": True,
                "soumis_tva": True,
            },
            {
                "code": "2206",
                "labels": {
                    "fr": "Impôt anticipé dû",
                    "de": "Geschuldete Verrechnungssteuer",
                    "it": "Imposta preventiva dovuta",
                    "en": "Withholding tax payable",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "220",
                "imputable": True,
            },
            {
                "code": "2208",
                "labels": {
                    "fr": "Impôts directs à payer",
                    "de": "Direkte Steuern",
                    "it": "Imposte dirette da pagare",
                    "en": "Direct taxes payable",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "220",
                "imputable": True,
            },
            {
                "code": "2261",
                "labels": {
                    "fr": "Dividendes",
                    "de": "Dividenden",
                    "it": "Dividendi",
                    "en": "Dividends payable",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "220",
                "imputable": True,
            },
            {
                "code": "2270",
                "labels": {
                    "fr": "Assurances sociales et prévoyance",
                    "de": "Sozialversicherungen und Vorsorge",
                    "it": "Assicurazioni sociali e previdenza",
                    "en": "Social insurance and pension",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "220",
                "imputable": True,
            },
            {
                "code": "2279",
                "labels": {
                    "fr": "Impôt à la source",
                    "de": "Quellensteuer",
                    "it": "Imposta alla fonte",
                    "en": "Withholding tax",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "220",
                "imputable": True,
            },
            # 230 - Passifs de régularisation
            {
                "code": "230",
                "labels": {
                    "fr": "Passifs de régularisation et provisions à court terme",
                    "de": "Passive Rechnungsabgrenzung und kurzfristige Rückstellungen",
                    "it": "Ratei e risconti passivi e accantonamenti a breve termine",
                    "en": "Accrued expenses and short-term provisions",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "20",
            },
            {
                "code": "2300",
                "labels": {
                    "fr": "Charges à payer",
                    "de": "Aufgelaufene Aufwendungen",
                    "it": "Ratei passivi",
                    "en": "Accrued expenses",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "230",
                "imputable": True,
            },
            {
                "code": "2301",
                "labels": {
                    "fr": "Produits encaissés d'avance",
                    "de": "Im Voraus erhaltene Erträge",
                    "it": "Risconti passivi",
                    "en": "Deferred income",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "230",
                "imputable": True,
            },
            {
                "code": "2330",
                "labels": {
                    "fr": "Provisions à court terme",
                    "de": "Kurzfristige Rückstellungen",
                    "it": "Accantonamenti a breve termine",
                    "en": "Short-term provisions",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "230",
                "imputable": True,
            },
            # 24 - Dettes à long terme
            {
                "code": "24",
                "labels": {
                    "fr": "Dettes à long terme",
                    "de": "Langfristiges Fremdkapital",
                    "it": "Debiti a lungo termine",
                    "en": "Long-term liabilities",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "2",
            },
            # 240 - Dettes à long terme rémunérées
            {
                "code": "240",
                "labels": {
                    "fr": "Dettes à long terme rémunérées",
                    "de": "Langfristige verzinsliche Verbindlichkeiten",
                    "it": "Debiti a lungo termine con interessi",
                    "en": "Long-term interest-bearing liabilities",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "24",
            },
            {
                "code": "2400",
                "labels": {
                    "fr": "Dettes bancaires à long terme",
                    "de": "Langfristige Bankverbindlichkeiten",
                    "it": "Debiti bancari a lungo termine",
                    "en": "Long-term bank debt",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "240",
                "imputable": True,
            },
            {
                "code": "2420",
                "labels": {
                    "fr": "Engagements de leasing à long terme",
                    "de": "Langfristige Leasingverbindlichkeiten",
                    "it": "Impegni di leasing a lungo termine",
                    "en": "Long-term lease liabilities",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "240",
                "imputable": True,
            },
            {
                "code": "2430",
                "labels": {
                    "fr": "Emprunts obligataires",
                    "de": "Obligationenanleihen",
                    "it": "Prestiti obbligazionari",
                    "en": "Bonds payable",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "240",
                "imputable": True,
            },
            {
                "code": "2450",
                "labels": {
                    "fr": "Emprunts",
                    "de": "Darlehen",
                    "it": "Mutui",
                    "en": "Loans payable",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "240",
                "imputable": True,
            },
            {
                "code": "2451",
                "labels": {
                    "fr": "Hypothèques",
                    "de": "Hypotheken",
                    "it": "Ipoteche",
                    "en": "Mortgages payable",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "240",
                "imputable": True,
            },
            # 260 - Provisions à long terme
            {
                "code": "260",
                "labels": {
                    "fr": "Provisions à long terme",
                    "de": "Langfristige Rückstellungen",
                    "it": "Accantonamenti a lungo termine",
                    "en": "Long-term provisions",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "24",
            },
            {
                "code": "2600",
                "labels": {
                    "fr": "Provisions",
                    "de": "Rückstellungen",
                    "it": "Accantonamenti",
                    "en": "Provisions",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "260",
                "imputable": True,
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
            # 280 - Capital
            {
                "code": "280",
                "labels": {
                    "fr": "Capital social",
                    "de": "Gesellschaftskapital",
                    "it": "Capitale sociale",
                    "en": "Share capital",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "28",
            },
            {
                "code": "2800",
                "labels": {
                    "fr": "Capital-actions / Capital social",
                    "de": "Aktienkapital / Gesellschaftskapital",
                    "it": "Capitale azionario / Capitale sociale",
                    "en": "Share capital",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "280",
                "imputable": True,
            },
            # 290 - Réserves et résultats
            {
                "code": "290",
                "labels": {
                    "fr": "Réserves et résultats",
                    "de": "Reserven und Ergebnisse",
                    "it": "Riserve e risultati",
                    "en": "Reserves and retained earnings",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "28",
            },
            {
                "code": "2900",
                "labels": {
                    "fr": "Réserves légales issues du capital",
                    "de": "Gesetzliche Kapitalreserven",
                    "it": "Riserve legali da capitale",
                    "en": "Legal capital reserves",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "290",
                "imputable": True,
            },
            {
                "code": "2950",
                "labels": {
                    "fr": "Réserves légales issues du bénéfice",
                    "de": "Gesetzliche Gewinnreserven",
                    "it": "Riserve legali da utili",
                    "en": "Legal profit reserves",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "290",
                "imputable": True,
            },
            {
                "code": "2960",
                "labels": {
                    "fr": "Réserves libres",
                    "de": "Freie Reserven",
                    "it": "Riserve libere",
                    "en": "Free reserves",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "290",
                "imputable": True,
            },
            {
                "code": "2970",
                "labels": {
                    "fr": "Bénéfice / perte reporté",
                    "de": "Gewinn-/Verlustvortrag",
                    "it": "Utile/perdita riportato",
                    "en": "Retained earnings",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "290",
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
                "parent": "290",
                "imputable": True,
            },
            {
                "code": "2980",
                "labels": {
                    "fr": "Propres actions",
                    "de": "Eigene Aktien",
                    "it": "Azioni proprie",
                    "en": "Treasury shares",
                },
                "type": "PASSIF",
                "classe": 2,
                "parent": "290",
                "imputable": True,
            },
            # ═══════════════════════════════════════════════════════════════
            # CLASSE 3 - PRODUITS D'EXPLOITATION
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "3",
                "labels": {
                    "fr": "Chiffre d'affaires résultant des ventes et prestations",
                    "de": "Betriebsertrag aus Lieferungen und Leistungen",
                    "it": "Ricavi da vendite e prestazioni",
                    "en": "Revenue from sales and services",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": None,
            },
            {
                "code": "3000",
                "labels": {
                    "fr": "Ventes de produits fabriqués",
                    "de": "Produktionserlöse",
                    "it": "Vendite di prodotti fabbricati",
                    "en": "Sales of manufactured products",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "3",
                "imputable": True,
                "soumis_tva": True,
                "code_tva_defaut": "200",
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
                "classe": 7,
                "parent": "3",
                "imputable": True,
                "soumis_tva": True,
                "code_tva_defaut": "200",
            },
            {
                "code": "3400",
                "labels": {
                    "fr": "Ventes de prestations de services",
                    "de": "Dienstleistungserlöse",
                    "it": "Vendite di prestazioni di servizi",
                    "en": "Sales of services",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "3",
                "imputable": True,
                "soumis_tva": True,
                "code_tva_defaut": "200",
            },
            {
                "code": "3600",
                "labels": {
                    "fr": "Autres ventes et prestations",
                    "de": "Übrige Erlöse aus Lieferungen und Leistungen",
                    "it": "Altre vendite e prestazioni",
                    "en": "Other sales and services",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "3",
                "imputable": True,
            },
            {
                "code": "3700",
                "labels": {
                    "fr": "Prestations propres",
                    "de": "Eigenleistungen",
                    "it": "Prestazioni proprie",
                    "en": "Own work capitalized",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "3",
                "imputable": True,
            },
            {
                "code": "3800",
                "labels": {
                    "fr": "Déductions sur ventes",
                    "de": "Erlösminderungen",
                    "it": "Deduzioni su vendite",
                    "en": "Sales deductions",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "3",
                "imputable": True,
            },
            {
                "code": "3805",
                "labels": {
                    "fr": "Pertes sur clients / Variation ducroire",
                    "de": "Debitorenverluste / Veränderung Delkredere",
                    "it": "Perdite su clienti / Variazione delcredere",
                    "en": "Bad debts / Allowance for doubtful accounts",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "3",
                "imputable": True,
            },
            {
                "code": "3900",
                "labels": {
                    "fr": "Variation des stocks de produits semi-finis",
                    "de": "Bestandsänderung unfertige Erzeugnisse",
                    "it": "Variazione scorte semilavorati",
                    "en": "Change in work in progress",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "3",
                "imputable": True,
            },
            {
                "code": "3901",
                "labels": {
                    "fr": "Variation des stocks de produits finis",
                    "de": "Bestandsänderung fertige Erzeugnisse",
                    "it": "Variazione scorte prodotti finiti",
                    "en": "Change in finished goods",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "3",
                "imputable": True,
            },
            # ═══════════════════════════════════════════════════════════════
            # CLASSE 4 - CHARGES DE MATÉRIEL
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "4",
                "labels": {
                    "fr": "Charges de matériel, marchandises et prestations de tiers",
                    "de": "Aufwand für Material, Handelswaren und Drittleistungen",
                    "it": "Costi per materiale, merci e prestazioni di terzi",
                    "en": "Cost of materials, goods and third-party services",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": None,
            },
            {
                "code": "4000",
                "labels": {
                    "fr": "Charges de matériel",
                    "de": "Materialaufwand",
                    "it": "Costi per materiale",
                    "en": "Material costs",
                },
                "type": "CHARGE",
                "classe": 6,
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
                "classe": 6,
                "parent": "4",
                "imputable": True,
            },
            {
                "code": "4400",
                "labels": {
                    "fr": "Prestations de tiers",
                    "de": "Aufwand für Drittleistungen",
                    "it": "Prestazioni di terzi",
                    "en": "Third-party services",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "4",
                "imputable": True,
            },
            {
                "code": "4500",
                "labels": {
                    "fr": "Charges d'énergie pour l'exploitation",
                    "de": "Energieaufwand zur Leistungserstellung",
                    "it": "Costi energetici per l'esercizio",
                    "en": "Energy costs for operations",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "4",
                "imputable": True,
            },
            {
                "code": "4900",
                "labels": {
                    "fr": "Déductions sur achats",
                    "de": "Bestandesänderungen und Material-Ertragsminderungen",
                    "it": "Deduzioni su acquisti",
                    "en": "Purchase deductions",
                },
                "type": "CHARGE",
                "classe": 6,
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
                "classe": 6,
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
                "classe": 6,
                "parent": "5",
                "imputable": True,
            },
            {
                "code": "5700",
                "labels": {
                    "fr": "Charges sociales AVS, AI, APG, AC",
                    "de": "Sozialversicherungsaufwand AHV, IV, EO, ALV",
                    "it": "Oneri sociali AVS, AI, IPG, AD",
                    "en": "Social security expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "5",
                "imputable": True,
            },
            {
                "code": "5710",
                "labels": {
                    "fr": "Charges sociales LPP",
                    "de": "Sozialversicherungsaufwand BVG",
                    "it": "Oneri sociali LPP",
                    "en": "Pension expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "5",
                "imputable": True,
            },
            {
                "code": "5720",
                "labels": {
                    "fr": "Charges LAA et LAAC",
                    "de": "Aufwand UVG und UVGZ",
                    "it": "Costi LAINF e LAINF complementare",
                    "en": "Accident insurance expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "5",
                "imputable": True,
            },
            {
                "code": "5730",
                "labels": {
                    "fr": "Charges allocations familiales",
                    "de": "Aufwand Familienzulagen",
                    "it": "Costi assegni familiari",
                    "en": "Family allowances expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "5",
                "imputable": True,
            },
            {
                "code": "5800",
                "labels": {
                    "fr": "Autres charges du personnel",
                    "de": "Übriger Personalaufwand",
                    "it": "Altri costi del personale",
                    "en": "Other personnel expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "5",
                "imputable": True,
            },
            {
                "code": "5900",
                "labels": {
                    "fr": "Personnel temporaire",
                    "de": "Temporärer Personal",
                    "it": "Personale temporaneo",
                    "en": "Temporary staff",
                },
                "type": "CHARGE",
                "classe": 6,
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
                "code": "6100",
                "labels": {
                    "fr": "Entretien et réparations",
                    "de": "Unterhalt und Reparaturen",
                    "it": "Manutenzione e riparazioni",
                    "en": "Maintenance and repairs",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6105",
                "labels": {
                    "fr": "Leasing immobilisations corporelles",
                    "de": "Leasing mobile Sachanlagen",
                    "it": "Leasing immobilizzazioni materiali",
                    "en": "Equipment leasing",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6200",
                "labels": {
                    "fr": "Charges de véhicules",
                    "de": "Fahrzeugaufwand",
                    "it": "Costi per veicoli",
                    "en": "Vehicle expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6260",
                "labels": {
                    "fr": "Leasing véhicules",
                    "de": "Fahrzeugleasing",
                    "it": "Leasing veicoli",
                    "en": "Vehicle leasing",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6300",
                "labels": {
                    "fr": "Assurances, taxes et autorisations",
                    "de": "Versicherungen, Abgaben, Bewilligungen",
                    "it": "Assicurazioni, tasse e autorizzazioni",
                    "en": "Insurance, fees and permits",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6400",
                "labels": {
                    "fr": "Charges d'énergie et d'évacuation",
                    "de": "Energie- und Entsorgungsaufwand",
                    "it": "Costi energetici e di smaltimento",
                    "en": "Energy and disposal costs",
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
                "code": "6503",
                "labels": {
                    "fr": "Honoraires fiduciaires et audit",
                    "de": "Treuhand- und Revisionskosten",
                    "it": "Onorari fiduciari e revisione",
                    "en": "Fiduciary and audit fees",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6510",
                "labels": {
                    "fr": "Téléphone et fax",
                    "de": "Telefon und Fax",
                    "it": "Telefono e fax",
                    "en": "Telephone and fax",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6570",
                "labels": {
                    "fr": "Charges informatiques",
                    "de": "Informatikaufwand",
                    "it": "Costi informatici",
                    "en": "IT expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6600",
                "labels": {
                    "fr": "Publicité",
                    "de": "Werbeaufwand",
                    "it": "Pubblicità",
                    "en": "Advertising",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6700",
                "labels": {
                    "fr": "Autres charges d'exploitation",
                    "de": "Sonstiger Betriebsaufwand",
                    "it": "Altri costi d'esercizio",
                    "en": "Other operating expenses",
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
            {
                "code": "6940",
                "labels": {
                    "fr": "Frais bancaires",
                    "de": "Bankspesen",
                    "it": "Spese bancarie",
                    "en": "Bank charges",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "6",
                "imputable": True,
            },
            {
                "code": "6950",
                "labels": {
                    "fr": "Produits financiers",
                    "de": "Finanzertrag",
                    "it": "Proventi finanziari",
                    "en": "Financial income",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "6",
                "imputable": True,
            },
            # ═══════════════════════════════════════════════════════════════
            # CLASSE 7 - RÉSULTATS DES ACTIVITÉS ANNEXES
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "7",
                "labels": {
                    "fr": "Résultats des activités annexes",
                    "de": "Betrieblicher Nebenerfolg",
                    "it": "Risultato attività accessorie",
                    "en": "Results from ancillary activities",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": None,
            },
            {
                "code": "7000",
                "labels": {
                    "fr": "Produits accessoires",
                    "de": "Nebenertrag",
                    "it": "Proventi accessori",
                    "en": "Ancillary income",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "7",
                "imputable": True,
            },
            {
                "code": "7010",
                "labels": {
                    "fr": "Charges accessoires",
                    "de": "Nebenaufwand",
                    "it": "Costi accessori",
                    "en": "Ancillary expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "7",
                "imputable": True,
            },
            {
                "code": "7500",
                "labels": {
                    "fr": "Produits des immeubles",
                    "de": "Liegenschaftenertrag",
                    "it": "Proventi da immobili",
                    "en": "Real estate income",
                },
                "type": "PRODUIT",
                "classe": 7,
                "parent": "7",
                "imputable": True,
            },
            {
                "code": "7510",
                "labels": {
                    "fr": "Charges des immeubles",
                    "de": "Liegenschaftenaufwand",
                    "it": "Costi da immobili",
                    "en": "Real estate expenses",
                },
                "type": "CHARGE",
                "classe": 6,
                "parent": "7",
                "imputable": True,
            },
            # ═══════════════════════════════════════════════════════════════
            # CLASSE 8 - RÉSULTATS EXTRAORDINAIRES
            # ═══════════════════════════════════════════════════════════════
            {
                "code": "8",
                "labels": {
                    "fr": "Résultats extraordinaires et hors exploitation",
                    "de": "Ausserordentlicher und betriebsfremder Erfolg",
                    "it": "Risultato straordinario e non operativo",
                    "en": "Extraordinary and non-operating results",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": None,
            },
            {
                "code": "8000",
                "labels": {
                    "fr": "Charges hors exploitation",
                    "de": "Betriebsfremder Aufwand",
                    "it": "Costi non operativi",
                    "en": "Non-operating expenses",
                },
                "type": "CHARGE",
                "classe": 8,
                "parent": "8",
                "imputable": True,
            },
            {
                "code": "8100",
                "labels": {
                    "fr": "Produits hors exploitation",
                    "de": "Betriebsfremder Ertrag",
                    "it": "Proventi non operativi",
                    "en": "Non-operating income",
                },
                "type": "PRODUIT",
                "classe": 8,
                "parent": "8",
                "imputable": True,
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
                    "fr": "Impôts directs",
                    "de": "Direkte Steuern",
                    "it": "Imposte dirette",
                    "en": "Direct taxes",
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
                    "fr": "Bénéfice / perte de l'exercice",
                    "de": "Jahresgewinn / Jahresverlust",
                    "it": "Utile / perdita dell'esercizio",
                    "en": "Net income / Net loss",
                },
                "type": "CHARGE",
                "classe": 9,
                "parent": "9",
                "imputable": True,
            },
        ]

    def _create_accounts(self, plan, accounts_data, force_update=False):
        """Crée les comptes avec hiérarchie et traductions"""

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

            # Préparer les données
            defaults = {
                "libelle_fr": labels.get("fr", ""),
                "libelle_de": labels.get("de", ""),
                "libelle_it": labels.get("it", ""),
                "libelle_en": labels.get("en", ""),
                "libelle_court_fr": labels.get("fr", "")[:100],
                "libelle_court_de": labels.get("de", "")[:100],
                "libelle_court_it": labels.get("it", "")[:100],
                "libelle_court_en": labels.get("en", "")[:100],
                "type_compte": account_data.get("type", "ACTIF"),
                "classe": account_data.get("classe", 1),
                "niveau": len(code),
                "compte_parent": parent_account,
                "est_collectif": len(code) <= 2,
                "imputable": account_data.get("imputable", len(code) >= 4),
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
                self.stdout.write(f"  ✓ {code} - {labels['fr']}")
            elif force_update:
                updated_count += 1
                self.stdout.write(f"  ↻ {code} - {labels['fr']}")

        return created_count, updated_count
