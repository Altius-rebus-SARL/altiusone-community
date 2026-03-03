from django.urls import path

from . import views

app_name = "projets"

urlpatterns = [
    # Positions
    path("mandats/<uuid:mandat_pk>/positions/", views.position_list_partial, name="position-list"),
    path("mandats/<uuid:mandat_pk>/positions/nouvelle/", views.position_create, name="position-create"),
    path("positions/<uuid:pk>/", views.position_detail, name="position-detail"),
    path("positions/<uuid:pk>/modifier/", views.position_update, name="position-update"),
    path("positions/<uuid:pk>/supprimer/", views.position_delete, name="position-delete"),

    # Operations
    path("positions/<uuid:position_pk>/operations/nouvelle/", views.operation_create, name="operation-create"),
    path("operations/<uuid:pk>/modifier/", views.operation_update, name="operation-update"),
    path("operations/<uuid:pk>/supprimer/", views.operation_delete, name="operation-delete"),
    path("operations/<uuid:pk>/statut/", views.operation_change_statut, name="operation-statut"),
    path("positions/<uuid:position_pk>/operations/reorder/", views.operation_reorder, name="operation-reorder"),
    path("operations/<uuid:pk>/notes/", views.operation_add_note, name="operation-note"),

    # Gantt / Timeline
    path("mandats/<uuid:mandat_pk>/gantt/", views.gantt_view, name="gantt-view"),
    path("mandats/<uuid:mandat_pk>/gantt/data/", views.gantt_data, name="gantt-data"),

    # Budget
    path("mandats/<uuid:mandat_pk>/budget/", views.budget_summary, name="budget-summary"),

    # Carte
    path("mandats/<uuid:mandat_pk>/carte/", views.map_view, name="map-view"),
    path("mandats/<uuid:mandat_pk>/carte/data/", views.map_data, name="map-data"),
]
