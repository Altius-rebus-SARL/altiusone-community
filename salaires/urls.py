# salaires/urls.py
from django.urls import path
from django.views.decorators.http import require_http_methods
from . import views

app_name = "salaires"

urlpatterns = [
    # Employés
    path("employes/", views.EmployeListView.as_view(), name="employe-list"),
    path("employes/nouveau/", views.EmployeCreateView.as_view(), name="employe-create"),
    path(
        "employes/<uuid:pk>/", views.EmployeDetailView.as_view(), name="employe-detail"
    ),
    path(
        "employes/<uuid:pk>/modifier/",
        views.EmployeUpdateView.as_view(),
        name="employe-update",
    ),
    # Fiches de salaire
    path("fiches/", views.FicheSalaireListView.as_view(), name="fiche-list"),
    path(
        "fiches/nouvelle/", views.FicheSalaireCreateView.as_view(), name="fiche-create"
    ),
    path(
        "fiches/<uuid:pk>/", views.FicheSalaireDetailView.as_view(), name="fiche-detail"
    ),
    path("fiches/<uuid:pk>/valider/", views.fiche_valider, name="fiche-valider"),
    path("fiches/<uuid:pk>/pdf/", views.fiche_generer_pdf, name="fiche-pdf"),
    path(
        "fiches/generer-masse/", views.generer_fiches_masse, name="generer-fiches-masse"
    ),
    # Certificats de salaire
    path(
        "certificats/",
        views.CertificatSalaireListView.as_view(),
        name="certificat-list",
    ),
    path(
        "certificats/<uuid:pk>/",
        views.CertificatSalaireDetailView.as_view(),
        name="certificat-detail",
    ),
    path(
        "employes/<uuid:employe_pk>/certificat/",
        views.generer_certificat,
        name="generer-certificat",
    ),
    # Déclarations cotisations
    path(
        "declarations-cotisations/",
        views.DeclarationCotisationsListView.as_view(),
        name="declaration-cotisations-list",
    ),
]
