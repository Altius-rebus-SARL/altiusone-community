# core/services/swiss_companies_service.py
"""
Service for searching Swiss companies via OpenData Altius API.

Endpoint: https://opendata.altius-group.ch/economics/swissenterprise/api/v1/companies/
778,882+ Swiss companies with full details (name, UID, address, legal form, canton).
"""
import logging
import requests
from dataclasses import dataclass
from typing import Optional
from django.core.cache import cache
from django.utils.translation import get_language

logger = logging.getLogger(__name__)

OPENDATA_ENDPOINT = "https://opendata.altius-group.ch/economics/swissenterprise/api/v1/companies/"
OPENDATA_TOKEN = "e67d0b6796a8f0f7cf3a1aa516c90177ff13441d"
CACHE_TIMEOUT = 3600

# Map legal form names (FR) to internal codes
LEGAL_FORM_NAME_MAP = {
    "entreprise individuelle": "EI",
    "einzelunternehmen": "EI",
    "ditta individuale": "EI",
    "société en nom collectif": "SNC",
    "kollektivgesellschaft": "SNC",
    "società in nome collettivo": "SNC",
    "société en commandite": "SC",
    "kommanditgesellschaft": "SC",
    "società in accomandita": "SC",
    "société anonyme": "SA",
    "aktiengesellschaft": "SA",
    "società anonima": "SA",
    "société à responsabilité limitée": "SARL",
    "gesellschaft mit beschränkter haftung": "SARL",
    "società a garanzia limitata": "SARL",
    "société coopérative": "COOP",
    "genossenschaft": "COOP",
    "società cooperativa": "COOP",
    "association": "ASSOC",
    "verein": "ASSOC",
    "associazione": "ASSOC",
    "fondation": "FOND",
    "stiftung": "FOND",
    "fondazione": "FOND",
}

# Supported languages
LANGS = {"fr", "de", "it"}


def _get_lang() -> str:
    lang = (get_language() or "fr")[:2]
    return lang if lang in LANGS else "fr"


@dataclass
class SwissCompany:
    """Represents a Swiss company from the OpenData registry."""
    uid: str
    name: str
    legal_form: str
    legal_form_code: str
    legal_seat: str
    canton: str
    status: str
    ch_id: str = ""
    ofrc_id: str = ""
    address_street: Optional[str] = None
    address_number: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_city: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'uid': self.uid,
            'ide_number': self.format_ide(),
            'name': self.name,
            'legal_form': self.legal_form,
            'legal_form_code': self.legal_form_code,
            'legal_seat': self.legal_seat,
            'canton': self.canton,
            'status': self.status,
            'ch_id': self.ch_id,
            'ofrc_id': self.ofrc_id,
            'address': {
                'street': self.address_street,
                'number': self.address_number,
                'postal_code': self.address_postal_code,
                'city': self.address_city,
            } if self.address_street or self.address_city else None,
        }

    def format_ide(self) -> str:
        if self.uid and len(self.uid) == 9 and self.uid.isdigit():
            return f"CHE-{self.uid[:3]}.{self.uid[3:6]}.{self.uid[6:]}"
        return self.uid

    def format_ch_id(self) -> str:
        if self.ch_id and len(self.ch_id) >= 12:
            ch = self.ch_id.replace("CH", "")
            if len(ch) >= 10:
                return f"CH-{ch[:3]}-{ch[3:10]}-{ch[10:]}"
        return self.ch_id


def _legal_form_code(name_fr: str, name_de: str = "", name_it: str = "") -> str:
    """Map a legal form name to our internal code."""
    for name in (name_fr, name_de, name_it):
        if name:
            code = LEGAL_FORM_NAME_MAP.get(name.lower().strip())
            if code:
                return code
    return ""


def _parse_company(item: dict) -> SwissCompany:
    """Parse an OpenData API company item into a SwissCompany."""
    lang = _get_lang()
    legal_form_field = f"legal_form_name_{lang}"
    legal_form = item.get(legal_form_field, "") or item.get("legal_form_name_fr", "")

    code = _legal_form_code(
        item.get("legal_form_name_fr", ""),
        item.get("legal_form_name_de", ""),
        item.get("legal_form_name_it", ""),
    )

    uid_raw = str(item.get("uid", ""))
    # API returns uid as "CHE109667576" — extract 9-digit number
    uid_clean = uid_raw.replace("CHE", "").replace("-", "").replace(".", "").replace(" ", "")

    return SwissCompany(
        uid=uid_clean,
        name=item.get("legal_name", ""),
        legal_form=legal_form,
        legal_form_code=code,
        legal_seat=item.get("city", ""),
        canton=item.get("canton_code", ""),
        status="active",
        address_street=item.get("street") or None,
        address_postal_code=item.get("postal_code") or None,
        address_city=item.get("city") or None,
    )


class SwissCompaniesService:
    """Service to search Swiss companies using OpenData Altius API."""

    @classmethod
    def _api_request(cls, params: dict, timeout: int = 10) -> Optional[dict]:
        response = requests.get(
            OPENDATA_ENDPOINT,
            params=params,
            headers={
                "Authorization": f"Token {OPENDATA_TOKEN}",
                "Accept": "application/json",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    @classmethod
    def search(cls, search_term: str, limit: int = 10) -> list[SwissCompany]:
        """Search for Swiss companies by name."""
        if not search_term or len(search_term) < 3:
            return []

        safe_term = search_term.lower().replace(" ", "_")[:50]
        cache_key = f"swiss_search:{safe_term}:{limit}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        try:
            data = cls._api_request({
                "search": search_term,
                "page_size": limit,
            })
            results_list = data.get("results", [])
            results = [_parse_company(item) for item in results_list]

            try:
                cache.set(cache_key, results, CACHE_TIMEOUT)
            except Exception:
                pass

            return results

        except requests.RequestException as e:
            logger.error("OpenData API error: %s", e)
            return []
        except (KeyError, ValueError) as e:
            logger.error("Error parsing OpenData response: %s", e)
            return []

    @classmethod
    def get_by_uid(cls, uid: str) -> Optional[SwissCompany]:
        """Get a specific company by UID."""
        clean_uid = uid.replace("CHE-", "").replace("CHE", "").replace(".", "").replace(" ", "")

        if not clean_uid or len(clean_uid) != 9 or not clean_uid.isdigit():
            return None

        cache_key = f"swiss_uid:{clean_uid}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        try:
            data = cls._api_request({"search": clean_uid, "page_size": 1})
            results_list = data.get("results", [])
            if not results_list:
                return None

            company = _parse_company(results_list[0])
            # Verify the UID matches
            if company.uid != clean_uid:
                return None

            try:
                cache.set(cache_key, company, CACHE_TIMEOUT)
            except Exception:
                pass

            return company

        except requests.RequestException as e:
            logger.error("OpenData API error: %s", e)
            return None
        except (KeyError, ValueError) as e:
            logger.error("Error parsing OpenData response: %s", e)
            return None
