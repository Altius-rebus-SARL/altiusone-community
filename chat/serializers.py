from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    read_by = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_name', 'role', 'content', 'read_by', 'created_at']
        read_only_fields = ['id', 'sender', 'sender_name', 'role', 'read_by', 'created_at']

    def get_sender_name(self, obj):
        if obj.sender:
            return f"{obj.sender.first_name} {obj.sender.last_name}".strip() or obj.sender.username
        return 'Assistant IA'


class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participants = ParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'participants', 'mandat', 'is_ai_conversation',
                  'last_message', 'last_message_at', 'unread_count', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        return msg.content[:100] if msg else None

    def get_last_message_at(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        return msg.created_at.isoformat() if msg else None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return 0
        user = request.user
        return obj.messages.exclude(read_by=user).exclude(sender=user).count()


class ConversationDetailSerializer(ConversationListSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + ['messages']
