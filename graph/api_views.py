# graph/api_views.py
"""API ViewSets et vues pour le graphe relationnel."""
import logging
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from pgvector.django import CosineDistance

from .models import OntologieType, Entite, Relation, Anomalie, RequeteSauvegardee
from .serializers import (
    OntologieTypeSerializer,
    EntiteListSerializer,
    EntiteDetailSerializer,
    RelationSerializer,
    AnomalieSerializer,
    AnomalieTraiterSerializer,
    RequeteSauvegardeeSerializer,
    GrapheExploreSerializer,
    RechercheSemantiquSerializer,
)
from .filters import EntiteFilter, RelationFilter, AnomalieFilter

logger = logging.getLogger(__name__)


class OntologieTypeViewSet(viewsets.ModelViewSet):
    """CRUD pour les types d'ontologie."""

    queryset = OntologieType.objects.filter(is_active=True)
    serializer_class = OntologieTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'ordre_affichage', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EntiteViewSet(viewsets.ModelViewSet):
    """CRUD pour les entités + actions explore/suggestions."""

    queryset = Entite.objects.filter(is_active=True).select_related('type')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EntiteFilter
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'confiance', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return EntiteListSerializer
        return EntiteDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def explore(self, request, pk=None):
        """Explore le graphe à partir de cette entité."""
        from .services.exploration import explorer_graphe

        serializer = GrapheExploreSerializer(data={
            'entite_id': pk,
            **request.query_params.dict(),
        })
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = explorer_graphe(
            entite_id=data['entite_id'],
            profondeur=data.get('profondeur', 2),
            types_entites=data.get('types_entites'),
            types_relations=data.get('types_relations'),
            date_min=data.get('date_min'),
            date_max=data.get('date_max'),
            confiance_min=data.get('confiance_min', 0.0),
        )
        return Response(result)

    @action(detail=True, methods=['get'])
    def suggestions(self, request, pk=None):
        """Suggère des connexions pour cette entité."""
        from .services.suggestions import suggerer_connexions

        limit = int(request.query_params.get('limit', 10))
        result = suggerer_connexions(pk, limit=limit)
        return Response(result)


class RelationViewSet(viewsets.ModelViewSet):
    """CRUD pour les relations."""

    queryset = Relation.objects.filter(is_active=True).select_related(
        'type', 'source__type', 'cible__type',
    )
    serializer_class = RelationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = RelationFilter
    ordering_fields = ['poids', 'date_debut', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AnomalieViewSet(viewsets.ReadOnlyModelViewSet):
    """Liste des anomalies + action traiter."""

    queryset = Anomalie.objects.filter(is_active=True).select_related(
        'entite__type', 'entite_liee__type',
    )
    serializer_class = AnomalieSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = AnomalieFilter
    ordering_fields = ['score', 'created_at', 'statut']

    @action(detail=True, methods=['post'])
    def traiter(self, request, pk=None):
        """Traite une anomalie (changer statut + commentaire)."""
        anomalie = self.get_object()
        serializer = AnomalieTraiterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        anomalie.statut = serializer.validated_data['statut']
        anomalie.commentaire_resolution = serializer.validated_data.get('commentaire', '')
        anomalie.traite_par = request.user
        anomalie.traite_at = timezone.now()
        anomalie.save(update_fields=[
            'statut', 'commentaire_resolution', 'traite_par', 'traite_at',
        ])

        return Response(AnomalieSerializer(anomalie).data)


class RequeteSauvegardeeViewSet(viewsets.ModelViewSet):
    """CRUD pour les requêtes sauvegardées."""

    serializer_class = RequeteSauvegardeeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RequeteSauvegardee.objects.filter(
            Q(created_by=self.request.user) | Q(partage=True),
            is_active=True,
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ========================================================================
# Function-Based Views
# ========================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recherche_semantique(request):
    """Recherche sémantique d'entités via pgvector."""
    serializer = RechercheSemantiquSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    from documents.embeddings import embedding_service

    query_embedding = embedding_service.generate_embedding(data['query'])
    if query_embedding is None:
        return Response(
            {'error': 'Impossible de générer l\'embedding pour cette requête'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    qs = (
        Entite.objects.filter(is_active=True, embedding__isnull=False)
        .annotate(distance=CosineDistance('embedding', query_embedding))
        .order_by('distance')
    )

    if data.get('types'):
        qs = qs.filter(type_id__in=data['types'])

    qs = qs[:data.get('limit', 20)]

    results = []
    for e in qs.select_related('type'):
        results.append({
            'id': str(e.pk),
            'nom': e.nom,
            'description': e.description[:200] if e.description else '',
            'type_nom': e.type.nom,
            'couleur': e.type.couleur,
            'icone': e.type.icone,
            'similarite': round(1 - e.distance, 4),
        })

    return Response({'results': results, 'query': data['query']})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def graph_stats(request):
    """Statistiques agrégées du graphe."""
    stats = {
        'entites': Entite.objects.filter(is_active=True).count(),
        'relations': Relation.objects.filter(is_active=True).count(),
        'types_entites': OntologieType.objects.filter(
            categorie='entity', is_active=True,
        ).count(),
        'types_relations': OntologieType.objects.filter(
            categorie='relation', is_active=True,
        ).count(),
        'anomalies_ouvertes': Anomalie.objects.filter(
            statut__in=['nouveau', 'en_cours'], is_active=True,
        ).count(),
        'entites_par_type': list(
            Entite.objects.filter(is_active=True)
            .values('type__nom', 'type__couleur', 'type__icone')
            .annotate(count=Count('id'))
            .order_by('-count')
        ),
        'anomalies_par_type': list(
            Anomalie.objects.filter(
                statut__in=['nouveau', 'en_cours'], is_active=True,
            )
            .values('type')
            .annotate(count=Count('id'))
            .order_by('-count')
        ),
    }
    return Response(stats)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_csv_view(request):
    """Import d'entités depuis un fichier CSV."""
    from .services.import_data import importer_csv

    file = request.FILES.get('file')
    type_id = request.data.get('type_id')
    mapping = request.data.get('mapping')

    if not file:
        return Response({'error': 'Fichier requis'}, status=400)
    if not type_id:
        return Response({'error': 'type_id requis'}, status=400)
    if not mapping or not isinstance(mapping, dict):
        return Response({'error': 'mapping requis (dict)'}, status=400)

    result = importer_csv(file, type_id, mapping, created_by=request.user)
    return Response(result, status=201 if result['created'] > 0 else 200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_document_view(request):
    """Import d'un document OCR comme entité du graphe."""
    from .services.import_data import importer_document_ocr

    document_id = request.data.get('document_id')
    if not document_id:
        return Response({'error': 'document_id requis'}, status=400)

    result = importer_document_ocr(document_id, created_by=request.user)
    if 'error' in result:
        return Response(result, status=404)
    return Response(result, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detecter_anomalies_view(request):
    """Lance la détection d'anomalies en tâche de fond."""
    from .tasks import detecter_anomalies_task

    task = detecter_anomalies_task.delay()
    return Response({'task_id': task.id, 'status': 'launched'}, status=202)
