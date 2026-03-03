# core/services/snb_exchange_rate_service.py
"""
Service de recuperation des taux de change.

Sources (par priorite):
1. Frankfurter API (https://api.frankfurter.dev) - taux journaliers BCE, gratuit, sans auth
2. SNB/BNS (https://data.snb.ch) - moyennes mensuelles officielles suisses, gratuit, sans auth

Le XOF est un taux fixe (1 EUR = 655.957 XOF), calcule a partir du taux EUR.
"""
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Taux fixe XOF/EUR (parite CFA)
XOF_PER_EUR = Decimal('655.957')

# Mapping des codes devise AltiusOne -> codes SNB
# La SNB utilise des suffixes indiquant l'unite (EUR1 = 1 EUR, JPY100 = 100 JPY)
# La valeur retournee = combien de CHF pour N unites de la devise
SNB_CURRENCY_MAP = {
    'EUR': ('EUR1', 1),
    'USD': ('USD1', 1),
    'GBP': ('GBP1', 1),
    'JPY': ('JPY100', 100),
    'CAD': ('CAD1', 1),
    'SEK': ('SEK100', 100),
    'NOK': ('NOK100', 100),
    'DKK': ('DKK100', 100),
    'AUD': ('AUD1', 1),
    'CNY': ('CNY100', 100),
}

SNB_API_URL = 'https://data.snb.ch/api/cube/devkum/data/csv/en'
CACHE_KEY_PREFIX = 'snb_rates'
CACHE_TTL = 3600  # 1 heure


@dataclass
class ExchangeRate:
    currency: str
    rate: Decimal
    date: date
    base_currency: str = 'CHF'


@dataclass
class ExchangeRateResult:
    rates: list = field(default_factory=list)
    fetch_date: Optional[date] = None
    source: str = 'SNB'
    error: Optional[str] = None


class SNBExchangeRateService:
    """Service pour recuperer les taux de change depuis la BNS."""

    @staticmethod
    def fetch_rates_frankfurter():
        """
        Recupere les taux journaliers depuis Frankfurter API (source BCE).
        Gratuit, sans authentification, taux mis a jour quotidiennement.

        Returns:
            ExchangeRateResult avec les taux ou une erreur
        """
        cache_key = f"frankfurter_rates:{date.today().isoformat()}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(
                'https://api.frankfurter.dev/v1/latest',
                params={'base': 'CHF'},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            result = ExchangeRateResult(
                fetch_date=date.fromisoformat(data['date']),
                source='Frankfurter/BCE',
            )

            for currency, rate_value in data.get('rates', {}).items():
                result.rates.append(ExchangeRate(
                    currency=currency,
                    rate=Decimal(str(rate_value)).quantize(Decimal('0.000001')),
                    date=result.fetch_date,
                ))

            # Calculer XOF depuis EUR (parite fixe 1 EUR = 655.957 XOF)
            eur_rate = data.get('rates', {}).get('EUR')
            if eur_rate:
                xof_rate = (Decimal(str(eur_rate)) * XOF_PER_EUR).quantize(Decimal('0.000001'))
                result.rates.append(ExchangeRate(
                    currency='XOF',
                    rate=xof_rate,
                    date=result.fetch_date,
                ))

            if result.rates:
                cache.set(cache_key, result, CACHE_TTL)
            else:
                result.error = "Aucun taux retourne par Frankfurter"

            return result

        except requests.RequestException as e:
            logger.warning("Frankfurter API indisponible: %s", e)
            return ExchangeRateResult(error=f"Erreur Frankfurter: {e}")
        except (ValueError, KeyError) as e:
            logger.warning("Reponse Frankfurter invalide: %s", e)
            return ExchangeRateResult(error=f"Reponse Frankfurter invalide: {e}")

    @staticmethod
    def fetch_rates(target_date=None, currencies=None):
        """
        Recupere les taux de change depuis l'API SNB.

        L'API fournit des moyennes mensuelles. La date est arrondie au mois.
        Si le mois courant n'a pas de donnees, tente le mois precedent.

        Args:
            target_date: Date cible (defaut: aujourd'hui). Arrondie au mois.
            currencies: Liste de codes devise (defaut: toutes les devises mappees)

        Returns:
            ExchangeRateResult avec les taux ou une erreur
        """
        if target_date is None:
            target_date = date.today()

        if currencies is None:
            currencies = list(SNB_CURRENCY_MAP.keys())

        result = SNBExchangeRateService._fetch_snb_month(target_date, currencies)

        # Fallback au mois precedent si le mois courant n'a pas de donnees
        if result.error and not result.rates:
            if target_date.month == 1:
                prev_date = date(target_date.year - 1, 12, 1)
            else:
                prev_date = date(target_date.year, target_date.month - 1, 1)
            logger.info("SNB: pas de donnees pour %s, essai %s",
                        target_date.strftime('%Y-%m'), prev_date.strftime('%Y-%m'))
            result = SNBExchangeRateService._fetch_snb_month(prev_date, currencies)

        return result

    @staticmethod
    def _fetch_snb_month(target_date, currencies):
        """Fetch SNB rates for a specific month."""
        month_str = target_date.strftime('%Y-%m')

        cache_key = f"{CACHE_KEY_PREFIX}:{month_str}:{','.join(sorted(currencies))}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        snb_codes = []
        for curr in currencies:
            if curr in SNB_CURRENCY_MAP:
                snb_codes.append(SNB_CURRENCY_MAP[curr][0])

        if not snb_codes:
            return ExchangeRateResult(error="Aucune devise reconnue")

        dim_sel = f"D1({','.join(snb_codes)})"
        params = {
            'dimSel': dim_sel,
            'fromDate': month_str,
            'toDate': month_str,
        }

        try:
            response = requests.get(SNB_API_URL, params=params, timeout=15)
            response.raise_for_status()
            result = SNBExchangeRateService._parse_csv_response(
                response.text, target_date, currencies
            )
            if not result.error:
                cache.set(cache_key, result, CACHE_TTL)
            return result

        except requests.RequestException as e:
            logger.error("Erreur API SNB: %s", e)
            return ExchangeRateResult(error=f"Erreur de connexion SNB: {e}")

    @staticmethod
    def _parse_csv_response(csv_text, target_date, currencies=None):
        """
        Parse la reponse CSV de la SNB.

        Format vertical (une ligne par devise):
        "Date";"D0";"D1";"Value"
        "2025-01";"M0";"EUR1";"0.94162"
        "2025-01";"M0";"USD1";"0.90933"
        ...

        D0=M0 (mensuel), D1=code devise SNB, Value=CHF par unite(s)
        """
        result = ExchangeRateResult(fetch_date=target_date)

        # Inverser le mapping SNB -> devise
        snb_to_currency = {}
        for curr, (snb_code, divisor) in SNB_CURRENCY_MAP.items():
            snb_to_currency[snb_code] = (curr, divisor)

        lines = csv_text.strip().split('\n')

        # Trouver la ligne d'en-tete des donnees
        data_start = None
        for i, line in enumerate(lines):
            cleaned = line.strip().strip('"')
            if cleaned.startswith('Date') or cleaned.startswith('"Date"'):
                data_start = i + 1
                break

        if data_start is None or data_start >= len(lines):
            result.error = "Format CSV SNB non reconnu"
            return result

        # Parser les lignes de donnees
        for line in lines[data_start:]:
            parts = [p.strip().strip('"') for p in line.split(';')]
            if len(parts) < 4:
                continue

            date_str = parts[0]  # ex: "2025-01"
            # D0 = parts[1]  # M0 (mensuel)
            d1_code = parts[2]  # ex: EUR1
            value_str = parts[3]  # ex: 0.94162

            if d1_code not in snb_to_currency:
                continue

            currency, divisor = snb_to_currency[d1_code]
            if currencies and currency not in currencies:
                continue

            if not value_str or value_str == '-':
                continue

            try:
                # Value = combien de CHF pour `divisor` unites de la devise
                # Ex: EUR1 = 0.94162 signifie 1 EUR = 0.94162 CHF
                # Pour le modele Devise: taux_change = 1 CHF = X devise
                # Donc rate = divisor / value
                chf_per_unit = Decimal(value_str)
                rate = (Decimal(divisor) / chf_per_unit).quantize(Decimal('0.000001'))

                # Parser la date mensuelle en date du 1er du mois
                try:
                    rate_date = date(int(date_str[:4]), int(date_str[5:7]), 1)
                except (ValueError, IndexError):
                    rate_date = target_date

                result.rates.append(ExchangeRate(
                    currency=currency,
                    rate=rate,
                    date=rate_date,
                ))
            except (InvalidOperation, ArithmeticError):
                logger.warning("Taux invalide pour %s: %s", d1_code, value_str)

        if not result.rates:
            result.error = f"Aucun taux disponible pour {target_date.strftime('%Y-%m')}"

        return result

    @staticmethod
    def update_devise_rates(target_date=None):
        """
        Met a jour les taux de change dans le modele Devise.

        Essaie Frankfurter (taux journaliers BCE) d'abord,
        puis SNB (moyennes mensuelles) en fallback.

        Returns:
            dict avec 'updated', 'errors', 'date', 'source'
        """
        # 1) Essayer Frankfurter (taux journaliers)
        result = SNBExchangeRateService.fetch_rates_frankfurter()

        # 2) Fallback SNB si Frankfurter echoue
        if result.error or not result.rates:
            logger.info("Frankfurter indisponible (%s), fallback SNB", result.error)
            result = SNBExchangeRateService.fetch_rates(target_date=target_date)

        if result.error:
            return {'updated': [], 'errors': [result.error], 'date': str(target_date)}

        from core.models import Devise

        updated = []
        errors = []

        for rate in result.rates:
            try:
                devise = Devise.objects.get(code=rate.currency, actif=True)
                devise.taux_change = rate.rate
                devise.date_taux = rate.date
                devise.save(update_fields=['taux_change', 'date_taux'])
                updated.append({
                    'code': rate.currency,
                    'rate': str(rate.rate),
                    'date': str(rate.date),
                })
            except Devise.DoesNotExist:
                logger.debug("Devise %s non trouvee ou inactive", rate.currency)
            except Exception as e:
                errors.append(f"{rate.currency}: {e}")

        return {
            'updated': updated,
            'errors': errors,
            'date': str(result.fetch_date),
            'source': result.source,
        }
