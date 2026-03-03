# graph/urls.py
from django.urls import path
from . import views

app_name = 'graph'

urlpatterns = [
    # Explorateur principal
    path('', views.ExplorerView.as_view(), name='explorer'),

    # Ontologie
    path('ontologie/', views.OntologieListView.as_view(), name='ontologie-list'),
    path('ontologie/creer/', views.OntologieCreateView.as_view(), name='ontologie-create'),
    path('ontologie/<uuid:pk>/modifier/', views.OntologieUpdateView.as_view(), name='ontologie-update'),

    # Entités
    path('entites/', views.EntiteListView.as_view(), name='entite-list'),
    path('entites/creer/', views.EntiteCreateView.as_view(), name='entite-create'),
    path('entites/<uuid:pk>/', views.EntiteDetailView.as_view(), name='entite-detail'),
    path('entites/<uuid:pk>/modifier/', views.EntiteUpdateView.as_view(), name='entite-update'),

    # Relations
    path('relations/creer/', views.RelationCreateView.as_view(), name='relation-create'),

    # Anomalies
    path('anomalies/', views.AnomalieListView.as_view(), name='anomalie-list'),
    path('anomalies/<uuid:pk>/', views.AnomalieDetailView.as_view(), name='anomalie-detail'),

    # Import
    path('import/', views.ImportView.as_view(), name='import'),

    # Recherche sémantique
    path('recherche/', views.RechercheView.as_view(), name='recherche'),
]
