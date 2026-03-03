# apps/modelforms/api_urls.py
"""
Routes API pour le module Model-Driven Forms.

Endpoints:
- /api/v1/modelforms/configurations/     - Configurations CRUD
- /api/v1/modelforms/submissions/        - Soumissions CRUD
- /api/v1/modelforms/templates/          - Templates CRUD
- /api/v1/modelforms/introspection/      - Introspection modèles
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    FormConfigurationViewSet,
    FormSubmissionViewSet,
    IntrospectionViewSet,
    FormTemplateViewSet,
)

app_name = 'modelforms'

router = DefaultRouter()
router.register(r'configurations', FormConfigurationViewSet, basename='configuration')
router.register(r'submissions', FormSubmissionViewSet, basename='submission')
router.register(r'templates', FormTemplateViewSet, basename='template')
router.register(r'introspection', IntrospectionViewSet, basename='introspection')

urlpatterns = [
    path('', include(router.urls)),
]


"""
API Endpoints:

CONFIGURATIONS:
- GET    /api/v1/modelforms/configurations/                    Liste des configurations
- POST   /api/v1/modelforms/configurations/                    Créer une configuration
- GET    /api/v1/modelforms/configurations/{id}/               Détail configuration
- PUT    /api/v1/modelforms/configurations/{id}/               Modifier configuration
- PATCH  /api/v1/modelforms/configurations/{id}/               Modifier partiellement
- DELETE /api/v1/modelforms/configurations/{id}/               Supprimer configuration
- GET    /api/v1/modelforms/configurations/{id}/schema/        Schéma complet pour rendu
- POST   /api/v1/modelforms/configurations/{id}/duplicate/     Dupliquer configuration

SUBMISSIONS:
- GET    /api/v1/modelforms/submissions/                       Liste des soumissions
- POST   /api/v1/modelforms/submissions/                       Créer une soumission
- GET    /api/v1/modelforms/submissions/{id}/                  Détail soumission
- PUT    /api/v1/modelforms/submissions/{id}/                  Modifier soumission
- DELETE /api/v1/modelforms/submissions/{id}/                  Supprimer soumission
- POST   /api/v1/modelforms/submissions/{id}/validate/         Valider soumission
- POST   /api/v1/modelforms/submissions/{id}/reject/           Rejeter soumission
- GET    /api/v1/modelforms/submissions/pending/               Soumissions en attente

TEMPLATES:
- GET    /api/v1/modelforms/templates/                         Liste des templates
- POST   /api/v1/modelforms/templates/                         Créer un template
- GET    /api/v1/modelforms/templates/{id}/                    Détail template
- PUT    /api/v1/modelforms/templates/{id}/                    Modifier template
- DELETE /api/v1/modelforms/templates/{id}/                    Supprimer template
- POST   /api/v1/modelforms/templates/{id}/instantiate/        Créer config depuis template

INTROSPECTION:
- GET    /api/v1/modelforms/introspection/models/              Modèles disponibles
- GET    /api/v1/modelforms/introspection/schema/{model}/      Schéma d'un modèle
- GET    /api/v1/modelforms/introspection/json-schema/{model}/ JSON Schema d'un modèle
"""
