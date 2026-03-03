# AltiusOne/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views import View
from django.conf.urls.i18n import i18n_patterns
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from core.auth_views import simple_login, check_auth, simple_logout

# Import des routers de chaque app
from core.api_urls import router as core_router
from comptabilite.api_urls import router as compta_router
from tva.api_urls import router as tva_router
from facturation.api_urls import router as factu_router
from salaires.api_urls import router as salaires_router
from documents.api_urls import router as docs_router, chat_urlpatterns as docs_chat_urls
from fiscalite.api_urls import router as fisc_router
from analytics.api_urls import router as analytics_router
from mailing.api_urls import router as mailing_router
from editeur.api_urls import urlpatterns as editeur_api_urls
from modelforms.api_urls import router as modelforms_router
from graph.api_urls import router as graph_router, graph_extra_urls as graph_extra_urls

# Créer un router principal
api_v1_router = DefaultRouter()

# Enregistrer tous les viewsets dans le router principal
api_v1_router.registry.extend(core_router.registry)
api_v1_router.registry.extend(compta_router.registry)
api_v1_router.registry.extend(tva_router.registry)
api_v1_router.registry.extend(factu_router.registry)
api_v1_router.registry.extend(salaires_router.registry)
api_v1_router.registry.extend(docs_router.registry)
api_v1_router.registry.extend(fisc_router.registry)
api_v1_router.registry.extend(analytics_router.registry)
api_v1_router.registry.extend(mailing_router.registry)
api_v1_router.registry.extend(modelforms_router.registry)
api_v1_router.registry.extend(graph_router.registry)


class HealthCheckView(View):
    def get(self, request):
        return JsonResponse({"status": "ok", "service": "altiusone"})


urlpatterns = [
    # Health check
    path("health/", HealthCheckView.as_view(), name="health"),

    # Admin
    path("admin/", admin.site.urls),

    # =========================================================================
    # OAuth2 / OIDC Provider (pour Docs et autres clients)
    # =========================================================================
    # Endpoints:
    # - /o/authorize/ : Authorization endpoint
    # - /o/token/ : Token endpoint
    # - /o/userinfo/ : UserInfo endpoint (OIDC)
    # - /o/jwks/ : JSON Web Key Set
    # - /o/.well-known/openid-configuration/ : OIDC Discovery
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    
    # Internationalisation
    path("i18n/", include("django.conf.urls.i18n")),
    
    # API v1 - Router principal
    path("api/v1/", include(api_v1_router.urls)),

    # API v1 - Documents Chat URLs additionnelles
    path("api/v1/documents/", include(docs_chat_urls)),

    # API v1 - Chat URLs (raccourci pour /api/v1/chat/)
    path("api/v1/", include(docs_chat_urls)),

    # API v1 - Chat & Messagerie (team messaging + AI)
    path("api/v1/messaging/", include("chat.api_urls")),

    # API v1 - Graphe relationnel (URLs additionnelles)
    path("api/v1/graph-analytics/", include(graph_extra_urls)),

    # API v1 - Éditeur collaboratif
    path("api/v1/editeur/", include(editeur_api_urls)),

    # MCP Server (Model Context Protocol)
    path("mcp/", include("mcp.urls", namespace="mcp")),

    # DRF browsable API auth
    path("api/v1/auth/", include("rest_framework.urls")),
    
    # =========================================================================
    # JWT Authentication Endpoints (for Mobile App)
    # =========================================================================
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/v1/auth/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    
    # =========================================================================
    # API Documentation (drf-spectacular)
    # =========================================================================
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
    # Auth simple pour dev (session-based, backwards compatibility)
    path("api/auth/login/", simple_login, name="simple-login"),
    path("api/auth/check/", check_auth, name="check-auth"),
    path("api/auth/logout/", simple_logout, name="simple-logout"),
]

# URLs avec préfixe de langue
urlpatterns += i18n_patterns(
    path("", include("core.urls", namespace="core")),
    path("comptabilite/", include("comptabilite.urls", namespace="comptabilite")),
    path("facturation/", include("facturation.urls", namespace="facturation")),
    path("tva/", include("tva.urls", namespace="tva")),
    path("salaires/", include("salaires.urls", namespace="salaires")),
    path("documents/", include("documents.urls", namespace="documents")),
    path("fiscalite/", include("fiscalite.urls", namespace="fiscalite")),
    path("analytics/", include("analytics.urls", namespace="analytics")),
    path("mailing/", include("mailing.urls", namespace="mailing")),
    path("editeur/", include("editeur.urls", namespace="editeur")),
    path("modelforms/", include("modelforms.urls", namespace="modelforms")),
    path("projets/", include("projets.urls", namespace="projets")),
    path("graph/", include("graph.urls", namespace="graph")),
    # Import/Export générique pour tous les modèles
    path("import-export/", include("core.import_export.urls", namespace="import_export")),
    prefix_default_language=True,
)

# Media/Static files (development only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin customization
admin.site.site_header = "AltiusOne Administration"
admin.site.site_title = "AltiusOne Admin"
admin.site.index_title = "Gestion d'Application"

# Error handlers
handler400 = "core.views.error_400"
handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"