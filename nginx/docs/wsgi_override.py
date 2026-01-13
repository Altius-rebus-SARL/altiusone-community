# =============================================================================
# WSGI Override pour Docs (La Suite Numérique) - AltiusOne Integration
# =============================================================================
# Ce fichier remplace impress/wsgi.py pour utiliser nos settings custom
# =============================================================================

import os

# IMPORTANT: Définir les variables d'environnement AVANT tout import Django
os.environ["DJANGO_SETTINGS_MODULE"] = "settings_override"
os.environ["DJANGO_CONFIGURATION"] = "AltiusOneProduction"

from configurations.wsgi import get_wsgi_application

application = get_wsgi_application()
