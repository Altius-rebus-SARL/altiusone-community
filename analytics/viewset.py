# analytics/viewset.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import (
    TableauBord,
    Indicateur,
    ValeurIndicateur,
    Rapport,
    PlanificationRapport,
    ComparaisonPeriode,
    AlerteMetrique,
    ExportDonnees,
)
from .serializers import (
    TableauBordSerializer,
    IndicateurSerializer,
    ValeurIndicateurSerializer,
    RapportListSerializer,
    RapportDetailSerializer,
    PlanificationRapportSerializer,
    ComparaisonPeriodeSerializer,
    AlerteMetriqueSerializer,
    ExportDonneesSerializer,
)


class TableauBordViewSet(viewsets.ModelViewSet):
    serializer_class = TableauBordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["proprietaire", "visibilite"]

    def get_queryset(self):
        user = self.request.user
        return TableauBord.objects.filter(
            Q(proprietaire=user) | Q(utilisateurs_partage=user) | Q(visibilite="TOUS")
        ).distinct()


class IndicateurViewSet(viewsets.ModelViewSet):
    queryset = Indicateur.objects.all()
    serializer_class = IndicateurSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["categorie", "type_calcul", "periodicite", "actif"]


class ValeurIndicateurViewSet(viewsets.ModelViewSet):
    queryset = ValeurIndicateur.objects.all()
    serializer_class = ValeurIndicateurSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["indicateur", "mandat", "date_mesure"]


class RapportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "type_rapport", "statut"]

    def get_queryset(self):
        return Rapport.objects.select_related("mandat", "genere_par")

    def get_serializer_class(self):
        if self.action == "list":
            return RapportListSerializer
        return RapportDetailSerializer


class PlanificationRapportViewSet(viewsets.ModelViewSet):
    queryset = PlanificationRapport.objects.all()
    serializer_class = PlanificationRapportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "frequence", "actif"]


class ComparaisonPeriodeViewSet(viewsets.ModelViewSet):
    queryset = ComparaisonPeriode.objects.all()
    serializer_class = ComparaisonPeriodeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "type_comparaison"]


class AlerteMetriqueViewSet(viewsets.ModelViewSet):
    queryset = AlerteMetrique.objects.all()
    serializer_class = AlerteMetriqueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["indicateur", "mandat", "niveau", "statut"]

    @action(detail=True, methods=["post"])
    def acquitter(self, request, pk=None):
        alerte = self.get_object()
        alerte.statut = "ACQUITTEE"
        alerte.acquittee_par = request.user
        alerte.date_acquittement = timezone.now()
        alerte.commentaire = request.data.get("commentaire", "")
        alerte.save()

        serializer = self.get_serializer(alerte)
        return Response(serializer.data)


class ExportDonneesViewSet(viewsets.ModelViewSet):
    queryset = ExportDonnees.objects.all()
    serializer_class = ExportDonneesSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "type_export", "format_export"]
