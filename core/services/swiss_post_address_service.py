# core/services/swiss_post_address_service.py
"""
Service for Swiss address autocomplete.

Uses geo.admin.ch SearchServer API (free, no auth) as primary backend.
Swiss Post API (OAuth2, requires approval) can be added as primary when available,
with geo.admin.ch as fallback.
"""
import logging
import re
import requests
from dataclasses import dataclass
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 3600  # 1 hour

# geo.admin.ch SearchServer - free, no authentication required
GEO_ADMIN_API_URL = "https://api3.geo.admin.ch/rest/services/api/SearchServer"

# Canton abbreviation mapping (geo.admin.ch returns lowercase 2-letter codes)
CANTON_MAP = {
    'zh': 'ZH', 'be': 'BE', 'lu': 'LU', 'ur': 'UR', 'sz': 'SZ', 'ow': 'OW',
    'nw': 'NW', 'gl': 'GL', 'zg': 'ZG', 'fr': 'FR', 'so': 'SO', 'bs': 'BS',
    'bl': 'BL', 'sh': 'SH', 'ar': 'AR', 'ai': 'AI', 'sg': 'SG', 'gr': 'GR',
    'ag': 'AG', 'tg': 'TG', 'ti': 'TI', 'vd': 'VD', 'vs': 'VS', 'ne': 'NE',
    'ge': 'GE', 'ju': 'JU',
}


@dataclass
class SwissAddress:
    """Represents a Swiss address."""
    street: str
    house_number: str
    zip_code: str
    city: str
    canton: str

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            'street': self.street,
            'house_number': self.house_number,
            'zip_code': self.zip_code,
            'city': self.city,
            'canton': self.canton,
        }


class SwissPostAddressService:
    """Service to autocomplete Swiss addresses using geo.admin.ch API."""

    @classmethod
    def autocomplete(cls, query: str, limit: int = 10) -> list[SwissAddress]:
        """
        Autocomplete Swiss addresses via geo.admin.ch SearchServer.

        Args:
            query: Address search string (minimum 3 characters)
            limit: Maximum number of results (default 10)

        Returns:
            List of SwissAddress objects
        """
        if not query or len(query) < 3:
            return []

        # Check cache first
        safe_query = query.lower().replace(" ", "_")
        cache_key = f"swiss_addr:{safe_query}:{limit}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        try:
            response = requests.get(
                GEO_ADMIN_API_URL,
                params={
                    "searchText": query,
                    "type": "locations",
                    "origins": "address",
                    "limit": limit,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
            response.raise_for_status()

            results = cls._parse_results(response.json())

            try:
                cache.set(cache_key, results, CACHE_TIMEOUT)
            except Exception:
                pass

            return results

        except requests.RequestException as e:
            logger.error(f"geo.admin.ch API error: {e}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing geo.admin.ch response: {e}")
            return []

    @classmethod
    def _parse_results(cls, data: dict) -> list[SwissAddress]:
        """Parse geo.admin.ch SearchServer response into SwissAddress objects.

        The 'detail' field format is:
            'rue numero npa localite bfs_id localite ch canton'
        Example:
            'bahnhofstrasse 1 8001 zuerich 261 zuerich ch zh'
            'rue du marche 1b 1820 montreux 5886 montreux ch vd'
        """
        addresses = []

        for result in data.get("results", []):
            attrs = result.get("attrs", {})

            if attrs.get("origin") != "address":
                continue

            detail = attrs.get("detail", "")
            label = attrs.get("label", "")

            # Extract canton from last 2 chars of detail
            canton_code = detail[-2:].strip() if len(detail) >= 2 else ""
            canton = CANTON_MAP.get(canton_code, canton_code.upper())

            # Parse the label: "Rue du Marché 1b <b>1820 Montreux</b>"
            # This preserves proper casing (detail is all lowercase)
            address = cls._parse_label(label, canton)
            if address:
                addresses.append(address)

        return addresses

    @classmethod
    def _parse_label(cls, label: str, canton: str) -> SwissAddress | None:
        """Parse a geo.admin.ch label into a SwissAddress.

        Label format: 'Street Number <b>ZipCode City</b>'
        Examples:
            'Bahnhofstrasse 1 <b>8001 Zürich</b>'
            'Rue du Marché 1b <b>1820 Montreux</b>'
            'Dorfstrasse <b>3000 Bern</b>'
        """
        if not label:
            return None

        # Split on <b> tag to get street part and zip+city part
        match = re.match(r'^(.*?)\s*<b>(\d{4})\s+(.+?)</b>$', label)
        if not match:
            return None

        street_part = match.group(1).strip()
        zip_code = match.group(2)
        city = match.group(3).strip()

        # Split street part into street name and house number
        # House number is typically the last token if it starts with a digit
        street = street_part
        house_number = ""

        if street_part:
            # Remove '#' placeholder (geo.admin.ch uses it for "no number")
            street_part = street_part.replace(' #', '').replace('#', '').strip()
            street = street_part
            # Match trailing house number (e.g. "1", "1b", "12a", "1-3")
            num_match = re.match(r'^(.+?)\s+(\d+\w*)$', street_part)
            if num_match:
                street = num_match.group(1)
                house_number = num_match.group(2)

        return SwissAddress(
            street=street,
            house_number=house_number,
            zip_code=zip_code,
            city=city,
            canton=canton,
        )
