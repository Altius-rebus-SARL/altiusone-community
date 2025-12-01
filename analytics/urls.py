# analytics/urls.py
from django.urls import path
from django.views.decorators.http import require_http_methods
from . import views

app_name = "analytics"

urlpatterns = [
    # Tableaux de bord
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
    path(
        "exports/<uuid:pk>/telecharger/",
        views.export_telecharger,
        name="export-telecharger",
    ),
]
