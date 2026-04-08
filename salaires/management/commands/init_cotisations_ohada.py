# salaires/management/commands/init_cotisations_ohada.py
"""
Seed les taux de cotisations sociales pour les pays OHADA / Afrique de l'Ouest.
Barèmes 2024. Idempotent via update_or_create.

Pays couverts : Mali (ML), Sénégal (SN), Côte d'Ivoire (CI),
Burkina Faso (BF), Niger (NE), Cameroun (CM).
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from salaires.models import TauxCotisation
from tva.models import RegimeFiscal


# Format : (type, libelle, taux_employe, taux_employeur, salaire_max, ordre)
COTISATIONS = {
    # ── Mali (INPS + AMO) ──────────────────────────────────────────
    'ML': [
        ('INPS_RET', 'INPS Retraite', Decimal('3.6'), Decimal('5.4'), None, 10),
        ('INPS_PF', 'INPS Prestations familiales', Decimal('0'), Decimal('8.0'), None, 20),
        ('INPS_AT', 'INPS Accidents du travail', Decimal('0'), Decimal('2.0'), None, 30),
        ('AMO_ML', 'AMO Assurance maladie', Decimal('3.06'), Decimal('3.5'), None, 40),
    ],
    # ── Sénégal (CSS + IPRES + IPM + CFCE) ─────────────────────────
    'SN': [
        ('IPRES_GEN', 'IPRES Régime général', Decimal('5.6'), Decimal('8.4'), None, 10),
        ('IPRES_CAD', 'IPRES Régime cadre', Decimal('3.6'), Decimal('5.4'), None, 20),
        ('CSS', 'CSS Prestations familiales', Decimal('0'), Decimal('7.0'), Decimal('63000'), 30),
        ('CSS', 'CSS Accidents du travail', Decimal('0'), Decimal('3.0'), Decimal('63000'), 31),
        ('IPM', 'IPM Maladie', Decimal('3.0'), Decimal('3.0'), None, 40),
        ('CFCE', 'CFCE Formation professionnelle', Decimal('0'), Decimal('3.0'), None, 50),
    ],
    # ── Côte d'Ivoire (CNPS + CMU + FNE) ────────────────────────────
    'CI': [
        ('CNPS_CI_RET', 'CNPS Retraite', Decimal('6.3'), Decimal('7.7'), Decimal('2700000'), 10),
        ('CNPS_CI_PF', 'CNPS Prestations familiales', Decimal('0'), Decimal('5.75'), Decimal('70000'), 20),
        ('CNPS_CI_AT', 'CNPS Accidents du travail', Decimal('0'), Decimal('2.0'), Decimal('70000'), 30),
        ('CMU_CI', 'CMU Assurance maladie', Decimal('1.3'), Decimal('1.3'), None, 40),
        ('FNE', 'FNE Contribution emploi', Decimal('0'), Decimal('1.2'), Decimal('70000'), 50),
    ],
    # ── Burkina Faso (CNSS) ──────────────────────────────────────────
    'BF': [
        ('CNSS_BF_RET', 'CNSS Retraite', Decimal('5.5'), Decimal('5.5'), Decimal('600000'), 10),
        ('CNSS_BF_PF', 'CNSS Prestations familiales', Decimal('0'), Decimal('7.0'), Decimal('600000'), 20),
        ('CNSS_BF_AT', 'CNSS Accidents du travail', Decimal('0'), Decimal('3.5'), Decimal('600000'), 30),
    ],
    # ── Niger (CNSS) ─────────────────────────────────────────────────
    'NE': [
        ('CNSS_NE_RET', 'CNSS Retraite', Decimal('1.6'), Decimal('6.4'), Decimal('500000'), 10),
        ('CNSS_NE_PF', 'CNSS Prestations familiales', Decimal('0'), Decimal('11.0'), Decimal('500000'), 20),
        ('CNSS_NE_AT', 'CNSS Accidents du travail', Decimal('0'), Decimal('1.75'), Decimal('500000'), 30),
    ],
    # ── Cameroun (CNPS) ──────────────────────────────────────────────
    'CM': [
        ('CNPS_VIE', 'CNPS Assurance vieillesse', Decimal('2.8'), Decimal('4.2'), Decimal('750000'), 10),
        ('CNPS_AF', 'CNPS Allocations familiales', Decimal('0'), Decimal('7.0'), Decimal('750000'), 20),
        ('CNPS_AT', 'CNPS Accidents du travail', Decimal('0'), Decimal('1.75'), Decimal('750000'), 30),
    ],
}


class Command(BaseCommand):
    help = "Initialise les taux de cotisations sociales OHADA (ML, SN, CI, BF, NE, CM)"

    def handle(self, *args, **options):
        date_debut = date(2024, 1, 1)
        count = 0

        for code_regime, cotisations in COTISATIONS.items():
            try:
                regime = RegimeFiscal.objects.get(code=code_regime)
            except RegimeFiscal.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Régime {code_regime} non trouvé — skip"))
                continue

            devise = regime.devise_defaut

            for type_cot, libelle, taux_emp, taux_pat, sal_max, ordre in cotisations:
                _, created = TauxCotisation.objects.update_or_create(
                    type_cotisation=type_cot,
                    regime_fiscal=regime,
                    date_debut=date_debut,
                    defaults={
                        'libelle': libelle,
                        'taux_employe': taux_emp,
                        'taux_employeur': taux_pat,
                        'salaire_max': sal_max,
                        'devise': devise,
                        'ordre': ordre,
                    },
                )
                if created:
                    count += 1
                    self.stdout.write(f"  {code_regime} — {libelle}")

        self.stdout.write(self.style.SUCCESS(
            f"init_cotisations_ohada: {count} taux créés"
        ))
