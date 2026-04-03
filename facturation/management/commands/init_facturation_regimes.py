# facturation/management/commands/init_facturation_regimes.py
"""
Seed les données de configuration facturation par régime fiscal :
- NiveauRelance (frais et délais de relance)
- TypeIdentifiantLegal (IDE, SIRET, RCCM, NIF…)
- MentionLegale (mentions obligatoires sur factures)

Idempotent : utilise get_or_create / update_or_create.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from core.models import TypeIdentifiantLegal
from facturation.models import NiveauRelance, MentionLegale
from tva.models import RegimeFiscal


class Command(BaseCommand):
    help = "Initialise les NiveauRelance, TypeIdentifiantLegal et MentionLegale par régime"

    def handle(self, *args, **options):
        self._seed_types_identifiants()
        self._seed_niveaux_relance()
        self._seed_mentions_legales()
        self.stdout.write(self.style.SUCCESS("init_facturation_regimes terminé"))

    # ── Types d'identifiants légaux ────────────────────────────────
    def _seed_types_identifiants(self):
        regimes = {r.code: r for r in RegimeFiscal.objects.all()}

        TYPES = [
            # Suisse
            {"code": "IDE", "libelle": "Identifiant des entreprises (IDE)", "pays": "CH",
             "regime": "CH", "format_validation": r"^CHE-\d{3}\.\d{3}\.\d{3}$",
             "exemple": "CHE-123.456.789", "obligatoire_entreprise": True, "obligatoire_client": False},
            {"code": "TVA_CH", "libelle": "Numéro TVA suisse", "pays": "CH",
             "regime": "CH", "format_validation": r"^CHE-\d{3}\.\d{3}\.\d{3}\s?TVA$",
             "exemple": "CHE-123.456.789 TVA", "obligatoire_entreprise": False, "obligatoire_client": False},
            {"code": "RC_CH", "libelle": "Registre du commerce (CH)", "pays": "CH",
             "regime": "CH", "exemple": "CH-550-1234567-8"},
            # France
            {"code": "SIRET", "libelle": "SIRET", "pays": "FR",
             "regime": "FR", "format_validation": r"^\d{14}$",
             "exemple": "12345678901234", "obligatoire_entreprise": True, "obligatoire_client": True},
            {"code": "SIREN", "libelle": "SIREN", "pays": "FR",
             "regime": "FR", "format_validation": r"^\d{9}$",
             "exemple": "123456789"},
            {"code": "TVA_INTRACOM", "libelle": "N° TVA intracommunautaire", "pays": "FR",
             "regime": "FR", "format_validation": r"^FR\d{2}\d{9}$",
             "exemple": "FR12345678901", "obligatoire_entreprise": True, "obligatoire_client": False},
            {"code": "APE", "libelle": "Code APE/NAF", "pays": "FR",
             "regime": "FR", "exemple": "6201Z"},
            # OHADA (Cameroun, Sénégal, Côte d'Ivoire, Mali…)
            {"code": "RCCM", "libelle": "Registre du Commerce et du Crédit Mobilier (RCCM)", "pays": "",
             "regime": None, "exemple": "RC/DLA/2024/B/1234",
             "obligatoire_entreprise": True, "obligatoire_client": True},
            {"code": "NIF", "libelle": "Numéro d'Identification Fiscale (NIF)", "pays": "",
             "regime": None, "exemple": "P012345678901A",
             "obligatoire_entreprise": True, "obligatoire_client": False},
            {"code": "NUM_CONTRIBUABLE", "libelle": "Numéro de contribuable", "pays": "",
             "regime": None, "exemple": "M012345678901T"},
            # Générique
            {"code": "TVA_GENERIC", "libelle": "Numéro de TVA", "pays": "",
             "regime": None, "obligatoire_entreprise": False, "obligatoire_client": False,
             "afficher_sur_facture": True},
        ]

        count = 0
        for t in TYPES:
            regime = regimes.get(t.pop("regime", None))
            _, created = TypeIdentifiantLegal.objects.update_or_create(
                code=t.pop("code"),
                defaults={
                    "libelle": t.get("libelle", ""),
                    "pays": t.get("pays", ""),
                    "regime_fiscal": regime,
                    "format_validation": t.get("format_validation", ""),
                    "exemple": t.get("exemple", ""),
                    "obligatoire_entreprise": t.get("obligatoire_entreprise", False),
                    "obligatoire_client": t.get("obligatoire_client", False),
                    "afficher_sur_facture": t.get("afficher_sur_facture", True),
                    "ordre": count,
                },
            )
            count += 1
            if created:
                self.stdout.write(f"  TypeIdentifiantLegal créé : {t.get('libelle')}")

    # ── Niveaux de relance par régime ──────────────────────────────
    def _seed_niveaux_relance(self):
        CONFIGS = {
            "CH": [
                {"niveau": 1, "libelle": "1ère relance", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 2, "libelle": "2ème relance", "delai_jours": 10, "frais": Decimal("20"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 3, "libelle": "3ème relance", "delai_jours": 10, "frais": Decimal("40"), "interets": True, "taux_interet": Decimal("5")},
                {"niveau": 4, "libelle": "Mise en demeure", "delai_jours": 10, "frais": Decimal("50"), "interets": True, "taux_interet": Decimal("5")},
            ],
            "CM": [
                {"niveau": 1, "libelle": "1er rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 2, "libelle": "2ème rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 3, "libelle": "Mise en demeure", "delai_jours": 8, "frais": Decimal("0"), "interets": True, "taux_interet": Decimal("10")},
            ],
            "SN": [
                {"niveau": 1, "libelle": "1er rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 2, "libelle": "2ème rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 3, "libelle": "Mise en demeure", "delai_jours": 8, "frais": Decimal("0"), "interets": True, "taux_interet": Decimal("10")},
            ],
            "CI": [
                {"niveau": 1, "libelle": "1er rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 2, "libelle": "2ème rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 3, "libelle": "Mise en demeure", "delai_jours": 8, "frais": Decimal("0"), "interets": True, "taux_interet": Decimal("10")},
            ],
            "ML": [
                {"niveau": 1, "libelle": "1er rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 2, "libelle": "2ème rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 3, "libelle": "Mise en demeure", "delai_jours": 8, "frais": Decimal("0"), "interets": True, "taux_interet": Decimal("10")},
            ],
            "BF": [
                {"niveau": 1, "libelle": "1er rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 2, "libelle": "2ème rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 3, "libelle": "Mise en demeure", "delai_jours": 8, "frais": Decimal("0"), "interets": True, "taux_interet": Decimal("10")},
            ],
            "NE": [
                {"niveau": 1, "libelle": "1er rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 2, "libelle": "2ème rappel", "delai_jours": 15, "frais": Decimal("0"), "interets": False, "taux_interet": Decimal("0")},
                {"niveau": 3, "libelle": "Mise en demeure", "delai_jours": 8, "frais": Decimal("0"), "interets": True, "taux_interet": Decimal("10")},
            ],
        }

        for code, niveaux in CONFIGS.items():
            try:
                regime = RegimeFiscal.objects.get(code=code)
            except RegimeFiscal.DoesNotExist:
                continue
            for n in niveaux:
                _, created = NiveauRelance.objects.update_or_create(
                    regime_fiscal=regime, niveau=n["niveau"],
                    defaults={
                        "libelle": n["libelle"],
                        "delai_jours": n["delai_jours"],
                        "frais": n["frais"],
                        "interets": n["interets"],
                        "taux_interet": n["taux_interet"],
                    },
                )
                if created:
                    self.stdout.write(f"  NiveauRelance créé : {code} niv.{n['niveau']}")

    # ── Mentions légales par régime ─────────────────────────────��──
    def _seed_mentions_legales(self):
        MENTIONS = {
            "CH": [
                {"code": "TVA_NUMBER", "libelle": "Numéro TVA", "texte": "N° TVA : {tva_number}",
                 "type_document": "TOUS", "obligatoire": True},
                {"code": "IDE_NUMBER", "libelle": "Numéro IDE", "texte": "IDE : {ide_number}",
                 "type_document": "TOUS", "obligatoire": True},
                {"code": "SIMPLIFIEE", "libelle": "Facture simplifiée", "texte": "Facture simplifiée conformément à l'art. 26 MWSTG",
                 "type_document": "FACTURE", "obligatoire": False},
            ],
            "CM": [
                {"code": "NIF", "libelle": "NIF", "texte": "NIF : {nif}",
                 "type_document": "TOUS", "obligatoire": True},
                {"code": "RCCM", "libelle": "RCCM", "texte": "RCCM : {rccm}",
                 "type_document": "TOUS", "obligatoire": True},
                {"code": "NUM_CONTRIBUABLE", "libelle": "N° contribuable", "texte": "N° Contribuable : {num_contribuable}",
                 "type_document": "TOUS", "obligatoire": True},
                {"code": "REGIME", "libelle": "Régime d'imposition", "texte": "Régime d'imposition : {regime_imposition}",
                 "type_document": "FACTURE", "obligatoire": True},
            ],
            "SN": [
                {"code": "NIF", "libelle": "NINEA", "texte": "NINEA : {nif}",
                 "type_document": "TOUS", "obligatoire": True},
                {"code": "RCCM", "libelle": "RCCM", "texte": "RCCM : {rccm}",
                 "type_document": "TOUS", "obligatoire": True},
            ],
            "CI": [
                {"code": "NIF", "libelle": "N° compte contribuable", "texte": "CC : {nif}",
                 "type_document": "TOUS", "obligatoire": True},
                {"code": "RCCM", "libelle": "RCCM", "texte": "RCCM : {rccm}",
                 "type_document": "TOUS", "obligatoire": True},
            ],
        }

        for code, mentions in MENTIONS.items():
            try:
                regime = RegimeFiscal.objects.get(code=code)
            except RegimeFiscal.DoesNotExist:
                continue
            for i, m in enumerate(mentions):
                _, created = MentionLegale.objects.update_or_create(
                    regime_fiscal=regime, code=m["code"],
                    defaults={
                        "libelle": m["libelle"],
                        "texte": m["texte"],
                        "type_document": m["type_document"],
                        "obligatoire": m["obligatoire"],
                        "ordre": i,
                    },
                )
                if created:
                    self.stdout.write(f"  MentionLegale créée : {code} — {m['code']}")
