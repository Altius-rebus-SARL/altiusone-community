"""
Serializers pour l'API REST de l'application Éditeur Collaboratif.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    DocumentCollaboratif,
    PartageDocument,
    LienPartagePublic,
    SessionEdition,
    VersionExportee,
    ModeleDocument
)

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les utilisateurs."""
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'nom_complet']

    def get_nom_complet(self, obj):
        return obj.get_full_name() or obj.email


class DocumentCollaboratifSerializer(serializers.ModelSerializer):
    """Serializer pour les documents collaboratifs."""
    createur = UserMinimalSerializer(read_only=True)
    url_edition = serializers.ReadOnlyField()
    est_editable = serializers.ReadOnlyField()
    mandat_nom = serializers.CharField(source='mandat.nom', read_only=True)
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    dossier_nom = serializers.CharField(source='dossier.nom', read_only=True)

    class Meta:
        model = DocumentCollaboratif
        fields = [
            'id',
            'docs_id',
            'titre',
            'description',
            'type_document',
            'statut',
            'mandat',
            'mandat_nom',
            'client',
            'client_nom',
            'dossier',
            'dossier_nom',
            'createur',
            'est_public',
            'date_creation',
            'date_modification',
            'date_derniere_edition',
            'nombre_collaborateurs',
            'nombre_versions',
            'taille_contenu',
            'langue',
            'url_edition',
            'est_editable',
        ]
        read_only_fields = [
            'id', 'docs_id', 'createur', 'date_creation', 'date_modification',
            'date_derniere_edition', 'nombre_collaborateurs', 'nombre_versions',
            'taille_contenu'
        ]


class DocumentCollaboratifCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de documents."""
    modele_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = DocumentCollaboratif
        fields = [
            'titre',
            'description',
            'type_document',
            'mandat',
            'client',
            'dossier',
            'langue',
            'est_public',
            'modele_id',
        ]


class PartageDocumentSerializer(serializers.ModelSerializer):
    """Serializer pour les partages de documents."""
    utilisateur = UserMinimalSerializer(read_only=True)
    utilisateur_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        source='utilisateur',
        write_only=True
    )
    partage_par = UserMinimalSerializer(read_only=True)
    est_expire = serializers.ReadOnlyField()
    peut_editer = serializers.ReadOnlyField()

    class Meta:
        model = PartageDocument
        fields = [
            'id',
            'utilisateur',
            'utilisateur_id',
            'niveau_acces',
            'partage_par',
            'date_partage',
            'date_expiration',
            'notifier_modifications',
            'est_expire',
            'peut_editer',
        ]
        read_only_fields = ['id', 'partage_par', 'date_partage']


class LienPartagePublicSerializer(serializers.ModelSerializer):
    """Serializer pour les liens de partage publics."""
    url_complet = serializers.ReadOnlyField()
    est_valide = serializers.ReadOnlyField()
    mot_de_passe = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = LienPartagePublic
        fields = [
            'id',
            'token',
            'permet_edition',
            'permet_commentaire',
            'permet_telechargement',
            'date_expiration',
            'nombre_acces_max',
            'nombre_acces',
            'date_creation',
            'est_actif',
            'url_complet',
            'est_valide',
            'mot_de_passe',
        ]
        read_only_fields = ['id', 'token', 'nombre_acces', 'date_creation']

    def create(self, validated_data):
        mot_de_passe = validated_data.pop('mot_de_passe', None)
        instance = super().create(validated_data)

        if mot_de_passe:
            from django.contrib.auth.hashers import make_password
            instance.mot_de_passe_hash = make_password(mot_de_passe)
            instance.save()

        return instance


class SessionEditionSerializer(serializers.ModelSerializer):
    """Serializer pour les sessions d'édition."""
    utilisateur = UserMinimalSerializer(read_only=True)
    document_titre = serializers.CharField(source='document.titre', read_only=True)

    class Meta:
        model = SessionEdition
        fields = [
            'id',
            'document',
            'document_titre',
            'utilisateur',
            'session_id',
            'debut',
            'derniere_activite',
            'fin',
            'est_active',
        ]
        read_only_fields = fields


class VersionExporteeSerializer(serializers.ModelSerializer):
    """Serializer pour les versions exportées."""
    exporte_par = UserMinimalSerializer(read_only=True)
    fichier_url = serializers.SerializerMethodField()

    class Meta:
        model = VersionExportee
        fields = [
            'id',
            'format_export',
            'fichier_url',
            'taille',
            'numero_version',
            'exporte_par',
            'date_export',
            'notes',
        ]
        read_only_fields = fields

    def get_fichier_url(self, obj):
        request = self.context.get('request')
        if obj.fichier and request:
            return request.build_absolute_uri(obj.fichier.url)
        return None


class ModeleDocumentSerializer(serializers.ModelSerializer):
    """Serializer pour les modèles de documents."""
    cree_par = UserMinimalSerializer(read_only=True)

    class Meta:
        model = ModeleDocument
        fields = [
            'id',
            'nom',
            'description',
            'categorie',
            'type_document',
            'contenu_json',
            'apercu_html',
            'cree_par',
            'date_creation',
            'date_modification',
            'est_public',
            'est_systeme',
            'langue',
            'nombre_utilisations',
        ]
        read_only_fields = [
            'id', 'cree_par', 'date_creation', 'date_modification',
            'est_systeme', 'nombre_utilisations'
        ]
