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
        "declarations/<uuid:pk>/modifier/",
        views.DeclarationTVAUpdateView.as_view(),
        name="declaration-update",
    ),
    path(
        "declarations/<uuid:pk>/supprimer/",
        views.declaration_supprimer,
        name="declaration-supprimer",
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
        "declarations/<uuid:pk>/rouvrir/",
        views.declaration_rouvrir,
        name="declaration-rouvrir",
    ),
    path(
        "declarations/<uuid:pk>/soumettre/",
        views.declaration_soumettre,
        name="declaration-soumettre",
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
    path(
        "declarations/<uuid:pk>/preview-pdf/",
        views.declaration_preview_pdf,
        name="declaration-preview-pdf",
    ),
    # Lignes TVA
    path(
        "declarations/<uuid:declaration_pk>/lignes/nouvelle/",
        views.ligne_tva_create,
        name="ligne-tva-create",
    ),
    path(
        "lignes/<uuid:pk>/modifier/",
        views.ligne_tva_update,
        name="ligne-tva-update",
    ),
    path(
        "lignes/<uuid:pk>/supprimer/",
        views.ligne_tva_delete,
        name="ligne-tva-delete",
    ),
    # Corrections TVA
    path(
        "declarations/<uuid:declaration_pk>/corrections/nouvelle/",
        views.correction_tva_create,
        name="correction-tva-create",
    ),
    path(
        "corrections/<uuid:pk>/supprimer/",
        views.correction_tva_delete,
        name="correction-tva-delete",
    ),
    # Opérations TVA
    path("operations/", views.OperationTVAListView.as_view(), name="operation-list"),
    path(
        "operations/nouvelle/",
        views.OperationTVACreateView.as_view(),
        name="operation-create",
    ),
    path(
        "operations/<uuid:pk>/modifier/",
        views.OperationTVAUpdateView.as_view(),
        name="operation-update",
    ),
    path(
        "operations/<uuid:pk>/supprimer/",
        views.operation_tva_delete,
        name="operation-tva-delete",
    ),
]
