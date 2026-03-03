# analytics/urls.py
from django.urls import path, include
from django.views.decorators.http import require_http_methods
from . import views

app_name = "analytics"

urlpatterns = [
    # Dashboard Exécutif (page principale)
    path(
        "",
        views.DashboardExecutifView.as_view(),
        name="dashboard-executif",
    ),
    # Visualisations D3.js
    path(
        "visualisations/",
        views.D3DashboardView.as_view(),
        name="visualisations",
    ),
    # API D3.js
    path("api/d3/", include("analytics.d3_urls")),
    path(
        "api/dashboard/refresh/",
        views.dashboard_api_refresh,
        name="dashboard-api-refresh",
    ),
    path(
        "api/rapport/preview/",
        views.rapport_preview_api,
        name="rapport-preview-api",
    ),

    # =========================================================================
    # API Sections de rapport
    # =========================================================================
    path(
        "api/rapport/<uuid:rapport_id>/sections/",
        views.rapport_sections_api,
        name="rapport-sections-api",
    ),
    path(
        "api/rapport/<uuid:rapport_id>/sections/<uuid:section_id>/",
        views.rapport_section_detail_api,
        name="rapport-section-detail-api",
    ),
    path(
        "api/rapport/<uuid:rapport_id>/sections/reorder/",
        views.rapport_sections_reorder_api,
        name="rapport-sections-reorder-api",
    ),
    path(
        "api/rapport/<uuid:rapport_id>/preview-pdf/",
        views.rapport_preview_pdf_api,
        name="rapport-preview-pdf-api",
    ),
    path(
        "api/rapport/preview-live/",
        views.rapport_preview_live_api,
        name="rapport-preview-live-api",
    ),
    path(
        "api/graphiques-disponibles/<str:type_rapport>/",
        views.graphiques_disponibles_api,
        name="graphiques-disponibles-api",
    ),
    path(
        "api/modeles-rapport/<str:type_rapport>/",
        views.modeles_rapport_api,
        name="modeles-rapport-api",
    ),

    # Tableaux de bord personnalisés
    path(
        "tableaux-bord/", views.TableauBordListView.as_view(), name="tableau-bord-list"
    ),
    path(
        "tableaux-bord/nouveau/",
        views.TableauBordCreateView.as_view(),
        name="tableau-bord-create",
    ),
    path(
        "tableaux-bord/<uuid:pk>/",
        views.TableauBordDetailView.as_view(),
        name="tableau-bord-detail",
    ),
    path(
        "tableaux-bord/<uuid:pk>/modifier/",
        views.TableauBordUpdateView.as_view(),
        name="tableau-bord-update",
    ),
    # Indicateurs
    path("indicateurs/", views.IndicateurListView.as_view(), name="indicateur-list"),
    path(
        "indicateurs/<uuid:pk>/",
        views.IndicateurDetailView.as_view(),
        name="indicateur-detail",
    ),
    # Rapports
    path("rapports/", views.RapportListView.as_view(), name="rapport-list"),
    path(
        "rapports/<uuid:pk>/", views.RapportDetailView.as_view(), name="rapport-detail"
    ),
    path(
        "rapports/<uuid:pk>/telecharger/",
        views.rapport_telecharger,
        name="rapport-telecharger",
    ),
    path(
        "rapports/<uuid:pk>/envoyer-email/",
        views.rapport_envoyer_email,
        name="rapport-envoyer-email",
    ),
    path(
        "rapports/<uuid:pk>/regenerer/",
        views.rapport_regenerer,
        name="rapport-regenerer",
    ),
    path("rapports/generer/", views.rapport_generer, name="rapport-generer"),
    # Planifications
    path(
        "planifications/",
        views.PlanificationRapportListView.as_view(),
        name="planification-list",
    ),
    path(
        "planifications/nouvelle/",
        views.PlanificationRapportCreateView.as_view(),
        name="planification-create",
    ),
    # Comparaisons
    path("comparaisons/", views.comparaison_periodes, name="comparaison-create"),
    path(
        "comparaisons/<uuid:pk>/",
        views.ComparaisonPeriodeDetailView.as_view(),
        name="comparaison-detail",
    ),
    # Alertes
    path("alertes/", views.AlerteMetriqueListView.as_view(), name="alerte-list"),
    path(
        "alertes/<uuid:pk>/acquitter/", views.alerte_acquitter, name="alerte-acquitter"
    ),
    # Exports
    path("exports/", views.ExportDonneesListView.as_view(), name="export-list"),
    path("exports/nouveau/", views.export_donnees, name="export-create"),
    path("exports/nouveau/", views.export_donnees, name="export-donnees"),  # Alias
    path(
        "exports/<uuid:pk>/telecharger/",
        views.export_telecharger,
        name="export-telecharger",
    ),
]
