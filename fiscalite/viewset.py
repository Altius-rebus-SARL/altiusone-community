# fiscalite/viewset.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import (
    DeclarationFiscale,
    AnnexeFiscale,
    CorrectionFiscale,
    ReportPerte,
    TauxImposition,
    OptimisationFiscale,
    ReclamationFiscale,
    UtilisationPerte,
)
from .serializers import (
    DeclarationFiscaleListSerializer,
    DeclarationFiscaleDetailSerializer,
    AnnexeFiscaleSerializer,
    CorrectionFiscaleSerializer,
    ReportPerteSerializer,
    TauxImpositionSerializer,
    OptimisationFiscaleSerializer,
    ReclamationFiscaleSerializer,
    UtilisationPerteSerializer,
)


class DeclarationFiscaleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "annee_fiscale", "type_impot", "statut"]

    def get_queryset(self):
        return DeclarationFiscale.objects.select_related("mandat__client")

    def get_serializer_class(self):
        if self.action == "list":
            return DeclarationFiscaleListSerializer
        return DeclarationFiscaleDetailSerializer

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """Passer la déclaration au statut A_VALIDER"""
        declaration = self.get_object()
        if declaration.statut not in ("BROUILLON", "EN_PREPARATION"):
            return Response(
                {"error": "La déclaration ne peut pas être validée dans son état actuel"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        declaration.statut = "A_VALIDER"
        declaration.save(update_fields=["statut"])
        serializer = self.get_serializer(declaration)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def soumettre(self, request, pk=None):
        """Soumettre la déclaration (statut → DEPOSE)"""
        declaration = self.get_object()
        if declaration.statut not in ("VALIDE", "A_VALIDER"):
            return Response(
                {"error": "La déclaration doit être validée avant soumission"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        declaration.statut = "DEPOSE"
        declaration.date_depot = timezone.now().date()
        declaration.save(update_fields=["statut", "date_depot"])
        serializer = self.get_serializer(declaration)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def populate_comptabilite(self, request, pk=None):
        """Peupler la déclaration depuis les données comptables"""
        from .services.auto_populate import populate_from_comptabilite
        declaration = self.get_object()
        success = populate_from_comptabilite(declaration)
        if success:
            serializer = self.get_serializer(declaration)
            return Response(serializer.data)
        return Response(
            {"error": "Impossible de pré-remplir : vérifiez l'exercice comptable lié"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"])
    def annexes(self, request, pk=None):
        """Liste des annexes liées à cette déclaration"""
        declaration = self.get_object()
        annexes = declaration.annexes.all().order_by("ordre")
        serializer = AnnexeFiscaleSerializer(annexes, many=True)
        return Response(serializer.data)


class AnnexeFiscaleViewSet(viewsets.ModelViewSet):
    queryset = AnnexeFiscale.objects.select_related("declaration")
    serializer_class = AnnexeFiscaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["declaration", "type_annexe"]


class CorrectionFiscaleViewSet(viewsets.ModelViewSet):
    queryset = CorrectionFiscale.objects.select_related("declaration", "compte")
    serializer_class = CorrectionFiscaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["declaration", "type_correction"]


class ReportPerteViewSet(viewsets.ModelViewSet):
    queryset = ReportPerte.objects.select_related("mandat__client")
    serializer_class = ReportPerteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "expire"]

    @action(detail=False, methods=["get"])
    def disponibles(self, request):
        """Reports de pertes non expirés avec montant restant > 0"""
        qs = self.queryset.filter(expire=False, montant_restant__gt=0)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


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
    queryset = OptimisationFiscale.objects.select_related("mandat__client")
    serializer_class = OptimisationFiscaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "categorie", "statut"]


class ReclamationFiscaleViewSet(viewsets.ModelViewSet):
    """ViewSet pour les réclamations fiscales"""

    queryset = ReclamationFiscale.objects.select_related("declaration").all()
    serializer_class = ReclamationFiscaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["declaration", "statut"]


class UtilisationPerteViewSet(viewsets.ModelViewSet):
    """ViewSet pour les utilisations de pertes"""

    queryset = UtilisationPerte.objects.select_related(
        "report_perte", "declaration_fiscale"
    ).all()
    serializer_class = UtilisationPerteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["report_perte", "declaration_fiscale"]
