# core/import_export/urls.py
"""
URLs pour l'import/export de données.

Ces URLs fournissent:
- Des endpoints génériques pour tous les modèles enregistrés
- Des API endpoints pour les appels AJAX/REST
"""

from django.urls import path

from .views import (
    ImportView,
    ExportView,
    TemplateDownloadView,
    ImportResultsView,
    ImportAPIView,
    ExportAPIView,
    TemplateAPIView,
)

app_name = 'import_export'

urlpatterns = [
    # =========================================================================
    # Vues HTML (formulaires)
    # =========================================================================

    # Import avec formulaire
    # URL: /import-export/<app>/<model>/import/
    path(
        '<str:app_label>/<str:model_name>/import/',
        ImportView.as_view(),
        name='import'
    ),

    # Export direct (téléchargement)
    # URL: /import-export/<app>/<model>/export/?format=xlsx
    path(
        '<str:app_label>/<str:model_name>/export/',
        ExportView.as_view(),
        name='export'
    ),

    # Téléchargement du template
    # URL: /import-export/<app>/<model>/template/?format=xlsx
    path(
        '<str:app_label>/<str:model_name>/template/',
        TemplateDownloadView.as_view(),
        name='template'
    ),

    # Résultats d'import
    path(
        'results/',
        ImportResultsView.as_view(),
        name='results'
    ),

    # =========================================================================
    # API Endpoints (pour AJAX)
    # =========================================================================

    # API Import
    # POST /import-export/api/<app>/<model>/import/
    path(
        'api/<str:app_label>/<str:model_name>/import/',
        ImportAPIView.as_view(),
        name='api-import'
    ),

    # API Export
    # GET /import-export/api/<app>/<model>/export/?format=xlsx
    path(
        'api/<str:app_label>/<str:model_name>/export/',
        ExportAPIView.as_view(),
        name='api-export'
    ),

    # API Template
    # GET /import-export/api/<app>/<model>/template/?format=xlsx
    path(
        'api/<str:app_label>/<str:model_name>/template/',
        TemplateAPIView.as_view(),
        name='api-template'
    ),
]
