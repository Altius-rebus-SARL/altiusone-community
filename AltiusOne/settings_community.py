# AltiusOne/settings_community.py
# ============================================================================
# SETTINGS COMMUNITY — Surcharge pour l'edition open-source (AGPL-3.0).
#
# Importe TOUT settings.py (code metier, apps, REST, JWT, etc.)
# puis desactive les services proprietaires/enterprise:
#   - Nextcloud / OnlyOffice (collaboration)
#   - Docs / Editeur collaboratif (La Suite Numerique)
#   - AI SDK altiusone-ai (OCR, embeddings, chat)
#   - GCS (Google Cloud Storage)
#
# Ce qui reste actif:
#   - Tout le coeur metier (15 apps Django)
#   - PostgreSQL + Redis + MinIO/S3
#   - MCP Server (connecter n'importe quel LLM)
#   - API REST + JWT + OAuth2/OIDC
#
# Usage:
#   DJANGO_SETTINGS_MODULE=AltiusOne.settings_community python manage.py runserver
# ============================================================================

from AltiusOne.settings import *  # noqa: F401, F403

# ============================================================================
# MODE COMMUNITY
# ============================================================================
COMMUNITY_MODE = True

# ============================================================================
# API DOCUMENTATION — Licence AGPL-3.0
# ============================================================================
SPECTACULAR_SETTINGS['LICENSE'] = {'name': 'AGPL-3.0', 'url': 'https://www.gnu.org/licenses/agpl-3.0.html'}  # noqa: F405

# ============================================================================
# EDITEUR COLLABORATIF (Docs) — Desactive
# ============================================================================
DOCS_API_URL = ''
DOCS_FRONTEND_URL = ''
DOCS_API_KEY = ''
DOCS_COLLABORATION_URL = ''
DOCS_WEBHOOK_SECRET = ''
DOCS_S3_BUCKET = ''
DOCS_S3_ENDPOINT = ''
DOCS_S3_ACCESS_KEY = ''
DOCS_S3_SECRET_KEY = ''

# ============================================================================
# NEXTCLOUD / ONLYOFFICE — Desactive
# ============================================================================
# Pas de Nextcloud ni OnlyOffice dans la version community.
# Le stockage de fichiers passe par MinIO/S3 directement.

# ============================================================================
# AI — Optionnel, via API compatible OpenAI (Ollama, vLLM, LiteLLM, etc.)
# ============================================================================
# Pas de SDK altiusone-ai. L'AI fonctionne si AI_API_URL et AI_API_KEY
# sont configures dans .env, sinon les features AI degradent gracieusement.
# Le serveur MCP (mcp/) reste disponible pour connecter n'importe quel LLM.
EMBEDDING_BACKEND = 'openai-compatible'

# ============================================================================
# GCS — Desactive (pas de Google Cloud Storage)
# ============================================================================
GCS_ENABLED = False
