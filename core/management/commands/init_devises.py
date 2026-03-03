"""
Commande de gestion pour initialiser les devises par défaut.

Crée les devises essentielles (CHF, EUR, USD, XOF) si elles n'existent pas,
puis met à jour les taux de change via le service SNB pour les devises supportées.
Idempotente : peut être relancée sans risque.
"""

from django.core.management.base import BaseCommand

from core.models import Devise
from core.services.snb_exchange_rate_service import SNBExchangeRateService


DEVISES_DEFAUT = [
    {
        "code": "CHF",
        "nom": "Franc suisse",
        "symbole": "CHF",
        "decimales": 2,
        "separateur_milliers": "'",
        "separateur_decimal": ".",
        "symbole_avant": False,
        "taux_change": 1,
        "est_devise_base": True,
        "actif": True,
    },
    {
        "code": "EUR",
        "nom": "Euro",
        "symbole": "€",
        "decimales": 2,
        "separateur_milliers": " ",
        "separateur_decimal": ",",
        "symbole_avant": False,
        "taux_change": 1,
        "est_devise_base": False,
        "actif": True,
    },
    {
        "code": "USD",
        "nom": "Dollar américain",
        "symbole": "$",
        "decimales": 2,
        "separateur_milliers": ",",
        "separateur_decimal": ".",
        "symbole_avant": True,
        "taux_change": 1,
        "est_devise_base": False,
        "actif": True,
    },
    {
        "code": "XOF",
        "nom": "Franc CFA (BCEAO)",
        "symbole": "FCFA",
        "decimales": 0,
        "separateur_milliers": " ",
        "separateur_decimal": ",",
        "symbole_avant": False,
        "taux_change": 1,
        "est_devise_base": False,
        "actif": True,
    },
]


class Command(BaseCommand):
    help = "Initialise les devises par défaut (CHF, EUR, USD, XOF) et met à jour les taux SNB"

    def handle(self, *args, **options):
        created_count = 0
        for devise_data in DEVISES_DEFAUT:
            _, created = Devise.objects.get_or_create(
                code=devise_data["code"],
                defaults=devise_data,
            )
            if created:
                self.stdout.write(f"  ✓ Devise créée : {devise_data['code']} - {devise_data['nom']}")
                created_count += 1
            else:
                self.stdout.write(f"  · Devise existante : {devise_data['code']}")

        if created_count:
            self.stdout.write(self.style.SUCCESS(f"{created_count} devise(s) créée(s)."))
        else:
            self.stdout.write(self.style.SUCCESS("Toutes les devises existent déjà."))

        # Mettre à jour les taux via SNB pour les devises supportées
        self.stdout.write("Mise à jour des taux de change via SNB...")
        try:
            result = SNBExchangeRateService.update_devise_rates()
            if result.get("updated"):
                for u in result["updated"]:
                    self.stdout.write(f"  ✓ Taux {u['code']}: {u['rate']} ({u['date']})")
            if result.get("errors"):
                for err in result["errors"]:
                    self.stdout.write(self.style.WARNING(f"  ⚠ {err}"))
            if not result.get("updated") and not result.get("errors"):
                self.stdout.write("  · Aucun taux mis à jour")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ Mise à jour SNB échouée: {e} (les taux seront mis à jour au prochain cycle)"))
