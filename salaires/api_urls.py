# apps/salaires/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    EmployeViewSet,
    TauxCotisationViewSet,
    FicheSalaireViewSet,
    CertificatSalaireViewSet,
    DeclarationCotisationsViewSet,
)

app_name = "salaires"

router = DefaultRouter()
router.register(r"salaires/employes", EmployeViewSet, basename="salaires-employe")
router.register(r"salaires/taux-cotisations", TauxCotisationViewSet, basename="salaires-taux-cotisation")
router.register(r"salaires/fiches", FicheSalaireViewSet, basename="salaires-fiche")
router.register(r"salaires/certificats", CertificatSalaireViewSet, basename="salaires-certificat")
router.register(r"salaires/declarations", DeclarationCotisationsViewSet, basename="salaires-declaration")

urlpatterns = [
    path("", include(router.urls)),
]

"""
API Endpoints:

EMPLOYÉS:
- GET    /api/v1/salaires/employes/                     Liste employés
- POST   /api/v1/salaires/employes/                     Créer employé
- GET    /api/v1/salaires/employes/{id}/                Détail employé
- PUT    /api/v1/salaires/employes/{id}/                Modifier employé
- DELETE /api/v1/salaires/employes/{id}/                Supprimer employé
- GET    /api/v1/salaires/employes/{id}/fiches_salaire/ Fiches de l'employé
- GET    /api/v1/salaires/employes/actifs/              Employés actifs uniquement

TAUX COTISATIONS:
- GET    /api/v1/salaires/taux-cotisations/             Liste taux
- POST   /api/v1/salaires/taux-cotisations/             Créer taux
- GET    /api/v1/salaires/taux-cotisations/{id}/        Détail taux
- PUT    /api/v1/salaires/taux-cotisations/{id}/        Modifier taux
- DELETE /api/v1/salaires/taux-cotisations/{id}/        Supprimer taux
- GET    /api/v1/salaires/taux-cotisations/actifs/      Taux actuellement valides

FICHES DE SALAIRE:
- GET    /api/v1/salaires/fiches/                       Liste fiches
- POST   /api/v1/salaires/fiches/                       Créer fiche
- GET    /api/v1/salaires/fiches/{id}/                  Détail fiche
- PUT    /api/v1/salaires/fiches/{id}/                  Modifier fiche
- DELETE /api/v1/salaires/fiches/{id}/                  Supprimer fiche
- POST   /api/v1/salaires/fiches/{id}/calculer/         Calculer montants
- POST   /api/v1/salaires/fiches/{id}/valider/          Valider fiche
- POST   /api/v1/salaires/fiches/{id}/generer_pdf/      Générer PDF
- POST   /api/v1/salaires/fiches/generer_lot/           Générer lot de fiches

CERTIFICATS DE SALAIRE:
- GET    /api/v1/salaires/certificats/                  Liste certificats
- POST   /api/v1/salaires/certificats/                  Créer certificat
- GET    /api/v1/salaires/certificats/{id}/             Détail certificat
- PUT    /api/v1/salaires/certificats/{id}/             Modifier certificat
- DELETE /api/v1/salaires/certificats/{id}/             Supprimer certificat
- POST   /api/v1/salaires/certificats/{id}/generer_pdf/ Générer PDF

DÉCLARATIONS COTISATIONS:
- GET    /api/v1/salaires/declarations/                 Liste déclarations
- POST   /api/v1/salaires/declarations/                 Créer déclaration
- GET    /api/v1/salaires/declarations/{id}/            Détail déclaration
- PUT    /api/v1/salaires/declarations/{id}/            Modifier déclaration
- DELETE /api/v1/salaires/declarations/{id}/            Supprimer déclaration
"""
