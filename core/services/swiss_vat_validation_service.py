# core/services/swiss_vat_validation_service.py
"""
Service de validation des numeros de TVA suisses via UID Register.

Utilise l'API SOAP UID-WSE (uid-wse.admin.ch) pour valider les numeros
TVA suisses (CHE-XXX.XXX.XXX MWST/TVA/IVA).

API gratuite, sans authentification.
"""
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

UID_WSE_ENDPOINT = 'https://www.uid-wse.admin.ch/V3.0/PublicServices.svc'
CACHE_KEY_PREFIX = 'swiss_vat'
CACHE_TTL_VALID = 86400    # 24h pour resultats valides
CACHE_TTL_INVALID = 3600   # 1h pour resultats invalides

VALIDATE_SOAP_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:uid="http://www.uid.admin.ch/xmlns/uid-wse">
  <soap:Body>
    <uid:ValidateVatNumber>
      <uid:vatNumber>{vat_number}</uid:vatNumber>
    </uid:ValidateVatNumber>
  </soap:Body>
</soap:Envelope>"""

VALIDATE_SOAP_ACTION = (
    '"http://www.uid.admin.ch/xmlns/uid-wse/IPublicServices/ValidateVatNumber"'
)


@dataclass
class SwissVatResult:
    valid: bool
    uid: str
    vat_number: str
    name: Optional[str] = None
    address: Optional[str] = None
    error: Optional[str] = None


class SwissVatValidationService:
    """Service pour valider les numeros de TVA suisses via UID Register."""

    @staticmethod
    def _normalize_vat_number(raw):
        """
        Normalise un numero TVA suisse vers le format CHE-XXX.XXX.XXX.

        Accepte: CHE-175.923.751, CHE175923751, CHE-175923751,
                 CHE-175.923.751 MWST, CHE-175.923.751 TVA, 175923751
        """
        cleaned = re.sub(r'\s*(MWST|TVA|IVA)\s*$', '', raw.strip(), flags=re.IGNORECASE)
        digits = re.sub(r'[^0-9]', '', cleaned)
        if len(digits) != 9:
            return None
        return f"CHE-{digits[:3]}.{digits[3:6]}.{digits[6:]}"

    @staticmethod
    def validate(raw_vat_number):
        """
        Valide un numero de TVA suisse via UID-WSE SOAP.

        Si valide, enrichit le resultat avec nom et adresse via GetByUID.

        Args:
            raw_vat_number: Numero TVA (CHE-XXX.XXX.XXX, CHE123456789, etc.)

        Returns:
            SwissVatResult
        """
        formatted = SwissVatValidationService._normalize_vat_number(raw_vat_number)
        if not formatted:
            return SwissVatResult(
                valid=False,
                uid='',
                vat_number=raw_vat_number,
                error="Format de numero TVA suisse invalide (9 chiffres attendus)",
            )

        digits = re.sub(r'[^0-9]', '', formatted)

        cache_key = f"{CACHE_KEY_PREFIX}:{digits}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Etape 1 : ValidateVatNumber
        soap_body = VALIDATE_SOAP_TEMPLATE.format(vat_number=formatted)

        try:
            response = requests.post(
                UID_WSE_ENDPOINT,
                data=soap_body.encode('utf-8'),
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': VALIDATE_SOAP_ACTION,
                },
                timeout=15,
            )
            response.raise_for_status()

            valid = SwissVatValidationService._parse_validate_response(response.text)

        except requests.RequestException as e:
            logger.error("Erreur UID-WSE ValidateVatNumber: %s", e)
            return SwissVatResult(
                valid=False,
                uid=digits,
                vat_number=formatted,
                error=f"Erreur de connexion UID Register: {e}",
            )

        if not valid:
            result = SwissVatResult(
                valid=False,
                uid=digits,
                vat_number=formatted,
                error="Numero TVA suisse non valide ou non assujetti",
            )
            cache.set(cache_key, result, CACHE_TTL_INVALID)
            return result

        # Etape 2 : enrichir avec GetByUID (nom, adresse)
        name = None
        address = None
        try:
            from .swiss_companies_service import SwissCompaniesService
            company = SwissCompaniesService.get_by_uid(digits)
            if company:
                name = company.name
                parts = []
                if company.address_street:
                    street = company.address_street
                    if company.address_number:
                        street += f" {company.address_number}"
                    parts.append(street)
                if company.address_postal_code or company.address_city:
                    parts.append(
                        f"{company.address_postal_code or ''} {company.address_city or ''}".strip()
                    )
                address = ', '.join(parts) if parts else None
        except Exception as e:
            logger.warning("Erreur enrichissement GetByUID pour %s: %s", formatted, e)

        result = SwissVatResult(
            valid=True,
            uid=digits,
            vat_number=formatted,
            name=name,
            address=address,
        )
        cache.set(cache_key, result, CACHE_TTL_VALID)
        return result

    @staticmethod
    def _parse_validate_response(xml_text):
        """Parse la reponse SOAP ValidateVatNumber. Retourne True/False."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error("Reponse UID-WSE invalide: %s", e)
            return False

        # Chercher le fault SOAP d'abord
        fault = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
        if fault is not None:
            fault_string = fault.findtext('faultstring', '')
            logger.error("UID-WSE SOAP fault: %s", fault_string)
            return False

        # Chercher ValidateVatNumberResult dans le namespace uid-wse
        ns_uid = 'http://www.uid.admin.ch/xmlns/uid-wse'
        elem = root.find(f'.//{{{ns_uid}}}ValidateVatNumberResult')
        if elem is not None and elem.text:
            return elem.text.strip().lower() == 'true'

        return False
