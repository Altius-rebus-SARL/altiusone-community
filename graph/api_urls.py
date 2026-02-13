# graph/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    OntologieTypeViewSet,
    EntiteViewSet,
    RelationViewSet,
    AnomalieViewSet,
    RequeteSauvegardeeViewSet,
    recherche_semantique,
    graph_stats,
    import_csv_view,
    import_document_view,
    detecter_anomalies_view,
)

app_name = "graph-api"

router = DefaultRouter()
router.register(r"graph-types", OntologieTypeViewSet, basename="graph-type")
router.register(r"graph-entites", EntiteViewSet, basename="graph-entite")
router.register(r"graph-relations", RelationViewSet, basename="graph-relation")
router.register(r"graph-anomalies", AnomalieViewSet, basename="graph-anomalie")
router.register(r"graph-requetes", RequeteSauvegardeeViewSet, basename="graph-requete")

graph_extra_urls = [
    path("recherche/", recherche_semantique, name="graph-recherche"),
    path("stats/", graph_stats, name="graph-stats"),
    path("import/csv/", import_csv_view, name="graph-import-csv"),
    path("import/document/", import_document_view, name="graph-import-document"),
    path("detecter-anomalies/", detecter_anomalies_view, name="graph-detecter-anomalies"),
]

urlpatterns = [
    path("", include(router.urls)),
] + graph_extra_urls
