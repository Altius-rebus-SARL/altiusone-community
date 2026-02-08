# core/services/swiss_companies_service.py
"""
Service for searching Swiss companies via Zefix LINDAS SPARQL API.
Used for autocomplete when creating new clients.
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
    legal_seat: str
    canton: str
    status: str
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
            'legal_seat': self.legal_seat,
            'canton': self.canton,
            'status': self.status,
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


class SwissCompaniesService:
    """Service to search Swiss companies using Zefix LINDAS SPARQL API."""

    SPARQL_QUERY = """
        PREFIX schema: <http://schema.org/>
        PREFIX admin: <https://schema.ld.admin.ch/>

        SELECT DISTINCT ?name ?uid ?legalForm ?seat ?canton ?status
                        ?street ?streetNumber ?postalCode ?city
        WHERE {{
            ?company a admin:ZefixOrganisation ;
                     schema:name ?name ;
                     schema:identifier ?uidUri .

            FILTER(CONTAINS(STR(?uidUri), "CHE"))
            BIND(REPLACE(REPLACE(STR(?uidUri), ".*CHE", ""), "[^0-9]", "") AS ?uid)

            OPTIONAL {{
                ?company admin:legalForm ?legalFormUri .
                ?legalFormUri schema:name ?legalForm .
                FILTER(LANG(?legalForm) = "fr" || LANG(?legalForm) = "")
            }}
            OPTIONAL {{ ?company admin:legalSeat ?seat }}
            OPTIONAL {{
                ?company admin:canton ?cantonUri .
                BIND(REPLACE(STR(?cantonUri), ".*/", "") AS ?canton)
            }}
            OPTIONAL {{
                ?company admin:status ?statusUri .
                BIND(REPLACE(STR(?statusUri), ".*/", "") AS ?status)
            }}

            OPTIONAL {{
                ?company schema:address ?address .
                OPTIONAL {{ ?address schema:streetAddress ?street }}
                OPTIONAL {{ ?address admin:streetAddressHouseNumber ?streetNumber }}
                OPTIONAL {{ ?address schema:postalCode ?postalCode }}
                OPTIONAL {{ ?address schema:addressLocality ?city }}
            }}

            FILTER(CONTAINS(LCASE(?name), LCASE("{search_term}")))
        }}
        ORDER BY ?name
        LIMIT {limit}
    """

    @classmethod
    def search(cls, search_term: str, limit: int = 10) -> list[SwissCompany]:
        """
        Search for Swiss companies by name.

        Args:
            search_term: Company name to search for (minimum 3 characters)
            limit: Maximum number of results (default 10)

        Returns:
            List of SwissCompany objects
        """
        if not search_term or len(search_term) < 3:
            return []

        # Check cache first
        cache_key = f"swiss_company_search:{search_term.lower()}:{limit}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass  # Cache unavailable, continue without it

        try:
            query = cls.SPARQL_QUERY.format(
                search_term=search_term.replace('"', '\\"'),
                limit=limit
            )

            response = requests.post(
                ZEFIX_ENDPOINT,
                data={"query": query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=15,
            )
            response.raise_for_status()

            results = cls._parse_results(response.json())

            # Deduplicate by UID (keep first occurrence)
            seen_uids = set()
            unique_results = []
            for company in results:
                if company.uid not in seen_uids:
                    seen_uids.add(company.uid)
                    unique_results.append(company)

            # Cache the results
            try:
                cache.set(cache_key, unique_results, CACHE_TIMEOUT)
            except Exception:
                pass  # Cache unavailable

            return unique_results

        except requests.RequestException as e:
            logger.error(f"Zefix API error: {e}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Zefix response: {e}")
            return []

    @classmethod
    def _parse_results(cls, data: dict) -> list[SwissCompany]:
        """Parse SPARQL JSON results into SwissCompany objects."""
        companies = []
        bindings = data.get("results", {}).get("bindings", [])

        for binding in bindings:
            company = SwissCompany(
                uid=binding.get("uid", {}).get("value", ""),
                name=binding.get("name", {}).get("value", ""),
                legal_form=binding.get("legalForm", {}).get("value", ""),
                legal_seat=binding.get("seat", {}).get("value", ""),
                canton=binding.get("canton", {}).get("value", ""),
                status=binding.get("status", {}).get("value", ""),
                address_street=binding.get("street", {}).get("value"),
                address_number=binding.get("streetNumber", {}).get("value"),
                address_postal_code=binding.get("postalCode", {}).get("value"),
                address_city=binding.get("city", {}).get("value"),
            )
            companies.append(company)

        return companies

    @classmethod
    def get_by_uid(cls, uid: str) -> Optional[SwissCompany]:
        """
        Get a specific company by its UID.

        Args:
            uid: The company UID (9 digits or CHE-XXX.XXX.XXX format)

        Returns:
            SwissCompany object or None if not found
        """
        # Clean the UID (remove CHE- and dots if present)
        clean_uid = uid.replace("CHE-", "").replace("CHE", "").replace(".", "").replace(" ", "")

        if not clean_uid or len(clean_uid) != 9 or not clean_uid.isdigit():
            return None

        cache_key = f"swiss_company_uid:{clean_uid}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass  # Cache unavailable

        query = f"""
            PREFIX schema: <http://schema.org/>
            PREFIX admin: <https://schema.ld.admin.ch/>

            SELECT DISTINCT ?name ?legalForm ?seat ?canton ?status
                            ?street ?streetNumber ?postalCode ?city
            WHERE {{
                ?company a admin:ZefixOrganisation ;
                         schema:name ?name ;
                         schema:identifier ?uidUri .

                FILTER(CONTAINS(STR(?uidUri), "CHE{clean_uid}"))

                OPTIONAL {{
                    ?company admin:legalForm ?legalFormUri .
                    ?legalFormUri schema:name ?legalForm .
                    FILTER(LANG(?legalForm) = "fr" || LANG(?legalForm) = "")
                }}
                OPTIONAL {{ ?company admin:legalSeat ?seat }}
                OPTIONAL {{
                    ?company admin:canton ?cantonUri .
                    BIND(REPLACE(STR(?cantonUri), ".*/", "") AS ?canton)
                }}
                OPTIONAL {{
                    ?company admin:status ?statusUri .
                    BIND(REPLACE(STR(?statusUri), ".*/", "") AS ?status)
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

        try:
            response = requests.post(
                ZEFIX_ENDPOINT,
                data={"query": query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=15,
            )
            response.raise_for_status()

            bindings = response.json().get("results", {}).get("bindings", [])
            if not bindings:
                return None

            binding = bindings[0]
            company = SwissCompany(
                uid=clean_uid,
                name=binding.get("name", {}).get("value", ""),
                legal_form=binding.get("legalForm", {}).get("value", ""),
                legal_seat=binding.get("seat", {}).get("value", ""),
                canton=binding.get("canton", {}).get("value", ""),
                status=binding.get("status", {}).get("value", ""),
                address_street=binding.get("street", {}).get("value"),
                address_number=binding.get("streetNumber", {}).get("value"),
                address_postal_code=binding.get("postalCode", {}).get("value"),
                address_city=binding.get("city", {}).get("value"),
            )

            try:
                cache.set(cache_key, company, CACHE_TIMEOUT)
            except Exception:
                pass  # Cache unavailable
            return company

        except requests.RequestException as e:
            logger.error(f"Zefix API error: {e}")
            return None
