# facturation/urls.py
from django.urls import path
from django.views.decorators.http import require_http_methods
from . import views

app_name = "facturation"

urlpatterns = [
    # Prestations
    path("prestations/", views.PrestationListView.as_view(), name="prestation-list"),
    path(
        "prestations/nouvelle/",
        views.PrestationCreateView.as_view(),
        name="prestation-create",
    ),
    path(
        "prestations/<uuid:pk>/",
        views.PrestationDetailView.as_view(),
        name="prestation-detail",
    ),
    path(
        "prestations/<uuid:pk>/modifier/",
        views.PrestationUpdateView.as_view(),
        name="prestation-update",
    ),
    # Time Tracking
    path("temps/", views.TimeTrackingListView.as_view(), name="timetracking-list"),
    path(
        "temps/nouveau/",
        views.TimeTrackingCreateView.as_view(),
        name="timetracking-create",
    ),
    # Factures
    path("factures/", views.FactureListView.as_view(), name="facture-list"),
    path(
        "factures/nouvelle/", views.FactureCreateView.as_view(), name="facture-create"
    ),
    path(
        "factures/<uuid:pk>/", views.FactureDetailView.as_view(), name="facture-detail"
    ),
    path(
        "factures/<uuid:pk>/modifier/",
        views.FactureUpdateView.as_view(),
        name="facture-update",
    ),
    path("factures/<uuid:pk>/valider/", views.facture_valider, name="facture-valider"),
    path(
        "factures/<uuid:pk>/pdf/", views.facture_generer_pdf, name="facture-generer-pdf"
    ),
    path(
        "factures/<uuid:pk>/envoyer/",
        views.facture_envoyer_email,
        name="facture-envoyer-email",
    ),
    # Lignes de facture
    path(
        "factures/<uuid:facture_pk>/lignes/nouvelle/",
        views.ligne_facture_create,
        name="ligne-create",
    ),
    path(
        "lignes/<uuid:pk>/supprimer/", views.ligne_facture_delete, name="ligne-delete"
    ),
    # Paiements
    path("paiements/", views.PaiementListView.as_view(), name="paiement-list"),
    path(
        "factures/<uuid:facture_pk>/paiements/nouveau/",
        views.paiement_create,
        name="paiement-create",
    ),
    path(
        "paiements/<uuid:pk>/valider/", views.paiement_valider, name="paiement-valider"
    ),
    # Relances
    path(
        "factures/<uuid:facture_pk>/relances/nouvelle/",
        views.relance_create,
        name="relance-create",
    ),
    # HTMX endpoints
    path("lignes/row/", views.ligne_facture_form_row, name="ligne-form-row"),
    path(
        "lignes/<int:index>/delete/",
        views.ligne_facture_delete_row,
        name="ligne-delete-row",
    ),
]
