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
    Devise,
    Mandat,
    ExerciceComptable,
    AuditLog,
    Notification,
    Tache,
    CollaborateurFiduciaire,
    FichierJoint,
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
    FichierJointListSerializer,
    FichierJointDetailSerializer,
    FichierJointUploadSerializer,
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

    # =========================================================================
    # 2FA (TOTP) endpoints
    # =========================================================================

    @action(detail=False, methods=["post"], url_path="2fa/setup")
    def setup_2fa(self, request):
        """
        Étape 1: Génère un secret TOTP + QR code.
        L'utilisateur scanne le QR dans son app authenticator.
        POST /api/v1/core/users/2fa/setup/
        """
        user = request.user
        if user.two_factor_enabled:
            return Response(
                {"error": "2FA déjà activée"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_secret = user.generate_totp_secret()
        user.save(update_fields=["totp_secret"])

        uri = user.get_totp_uri()
        from .services.two_factor_service import generate_qr_code_base64
        qr_base64 = generate_qr_code_base64(uri)

        return Response({
            "secret": raw_secret,
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "otpauth_uri": uri,
        })

    @action(detail=False, methods=["post"], url_path="2fa/enable")
    def enable_2fa(self, request):
        """
        Étape 2: Vérifie le premier code TOTP et active la 2FA.
        Retourne les codes de secours (à sauvegarder par l'utilisateur).
        POST /api/v1/core/users/2fa/enable/ { "code": "123456" }
        """
        user = request.user
        if user.two_factor_enabled:
            return Response(
                {"error": "2FA déjà activée"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.totp_secret:
            return Response(
                {"error": "Veuillez d'abord appeler /2fa/setup/"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = request.data.get("code", "").strip()
        if not code or not user.verify_totp(code):
            return Response(
                {"error": "Code invalide"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        backup_codes = user.generate_backup_codes()
        user.enable_2fa()
        user.save(update_fields=["backup_codes"])

        return Response({
            "message": "2FA activée avec succès",
            "backup_codes": backup_codes,
        })

    @action(detail=False, methods=["post"], url_path="2fa/disable")
    def disable_2fa(self, request):
        """
        Désactive la 2FA (nécessite le mot de passe pour confirmer).
        POST /api/v1/core/users/2fa/disable/ { "password": "..." }
        """
        user = request.user
        if not user.two_factor_enabled:
            return Response(
                {"error": "2FA n'est pas activée"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password = request.data.get("password", "")
        if not user.check_password(password):
            return Response(
                {"error": "Mot de passe incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.disable_2fa()
        return Response({"message": "2FA désactivée avec succès"})

    @action(detail=False, methods=["get"], url_path="2fa/status")
    def status_2fa(self, request):
        """
        Retourne le statut 2FA de l'utilisateur.
        GET /api/v1/core/users/2fa/status/
        """
        user = request.user
        return Response({
            "two_factor_enabled": user.two_factor_enabled,
            "backup_codes_remaining": len(user.backup_codes) if user.backup_codes else 0,
        })

    # =========================================================================
    # Push Notifications — device registration
    # =========================================================================

    @action(detail=False, methods=["post"], url_path="devices/register")
    def register_device(self, request):
        """
        Enregistre un device pour recevoir des push notifications.
        POST /api/v1/core/users/devices/register/
        {
            "token": "fcm-or-webpush-token",
            "device_type": "android" | "ios" | "web",
            "device_id": "optional-unique-id",
            "name": "optional-device-name"
        }
        """
        token = request.data.get("token", "").strip()
        device_type = request.data.get("device_type", "").strip().lower()

        if not token:
            return Response(
                {"error": "Le token est requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if device_type not in ("android", "ios", "web"):
            return Response(
                {"error": "device_type doit être 'android', 'ios' ou 'web'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .services.push_notification_service import register_device, is_push_enabled
        if not is_push_enabled():
            return Response(
                {"message": "Push notifications non activées sur cette instance", "registered": False},
                status=status.HTTP_200_OK,
            )

        device = register_device(
            user=request.user,
            token=token,
            device_type=device_type,
            device_id=request.data.get("device_id"),
            name=request.data.get("name"),
        )

        return Response({
            "registered": device is not None,
            "device_type": device_type,
        })

    @action(detail=False, methods=["post"], url_path="devices/unregister")
    def unregister_device(self, request):
        """
        Désactive un device pour ne plus recevoir de notifications.
        POST /api/v1/core/users/devices/unregister/
        { "token": "fcm-or-webpush-token" }
        """
        token = request.data.get("token", "").strip()
        if not token:
            return Response(
                {"error": "Le token est requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .services.push_notification_service import unregister_device, is_push_enabled
        if not is_push_enabled():
            return Response({"unregistered": False}, status=status.HTTP_200_OK)

        success = unregister_device(user=request.user, token=token)
        return Response({"unregistered": success})

    @action(detail=False, methods=["get"], url_path="push/config")
    def push_config(self, request):
        """
        Retourne la configuration push notifications pour le client.
        GET /api/v1/core/users/push/config/
        """
        from .services.push_notification_service import is_push_enabled
        from django.conf import settings as django_settings

        if not is_push_enabled():
            return Response({
                "enabled": False,
                "vapid_public_key": None,
            })

        push_settings = getattr(django_settings, 'PUSH_NOTIFICATIONS_SETTINGS', {})
        # Extraire la clé publique VAPID pour Web Push
        vapid_public_key = push_settings.get('WP_PUBLIC_KEY', '')

        return Response({
            "enabled": True,
            "vapid_public_key": vapid_public_key,
        })


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

    @action(detail=False, methods=["get"], url_path="validate-vat")
    def validate_vat(self, request):
        """
        Valider un numero de TVA (europeen via VIES ou suisse via UID Register).
        GET /api/v1/core/clients/validate-vat/?vat_number=FR40303265045
        GET /api/v1/core/clients/validate-vat/?vat_number=CHE-175.923.751
        """
        import re

        vat_number = request.query_params.get("vat_number", "").strip()
        if not vat_number:
            return Response(
                {"error": "Parametre vat_number requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Detecter les numeros suisses (CHE-xxx ou digits purs avec 9 chiffres)
        cleaned = re.sub(r'[\s.\-]', '', vat_number).upper()
        cleaned = re.sub(r'(MWST|TVA|IVA)$', '', cleaned)
        is_swiss = cleaned.startswith('CHE')

        if is_swiss:
            from .services import SwissVatValidationService

            result = SwissVatValidationService.validate(vat_number)
            data = {
                "valid": result.valid,
                "country_code": "CH",
                "vat_number": result.vat_number,
                "name": result.name,
                "address": result.address,
                "request_date": None,
            }
            if result.error:
                data["error"] = result.error
        else:
            from .services import ViesValidationService

            result = ViesValidationService.validate_full_number(vat_number)
            data = {
                "valid": result.valid,
                "country_code": result.country_code,
                "vat_number": result.vat_number,
                "name": result.name,
                "address": result.address,
                "request_date": str(result.request_date) if result.request_date else None,
            }
            if result.error:
                data["error"] = result.error

        return Response(data)

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
    filterset_fields = ["statut", "priorite", "mandat"]
    search_fields = ["titre", "description"]
    ordering_fields = ["date_echeance", "priorite", "created_at"]
    ordering = ["date_echeance", "-priorite"]

    def get_queryset(self):
        user = self.request.user
        queryset = Tache.objects.prefetch_related('assignes').select_related(
            'cree_par', 'mandat__client', 'prestation'
        )

        # Par défaut, montrer les tâches assignées à l'utilisateur
        if not user.is_staff:
            queryset = queryset.filter(
                Q(assignes=user) | Q(cree_par=user)
            ).distinct()

        # Filtre par assigné
        assigne_id = self.request.query_params.get("assignes", None)
        if assigne_id:
            queryset = queryset.filter(assignes__pk=assigne_id).distinct()

        return queryset

    def perform_create(self, serializer):
        tache = serializer.save(cree_par=self.request.user)
        from core.services.tache_service import envoyer_notification_assignation
        envoyer_notification_assignation(tache, self.request.user)

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
            assignes=request.user, statut__in=["A_FAIRE", "EN_COURS"]
        ).distinct()
        serializer = self.get_serializer(taches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def calendar_events(self, request):
        """Retourne les tâches au format calendrier pour le mobile"""
        start = request.query_params.get("start")
        end = request.query_params.get("end")

        taches = self.get_queryset().exclude(statut="ANNULEE")

        if start:
            taches = taches.filter(
                Q(date_echeance__gte=start) | Q(date_echeance__isnull=True, date_debut__gte=start)
            )
        if end:
            taches = taches.filter(
                Q(date_echeance__lte=end) | Q(date_echeance__isnull=True, date_debut__lte=end)
            )

        taches = taches.distinct()

        events = []
        for t in taches:
            event_date = t.date_echeance or (t.date_debut.date() if t.date_debut else None)
            if not event_date:
                continue
            events.append({
                "id": str(t.pk),
                "title": t.titre,
                "start": event_date.isoformat(),
                "priorite": t.priorite,
                "statut": t.statut,
                "description": (t.description[:100] if t.description else ""),
            })

        return Response(events)


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


class DeviseViewSet(viewsets.ViewSet):
    """ViewSet pour les devises et taux de change SNB."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Liste des devises actives avec leurs taux."""
        devises = Devise.objects.filter(actif=True).order_by('code')
        data = [
            {
                'code': d.code,
                'nom': d.nom,
                'symbole': d.symbole,
                'taux_change': str(d.taux_change),
                'date_taux': str(d.date_taux) if d.date_taux else None,
                'est_devise_base': d.est_devise_base,
            }
            for d in devises
        ]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='taux-snb')
    def taux_snb(self, request):
        """Preview des taux SNB sans sauvegarder."""
        from .services import SNBExchangeRateService

        date_str = request.query_params.get('date')
        target_date = None
        if date_str:
            try:
                from datetime import datetime
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Format de date invalide (YYYY-MM-DD)'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        result = SNBExchangeRateService.fetch_rates(target_date=target_date)
        if result.error:
            return Response({'error': result.error}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            'source': result.source,
            'date': str(result.fetch_date),
            'rates': [
                {
                    'currency': r.currency,
                    'rate': str(r.rate),
                    'date': str(r.date),
                    'base_currency': r.base_currency,
                }
                for r in result.rates
            ],
        })

    @action(detail=False, methods=['post'], url_path='update-rates')
    def update_rates(self, request):
        """Met a jour les taux de change en BD depuis la SNB."""
        from .services import SNBExchangeRateService

        date_str = request.data.get('date')
        target_date = None
        if date_str:
            try:
                from datetime import datetime
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Format de date invalide (YYYY-MM-DD)'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        result = SNBExchangeRateService.update_devise_rates(target_date=target_date)
        if result.get('errors'):
            return Response(result, status=status.HTTP_207_MULTI_STATUS)
        return Response(result)


class AdresseViewSet(viewsets.GenericViewSet):
    """ViewSet pour l'autocomplete d'adresses suisses via Swiss Post API."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="autocomplete")
    def autocomplete(self, request):
        """
        GET /api/v1/core/adresses/autocomplete/?q=Bahnhofstr
        Recherche d'adresses suisses via Swiss Post API.
        """
        from .services import SwissPostAddressService

        q = request.query_params.get("q", "").strip()
        if len(q) < 3:
            return Response({"results": []})

        results = SwissPostAddressService.autocomplete(q)
        return Response({"results": [r.to_dict() for r in results]})


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


class FichierJointViewSet(viewsets.ModelViewSet):
    """ViewSet pour les fichiers joints (pièces jointes génériques).

    Supporte l'upload multipart et base64 (mobile).
    Filtrable par content_type et object_id pour récupérer les pièces jointes
    d'un objet spécifique.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["content_type", "object_id"]
    ordering = ["ordre", "created_at"]

    def get_queryset(self):
        from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
        return FichierJoint.objects.select_related("content_type")

    def get_parsers(self):
        from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
        return [MultiPartParser(), FormParser(), JSONParser()]

    def get_serializer_class(self):
        if self.action == "list":
            return FichierJointListSerializer
        if self.action == "create":
            return FichierJointUploadSerializer
        return FichierJointDetailSerializer

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Télécharger un fichier joint"""
        fichier_joint = self.get_object()
        if not fichier_joint.fichier:
            return Response(
                {"error": "Aucun fichier disponible"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            "url": fichier_joint.fichier.url,
            "nom_fichier": fichier_joint.nom_original,
            "mime_type": fichier_joint.mime_type,
            "taille": fichier_joint.taille,
        })

    @action(detail=False, methods=["get"])
    def par_objet(self, request):
        """Récupérer les fichiers joints d'un objet par content_type et object_id.

        ?content_type_model=timetracking&object_id=uuid
        """
        from django.contrib.contenttypes.models import ContentType

        model_name = request.query_params.get("content_type_model")
        object_id = request.query_params.get("object_id")

        if not model_name or not object_id:
            return Response(
                {"error": "content_type_model et object_id sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ct = ContentType.objects.get(model=model_name.lower())
        except ContentType.DoesNotExist:
            return Response(
                {"error": f"Type de contenu '{model_name}' introuvable"},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = self.get_queryset().filter(content_type=ct, object_id=object_id)
        serializer = FichierJointListSerializer(qs, many=True)
        return Response(serializer.data)
