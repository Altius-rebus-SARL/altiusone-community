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


class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'upload de documents.
    Supporte deux modes:
    - Upload classique avec fichier multipart (fichier)
    - Upload base64 depuis mobile (fichier_base64 + fichier_nom + fichier_type)
    """

    # Mode classique - fichier multipart
    fichier = serializers.FileField(write_only=True, required=False)

    # Mode base64 pour React Native
    fichier_base64 = serializers.CharField(write_only=True, required=False)
    fichier_nom = serializers.CharField(write_only=True, required=False)
    fichier_type = serializers.CharField(write_only=True, required=False, default='application/octet-stream')

    class Meta:
        model = Document
        fields = [
            "id",
            "fichier",
            "fichier_base64",
            "fichier_nom",
            "fichier_type",
            "mandat",
            "dossier",
            "type_document",
            "categorie",
            "date_document",
            "description",
            "tags",
            "confidentiel",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            'dossier': {'required': False},
            'type_document': {'required': False},
            'categorie': {'required': False},
            'date_document': {'required': False},
            'description': {'required': False},
            'tags': {'required': False},
            'confidentiel': {'required': False},
        }

    def validate(self, attrs):
        """Valider qu'on a soit un fichier, soit les données base64."""
        fichier = attrs.get('fichier')
        fichier_base64 = attrs.get('fichier_base64')
        fichier_nom = attrs.get('fichier_nom')

        print(f"[DocumentUploadSerializer] validate called")
        print(f"[DocumentUploadSerializer] fichier present: {fichier is not None}")
        print(f"[DocumentUploadSerializer] fichier_base64 present: {fichier_base64 is not None}")
        print(f"[DocumentUploadSerializer] attrs keys: {attrs.keys()}")

        if not fichier and not fichier_base64:
            raise serializers.ValidationError({
                'fichier': 'Un fichier est requis (fichier ou fichier_base64)'
            })

        if fichier_base64 and not fichier_nom:
            raise serializers.ValidationError({
                'fichier_nom': 'Le nom du fichier est requis avec fichier_base64'
            })

        return attrs

    def create(self, validated_data):
        import hashlib
        import os
        import uuid
        import base64
        from django.core.files.base import ContentFile
        from core.storage import get_storage_backend

        print(f"[DocumentUploadSerializer] create called with keys: {validated_data.keys()}")

        # Extraire les données de fichier
        fichier = validated_data.pop('fichier', None)
        fichier_base64 = validated_data.pop('fichier_base64', None)
        fichier_nom = validated_data.pop('fichier_nom', None)
        fichier_type = validated_data.pop('fichier_type', 'application/octet-stream')

        # Mode base64
        if fichier_base64:
            print(f"[DocumentUploadSerializer] Processing base64 file: {fichier_nom}")
            # Décoder le base64
            try:
                # Supprimer le préfixe data:xxx;base64, si présent
                if ';base64,' in fichier_base64:
                    fichier_base64 = fichier_base64.split(';base64,')[1]
                file_content = base64.b64decode(fichier_base64)
            except Exception as e:
                raise serializers.ValidationError({
                    'fichier_base64': f'Erreur de décodage base64: {str(e)}'
                })

            file_name = fichier_nom
            file_size = len(file_content)
            mime_type = fichier_type

        # Mode fichier classique
        elif fichier:
            print(f"[DocumentUploadSerializer] Processing multipart file: {fichier.name}")
            file_content = fichier.read()
            fichier.seek(0)
            file_name = fichier.name
            file_size = fichier.size
            mime_type = fichier.content_type or 'application/octet-stream'

        else:
            raise serializers.ValidationError({'fichier': 'Aucun fichier fourni'})

        # Calculer le hash
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Générer le path_storage unique
        path_storage = f"{validated_data['mandat'].id}/{uuid.uuid4()}/{file_name}"

        # Upload le fichier vers S3/MinIO
        try:
            storage = get_storage_backend('document')
            # Le storage 'document' a location='documents', donc le path final sera documents/{path_storage}
            saved_path = storage.save(path_storage, ContentFile(file_content))
            print(f"[DocumentUploadSerializer] File uploaded to S3: {saved_path}")
        except Exception as e:
            print(f"[DocumentUploadSerializer] S3 upload error: {e}")
            raise serializers.ValidationError({
                'fichier': f'Erreur lors de l\'upload vers le stockage: {str(e)}'
            })

        # Créer le document
        document = Document.objects.create(
            **validated_data,
            nom_original=file_name,
            nom_fichier=file_name,
            extension=os.path.splitext(file_name)[1].lower(),
            mime_type=mime_type,
            taille=file_size,
            hash_fichier=file_hash,
            path_storage=saved_path,  # Utiliser le path retourné par storage.save()
            statut_traitement='UPLOAD',
        )

        print(f"[DocumentUploadSerializer] Document created: {document.id}")

        return document

    def to_representation(self, instance):
        """Retourner les données complètes du document après création."""
        return DocumentDetailSerializer(instance).data


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
