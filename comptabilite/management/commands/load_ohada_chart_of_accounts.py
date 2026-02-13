# comptabilite/management/commands/load_ohada_chart_of_accounts.py
"""
Commande pour charger le plan comptable SYSCOHADA révisé.

Usage:
    python manage.py load_ohada_chart_of_accounts
    python manage.py load_ohada_chart_of_accounts --mandat-id <uuid>
    python manage.py load_ohada_chart_of_accounts --force
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from comptabilite.models import TypePlanComptable, ClasseComptable, PlanComptable, Compte


class Command(BaseCommand):
    help = "Charge le plan comptable OHADA (SYSCOHADA révisé 2017)"

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

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("📊 Chargement du plan comptable OHADA (SYSCOHADA révisé)...")
        )

        with transaction.atomic():
            type_plan = self._get_or_create_type_plan()
            plan = self._get_or_create_plan(options, type_plan)
            accounts_data = self._get_ohada_accounts()
            created_count, updated_count = self._create_accounts(
                plan, type_plan, accounts_data, options["force"]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Plan "{plan.nom}" : {created_count} comptes créés, {updated_count} mis à jour'
                )
            )
            return str(plan.id)

    def _get_or_create_type_plan(self):
        """Récupère ou crée le type de plan comptable OHADA."""
        try:
            return TypePlanComptable.objects.get(code="OHADA")
        except TypePlanComptable.DoesNotExist:
            self.stdout.write(
                self.style.WARNING("  ⚠ Type de plan OHADA non trouvé, création...")
            )

            type_plan = TypePlanComptable.objects.create(
                code="OHADA",
                nom="Plan Comptable OHADA",
                description="Système comptable OHADA pour les pays de la zone OHADA",
                pays="Zone OHADA",
                region="Afrique",
                norme_comptable="SYSCOHADA révisé",
                version="2017",
                ordre=2,
            )

            classes = [
                {'numero': 1, 'libelle': 'Comptes de ressources durables', 'type_compte': 'PASSIF', 'numero_debut': '1000', 'numero_fin': '1999'},
                {'numero': 2, 'libelle': "Comptes d'actif immobilisé", 'type_compte': 'ACTIF', 'numero_debut': '2000', 'numero_fin': '2999'},
                {'numero': 3, 'libelle': 'Comptes de stocks', 'type_compte': 'ACTIF', 'numero_debut': '3000', 'numero_fin': '3999'},
                {'numero': 4, 'libelle': 'Comptes de tiers', 'type_compte': 'ACTIF', 'numero_debut': '4000', 'numero_fin': '4999'},
                {'numero': 5, 'libelle': 'Comptes de trésorerie', 'type_compte': 'ACTIF', 'numero_debut': '5000', 'numero_fin': '5999'},
                {'numero': 6, 'libelle': 'Comptes de charges des activités ordinaires', 'type_compte': 'CHARGE', 'numero_debut': '6000', 'numero_fin': '6999'},
                {'numero': 7, 'libelle': 'Comptes de produits des activités ordinaires', 'type_compte': 'PRODUIT', 'numero_debut': '7000', 'numero_fin': '7999'},
                {'numero': 8, 'libelle': 'Comptes des autres charges et produits', 'type_compte': 'RESULTAT', 'numero_debut': '8000', 'numero_fin': '8999'},
            ]

            for c in classes:
                ClasseComptable.objects.create(
                    type_plan=type_plan,
                    numero=c['numero'],
                    libelle=c['libelle'],
                    type_compte=c['type_compte'],
                    numero_debut=c.get('numero_debut', ''),
                    numero_fin=c.get('numero_fin', ''),
                )

            self.stdout.write(self.style.SUCCESS("  ✓ Type de plan OHADA créé"))
            return type_plan

    def _get_or_create_plan(self, options, type_plan):
        """Crée ou récupère le plan comptable OHADA."""
        from core.models import Mandat

        mandat = None
        if options["mandat_id"]:
            mandat = Mandat.objects.get(pk=options["mandat_id"])

        defaults = {
            "nom_fr": "Plan Comptable OHADA",
            "nom_de": "OHADA-Kontenrahmen",
            "nom_it": "Piano Contabile OHADA",
            "nom_en": "OHADA Chart of Accounts",
            "description_fr": "Plan comptable SYSCOHADA révisé 2017",
            "description_de": "SYSCOHADA revidierter Kontenrahmen 2017",
            "description_it": "Piano contabile SYSCOHADA revisionato 2017",
            "description_en": "Revised SYSCOHADA chart of accounts 2017",
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
                for key, value in defaults.items():
                    if key != 'type_plan':
                        setattr(plan, key, value)
                plan.save()
                self.stdout.write("  → Traductions mises à jour")

        return plan

    def _create_accounts(self, plan, type_plan, accounts_data, force_update=False):
        """Crée les comptes avec hiérarchie et traductions."""
        classes_map = {
            c.numero: c for c in ClasseComptable.objects.filter(type_plan=type_plan)
        }

        code_to_account = {}
        created_count = 0
        updated_count = 0

        sorted_accounts = sorted(accounts_data, key=lambda x: len(x["code"]))

        for account_data in sorted_accounts:
            code = account_data["code"]
            labels = account_data["labels"]
            parent_code = account_data.get("parent")

            parent_account = code_to_account.get(parent_code) if parent_code else None

            classe_num = account_data.get("classe", int(code[0]) if code else 1)
            classe_comptable = classes_map.get(classe_num)

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

    def _get_ohada_accounts(self):
        """Retourne les données du plan comptable OHADA (SYSCOHADA révisé)."""
        return [
            # ═══════════════════════════════════════════════════════════════
            # CLASSE 1 - COMPTES DE RESSOURCES DURABLES
            # ═══════════════════════════════════════════════════════════════
            {"code": "1", "labels": {"fr": "Comptes de ressources durables", "en": "Long-term resources accounts"}, "type": "PASSIF", "classe": 1, "parent": None},
            {"code": "10", "labels": {"fr": "Capital", "en": "Capital"}, "type": "PASSIF", "classe": 1, "parent": "1"},
            {"code": "101", "labels": {"fr": "Capital social", "en": "Share capital"}, "type": "PASSIF", "classe": 1, "parent": "10", "imputable": True},
            {"code": "109", "labels": {"fr": "Actionnaires, capital souscrit non appelé", "en": "Shareholders, subscribed uncalled capital"}, "type": "PASSIF", "classe": 1, "parent": "10", "imputable": True},
            {"code": "11", "labels": {"fr": "Réserves", "en": "Reserves"}, "type": "PASSIF", "classe": 1, "parent": "1"},
            {"code": "111", "labels": {"fr": "Réserve légale", "en": "Legal reserve"}, "type": "PASSIF", "classe": 1, "parent": "11", "imputable": True},
            {"code": "112", "labels": {"fr": "Réserves statutaires ou contractuelles", "en": "Statutory or contractual reserves"}, "type": "PASSIF", "classe": 1, "parent": "11", "imputable": True},
            {"code": "118", "labels": {"fr": "Autres réserves", "en": "Other reserves"}, "type": "PASSIF", "classe": 1, "parent": "11", "imputable": True},
            {"code": "12", "labels": {"fr": "Report à nouveau", "en": "Retained earnings"}, "type": "PASSIF", "classe": 1, "parent": "1"},
            {"code": "121", "labels": {"fr": "Report à nouveau créditeur", "en": "Retained earnings (credit)"}, "type": "PASSIF", "classe": 1, "parent": "12", "imputable": True},
            {"code": "129", "labels": {"fr": "Report à nouveau débiteur", "en": "Retained earnings (debit)"}, "type": "PASSIF", "classe": 1, "parent": "12", "imputable": True},
            {"code": "13", "labels": {"fr": "Résultat net de l'exercice", "en": "Net result"}, "type": "PASSIF", "classe": 1, "parent": "1"},
            {"code": "131", "labels": {"fr": "Résultat net: bénéfice", "en": "Net result: profit"}, "type": "PASSIF", "classe": 1, "parent": "13", "imputable": True},
            {"code": "139", "labels": {"fr": "Résultat net: perte", "en": "Net result: loss"}, "type": "PASSIF", "classe": 1, "parent": "13", "imputable": True},
            {"code": "14", "labels": {"fr": "Subventions d'investissement", "en": "Investment subsidies"}, "type": "PASSIF", "classe": 1, "parent": "1"},
            {"code": "141", "labels": {"fr": "Subventions d'équipement", "en": "Equipment subsidies"}, "type": "PASSIF", "classe": 1, "parent": "14", "imputable": True},
            {"code": "15", "labels": {"fr": "Provisions réglementées et fonds assimilés", "en": "Regulated provisions and similar funds"}, "type": "PASSIF", "classe": 1, "parent": "1"},
            {"code": "151", "labels": {"fr": "Amortissements dérogatoires", "en": "Accelerated depreciation"}, "type": "PASSIF", "classe": 1, "parent": "15", "imputable": True},
            {"code": "16", "labels": {"fr": "Emprunts et dettes assimilées", "en": "Borrowings and similar debts"}, "type": "PASSIF", "classe": 1, "parent": "1"},
            {"code": "161", "labels": {"fr": "Emprunts obligataires", "en": "Bond loans"}, "type": "PASSIF", "classe": 1, "parent": "16", "imputable": True},
            {"code": "162", "labels": {"fr": "Emprunts et dettes auprès des établissements de crédit", "en": "Loans from credit institutions"}, "type": "PASSIF", "classe": 1, "parent": "16", "imputable": True},
            {"code": "17", "labels": {"fr": "Dettes de crédit-bail et contrats assimilés", "en": "Lease liabilities and similar contracts"}, "type": "PASSIF", "classe": 1, "parent": "1"},
            {"code": "172", "labels": {"fr": "Emprunts équivalents de crédit-bail immobilier", "en": "Real estate lease equivalent loans"}, "type": "PASSIF", "classe": 1, "parent": "17", "imputable": True},
            {"code": "19", "labels": {"fr": "Provisions financières pour risques et charges", "en": "Financial provisions for risks and charges"}, "type": "PASSIF", "classe": 1, "parent": "1"},
            {"code": "191", "labels": {"fr": "Provisions pour litiges", "en": "Provisions for litigation"}, "type": "PASSIF", "classe": 1, "parent": "19", "imputable": True},
            {"code": "195", "labels": {"fr": "Provisions pour impôts", "en": "Provisions for taxes"}, "type": "PASSIF", "classe": 1, "parent": "19", "imputable": True},

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 2 - COMPTES D'ACTIF IMMOBILISÉ
            # ═══════════════════════════════════════════════════════════════
            {"code": "2", "labels": {"fr": "Comptes d'actif immobilisé", "en": "Fixed assets accounts"}, "type": "ACTIF", "classe": 2, "parent": None},
            {"code": "21", "labels": {"fr": "Immobilisations incorporelles", "en": "Intangible assets"}, "type": "ACTIF", "classe": 2, "parent": "2"},
            {"code": "211", "labels": {"fr": "Frais de développement", "en": "Development costs"}, "type": "ACTIF", "classe": 2, "parent": "21", "imputable": True},
            {"code": "212", "labels": {"fr": "Brevets, licences, concessions", "en": "Patents, licenses, concessions"}, "type": "ACTIF", "classe": 2, "parent": "21", "imputable": True},
            {"code": "213", "labels": {"fr": "Logiciels et sites internet", "en": "Software and websites"}, "type": "ACTIF", "classe": 2, "parent": "21", "imputable": True},
            {"code": "215", "labels": {"fr": "Fonds commercial", "en": "Goodwill"}, "type": "ACTIF", "classe": 2, "parent": "21", "imputable": True},
            {"code": "22", "labels": {"fr": "Terrains", "en": "Land"}, "type": "ACTIF", "classe": 2, "parent": "2"},
            {"code": "221", "labels": {"fr": "Terrains agricoles et forestiers", "en": "Agricultural and forest land"}, "type": "ACTIF", "classe": 2, "parent": "22", "imputable": True},
            {"code": "222", "labels": {"fr": "Terrains nus", "en": "Unimproved land"}, "type": "ACTIF", "classe": 2, "parent": "22", "imputable": True},
            {"code": "223", "labels": {"fr": "Terrains bâtis", "en": "Developed land"}, "type": "ACTIF", "classe": 2, "parent": "22", "imputable": True},
            {"code": "23", "labels": {"fr": "Bâtiments, installations techniques et agencements", "en": "Buildings, technical installations and fixtures"}, "type": "ACTIF", "classe": 2, "parent": "2"},
            {"code": "231", "labels": {"fr": "Bâtiments industriels", "en": "Industrial buildings"}, "type": "ACTIF", "classe": 2, "parent": "23", "imputable": True},
            {"code": "232", "labels": {"fr": "Bâtiments commerciaux", "en": "Commercial buildings"}, "type": "ACTIF", "classe": 2, "parent": "23", "imputable": True},
            {"code": "233", "labels": {"fr": "Bâtiments administratifs", "en": "Administrative buildings"}, "type": "ACTIF", "classe": 2, "parent": "23", "imputable": True},
            {"code": "24", "labels": {"fr": "Matériel", "en": "Equipment"}, "type": "ACTIF", "classe": 2, "parent": "2"},
            {"code": "241", "labels": {"fr": "Matériel et outillage industriel et commercial", "en": "Industrial and commercial equipment and tools"}, "type": "ACTIF", "classe": 2, "parent": "24", "imputable": True},
            {"code": "244", "labels": {"fr": "Matériel et mobilier de bureau", "en": "Office equipment and furniture"}, "type": "ACTIF", "classe": 2, "parent": "24", "imputable": True},
            {"code": "245", "labels": {"fr": "Matériel de transport", "en": "Transport equipment"}, "type": "ACTIF", "classe": 2, "parent": "24", "imputable": True},
            {"code": "25", "labels": {"fr": "Avances et acomptes versés sur immobilisations", "en": "Advances on fixed assets"}, "type": "ACTIF", "classe": 2, "parent": "2"},
            {"code": "251", "labels": {"fr": "Avances versées sur immobilisations incorporelles", "en": "Advances on intangible assets"}, "type": "ACTIF", "classe": 2, "parent": "25", "imputable": True},
            {"code": "26", "labels": {"fr": "Titres de participation", "en": "Equity investments"}, "type": "ACTIF", "classe": 2, "parent": "2"},
            {"code": "261", "labels": {"fr": "Titres de participation dans des sociétés sous contrôle exclusif", "en": "Shares in exclusively controlled companies"}, "type": "ACTIF", "classe": 2, "parent": "26", "imputable": True},
            {"code": "28", "labels": {"fr": "Amortissements", "en": "Accumulated depreciation"}, "type": "ACTIF", "classe": 2, "parent": "2"},
            {"code": "281", "labels": {"fr": "Amortissements des immobilisations incorporelles", "en": "Depreciation of intangible assets"}, "type": "ACTIF", "classe": 2, "parent": "28", "imputable": True},
            {"code": "283", "labels": {"fr": "Amortissements des bâtiments", "en": "Depreciation of buildings"}, "type": "ACTIF", "classe": 2, "parent": "28", "imputable": True},
            {"code": "284", "labels": {"fr": "Amortissements du matériel", "en": "Depreciation of equipment"}, "type": "ACTIF", "classe": 2, "parent": "28", "imputable": True},
            {"code": "29", "labels": {"fr": "Dépréciations des immobilisations", "en": "Impairment of fixed assets"}, "type": "ACTIF", "classe": 2, "parent": "2"},
            {"code": "291", "labels": {"fr": "Dépréciations des immobilisations incorporelles", "en": "Impairment of intangible assets"}, "type": "ACTIF", "classe": 2, "parent": "29", "imputable": True},

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 3 - COMPTES DE STOCKS
            # ═══════════════════════════════════════════════════════════════
            {"code": "3", "labels": {"fr": "Comptes de stocks", "en": "Inventory accounts"}, "type": "ACTIF", "classe": 3, "parent": None},
            {"code": "31", "labels": {"fr": "Marchandises", "en": "Goods"}, "type": "ACTIF", "classe": 3, "parent": "3"},
            {"code": "311", "labels": {"fr": "Marchandises A", "en": "Goods A"}, "type": "ACTIF", "classe": 3, "parent": "31", "imputable": True},
            {"code": "32", "labels": {"fr": "Matières premières et fournitures liées", "en": "Raw materials and related supplies"}, "type": "ACTIF", "classe": 3, "parent": "3"},
            {"code": "321", "labels": {"fr": "Matières premières", "en": "Raw materials"}, "type": "ACTIF", "classe": 3, "parent": "32", "imputable": True},
            {"code": "322", "labels": {"fr": "Fournitures liées", "en": "Related supplies"}, "type": "ACTIF", "classe": 3, "parent": "32", "imputable": True},
            {"code": "33", "labels": {"fr": "Autres approvisionnements", "en": "Other supplies"}, "type": "ACTIF", "classe": 3, "parent": "3"},
            {"code": "331", "labels": {"fr": "Matières consommables", "en": "Consumable materials"}, "type": "ACTIF", "classe": 3, "parent": "33", "imputable": True},
            {"code": "34", "labels": {"fr": "Produits en cours", "en": "Work in progress"}, "type": "ACTIF", "classe": 3, "parent": "3"},
            {"code": "341", "labels": {"fr": "Produits en cours", "en": "Work in progress"}, "type": "ACTIF", "classe": 3, "parent": "34", "imputable": True},
            {"code": "35", "labels": {"fr": "Services en cours", "en": "Services in progress"}, "type": "ACTIF", "classe": 3, "parent": "3"},
            {"code": "351", "labels": {"fr": "Travaux en cours", "en": "Works in progress"}, "type": "ACTIF", "classe": 3, "parent": "35", "imputable": True},
            {"code": "36", "labels": {"fr": "Produits finis", "en": "Finished goods"}, "type": "ACTIF", "classe": 3, "parent": "3"},
            {"code": "361", "labels": {"fr": "Produits finis", "en": "Finished goods"}, "type": "ACTIF", "classe": 3, "parent": "36", "imputable": True},
            {"code": "39", "labels": {"fr": "Dépréciations des stocks", "en": "Inventory impairment"}, "type": "ACTIF", "classe": 3, "parent": "3"},
            {"code": "391", "labels": {"fr": "Dépréciations des stocks de marchandises", "en": "Impairment of goods inventory"}, "type": "ACTIF", "classe": 3, "parent": "39", "imputable": True},

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 4 - COMPTES DE TIERS
            # ═══════════════════════════════════════════════════════════════
            {"code": "4", "labels": {"fr": "Comptes de tiers", "en": "Third-party accounts"}, "type": "ACTIF", "classe": 4, "parent": None},
            {"code": "40", "labels": {"fr": "Fournisseurs et comptes rattachés", "en": "Suppliers and related accounts"}, "type": "PASSIF", "classe": 4, "parent": "4"},
            {"code": "401", "labels": {"fr": "Fournisseurs, dettes en compte", "en": "Suppliers, account payables"}, "type": "PASSIF", "classe": 4, "parent": "40", "imputable": True, "lettrable": True},
            {"code": "402", "labels": {"fr": "Fournisseurs, effets à payer", "en": "Suppliers, notes payable"}, "type": "PASSIF", "classe": 4, "parent": "40", "imputable": True, "lettrable": True},
            {"code": "408", "labels": {"fr": "Fournisseurs, factures non parvenues", "en": "Suppliers, uninvoiced receipts"}, "type": "PASSIF", "classe": 4, "parent": "40", "imputable": True},
            {"code": "41", "labels": {"fr": "Clients et comptes rattachés", "en": "Customers and related accounts"}, "type": "ACTIF", "classe": 4, "parent": "4"},
            {"code": "411", "labels": {"fr": "Clients", "en": "Customers"}, "type": "ACTIF", "classe": 4, "parent": "41", "imputable": True, "lettrable": True},
            {"code": "412", "labels": {"fr": "Clients, effets à recevoir en portefeuille", "en": "Customers, notes receivable"}, "type": "ACTIF", "classe": 4, "parent": "41", "imputable": True, "lettrable": True},
            {"code": "416", "labels": {"fr": "Créances clients litigieuses ou douteuses", "en": "Disputed or doubtful customer receivables"}, "type": "ACTIF", "classe": 4, "parent": "41", "imputable": True},
            {"code": "42", "labels": {"fr": "Personnel", "en": "Personnel"}, "type": "PASSIF", "classe": 4, "parent": "4"},
            {"code": "421", "labels": {"fr": "Personnel, rémunérations dues", "en": "Personnel, wages payable"}, "type": "PASSIF", "classe": 4, "parent": "42", "imputable": True},
            {"code": "422", "labels": {"fr": "Personnel, avances et acomptes", "en": "Personnel, advances"}, "type": "ACTIF", "classe": 4, "parent": "42", "imputable": True},
            {"code": "43", "labels": {"fr": "Organismes sociaux", "en": "Social security bodies"}, "type": "PASSIF", "classe": 4, "parent": "4"},
            {"code": "431", "labels": {"fr": "Sécurité sociale", "en": "Social security"}, "type": "PASSIF", "classe": 4, "parent": "43", "imputable": True},
            {"code": "44", "labels": {"fr": "État et collectivités publiques", "en": "Government and public entities"}, "type": "PASSIF", "classe": 4, "parent": "4"},
            {"code": "441", "labels": {"fr": "État, impôt sur les bénéfices", "en": "State, corporate income tax"}, "type": "PASSIF", "classe": 4, "parent": "44", "imputable": True},
            {"code": "443", "labels": {"fr": "État, TVA facturée", "en": "State, invoiced VAT"}, "type": "PASSIF", "classe": 4, "parent": "44", "imputable": True, "soumis_tva": True},
            {"code": "445", "labels": {"fr": "État, TVA récupérable", "en": "State, recoverable VAT"}, "type": "ACTIF", "classe": 4, "parent": "44", "imputable": True, "soumis_tva": True},
            {"code": "447", "labels": {"fr": "État, impôts retenus à la source", "en": "State, withholding taxes"}, "type": "PASSIF", "classe": 4, "parent": "44", "imputable": True},
            {"code": "449", "labels": {"fr": "État, créances et dettes fiscales diverses", "en": "State, misc tax receivables and payables"}, "type": "PASSIF", "classe": 4, "parent": "44", "imputable": True},
            {"code": "46", "labels": {"fr": "Associés et groupe", "en": "Partners and group"}, "type": "ACTIF", "classe": 4, "parent": "4"},
            {"code": "461", "labels": {"fr": "Associés, opérations sur le capital", "en": "Partners, capital transactions"}, "type": "ACTIF", "classe": 4, "parent": "46", "imputable": True},
            {"code": "462", "labels": {"fr": "Associés, comptes courants", "en": "Partners, current accounts"}, "type": "PASSIF", "classe": 4, "parent": "46", "imputable": True},
            {"code": "47", "labels": {"fr": "Débiteurs et créditeurs divers", "en": "Miscellaneous debtors and creditors"}, "type": "ACTIF", "classe": 4, "parent": "4"},
            {"code": "471", "labels": {"fr": "Débiteurs divers", "en": "Miscellaneous debtors"}, "type": "ACTIF", "classe": 4, "parent": "47", "imputable": True},
            {"code": "472", "labels": {"fr": "Créditeurs divers", "en": "Miscellaneous creditors"}, "type": "PASSIF", "classe": 4, "parent": "47", "imputable": True},
            {"code": "48", "labels": {"fr": "Comptes de régularisation et assimilés", "en": "Accruals and deferrals"}, "type": "ACTIF", "classe": 4, "parent": "4"},
            {"code": "481", "labels": {"fr": "Charges à répartir sur plusieurs exercices", "en": "Deferred charges"}, "type": "ACTIF", "classe": 4, "parent": "48", "imputable": True},
            {"code": "49", "labels": {"fr": "Dépréciations et provisions pour risques à court terme", "en": "Short-term impairment and provisions"}, "type": "ACTIF", "classe": 4, "parent": "4"},
            {"code": "491", "labels": {"fr": "Dépréciations des comptes clients", "en": "Impairment of customer accounts"}, "type": "ACTIF", "classe": 4, "parent": "49", "imputable": True},

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 5 - COMPTES DE TRÉSORERIE
            # ═══════════════════════════════════════════════════════════════
            {"code": "5", "labels": {"fr": "Comptes de trésorerie", "en": "Cash accounts"}, "type": "ACTIF", "classe": 5, "parent": None},
            {"code": "51", "labels": {"fr": "Valeurs à encaisser", "en": "Values to collect"}, "type": "ACTIF", "classe": 5, "parent": "5"},
            {"code": "511", "labels": {"fr": "Effets à encaisser", "en": "Notes receivable"}, "type": "ACTIF", "classe": 5, "parent": "51", "imputable": True},
            {"code": "52", "labels": {"fr": "Banques", "en": "Banks"}, "type": "ACTIF", "classe": 5, "parent": "5"},
            {"code": "521", "labels": {"fr": "Banques locales", "en": "Local banks"}, "type": "ACTIF", "classe": 5, "parent": "52", "imputable": True},
            {"code": "522", "labels": {"fr": "Banques autres États OHADA", "en": "Banks in other OHADA states"}, "type": "ACTIF", "classe": 5, "parent": "52", "imputable": True},
            {"code": "523", "labels": {"fr": "Banques hors OHADA", "en": "Banks outside OHADA zone"}, "type": "ACTIF", "classe": 5, "parent": "52", "imputable": True},
            {"code": "53", "labels": {"fr": "Établissements financiers et assimilés", "en": "Financial institutions"}, "type": "ACTIF", "classe": 5, "parent": "5"},
            {"code": "531", "labels": {"fr": "Chèques postaux", "en": "Postal checks"}, "type": "ACTIF", "classe": 5, "parent": "53", "imputable": True},
            {"code": "56", "labels": {"fr": "Banques, crédits de trésorerie", "en": "Bank, short-term loans"}, "type": "PASSIF", "classe": 5, "parent": "5"},
            {"code": "561", "labels": {"fr": "Crédits de trésorerie", "en": "Short-term bank loans"}, "type": "PASSIF", "classe": 5, "parent": "56", "imputable": True},
            {"code": "57", "labels": {"fr": "Caisse", "en": "Cash on hand"}, "type": "ACTIF", "classe": 5, "parent": "5"},
            {"code": "571", "labels": {"fr": "Caisse siège social", "en": "Head office cash"}, "type": "ACTIF", "classe": 5, "parent": "57", "imputable": True},
            {"code": "572", "labels": {"fr": "Caisse succursale", "en": "Branch cash"}, "type": "ACTIF", "classe": 5, "parent": "57", "imputable": True},
            {"code": "58", "labels": {"fr": "Régies d'avances, accréditifs et virements internes", "en": "Petty cash, letters of credit and internal transfers"}, "type": "ACTIF", "classe": 5, "parent": "5"},
            {"code": "581", "labels": {"fr": "Virements de fonds", "en": "Fund transfers"}, "type": "ACTIF", "classe": 5, "parent": "58", "imputable": True},
            {"code": "59", "labels": {"fr": "Dépréciations des titres de placement", "en": "Impairment of investment securities"}, "type": "ACTIF", "classe": 5, "parent": "5"},
            {"code": "591", "labels": {"fr": "Dépréciations des titres de placement", "en": "Impairment of investment securities"}, "type": "ACTIF", "classe": 5, "parent": "59", "imputable": True},

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 6 - COMPTES DE CHARGES DES ACTIVITÉS ORDINAIRES
            # ═══════════════════════════════════════════════════════════════
            {"code": "6", "labels": {"fr": "Comptes de charges des activités ordinaires", "en": "Operating expense accounts"}, "type": "CHARGE", "classe": 6, "parent": None},
            {"code": "60", "labels": {"fr": "Achats et variations de stocks", "en": "Purchases and inventory changes"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "601", "labels": {"fr": "Achats de marchandises", "en": "Purchase of goods"}, "type": "CHARGE", "classe": 6, "parent": "60", "imputable": True},
            {"code": "602", "labels": {"fr": "Achats de matières premières", "en": "Purchase of raw materials"}, "type": "CHARGE", "classe": 6, "parent": "60", "imputable": True},
            {"code": "604", "labels": {"fr": "Achats stockés de matières et fournitures consommables", "en": "Stocked consumable supplies"}, "type": "CHARGE", "classe": 6, "parent": "60", "imputable": True},
            {"code": "605", "labels": {"fr": "Autres achats", "en": "Other purchases"}, "type": "CHARGE", "classe": 6, "parent": "60", "imputable": True},
            {"code": "608", "labels": {"fr": "Achats d'emballages", "en": "Purchase of packaging"}, "type": "CHARGE", "classe": 6, "parent": "60", "imputable": True},
            {"code": "61", "labels": {"fr": "Transports", "en": "Transport"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "611", "labels": {"fr": "Transports sur achats", "en": "Transport on purchases"}, "type": "CHARGE", "classe": 6, "parent": "61", "imputable": True},
            {"code": "612", "labels": {"fr": "Transports sur ventes", "en": "Transport on sales"}, "type": "CHARGE", "classe": 6, "parent": "61", "imputable": True},
            {"code": "613", "labels": {"fr": "Transports pour le compte de tiers", "en": "Transport for third parties"}, "type": "CHARGE", "classe": 6, "parent": "61", "imputable": True},
            {"code": "62", "labels": {"fr": "Services extérieurs A", "en": "External services A"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "621", "labels": {"fr": "Sous-traitance générale", "en": "General subcontracting"}, "type": "CHARGE", "classe": 6, "parent": "62", "imputable": True},
            {"code": "622", "labels": {"fr": "Locations et charges locatives", "en": "Rental and related charges"}, "type": "CHARGE", "classe": 6, "parent": "62", "imputable": True},
            {"code": "624", "labels": {"fr": "Entretiens, réparations et maintenance", "en": "Maintenance and repairs"}, "type": "CHARGE", "classe": 6, "parent": "62", "imputable": True},
            {"code": "625", "labels": {"fr": "Primes d'assurance", "en": "Insurance premiums"}, "type": "CHARGE", "classe": 6, "parent": "62", "imputable": True},
            {"code": "63", "labels": {"fr": "Services extérieurs B", "en": "External services B"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "631", "labels": {"fr": "Frais bancaires", "en": "Banking fees"}, "type": "CHARGE", "classe": 6, "parent": "63", "imputable": True},
            {"code": "632", "labels": {"fr": "Rémunérations d'intermédiaires et de conseils", "en": "Intermediary and advisory fees"}, "type": "CHARGE", "classe": 6, "parent": "63", "imputable": True},
            {"code": "633", "labels": {"fr": "Frais de formation du personnel", "en": "Personnel training costs"}, "type": "CHARGE", "classe": 6, "parent": "63", "imputable": True},
            {"code": "634", "labels": {"fr": "Redevances pour brevets et licences", "en": "Patent and license royalties"}, "type": "CHARGE", "classe": 6, "parent": "63", "imputable": True},
            {"code": "64", "labels": {"fr": "Impôts et taxes", "en": "Taxes and duties"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "641", "labels": {"fr": "Impôts et taxes directs", "en": "Direct taxes"}, "type": "CHARGE", "classe": 6, "parent": "64", "imputable": True},
            {"code": "645", "labels": {"fr": "Impôts et taxes indirects", "en": "Indirect taxes"}, "type": "CHARGE", "classe": 6, "parent": "64", "imputable": True},
            {"code": "65", "labels": {"fr": "Autres charges", "en": "Other expenses"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "651", "labels": {"fr": "Pertes sur créances clients", "en": "Losses on customer receivables"}, "type": "CHARGE", "classe": 6, "parent": "65", "imputable": True},
            {"code": "66", "labels": {"fr": "Charges de personnel", "en": "Personnel expenses"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "661", "labels": {"fr": "Rémunérations directes versées au personnel national", "en": "Direct compensation to national staff"}, "type": "CHARGE", "classe": 6, "parent": "66", "imputable": True},
            {"code": "662", "labels": {"fr": "Rémunérations directes versées au personnel non national", "en": "Direct compensation to non-national staff"}, "type": "CHARGE", "classe": 6, "parent": "66", "imputable": True},
            {"code": "663", "labels": {"fr": "Indemnités forfaitaires versées au personnel", "en": "Lump sum allowances to staff"}, "type": "CHARGE", "classe": 6, "parent": "66", "imputable": True},
            {"code": "664", "labels": {"fr": "Charges sociales", "en": "Social charges"}, "type": "CHARGE", "classe": 6, "parent": "66", "imputable": True},
            {"code": "67", "labels": {"fr": "Frais financiers et charges assimilées", "en": "Financial costs"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "671", "labels": {"fr": "Intérêts des emprunts", "en": "Loan interest"}, "type": "CHARGE", "classe": 6, "parent": "67", "imputable": True},
            {"code": "674", "labels": {"fr": "Pertes de change", "en": "Exchange losses"}, "type": "CHARGE", "classe": 6, "parent": "67", "imputable": True},
            {"code": "68", "labels": {"fr": "Dotations aux amortissements", "en": "Depreciation charges"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "681", "labels": {"fr": "Dotations aux amortissements d'exploitation", "en": "Operating depreciation charges"}, "type": "CHARGE", "classe": 6, "parent": "68", "imputable": True},
            {"code": "69", "labels": {"fr": "Dotations aux provisions", "en": "Provision charges"}, "type": "CHARGE", "classe": 6, "parent": "6"},
            {"code": "691", "labels": {"fr": "Dotations aux provisions d'exploitation", "en": "Operating provision charges"}, "type": "CHARGE", "classe": 6, "parent": "69", "imputable": True},

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 7 - COMPTES DE PRODUITS DES ACTIVITÉS ORDINAIRES
            # ═══════════════════════════════════════════════════════════════
            {"code": "7", "labels": {"fr": "Comptes de produits des activités ordinaires", "en": "Operating income accounts"}, "type": "PRODUIT", "classe": 7, "parent": None},
            {"code": "70", "labels": {"fr": "Ventes", "en": "Sales"}, "type": "PRODUIT", "classe": 7, "parent": "7"},
            {"code": "701", "labels": {"fr": "Ventes de marchandises", "en": "Sales of goods"}, "type": "PRODUIT", "classe": 7, "parent": "70", "imputable": True, "soumis_tva": True},
            {"code": "702", "labels": {"fr": "Ventes de produits finis", "en": "Sales of finished goods"}, "type": "PRODUIT", "classe": 7, "parent": "70", "imputable": True, "soumis_tva": True},
            {"code": "704", "labels": {"fr": "Ventes de travaux", "en": "Sales of works"}, "type": "PRODUIT", "classe": 7, "parent": "70", "imputable": True, "soumis_tva": True},
            {"code": "705", "labels": {"fr": "Travaux facturés", "en": "Invoiced works"}, "type": "PRODUIT", "classe": 7, "parent": "70", "imputable": True, "soumis_tva": True},
            {"code": "706", "labels": {"fr": "Services vendus", "en": "Services sold"}, "type": "PRODUIT", "classe": 7, "parent": "70", "imputable": True, "soumis_tva": True},
            {"code": "707", "labels": {"fr": "Produits accessoires", "en": "Ancillary revenue"}, "type": "PRODUIT", "classe": 7, "parent": "70", "imputable": True, "soumis_tva": True},
            {"code": "71", "labels": {"fr": "Subventions d'exploitation", "en": "Operating subsidies"}, "type": "PRODUIT", "classe": 7, "parent": "7"},
            {"code": "711", "labels": {"fr": "Subventions d'exploitation reçues", "en": "Operating subsidies received"}, "type": "PRODUIT", "classe": 7, "parent": "71", "imputable": True},
            {"code": "72", "labels": {"fr": "Production immobilisée", "en": "Capitalized production"}, "type": "PRODUIT", "classe": 7, "parent": "7"},
            {"code": "721", "labels": {"fr": "Production immobilisée incorporelle", "en": "Capitalized intangible production"}, "type": "PRODUIT", "classe": 7, "parent": "72", "imputable": True},
            {"code": "722", "labels": {"fr": "Production immobilisée corporelle", "en": "Capitalized tangible production"}, "type": "PRODUIT", "classe": 7, "parent": "72", "imputable": True},
            {"code": "73", "labels": {"fr": "Variations de stocks de produits et en-cours", "en": "Changes in inventories of products and WIP"}, "type": "PRODUIT", "classe": 7, "parent": "7"},
            {"code": "734", "labels": {"fr": "Variation de stocks de produits en cours", "en": "Changes in work in progress"}, "type": "PRODUIT", "classe": 7, "parent": "73", "imputable": True},
            {"code": "736", "labels": {"fr": "Variation de stocks de produits finis", "en": "Changes in finished goods"}, "type": "PRODUIT", "classe": 7, "parent": "73", "imputable": True},
            {"code": "75", "labels": {"fr": "Autres produits", "en": "Other income"}, "type": "PRODUIT", "classe": 7, "parent": "7"},
            {"code": "754", "labels": {"fr": "Produits de cessions courantes d'immobilisations", "en": "Proceeds from current asset disposals"}, "type": "PRODUIT", "classe": 7, "parent": "75", "imputable": True},
            {"code": "758", "labels": {"fr": "Produits divers", "en": "Miscellaneous income"}, "type": "PRODUIT", "classe": 7, "parent": "75", "imputable": True},
            {"code": "77", "labels": {"fr": "Revenus financiers et produits assimilés", "en": "Financial income"}, "type": "PRODUIT", "classe": 7, "parent": "7"},
            {"code": "771", "labels": {"fr": "Intérêts de prêts", "en": "Loan interest income"}, "type": "PRODUIT", "classe": 7, "parent": "77", "imputable": True},
            {"code": "774", "labels": {"fr": "Gains de change", "en": "Exchange gains"}, "type": "PRODUIT", "classe": 7, "parent": "77", "imputable": True},
            {"code": "776", "labels": {"fr": "Gains sur cessions de titres de placement", "en": "Gains on investment securities"}, "type": "PRODUIT", "classe": 7, "parent": "77", "imputable": True},
            {"code": "78", "labels": {"fr": "Transferts de charges", "en": "Charge transfers"}, "type": "PRODUIT", "classe": 7, "parent": "7"},
            {"code": "781", "labels": {"fr": "Transferts de charges d'exploitation", "en": "Operating charge transfers"}, "type": "PRODUIT", "classe": 7, "parent": "78", "imputable": True},
            {"code": "79", "labels": {"fr": "Reprises de provisions", "en": "Provision reversals"}, "type": "PRODUIT", "classe": 7, "parent": "7"},
            {"code": "791", "labels": {"fr": "Reprises de provisions d'exploitation", "en": "Operating provision reversals"}, "type": "PRODUIT", "classe": 7, "parent": "79", "imputable": True},

            # ═══════════════════════════════════════════════════════════════
            # CLASSE 8 - COMPTES DES AUTRES CHARGES ET PRODUITS
            # ═══════════════════════════════════════════════════════════════
            {"code": "8", "labels": {"fr": "Comptes des autres charges et produits", "en": "Other charges and income accounts"}, "type": "CHARGE", "classe": 8, "parent": None},
            {"code": "81", "labels": {"fr": "Valeurs comptables des cessions d'immobilisations", "en": "Book values of asset disposals"}, "type": "CHARGE", "classe": 8, "parent": "8"},
            {"code": "811", "labels": {"fr": "Valeurs comptables des cessions d'immobilisations incorporelles", "en": "Book values of intangible asset disposals"}, "type": "CHARGE", "classe": 8, "parent": "81", "imputable": True},
            {"code": "812", "labels": {"fr": "Valeurs comptables des cessions d'immobilisations corporelles", "en": "Book values of tangible asset disposals"}, "type": "CHARGE", "classe": 8, "parent": "81", "imputable": True},
            {"code": "82", "labels": {"fr": "Produits des cessions d'immobilisations", "en": "Proceeds from asset disposals"}, "type": "PRODUIT", "classe": 8, "parent": "8"},
            {"code": "821", "labels": {"fr": "Produits des cessions d'immobilisations incorporelles", "en": "Proceeds from intangible asset disposals"}, "type": "PRODUIT", "classe": 8, "parent": "82", "imputable": True},
            {"code": "822", "labels": {"fr": "Produits des cessions d'immobilisations corporelles", "en": "Proceeds from tangible asset disposals"}, "type": "PRODUIT", "classe": 8, "parent": "82", "imputable": True},
            {"code": "83", "labels": {"fr": "Charges hors activités ordinaires", "en": "Non-operating charges"}, "type": "CHARGE", "classe": 8, "parent": "8"},
            {"code": "831", "labels": {"fr": "Charges hors activités ordinaires", "en": "Non-operating charges"}, "type": "CHARGE", "classe": 8, "parent": "83", "imputable": True},
            {"code": "84", "labels": {"fr": "Produits hors activités ordinaires", "en": "Non-operating income"}, "type": "PRODUIT", "classe": 8, "parent": "8"},
            {"code": "841", "labels": {"fr": "Produits hors activités ordinaires", "en": "Non-operating income"}, "type": "PRODUIT", "classe": 8, "parent": "84", "imputable": True},
            {"code": "85", "labels": {"fr": "Dotations hors activités ordinaires", "en": "Non-operating provisions"}, "type": "CHARGE", "classe": 8, "parent": "8"},
            {"code": "851", "labels": {"fr": "Dotations aux provisions hors activités ordinaires", "en": "Non-operating provision charges"}, "type": "CHARGE", "classe": 8, "parent": "85", "imputable": True},
            {"code": "86", "labels": {"fr": "Reprises hors activités ordinaires", "en": "Non-operating reversals"}, "type": "PRODUIT", "classe": 8, "parent": "8"},
            {"code": "861", "labels": {"fr": "Reprises de provisions hors activités ordinaires", "en": "Non-operating provision reversals"}, "type": "PRODUIT", "classe": 8, "parent": "86", "imputable": True},
            {"code": "87", "labels": {"fr": "Participation des travailleurs", "en": "Employee profit sharing"}, "type": "CHARGE", "classe": 8, "parent": "8"},
            {"code": "871", "labels": {"fr": "Participation des travailleurs", "en": "Employee profit sharing"}, "type": "CHARGE", "classe": 8, "parent": "87", "imputable": True},
            {"code": "89", "labels": {"fr": "Impôts sur le résultat", "en": "Income taxes"}, "type": "CHARGE", "classe": 8, "parent": "8"},
            {"code": "891", "labels": {"fr": "Impôts sur les bénéfices de l'exercice", "en": "Income tax expense"}, "type": "CHARGE", "classe": 8, "parent": "89", "imputable": True},
            {"code": "892", "labels": {"fr": "Rappels d'impôts sur les résultats", "en": "Prior year tax adjustments"}, "type": "CHARGE", "classe": 8, "parent": "89", "imputable": True},
        ]
