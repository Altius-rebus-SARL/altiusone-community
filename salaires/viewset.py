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
    """ViewSet pour les employés

    Permissions:
    - Superuser / Manager: tous les employés
    - STAFF Employé: employés des mandats où il est responsable/équipe
    - STAFF Prestataire: employés des mandats assignés via CollaborateurFiduciaire
    - CLIENT: employés des mandats accessibles via AccesMandat
    """

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
        user = self.request.user
        base_queryset = Employe.objects.select_related("mandat", "adresse", "utilisateur")

        # Superuser ou Manager: accès complet
        if user.is_superuser or (user.is_staff_user() and user.is_manager()):
            return base_queryset

        # Filtrer par mandats accessibles
        accessible_mandats = user.get_accessible_mandats()
        return base_queryset.filter(mandat__in=accessible_mandats)

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

    @action(detail=True, methods=["post"])
    def lier_utilisateur(self, request, pk=None):
        """
        Lie un employé à un compte utilisateur existant.
        Le compte doit exister et ne pas être déjà lié à un autre employé.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()
        employe = self.get_object()

        utilisateur_id = request.data.get("utilisateur_id")
        if not utilisateur_id:
            return Response(
                {"error": "utilisateur_id requis"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            utilisateur = User.objects.get(id=utilisateur_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Utilisateur non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )

        # Vérifier que l'utilisateur n'est pas déjà lié à un autre employé
        if hasattr(utilisateur, "employe_record") and utilisateur.employe_record:
            if utilisateur.employe_record.id != employe.id:
                return Response(
                    {"error": "Cet utilisateur est déjà lié à un autre employé"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        employe.utilisateur = utilisateur
        employe.save(update_fields=["utilisateur", "updated_at"])

        serializer = self.get_serializer(employe)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def creer_compte(self, request, pk=None):
        """
        Crée un compte utilisateur pour cet employé et le lie automatiquement.
        Utilise l'email de l'employé comme username.
        """
        from django.contrib.auth import get_user_model
        from core.models import Role, TypeCollaborateur

        User = get_user_model()
        employe = self.get_object()

        # Vérifier que l'employé n'a pas déjà un compte lié
        if employe.utilisateur:
            return Response(
                {"error": "Cet employé a déjà un compte utilisateur lié"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier que l'email de l'employé est renseigné
        if not employe.email:
            return Response(
                {"error": "L'employé doit avoir une adresse email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier qu'aucun utilisateur n'existe avec cet email
        if User.objects.filter(email=employe.email).exists():
            return Response(
                {"error": f"Un utilisateur avec l'email {employe.email} existe déjà"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupérer le rôle client par défaut
        role_client = Role.objects.filter(code=Role.CLIENT, actif=True).first()

        # Générer un mot de passe temporaire
        import secrets

        temp_password = secrets.token_urlsafe(12)

        # Créer l'utilisateur
        utilisateur = User.objects.create_user(
            username=employe.email,
            email=employe.email,
            password=temp_password,
            first_name=employe.prenom,
            last_name=employe.nom,
            type_utilisateur=User.TypeUtilisateur.CLIENT,
            type_collaborateur=TypeCollaborateur.EMPLOYE,
            role=role_client,
            doit_changer_mot_de_passe=True,
        )

        # Lier l'employé à l'utilisateur
        employe.utilisateur = utilisateur
        employe.save(update_fields=["utilisateur", "updated_at"])

        # TODO: Envoyer un email avec les identifiants
        # from mailing.services import email_service
        # email_service.send_template_email(...)

        return Response(
            {
                "message": "Compte créé avec succès",
                "utilisateur_id": str(utilisateur.id),
                "email": utilisateur.email,
                "mot_de_passe_temporaire": temp_password,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def delier_utilisateur(self, request, pk=None):
        """Supprime le lien entre un employé et son compte utilisateur"""
        employe = self.get_object()

        if not employe.utilisateur:
            return Response(
                {"error": "Cet employé n'a pas de compte utilisateur lié"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employe.utilisateur = None
        employe.save(update_fields=["utilisateur", "updated_at"])

        return Response({"message": "Lien supprimé avec succès"})


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
    """ViewSet pour les fiches de salaire

    Permissions: Fiches des employés accessibles selon les permissions de l'utilisateur
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["employe", "statut", "annee", "mois"]
    ordering = ["-periode"]

    def get_queryset(self):
        user = self.request.user
        base_queryset = FicheSalaire.objects.select_related(
            "employe", "employe__mandat", "valide_par"
        )

        # Superuser ou Manager: accès complet
        if user.is_superuser or (user.is_staff_user() and user.is_manager()):
            return base_queryset

        # Filtrer par mandats accessibles
        accessible_mandats = user.get_accessible_mandats()
        return base_queryset.filter(employe__mandat__in=accessible_mandats)

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
    """ViewSet pour les certificats de salaire

    Permissions: Certificats des employés accessibles selon les permissions de l'utilisateur
    """

    serializer_class = CertificatSalaireSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["employe", "annee"]
    ordering = ["-annee"]

    def get_queryset(self):
        user = self.request.user
        base_queryset = CertificatSalaire.objects.select_related(
            "employe", "employe__mandat", "genere_par"
        )

        # Superuser ou Manager: accès complet
        if user.is_superuser or (user.is_staff_user() and user.is_manager()):
            return base_queryset

        # Filtrer par mandats accessibles
        accessible_mandats = user.get_accessible_mandats()
        return base_queryset.filter(employe__mandat__in=accessible_mandats)

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
    """ViewSet pour les déclarations de cotisations

    Permissions: Déclarations des mandats accessibles selon les permissions de l'utilisateur
    """

    serializer_class = DeclarationCotisationsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["mandat", "organisme"]
    ordering = ["-date_declaration"]

    def get_queryset(self):
        user = self.request.user
        base_queryset = DeclarationCotisations.objects.select_related("mandat")

        # Superuser ou Manager: accès complet
        if user.is_superuser or (user.is_staff_user() and user.is_manager()):
            return base_queryset

        # Filtrer par mandats accessibles
        accessible_mandats = user.get_accessible_mandats()
        return base_queryset.filter(mandat__in=accessible_mandats)
