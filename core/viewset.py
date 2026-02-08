# core/viewset.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from .models import (
    User,
    Adresse,
    Client,
    Contact,
    Mandat,
    ExerciceComptable,
    AuditLog,
    Notification,
    Tache,
    CollaborateurFiduciaire,
)
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    AdresseSerializer,
    ClientListSerializer,
    ClientDetailSerializer,
    ContactSerializer,
    MandatListSerializer,
    MandatDetailSerializer,
    ExerciceComptableSerializer,
    AuditLogSerializer,
    NotificationSerializer,
    TacheSerializer,
    CollaborateurFiduciaireListSerializer,
    CollaborateurFiduciaireDetailSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les utilisateurs
    """

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "first_name", "last_name", "email"]
    ordering_fields = ["username", "date_joined", "last_name"]
    ordering = ["-date_joined"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ["create", "destroy"]:
            return [IsAdminUser()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Récupérer le profil de l'utilisateur connecté"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def change_password(self, request, pk=None):
        """Changer le mot de passe d'un utilisateur"""
        user = self.get_object()

        if user != request.user and not request.user.is_staff:
            return Response({"error": "Non autorisé"}, status=status.HTTP_403_FORBIDDEN)

        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not user.check_password(old_password):
            return Response(
                {"error": "Ancien mot de passe incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response({"message": "Mot de passe changé avec succès"})


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les clients
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["statut", "forme_juridique", "responsable"]
    search_fields = ["raison_sociale", "nom_commercial", "ide_number", "email"]
    ordering_fields = ["raison_sociale", "created_at"]
    ordering = ["raison_sociale"]

    def get_queryset(self):
        queryset = Client.objects.select_related(
            "adresse_siege",
            "adresse_correspondance",
            "responsable",
            "contact_principal",
        ).prefetch_related("contacts", "mandats")

        # Filtre par statut
        statut = self.request.query_params.get("statut", None)
        if statut:
            queryset = queryset.filter(statut=statut)

        # Filtre par canton
        canton = self.request.query_params.get("canton", None)
        if canton:
            queryset = queryset.filter(adresse_siege__canton=canton)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ClientListSerializer
        return ClientDetailSerializer

    @action(detail=True, methods=["get"])
    def mandats(self, request, pk=None):
        """Récupérer tous les mandats d'un client"""
        client = self.get_object()
        mandats = client.mandats.all()
        serializer = MandatListSerializer(mandats, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def contacts(self, request, pk=None):
        """Récupérer tous les contacts d'un client"""
        client = self.get_object()
        contacts = client.contacts.all()
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Statistiques sur les clients"""
        stats = {
            "total": Client.objects.count(),
            "actifs": Client.objects.filter(statut="ACTIF").count(),
            "prospects": Client.objects.filter(statut="PROSPECT").count(),
            "par_forme_juridique": dict(
                Client.objects.values("forme_juridique")
                .annotate(count=Count("id"))
                .values_list("forme_juridique", "count")
            ),
        }
        return Response(stats)

    @action(detail=False, methods=["get"], permission_classes=[])
    def search_swiss(self, request):
        """
        Search Swiss companies via LINDAS API (Zefix registry).
        Used for autocomplete when creating new clients.
        Public endpoint (no auth required) - Zefix data is public.

        Query params:
            q: Search term (min 3 characters)
            limit: Max results (default 10, max 50)

        Returns list of companies with IDE, name, legal form, address, etc.
        """
        from .services import SwissCompaniesService

        search_term = request.query_params.get("q", "").strip()
        if len(search_term) < 3:
            return Response(
                {"error": "Le terme de recherche doit contenir au moins 3 caractères"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            limit = min(int(request.query_params.get("limit", 10)), 50)
        except ValueError:
            limit = 10

        companies = SwissCompaniesService.search(search_term, limit=limit)
        results = [company.to_dict() for company in companies]

        return Response({
            "count": len(results),
            "results": results,
        })

    @action(detail=False, methods=["get"], url_path=r"swiss/(?P<uid>[\w\-\.]+)", permission_classes=[])
    def get_swiss_company(self, request, uid=None):
        """
        Get a specific Swiss company by UID.
        Public endpoint (no auth required) - Zefix data is public.

        Path param:
            uid: Company UID (9 digits or CHE-XXX.XXX.XXX format)

        Returns company details if found.
        """
        from .services import SwissCompaniesService

        if not uid:
            return Response(
                {"error": "UID requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company = SwissCompaniesService.get_by_uid(uid)
        if not company:
            return Response(
                {"error": "Entreprise non trouvée"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(company.to_dict())


class ContactViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les contacts
    """

    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["client", "fonction", "principal"]
    search_fields = ["nom", "prenom", "email", "telephone"]
    ordering_fields = ["nom", "prenom"]
    ordering = ["nom", "prenom"]


class MandatViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les mandats
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["client", "type_mandat", "statut", "responsable"]
    search_fields = ["numero", "client__raison_sociale"]
    ordering_fields = ["date_debut", "numero"]
    ordering = ["-date_debut"]

    def get_queryset(self):
        queryset = Mandat.objects.select_related(
            "client", "responsable"
        ).prefetch_related("equipe", "exercices")

        # Filtrer par utilisateur si demandé
        user_id = self.request.query_params.get("user", None)
        if user_id:
            queryset = queryset.filter(
                Q(responsable_id=user_id) | Q(equipe__id=user_id)
            ).distinct()

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return MandatListSerializer
        return MandatDetailSerializer

    @action(detail=True, methods=["get"])
    def exercices(self, request, pk=None):
        """Récupérer tous les exercices d'un mandat"""
        mandat = self.get_object()
        exercices = mandat.exercices.all()
        serializer = ExerciceComptableSerializer(exercices, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def change_status(self, request, pk=None):
        """Changer le statut d'un mandat"""
        mandat = self.get_object()
        new_status = request.data.get("statut")

        if new_status not in dict(Mandat.STATUT_CHOICES):
            return Response(
                {"error": "Statut invalide"}, status=status.HTTP_400_BAD_REQUEST
            )

        mandat.statut = new_status
        mandat.save()

        serializer = self.get_serializer(mandat)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def actifs(self, request):
        """Récupérer uniquement les mandats actifs"""
        mandats = self.get_queryset().filter(statut="ACTIF")
        serializer = self.get_serializer(mandats, many=True)
        return Response(serializer.data)


class ExerciceComptableViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les exercices comptables
    """

    queryset = ExerciceComptable.objects.all()
    serializer_class = ExerciceComptableSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["mandat", "annee", "statut"]
    ordering_fields = ["annee", "date_debut"]
    ordering = ["-annee"]

    @action(detail=True, methods=["post"])
    def cloturer(self, request, pk=None):
        """Clôturer un exercice"""
        exercice = self.get_object()

        if exercice.statut == "CLOTURE_DEFINITIVE":
            return Response(
                {"error": "Exercice déjà clôturé"}, status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone

        exercice.statut = "CLOTURE_DEFINITIVE"
        exercice.date_cloture = timezone.now()
        exercice.cloture_par = request.user
        exercice.save()

        serializer = self.get_serializer(exercice)
        return Response(serializer.data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour consulter les logs d'audit (lecture seule)
    """

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["utilisateur", "action", "table_name", "mandat"]
    search_fields = ["object_repr", "table_name"]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les notifications
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["type_notification", "lue", "archivee"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # Chaque utilisateur ne voit que ses propres notifications
        return Notification.objects.filter(destinataire=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Marquer une notification comme lue"""
        notification = self.get_object()

        from django.utils import timezone

        notification.lue = True
        notification.date_lecture = timezone.now()
        notification.save()

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Marquer toutes les notifications comme lues"""
        from django.utils import timezone

        Notification.objects.filter(destinataire=request.user, lue=False).update(
            lue=True, date_lecture=timezone.now()
        )

        return Response(
            {"message": "Toutes les notifications ont été marquées comme lues"}
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Compter les notifications non lues"""
        count = Notification.objects.filter(
            destinataire=request.user, lue=False
        ).count()
        return Response({"unread_count": count})


class TacheViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les tâches
    """

    serializer_class = TacheSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["assigne_a", "statut", "priorite", "mandat"]
    search_fields = ["titre", "description"]
    ordering_fields = ["date_echeance", "priorite", "created_at"]
    ordering = ["date_echeance", "-priorite"]

    def get_queryset(self):
        user = self.request.user
        queryset = Tache.objects.all()

        # Par défaut, montrer les tâches assignées à l'utilisateur
        if not user.is_staff:
            queryset = queryset.filter(Q(assigne_a=user) | Q(cree_par=user))

        # Filtres personnalisés
        mes_taches = self.request.query_params.get("mes_taches", None)
        if mes_taches == "true":
            queryset = queryset.filter(assigne_a=user)

        return queryset

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)

    @action(detail=True, methods=["post"])
    def change_status(self, request, pk=None):
        """Changer le statut d'une tâche"""
        tache = self.get_object()
        new_status = request.data.get("statut")

        if new_status not in dict(Tache.STATUT_CHOICES):
            return Response(
                {"error": "Statut invalide"}, status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone

        tache.statut = new_status

        if new_status == "EN_COURS" and not tache.date_debut:
            tache.date_debut = timezone.now()
        elif new_status == "TERMINEE":
            tache.date_fin = timezone.now()

        tache.save()

        serializer = self.get_serializer(tache)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def mes_taches(self, request):
        """Récupérer les tâches de l'utilisateur connecté"""
        taches = self.get_queryset().filter(
            assigne_a=request.user, statut__in=["A_FAIRE", "EN_COURS"]
        )
        serializer = self.get_serializer(taches, many=True)
        return Response(serializer.data)


class IsManagerOrAbove:
    """Permission: seuls les managers ou supérieurs peuvent accéder"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.is_manager()
        )


class CollaborateurFiduciaireViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des affectations prestataires fiduciaires.
    Réservé aux managers et administrateurs.
    """

    permission_classes = [IsAuthenticated, IsManagerOrAbove]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["utilisateur", "mandat", "is_active"]
    search_fields = [
        "utilisateur__username",
        "utilisateur__first_name",
        "utilisateur__last_name",
        "mandat__numero",
        "mandat__client__raison_sociale",
        "role_sur_mandat",
    ]
    ordering_fields = ["date_debut", "date_fin", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return CollaborateurFiduciaire.objects.select_related(
            "utilisateur", "mandat", "mandat__client"
        ).filter(is_active=True)

    def get_serializer_class(self):
        if self.action == "list":
            return CollaborateurFiduciaireListSerializer
        return CollaborateurFiduciaireDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def par_prestataire(self, request):
        """Liste les affectations groupées par prestataire"""
        utilisateur_id = request.query_params.get("utilisateur_id")
        if not utilisateur_id:
            return Response(
                {"error": "utilisateur_id requis"}, status=status.HTTP_400_BAD_REQUEST
            )

        affectations = self.get_queryset().filter(utilisateur_id=utilisateur_id)
        serializer = CollaborateurFiduciaireListSerializer(affectations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def par_mandat(self, request):
        """Liste les prestataires affectés à un mandat"""
        mandat_id = request.query_params.get("mandat_id")
        if not mandat_id:
            return Response(
                {"error": "mandat_id requis"}, status=status.HTTP_400_BAD_REQUEST
            )

        affectations = self.get_queryset().filter(mandat_id=mandat_id)
        serializer = CollaborateurFiduciaireListSerializer(affectations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def desactiver(self, request, pk=None):
        """Désactive une affectation (soft delete)"""
        affectation = self.get_object()
        affectation.is_active = False
        affectation.save(update_fields=["is_active", "updated_at"])
        return Response({"message": "Affectation désactivée"})

    @action(detail=False, methods=["get"])
    def prestataires_disponibles(self, request):
        """Liste les prestataires fiduciaires disponibles pour affectation"""
        from .models import TypeCollaborateur

        prestataires = User.objects.filter(
            type_utilisateur=User.TypeUtilisateur.STAFF,
            type_collaborateur=TypeCollaborateur.PRESTATAIRE,
            is_active=True,
        )
        serializer = UserSerializer(prestataires, many=True)
        return Response(serializer.data)


class GraphViewSet(viewsets.ViewSet):
    """
    ViewSet pour l'API du graphe relationnel.
    Utilisé par l'application mobile React Native.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /api/v1/core/graph/
        Retourne le graphe complet (nodes + edges).
        """
        from .views.graph_views import GraphDataMixin

        mixin = GraphDataMixin()
        graph_data = mixin.get_graph_data()
        return Response(graph_data)

    def retrieve(self, request, pk=None):
        """
        GET /api/v1/core/graph/{type}:{pk}/
        Retourne un sous-graphe centré sur une entité.
        """
        from .views.graph_views import GraphDataMixin

        # pk format: "client:uuid" ou "mandat:uuid"
        if ':' in str(pk):
            entity_type, entity_pk = pk.split(':', 1)
        else:
            entity_type = request.query_params.get('type')
            entity_pk = pk

        mixin = GraphDataMixin()
        graph_data = mixin.get_graph_data(center_type=entity_type, center_pk=entity_pk)
        return Response(graph_data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        GET /api/v1/core/graph/stats/
        Retourne les statistiques du graphe par type d'entité.
        """
        from django.apps import apps
        from .views.graph_views import GRAPH_CONFIG, get_list_url

        stats = {}
        for model_label, config in GRAPH_CONFIG['models'].items():
            try:
                app_label, model_name = model_label.split('.')
                model = apps.get_model(app_label, model_name)
                stats[model_label] = {
                    'count': model.objects.count(),
                    'color': config['color'],
                    'label': model._meta.verbose_name_plural,
                    'list_url': get_list_url(model),
                }
            except (LookupError, ValueError):
                continue

        return Response({'stats': stats})
