# apps/tva/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    RegimeFiscalViewSet,
    ConfigurationTVAViewSet,
    TauxTVAViewSet,
    CodeTVAViewSet,
    DeclarationTVAViewSet,
    LigneTVAViewSet,
    OperationTVAViewSet,
    CorrectionTVAViewSet,
)

app_name = "tva"

router = DefaultRouter()
router.register(r"regimes", RegimeFiscalViewSet, basename="regime")
router.register(r"configurations", ConfigurationTVAViewSet, basename="configuration")
router.register(r"taux", TauxTVAViewSet, basename="taux")
router.register(r"codes", CodeTVAViewSet, basename="code")
router.register(r"declarations", DeclarationTVAViewSet, basename="declaration")
router.register(r"lignes", LigneTVAViewSet, basename="ligne")
router.register(r"operations", OperationTVAViewSet, basename="operation")
router.register(r"corrections", CorrectionTVAViewSet, basename="correction")

urlpatterns = [
    path("", include(router.urls)),
]

"""
API Endpoints:

CONFIGURATION TVA:
- GET    /api/v1/tva/configurations/                    Liste configurations
- POST   /api/v1/tva/configurations/                    Créer configuration
- GET    /api/v1/tva/configurations/{id}/               Détail configuration
- PUT    /api/v1/tva/configurations/{id}/               Modifier configuration
- DELETE /api/v1/tva/configurations/{id}/               Supprimer configuration

TAUX TVA:
- GET    /api/v1/tva/taux/                              Liste des taux
- POST   /api/v1/tva/taux/                              Créer un taux
- GET    /api/v1/tva/taux/{id}/                         Détail taux
- PUT    /api/v1/tva/taux/{id}/                         Modifier taux
- DELETE /api/v1/tva/taux/{id}/                         Supprimer taux
- GET    /api/v1/tva/taux/actifs/                       Taux actuellement valides

CODES TVA:
- GET    /api/v1/tva/codes/                             Liste des codes
- POST   /api/v1/tva/codes/                             Créer un code
- GET    /api/v1/tva/codes/{id}/                        Détail code
- PUT    /api/v1/tva/codes/{id}/                        Modifier code
- DELETE /api/v1/tva/codes/{id}/                        Supprimer code

DÉCLARATIONS TVA:
- GET    /api/v1/tva/declarations/                      Liste déclarations
- POST   /api/v1/tva/declarations/                      Créer déclaration
- GET    /api/v1/tva/declarations/{id}/                 Détail déclaration
- PUT    /api/v1/tva/declarations/{id}/                 Modifier déclaration
- DELETE /api/v1/tva/declarations/{id}/                 Supprimer déclaration
- GET    /api/v1/tva/declarations/{id}/lignes/          Lignes de la déclaration
- POST   /api/v1/tva/declarations/{id}/calculer/        Calculer montants
- POST   /api/v1/tva/declarations/{id}/valider/         Valider déclaration
- POST   /api/v1/tva/declarations/{id}/soumettre/       Soumettre à l'AFC
- POST   /api/v1/tva/declarations/{id}/generer_xml/     Générer fichier XML

LIGNES TVA:
- GET    /api/v1/tva/lignes/                            Liste des lignes
- POST   /api/v1/tva/lignes/                            Créer une ligne
- GET    /api/v1/tva/lignes/{id}/                       Détail ligne
- PUT    /api/v1/tva/lignes/{id}/                       Modifier ligne
- DELETE /api/v1/tva/lignes/{id}/                       Supprimer ligne
- POST   /api/v1/tva/lignes/{id}/calculer/              Calculer montant TVA

OPÉRATIONS TVA:
- GET    /api/v1/tva/operations/                        Liste opérations
- POST   /api/v1/tva/operations/                        Créer opération
- GET    /api/v1/tva/operations/{id}/                   Détail opération
- PUT    /api/v1/tva/operations/{id}/                   Modifier opération
- DELETE /api/v1/tva/operations/{id}/                   Supprimer opération
- GET    /api/v1/tva/operations/non_integrees/          Opérations non intégrées
- POST   /api/v1/tva/operations/integrer/               Intégrer opérations

CORRECTIONS TVA:
- GET    /api/v1/tva/corrections/                       Liste corrections
- POST   /api/v1/tva/corrections/                       Créer correction
- GET    /api/v1/tva/corrections/{id}/                  Détail correction
- PUT    /api/v1/tva/corrections/{id}/                  Modifier correction
- DELETE /api/v1/tva/corrections/{id}/                  Supprimer correction
"""
