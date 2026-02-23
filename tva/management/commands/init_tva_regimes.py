# tva/management/commands/init_tva_regimes.py
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from core.models import Devise
from tva.models import RegimeFiscal, TauxTVA, CodeTVA


REGIMES = [
    {
        'code': 'CH',
        'nom': 'Suisse',
        'pays': 'CH',
        'devise_code': 'CHF',
        'devise_defaults': {
            'nom': 'Franc suisse',
            'symbole': 'Fr.',
            'separateur_milliers': "'",
            'separateur_decimal': '.',
            'taux_change': Decimal('1'),
            'est_devise_base': True,
        },
        'nom_taxe': 'TVA',
        'taux_normal': Decimal('8.1'),
        'a_taux_reduit': True,
        'a_taux_special': True,
        'format_numero_tva': r'^CHE-\d{3}\.\d{3}\.\d{3}\s?TVA$',
        'supporte_xml': True,
        'methodes_disponibles': [
            'EFFECTIVE', 'TAUX_DETTE', 'TAUX_FORFAITAIRE', 'FORFAIT_BRANCHE'
        ],
        'taux': [
            ('NORMAL', Decimal('8.1'), 'Taux normal TVA Suisse'),
            ('REDUIT', Decimal('2.6'), 'Taux réduit TVA Suisse'),
            ('SPECIAL', Decimal('3.8'), 'Taux spécial hébergement'),
        ],
        'taux_sss': [
            (Decimal('0.1'), 'SSS 0.1%'),
            (Decimal('0.6'), 'SSS 0.6%'),
            (Decimal('1.3'), 'SSS 1.3%'),
            (Decimal('2.1'), 'SSS 2.1%'),
            (Decimal('3.0'), 'SSS 3.0%'),
            (Decimal('3.7'), 'SSS 3.7%'),
            (Decimal('4.5'), 'SSS 4.5%'),
            (Decimal('5.3'), 'SSS 5.3%'),
            (Decimal('6.2'), 'SSS 6.2%'),
            (Decimal('6.8'), 'SSS 6.8%'),
        ],
    },
    {
        'code': 'CM',
        'nom': 'Cameroun (OHADA)',
        'pays': 'CM',
        'devise_code': 'XAF',
        'devise_defaults': {
            'nom': 'Franc CFA (CEMAC)',
            'symbole': 'FCFA',
            'separateur_milliers': ' ',
            'separateur_decimal': ',',
            'taux_change': Decimal('0.00152'),
            'est_devise_base': False,
        },
        'nom_taxe': 'TVA',
        'taux_normal': Decimal('19.25'),
        'a_taux_reduit': False,
        'a_taux_special': False,
        'format_numero_tva': '',
        'supporte_xml': False,
        'methodes_disponibles': [
            'REEL_NORMAL', 'REEL_SIMPLIFIE', 'FORFAITAIRE'
        ],
        'taux': [
            ('NORMAL', Decimal('19.25'), 'Taux normal TVA Cameroun'),
        ],
    },
    {
        'code': 'SN',
        'nom': 'Sénégal (OHADA)',
        'pays': 'SN',
        'devise_code': 'XOF',
        'devise_defaults': {
            'nom': 'Franc CFA (UEMOA)',
            'symbole': 'FCFA',
            'separateur_milliers': ' ',
            'separateur_decimal': ',',
            'taux_change': Decimal('0.00152'),
            'est_devise_base': False,
        },
        'nom_taxe': 'TVA',
        'taux_normal': Decimal('18.0'),
        'a_taux_reduit': True,
        'a_taux_special': False,
        'format_numero_tva': '',
        'supporte_xml': False,
        'methodes_disponibles': [
            'REEL_NORMAL', 'REEL_SIMPLIFIE'
        ],
        'taux': [
            ('NORMAL', Decimal('18.0'), 'Taux normal TVA Sénégal'),
            ('REDUIT', Decimal('10.0'), 'Taux réduit TVA Sénégal'),
        ],
    },
    {
        'code': 'CI',
        'nom': "Côte d'Ivoire (OHADA)",
        'pays': 'CI',
        'devise_code': 'XOF',
        'devise_defaults': {
            'nom': 'Franc CFA (UEMOA)',
            'symbole': 'FCFA',
            'separateur_milliers': ' ',
            'separateur_decimal': ',',
            'taux_change': Decimal('0.00152'),
            'est_devise_base': False,
        },
        'nom_taxe': 'TVA',
        'taux_normal': Decimal('18.0'),
        'a_taux_reduit': True,
        'a_taux_special': False,
        'format_numero_tva': '',
        'supporte_xml': False,
        'methodes_disponibles': [
            'REEL_NORMAL', 'REEL_SIMPLIFIE'
        ],
        'taux': [
            ('NORMAL', Decimal('18.0'), "Taux normal TVA Côte d'Ivoire"),
            ('REDUIT', Decimal('9.0'), "Taux réduit TVA Côte d'Ivoire"),
        ],
    },
]


# 19 codes AFC suisses pour le decompte TVA (methode effective)
CODES_AFC_CH = [
    # I. Chiffre d'affaires
    ('200', "Total des contre-prestations convenues ou reçues", 'CHIFFRE_AFFAIRES', 10),
    ('205', "Prestations non-imposables (art. 21)", 'CHIFFRE_AFFAIRES', 20),
    ('900', "Subventions, taxes de séjour", 'CHIFFRE_AFFAIRES', 30),
    ('910', "Dons, dividendes, indemnités dommages", 'CHIFFRE_AFFAIRES', 40),
    # II. Déductions
    ('220', "Déductions (prestations à l'étranger)", 'DEDUCTIONS', 50),
    ('221', "Prestations exonérées (art. 23)", 'DEDUCTIONS', 60),
    ('225', "Contre-prestations exclues du calcul", 'DEDUCTIONS', 70),
    ('230', "Prestations à des non-assujettis", 'DEDUCTIONS', 80),
    ('235', "Diminutions de la contre-prestation", 'DEDUCTIONS', 90),
    # III. Prestations imposables
    ('302', "Prestations au taux normal (8.1%)", 'PRESTATIONS_IMPOSABLES', 100),
    ('312', "Prestations au taux réduit (2.6%)", 'PRESTATIONS_IMPOSABLES', 110),
    ('342', "Prestations au taux spécial hébergement (3.8%)", 'PRESTATIONS_IMPOSABLES', 120),
    # IV. TVA due
    ('382', "Impôt sur les acquisitions", 'TVA_DUE', 130),
    # V. Impôt préalable
    ('400', "Impôt préalable sur coût matériel/prestations", 'TVA_PREALABLE', 140),
    ('405', "Impôt préalable sur investissements", 'TVA_PREALABLE', 150),
    ('410', "Dégrèvement ultérieur de l'impôt préalable", 'TVA_PREALABLE', 160),
    # VI. Corrections
    ('415', "Réductions de la déduction de l'impôt préalable", 'CORRECTIONS', 170),
    ('500', "Montant à payer / en faveur de l'AFC", 'CORRECTIONS', 180),
    ('510', "Correction du solde exercice précédent", 'CORRECTIONS', 190),
]

# Mapping code -> type_taux pour lier les codes 302/312/342 a leur TauxTVA
CODE_TAUX_MAP = {
    '302': 'NORMAL',
    '312': 'REDUIT',
    '342': 'SPECIAL',
}

# Codes simplifies pour la methode SSS
CODES_SSS_CH = [
    ('200', "Total des contre-prestations convenues ou reçues (TTC)", 'CHIFFRE_AFFAIRES', 10),
    ('205', "Prestations non-imposables (art. 21)", 'CHIFFRE_AFFAIRES', 20),
    ('220', "Déductions", 'DEDUCTIONS', 30),
    ('321', "Impôt au taux de la dette fiscale nette", 'TVA_DUE', 40),
    ('500', "Montant à payer", 'CORRECTIONS', 50),
]


class Command(BaseCommand):
    help = 'Initialise les régimes fiscaux (CH, CM, SN, CI) avec leurs taux TVA et codes AFC'

    def handle(self, *args, **options):
        created_regimes = 0
        created_taux = 0
        created_codes = 0

        for regime_data in REGIMES:
            # 1. Create/get Devise
            devise, _ = Devise.objects.get_or_create(
                code=regime_data['devise_code'],
                defaults=regime_data['devise_defaults'],
            )

            # 2. Create/get TypePlanComptable if OHADA
            type_plan = None
            if regime_data['code'] != 'CH':
                from comptabilite.models import TypePlanComptable
                type_plan, _ = TypePlanComptable.objects.get_or_create(
                    code='OHADA',
                    defaults={
                        'nom': 'Plan comptable OHADA',
                        'description': 'Système comptable OHADA pour les pays africains',
                        'pays': 'CEMAC/UEMOA',
                        'norme_comptable': 'OHADA',
                    }
                )

            # 3. Create/get RegimeFiscal
            regime, created = RegimeFiscal.objects.get_or_create(
                code=regime_data['code'],
                defaults={
                    'nom': regime_data['nom'],
                    'pays': regime_data['pays'],
                    'devise_defaut': devise,
                    'type_plan_comptable': type_plan,
                    'nom_taxe': regime_data['nom_taxe'],
                    'taux_normal': regime_data['taux_normal'],
                    'a_taux_reduit': regime_data['a_taux_reduit'],
                    'a_taux_special': regime_data['a_taux_special'],
                    'format_numero_tva': regime_data['format_numero_tva'],
                    'supporte_xml': regime_data['supporte_xml'],
                    'methodes_disponibles': regime_data['methodes_disponibles'],
                }
            )
            if created:
                created_regimes += 1

            # 4. Create TauxTVA for this regime
            for type_taux, valeur, description in regime_data['taux']:
                _, taux_created = TauxTVA.objects.get_or_create(
                    regime=regime,
                    type_taux=type_taux,
                    date_debut=date(2024, 1, 1),
                    defaults={
                        'taux': valeur,
                        'description': description,
                    },
                )
                if taux_created:
                    created_taux += 1

            # 5. Create SSS rates (Switzerland only)
            for valeur, description in regime_data.get('taux_sss', []):
                _, taux_created = TauxTVA.objects.get_or_create(
                    regime=regime,
                    type_taux='SSS',
                    taux=valeur,
                    date_debut=date(2024, 1, 1),
                    defaults={
                        'description': description,
                    },
                )
                if taux_created:
                    created_taux += 1

        # 6. Create CodeTVA AFC for Swiss regime
        try:
            regime_ch = RegimeFiscal.objects.get(code='CH')
        except RegimeFiscal.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                'Régime CH introuvable, codes AFC non créés'
            ))
        else:
            # Effective method codes
            for code, libelle, categorie, ordre in CODES_AFC_CH:
                taux_applicable = None
                if code in CODE_TAUX_MAP:
                    taux_applicable = TauxTVA.objects.filter(
                        regime=regime_ch,
                        type_taux=CODE_TAUX_MAP[code],
                        date_fin__isnull=True,
                    ).first()

                _, code_created = CodeTVA.objects.get_or_create(
                    regime=regime_ch,
                    code=code,
                    defaults={
                        'libelle': libelle,
                        'categorie': categorie,
                        'ordre_affichage': ordre,
                        'taux_applicable': taux_applicable,
                        'actif': True,
                    },
                )
                if code_created:
                    created_codes += 1

        total_regimes = RegimeFiscal.objects.count()
        total_codes = CodeTVA.objects.filter(regime__code='CH').count()
        self.stdout.write(self.style.SUCCESS(
            f'Régimes fiscaux: {created_regimes} créés, {total_regimes} total'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Taux TVA: {created_taux} créés'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Codes AFC: {created_codes} créés, {total_codes} total pour CH'
        ))
