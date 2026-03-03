"""
URLs API REST pour l'application Éditeur Collaboratif.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'documents', api_views.DocumentCollaboratifViewSet, basename='document')
router.register(r'modeles', api_views.ModeleDocumentViewSet, basename='modele')

urlpatterns = [
    # ViewSets
    path('', include(router.urls)),

    # Endpoints spécifiques
    path('health/', api_views.DocsHealthView.as_view(), name='docs_health'),
    path('documents/<uuid:pk>/token/', api_views.DocumentTokenView.as_view(), name='document_token'),
    path('documents/<uuid:pk>/collaborators/', api_views.CollaboratorsView.as_view(), name='document_collaborators'),
]
