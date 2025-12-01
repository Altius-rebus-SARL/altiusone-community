# facturation/viewset.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Prestation, TimeTracking, Facture, LigneFacture, Paiement, Relance
from .serializers import (
    PrestationSerializer,
    TimeTrackingSerializer,
    FactureListSerializer,
    FactureDetailSerializer,
    LigneFactureSerializer,
    PaiementSerializer,
    RelanceSerializer,
)


class PrestationViewSet(viewsets.ModelViewSet):
    queryset = Prestation.objects.all()
    serializer_class = PrestationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["type_prestation", "actif"]


class TimeTrackingViewSet(viewsets.ModelViewSet):
    queryset = TimeTracking.objects.all()
    serializer_class = TimeTrackingSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["mandat", "utilisateur", "facturable"]

    @action(detail=True, methods=["post"])
    def calculer_montant(self, request, pk=None):
        temps = self.get_object()
        montant = temps.calculer_montant()
        return Response({"montant_ht": montant})


class FactureViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_fields = ["client", "mandat", "statut"]

    def get_queryset(self):
        return Facture.objects.select_related("client", "mandat")

    def get_serializer_class(self):
        if self.action == "list":
            return FactureListSerializer
        return FactureDetailSerializer

    @action(detail=True, methods=["post"])
    def generer_qr(self, request, pk=None):
        facture = self.get_object()
        reference = facture.generer_qr_reference()
        return Response({"qr_reference": reference})

    @action(detail=True, methods=["post"])
    def generer_pdf(self, request, pk=None):
        # TODO: Implémenter génération PDF
        return Response({"message": "PDF généré"})


class LigneFactureViewSet(viewsets.ModelViewSet):
    queryset = LigneFacture.objects.all()
    serializer_class = LigneFactureSerializer
    permission_classes = [IsAuthenticated]


class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer
    permission_classes = [IsAuthenticated]


class RelanceViewSet(viewsets.ModelViewSet):
    queryset = Relance.objects.all()
    serializer_class = RelanceSerializer
    permission_classes = [IsAuthenticated]
