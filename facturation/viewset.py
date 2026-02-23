# facturation/viewset.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from core.pdf import PDFViewSetMixin
from .models import (
    Prestation,
    TimeTracking,
    Facture,
    LigneFacture,
    Paiement,
    Relance,
    TypePrestation,
    ZoneGeographique,
    TarifMandat,
)
from .serializers import (
    PrestationSerializer,
    TimeTrackingSerializer,
    FactureListSerializer,
    FactureDetailSerializer,
    LigneFactureSerializer,
    PaiementSerializer,
    RelanceSerializer,
    TypePrestationSerializer,
    ZoneGeographiqueSerializer,
    TarifMandatSerializer,
)


class PrestationViewSet(viewsets.ModelViewSet):
    queryset = Prestation.objects.all()
    serializer_class = PrestationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["type_prestation__code", "actif"]


class TimeTrackingViewSet(viewsets.ModelViewSet):
    queryset = TimeTracking.objects.all()
    serializer_class = TimeTrackingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "utilisateur", "facturable"]

    @action(detail=True, methods=["post"])
    def calculer_montant(self, request, pk=None):
        temps = self.get_object()
        montant = temps.calculer_montant()
        return Response({"montant_ht": montant})

    @action(detail=False, methods=["get"])
    def non_factures(self, request):
        """Temps facturables non encore facturés"""
        qs = self.queryset.filter(facturable=True, facture__isnull=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """Valider une entrée de temps"""
        temps = self.get_object()
        if temps.valide:
            return Response(
                {"error": "Ce temps est déjà validé"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        temps.valide = True
        temps.valide_par = request.user
        temps.save(update_fields=["valide", "valide_par"])
        serializer = self.get_serializer(temps)
        return Response(serializer.data)


class FactureViewSet(PDFViewSetMixin, viewsets.ModelViewSet):
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

    @action(detail=True, methods=["post"])
    def calculer(self, request, pk=None):
        """Recalculer montant_ht/tva/ttc depuis les lignes"""
        facture = self.get_object()
        facture.calculer_totaux()
        serializer = self.get_serializer(facture)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """Passer la facture de BROUILLON à EMISE"""
        facture = self.get_object()
        if facture.statut != "BROUILLON":
            return Response(
                {"error": "Seule une facture en brouillon peut être validée"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        facture.statut = "EMISE"
        facture.date_validation = timezone.now()
        facture.validee_par = request.user
        facture.save(update_fields=["statut", "date_validation", "validee_par"])
        serializer = self.get_serializer(facture)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def envoyer(self, request, pk=None):
        """Marquer la facture comme envoyée"""
        facture = self.get_object()
        if facture.statut not in ("EMISE", "BROUILLON"):
            return Response(
                {"error": "La facture doit être émise pour être envoyée"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        facture.statut = "ENVOYEE"
        facture.save(update_fields=["statut"])
        serializer = self.get_serializer(facture)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def impayees(self, request):
        """Factures envoyées dont l'échéance est dépassée"""
        from datetime import date

        qs = self.get_queryset().filter(
            statut="ENVOYEE", date_echeance__lt=date.today()
        )
        serializer = FactureListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def en_retard(self, request):
        """Factures dépassant l'échéance (tous statuts non payés)"""
        from datetime import date

        qs = self.get_queryset().filter(
            date_echeance__lt=date.today()
        ).exclude(statut__in=["PAYEE", "ANNULEE", "AVOIR"])
        serializer = FactureListSerializer(qs, many=True)
        return Response(serializer.data)


class LigneFactureViewSet(viewsets.ModelViewSet):
    queryset = LigneFacture.objects.all()
    serializer_class = LigneFactureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["facture"]


class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["facture", "mode_paiement"]

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """Valider un paiement"""
        paiement = self.get_object()
        if paiement.valide:
            return Response(
                {"error": "Ce paiement est déjà validé"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        paiement.valide = True
        paiement.valide_par = request.user
        paiement.date_validation = timezone.now()
        paiement.save()
        serializer = self.get_serializer(paiement)
        return Response(serializer.data)


class RelanceViewSet(viewsets.ModelViewSet):
    queryset = Relance.objects.all()
    serializer_class = RelanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["facture", "niveau", "envoyee"]

    @action(detail=True, methods=["post"])
    def envoyer(self, request, pk=None):
        """Marquer la relance comme envoyée"""
        relance = self.get_object()
        if relance.envoyee:
            return Response(
                {"error": "Cette relance a déjà été envoyée"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from datetime import date

        relance.envoyee = True
        relance.date_envoi = date.today()
        relance.save(update_fields=["envoyee", "date_envoi"])
        serializer = self.get_serializer(relance)
        return Response(serializer.data)

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


class TypePrestationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les types de prestation"""

    queryset = TypePrestation.objects.all()
    serializer_class = TypePrestationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active"]
    search_fields = ["code", "libelle"]


class ZoneGeographiqueViewSet(viewsets.ModelViewSet):
    """ViewSet pour les zones géographiques"""

    queryset = ZoneGeographique.objects.all()
    serializer_class = ZoneGeographiqueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["nom"]


class TarifMandatViewSet(viewsets.ModelViewSet):
    """ViewSet pour les tarifs par mandat"""

    queryset = TarifMandat.objects.select_related("mandat", "prestation").all()
    serializer_class = TarifMandatSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "prestation"]
