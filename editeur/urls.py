"""
URLs pour l'application Éditeur Collaboratif.
"""

from django.urls import path
from . import views

app_name = 'editeur'

urlpatterns = [
    # Dashboard
    path('', views.EditeurDashboardView.as_view(), name='dashboard'),

    # Documents collaboratifs
    path('documents/', views.DocumentListView.as_view(), name='document_list'),
    path('documents/nouveau/', views.DocumentCreateView.as_view(), name='document_create'),
    path('documents/<uuid:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('documents/<uuid:pk>/editer/', views.DocumentEditView.as_view(), name='document_edit'),
    path('documents/<uuid:pk>/supprimer/', views.DocumentDeleteView.as_view(), name='document_delete'),

    # Export
    path('documents/<uuid:pk>/export/<str:format>/', views.DocumentExportView.as_view(), name='document_export'),
    path('documents/<uuid:pk>/archiver/', views.DocumentArchiveToGEDView.as_view(), name='document_archive'),

    # Partage
    path('documents/<uuid:pk>/partager/', views.PartageCreateView.as_view(), name='partage_create'),
    path('documents/<uuid:pk>/partage/<uuid:partage_pk>/supprimer/', views.PartageDeleteView.as_view(), name='partage_delete'),

    # Liens publics
    path('documents/<uuid:pk>/lien-public/', views.LienPublicCreateView.as_view(), name='lien_public_create'),
    path('public/<str:token>/', views.LienPublicView.as_view(), name='lien_public'),

    # Modèles
    path('modeles/', views.ModeleListView.as_view(), name='modele_list'),
    path('modeles/nouveau/', views.ModeleCreateView.as_view(), name='modele_create'),

    # Webhook Docs
    path('webhook/docs/', views.DocsWebhookView.as_view(), name='webhook_docs'),
]
