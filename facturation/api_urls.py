# apps/facturation/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    PrestationViewSet,
    TimeTrackingViewSet,
    FactureViewSet,
    LigneFactureViewSet,
    PaiementViewSet,
    RelanceViewSet,
)

app_name = "facturation"

router = DefaultRouter()
router.register(r"prestations", PrestationViewSet, basename="prestation")
router.register(r"temps", TimeTrackingViewSet, basename="temps")
router.register(r"factures", FactureViewSet, basename="facture")
router.register(r"lignes", LigneFactureViewSet, basename="ligne")
router.register(r"paiements", PaiementViewSet, basename="paiement")
router.register(r"relances", RelanceViewSet, basename="relance")

urlpatterns = [
    path("", include(router.urls)),
]

"""
API Endpoints:

PRESTATIONS:
- GET    /api/v1/facturation/prestations/              Liste prestations
- POST   /api/v1/facturation/prestations/              Créer prestation
- GET    /api/v1/facturation/prestations/{id}/         Détail prestation
- PUT    /api/v1/facturation/prestations/{id}/         Modifier prestation
- DELETE /api/v1/facturation/prestations/{id}/         Supprimer prestation

TIME TRACKING:
- GET    /api/v1/facturation/temps/                    Liste temps
- POST   /api/v1/facturation/temps/                    Créer entrée temps
- GET    /api/v1/facturation/temps/{id}/               Détail temps
- PUT    /api/v1/facturation/temps/{id}/               Modifier temps
- DELETE /api/v1/facturation/temps/{id}/               Supprimer temps
- GET    /api/v1/facturation/temps/non_factures/       Temps non facturés
- POST   /api/v1/facturation/temps/{id}/valider/       Valider temps

FACTURES:
- GET    /api/v1/facturation/factures/                 Liste factures
- POST   /api/v1/facturation/factures/                 Créer facture
- GET    /api/v1/facturation/factures/{id}/            Détail facture
- PUT    /api/v1/facturation/factures/{id}/            Modifier facture
- DELETE /api/v1/facturation/factures/{id}/            Supprimer facture
- GET    /api/v1/facturation/factures/{id}/lignes/     Lignes de la facture
- POST   /api/v1/facturation/factures/{id}/calculer/   Recalculer totaux
- POST   /api/v1/facturation/factures/{id}/valider/    Valider facture
- POST   /api/v1/facturation/factures/{id}/envoyer/    Envoyer facture
- POST   /api/v1/facturation/factures/{id}/generer_pdf/ Générer PDF
- POST   /api/v1/facturation/factures/{id}/generer_qr/  Générer QR-Bill
- GET    /api/v1/facturation/factures/impayees/        Factures impayées
- GET    /api/v1/facturation/factures/en_retard/       Factures en retard

LIGNES FACTURE:
- GET    /api/v1/facturation/lignes/                   Liste lignes
- POST   /api/v1/facturation/lignes/                   Créer ligne
- GET    /api/v1/facturation/lignes/{id}/              Détail ligne
- PUT    /api/v1/facturation/lignes/{id}/              Modifier ligne
- DELETE /api/v1/facturation/lignes/{id}/              Supprimer ligne

PAIEMENTS:
- GET    /api/v1/facturation/paiements/                Liste paiements
- POST   /api/v1/facturation/paiements/                Enregistrer paiement
- GET    /api/v1/facturation/paiements/{id}/           Détail paiement
- PUT    /api/v1/facturation/paiements/{id}/           Modifier paiement
- DELETE /api/v1/facturation/paiements/{id}/           Supprimer paiement
- POST   /api/v1/facturation/paiements/{id}/valider/   Valider paiement

RELANCES:
- GET    /api/v1/facturation/relances/                 Liste relances
- POST   /api/v1/facturation/relances/                 Créer relance
- GET    /api/v1/facturation/relances/{id}/            Détail relance
- PUT    /api/v1/facturation/relances/{id}/            Modifier relance
- DELETE /api/v1/facturation/relances/{id}/            Supprimer relance
- POST   /api/v1/facturation/relances/{id}/envoyer/    Envoyer relance
"""
