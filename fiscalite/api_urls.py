# apps/fiscalite/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    DeclarationFiscaleViewSet,
    AnnexeFiscaleViewSet,
    CorrectionFiscaleViewSet,
    ReportPerteViewSet,
    TauxImpositionViewSet,
    OptimisationFiscaleViewSet,
)

app_name = "fiscalite"

router = DefaultRouter()
router.register(r"fiscalite/declarations", DeclarationFiscaleViewSet, basename="fisc-declaration")
router.register(r"fiscalite/annexes", AnnexeFiscaleViewSet, basename="fisc-annexe")
router.register(r"fiscalite/corrections", CorrectionFiscaleViewSet, basename="fisc-correction")
router.register(r"fiscalite/reports-pertes", ReportPerteViewSet, basename="fisc-report-perte")
router.register(r"fiscalite/taux", TauxImpositionViewSet, basename="fisc-taux")
router.register(r"fiscalite/optimisations", OptimisationFiscaleViewSet, basename="fisc-optimisation")

urlpatterns = [
    path("", include(router.urls)),
]

"""
API Endpoints:

DÉCLARATIONS FISCALES:
- GET    /api/v1/fiscalite/declarations/               Liste déclarations
- POST   /api/v1/fiscalite/declarations/               Créer déclaration
- GET    /api/v1/fiscalite/declarations/{id}/          Détail déclaration
- PUT    /api/v1/fiscalite/declarations/{id}/          Modifier déclaration
- DELETE /api/v1/fiscalite/declarations/{id}/          Supprimer déclaration
- GET    /api/v1/fiscalite/declarations/{id}/annexes/  Annexes déclaration
- POST   /api/v1/fiscalite/declarations/{id}/valider/  Valider déclaration
- POST   /api/v1/fiscalite/declarations/{id}/soumettre/ Soumettre

ANNEXES FISCALES:
- GET    /api/v1/fiscalite/annexes/                    Liste annexes
- POST   /api/v1/fiscalite/annexes/                    Créer annexe
- GET    /api/v1/fiscalite/annexes/{id}/               Détail annexe
- PUT    /api/v1/fiscalite/annexes/{id}/               Modifier annexe
- DELETE /api/v1/fiscalite/annexes/{id}/               Supprimer annexe

CORRECTIONS FISCALES:
- GET    /api/v1/fiscalite/corrections/                Liste corrections
- POST   /api/v1/fiscalite/corrections/                Créer correction
- GET    /api/v1/fiscalite/corrections/{id}/           Détail correction
- PUT    /api/v1/fiscalite/corrections/{id}/           Modifier correction
- DELETE /api/v1/fiscalite/corrections/{id}/           Supprimer correction

REPORTS DE PERTES:
- GET    /api/v1/fiscalite/reports-pertes/             Liste reports
- POST   /api/v1/fiscalite/reports-pertes/             Créer report
- GET    /api/v1/fiscalite/reports-pertes/{id}/        Détail report
- PUT    /api/v1/fiscalite/reports-pertes/{id}/        Modifier report
- DELETE /api/v1/fiscalite/reports-pertes/{id}/        Supprimer report
- GET    /api/v1/fiscalite/reports-pertes/disponibles/ Reports disponibles

TAUX D'IMPOSITION:
- GET    /api/v1/fiscalite/taux/                       Liste taux
- POST   /api/v1/fiscalite/taux/                       Créer taux
- GET    /api/v1/fiscalite/taux/{id}/                  Détail taux
- PUT    /api/v1/fiscalite/taux/{id}/                  Modifier taux
- DELETE /api/v1/fiscalite/taux/{id}/                  Supprimer taux
- POST   /api/v1/fiscalite/taux/{id}/calculer_impot/   Calculer impôt

OPTIMISATIONS FISCALES:
- GET    /api/v1/fiscalite/optimisations/              Liste optimisations
- POST   /api/v1/fiscalite/optimisations/              Créer optimisation
- GET    /api/v1/fiscalite/optimisations/{id}/         Détail optimisation
- PUT    /api/v1/fiscalite/optimisations/{id}/         Modifier optimisation
- DELETE /api/v1/fiscalite/optimisations/{id}/         Supprimer optimisation
"""
