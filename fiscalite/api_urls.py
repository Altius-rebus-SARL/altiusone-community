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
    ReclamationFiscaleViewSet,
    UtilisationPerteViewSet,
    AcompteFiscalViewSet,
    ImpotAnticipeViewSet,
)

app_name = "fiscalite"

router = DefaultRouter()
router.register(r"declarations", DeclarationFiscaleViewSet, basename="declaration")
router.register(r"annexes", AnnexeFiscaleViewSet, basename="annexe")
router.register(r"corrections", CorrectionFiscaleViewSet, basename="correction")
router.register(r"reports-pertes", ReportPerteViewSet, basename="report-perte")
router.register(r"taux", TauxImpositionViewSet, basename="taux")
router.register(r"optimisations", OptimisationFiscaleViewSet, basename="optimisation")
router.register(r"reclamations", ReclamationFiscaleViewSet, basename="reclamation")
router.register(r"utilisations-pertes", UtilisationPerteViewSet, basename="utilisation-perte")
router.register(r"acomptes", AcompteFiscalViewSet, basename="acompte-fiscal")
router.register(r"impots-anticipes", ImpotAnticipeViewSet, basename="impot-anticipe")

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
- GET    /api/v1/fiscalite/taux/preview-estv/          Preview taux ESTV (sans sauvegarde)
- POST   /api/v1/fiscalite/taux/fetch-estv/            Fetch + sauvegarde taux ESTV
- POST   /api/v1/fiscalite/taux/import-csv/            Import CSV fallback

OPTIMISATIONS FISCALES:
- GET    /api/v1/fiscalite/optimisations/              Liste optimisations
- POST   /api/v1/fiscalite/optimisations/              Créer optimisation
- GET    /api/v1/fiscalite/optimisations/{id}/         Détail optimisation
- PUT    /api/v1/fiscalite/optimisations/{id}/         Modifier optimisation
- DELETE /api/v1/fiscalite/optimisations/{id}/         Supprimer optimisation
"""
