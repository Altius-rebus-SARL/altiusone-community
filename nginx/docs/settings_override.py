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
    # SSL/HTTPS - Géré par Nginx
    # ==========================================================================
    # Pas de redirection SSL par Django (c'est Nginx qui gère)
    SECURE_SSL_REDIRECT = False
    # Mais on fait confiance au header X-Forwarded-Proto pour request.is_secure()
    # et request.build_absolute_uri() (crucial pour OIDC redirect_uri)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # ==========================================================================
    # Cookies - Configuration pour HTTPS en production
    # ==========================================================================
    # En production HTTPS, les cookies doivent être Secure pour être envoyés
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # SameSite=None permet les redirections OIDC cross-origin (requiert Secure=True)
    # "None" (string) = envoyer le cookie même en cross-origin
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE = "None"

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
