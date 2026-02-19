from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, Message
from .serializers import ConversationListSerializer, ConversationDetailSerializer, MessageSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationListSerializer

    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user,
            is_ai_conversation=False,
        ).distinct().prefetch_related('participants', 'messages')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()

        # Add creator as participant
        conversation.participants.add(request.user)

        # Add other participants sent as list of UUIDs
        participant_ids = request.data.get('participants', [])
        if participant_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            users = User.objects.filter(id__in=participant_ids)
            conversation.participants.add(*users)

        # Re-serialize with participants now attached
        conversation.refresh_from_db()
        output_serializer = self.get_serializer(conversation)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Le message ne peut pas être vide.'}, status=status.HTTP_400_BAD_REQUEST)
        msg = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            role='user',
            content=content,
        )
        msg.read_by.add(request.user)
        conversation.save()  # update updated_at
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        conversation = self.get_object()
        unread = conversation.messages.exclude(read_by=request.user)
        for msg in unread:
            msg.read_by.add(request.user)
        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        conversations = self.get_queryset()
        total = 0
        for conv in conversations:
            total += conv.messages.exclude(read_by=request.user).exclude(sender=request.user).count()
        return Response({'count': total})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_ask_ai(request):
    """Simple AI chat endpoint - receives a message and returns a response.
    For now, returns a placeholder response. Connect to an LLM later."""
    content = request.data.get('message', '').strip()
    mandat_id = request.data.get('mandat_id')

    if not content:
        return Response({'error': 'Le message ne peut pas être vide.'}, status=status.HTTP_400_BAD_REQUEST)

    # Placeholder response - connect to LLM service later
    response_content = (
        f"Je suis l'assistant IA AltiusOne. Vous avez demandé : \"{content}\". "
        "Cette fonctionnalité sera bientôt connectée à notre moteur d'IA pour vous fournir "
        "des réponses pertinentes basées sur les données de votre mandat."
    )

    return Response({
        'role': 'assistant',
        'content': response_content,
    })
