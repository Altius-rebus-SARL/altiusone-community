# salaires/management/commands/init_allocations_familiales.py
"""
Seed les montants d'allocations familiales par canton (barèmes 2024).
Idempotent : utilise update_or_create.
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from salaires.models import AllocationFamiliale


BAREMES_2024 = {
    'GE': {'ENFANT': 311, 'FORMATION': 415, 'NAISSANCE': 2000},
    'VD': {'ENFANT': 300, 'FORMATION': 400, 'NAISSANCE': 1500},
    'VS': {'ENFANT': 305, 'FORMATION': 440, 'NAISSANCE': 2000},
    'NE': {'ENFANT': 250, 'FORMATION': 320, 'NAISSANCE': 1200},
    'JU': {'ENFANT': 275, 'FORMATION': 325, 'NAISSANCE': 1500},
    'FR': {'ENFANT': 285, 'FORMATION': 365, 'NAISSANCE': 1500},
    'BE': {'ENFANT': 230, 'FORMATION': 290, 'NAISSANCE': 0},
    'ZH': {'ENFANT': 200, 'FORMATION': 250, 'NAISSANCE': 0},
    'LU': {'ENFANT': 210, 'FORMATION': 260, 'NAISSANCE': 0},
    'AG': {'ENFANT': 200, 'FORMATION': 250, 'NAISSANCE': 0},
    'SG': {'ENFANT': 230, 'FORMATION': 280, 'NAISSANCE': 0},
    'TI': {'ENFANT': 200, 'FORMATION': 250, 'NAISSANCE': 0},
    'BS': {'ENFANT': 275, 'FORMATION': 325, 'NAISSANCE': 0},
    # Montants fédéraux minimaux
    'DEFAULT': {'ENFANT': 200, 'FORMATION': 250, 'NAISSANCE': 0},
}


class Command(BaseCommand):
    help = "Initialise les barèmes d'allocations familiales par canton"

    def handle(self, *args, **options):
        date_debut = date(2024, 1, 1)
        count = 0
        for canton, types in BAREMES_2024.items():
            for type_alloc, montant in types.items():
                _, created = AllocationFamiliale.objects.update_or_create(
                    canton=canton,
                    type_allocation=type_alloc,
                    date_debut=date_debut,
                    defaults={'montant': Decimal(str(montant))},
                )
                if created:
                    count += 1
        self.stdout.write(self.style.SUCCESS(
            f"init_allocations_familiales: {count} barèmes créés"
        ))
