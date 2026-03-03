# mailing/viewset.py
"""
ViewSets pour l'API REST du module mailing.
Django 6 - Utilisation des pratiques modernes avec DRF.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone

from .models import ConfigurationEmail, TemplateEmail, EmailEnvoye, EmailRecu
from .serializers import (
    # Configuration
    ConfigurationEmailListSerializer,
    ConfigurationEmailDetailSerializer,
    ConfigurationEmailCreateSerializer,
    # Template
    TemplateEmailListSerializer,
    TemplateEmailDetailSerializer,
    TemplateEmailCreateSerializer,
    # Email envoyé
    EmailEnvoyeListSerializer,
    EmailEnvoyeDetailSerializer,
    EmailEnvoyeCreateSerializer,
    # Email reçu
    EmailRecuListSerializer,
    EmailRecuDetailSerializer,
    EmailRecuUpdateSerializer,
)


class ConfigurationEmailViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les configurations email.

    Endpoints:
    - GET    /configurations/                Liste des configurations
    - POST   /configurations/                Créer une configuration
    - GET    /configurations/{id}/           Détail configuration
    - PUT    /configurations/{id}/           Modifier configuration
    - PATCH  /configurations/{id}/           Modification partielle
    - DELETE /configurations/{id}/           Supprimer configuration
    - POST   /configurations/{id}/test/      Tester la connexion
    - GET    /configurations/by_usage/       Configurations par usage
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['type_config', 'usage', 'actif', 'est_defaut']
    search_fields = ['nom', 'email_address', 'smtp_host', 'imap_host']
    ordering_fields = ['nom', 'created_at', 'usage']
    ordering = ['-est_defaut', 'nom']

    def get_queryset(self):
        return ConfigurationEmail.objects.select_related('created_by').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return ConfigurationEmailListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ConfigurationEmailCreateSerializer
        return ConfigurationEmailDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Tester la connexion SMTP/IMAP d'une configuration"""
        config = self.get_object()
        results = {'smtp': None, 'imap': None}

        # Test SMTP
        if config.smtp_host:
            try:
                from .services import EmailService
                service = EmailService(config)
                service.test_smtp_connection()
                results['smtp'] = {'success': True, 'message': 'Connexion SMTP réussie'}
            except Exception as e:
                results['smtp'] = {'success': False, 'message': str(e)}

        # Test IMAP
        if config.imap_host:
            try:
                from .services import EmailService
                service = EmailService(config)
                service.test_imap_connection()
                results['imap'] = {'success': True, 'message': 'Connexion IMAP réussie'}
            except Exception as e:
                results['imap'] = {'success': False, 'message': str(e)}

        return Response(results)

    @action(detail=False, methods=['get'])
    def by_usage(self, request):
        """Récupérer les configurations par usage"""
        usage = request.query_params.get('usage', None)
        queryset = self.get_queryset().filter(actif=True)

        if usage:
            queryset = queryset.filter(usage=usage)

        serializer = ConfigurationEmailListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques des configurations email"""
        configs = ConfigurationEmail.objects.filter(actif=True)
        stats = {
            'total': configs.count(),
            'par_usage': dict(
                configs.values('usage')
                .annotate(count=Count('id'))
                .values_list('usage', 'count')
            ),
            'par_type': dict(
                configs.values('type_config')
                .annotate(count=Count('id'))
                .values_list('type_config', 'count')
            ),
            'avec_smtp': configs.exclude(smtp_host='').count(),
            'avec_imap': configs.exclude(imap_host='').count(),
            'avec_analyse_ai': configs.filter(analyse_ai_activee=True).count(),
        }
        return Response(stats)


class TemplateEmailViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les templates email.

    Endpoints:
    - GET    /templates/                     Liste des templates
    - POST   /templates/                     Créer un template
    - GET    /templates/{id}/                Détail template
    - PUT    /templates/{id}/                Modifier template
    - DELETE /templates/{id}/                Supprimer template
    - POST   /templates/{id}/preview/        Prévisualiser le template
    - GET    /templates/by_type/             Templates par type
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['type_template', 'actif', 'configuration']
    search_fields = ['code', 'nom', 'sujet']
    ordering_fields = ['nom', 'code', 'created_at']
    ordering = ['type_template', 'nom']

    def get_queryset(self):
        return TemplateEmail.objects.select_related(
            'configuration', 'created_by'
        ).all()

    def get_serializer_class(self):
        if self.action == 'list':
            return TemplateEmailListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TemplateEmailCreateSerializer
        return TemplateEmailDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Prévisualiser un template avec des données de test"""
        template = self.get_object()
        context = request.data.get('context', {})

        try:
            sujet, corps_html, corps_texte = template.render(context)
            return Response({
                'sujet': sujet,
                'corps_html': corps_html,
                'corps_texte': corps_texte,
            })
        except Exception as e:
            return Response(
                {'error': f'Erreur de rendu: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Récupérer les templates par type"""
        type_template = request.query_params.get('type', None)
        queryset = self.get_queryset().filter(actif=True)

        if type_template:
            queryset = queryset.filter(type_template=type_template)

        serializer = TemplateEmailListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_code(self, request):
        """Récupérer un template par son code"""
        code = request.query_params.get('code', None)
        if not code:
            return Response(
                {'error': 'Le paramètre code est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            template = self.get_queryset().get(code=code)
            serializer = TemplateEmailDetailSerializer(template)
            return Response(serializer.data)
        except TemplateEmail.DoesNotExist:
            return Response(
                {'error': 'Template non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )


class EmailEnvoyeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les emails envoyés.

    Endpoints:
    - GET    /envoyes/                       Liste des emails envoyés
    - POST   /envoyes/                       Créer un email à envoyer
    - GET    /envoyes/{id}/                  Détail email
    - DELETE /envoyes/{id}/                  Supprimer email
    - POST   /envoyes/{id}/resend/           Renvoyer un email
    - GET    /envoyes/statistics/            Statistiques d'envoi
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['statut', 'configuration', 'template', 'utilisateur', 'mandat']
    search_fields = ['destinataire', 'sujet']
    ordering_fields = ['created_at', 'date_envoi']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = EmailEnvoye.objects.select_related(
            'configuration', 'template', 'utilisateur', 'mandat'
        )

        # Les non-admin ne voient que leurs propres emails
        if not self.request.user.is_staff:
            queryset = queryset.filter(utilisateur=self.request.user)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return EmailEnvoyeListSerializer
        elif self.action == 'create':
            return EmailEnvoyeCreateSerializer
        return EmailEnvoyeDetailSerializer

    # Pas de update/partial_update pour les emails envoyés
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def perform_create(self, serializer):
        email = serializer.save()
        # Lancer l'envoi asynchrone
        from .tasks import envoyer_email_task
        envoyer_email_task.delay(str(email.id))

    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Renvoyer un email qui a échoué"""
        email = self.get_object()

        if email.statut not in [EmailEnvoye.Statut.ECHEC, EmailEnvoye.Statut.BOUNCE]:
            return Response(
                {'error': 'Seuls les emails en échec peuvent être renvoyés'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Réinitialiser le statut
        email.statut = EmailEnvoye.Statut.EN_ATTENTE
        email.erreur = ''
        email.save()

        # Relancer l'envoi
        from .tasks import envoyer_email_task
        envoyer_email_task.delay(str(email.id))

        serializer = self.get_serializer(email)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques des emails envoyés"""
        queryset = self.get_queryset()

        # Filtre par période
        days = int(request.query_params.get('days', 30))
        from_date = timezone.now() - timezone.timedelta(days=days)
        queryset = queryset.filter(created_at__gte=from_date)

        stats = {
            'periode_jours': days,
            'total': queryset.count(),
            'par_statut': dict(
                queryset.values('statut')
                .annotate(count=Count('id'))
                .values_list('statut', 'count')
            ),
            'taux_succes': 0,
        }

        if stats['total'] > 0:
            envoyes = queryset.filter(statut=EmailEnvoye.Statut.ENVOYE).count()
            stats['taux_succes'] = round((envoyes / stats['total']) * 100, 2)

        return Response(stats)


class EmailRecuViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les emails reçus.

    Endpoints:
    - GET    /recus/                         Liste des emails reçus
    - GET    /recus/{id}/                    Détail email
    - PATCH  /recus/{id}/                    Modifier email (statut, importance)
    - DELETE /recus/{id}/                    Supprimer email
    - POST   /recus/{id}/mark_read/          Marquer comme lu
    - POST   /recus/{id}/mark_unread/        Marquer comme non lu
    - POST   /recus/{id}/toggle_important/   Basculer importance
    - POST   /recus/{id}/analyze/            Lancer l'analyse IA
    - POST   /recus/fetch/                   Récupérer les nouveaux emails
    - GET    /recus/statistics/              Statistiques des emails reçus
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['statut', 'configuration', 'est_important', 'analyse_effectuee', 'mandat_detecte', 'client_detecte']
    search_fields = ['expediteur', 'expediteur_nom', 'sujet']
    ordering_fields = ['date_reception', 'date_lecture']
    ordering = ['-date_reception']

    def get_queryset(self):
        return EmailRecu.objects.select_related(
            'configuration', 'mandat_detecte', 'client_detecte'
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return EmailRecuListSerializer
        elif self.action in ['update', 'partial_update']:
            return EmailRecuUpdateSerializer
        return EmailRecuDetailSerializer

    # Pas de create pour les emails reçus (ils viennent du fetch)
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def retrieve(self, request, *args, **kwargs):
        """Marquer automatiquement comme lu lors de la consultation"""
        instance = self.get_object()
        if instance.date_lecture is None:
            instance.date_lecture = timezone.now()
            if instance.statut == EmailRecu.Statut.NON_LU:
                instance.statut = EmailRecu.Statut.LU
            instance.save(update_fields=['date_lecture', 'statut', 'updated_at'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Marquer un email comme lu"""
        email = self.get_object()
        email.date_lecture = timezone.now()
        if email.statut == EmailRecu.Statut.NON_LU:
            email.statut = EmailRecu.Statut.LU
        email.save()

        serializer = self.get_serializer(email)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Marquer un email comme non lu"""
        email = self.get_object()
        email.date_lecture = None
        email.statut = EmailRecu.Statut.NON_LU
        email.save()

        serializer = self.get_serializer(email)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle_important(self, request, pk=None):
        """Basculer l'importance d'un email"""
        email = self.get_object()
        email.est_important = not email.est_important
        email.save()

        serializer = self.get_serializer(email)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """Lancer l'analyse IA d'un email"""
        email = self.get_object()

        if email.analyse_effectuee:
            return Response(
                {'warning': 'Cet email a déjà été analysé', 'resultat': email.analyse_resultat}
            )

        # Lancer l'analyse asynchrone
        from .tasks import analyser_email_task
        analyser_email_task.delay(str(email.id))

        return Response({'message': 'Analyse en cours...'})

    @action(detail=False, methods=['post'])
    def fetch(self, request):
        """Récupérer les nouveaux emails depuis les serveurs IMAP"""
        config_id = request.data.get('configuration_id', None)

        from .tasks import fetch_emails_task

        if config_id:
            fetch_emails_task.delay(config_id)
        else:
            fetch_emails_task.delay()

        return Response({'message': 'Récupération des emails lancée'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Marquer tous les emails non lus comme lus"""
        config_id = request.data.get('configuration_id', None)
        queryset = self.get_queryset().filter(date_lecture__isnull=True)

        if config_id:
            queryset = queryset.filter(configuration_id=config_id)

        count = queryset.update(
            date_lecture=timezone.now(),
            statut=EmailRecu.Statut.LU,
            updated_at=timezone.now()
        )

        return Response({'message': f'{count} email(s) marqué(s) comme lu(s)'})

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques des emails reçus"""
        queryset = self.get_queryset()

        # Filtre par période
        days = int(request.query_params.get('days', 30))
        from_date = timezone.now() - timezone.timedelta(days=days)
        queryset = queryset.filter(date_reception__gte=from_date)

        stats = {
            'periode_jours': days,
            'total': queryset.count(),
            'non_lus': queryset.filter(date_lecture__isnull=True).count(),
            'importants': queryset.filter(est_important=True).count(),
            'analyses': queryset.filter(analyse_effectuee=True).count(),
            'par_statut': dict(
                queryset.values('statut')
                .annotate(count=Count('id'))
                .values_list('statut', 'count')
            ),
            'avec_mandat_detecte': queryset.filter(mandat_detecte__isnull=False).count(),
            'avec_client_detecte': queryset.filter(client_detecte__isnull=False).count(),
        }

        return Response(stats)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Compter les emails non lus"""
        config_id = request.query_params.get('configuration_id', None)
        queryset = self.get_queryset().filter(date_lecture__isnull=True)

        if config_id:
            queryset = queryset.filter(configuration_id=config_id)

        return Response({'unread_count': queryset.count()})
