# core/services/swiss_companies_service.py
"""
Service for searching Swiss companies via Zefix LINDAS SPARQL API.
Used for autocomplete when creating new clients/entreprises.

Optimized: search uses a lightweight query (name, UID, legal form, seat, canton).
Full details (address, CH-ID, OFRC-ID) are fetched only via get_by_uid.
"""
import logging
import requests
from dataclasses import dataclass
from typing import Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Zefix SPARQL endpoint (register.ld.admin.ch)
ZEFIX_ENDPOINT = "https://register.ld.admin.ch/query/"
CACHE_TIMEOUT = 3600  # 1 hour


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
        """Convert to dictionary for API response."""
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
        """Format UID to IDE format (CHE-XXX.XXX.XXX)."""
        if self.uid and len(self.uid) == 9 and self.uid.isdigit():
            return f"CHE-{self.uid[:3]}.{self.uid[3:6]}.{self.uid[6:]}"
        return self.uid

    def format_ch_id(self) -> str:
        """Format CH-ID (CH-XXX-XXXXXXX-X)."""
        if self.ch_id and len(self.ch_id) >= 12:
            ch = self.ch_id.replace("CH", "")
            if len(ch) >= 10:
                return f"CH-{ch[:3]}-{ch[3:10]}-{ch[10:]}"
        return self.ch_id


class SwissCompaniesService:
    """Service to search Swiss companies using Zefix LINDAS SPARQL API."""

    # Lightweight query for autocomplete: name, UID, legal form, seat, canton only.
    # No address, CH-ID, OFRC-ID = ~3x faster (1.2s vs 3.2s).
    SPARQL_SEARCH = """
        PREFIX schema: <http://schema.org/>
        PREFIX admin: <https://schema.ld.admin.ch/>

        SELECT DISTINCT ?name ?uid ?legalFormCode ?legalForm ?seat ?canton
        WHERE {{
            ?company a admin:ZefixOrganisation ;
                     schema:name ?name ;
                     schema:identifier ?uidUri .

            FILTER(CONTAINS(STR(?uidUri), "CHE"))
            BIND(REPLACE(REPLACE(STR(?uidUri), ".*CHE", ""), "[^0-9]", "") AS ?uid)

            OPTIONAL {{
                ?company schema:additionalType ?legalFormUri .
                BIND(REPLACE(STR(?legalFormUri), ".*/", "") AS ?legalFormCode)
                OPTIONAL {{
                    ?legalFormUri schema:name ?legalForm .
                    FILTER(LANG(?legalForm) = "fr")
                }}
            }}

            OPTIONAL {{
                ?company schema:municipality ?municipalityUri .
                ?municipalityUri schema:name ?seat .
            }}

            OPTIONAL {{
                ?company admin:canton ?cantonUri .
                BIND(REPLACE(STR(?cantonUri), ".*/", "") AS ?canton)
            }}

            FILTER(CONTAINS(LCASE(?name), LCASE("{search_term}")))
        }}
        ORDER BY ?name
        LIMIT {limit}
    """

    # Full query for single company lookup by UID (includes address, CH-ID, OFRC-ID).
    SPARQL_BY_UID = """
        PREFIX schema: <http://schema.org/>
        PREFIX admin: <https://schema.ld.admin.ch/>

        SELECT DISTINCT ?name ?legalFormCode ?legalForm ?seat ?canton ?status
                        ?chid ?ofrcid ?street ?streetNumber ?postalCode ?city
        WHERE {{
            ?company a admin:ZefixOrganisation ;
                     schema:name ?name ;
                     schema:identifier ?uidUri .

            FILTER(CONTAINS(STR(?uidUri), "CHE{uid}"))

            OPTIONAL {{
                ?company schema:additionalType ?legalFormUri .
                BIND(REPLACE(STR(?legalFormUri), ".*/", "") AS ?legalFormCode)
                OPTIONAL {{
                    ?legalFormUri schema:name ?legalForm .
                    FILTER(LANG(?legalForm) = "fr")
                }}
            }}

            OPTIONAL {{
                ?company schema:municipality ?municipalityUri .
                ?municipalityUri schema:name ?seat .
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
    def _sparql_request(cls, query: str, timeout: int = 10) -> Optional[dict]:
        """Execute a SPARQL query and return parsed JSON results."""
        response = requests.post(
            ZEFIX_ENDPOINT,
            data={"query": query},
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    @classmethod
    def search(cls, search_term: str, limit: int = 10) -> list[SwissCompany]:
        """
        Search for Swiss companies by name (lightweight, for autocomplete).

        Returns basic info only (name, UID, legal form, seat, canton).
        Use get_by_uid() to fetch full details including address.
        """
        if not search_term or len(search_term) < 3:
            return []

        safe_term = search_term.lower().replace(" ", "_")
        cache_key = f"swiss_search:{safe_term}:{limit}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        try:
            query = cls.SPARQL_SEARCH.format(
                search_term=search_term.replace('"', '\\"'),
                limit=limit,
            )
            data = cls._sparql_request(query)
            bindings = data.get("results", {}).get("bindings", [])

            # Parse and deduplicate by UID
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
        """
        Get a specific company by UID with full details (address, CH-ID, OFRC-ID).
        """
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
            query = cls.SPARQL_BY_UID.format(uid=clean_uid)
            data = cls._sparql_request(query)
            bindings = data.get("results", {}).get("bindings", [])

            if not bindings:
                return None

            b = bindings[0]
            company = SwissCompany(
                uid=clean_uid,
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

            try:
                cache.set(cache_key, company, CACHE_TIMEOUT)
            except Exception:
                pass

            return company

        except requests.RequestException as e:
            logger.error("Zefix API error: %s", e)
            return None
