# fiscalite/viewset.py
from rest_framework import viewsets
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


class OptimisationFiscaleViewSet(viewsets.ModelViewSet):
    queryset = OptimisationFiscale.objects.all()
    serializer_class = OptimisationFiscaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "categorie", "statut"]
