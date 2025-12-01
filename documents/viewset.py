# documents/viewset.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Dossier, TypeDocument, Document
from .serializers import (
    DossierSerializer,
    TypeDocumentSerializer,
    DocumentListSerializer,
    DocumentDetailSerializer,
)


class DossierViewSet(viewsets.ModelViewSet):
    queryset = Dossier.objects.all()
    serializer_class = DossierSerializer
    permission_classes = [IsAuthenticated]


class TypeDocumentViewSet(viewsets.ModelViewSet):
    queryset = TypeDocument.objects.all()
    serializer_class = TypeDocumentSerializer
    permission_classes = [IsAuthenticated]


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.select_related("mandat", "dossier", "type_document")

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        return DocumentDetailSerializer
