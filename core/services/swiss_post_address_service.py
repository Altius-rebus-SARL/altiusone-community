# core/services/swiss_post_address_service.py
"""
Service for Swiss address autocomplete via Swiss Post API (autocomplete4).
Used for address fields across the application.
"""
import logging
import requests
from dataclasses import dataclass
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 3600  # 1 hour


@dataclass
class SwissAddress:
    """Represents a Swiss address from the Post API."""
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
    """Service to autocomplete Swiss addresses using Swiss Post API."""

    @classmethod
    def autocomplete(cls, query: str, limit: int = 10) -> list[SwissAddress]:
        """
        Autocomplete Swiss addresses.

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

        # Check credentials
        api_url = getattr(settings, 'SWISS_POST_API_URL', '')
        api_user = getattr(settings, 'SWISS_POST_API_USER', '')
        api_password = getattr(settings, 'SWISS_POST_API_PASSWORD', '')

        if not api_user or not api_password:
            logger.debug("Swiss Post API credentials not configured")
            return []

        try:
            payload = {
                "request": {
                    "ONRP": 0,
                    "ZipCity": "",
                    "ZipAddition": "",
                    "Street": query,
                    "HouseKey": 0,
                    "HouseNumber": "",
                    "HouseNumberAddition": "",
                },
                "zipOrderBy": [],
                "zipFilterBy": [],
            }

            response = requests.post(
                api_url,
                json=payload,
                auth=(api_user, api_password),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()

            results = cls._parse_results(response.json(), limit)

            try:
                cache.set(cache_key, results, CACHE_TIMEOUT)
            except Exception:
                pass

            return results

        except requests.RequestException as e:
            logger.error(f"Swiss Post API error: {e}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Swiss Post response: {e}")
            return []

    @classmethod
    def _parse_results(cls, data: dict, limit: int) -> list[SwissAddress]:
        """Parse Swiss Post API response into SwissAddress objects."""
        addresses = []
        rows = data.get("rows", [])

        for row in rows[:limit]:
            street = row.get("Street", "") or ""
            house_number = row.get("HouseNumber", "") or ""
            zip_code = str(row.get("ZipCode", "") or "")
            city = row.get("TownName", "") or row.get("City", "") or ""
            canton = row.get("Canton", "") or ""

            if not street and not zip_code:
                continue

            addresses.append(SwissAddress(
                street=street,
                house_number=house_number,
                zip_code=zip_code,
                city=city,
                canton=canton,
            ))

        return addresses
