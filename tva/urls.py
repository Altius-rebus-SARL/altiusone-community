# tva/urls.py
from django.urls import path
from django.views.decorators.http import require_http_methods
from . import views

app_name = "tva"

urlpatterns = [
    # Configuration TVA
    path(
        "configurations/",
        views.ConfigurationTVAListView.as_view(),
        name="configuration-list",
    ),
    path(
        "configurations/<uuid:pk>/",
        views.ConfigurationTVADetailView.as_view(),
        name="configuration-detail",
    ),
    path(
        "configurations/<uuid:pk>/modifier/",
        views.ConfigurationTVAUpdateView.as_view(),
        name="configuration-update",
    ),
    # Déclarations TVA
    path(
        "declarations/", views.DeclarationTVAListView.as_view(), name="declaration-list"
    ),
    path(
        "declarations/nouvelle/",
        views.DeclarationTVACreateView.as_view(),
        name="declaration-create",
    ),
    path(
        "declarations/<uuid:pk>/",
        views.DeclarationTVADetailView.as_view(),
        name="declaration-detail",
    ),
    path(
        "declarations/<uuid:pk>/calculer/",
        views.declaration_calculer,
        name="declaration-calculer",
    ),
    path(
        "declarations/<uuid:pk>/valider/",
        views.declaration_valider,
        name="declaration-valider",
    ),
    path(
        "declarations/<uuid:pk>/xml/",
        views.declaration_exporter_xml,
        name="declaration-xml",
    ),
    path(
        "declarations/<uuid:pk>/pdf/",
        views.declaration_exporter_pdf,
        name="declaration-pdf",
    ),
    # Opérations TVA
    path("operations/", views.OperationTVAListView.as_view(), name="operation-list"),
    path(
        "operations/nouvelle/",
        views.OperationTVACreateView.as_view(),
        name="operation-create",
    ),
]
