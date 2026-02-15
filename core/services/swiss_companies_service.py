# core/services/swiss_companies_service.py
"""
Service for searching Swiss companies via Zefix.

Two backends:
1. Zefix PublicREST API (complete: 700k+ companies, requires credentials)
   Credentials: request free access at zefix@bj.admin.ch
   Docs: https://www.zefix.admin.ch/ZefixPublicREST/swagger-ui/index.html
2. LINDAS SPARQL (fallback: ~30k companies, no auth needed)

Set ZEFIX_USERNAME and ZEFIX_PASSWORD in environment to use the full API.
"""
import logging
import unicodedata
import requests
from dataclasses import dataclass
from typing import Optional
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import get_language

logger = logging.getLogger(__name__)

# Zefix PublicREST API (complete dataset)
ZEFIX_API_URL = "https://www.zefix.admin.ch/ZefixPublicREST/api/v1"

# LINDAS SPARQL endpoint (fallback, ~30k companies only)
LINDAS_ENDPOINT = "https://register.ld.admin.ch/query/"

CACHE_TIMEOUT = 3600
ZEFIX_LANGUAGES = {"fr", "de", "it"}


def _get_zefix_lang() -> str:
    lang = (get_language() or "fr")[:2]
    return lang if lang in ZEFIX_LANGUAGES else "fr"


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def _has_zefix_credentials() -> bool:
    return bool(
        getattr(settings, "ZEFIX_USERNAME", None)
        and getattr(settings, "ZEFIX_PASSWORD", None)
    )


# SPARQL accent normalization chain
_SPARQL_NORMALIZE = (
    'REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE('
    'LCASE(?name),'
    '"[éèêë]","e"),'
    '"[àâäã]","a"),'
    '"[ùûü]","u"),'
    '"[îïì]","i"),'
    '"[ôöò]","o"),'
    '"[ç]","c")'
)


@dataclass
class SwissCompany:
    """Represents a Swiss company from the Zefix registry."""
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


# =============================================================================
# ZEFIX REST API BACKEND (complete, requires credentials)
# =============================================================================

class _ZefixRestBackend:
    """Backend using the official Zefix PublicREST API (700k+ companies)."""

    # Legal form code mapping from Zefix API numeric codes
    LEGAL_FORM_MAP = {
        "0101": "Entreprise individuelle",
        "0103": "Société en nom collectif",
        "0104": "Société en commandite",
        "0105": "Société en commandite par actions",
        "0106": "Société anonyme",
        "0107": "Société à responsabilité limitée",
        "0108": "Société coopérative",
        "0109": "Association",
        "0110": "Fondation",
        "0111": "Succursale CH d'une société étrangère",
        "0113": "Institut de droit public",
        "0114": "Entreprise étrangère",
        "0117": "Administration fédérale / cantonale / communale",
        "0151": "Succursale suisse",
        "0152": "Société simple",
    }

    @classmethod
    def _auth(cls):
        return (settings.ZEFIX_USERNAME, settings.ZEFIX_PASSWORD)

    @classmethod
    def _parse_company(cls, item: dict) -> SwissCompany:
        """Parse a Zefix REST API company object."""
        uid_str = str(item.get("uid", ""))
        # Extract address from first registered office
        address = item.get("address", {}) or {}
        # Legal form
        lf = item.get("legalForm", {}) or {}
        lf_id = str(lf.get("id", ""))
        lf_code = lf_id.zfill(4) if lf_id else ""
        lang = _get_zefix_lang()
        lf_name = lf.get("name", {}).get(lang, "") if isinstance(lf.get("name"), dict) else str(lf.get("name", ""))
        if not lf_name and lf_code in cls.LEGAL_FORM_MAP:
            lf_name = cls.LEGAL_FORM_MAP[lf_code]
        # Canton
        canton = ""
        seat = item.get("legalSeat", "")
        rc = item.get("registryOfCommerce", {}) or {}
        canton = rc.get("cantonAbbreviation", "")
        # CH-ID
        ch_id = str(item.get("chid", "")) if item.get("chid") else ""
        # EHRAID
        ehraid = str(item.get("ehraid", "")) if item.get("ehraid") else ""
        # Status
        status_raw = item.get("status", "")
        status = str(status_raw) if status_raw else ""

        return SwissCompany(
            uid=uid_str,
            name=item.get("name", ""),
            legal_form=lf_name,
            legal_form_code=lf_code,
            legal_seat=seat,
            canton=canton,
            status=status,
            ch_id=ch_id,
            ofrc_id=ehraid,
            address_street=address.get("street"),
            address_number=address.get("houseNumber"),
            address_postal_code=address.get("swissZipCode"),
            address_city=address.get("city"),
        )

    @classmethod
    def search(cls, search_term: str, limit: int = 10) -> list[SwissCompany]:
        lang = _get_zefix_lang()
        payload = {
            "name": search_term,
            "languageKey": lang,
            "maxEntries": limit,
        }
        response = requests.post(
            f"{ZEFIX_API_URL}/company/search",
            json=payload,
            auth=cls._auth(),
            timeout=10,
        )
        response.raise_for_status()
        items = response.json()
        if not isinstance(items, list):
            return []
        return [cls._parse_company(item) for item in items[:limit]]

    @classmethod
    def get_by_uid(cls, uid: str) -> Optional[SwissCompany]:
        formatted = uid
        if len(uid) == 9 and uid.isdigit():
            formatted = f"CHE-{uid[:3]}.{uid[3:6]}.{uid[6:]}"
        response = requests.get(
            f"{ZEFIX_API_URL}/company/uid/{formatted}",
            auth=cls._auth(),
            timeout=10,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        items = response.json()
        if not items:
            return None
        item = items[0] if isinstance(items, list) else items
        return cls._parse_company(item)


# =============================================================================
# LINDAS SPARQL BACKEND (fallback, ~30k companies)
# =============================================================================

class _LindasBackend:
    """Fallback backend using LINDAS SPARQL (~30k companies only)."""

    SPARQL_SEARCH = """
        PREFIX schema: <http://schema.org/>
        PREFIX admin: <https://schema.ld.admin.ch/>

        SELECT DISTINCT ?name ?uid ?legalFormCode ?legalForm ?seat ?canton
        WHERE {{
            ?company a admin:ZefixOrganisation ;
                     schema:name ?name ;
                     schema:identifier ?uidUri .

            FILTER(LANG(?name) = "{lang}" || LANG(?name) = "")
            FILTER(CONTAINS(STR(?uidUri), "CHE"))
            BIND(REPLACE(REPLACE(STR(?uidUri), ".*CHE", ""), "[^0-9]", "") AS ?uid)

            OPTIONAL {{
                ?company schema:additionalType ?legalFormUri .
                BIND(REPLACE(STR(?legalFormUri), ".*/", "") AS ?legalFormCode)
                OPTIONAL {{
                    ?legalFormUri schema:name ?legalForm .
                    FILTER(LANG(?legalForm) = "{lang}")
                }}
            }}

            OPTIONAL {{
                ?company schema:municipality ?municipalityUri .
                ?municipalityUri schema:name ?seat .
                FILTER(LANG(?seat) = "{lang}" || LANG(?seat) = "")
            }}

            OPTIONAL {{
                ?company admin:canton ?cantonUri .
                BIND(REPLACE(STR(?cantonUri), ".*/", "") AS ?canton)
            }}

            BIND({normalize} AS ?nameNorm)
            FILTER(CONTAINS(?nameNorm, "{search_term}"))
        }}
        ORDER BY ?name
        LIMIT {limit}
    """

    SPARQL_BY_UID = """
        PREFIX schema: <http://schema.org/>
        PREFIX admin: <https://schema.ld.admin.ch/>

        SELECT DISTINCT ?name ?legalFormCode ?legalForm ?seat ?canton ?status
                        ?chid ?ofrcid ?street ?streetNumber ?postalCode ?city
        WHERE {{
            ?company a admin:ZefixOrganisation ;
                     schema:name ?name ;
                     schema:identifier ?uidUri .

            FILTER(LANG(?name) = "{lang}" || LANG(?name) = "")
            FILTER(CONTAINS(STR(?uidUri), "CHE{uid}"))

            OPTIONAL {{
                ?company schema:additionalType ?legalFormUri .
                BIND(REPLACE(STR(?legalFormUri), ".*/", "") AS ?legalFormCode)
                OPTIONAL {{
                    ?legalFormUri schema:name ?legalForm .
                    FILTER(LANG(?legalForm) = "{lang}")
                }}
            }}

            OPTIONAL {{
                ?company schema:municipality ?municipalityUri .
                ?municipalityUri schema:name ?seat .
                FILTER(LANG(?seat) = "{lang}" || LANG(?seat) = "")
            }}

            OPTIONAL {{
                ?company admin:canton ?cantonUri .
                BIND(REPLACE(STR(?cantonUri), ".*/", "") AS ?canton)
            }}

            OPTIONAL {{
                ?company admin:status ?statusUri .
                BIND(REPLACE(STR(?statusUri), ".*/", "") AS ?status)
            }}

            OPTIONAL {{
                ?company schema:identifier ?chidUri .
                FILTER(CONTAINS(STR(?chidUri), "/CHID/"))
                BIND(REPLACE(STR(?chidUri), ".*/CHID/", "") AS ?chid)
            }}

            OPTIONAL {{
                ?company schema:identifier ?ofrcUri .
                FILTER(CONTAINS(STR(?ofrcUri), "/EHRAID"))
                BIND(REPLACE(REPLACE(STR(?ofrcUri), ".*/company/", ""), "/EHRAID", "") AS ?ofrcid)
            }}

            OPTIONAL {{
                ?company schema:address ?address .
                OPTIONAL {{ ?address schema:streetAddress ?street }}
                OPTIONAL {{ ?address admin:streetAddressHouseNumber ?streetNumber }}
                OPTIONAL {{ ?address schema:postalCode ?postalCode }}
                OPTIONAL {{ ?address schema:addressLocality ?city }}
            }}
        }}
        LIMIT 1
    """

    @classmethod
    def _sparql_request(cls, query: str) -> dict:
        response = requests.post(
            LINDAS_ENDPOINT,
            data={"query": query},
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    @classmethod
    def search(cls, search_term: str, limit: int = 10) -> list[SwissCompany]:
        lang = _get_zefix_lang()
        normalized = _strip_accents(search_term.lower())
        query = cls.SPARQL_SEARCH.format(
            lang=lang,
            search_term=normalized.replace('"', '\\"'),
            normalize=_SPARQL_NORMALIZE,
            limit=limit,
        )
        data = cls._sparql_request(query)
        bindings = data.get("results", {}).get("bindings", [])

        seen_uids = set()
        results = []
        for b in bindings:
            uid = b.get("uid", {}).get("value", "")
            if uid in seen_uids:
                continue
            seen_uids.add(uid)
            results.append(SwissCompany(
                uid=uid,
                name=b.get("name", {}).get("value", ""),
                legal_form=b.get("legalForm", {}).get("value", ""),
                legal_form_code=b.get("legalFormCode", {}).get("value", ""),
                legal_seat=b.get("seat", {}).get("value", ""),
                canton=b.get("canton", {}).get("value", ""),
                status="",
            ))
        return results

    @classmethod
    def get_by_uid(cls, uid: str) -> Optional[SwissCompany]:
        lang = _get_zefix_lang()
        query = cls.SPARQL_BY_UID.format(lang=lang, uid=uid)
        data = cls._sparql_request(query)
        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return None
        b = bindings[0]
        return SwissCompany(
            uid=uid,
            name=b.get("name", {}).get("value", ""),
            legal_form=b.get("legalForm", {}).get("value", ""),
            legal_form_code=b.get("legalFormCode", {}).get("value", ""),
            legal_seat=b.get("seat", {}).get("value", ""),
            canton=b.get("canton", {}).get("value", ""),
            status=b.get("status", {}).get("value", ""),
            ch_id=b.get("chid", {}).get("value", ""),
            ofrc_id=b.get("ofrcid", {}).get("value", ""),
            address_street=b.get("street", {}).get("value"),
            address_number=b.get("streetNumber", {}).get("value"),
            address_postal_code=b.get("postalCode", {}).get("value"),
            address_city=b.get("city", {}).get("value"),
        )


# =============================================================================
# PUBLIC SERVICE (auto-selects backend)
# =============================================================================

class SwissCompaniesService:
    """
    Service to search Swiss companies.
    Uses Zefix REST API if credentials configured, falls back to LINDAS SPARQL.
    """

    @classmethod
    def _backend(cls):
        return _ZefixRestBackend if _has_zefix_credentials() else _LindasBackend

    @classmethod
    def search(cls, search_term: str, limit: int = 10) -> list[SwissCompany]:
        if not search_term or len(search_term) < 3:
            return []

        lang = _get_zefix_lang()
        safe_term = _strip_accents(search_term.lower()).replace(" ", "_")
        cache_key = f"swiss_search:{lang}:{safe_term}:{limit}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        try:
            results = cls._backend().search(search_term, limit)
            try:
                cache.set(cache_key, results, CACHE_TIMEOUT)
            except Exception:
                pass
            return results
        except requests.RequestException as e:
            logger.error("Zefix API error: %s", e)
            return []
        except (KeyError, ValueError) as e:
            logger.error("Error parsing Zefix response: %s", e)
            return []

    @classmethod
    def get_by_uid(cls, uid: str) -> Optional[SwissCompany]:
        clean_uid = uid.replace("CHE-", "").replace("CHE", "").replace(".", "").replace(" ", "")
        if not clean_uid or len(clean_uid) != 9 or not clean_uid.isdigit():
            return None

        lang = _get_zefix_lang()
        cache_key = f"swiss_uid:{lang}:{clean_uid}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        try:
            company = cls._backend().get_by_uid(clean_uid)
            if company:
                try:
                    cache.set(cache_key, company, CACHE_TIMEOUT)
                except Exception:
                    pass
            return company
        except requests.RequestException as e:
            logger.error("Zefix API error: %s", e)
            return None
