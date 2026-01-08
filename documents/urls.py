# documents/urls.py
from django.urls import path
from django.views.decorators.http import require_http_methods
from . import views

app_name = "documents"

urlpatterns = [
    # Chat AI
    path("chat/", views.ChatView.as_view(), name="chat"),

    # Dossiers
    path("dossiers/", views.DossierListView.as_view(), name="dossier-list"),
    path("dossiers/nouveau/", views.DossierCreateView.as_view(), name="dossier-create"),
    path(
        "dossiers/<uuid:pk>/", views.DossierDetailView.as_view(), name="dossier-detail"
    ),
    # Documents
    path("", views.DocumentListView.as_view(), name="document-list"),
    path("upload/", views.DocumentUploadView.as_view(), name="document-upload"),
    path("<uuid:pk>/", views.DocumentDetailView.as_view(), name="document-detail"),
    path(
        "<uuid:pk>/telecharger/",
        views.document_telecharger,
        name="document-telecharger",
    ),
    path(
        "<uuid:pk>/apercu/",
        views.document_apercu,
        name="document-apercu",
    ),
    path("<uuid:pk>/valider/", views.document_valider, name="document-valider"),
    path("<uuid:pk>/ocr/", views.document_ocr, name="document-ocr"),
    # Recherche
    path("recherche/", views.recherche_documents, name="recherche"),
    # Catégories
    # Catégories
    path(
        "categories/", views.CategorieDocumentListView.as_view(), name="categorie-list"
    ),
    path(
        "categories/nouvelle/",
        views.CategorieDocumentCreateView.as_view(),
        name="categorie-create",
    ),
    path(
        "categories/create-ajax/",
        views.categorie_document_create_ajax,
        name="categorie-create-ajax",
    ),
    path(
        "categories/<uuid:pk>/",
        views.CategorieDocumentDetailView.as_view(),
        name="categorie-detail",
    ),
    path(
        "categories/<uuid:pk>/modifier/",
        views.CategorieDocumentUpdateView.as_view(),
        name="categorie-update",
    ),
    path(
        "categories/<uuid:pk>/update-ajax/",
        views.categorie_document_update_ajax,
        name="categorie-update-ajax",
    ),
    path(
        "categories/<uuid:pk>/get-data/",
        views.categorie_document_get_data,
        name="categorie-get-data",
    ),
    # Types
    path("types/", views.TypeDocumentListView.as_view(), name="type-list"),
    path("types/nouveau/", views.TypeDocumentCreateView.as_view(), name="type-create"),
    path(
        "types/create-ajax/", views.type_document_create_ajax, name="type-create-ajax"
    ),
    path(
        "types/<uuid:pk>/", views.TypeDocumentDetailView.as_view(), name="type-detail"
    ),
    path(
        "types/<uuid:pk>/modifier/",
        views.TypeDocumentUpdateView.as_view(),
        name="type-update",
    ),
    path(
        "types/<uuid:pk>/update-ajax/",
        views.type_document_update_ajax,
        name="type-update-ajax",
    ),
    path(
        "types/<uuid:pk>/get-data/", views.type_document_get_data, name="type-get-data"
    ),
    # API AJAX pour filtrage dynamique
    path(
        "api/mandat/<uuid:mandat_pk>/dossiers/",
        views.api_dossiers_par_mandat,
        name="api-dossiers-mandat",
    ),
    path(
        "api/dossiers/",
        views.api_tous_dossiers,
        name="api-tous-dossiers",
    ),
]
