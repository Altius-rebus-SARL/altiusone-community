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
    CategorieTemps,
)
from .serializers import (
    PrestationSerializer,
    TimeTrackingSerializer,
    TimeTrackingListSerializer,
    FactureListSerializer,
    FactureDetailSerializer,
    LigneFactureSerializer,
    PaiementSerializer,
    RelanceSerializer,
    TypePrestationSerializer,
    ZoneGeographiqueSerializer,
    TarifMandatSerializer,
    CategorieTempsSerializer,
)


class PrestationViewSet(viewsets.ModelViewSet):
    queryset = Prestation.objects.prefetch_related('types_mandats').all()
    serializer_class = PrestationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["type_prestation__code", "actif", "types_mandats__code"]


class CategorieTempsViewSet(viewsets.ModelViewSet):
    """ViewSet pour les catégories de temps (interne et absences)"""

    queryset = CategorieTemps.objects.all()
    serializer_class = CategorieTempsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["type_categorie", "is_active", "decompte_vacances", "decompte_maladie"]
    search_fields = ["code", "libelle"]

    @action(detail=False, methods=["get"])
    def internes(self, request):
        """Catégories de type INTERNE uniquement"""
        qs = self.queryset.filter(type_categorie="INTERNE", is_active=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def absences(self, request):
        """Catégories de type ABSENCE uniquement"""
        qs = self.queryset.filter(type_categorie="ABSENCE", is_active=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class TimeTrackingViewSet(viewsets.ModelViewSet):
    """ViewSet pour le suivi du temps : client, interne et absences"""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["mandat", "utilisateur", "facturable", "type_entree", "categorie", "valide", "position", "operation"]
    ordering_fields = ["date_travail", "duree_minutes", "created_at"]
    ordering = ["-date_travail"]

    def get_queryset(self):
        return TimeTracking.objects.select_related(
            "mandat", "utilisateur", "prestation", "categorie", "position", "operation"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return TimeTrackingListSerializer
        return TimeTrackingSerializer

    @action(detail=True, methods=["post"])
    def calculer_montant(self, request, pk=None):
        temps = self.get_object()
        if temps.type_entree != "CLIENT":
            return Response(
                {"error": "Le calcul de montant n'est applicable qu'aux entrées client"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        montant = temps.calculer_montant()
        return Response({"montant_ht": montant})

    @action(detail=False, methods=["get"])
    def non_factures(self, request):
        """Temps facturables non encore facturés"""
        qs = self.get_queryset().filter(
            type_entree="CLIENT", facturable=True, facture__isnull=True
        )
        serializer = TimeTrackingListSerializer(qs, many=True)
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

    @action(detail=False, methods=["get"])
    def mes_temps(self, request):
        """Temps de l'utilisateur connecté"""
        qs = self.get_queryset().filter(utilisateur=request.user)
        type_entree = request.query_params.get("type_entree")
        if type_entree:
            qs = qs.filter(type_entree=type_entree)
        serializer = TimeTrackingListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def solde_vacances(self, request):
        """Solde de vacances de l'utilisateur connecté (ou d'un utilisateur spécifié)"""
        from django.db.models import Sum

        utilisateur_id = request.query_params.get("utilisateur_id")
        if utilisateur_id and request.user.is_superuser:
            user_id = utilisateur_id
        else:
            user_id = request.user.pk

        # Récupérer le droit annuel depuis le profil Employe
        try:
            from salaires.models import Employe
            employe = Employe.objects.get(utilisateur_id=user_id)
            droit_annuel = employe.jours_vacances_annuel or 0
        except Employe.DoesNotExist:
            droit_annuel = 0

        # Calculer les jours pris (entrées ABSENCE avec catégorie decompte_vacances)
        annee = request.query_params.get("annee", timezone.now().year)
        jours_pris_minutes = TimeTracking.objects.filter(
            utilisateur_id=user_id,
            type_entree="ABSENCE",
            categorie__decompte_vacances=True,
            date_travail__year=annee,
        ).aggregate(total=Sum("duree_minutes"))["total"] or 0

        # Convertir en jours (8h = 480min)
        jours_pris = round(jours_pris_minutes / 480, 1)

        return Response({
            "annee": int(annee),
            "droit_annuel": droit_annuel,
            "jours_pris": jours_pris,
            "solde": round(droit_annuel - jours_pris, 1),
        })

    @action(detail=False, methods=["get"])
    def statistiques(self, request):
        """Statistiques de temps par type d'entrée pour un utilisateur/période"""
        from django.db.models import Sum, Count

        utilisateur_id = request.query_params.get("utilisateur_id", request.user.pk)
        annee = request.query_params.get("annee", timezone.now().year)
        mois = request.query_params.get("mois")

        qs = TimeTracking.objects.filter(
            utilisateur_id=utilisateur_id,
            date_travail__year=annee,
        )
        if mois:
            qs = qs.filter(date_travail__month=mois)

        stats = qs.values("type_entree").annotate(
            total_minutes=Sum("duree_minutes"),
            nombre_entrees=Count("id"),
        ).order_by("type_entree")

        # Détail par catégorie pour INTERNE et ABSENCE
        detail_categories = qs.exclude(
            type_entree="CLIENT"
        ).values(
            "categorie__code", "categorie__libelle", "type_entree"
        ).annotate(
            total_minutes=Sum("duree_minutes"),
            nombre_entrees=Count("id"),
        ).order_by("type_entree", "categorie__libelle")

        return Response({
            "annee": int(annee),
            "mois": int(mois) if mois else None,
            "par_type": list(stats),
            "par_categorie": list(detail_categories),
        })


class FactureViewSet(PDFViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_fields = ["client", "mandat", "statut", "position"]

    def get_queryset(self):
        return Facture.objects.select_related("client", "mandat", "position")

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

    @action(detail=True, methods=["get"])
    def stream_pdf(self, request, pk=None):
        """Stream le PDF de la facture (proxy pour mobile)."""
        from django.http import FileResponse
        facture = self.get_object()

        if not facture.fichier_pdf:
            return Response(
                {"error": "Aucun PDF disponible"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            file_obj = facture.fichier_pdf.open('rb')
            response = FileResponse(
                file_obj,
                content_type='application/pdf',
                as_attachment=False,
            )
            response['Content-Disposition'] = f'inline; filename="{facture.numero_facture}.pdf"'
            return response
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
    filterset_fields = ["facture", "facture__mandat", "mode_paiement"]

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
    filterset_fields = ["facture", "facture__mandat", "niveau", "envoyee"]

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
