# apps/analytics/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    TableauBordViewSet,
    IndicateurViewSet,
    ValeurIndicateurViewSet,
    RapportViewSet,
    PlanificationRapportViewSet,
    ComparaisonPeriodeViewSet,
    AlerteMetriqueViewSet,
    ExportDonneesViewSet,
    dashboard_data,
)

router = DefaultRouter()
router.register(r"tableaux-bord", TableauBordViewSet, basename="tableau-bord")
router.register(r"indicateurs", IndicateurViewSet, basename="indicateur")
router.register(r"valeurs", ValeurIndicateurViewSet, basename="valeur")
router.register(r"rapports", RapportViewSet, basename="rapport")
router.register(
    r"planifications", PlanificationRapportViewSet, basename="planification"
)
router.register(r"comparaisons", ComparaisonPeriodeViewSet, basename="comparaison")
router.register(r"alertes", AlerteMetriqueViewSet, basename="alerte")
router.register(r"exports", ExportDonneesViewSet, basename="export")

urlpatterns = [
    path("dashboard/", dashboard_data, name="api-dashboard-data"),
    path("", include(router.urls)),
]

"""
API Endpoints:

TABLEAUX DE BORD:
- GET    /api/v1/analytics/tableaux-bord/              Liste tableaux
- POST   /api/v1/analytics/tableaux-bord/              Créer tableau
- GET    /api/v1/analytics/tableaux-bord/{id}/         Détail tableau
- PUT    /api/v1/analytics/tableaux-bord/{id}/         Modifier tableau
- DELETE /api/v1/analytics/tableaux-bord/{id}/         Supprimer tableau
- GET    /api/v1/analytics/tableaux-bord/{id}/data/    Données tableau
- POST   /api/v1/analytics/tableaux-bord/{id}/dupliquer/ Dupliquer

INDICATEURS:
- GET    /api/v1/analytics/indicateurs/                Liste indicateurs
- POST   /api/v1/analytics/indicateurs/                Créer indicateur
- GET    /api/v1/analytics/indicateurs/{id}/           Détail indicateur
- PUT    /api/v1/analytics/indicateurs/{id}/           Modifier indicateur
- DELETE /api/v1/analytics/indicateurs/{id}/           Supprimer indicateur
- GET    /api/v1/analytics/indicateurs/{id}/valeurs/   Valeurs indicateur
- POST   /api/v1/analytics/indicateurs/{id}/calculer/  Calculer valeur

VALEURS INDICATEURS:
- GET    /api/v1/analytics/valeurs/                    Liste valeurs
- POST   /api/v1/analytics/valeurs/                    Créer valeur
- GET    /api/v1/analytics/valeurs/{id}/               Détail valeur
- PUT    /api/v1/analytics/valeurs/{id}/               Modifier valeur
- DELETE /api/v1/analytics/valeurs/{id}/               Supprimer valeur

RAPPORTS:
- GET    /api/v1/analytics/rapports/                   Liste rapports
- POST   /api/v1/analytics/rapports/                   Générer rapport
- GET    /api/v1/analytics/rapports/{id}/              Détail rapport
- DELETE /api/v1/analytics/rapports/{id}/              Supprimer rapport
- GET    /api/v1/analytics/rapports/{id}/download/     Télécharger rapport
- POST   /api/v1/analytics/rapports/{id}/envoyer/      Envoyer par email

PLANIFICATIONS RAPPORTS:
- GET    /api/v1/analytics/planifications/             Liste planifications
- POST   /api/v1/analytics/planifications/             Créer planification
- GET    /api/v1/analytics/planifications/{id}/        Détail planification
- PUT    /api/v1/analytics/planifications/{id}/        Modifier planification
- DELETE /api/v1/analytics/planifications/{id}/        Supprimer planification

COMPARAISONS PÉRIODES:
- GET    /api/v1/analytics/comparaisons/               Liste comparaisons
- POST   /api/v1/analytics/comparaisons/               Créer comparaison
- GET    /api/v1/analytics/comparaisons/{id}/          Détail comparaison
- DELETE /api/v1/analytics/comparaisons/{id}/          Supprimer comparaison

ALERTES MÉTRIQUES:
- GET    /api/v1/analytics/alertes/                    Liste alertes
- POST   /api/v1/analytics/alertes/                    Créer alerte
- GET    /api/v1/analytics/alertes/{id}/               Détail alerte
- DELETE /api/v1/analytics/alertes/{id}/               Supprimer alerte
- POST   /api/v1/analytics/alertes/{id}/acquitter/     Acquitter alerte
- GET    /api/v1/analytics/alertes/actives/            Alertes actives

EXPORTS DONNÉES:
- GET    /api/v1/analytics/exports/                    Liste exports
- POST   /api/v1/analytics/exports/                    Demander export
- GET    /api/v1/analytics/exports/{id}/               Détail export
- DELETE /api/v1/analytics/exports/{id}/               Supprimer export
- GET    /api/v1/analytics/exports/{id}/download/      Télécharger export
"""
