# =============================================================================
# Settings Override pour Docs (La Suite Numérique)
# =============================================================================
# Ce fichier surcharge les settings de production de Docs pour désactiver
# les redirections SSL. Le SSL est géré par notre Nginx, pas par Django.
#
# Utilisation: Monter ce fichier dans le container et définir:
#   DJANGO_SETTINGS_MODULE=settings_override
#   DJANGO_CONFIGURATION=AltiusOneProduction
# =============================================================================

import os
# Force les variables AVANT d'importer quoi que ce soit
os.environ["DJANGO_SETTINGS_MODULE"] = "settings_override"
os.environ["DJANGO_CONFIGURATION"] = "AltiusOneProduction"

from impress.settings import Production


class AltiusOneProduction(Production):
    """
    Configuration Production pour AltiusOne.

    Hérite de la config Production de Docs mais désactive les settings SSL
    car c'est notre Nginx qui gère la terminaison SSL.
    """

    # ==========================================================================
    # Sessions Redis - CRITIQUE pour OIDC
    # ==========================================================================
    # Les sessions doivent être persistées dans Redis pour que l'état OIDC
    # survive aux redirections cross-origin (localhost:3000 -> localhost:8012)
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"

    # Configuration du cache Redis
    @property
    def CACHES(self):
        return {
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/1"),
            }
        }

    # ==========================================================================
    # SSL/HTTPS - Désactivé (géré par Nginx)
    # ==========================================================================
    SECURE_SSL_REDIRECT = False
    SECURE_PROXY_SSL_HEADER = None

    # ==========================================================================
    # Cookies - Configuration pour dev local (HTTP)
    # ==========================================================================
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

    # SameSite=False (désactivé) pour permettre les redirections OIDC cross-origin
    # En dev HTTP, on ne peut pas utiliser SameSite=None (qui requiert Secure=True)
    # False = ne pas envoyer l'attribut SameSite du tout
    SESSION_COOKIE_SAMESITE = False
    CSRF_COOKIE_SAMESITE = False

    # ==========================================================================
    # HSTS - Désactivé (géré par Nginx si besoin)
    # ==========================================================================
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

    # ==========================================================================
    # OIDC - Configuration pour l'authentification
    # ==========================================================================
    OIDC_STORE_ID_TOKEN = True
