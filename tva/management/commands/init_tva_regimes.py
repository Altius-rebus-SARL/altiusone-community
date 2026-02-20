# tva/management/commands/init_tva_regimes.py
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from core.models import Devise
from tva.models import RegimeFiscal, TauxTVA


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


class Command(BaseCommand):
    help = 'Initialise les régimes fiscaux (CH, CM, SN, CI) avec leurs taux TVA'

    def handle(self, *args, **options):
        created_regimes = 0
        created_taux = 0

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

        total_regimes = RegimeFiscal.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Régimes fiscaux: {created_regimes} créés, {total_regimes} total'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Taux TVA: {created_taux} créés'
        ))
