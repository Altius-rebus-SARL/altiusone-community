# documents/api_views.py
"""
API REST pour le module de chat avec recherche universelle.

Endpoints:
- /api/chat/conversations/ - CRUD conversations
- /api/chat/conversations/{id}/messages/ - Envoi de messages
- /api/chat/conversations/{id}/messages/{id}/feedback/ - Feedback
- /api/chat/search/ - Recherche universelle (documents + entites)
- /api/chat/entities/ - Recherche d'entites specifiques
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Conversation, Message, Document
from .serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageFeedbackSerializer,
    ChatSearchSerializer,
)
from .chat_service import chat_service
from .universal_search import universal_search, SearchContext, EntityType


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les conversations de chat.

    Endpoints:
    - GET /api/chat/conversations/ - Liste des conversations
    - POST /api/chat/conversations/ - Creer une conversation
    - GET /api/chat/conversations/{id}/ - Detail avec messages
    - PATCH /api/chat/conversations/{id}/ - Modifier
    - DELETE /api/chat/conversations/{id}/ - Archiver

    Actions:
    - POST /api/chat/conversations/{id}/send_message/ - Envoyer un message
    - GET /api/chat/conversations/{id}/messages/ - Liste des messages
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtre les conversations de l'utilisateur courant."""
        user = self.request.user
        qs = Conversation.objects.filter(
            utilisateur=user,
            statut__in=['ACTIVE', 'ARCHIVEE']
        ).select_related('mandat', 'document')

        # Filtre par mandat
        mandat_id = self.request.query_params.get('mandat')
        if mandat_id:
            qs = qs.filter(mandat_id=mandat_id)

        # Filtre par statut
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)

        return qs.order_by('-updated_at')

    def get_serializer_class(self):
        """Retourne le serializer selon l'action."""
        if self.action == 'create':
            return ConversationCreateSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return ConversationDetailSerializer
        return ConversationListSerializer

    def perform_destroy(self, instance):
        """Archive la conversation au lieu de la supprimer."""
        instance.statut = 'SUPPRIMEE'
        instance.save(update_fields=['statut'])

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        Envoie un message dans la conversation.

        Request body:
        {
            "message": "Texte du message",
            "use_semantic_search": true,
            "max_context_docs": 5
        }

        Response:
        {
            "message": {...},
            "sources": [...],
            "conversation_id": "..."
        }
        """
        conversation = self.get_object()
        serializer = MessageCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Envoyer le message via le service
        response = chat_service.chat(
            conversation=conversation,
            message=serializer.validated_data['message'],
            use_semantic_search=serializer.validated_data.get('use_semantic_search', True),
            max_context_results=serializer.validated_data.get('max_context_docs', 10)
        )

        # Recuperer le dernier message assistant
        assistant_message = conversation.messages.filter(
            role='ASSISTANT'
        ).order_by('-created_at').first()

        if response.erreur:
            return Response({
                'error': response.erreur,
                'conversation_id': str(conversation.id)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'message': MessageSerializer(assistant_message).data,
            'sources': response.sources,
            'entities': response.entities,  # Nouvelles entites (clients, employes, etc.)
            'conversation_id': str(conversation.id),
            'tokens_used': response.tokens_prompt + response.tokens_completion,
            'duration_ms': response.duree_ms
        })

    @action(detail=True, methods=['post'], url_path='stream_message')
    def stream_message(self, request, pk=None):
        """
        Stream a message response as Server-Sent Events.

        Same request body as send_message:
        {
            "message": "Texte du message",
            "use_semantic_search": true,
            "max_context_docs": 5
        }

        Response: text/event-stream with JSON lines:
        {"type":"sources","sources":[...],"entities":[...]}
        {"type":"token","token":"mot"}
        {"type":"done","model":"...","tokens_used":N,"processing_time_ms":N}
        {"type":"message_saved","message_id":"uuid"}
        """
        conversation = self.get_object()
        serializer = MessageCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        def event_stream():
            for event in chat_service.chat_stream(
                conversation=conversation,
                message=serializer.validated_data['message'],
                use_semantic_search=serializer.validated_data.get('use_semantic_search', True),
                max_context_results=serializer.validated_data.get('max_context_docs', 10),
            ):
                yield f"data: {event}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Liste les messages d'une conversation.

        Query params:
        - limit: nombre max de messages (default: 50)
        - offset: pagination
        """
        conversation = self.get_object()
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))

        messages = conversation.messages.order_by('created_at')[offset:offset+limit]
        serializer = MessageSerializer(messages, many=True)

        return Response({
            'results': serializer.data,
            'count': conversation.messages.count(),
            'conversation_id': str(conversation.id)
        })

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive une conversation."""
        conversation = self.get_object()
        conversation.statut = 'ARCHIVEE'
        conversation.save(update_fields=['statut'])

        return Response({'status': 'archived'})

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restaure une conversation archivee."""
        conversation = self.get_object()
        conversation.statut = 'ACTIVE'
        conversation.save(update_fields=['statut'])

        return Response({'status': 'restored'})


class MessageFeedbackView:
    """Vue pour le feedback sur les messages."""

    @staticmethod
    @api_view(['POST'])
    @permission_classes([IsAuthenticated])
    def feedback(request, conversation_id, message_id):
        """
        Ajoute un feedback sur un message.

        POST /api/chat/conversations/{conv_id}/messages/{msg_id}/feedback/
        {
            "feedback": "POSITIF" | "NEGATIF",
            "commentaire": "optionnel"
        }
        """
        message = get_object_or_404(
            Message,
            id=message_id,
            conversation_id=conversation_id,
            conversation__utilisateur=request.user
        )

        serializer = MessageFeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        message.feedback = serializer.validated_data['feedback']
        message.commentaire_feedback = serializer.validated_data.get('commentaire', '')
        message.save(update_fields=['feedback', 'commentaire_feedback'])

        return Response({'status': 'feedback_saved'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_search(request):
    """
    Recherche universelle pour le contexte du chat.

    POST /api/chat/search/
    {
        "query": "factures janvier",
        "mandat_id": "uuid",  // optionnel
        "entity_types": ["document", "client", "employe"],  // optionnel
        "limit": 20
    }

    Response:
    {
        "results": [...],  // Tous les resultats
        "documents": [...],  // Documents seulement
        "entities": [...],  // Autres entites (clients, employes, etc.)
        "count": 20
    }
    """
    query = request.data.get('query', '')
    mandat_id = request.data.get('mandat_id')
    entity_type_names = request.data.get('entity_types', [])
    limit = request.data.get('limit', 20)

    if not query:
        return Response(
            {'error': 'Le parametre query est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Convertir les noms en EntityType
    entity_types = None
    if entity_type_names:
        entity_types = []
        for name in entity_type_names:
            try:
                entity_types.append(EntityType(name))
            except ValueError:
                pass  # Ignorer les types inconnus

    # Construire le contexte de recherche
    context = SearchContext(
        user=request.user,
        mandat_ids=[mandat_id] if mandat_id else None,
        entity_types=entity_types
    )

    # Recherche universelle
    results = universal_search.search(
        query=query,
        context=context,
        limit=limit
    )

    # Separer documents et autres entites
    documents = []
    entities = []
    for result in results:
        result_dict = result.to_dict()
        if result.entity_type == EntityType.DOCUMENT:
            documents.append(result_dict)
        else:
            entities.append(result_dict)

    return Response({
        'results': [r.to_dict() for r in results],
        'documents': documents,
        'entities': entities,
        'count': len(results)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_entities(request):
    """
    Recherche d'entites pour l'autocomplete et la recherche rapide.

    GET /api/chat/entities/?q=dupont&types=client,employe&limit=10

    Response:
    {
        "results": [
            {
                "entity_type": "client",
                "entity_id": "uuid",
                "title": "Dupont SA",
                "subtitle": "Societe anonyme - ACTIF",
                "url": "/clients/uuid/",
                "icon": "ph-buildings",
                "color": "info",
                "score": 0.85
            },
            ...
        ],
        "count": 5
    }
    """
    query = request.query_params.get('q', '')
    type_names = request.query_params.get('types', '').split(',')
    mandat_id = request.query_params.get('mandat_id')
    limit = int(request.query_params.get('limit', 10))

    if not query or len(query) < 2:
        return Response({
            'results': [],
            'count': 0
        })

    # Convertir les noms en EntityType
    entity_types = None
    if type_names and type_names[0]:
        entity_types = []
        for name in type_names:
            name = name.strip()
            try:
                entity_types.append(EntityType(name))
            except ValueError:
                pass

    # Construire le contexte
    context = SearchContext(
        user=request.user,
        mandat_ids=[mandat_id] if mandat_id else None,
        entity_types=entity_types
    )

    # Recherche
    results = universal_search.search(
        query=query,
        context=context,
        limit=limit
    )

    return Response({
        'results': [r.to_dict() for r in results],
        'count': len(results)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_health(request):
    """
    Verifie l'etat du service de chat.

    GET /api/chat/health/

    Response:
    {
        "status": "ok",
        "ai_service": {...}
    }
    """
    from .ai_service import ai_service

    health = ai_service.health_check()

    return Response({
        'status': 'ok' if health.get('connected') else 'degraded',
        'ai_service': health
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def quick_chat(request):
    """
    Endpoint pour chat rapide sans conversation persistante.

    GET /api/chat/quick/?q=question&mandat_id=uuid

    Utile pour l'application mobile pour des questions rapides.
    """
    query = request.query_params.get('q', '')
    mandat_id = request.query_params.get('mandat_id')

    if not query:
        return Response(
            {'error': 'Parameter q is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    from .ai_service import ai_service

    # Construire un contexte simple si mandat specifie
    context_text = ""
    if mandat_id:
        docs = Document.objects.filter(
            mandat_id=mandat_id,
            is_active=True,
            ocr_text__isnull=False
        ).exclude(ocr_text='').order_by('-date_upload')[:3]

        for doc in docs:
            context_text += f"\n--- {doc.nom_fichier} ---\n"
            context_text += doc.ocr_text[:1000] + "\n"

    system_prompt = f"""Tu es un assistant pour une fiduciaire suisse.
Reponds en francais, de maniere concise.

Contexte documentaire:
{context_text if context_text else 'Aucun document disponible.'}
"""

    response = ai_service.chat(
        message=query,
        system_prompt=system_prompt
    )

    return Response({
        'response': response.get('response', ''),
        'query': query
    })
