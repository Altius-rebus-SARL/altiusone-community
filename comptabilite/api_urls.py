# apps/comptabilite/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    PlanComptableViewSet,
    CompteViewSet,
    JournalViewSet,
    EcritureComptableViewSet,
    PieceComptableViewSet,
    LettrageViewSet,
    RapportsViewSet,
)

app_name = "comptabilite"

router = DefaultRouter()
router.register(r"plans-comptables", PlanComptableViewSet, basename="plan-comptable")
router.register(r"comptes", CompteViewSet, basename="compte")
router.register(r"journaux", JournalViewSet, basename="journal")
router.register(r"ecritures", EcritureComptableViewSet, basename="ecriture")
router.register(r"pieces", PieceComptableViewSet, basename="piece")
router.register(r"lettrages", LettrageViewSet, basename="lettrage")
router.register(r"rapports", RapportsViewSet, basename="rapport")

urlpatterns = [
    path("", include(router.urls)),
]

"""
API Endpoints:

PLANS COMPTABLES:
- GET    /api/v1/comptabilite/plans-comptables/          Liste plans comptables
- POST   /api/v1/comptabilite/plans-comptables/          Créer plan comptable
- GET    /api/v1/comptabilite/plans-comptables/{id}/     Détail plan
- PUT    /api/v1/comptabilite/plans-comptables/{id}/     Modifier plan
- DELETE /api/v1/comptabilite/plans-comptables/{id}/     Supprimer plan
- GET    /api/v1/comptabilite/plans-comptables/templates/  Plans templates
- POST   /api/v1/comptabilite/plans-comptables/{id}/dupliquer/  Dupliquer plan

COMPTES:
- GET    /api/v1/comptabilite/comptes/                   Liste des comptes
- POST   /api/v1/comptabilite/comptes/                   Créer un compte
- GET    /api/v1/comptabilite/comptes/{id}/              Détail compte
- PUT    /api/v1/comptabilite/comptes/{id}/              Modifier compte
- DELETE /api/v1/comptabilite/comptes/{id}/              Supprimer compte
- GET    /api/v1/comptabilite/comptes/tree/              Arbre hiérarchique
- GET    /api/v1/comptabilite/comptes/{id}/solde/        Solde détaillé

JOURNAUX:
- GET    /api/v1/comptabilite/journaux/                  Liste des journaux
- POST   /api/v1/comptabilite/journaux/                  Créer un journal
- GET    /api/v1/comptabilite/journaux/{id}/             Détail journal
- PUT    /api/v1/comptabilite/journaux/{id}/             Modifier journal
- DELETE /api/v1/comptabilite/journaux/{id}/             Supprimer journal
- POST   /api/v1/comptabilite/journaux/{id}/generer_numero/  Générer n° pièce

ÉCRITURES COMPTABLES:
- GET    /api/v1/comptabilite/ecritures/                 Liste des écritures
- POST   /api/v1/comptabilite/ecritures/                 Créer une écriture
- GET    /api/v1/comptabilite/ecritures/{id}/            Détail écriture
- PUT    /api/v1/comptabilite/ecritures/{id}/            Modifier écriture
- DELETE /api/v1/comptabilite/ecritures/{id}/            Supprimer écriture
- GET    /api/v1/comptabilite/ecritures/par_periode/     Écritures par période
- POST   /api/v1/comptabilite/ecritures/{id}/valider/    Valider écriture
- POST   /api/v1/comptabilite/ecritures/{id}/lettrer/    Lettrer écriture

PIÈCES COMPTABLES:
- GET    /api/v1/comptabilite/pieces/                    Liste des pièces
- POST   /api/v1/comptabilite/pieces/                    Créer une pièce
- GET    /api/v1/comptabilite/pieces/{id}/               Détail pièce
- PUT    /api/v1/comptabilite/pieces/{id}/               Modifier pièce
- DELETE /api/v1/comptabilite/pieces/{id}/               Supprimer pièce
- POST   /api/v1/comptabilite/pieces/{id}/recalculer/    Recalculer équilibre

LETTRAGES:
- GET    /api/v1/comptabilite/lettrages/                 Liste des lettrages
- POST   /api/v1/comptabilite/lettrages/                 Créer un lettrage
- GET    /api/v1/comptabilite/lettrages/{id}/            Détail lettrage
- DELETE /api/v1/comptabilite/lettrages/{id}/            Supprimer lettrage
- GET    /api/v1/comptabilite/lettrages/{id}/ecritures/  Écritures lettrées

RAPPORTS:
- GET    /api/v1/comptabilite/rapports/balance/          Balance des comptes
- GET    /api/v1/comptabilite/rapports/bilan/            Bilan
- GET    /api/v1/comptabilite/rapports/compte_resultats/ Compte de résultats
"""
