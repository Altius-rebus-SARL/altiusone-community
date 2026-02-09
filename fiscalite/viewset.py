# fiscalite/viewset.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    DeclarationFiscale,
    AnnexeFiscale,
    CorrectionFiscale,
    ReportPerte,
    TauxImposition,
    OptimisationFiscale,
)
from .serializers import (
    DeclarationFiscaleListSerializer,
    DeclarationFiscaleDetailSerializer,
    AnnexeFiscaleSerializer,
    CorrectionFiscaleSerializer,
    ReportPerteSerializer,
    TauxImpositionSerializer,
    OptimisationFiscaleSerializer,
)


class DeclarationFiscaleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "annee_fiscale", "type_impot", "statut"]

    def get_queryset(self):
        return DeclarationFiscale.objects.select_related("mandat")

    def get_serializer_class(self):
        if self.action == "list":
            return DeclarationFiscaleListSerializer
        return DeclarationFiscaleDetailSerializer


class AnnexeFiscaleViewSet(viewsets.ModelViewSet):
    queryset = AnnexeFiscale.objects.all()
    serializer_class = AnnexeFiscaleSerializer
    permission_classes = [IsAuthenticated]


class CorrectionFiscaleViewSet(viewsets.ModelViewSet):
    queryset = CorrectionFiscale.objects.all()
    serializer_class = CorrectionFiscaleSerializer
    permission_classes = [IsAuthenticated]


class ReportPerteViewSet(viewsets.ModelViewSet):
    queryset = ReportPerte.objects.all()
    serializer_class = ReportPerteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "expire"]


class TauxImpositionViewSet(viewsets.ModelViewSet):
    queryset = TauxImposition.objects.all()
    serializer_class = TauxImpositionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["canton", "type_impot", "annee"]

    @action(detail=False, methods=['get'], url_path='preview-estv')
    def preview_estv(self, request):
        """
        Preview des taux ESTV sans sauvegarder.
        GET /api/v1/fiscalite/taux/preview-estv/?canton=ZH&commune_bfs_nr=261&year=2025
        """
        from fiscalite.services import EstvTaxRateService

        canton = request.query_params.get('canton', '').strip().upper()
        commune_bfs_nr = request.query_params.get('commune_bfs_nr', '')
        year = request.query_params.get('year', '')

        if not canton or not commune_bfs_nr or not year:
            return Response(
                {'error': 'canton, commune_bfs_nr et year requis'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            commune_bfs_nr = int(commune_bfs_nr)
            year = int(year)
        except ValueError:
            return Response(
                {'error': 'commune_bfs_nr et year doivent etre des entiers'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = EstvTaxRateService.fetch_tax_rates(canton, commune_bfs_nr, year)
        if result.error:
            return Response({'error': result.error}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            'canton': result.canton,
            'commune': result.commune,
            'commune_bfs_nr': result.commune_bfs_nr,
            'year': result.year,
            'federal_rate': str(result.federal_rate) if result.federal_rate else None,
            'cantonal_rate': str(result.cantonal_rate) if result.cantonal_rate else None,
            'communal_rate': str(result.communal_rate) if result.communal_rate else None,
            'multiplicateurs': result.multiplicateurs,
        })

    @action(detail=False, methods=['post'], url_path='fetch-estv')
    def fetch_estv(self, request):
        """
        Fetch et sauvegarde les taux ESTV.
        POST /api/v1/fiscalite/taux/fetch-estv/
        Body: {canton, commune_bfs_nr, year, commune_name (optionnel)}
        """
        from fiscalite.services import EstvTaxRateService

        canton = request.data.get('canton', '').strip().upper()
        commune_bfs_nr = request.data.get('commune_bfs_nr')
        year = request.data.get('year')
        commune_name = request.data.get('commune_name')

        if not canton or not commune_bfs_nr or not year:
            return Response(
                {'error': 'canton, commune_bfs_nr et year requis'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            commune_bfs_nr = int(commune_bfs_nr)
            year = int(year)
        except (ValueError, TypeError):
            return Response(
                {'error': 'commune_bfs_nr et year doivent etre des entiers'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = EstvTaxRateService.populate_taux_imposition(
            canton, commune_bfs_nr, year, commune_name
        )
        if result.get('errors'):
            return Response(result, status=status.HTTP_207_MULTI_STATUS)
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        """
        Import CSV fallback pour les taux d'imposition.
        POST /api/v1/fiscalite/taux/import-csv/
        Multipart: file + year
        """
        from fiscalite.services import EstvTaxRateService

        csv_file = request.FILES.get('file')
        year = request.data.get('year')

        if not csv_file or not year:
            return Response(
                {'error': 'file et year requis'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response(
                {'error': 'year doit etre un entier'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        csv_content = csv_file.read()
        result = EstvTaxRateService.import_from_csv(csv_content, year)

        if result.get('errors'):
            return Response(result, status=status.HTTP_207_MULTI_STATUS)
        return Response(result, status=status.HTTP_201_CREATED)


class OptimisationFiscaleViewSet(viewsets.ModelViewSet):
    queryset = OptimisationFiscale.objects.all()
    serializer_class = OptimisationFiscaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "categorie", "statut"]
