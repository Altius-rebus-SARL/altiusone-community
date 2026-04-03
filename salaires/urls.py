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
    path("fiches/<uuid:pk>/preview-pdf/", views.fiche_preview_pdf, name="fiche-preview-pdf"),
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
        "certificats/<uuid:pk>/preview-pdf/",
        views.certificat_preview_pdf,
        name="certificat-preview-pdf",
    ),
    path(
        "certificats/<uuid:pk>/xml/",
        views.certificat_export_xml,
        name="certificat-xml",
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
        "certificats-travail/<uuid:pk>/preview-pdf/",
        views.certificat_travail_preview_pdf,
        name="certificat-travail-preview-pdf",
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
    path(
        "declarations-cotisations/nouvelle/",
        views.DeclarationCotisationsCreateView.as_view(),
        name="declaration-cotisations-create",
    ),
    path(
        "declarations-cotisations/generer-masse/",
        views.declarations_generer_masse,
        name="declaration-cotisations-generer-masse",
    ),
    path(
        "declarations-cotisations/<uuid:pk>/",
        views.DeclarationCotisationsDetailView.as_view(),
        name="declaration-cotisations-detail",
    ),
    path(
        "declarations-cotisations/<uuid:pk>/modifier/",
        views.DeclarationCotisationsUpdateView.as_view(),
        name="declaration-cotisations-edit",
    ),
    path(
        "declarations-cotisations/<uuid:pk>/calculer/",
        views.declaration_calculer,
        name="declaration-cotisations-calculer",
    ),
    path(
        "declarations-cotisations/<uuid:pk>/transmettre/",
        views.declaration_transmettre,
        name="declaration-cotisations-transmettre",
    ),
    path(
        "declarations-cotisations/<uuid:pk>/payer/",
        views.declaration_payer,
        name="declaration-cotisations-payer",
    ),
    path(
        "declarations-cotisations/<uuid:pk>/pdf/",
        views.declaration_generer_pdf,
        name="declaration-cotisations-pdf",
    ),
    path(
        "declarations-cotisations/<uuid:pk>/telecharger-pdf/",
        views.declaration_telecharger_pdf,
        name="declaration-cotisations-telecharger-pdf",
    ),
    path(
        "declarations-cotisations/<uuid:pk>/preview-pdf/",
        views.declaration_preview_pdf,
        name="declaration-cotisations-preview-pdf",
    ),
    # Document Studio
    path("fiches/<uuid:pk>/studio/", views.fiche_studio, name="fiche-studio"),
    path("api/studio/fiche/preview/", views.fiche_studio_preview, name="fiche-studio-preview"),
    path("certificats/<uuid:pk>/studio/", views.certificat_studio, name="certificat-studio"),
    path("api/studio/certificat/preview/", views.certificat_studio_preview, name="certificat-studio-preview"),
    path("certificats-travail/<uuid:pk>/studio/", views.certificat_travail_studio, name="certificat-travail-studio"),
    path("api/studio/certificat-travail/preview/", views.certificat_travail_studio_preview, name="certificat-travail-studio-preview"),
    path("declarations-cotisations/<uuid:pk>/studio/", views.declaration_studio, name="declaration-studio"),
    path("api/studio/declaration/preview/", views.declaration_studio_preview, name="declaration-studio-preview"),
]
