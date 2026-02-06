# documents/viewset.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse, HttpResponse
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
import hashlib
import os

from .models import Dossier, TypeDocument, Document, TraitementDocument
from .serializers import (
    DossierSerializer,
    TypeDocumentSerializer,
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentUploadSerializer,
)


class DossierViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les dossiers GED

    Permissions: Dossiers des mandats accessibles selon les permissions de l'utilisateur
    """

    serializer_class = DossierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['client', 'mandat', 'type_dossier', 'parent']
    search_fields = ['nom', 'chemin_complet', 'description']
    ordering_fields = ['nom', 'created_at', 'niveau']
    ordering = ['chemin_complet']

    def get_queryset(self):
        user = self.request.user
        base_queryset = Dossier.objects.select_related('mandat', 'client', 'parent')

        # Superuser ou Manager: accès complet
        if user.is_superuser or (user.is_staff_user() and user.is_manager()):
            return base_queryset

        # Filtrer par mandats accessibles
        accessible_mandats = user.get_accessible_mandats()
        return base_queryset.filter(
            Q(mandat__in=accessible_mandats) |
            Q(mandat__isnull=True, client__mandats__in=accessible_mandats)
        ).distinct()

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Retourne l'arborescence des dossiers

        Pour un mandat donné, retourne:
        - Les dossiers liés directement au mandat
        - Les dossiers liés au client du mandat (si pas de mandat spécifique)
        """
        from core.models import Mandat

        mandat_id = request.query_params.get('mandat')
        client_id = request.query_params.get('client')

        queryset = self.get_queryset()

        if mandat_id:
            # Récupérer le mandat pour avoir le client associé
            try:
                mandat = Mandat.objects.get(id=mandat_id)
                # Inclure les dossiers du mandat OU du client (si pas de mandat spécifique)
                queryset = queryset.filter(
                    Q(mandat_id=mandat_id) |
                    Q(mandat__isnull=True, client_id=mandat.client_id)
                )
            except Mandat.DoesNotExist:
                queryset = queryset.none()
        elif client_id:
            queryset = queryset.filter(client_id=client_id)

        # Récupérer uniquement les dossiers racine et construire l'arbre
        racines = queryset.filter(parent__isnull=True)

        def build_tree(dossier):
            return {
                'id': dossier.id,
                'nom': dossier.nom,
                'type_dossier': dossier.type_dossier,
                'chemin_complet': dossier.chemin_complet,
                'nombre_documents': dossier.nombre_documents,
                'enfants': [build_tree(enfant) for enfant in dossier.sous_dossiers.all()]
            }

        tree = [build_tree(d) for d in racines]
        return Response(tree)

    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Liste des documents dans ce dossier"""
        dossier = self.get_object()
        documents = Document.objects.filter(dossier=dossier)
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)


class TypeDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les types de documents"""

    queryset = TypeDocument.objects.all()
    serializer_class = TypeDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['type_document', 'categorie', 'validation_requise']
    search_fields = ['code', 'libelle']


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet complet pour la gestion des documents.
    Inclut upload, OCR, classification, extraction et validation.

    Supporte deux modes d'upload:
    - Multipart (fichier) - pour web et certaines apps mobiles
    - JSON avec base64 (fichier_base64) - pour React Native et APIs

    Permissions: Documents des mandats accessibles selon les permissions de l'utilisateur
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['mandat', 'dossier', 'type_document', 'statut_traitement', 'statut_validation']
    search_fields = ['nom_fichier', 'nom_original', 'description', 'ocr_text', 'tags']
    ordering_fields = ['date_upload', 'date_document', 'nom_fichier', 'taille']
    ordering = ['-date_upload']

    def get_queryset(self):
        user = self.request.user
        base_queryset = Document.objects.select_related(
            "mandat", "dossier", "type_document", "categorie", "valide_par"
        )

        # Superuser ou Manager: accès complet
        if user.is_superuser or (user.is_staff_user() and user.is_manager()):
            return base_queryset

        # Filtrer par mandats accessibles
        accessible_mandats = user.get_accessible_mandats()
        return base_queryset.filter(mandat__in=accessible_mandats)

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        if self.action == "create":
            return DocumentUploadSerializer
        return DocumentDetailSerializer

    def get_serializer(self, *args, **kwargs):
        """
        Override pour mapper le champ 'file' vers 'fichier' si présent.
        Permet de supporter les deux noms de champ côté client.
        """
        if self.action == "create":
            print(f"[DocumentViewSet] get_serializer called for create action")
            print(f"[DocumentViewSet] request.FILES: {self.request.FILES}")
            print(f"[DocumentViewSet] request.data: {self.request.data}")
            print(f"[DocumentViewSet] request.content_type: {self.request.content_type}")

            if self.request.FILES:
                # Accepter 'file' ou 'fichier' comme nom de champ
                if 'file' in self.request.FILES and 'fichier' not in self.request.FILES:
                    self.request.FILES['fichier'] = self.request.FILES['file']
            else:
                print(f"[DocumentViewSet] WARNING: No files in request.FILES!")

        return super().get_serializer(*args, **kwargs)

    @action(detail=False, methods=['post'])
    def recherche(self, request):
        """
        Recherche avancée de documents
        Body: {
            "query": "facture 2024",
            "mandat_id": 1,
            "type_document": "FACTURE_ACHAT",
            "date_debut": "2024-01-01",
            "date_fin": "2024-12-31",
            "tags": ["urgent", "a_traiter"]
        }
        """
        query = request.data.get('query', '')
        mandat_id = request.data.get('mandat_id')
        type_doc = request.data.get('type_document')
        date_debut = request.data.get('date_debut')
        date_fin = request.data.get('date_fin')
        tags = request.data.get('tags', [])

        queryset = self.get_queryset()

        if query:
            queryset = queryset.filter(
                Q(nom_fichier__icontains=query) |
                Q(description__icontains=query) |
                Q(ocr_text__icontains=query)
            )

        if mandat_id:
            queryset = queryset.filter(mandat_id=mandat_id)

        if type_doc:
            queryset = queryset.filter(type_document__type_document=type_doc)

        if date_debut:
            queryset = queryset.filter(date_document__gte=date_debut)

        if date_fin:
            queryset = queryset.filter(date_document__lte=date_fin)

        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])

        serializer = DocumentListSerializer(queryset[:100], many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    @action(detail=True, methods=['post'])
    def ocr(self, request, pk=None):
        """
        Lance le traitement OCR sur un document.
        Utilise Celery pour le traitement asynchrone.
        """
        document = self.get_object()

        # Vérifier que le document n'est pas déjà traité
        if document.statut_traitement not in ['UPLOAD', 'ERREUR']:
            return Response(
                {'error': 'Document déjà en cours de traitement ou traité'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer un log de traitement
        traitement = TraitementDocument.objects.create(
            document=document,
            type_traitement='OCR',
            statut='EN_COURS',
            moteur='Tesseract 5.0'
        )

        # Mettre à jour le statut
        document.statut_traitement = 'OCR_EN_COURS'
        document.save()

        # Lancer la tâche Celery (à implémenter)
        # from .tasks import process_ocr
        # process_ocr.delay(document.id)

        return Response({
            'message': 'OCR lancé',
            'traitement_id': traitement.id,
            'document_id': document.id,
            'statut': document.statut_traitement
        })

    @action(detail=True, methods=['post'])
    def classifier(self, request, pk=None):
        """
        Classification automatique du document via AI.
        Prédit le type de document basé sur le contenu OCR.
        """
        document = self.get_object()

        # Vérifier que l'OCR est terminé
        if not document.ocr_text:
            return Response(
                {'error': 'OCR non effectué. Lancez d\'abord l\'OCR.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer un log de traitement
        traitement = TraitementDocument.objects.create(
            document=document,
            type_traitement='CLASSIFICATION',
            statut='EN_COURS',
            moteur='OpenAI GPT-4'
        )

        # Mettre à jour le statut
        document.statut_traitement = 'CLASSIFICATION_EN_COURS'
        document.save()

        # Lancer la tâche Celery (à implémenter)
        # from .tasks import classify_document
        # classify_document.delay(document.id)

        return Response({
            'message': 'Classification lancée',
            'traitement_id': traitement.id,
            'document_id': document.id,
            'statut': document.statut_traitement
        })

    @action(detail=True, methods=['post'])
    def extraire(self, request, pk=None):
        """
        Extraction automatique des métadonnées du document.
        Extrait: montants, dates, numéros de facture, TVA, etc.
        """
        document = self.get_object()

        # Vérifier que l'OCR est terminé
        if not document.ocr_text:
            return Response(
                {'error': 'OCR non effectué. Lancez d\'abord l\'OCR.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer un log de traitement
        traitement = TraitementDocument.objects.create(
            document=document,
            type_traitement='EXTRACTION',
            statut='EN_COURS',
            moteur='OpenAI GPT-4'
        )

        # Mettre à jour le statut
        document.statut_traitement = 'EXTRACTION_EN_COURS'
        document.save()

        # Lancer la tâche Celery (à implémenter)
        # from .tasks import extract_metadata
        # extract_metadata.delay(document.id)

        return Response({
            'message': 'Extraction lancée',
            'traitement_id': traitement.id,
            'document_id': document.id,
            'statut': document.statut_traitement
        })

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        """
        Valide un document après review humain.
        Body: {
            "validation": "VALIDE" | "REJETE",
            "commentaire": "OK pour comptabilisation"
        }
        """
        document = self.get_object()
        validation = request.data.get('validation', 'VALIDE')
        commentaire = request.data.get('commentaire', '')

        if validation not in ['VALIDE', 'REJETE']:
            return Response(
                {'error': 'Validation doit être VALIDE ou REJETE'},
                status=status.HTTP_400_BAD_REQUEST
            )

        document.statut_validation = validation
        document.valide_par = request.user
        document.date_validation = timezone.now()
        document.commentaire_validation = commentaire

        if validation == 'VALIDE':
            document.statut_traitement = 'VALIDE'

        document.save()

        serializer = self.get_serializer(document)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Télécharge le fichier document.
        Retourne une URL signée pour télécharger le fichier depuis S3/MinIO.
        """
        document = self.get_object()

        if not document.fichier:
            return Response(
                {'error': 'Aucun fichier associé à ce document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            # FileField génère automatiquement l'URL signée
            return Response({
                'url': document.fichier.url,
                'nom_fichier': document.nom_fichier,
                'mime_type': document.mime_type,
                'taille': document.taille,
            })
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la génération du lien: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """
        Génère une URL de prévisualisation du document.
        Retourne une URL signée pour accéder au fichier depuis S3/MinIO.
        """
        document = self.get_object()

        preview_url = None

        if document.fichier:
            try:
                # FileField génère automatiquement l'URL signée
                preview_url = document.fichier.url
            except Exception as e:
                print(f"[Preview] Error generating URL: {e}")

        return Response({
            'document_id': str(document.id),
            'nom': document.nom_fichier,
            'mime_type': document.mime_type,
            'extension': document.extension,
            'taille': document.taille,
            'url': preview_url,
            'ocr_text': document.ocr_text[:500] if document.ocr_text else None,
        })

    @action(detail=True, methods=['get'])
    def traitements(self, request, pk=None):
        """Liste l'historique des traitements d'un document"""
        document = self.get_object()
        traitements = document.traitements.all().order_by('-date_debut')

        data = [{
            'id': t.id,
            'type': t.type_traitement,
            'statut': t.statut,
            'moteur': t.moteur,
            'date_debut': t.date_debut,
            'date_fin': t.date_fin,
            'duree_secondes': t.duree_secondes,
            'erreur': t.erreur if t.statut == 'ERREUR' else None,
        } for t in traitements]

        return Response(data)

    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """
        Statistiques sur les documents.
        Filtrable par mandat.
        """
        mandat_id = request.query_params.get('mandat')

        queryset = self.get_queryset()
        if mandat_id:
            queryset = queryset.filter(mandat_id=mandat_id)

        stats = {
            'total': queryset.count(),
            'par_statut_traitement': {},
            'par_type_document': {},
            'en_attente_validation': queryset.filter(statut_validation='EN_ATTENTE').count(),
            'taille_totale_mo': sum(d.taille for d in queryset) / (1024 * 1024),
        }

        # Par statut traitement
        for statut, label in Document.STATUT_TRAITEMENT_CHOICES:
            count = queryset.filter(statut_traitement=statut).count()
            if count > 0:
                stats['par_statut_traitement'][statut] = count

        # Par type document
        types = queryset.exclude(type_document__isnull=True).values_list(
            'type_document__type_document', flat=True
        ).distinct()
        for type_doc in types:
            stats['par_type_document'][type_doc] = queryset.filter(
                type_document__type_document=type_doc
            ).count()

        return Response(stats)

    @action(detail=False, methods=['post'])
    def batch_valider(self, request):
        """
        Validation en batch de plusieurs documents.
        Body: {
            "document_ids": [1, 2, 3],
            "validation": "VALIDE"
        }
        """
        document_ids = request.data.get('document_ids', [])
        validation = request.data.get('validation', 'VALIDE')

        if not document_ids:
            return Response(
                {'error': 'Aucun document spécifié'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated = Document.objects.filter(id__in=document_ids).update(
            statut_validation=validation,
            valide_par=request.user,
            date_validation=timezone.now()
        )

        return Response({
            'message': f'{updated} documents mis à jour',
            'validation': validation
        })
