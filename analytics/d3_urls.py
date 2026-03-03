# analytics/d3_urls.py
"""URLs pour les endpoints D3.js."""
from django.urls import path
from . import d3_views

urlpatterns = [
    path('plan-comptable/', d3_views.d3_plan_comptable, name='d3-plan-comptable'),
    path('flux-tresorerie/', d3_views.d3_flux_tresorerie, name='d3-flux-tresorerie'),
    path('calendrier-activite/', d3_views.d3_calendrier_activite, name='d3-calendrier-activite'),
    path('reseau-clients/', d3_views.d3_reseau_clients, name='d3-reseau-clients'),
    path('decomposition-salaires/', d3_views.d3_decomposition_salaires, name='d3-decomposition-salaires'),
    path('timeline-projets/', d3_views.d3_timeline_projets, name='d3-timeline-projets'),
]
