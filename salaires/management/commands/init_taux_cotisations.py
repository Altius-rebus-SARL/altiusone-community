"""
Commande de gestion pour initialiser les taux de cotisations sociales suisses.

Cree les taux 2026 par defaut si ils n'existent pas.
Idempotente : peut etre relancee sans risque (get_or_create sur type_cotisation).

Note : LPP (15%) et LAA (1.5%) sont des taux moyens/par defaut.
En realite ils varient par entreprise. Les taux sont modifiables via l'API/UI.
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from salaires.models import TauxCotisation


TAUX_2026 = [
    {
        'type_cotisation': 'AVS',
        'libelle': 'AVS/AI/APG',
        'taux_total': Decimal('10.6000'),
        'taux_employeur': Decimal('5.3000'),
        'taux_employe': Decimal('5.3000'),
        'repartition': 'PARTAGE',
        'salaire_min': None,
        'salaire_max': None,
        'date_debut': date(2026, 1, 1),
        'date_fin': None,
        'actif': True,
    },
    {
        'type_cotisation': 'AC',
        'libelle': 'Assurance chômage',
        'taux_total': Decimal('2.2000'),
        'taux_employeur': Decimal('1.1000'),
        'taux_employe': Decimal('1.1000'),
        'repartition': 'PARTAGE',
        'salaire_min': None,
        'salaire_max': Decimal('148200.00'),
        'date_debut': date(2026, 1, 1),
        'date_fin': None,
        'actif': True,
    },
    {
        'type_cotisation': 'AC_SUPP',
        'libelle': 'AC supplément solidarité',
        'taux_total': Decimal('1.0000'),
        'taux_employeur': Decimal('0.5000'),
        'taux_employe': Decimal('0.5000'),
        'repartition': 'PARTAGE',
        'salaire_min': Decimal('148200.00'),
        'salaire_max': None,
        'date_debut': date(2026, 1, 1),
        'date_fin': None,
        'actif': True,
    },
    {
        'type_cotisation': 'LPP',
        'libelle': 'Prévoyance professionnelle (2e pilier)',
        'taux_total': Decimal('15.0000'),
        'taux_employeur': Decimal('7.5000'),
        'taux_employe': Decimal('7.5000'),
        'repartition': 'PARTAGE',
        'salaire_min': None,
        'salaire_max': None,
        'date_debut': date(2026, 1, 1),
        'date_fin': None,
        'actif': True,
    },
    {
        'type_cotisation': 'LAA',
        'libelle': 'LAA Accidents professionnels',
        'taux_total': Decimal('1.5000'),
        'taux_employeur': Decimal('1.5000'),
        'taux_employe': Decimal('0.0000'),
        'repartition': 'EMPLOYEUR',
        'salaire_min': None,
        'salaire_max': Decimal('148200.00'),
        'date_debut': date(2026, 1, 1),
        'date_fin': None,
        'actif': True,
    },
    {
        'type_cotisation': 'LAAC',
        'libelle': 'LAAC Accidents complémentaire',
        'taux_total': Decimal('0.5000'),
        'taux_employeur': Decimal('0.2500'),
        'taux_employe': Decimal('0.2500'),
        'repartition': 'PARTAGE',
        'salaire_min': None,
        'salaire_max': Decimal('148200.00'),
        'date_debut': date(2026, 1, 1),
        'date_fin': None,
        'actif': True,
    },
    {
        'type_cotisation': 'IJM',
        'libelle': 'Indemnités journalières maladie',
        'taux_total': Decimal('1.4000'),
        'taux_employeur': Decimal('0.7000'),
        'taux_employe': Decimal('0.7000'),
        'repartition': 'PARTAGE',
        'salaire_min': None,
        'salaire_max': None,
        'date_debut': date(2026, 1, 1),
        'date_fin': None,
        'actif': True,
    },
    {
        'type_cotisation': 'AF',
        'libelle': 'Allocations familiales',
        'taux_total': Decimal('2.0000'),
        'taux_employeur': Decimal('2.0000'),
        'taux_employe': Decimal('0.0000'),
        'repartition': 'EMPLOYEUR',
        'salaire_min': None,
        'salaire_max': None,
        'date_debut': date(2026, 1, 1),
        'date_fin': None,
        'actif': True,
    },
]


class Command(BaseCommand):
    help = "Initialise les taux de cotisations sociales suisses 2026"

    def handle(self, *args, **options):
        created_count = 0
        for taux_data in TAUX_2026:
            type_cot = taux_data['type_cotisation']
            defaults = {k: v for k, v in taux_data.items() if k != 'type_cotisation'}

            _, created = TauxCotisation.objects.get_or_create(
                type_cotisation=type_cot,
                defaults=defaults,
            )
            if created:
                self.stdout.write(
                    f"  ✓ Taux créé : {type_cot} - {taux_data['libelle']} "
                    f"({taux_data['taux_total']}%)"
                )
                created_count += 1
            else:
                self.stdout.write(f"  · Taux existant : {type_cot}")

        if created_count:
            self.stdout.write(self.style.SUCCESS(
                f"{created_count} taux de cotisation(s) créé(s)."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Tous les taux de cotisations existent déjà."
            ))
