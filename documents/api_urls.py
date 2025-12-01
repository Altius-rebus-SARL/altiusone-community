# apps/documents/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    DossierViewSet,
    TypeDocumentViewSet,
    DocumentViewSet,
)

app_name = "documents"

router = DefaultRouter()
router.register(r"dossiers", DossierViewSet, basename="dossier")
router.register(r"types", TypeDocumentViewSet, basename="type")
router.register(r"documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("", include(router.urls)),
]

"""
API Endpoints:

DOSSIERS:
- GET    /api/v1/documents/dossiers/                   Liste dossiers
- POST   /api/v1/documents/dossiers/                   Créer dossier
- GET    /api/v1/documents/dossiers/{id}/              Détail dossier
- PUT    /api/v1/documents/dossiers/{id}/              Modifier dossier
- DELETE /api/v1/documents/dossiers/{id}/              Supprimer dossier
- GET    /api/v1/documents/dossiers/tree/              Arbre dossiers
- GET    /api/v1/documents/dossiers/{id}/documents/    Documents du dossier

TYPES DOCUMENT:
- GET    /api/v1/documents/types/                      Liste types
- POST   /api/v1/documents/types/                      Créer type
- GET    /api/v1/documents/types/{id}/                 Détail type
- PUT    /api/v1/documents/types/{id}/                 Modifier type
- DELETE /api/v1/documents/types/{id}/                 Supprimer type

DOCUMENTS:
- GET    /api/v1/documents/documents/                  Liste documents
- POST   /api/v1/documents/documents/                  Upload document
- GET    /api/v1/documents/documents/{id}/             Détail document
- PUT    /api/v1/documents/documents/{id}/             Modifier document
- DELETE /api/v1/documents/documents/{id}/             Supprimer document
- POST   /api/v1/documents/documents/recherche/        Recherche documents
- POST   /api/v1/documents/documents/{id}/ocr/         Lancer OCR
- POST   /api/v1/documents/documents/{id}/classifier/  Classifier document
- POST   /api/v1/documents/documents/{id}/extraire/    Extraire métadonnées
- POST   /api/v1/documents/documents/{id}/valider/     Valider document
- GET    /api/v1/documents/documents/{id}/download/    Télécharger document
- GET    /api/v1/documents/documents/{id}/preview/     Aperçu document
"""
