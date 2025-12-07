# AltiusOne/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.http import JsonResponse
from django.views import View
from django.conf.urls.i18n import i18n_patterns
from .api_root import api_root
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)

from core.auth_views import simple_login, check_auth, simple_logout

# Import des routers de chaque app
from core.api_urls import router as core_router
from comptabilite.api_urls import router as compta_router
from tva.api_urls import router as tva_router
from facturation.api_urls import router as factu_router
from salaires.api_urls import router as salaires_router
from documents.api_urls import router as docs_router
from fiscalite.api_urls import router as fisc_router
from analytics.api_urls import router as analytics_router

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

schema_view = get_schema_view(
    openapi.Info(
        title="AltiusOne API",
        default_version="v1",
        description="API de gestion fiduciaire complète pour la Suisse",
        terms_of_service="https://www.altius.ch/terms/",
        contact=openapi.Contact(email="contact@altius.ch"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)


class HealthCheckView(View):
    def get(self, request):
        return JsonResponse({"status": "ok", "service": "altiusone"})

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    # Admin
    path("admin/", admin.site.urls),
    # Internationalisation
    path("i18n/", include("django.conf.urls.i18n")),
    # API v1 - Router principal qui génère automatiquement l'API root
    path("api/v1/", include(api_v1_router.urls)),
    # Auth
    path("api/v1/auth/", include("rest_framework.urls")),

    # =========================================================================
    # JWT Authentication Endpoints (for Mobile App)
    # =========================================================================
    # POST /api/v1/auth/token/ - Obtain access & refresh tokens
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    # POST /api/v1/auth/token/refresh/ - Refresh access token
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # POST /api/v1/auth/token/verify/ - Verify token validity
    path("api/v1/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # POST /api/v1/auth/token/blacklist/ - Logout (blacklist refresh token)
    path("api/v1/auth/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),

    # API Documentation
    path(
        "api/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    # Auth simple pour dev (session-based, kept for backwards compatibility)
    path("api/auth/login/", simple_login, name="simple-login"),
    path("api/auth/check/", check_auth, name="check-auth"),
    path("api/auth/logout/", simple_logout, name="simple-logout"),
]


# URLs avec préfixe de langue
urlpatterns += i18n_patterns(
    # Core
    path("", include("core.urls", namespace="core")),
    # Comptabilité
    path("comptabilite/", include("comptabilite.urls", namespace="comptabilite")),
    # Facturation
    path("facturation/", include("facturation.urls", namespace="facturation")),
    # TVA
    path("tva/", include("tva.urls", namespace="tva")),
    # Salaires
    path("salaires/", include("salaires.urls", namespace="salaires")),
    # Documents
    path("documents/", include("documents.urls", namespace="documents")),
    # Fiscalité
    path("fiscalite/", include("fiscalite.urls", namespace="fiscalite")),
    # Analytics
    path("analytics/", include("analytics.urls", namespace="analytics")),
    prefix_default_language=True,
)

# Media files (development only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "AltiusOne Administration"
admin.site.site_title = "AltiusOne Admin"
admin.site.index_title = "Gestion Fiduciaire"



