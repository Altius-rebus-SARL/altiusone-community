# tva/viewset.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Q
from core.pdf import PDFViewSetMixin

from .models import (
    ConfigurationTVA,
    TauxTVA,
    CodeTVA,
    DeclarationTVA,
    LigneTVA,
    OperationTVA,
    CorrectionTVA,
)
from .serializers import (
    ConfigurationTVASerializer,
    TauxTVASerializer,
    CodeTVASerializer,
    DeclarationTVAListSerializer,
    DeclarationTVADetailSerializer,
    LigneTVASerializer,
    OperationTVASerializer,
    CorrectionTVASerializer,
)


class ConfigurationTVAViewSet(viewsets.ModelViewSet):
    """ViewSet pour les configurations TVA"""

    queryset = ConfigurationTVA.objects.all()
    serializer_class = ConfigurationTVASerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["mandat", "assujetti_tva", "methode_calcul"]


class TauxTVAViewSet(viewsets.ModelViewSet):
    """ViewSet pour les taux de TVA"""

    queryset = TauxTVA.objects.all()
    serializer_class = TauxTVASerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["type_taux"]
    ordering = ["-date_debut"]

    @action(detail=False, methods=["get"])
    def actifs(self, request):
        """Récupérer les taux actuellement en vigueur"""
        from datetime import date

        today = date.today()

        taux = self.queryset.filter(date_debut__lte=today).filter(
            Q(date_fin__gte=today) | Q(date_fin__isnull=True)
        )

        serializer = self.get_serializer(taux, many=True)
        return Response(serializer.data)


class CodeTVAViewSet(viewsets.ModelViewSet):
    """ViewSet pour les codes TVA"""

    queryset = CodeTVA.objects.all()
    serializer_class = CodeTVASerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["categorie", "actif"]
    search_fields = ["code", "libelle"]
    ordering = ["categorie", "ordre_affichage", "code"]


class DeclarationTVAViewSet(PDFViewSetMixin, viewsets.ModelViewSet):
    """ViewSet pour les déclarations TVA"""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["mandat", "annee", "trimestre", "semestre", "statut"]
    ordering = ["-annee", "-trimestre", "-semestre"]

    def get_queryset(self):
        return DeclarationTVA.objects.select_related(
            "mandat", "valide_par", "soumis_par"
        ).prefetch_related("lignes", "corrections", "operations")

    def get_serializer_class(self):
        if self.action == "list":
            return DeclarationTVAListSerializer
        return DeclarationTVADetailSerializer

    @action(detail=True, methods=["get"])
    def lignes(self, request, pk=None):
        """Récupérer toutes les lignes d'une déclaration"""
        declaration = self.get_object()
        lignes = declaration.lignes.all().order_by("ordre", "code_tva__code")
        serializer = LigneTVASerializer(lignes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def calculer(self, request, pk=None):
        """Calculer/recalculer les montants de la déclaration"""
        declaration = self.get_object()

        # Recalculer les montants des lignes
        for ligne in declaration.lignes.all():
            if ligne.calcul_automatique:
                ligne.calculer_montant()

        # Recalculer les totaux
        declaration.calculer_solde()

        serializer = self.get_serializer(declaration)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """Valider une déclaration"""
        declaration = self.get_object()

        if declaration.statut in ["VALIDE", "SOUMIS", "ACCEPTE"]:
            return Response(
                {"error": "Déclaration déjà validée"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        declaration.statut = "VALIDE"
        declaration.valide_par = request.user
        declaration.date_validation = timezone.now()
        declaration.save()

        serializer = self.get_serializer(declaration)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def soumettre(self, request, pk=None):
        """Soumettre une déclaration à l'AFC"""
        declaration = self.get_object()

        if declaration.statut != "VALIDE":
            return Response(
                {"error": "La déclaration doit être validée avant soumission"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Générer le XML AFC
        try:
            declaration.generer_xml()
        except Exception as e:
            return Response(
                {"error": f"Erreur lors de la génération XML: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        declaration.statut = "SOUMIS"
        declaration.soumis_par = request.user
        declaration.date_soumission = timezone.now()
        declaration.save()

        serializer = self.get_serializer(declaration)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def generer_xml(self, request, pk=None):
        """Générer le fichier XML pour l'AFC"""
        declaration = self.get_object()

        try:
            fichier = declaration.generer_xml()
            return Response(
                {
                    "message": "Fichier XML généré avec succès",
                    "fichier": fichier.url if fichier else None,
                }
            )
        except Exception as e:
            return Response(
                {"error": f"Erreur lors de la génération XML: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def generer_pdf(self, request, pk=None):
        """Générer le fichier PDF de la déclaration"""
        declaration = self.get_object()

        try:
            fichier = declaration.generer_pdf()
            return Response(
                {
                    "message": "Fichier PDF généré avec succès",
                    "fichier": fichier.url if fichier else None,
                }
            )
        except Exception as e:
            return Response(
                {"error": f"Erreur lors de la génération PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LigneTVAViewSet(viewsets.ModelViewSet):
    """ViewSet pour les lignes TVA"""

    queryset = LigneTVA.objects.all()
    serializer_class = LigneTVASerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["declaration", "code_tva"]

    @action(detail=True, methods=["post"])
    def calculer(self, request, pk=None):
        """Calculer le montant de TVA de la ligne"""
        ligne = self.get_object()
        montant = ligne.calculer_montant()

        return Response(
            {
                "montant_tva": montant,
                "base_imposable": ligne.base_imposable,
                "taux_tva": ligne.taux_tva,
            }
        )


class OperationTVAViewSet(viewsets.ModelViewSet):
    """ViewSet pour les opérations TVA"""

    queryset = OperationTVA.objects.all()
    serializer_class = OperationTVASerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "mandat",
        "declaration_tva",
        "type_operation",
        "integre_declaration",
    ]
    search_fields = ["libelle", "tiers", "numero_facture"]
    ordering = ["-date_operation"]

    @action(detail=False, methods=["get"])
    def non_integrees(self, request):
        """Récupérer les opérations non encore intégrées dans une déclaration"""
        mandat_id = request.query_params.get("mandat")

        if not mandat_id:
            return Response(
                {"error": "mandat requis"}, status=status.HTTP_400_BAD_REQUEST
            )

        operations = self.queryset.filter(
            mandat_id=mandat_id, integre_declaration=False
        )

        serializer = self.get_serializer(operations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def integrer(self, request):
        """Intégrer des opérations dans une déclaration"""
        declaration_id = request.data.get("declaration_id")
        operation_ids = request.data.get("operation_ids", [])

        if not declaration_id or not operation_ids:
            return Response(
                {"error": "declaration_id et operation_ids requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        operations = self.queryset.filter(id__in=operation_ids)
        operations.update(
            declaration_tva_id=declaration_id,
            integre_declaration=True,
            date_integration=timezone.now(),
        )

        return Response({"message": f"{operations.count()} opérations intégrées"})


class CorrectionTVAViewSet(viewsets.ModelViewSet):
    """ViewSet pour les corrections TVA"""

    queryset = CorrectionTVA.objects.all()
    serializer_class = CorrectionTVASerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["declaration", "type_correction"]
