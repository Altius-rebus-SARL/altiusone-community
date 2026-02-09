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
    CertificatSalaireListSerializer,
    CertificatSalaireDetailSerializer,
    CertificatSalaireCreateSerializer,
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
    """ViewSet pour les certificats de salaire - Formulaire 11 suisse

    Permissions: Certificats des employés accessibles selon les permissions de l'utilisateur

    Actions disponibles:
    - list: Liste des certificats
    - retrieve: Détail d'un certificat
    - create: Créer un certificat (avec option auto_calculer)
    - update/partial_update: Modifier un certificat
    - delete: Supprimer un certificat
    - calculer: Recalculer depuis les fiches de salaire
    - generer_pdf: Générer le PDF Formulaire 11
    - valider: Marquer comme vérifié
    - signer: Signer le certificat
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["employe", "annee", "statut", "est_signe"]
    search_fields = ["employe__nom", "employe__prenom", "employe__matricule"]
    ordering = ["-annee", "-created_at"]

    def get_queryset(self):
        user = self.request.user
        base_queryset = CertificatSalaire.objects.select_related(
            "employe", "employe__mandat", "employe__mandat__client", "genere_par"
        )

        # Superuser ou Manager: accès complet
        if user.is_superuser or (user.is_staff_user() and user.is_manager()):
            return base_queryset

        # Filtrer par mandats accessibles
        accessible_mandats = user.get_accessible_mandats()
        return base_queryset.filter(employe__mandat__in=accessible_mandats)

    def get_serializer_class(self):
        if self.action == "list":
            return CertificatSalaireListSerializer
        elif self.action == "create":
            return CertificatSalaireCreateSerializer
        elif self.action in ["retrieve", "update", "partial_update"]:
            return CertificatSalaireDetailSerializer
        return CertificatSalaireSerializer

    def perform_create(self, serializer):
        """Enregistre l'utilisateur qui crée le certificat"""
        serializer.save(genere_par=self.request.user)

    @action(detail=True, methods=["post"])
    def calculer(self, request, pk=None):
        """Recalculer le certificat depuis les fiches de salaire validées.

        Agrège toutes les fiches de salaire validées de l'année pour remplir
        automatiquement les champs du Formulaire 11.
        """
        certificat = self.get_object()

        try:
            certificat.calculer_depuis_fiches(save=True)
            return Response({
                "message": "Certificat recalculé avec succès",
                "statut": certificat.statut,
                "chiffre_8_total_brut": str(certificat.chiffre_8_total_brut),
                "chiffre_11_net": str(certificat.chiffre_11_net),
                "date_debut": certificat.date_debut.isoformat() if certificat.date_debut else None,
                "date_fin": certificat.date_fin.isoformat() if certificat.date_fin else None,
            })
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def generer_pdf(self, request, pk=None):
        """Générer le PDF du certificat de salaire au format Formulaire 11.

        Le PDF généré est conforme au format officiel suisse de l'AFC.
        """
        certificat = self.get_object()

        try:
            certificat.generer_pdf_formulaire11()
            return Response({
                "message": "PDF Formulaire 11 généré avec succès",
                "fichier": certificat.fichier_pdf.url if certificat.fichier_pdf else None,
                "filename": certificat.fichier_pdf.name if certificat.fichier_pdf else None,
            })
        except Exception as e:
            return Response(
                {"error": f"Erreur lors de la génération du PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """Marquer le certificat comme vérifié.

        Un certificat vérifié peut ensuite être signé.
        """
        certificat = self.get_object()

        try:
            certificat.valider(user=request.user)
            return Response({
                "message": "Certificat validé",
                "statut": certificat.statut,
            })
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def signer(self, request, pk=None):
        """Signer le certificat.

        Paramètres requis:
        - lieu: Lieu de signature
        - nom_signataire: Nom de la personne qui signe

        Paramètres optionnels:
        - telephone: Numéro de téléphone pour questions
        """
        certificat = self.get_object()

        lieu = request.data.get("lieu")
        nom_signataire = request.data.get("nom_signataire")
        telephone = request.data.get("telephone", "")

        if not lieu:
            return Response(
                {"error": "Le lieu de signature est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not nom_signataire:
            return Response(
                {"error": "Le nom du signataire est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            certificat.signer(
                lieu=lieu,
                nom_signataire=nom_signataire,
                telephone=telephone,
                user=request.user
            )
            return Response({
                "message": "Certificat signé",
                "statut": certificat.statut,
                "date_signature": certificat.date_signature.isoformat() if certificat.date_signature else None,
                "lieu_signature": certificat.lieu_signature,
                "nom_signataire": certificat.nom_signataire,
            })
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["post"])
    def generer_masse(self, request):
        """Générer des certificats de salaire pour plusieurs employés.

        Paramètres:
        - annee: Année fiscale (requis)
        - employes: Liste d'IDs d'employés (optionnel, sinon tous les employés accessibles)
        - auto_calculer: Si True, calcule automatiquement (défaut: True)
        """
        annee = request.data.get("annee")
        employes_ids = request.data.get("employes", [])
        auto_calculer = request.data.get("auto_calculer", True)

        if not annee:
            return Response(
                {"error": "L'année est requise"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer les employés accessibles
        from .models import Employe
        user = request.user

        if user.is_superuser or (user.is_staff_user() and user.is_manager()):
            queryset = Employe.objects.filter(statut='ACTIF')
        else:
            accessible_mandats = user.get_accessible_mandats()
            queryset = Employe.objects.filter(mandat__in=accessible_mandats, statut='ACTIF')

        if employes_ids:
            queryset = queryset.filter(id__in=employes_ids)

        resultats = {
            "crees": [],
            "existants": [],
            "erreurs": [],
        }

        for employe in queryset:
            # Vérifier si un certificat existe déjà
            if CertificatSalaire.objects.filter(employe=employe, annee=annee).exists():
                resultats["existants"].append({
                    "employe_id": employe.id,
                    "employe_nom": str(employe),
                })
                continue

            try:
                from datetime import date
                certificat = CertificatSalaire.objects.create(
                    employe=employe,
                    annee=annee,
                    date_debut=date(annee, 1, 1),
                    date_fin=date(annee, 12, 31),
                    genere_par=request.user,
                )

                if auto_calculer:
                    try:
                        certificat.calculer_depuis_fiches(save=True)
                    except ValueError:
                        pass  # Pas de fiches, le certificat reste en brouillon

                resultats["crees"].append({
                    "certificat_id": certificat.id,
                    "employe_id": employe.id,
                    "employe_nom": str(employe),
                    "statut": certificat.statut,
                })
            except Exception as e:
                resultats["erreurs"].append({
                    "employe_id": employe.id,
                    "employe_nom": str(employe),
                    "erreur": str(e),
                })

        return Response({
            "message": f"{len(resultats['crees'])} certificats créés",
            "resultats": resultats,
        })


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
