# documents/serializers.py
from rest_framework import serializers
from .models import Dossier, TypeDocument, Document, Conversation, Message
from core.serializers import MandatListSerializer


class DossierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dossier
        fields = "__all__"


class TypeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeDocument
        fields = "__all__"


class DocumentListSerializer(serializers.ModelSerializer):
    statut_traitement_display = serializers.CharField(
        source="get_statut_traitement_display", read_only=True
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "nom_fichier",
            "extension",
            "taille",
            "date_document",
            "type_document",
            "statut_traitement",
            "statut_traitement_display",
        ]


class DocumentDetailSerializer(serializers.ModelSerializer):
    mandat = MandatListSerializer(read_only=True)

    class Meta:
        model = Document
        fields = "__all__"


# ============================================================================
# SERIALIZERS CHAT
# ============================================================================

class MessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages de chat."""

    documents_contexte = DocumentListSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'role',
            'contenu',
            'tokens_prompt',
            'tokens_completion',
            'duree_ms',
            'documents_contexte',
            'sources',
            'feedback',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'tokens_prompt',
            'tokens_completion',
            'duree_ms',
            'documents_contexte',
            'sources',
            'created_at',
        ]


class MessageCreateSerializer(serializers.Serializer):
    """Serializer pour l'envoi d'un nouveau message."""

    message = serializers.CharField(
        max_length=10000,
        help_text='Message de l\'utilisateur'
    )
    use_semantic_search = serializers.BooleanField(
        default=True,
        help_text='Utiliser la recherche semantique pour le contexte'
    )
    max_context_docs = serializers.IntegerField(
        default=5,
        min_value=0,
        max_value=20,
        help_text='Nombre max de documents pour le contexte'
    )


class MessageFeedbackSerializer(serializers.Serializer):
    """Serializer pour le feedback sur un message."""

    feedback = serializers.ChoiceField(
        choices=['POSITIF', 'NEGATIF'],
        help_text='Type de feedback'
    )
    commentaire = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text='Commentaire optionnel'
    )


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des conversations."""

    mandat_numero = serializers.CharField(
        source='mandat.numero',
        read_only=True,
        allow_null=True
    )
    document_nom = serializers.CharField(
        source='document.nom_fichier',
        read_only=True,
        allow_null=True
    )
    dernier_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'titre',
            'mandat',
            'mandat_numero',
            'document',
            'document_nom',
            'statut',
            'nombre_messages',
            'dernier_message',
            'created_at',
            'updated_at',
        ]

    def get_dernier_message(self, obj):
        """Retourne un apercu du dernier message."""
        dernier = obj.messages.order_by('-created_at').first()
        if dernier:
            return {
                'role': dernier.role,
                'contenu': dernier.contenu[:100] + '...' if len(dernier.contenu) > 100 else dernier.contenu,
                'date': dernier.created_at
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer detaille pour une conversation avec ses messages."""

    mandat_numero = serializers.CharField(
        source='mandat.numero',
        read_only=True,
        allow_null=True
    )
    document_nom = serializers.CharField(
        source='document.nom_fichier',
        read_only=True,
        allow_null=True
    )
    messages = MessageSerializer(many=True, read_only=True)
    utilisateur_nom = serializers.CharField(
        source='utilisateur.get_full_name',
        read_only=True
    )

    class Meta:
        model = Conversation
        fields = [
            'id',
            'titre',
            'description',
            'utilisateur',
            'utilisateur_nom',
            'mandat',
            'mandat_numero',
            'document',
            'document_nom',
            'modele_ia',
            'temperature',
            'contexte_systeme',
            'statut',
            'nombre_messages',
            'tokens_utilises',
            'messages',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'utilisateur',
            'nombre_messages',
            'tokens_utilises',
            'created_at',
            'updated_at',
        ]


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la creation d'une conversation."""

    class Meta:
        model = Conversation
        fields = [
            'id',
            'mandat',
            'document',
            'titre',
            'description',
            'temperature',
            'contexte_systeme',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """Valide les donnees de creation."""
        # Si document specifie, verifier qu'il appartient au mandat
        document = data.get('document')
        mandat = data.get('mandat')

        if document and mandat:
            if document.mandat_id != mandat.id:
                raise serializers.ValidationError({
                    'document': 'Le document doit appartenir au mandat specifie.'
                })

        # Si document sans mandat, recuperer le mandat du document
        if document and not mandat:
            data['mandat'] = document.mandat

        return data

    def create(self, validated_data):
        """Cree la conversation avec l'utilisateur courant."""
        validated_data['utilisateur'] = self.context['request'].user
        return super().create(validated_data)


class ChatSearchSerializer(serializers.Serializer):
    """Serializer pour la recherche de documents dans le chat."""

    query = serializers.CharField(
        max_length=1000,
        help_text='Texte de recherche'
    )
    mandat_id = serializers.UUIDField(
        help_text='ID du mandat pour filtrer'
    )
    limit = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=50,
        help_text='Nombre max de resultats'
    )
    search_type = serializers.ChoiceField(
        choices=['fulltext', 'semantic', 'hybrid'],
        default='hybrid',
        help_text='Type de recherche'
    )


class ChatResponseSerializer(serializers.Serializer):
    """Serializer pour la reponse du chat."""

    message = MessageSerializer()
    sources = serializers.ListField(
        child=serializers.DictField()
    )
    conversation_id = serializers.UUIDField()
