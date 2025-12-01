# documents/serializers.py
from rest_framework import serializers
from .models import Dossier, TypeDocument, Document
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
