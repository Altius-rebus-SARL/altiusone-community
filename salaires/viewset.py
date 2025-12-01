# salaires/viewset.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import (
    Employe,
    TauxCotisation,
    FicheSalaire,
    CertificatSalaire,
    DeclarationCotisations,
)
from .serializers import (
    EmployeListSerializer,
    EmployeDetailSerializer,
    TauxCotisationSerializer,
    FicheSalaireListSerializer,
    FicheSalaireDetailSerializer,
    CertificatSalaireSerializer,
    DeclarationCotisationsSerializer,
)


class EmployeViewSet(viewsets.ModelViewSet):
    """ViewSet pour les employés"""

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["mandat", "statut", "type_contrat", "fonction"]
    search_fields = ["nom", "prenom", "matricule", "avs_number"]
    ordering = ["nom", "prenom"]

    def get_queryset(self):
        return Employe.objects.select_related("mandat", "adresse")

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeListSerializer
        return EmployeDetailSerializer

    @action(detail=True, methods=["get"])
    def fiches_salaire(self, request, pk=None):
        """Récupérer toutes les fiches de salaire d'un employé"""
        employe = self.get_object()
        fiches = employe.fiches_salaire.all().order_by("-periode")
        serializer = FicheSalaireListSerializer(fiches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def actifs(self, request):
        """Récupérer uniquement les employés actifs"""
        employes = self.get_queryset().filter(statut="ACTIF")
        serializer = self.get_serializer(employes, many=True)
        return Response(serializer.data)


class TauxCotisationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les taux de cotisations"""

    queryset = TauxCotisation.objects.all()
    serializer_class = TauxCotisationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["type_cotisation", "actif"]
    ordering = ["type_cotisation", "-date_debut"]

    @action(detail=False, methods=["get"])
    def actifs(self, request):
        """Récupérer les taux actuellement en vigueur"""
        from datetime import date

        today = date.today()

        taux_actifs = []
        for type_cot in TauxCotisation.TYPE_COTISATION_CHOICES:
            taux = TauxCotisation.get_taux_actif(type_cot[0], today)
            if taux:
                taux_actifs.append(taux)

        serializer = self.get_serializer(taux_actifs, many=True)
        return Response(serializer.data)


class FicheSalaireViewSet(viewsets.ModelViewSet):
    """ViewSet pour les fiches de salaire"""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["employe", "statut", "annee", "mois"]
    ordering = ["-periode"]

    def get_queryset(self):
        return FicheSalaire.objects.select_related("employe", "valide_par")

    def get_serializer_class(self):
        if self.action == "list":
            return FicheSalaireListSerializer
        return FicheSalaireDetailSerializer

    @action(detail=True, methods=["post"])
    def calculer(self, request, pk=None):
        """Calculer tous les montants d'une fiche de salaire"""
        fiche = self.get_object()

        if fiche.statut != "BROUILLON":
            return Response(
                {"error": "Seules les fiches en brouillon peuvent être recalculées"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        salaire_net = fiche.calculer()

        return Response(
            {
                "salaire_net": salaire_net,
                "salaire_brut_total": fiche.salaire_brut_total,
                "total_deductions": fiche.total_deductions,
            }
        )

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """Valider une fiche de salaire"""
        fiche = self.get_object()

        if fiche.statut != "BROUILLON":
            return Response(
                {"error": "Fiche déjà validée"}, status=status.HTTP_400_BAD_REQUEST
            )

        fiche.statut = "VALIDE"
        fiche.valide_par = request.user
        fiche.date_validation = timezone.now()
        fiche.save()

        serializer = self.get_serializer(fiche)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def generer_pdf(self, request, pk=None):
        """Générer le PDF d'une fiche de salaire"""
        fiche = self.get_object()

        # TODO: Implémenter la génération PDF

        return Response(
            {
                "message": "PDF généré",
                "fichier": fiche.fichier_pdf.url if fiche.fichier_pdf else None,
            }
        )

    @action(detail=False, methods=["post"])
    def generer_lot(self, request):
        """Générer un lot de fiches de salaire pour une période"""
        mandat_id = request.data.get("mandat_id")
        periode = request.data.get("periode")  # Format: YYYY-MM-DD

        if not mandat_id or not periode:
            return Response(
                {"error": "mandat_id et periode requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupérer les employés actifs du mandat
        employes = Employe.objects.filter(mandat_id=mandat_id, statut="ACTIF")

        fiches_creees = []
        for employe in employes:
            # Créer la fiche
            fiche = FicheSalaire.objects.create(
                employe=employe,
                periode=periode,
                salaire_base=employe.salaire_brut_mensuel,
            )
            fiches_creees.append(fiche)

        return Response(
            {
                "message": f"{len(fiches_creees)} fiches créées",
                "fiches": FicheSalaireListSerializer(fiches_creees, many=True).data,
            }
        )


class CertificatSalaireViewSet(viewsets.ModelViewSet):
    """ViewSet pour les certificats de salaire"""

    queryset = CertificatSalaire.objects.all()
    serializer_class = CertificatSalaireSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["employe", "annee"]
    ordering = ["-annee"]

    @action(detail=True, methods=["post"])
    def generer_pdf(self, request, pk=None):
        """Générer le PDF du certificat de salaire"""
        certificat = self.get_object()

        # TODO: Implémenter la génération PDF

        return Response(
            {
                "message": "PDF généré",
                "fichier": certificat.fichier_pdf.url
                if certificat.fichier_pdf
                else None,
            }
        )


class DeclarationCotisationsViewSet(viewsets.ModelViewSet):
    """ViewSet pour les déclarations de cotisations"""

    queryset = DeclarationCotisations.objects.all()
    serializer_class = DeclarationCotisationsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["mandat", "organisme"]
    ordering = ["-date_declaration"]
