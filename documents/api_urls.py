# apps/documents/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewset import (
    DossierViewSet,
    TypeDocumentViewSet,
    DocumentViewSet,
)
from .api_views import (
    ConversationViewSet,
    MessageFeedbackView,
    chat_search,
    chat_health,
    quick_chat,
    search_entities,
)

app_name = "documents"

router = DefaultRouter()
router.register(r"documents/dossiers", DossierViewSet, basename="docs-dossier")
router.register(r"documents/types", TypeDocumentViewSet, basename="docs-type")
router.register(r"documents/documents", DocumentViewSet, basename="docs-document")
router.register(r"documents/chat/conversations", ConversationViewSet, basename="docs-conversation")

# URLs additionnelles pour le chat
chat_urlpatterns = [
    path("chat/search/", chat_search, name="chat-search"),
    path("chat/entities/", search_entities, name="chat-entities"),  # Recherche d'entites
    path("chat/health/", chat_health, name="chat-health"),
    path("chat/quick/", quick_chat, name="chat-quick"),
    path(
        "chat/conversations/<uuid:conversation_id>/messages/<uuid:message_id>/feedback/",
        MessageFeedbackView.feedback,
        name="message-feedback"
    ),
]

urlpatterns = [
    path("", include(router.urls)),
] + chat_urlpatterns

"""
API Endpoints:

CHAT (Assistant IA documentaire):
- GET    /api/v1/documents/chat/health/                              Verifier service AI
- GET    /api/v1/documents/chat/quick/?q=...&mandat_id=...           Chat rapide sans persistance
- POST   /api/v1/documents/chat/search/                              Recherche documents pour contexte

CONVERSATIONS:
- GET    /api/v1/documents/chat/conversations/                       Liste conversations
- POST   /api/v1/documents/chat/conversations/                       Creer conversation
- GET    /api/v1/documents/chat/conversations/{id}/                  Detail conversation + messages
- PATCH  /api/v1/documents/chat/conversations/{id}/                  Modifier conversation
- DELETE /api/v1/documents/chat/conversations/{id}/                  Archiver conversation
- POST   /api/v1/documents/chat/conversations/{id}/send_message/     Envoyer message
- GET    /api/v1/documents/chat/conversations/{id}/messages/         Liste messages
- POST   /api/v1/documents/chat/conversations/{id}/archive/          Archiver
- POST   /api/v1/documents/chat/conversations/{id}/restore/          Restaurer
- POST   /api/v1/documents/chat/conversations/{conv_id}/messages/{msg_id}/feedback/  Feedback

DOSSIERS:
- GET    /api/v1/documents/dossiers/                   Liste dossiers
- POST   /api/v1/documents/dossiers/                   Créer dossier
- GET    /api/v1/documents/dossiers/{id}/              Détail dossier
- PUT    /api/v1/documents/dossiers/{id}/              Modifier dossier
- DELETE /api/v1/documents/dossiers/{id}/              Supprimer dossier
- GET    /api/v1/documents/dossiers/tree/              Arbre dossiers
- GET    /api/v1/documents/dossiers/{id}/documents/    Documents du dossier

TYPES DOCUMENT:
- GET    /api/v1/documents/types/                      Liste types
- POST   /api/v1/documents/types/                      Créer type
- GET    /api/v1/documents/types/{id}/                 Détail type
- PUT    /api/v1/documents/types/{id}/                 Modifier type
- DELETE /api/v1/documents/types/{id}/                 Supprimer type

DOCUMENTS:
- GET    /api/v1/documents/documents/                  Liste documents
- POST   /api/v1/documents/documents/                  Upload document
- GET    /api/v1/documents/documents/{id}/             Détail document
- PUT    /api/v1/documents/documents/{id}/             Modifier document
- DELETE /api/v1/documents/documents/{id}/             Supprimer document
- POST   /api/v1/documents/documents/recherche/        Recherche documents
- POST   /api/v1/documents/documents/{id}/ocr/         Lancer OCR
- POST   /api/v1/documents/documents/{id}/classifier/  Classifier document
- POST   /api/v1/documents/documents/{id}/extraire/    Extraire métadonnées
- POST   /api/v1/documents/documents/{id}/valider/     Valider document
- GET    /api/v1/documents/documents/{id}/download/    Télécharger document
- GET    /api/v1/documents/documents/{id}/preview/     Aperçu document
"""
