# mailing/api_urls.py
"""
URLs pour l'API REST du module mailing.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    ConfigurationEmailViewSet,
    TemplateEmailViewSet,
    EmailEnvoyeViewSet,
    EmailRecuViewSet,
)

app_name = "mailing"

router = DefaultRouter()
router.register(r"mailing/configurations", ConfigurationEmailViewSet, basename="mailing-configuration")
router.register(r"mailing/templates", TemplateEmailViewSet, basename="mailing-template")
router.register(r"mailing/envoyes", EmailEnvoyeViewSet, basename="mailing-envoye")
router.register(r"mailing/recus", EmailRecuViewSet, basename="mailing-recu")

urlpatterns = [
    path("", include(router.urls)),
]

"""
API Endpoints:

CONFIGURATIONS EMAIL:
- GET    /api/v1/mailing/configurations/                    Liste des configurations
- POST   /api/v1/mailing/configurations/                    Créer une configuration
- GET    /api/v1/mailing/configurations/{id}/               Détail configuration
- PUT    /api/v1/mailing/configurations/{id}/               Modifier configuration
- PATCH  /api/v1/mailing/configurations/{id}/               Modification partielle
- DELETE /api/v1/mailing/configurations/{id}/               Supprimer configuration
- POST   /api/v1/mailing/configurations/{id}/test/          Tester la connexion SMTP/IMAP
- GET    /api/v1/mailing/configurations/by_usage/           Configurations par usage
- GET    /api/v1/mailing/configurations/statistics/         Statistiques configurations

TEMPLATES EMAIL:
- GET    /api/v1/mailing/templates/                         Liste des templates
- POST   /api/v1/mailing/templates/                         Créer un template
- GET    /api/v1/mailing/templates/{id}/                    Détail template
- PUT    /api/v1/mailing/templates/{id}/                    Modifier template
- DELETE /api/v1/mailing/templates/{id}/                    Supprimer template
- POST   /api/v1/mailing/templates/{id}/preview/            Prévisualiser le template
- GET    /api/v1/mailing/templates/by_type/                 Templates par type
- GET    /api/v1/mailing/templates/by_code/?code=XXX        Template par code

EMAILS ENVOYÉS:
- GET    /api/v1/mailing/envoyes/                           Liste des emails envoyés
- POST   /api/v1/mailing/envoyes/                           Créer un email à envoyer
- GET    /api/v1/mailing/envoyes/{id}/                      Détail email
- DELETE /api/v1/mailing/envoyes/{id}/                      Supprimer email
- POST   /api/v1/mailing/envoyes/{id}/resend/               Renvoyer un email échoué
- GET    /api/v1/mailing/envoyes/statistics/?days=30        Statistiques d'envoi

EMAILS REÇUS:
- GET    /api/v1/mailing/recus/                             Liste des emails reçus
- GET    /api/v1/mailing/recus/{id}/                        Détail email (marque comme lu)
- PATCH  /api/v1/mailing/recus/{id}/                        Modifier email
- DELETE /api/v1/mailing/recus/{id}/                        Supprimer email
- POST   /api/v1/mailing/recus/{id}/mark_read/              Marquer comme lu
- POST   /api/v1/mailing/recus/{id}/mark_unread/            Marquer comme non lu
- POST   /api/v1/mailing/recus/{id}/toggle_important/       Basculer importance
- POST   /api/v1/mailing/recus/{id}/analyze/                Lancer l'analyse IA
- POST   /api/v1/mailing/recus/fetch/                       Récupérer les nouveaux emails
- POST   /api/v1/mailing/recus/mark_all_read/               Marquer tous comme lus
- GET    /api/v1/mailing/recus/statistics/?days=30          Statistiques emails reçus
- GET    /api/v1/mailing/recus/unread_count/                Compter les non lus

Filtres disponibles:
- configurations: type_config, usage, actif, est_defaut
- templates: type_template, actif, configuration
- envoyes: statut, configuration, template, utilisateur, mandat
- recus: statut, configuration, est_important, analyse_effectuee, mandat_detecte, client_detecte
"""
