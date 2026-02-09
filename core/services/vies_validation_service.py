# core/services/vies_validation_service.py
"""
Service de validation des numeros de TVA europeens via VIES.

VIES (VAT Information Exchange System) est le systeme de la Commission
Europeenne pour verifier la validite des numeros de TVA.

API SOAP gratuite, sans authentification.
"""
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

VIES_ENDPOINT = 'https://ec.europa.eu/taxation_customs/vies/services/checkVatService'
CACHE_KEY_PREFIX = 'vies_vat'
CACHE_TTL_VALID = 86400    # 24h pour resultats valides
CACHE_TTL_INVALID = 3600   # 1h pour resultats invalides

# Pays membres UE + XI (Irlande du Nord)
EU_COUNTRIES = {
    'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'EL', 'ES',
    'FI', 'FR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT',
    'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK', 'XI',
}

SOAP_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:urn="urn:ec.europa.eu:taxud:vies:services:checkVat:types">
    <soapenv:Body>
        <urn:checkVat>
            <urn:countryCode>{country_code}</urn:countryCode>
            <urn:vatNumber>{vat_number}</urn:vatNumber>
        </urn:checkVat>
    </soapenv:Body>
</soapenv:Envelope>"""


@dataclass
class ViesResult:
    valid: bool
    country_code: str
    vat_number: str
    name: Optional[str] = None
    address: Optional[str] = None
    request_date: Optional[date] = None
    error: Optional[str] = None


class ViesValidationService:
    """Service pour valider les numeros de TVA via VIES."""

    @staticmethod
    def validate_vat(country_code, vat_number):
        """
        Valide un numero de TVA via VIES SOAP.

        Args:
            country_code: Code pays (2 lettres, ex: 'FR', 'DE')
            vat_number: Numero de TVA sans prefixe pays

        Returns:
            ViesResult
        """
        country_code = country_code.upper().strip()
        vat_number = re.sub(r'[\s.\-]', '', vat_number).strip()

        if country_code not in EU_COUNTRIES:
            return ViesResult(
                valid=False,
                country_code=country_code,
                vat_number=vat_number,
                error=f"Code pays '{country_code}' non reconnu (pays UE + XI uniquement)",
            )

        cache_key = f"{CACHE_KEY_PREFIX}:{country_code}:{vat_number}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        soap_body = SOAP_TEMPLATE.format(
            country_code=country_code,
            vat_number=vat_number,
        )

        try:
            response = requests.post(
                VIES_ENDPOINT,
                data=soap_body.encode('utf-8'),
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': '',
                },
                timeout=15,
            )
            response.raise_for_status()
            result = ViesValidationService._parse_soap_response(
                response.text, country_code, vat_number
            )

            ttl = CACHE_TTL_VALID if result.valid else CACHE_TTL_INVALID
            cache.set(cache_key, result, ttl)
            return result

        except requests.RequestException as e:
            logger.error("Erreur VIES: %s", e)
            return ViesResult(
                valid=False,
                country_code=country_code,
                vat_number=vat_number,
                error=f"Erreur de connexion VIES: {e}",
            )

    @staticmethod
    def validate_full_number(full_vat_number):
        """
        Valide un numero de TVA complet (ex: 'FR40303265045', 'DE123456789').

        Parse automatiquement le prefixe pays.
        """
        cleaned = re.sub(r'[\s.\-]', '', full_vat_number).strip().upper()

        if len(cleaned) < 4:
            return ViesResult(
                valid=False,
                country_code='',
                vat_number=cleaned,
                error="Numero de TVA trop court",
            )

        # Extraire le code pays (2 premiers caracteres)
        country_code = cleaned[:2]
        vat_number = cleaned[2:]

        # Cas special: EL (Grece) utilise parfois GR
        if country_code == 'GR':
            country_code = 'EL'

        return ViesValidationService.validate_vat(country_code, vat_number)

    @staticmethod
    def _parse_soap_response(xml_text, country_code, vat_number):
        """Parse la reponse SOAP VIES."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return ViesResult(
                valid=False,
                country_code=country_code,
                vat_number=vat_number,
                error=f"Reponse VIES invalide: {e}",
            )

        # Chercher les elements dans tous les namespaces
        ns_vies = 'urn:ec.europa.eu:taxud:vies:services:checkVat:types'

        def find_text(tag):
            elem = root.find(f'.//{{{ns_vies}}}{tag}')
            if elem is not None and elem.text:
                text = elem.text.strip()
                return text if text != '---' else None
            return None

        valid_str = find_text('valid')
        valid = valid_str == 'true' if valid_str else False

        name = find_text('name')
        address = find_text('address')
        request_date_str = find_text('requestDate')

        request_date = None
        if request_date_str:
            try:
                request_date = datetime.strptime(request_date_str[:10], '%Y-%m-%d').date()
            except ValueError:
                pass

        # Verifier les faults SOAP
        fault = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
        if fault is not None:
            fault_string = fault.findtext('faultstring', '')
            return ViesResult(
                valid=False,
                country_code=country_code,
                vat_number=vat_number,
                error=f"VIES fault: {fault_string}",
            )

        return ViesResult(
            valid=valid,
            country_code=country_code,
            vat_number=vat_number,
            name=name,
            address=address,
            request_date=request_date or date.today(),
        )
