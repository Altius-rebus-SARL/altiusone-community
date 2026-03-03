"""
Vues API REST pour l'application Éditeur Collaboratif.
"""

import logging
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import (
    DocumentCollaboratif,
    PartageDocument,
    ModeleDocument,
    SessionEdition
)
from .serializers import (
    DocumentCollaboratifSerializer,
    DocumentCollaboratifCreateSerializer,
    PartageDocumentSerializer,
    ModeleDocumentSerializer,
    SessionEditionSerializer
)
from .docs_service import docs_service, DocsServiceError

logger = logging.getLogger(__name__)


class DocumentCollaboratifViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les documents collaboratifs.

    Endpoints:
    - GET /api/v1/editeur/documents/ - Liste des documents
    - POST /api/v1/editeur/documents/ - Créer un document
    - GET /api/v1/editeur/documents/{id}/ - Détail d'un document
    - PUT/PATCH /api/v1/editeur/documents/{id}/ - Modifier
    - DELETE /api/v1/editeur/documents/{id}/ - Supprimer
    - POST /api/v1/editeur/documents/{id}/share/ - Partager
    - POST /api/v1/editeur/documents/{id}/export/ - Exporter
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentCollaboratifCreateSerializer
        return DocumentCollaboratifSerializer

    def get_queryset(self):
        user = self.request.user
        return DocumentCollaboratif.objects.filter(
            Q(createur=user) |
            Q(partages__utilisateur=user) |
            Q(est_public=True, mandat__in=user.mandats_accessibles)
        ).distinct().select_related(
            'createur', 'mandat', 'client', 'dossier'
        ).prefetch_related('partages')

    def perform_create(self, serializer):
        user = self.request.user
        document = serializer.save(createur=user)

        try:
            # Créer dans Docs
            modele_id = self.request.data.get('modele_id')
            content = None

            if modele_id:
                modele = ModeleDocument.objects.get(id=modele_id)
                content = modele.contenu_json
                modele.incrementer_utilisation()

            docs_doc = docs_service.create_document(
                title=document.titre,
                user=user,
                content=content
            )
            document.docs_id = docs_doc.id
            document.save()

        except DocsServiceError as e:
            logger.error(f"Erreur création Docs: {e}")
            document.delete()
            raise

    def perform_destroy(self, instance):
        try:
            docs_service.delete_document(instance.docs_id)
        except DocsServiceError as e:
            logger.warning(f"Erreur suppression Docs: {e}")

        instance.delete()

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Partage le document avec un utilisateur."""
        document = self.get_object()

        if document.createur != request.user:
            return Response(
                {'error': 'Seul le créateur peut partager ce document'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PartageDocumentSerializer(data=request.data)
        if serializer.is_valid():
            partage = serializer.save(
                document=document,
                partage_par=request.user
            )

            try:
                permission_map = {
                    'LECTURE': 'view',
                    'COMMENTAIRE': 'comment',
                    'EDITION': 'edit',
                    'ADMIN': 'admin'
                }
                docs_service.add_collaborator(
                    document.docs_id,
                    partage.utilisateur,
                    permission_map.get(partage.niveau_acces, 'view')
                )
            except DocsServiceError as e:
                partage.delete()
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            document.nombre_collaborateurs = document.partages.count() + 1
            document.save(update_fields=['nombre_collaborateurs'])

            return Response(
                PartageDocumentSerializer(partage).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """Exporte le document dans un format spécifié."""
        document = self.get_object()
        format_export = request.data.get('format', 'pdf')

        try:
            content = docs_service.export_document(document.docs_id, format_export)

            # Créer la version exportée
            from django.core.files.base import ContentFile
            import hashlib
            from .models import VersionExportee

            version = VersionExportee(
                document=document,
                format_export=format_export.upper(),
                exporte_par=request.user,
                numero_version=document.versions_exportees.count() + 1,
                hash_contenu=hashlib.sha256(content).hexdigest(),
                taille=len(content)
            )

            filename = f"{document.titre}.{format_export}"
            version.fichier.save(filename, ContentFile(content))
            version.save()

            return Response({
                'message': 'Export réussi',
                'version_id': str(version.id),
                'format': format_export,
                'taille': version.taille
            })

        except DocsServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Liste les sessions d'édition actives."""
        document = self.get_object()
        sessions = SessionEdition.objects.filter(
            document=document,
            est_active=True
        ).select_related('utilisateur')

        return Response(SessionEditionSerializer(sessions, many=True).data)

    @action(detail=True, methods=['post'])
    def archive_ged(self, request, pk=None):
        """Archive le document dans la GED."""
        document = self.get_object()

        if document.createur != request.user:
            return Response(
                {'error': 'Seul le créateur peut archiver ce document'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            content = docs_service.export_document(document.docs_id, 'pdf')

            from documents.models import Document as DocumentGED, TypeDocument
            from django.core.files.base import ContentFile

            type_doc = TypeDocument.objects.filter(code='AUTRE').first()

            doc_ged = DocumentGED(
                nom=f"{document.titre}.pdf",
                description=document.description or "Export depuis l'éditeur collaboratif",
                mandat=document.mandat,
                dossier=document.dossier,
                type_document=type_doc,
                createur=request.user,
            )

            doc_ged.fichier.save(f"{document.titre}.pdf", ContentFile(content))
            doc_ged.save()

            document.document_exporte = doc_ged
            document.statut = DocumentCollaboratif.Statut.ARCHIVE
            document.save()

            return Response({
                'message': 'Document archivé dans la GED',
                'document_ged_id': str(doc_ged.id)
            })

        except DocsServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModeleDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet pour les modèles de documents."""
    serializer_class = ModeleDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ModeleDocument.objects.filter(
            Q(est_public=True) | Q(cree_par=user)
        )

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)


class DocsHealthView(views.APIView):
    """Vérifie l'état du service Docs."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        health = docs_service.health_check()
        status_code = status.HTTP_200_OK if health['status'] == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health, status=status_code)


class DocumentTokenView(views.APIView):
    """Génère un token d'accès pour un document."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        document = get_object_or_404(
            DocumentCollaboratif,
            pk=pk
        )

        # Vérifier l'accès
        has_access = (
            document.createur == user or
            document.partages.filter(utilisateur=user).exists() or
            (document.est_public and document.mandat in user.mandats_accessibles)
        )

        if not has_access:
            return Response(
                {'error': 'Accès refusé'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Déterminer si lecture seule
        can_edit = (
            document.createur == user or
            document.partages.filter(
                utilisateur=user,
                niveau_acces__in=['EDITION', 'ADMIN']
            ).exists()
        )

        try:
            if can_edit:
                token = docs_service.generate_edit_token(user, document.docs_id)
                editor_url = docs_service.get_embed_url(document.docs_id, token, readonly=False)
            else:
                token = docs_service.generate_readonly_token(document.docs_id)
                editor_url = docs_service.get_embed_url(document.docs_id, token, readonly=True)

            return Response({
                'token': token,
                'editor_url': editor_url,
                'can_edit': can_edit,
                'docs_id': document.docs_id
            })

        except DocsServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class CollaboratorsView(views.APIView):
    """Gestion des collaborateurs d'un document."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """Liste les collaborateurs."""
        document = get_object_or_404(DocumentCollaboratif, pk=pk)
        partages = document.partages.select_related('utilisateur', 'partage_par')
        return Response(PartageDocumentSerializer(partages, many=True).data)

    def post(self, request, pk):
        """Ajoute un collaborateur."""
        document = get_object_or_404(DocumentCollaboratif, pk=pk, createur=request.user)

        serializer = PartageDocumentSerializer(data=request.data)
        if serializer.is_valid():
            partage = serializer.save(
                document=document,
                partage_par=request.user
            )

            try:
                permission_map = {
                    'LECTURE': 'view',
                    'COMMENTAIRE': 'comment',
                    'EDITION': 'edit',
                    'ADMIN': 'admin'
                }
                docs_service.add_collaborator(
                    document.docs_id,
                    partage.utilisateur,
                    permission_map.get(partage.niveau_acces, 'view')
                )
            except DocsServiceError as e:
                partage.delete()
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response(PartageDocumentSerializer(partage).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Retire un collaborateur."""
        document = get_object_or_404(DocumentCollaboratif, pk=pk, createur=request.user)
        utilisateur_id = request.data.get('utilisateur_id')

        partage = get_object_or_404(PartageDocument, document=document, utilisateur_id=utilisateur_id)

        try:
            docs_service.remove_collaborator(document.docs_id, partage.utilisateur)
        except DocsServiceError as e:
            logger.warning(f"Erreur retrait Docs: {e}")

        partage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
