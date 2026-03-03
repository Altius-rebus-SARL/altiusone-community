# AltiusOne/settings_community.py
# ============================================================================
# SETTINGS COMMUNITY — Surcharge minimale pour l'edition open-source.
#
# Importe TOUT settings.py (code metier, apps, REST, JWT, etc.)
# puis ajuste uniquement:
#   - Licence AGPL-3.0 dans la doc API
#   - AI optionnel via MCP ou API compatible OpenAI (pas d'altiusone-ai SDK)
#   - Pas de verification de licence portal
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
# AI — Optionnel, via API compatible OpenAI (Ollama, vLLM, LiteLLM, etc.)
# ============================================================================
# Pas de SDK altiusone-ai. L'AI fonctionne si AI_API_URL et AI_API_KEY
# sont configures dans .env, sinon les features AI degradent gracieusement.
# Le serveur MCP (mcp/) reste disponible pour connecter n'importe quel LLM.
EMBEDDING_BACKEND = 'openai-compatible'
