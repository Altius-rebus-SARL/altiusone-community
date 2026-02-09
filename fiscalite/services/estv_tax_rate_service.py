# fiscalite/services/estv_tax_rate_service.py
"""
Service de recuperation des taux d'imposition depuis l'ESTV
(Administration federale des contributions).

API non-documentee du calculateur d'impot suisse.
Parsing defensif avec stockage des donnees brutes pour debug.
"""
import csv
import io
import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

ESTV_API_URL = 'https://swisstaxcalculator.estv.admin.ch/delegate/ost-integration/v1/lg-proxy/operation/'
CACHE_KEY_PREFIX = 'estv_rates'
CACHE_TTL = 86400  # 24h


@dataclass
class EstvTaxRates:
    canton: str = ''
    commune: str = ''
    commune_bfs_nr: int = 0
    year: int = 0
    federal_rate: Optional[Decimal] = None
    cantonal_rate: Optional[Decimal] = None
    communal_rate: Optional[Decimal] = None
    multiplicateurs: dict = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)
    error: Optional[str] = None


class EstvTaxRateService:
    """Service pour recuperer les taux d'imposition depuis l'ESTV."""

    @staticmethod
    def fetch_tax_rates(canton, commune_bfs_nr, year):
        """
        Recupere les taux d'imposition depuis l'API ESTV.

        Args:
            canton: Code canton (2 lettres, ex: 'ZH')
            commune_bfs_nr: Numero BFS de la commune
            year: Annee fiscale

        Returns:
            EstvTaxRates
        """
        cache_key = f"{CACHE_KEY_PREFIX}:{canton}:{commune_bfs_nr}:{year}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        payload = {
            'canton': canton.upper(),
            'bfsNr': int(commune_bfs_nr),
            'taxYear': int(year),
        }

        try:
            response = requests.post(ESTV_API_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            result = EstvTaxRateService._parse_api_response(
                data, canton, commune_bfs_nr, year
            )
            if not result.error:
                cache.set(cache_key, result, CACHE_TTL)
            return result

        except requests.RequestException as e:
            logger.error("Erreur API ESTV: %s", e)
            return EstvTaxRates(
                canton=canton,
                commune_bfs_nr=commune_bfs_nr,
                year=year,
                error=f"Erreur de connexion ESTV: {e}",
            )
        except (ValueError, KeyError) as e:
            logger.error("Erreur parsing ESTV: %s", e)
            return EstvTaxRates(
                canton=canton,
                commune_bfs_nr=commune_bfs_nr,
                year=year,
                error=f"Erreur de parsing ESTV: {e}",
            )

    @staticmethod
    def _parse_api_response(data, canton, commune_bfs_nr, year):
        """
        Parse defensif de la reponse API ESTV.

        L'API n'etant pas documentee, on stocke raw_data pour debug.
        """
        result = EstvTaxRates(
            canton=canton,
            commune_bfs_nr=commune_bfs_nr,
            year=year,
            raw_data=data,
        )

        def safe_decimal(val):
            if val is None:
                return None
            try:
                return Decimal(str(val))
            except (InvalidOperation, TypeError):
                return None

        # Parsing defensif: plusieurs structures possibles
        if isinstance(data, dict):
            # Nom de commune
            result.commune = data.get('municipalityName', data.get('commune', ''))

            # Taux federaux
            result.federal_rate = safe_decimal(
                data.get('federalTaxRate', data.get('tauxFederal'))
            )

            # Taux cantonaux
            result.cantonal_rate = safe_decimal(
                data.get('cantonalTaxRate', data.get('tauxCantonal'))
            )

            # Taux communaux
            result.communal_rate = safe_decimal(
                data.get('communalTaxRate', data.get('tauxCommunal'))
            )

            # Multiplicateurs
            mult_cantonal = safe_decimal(
                data.get('cantonalMultiplier',
                         data.get('multiplicateurCantonal',
                                  data.get('cantonalCoefficient')))
            )
            mult_communal = safe_decimal(
                data.get('communalMultiplier',
                         data.get('multiplicateurCommunal',
                                  data.get('communalCoefficient')))
            )
            mult_church = safe_decimal(
                data.get('churchMultiplier',
                         data.get('multiplicateurEcclesiastique'))
            )

            result.multiplicateurs = {
                'cantonal': str(mult_cantonal) if mult_cantonal else None,
                'communal': str(mult_communal) if mult_communal else None,
                'ecclesiastique': str(mult_church) if mult_church else None,
            }

            # Sous-structure "taxes" si presente
            taxes = data.get('taxes', data.get('results', []))
            if isinstance(taxes, list):
                for tax in taxes:
                    if not isinstance(tax, dict):
                        continue
                    tax_type = tax.get('type', tax.get('taxType', ''))
                    rate = safe_decimal(tax.get('rate', tax.get('taux')))
                    if 'federal' in str(tax_type).lower() and rate:
                        result.federal_rate = rate
                    elif 'cantonal' in str(tax_type).lower() and rate:
                        result.cantonal_rate = rate
                    elif 'communal' in str(tax_type).lower() and rate:
                        result.communal_rate = rate

        return result

    @staticmethod
    def populate_taux_imposition(canton, commune_bfs_nr, year, commune_name=None):
        """
        Cree/met a jour les enregistrements TauxImposition.

        Returns:
            dict avec 'created', 'updated', 'errors'
        """
        from fiscalite.models import TauxImposition

        rates = EstvTaxRateService.fetch_tax_rates(canton, commune_bfs_nr, year)
        if rates.error:
            return {'created': 0, 'updated': 0, 'errors': [rates.error]}

        commune = commune_name or rates.commune or str(commune_bfs_nr)
        created = 0
        updated = 0
        errors = []

        # Mapping: type_impot -> (taux, mult_cantonal, mult_communal)
        entries = []
        if rates.federal_rate is not None:
            entries.append(('IFD_BENEFICE', rates.federal_rate, None, None))
        if rates.cantonal_rate is not None:
            mult_c = None
            mult_m = None
            if rates.multiplicateurs.get('cantonal'):
                try:
                    mult_c = Decimal(rates.multiplicateurs['cantonal'])
                except InvalidOperation:
                    pass
            if rates.multiplicateurs.get('communal'):
                try:
                    mult_m = Decimal(rates.multiplicateurs['communal'])
                except InvalidOperation:
                    pass
            entries.append(('ICC_BENEFICE', rates.cantonal_rate, mult_c, mult_m))
        if rates.communal_rate is not None:
            entries.append(('ICC_CAPITAL', rates.communal_rate, None, None))

        for type_impot, taux, mult_cant, mult_comm in entries:
            try:
                obj, was_created = TauxImposition.objects.update_or_create(
                    canton=canton,
                    commune=commune,
                    type_impot=type_impot,
                    annee=year,
                    defaults={
                        'taux_fixe': taux,
                        'multiplicateur_cantonal': mult_cant,
                        'multiplicateur_communal': mult_comm,
                        'actif': True,
                    }
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors.append(f"{type_impot}: {e}")

        return {
            'created': created,
            'updated': updated,
            'errors': errors,
            'commune': commune,
            'canton': canton,
            'year': year,
        }

    @staticmethod
    def import_from_csv(csv_content, year):
        """
        Import de taux d'imposition depuis un fichier CSV (fallback).

        Format CSV attendu (point-virgule):
        canton;commune;bfs_nr;type_impot;taux_fixe;mult_cantonal;mult_communal

        Returns:
            dict avec 'created', 'updated', 'errors'
        """
        from fiscalite.models import TauxImposition

        if isinstance(csv_content, bytes):
            csv_content = csv_content.decode('utf-8-sig')

        reader = csv.DictReader(
            io.StringIO(csv_content),
            delimiter=';',
        )

        created = 0
        updated = 0
        errors = []
        row_num = 0

        for row in reader:
            row_num += 1
            try:
                canton = row.get('canton', '').strip().upper()
                commune = row.get('commune', '').strip()
                type_impot = row.get('type_impot', '').strip()

                if not canton or not type_impot:
                    errors.append(f"Ligne {row_num}: canton ou type_impot manquant")
                    continue

                def parse_decimal(val):
                    val = val.strip() if val else ''
                    if not val:
                        return None
                    try:
                        return Decimal(val)
                    except InvalidOperation:
                        return None

                taux_fixe = parse_decimal(row.get('taux_fixe', ''))
                mult_cantonal = parse_decimal(row.get('mult_cantonal', ''))
                mult_communal = parse_decimal(row.get('mult_communal', ''))

                obj, was_created = TauxImposition.objects.update_or_create(
                    canton=canton,
                    commune=commune,
                    type_impot=type_impot,
                    annee=year,
                    defaults={
                        'taux_fixe': taux_fixe,
                        'multiplicateur_cantonal': mult_cantonal,
                        'multiplicateur_communal': mult_communal,
                        'actif': True,
                    }
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errors.append(f"Ligne {row_num}: {e}")

        return {
            'created': created,
            'updated': updated,
            'errors': errors,
            'total_rows': row_num,
        }
