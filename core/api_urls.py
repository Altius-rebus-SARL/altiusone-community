# apps/core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    UserViewSet,
    ClientViewSet,
    ContactViewSet,
    MandatViewSet,
    ExerciceComptableViewSet,
    AuditLogViewSet,
    NotificationViewSet,
    TacheViewSet,
    CollaborateurFiduciaireViewSet,
)

app_name = "core"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"contacts", ContactViewSet, basename="contact")
router.register(r"mandats", MandatViewSet, basename="mandat")
router.register(r"exercices", ExerciceComptableViewSet, basename="exercice")
router.register(r"audit-logs", AuditLogViewSet, basename="auditlog")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"taches", TacheViewSet, basename="tache")
router.register(r"collaborateurs", CollaborateurFiduciaireViewSet, basename="collaborateur")

urlpatterns = [
    path("", include(router.urls)),
]

"""
API Endpoints:

USERS:
- GET    /api/v1/core/users/                    Liste des utilisateurs
- POST   /api/v1/core/users/                    Créer un utilisateur
- GET    /api/v1/core/users/{id}/               Détail utilisateur
- PUT    /api/v1/core/users/{id}/               Modifier utilisateur
- PATCH  /api/v1/core/users/{id}/               Modifier partiellement
- DELETE /api/v1/core/users/{id}/               Supprimer utilisateur
- GET    /api/v1/core/users/me/                 Mon profil
- POST   /api/v1/core/users/{id}/change_password/  Changer mot de passe

CLIENTS:
- GET    /api/v1/core/clients/                  Liste des clients
- POST   /api/v1/core/clients/                  Créer un client
- GET    /api/v1/core/clients/{id}/             Détail client
- PUT    /api/v1/core/clients/{id}/             Modifier client
- DELETE /api/v1/core/clients/{id}/             Supprimer client
- GET    /api/v1/core/clients/{id}/mandats/     Mandats du client
- GET    /api/v1/core/clients/{id}/contacts/    Contacts du client
- GET    /api/v1/core/clients/statistics/       Statistiques clients

CONTACTS:
- GET    /api/v1/core/contacts/                 Liste des contacts
- POST   /api/v1/core/contacts/                 Créer un contact
- GET    /api/v1/core/contacts/{id}/            Détail contact
- PUT    /api/v1/core/contacts/{id}/            Modifier contact
- DELETE /api/v1/core/contacts/{id}/            Supprimer contact

MANDATS:
- GET    /api/v1/core/mandats/                  Liste des mandats
- POST   /api/v1/core/mandats/                  Créer un mandat
- GET    /api/v1/core/mandats/{id}/             Détail mandat
- PUT    /api/v1/core/mandats/{id}/             Modifier mandat
- DELETE /api/v1/core/mandats/{id}/             Supprimer mandat
- GET    /api/v1/core/mandats/{id}/exercices/   Exercices du mandat
- POST   /api/v1/core/mandats/{id}/change_status/  Changer statut
- GET    /api/v1/core/mandats/actifs/           Mandats actifs uniquement

EXERCICES COMPTABLES:
- GET    /api/v1/core/exercices/                Liste des exercices
- POST   /api/v1/core/exercices/                Créer un exercice
- GET    /api/v1/core/exercices/{id}/           Détail exercice
- PUT    /api/v1/core/exercices/{id}/           Modifier exercice
- POST   /api/v1/core/exercices/{id}/cloturer/  Clôturer exercice

NOTIFICATIONS:
- GET    /api/v1/core/notifications/            Mes notifications
- POST   /api/v1/core/notifications/            Créer notification
- GET    /api/v1/core/notifications/{id}/       Détail notification
- DELETE /api/v1/core/notifications/{id}/       Supprimer notification
- POST   /api/v1/core/notifications/{id}/mark_read/      Marquer comme lue
- POST   /api/v1/core/notifications/mark_all_read/       Tout marquer comme lu
- GET    /api/v1/core/notifications/unread_count/        Nombre non lues

TÂCHES:
- GET    /api/v1/core/taches/                   Liste des tâches
- POST   /api/v1/core/taches/                   Créer une tâche
- GET    /api/v1/core/taches/{id}/              Détail tâche
- PUT    /api/v1/core/taches/{id}/              Modifier tâche
- DELETE /api/v1/core/taches/{id}/              Supprimer tâche
- POST   /api/v1/core/taches/{id}/change_status/  Changer statut
- GET    /api/v1/core/taches/mes_taches/        Mes tâches

AUDIT LOGS (lecture seule):
- GET    /api/v1/core/audit-logs/               Logs d'audit
- GET    /api/v1/core/audit-logs/{id}/          Détail log
"""
