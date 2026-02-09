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
    # Certificats de salaire (Formulaire 11)
    path(
        "certificats/",
        views.CertificatSalaireListView.as_view(),
        name="certificat-list",
    ),
    path(
        "certificats/generer-masse/",
        views.certificat_generer_masse,
        name="certificat-generer-masse",
    ),
    path(
        "certificats/<uuid:pk>/",
        views.CertificatSalaireDetailView.as_view(),
        name="certificat-detail",
    ),
    path(
        "certificats/<uuid:pk>/modifier/",
        views.CertificatSalaireUpdateView.as_view(),
        name="certificat-edit",
    ),
    path(
        "certificats/<uuid:pk>/recalculer/",
        views.certificat_recalculer,
        name="certificat-recalculer",
    ),
    path(
        "certificats/<uuid:pk>/valider/",
        views.certificat_valider,
        name="certificat-valider",
    ),
    path(
        "certificats/<uuid:pk>/signer/",
        views.certificat_signer,
        name="certificat-signer",
    ),
    path(
        "certificats/<uuid:pk>/pdf/",
        views.certificat_generer_pdf,
        name="certificat-pdf",
    ),
    path(
        "employes/<uuid:employe_pk>/certificat/",
        views.generer_certificat,
        name="generer-certificat",
    ),
    # Certificats de travail
    path(
        "certificats-travail/",
        views.CertificatTravailListView.as_view(),
        name="certificat-travail-list",
    ),
    path(
        "certificats-travail/nouveau/",
        views.CertificatTravailCreateView.as_view(),
        name="certificat-travail-create",
    ),
    path(
        "certificats-travail/<uuid:pk>/",
        views.CertificatTravailDetailView.as_view(),
        name="certificat-travail-detail",
    ),
    path(
        "certificats-travail/<uuid:pk>/modifier/",
        views.CertificatTravailUpdateView.as_view(),
        name="certificat-travail-update",
    ),
    path(
        "certificats-travail/<uuid:pk>/pdf/",
        views.certificat_travail_generer_pdf,
        name="certificat-travail-pdf",
    ),
    path(
        "employes/<uuid:employe_pk>/certificat-travail/",
        views.CertificatTravailCreateView.as_view(),
        name="employe-certificat-travail",
    ),
    # Déclarations cotisations
    path(
        "declarations-cotisations/",
        views.DeclarationCotisationsListView.as_view(),
        name="declaration-cotisations-list",
    ),
]
