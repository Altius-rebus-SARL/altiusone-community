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
        """Génère le PDF de la facture et retourne l'URL de téléchargement"""
        facture = self.get_object()
        avec_qr_bill = request.data.get("avec_qr_bill", False)

        try:
            facture.generer_pdf(avec_qr_bill=avec_qr_bill)
            return Response({
                "message": "PDF généré",
                "url": facture.fichier_pdf.url if facture.fichier_pdf else None,
                "nom_fichier": facture.fichier_pdf.name.split("/")[-1] if facture.fichier_pdf else None,
            })
        except Exception as e:
            return Response(
                {"error": f"Erreur lors de la génération du PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def download_pdf(self, request, pk=None):
        """Retourne l'URL présignée pour télécharger le PDF de la facture"""
        facture = self.get_object()

        if not facture.fichier_pdf:
            return Response(
                {"error": "Aucun PDF disponible pour cette facture"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "url": facture.fichier_pdf.url,
            "nom_fichier": facture.fichier_pdf.name.split("/")[-1],
            "numero_facture": facture.numero_facture,
        })


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

    @action(detail=True, methods=["get"])
    def download_pdf(self, request, pk=None):
        """Retourne l'URL présignée pour télécharger le PDF de la relance"""
        relance = self.get_object()

        if not relance.fichier_pdf:
            return Response(
                {"error": "Aucun PDF disponible pour cette relance"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "url": relance.fichier_pdf.url,
            "nom_fichier": relance.fichier_pdf.name.split("/")[-1],
        })
