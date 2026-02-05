# apps/modelforms/viewset.py
"""
ViewSets pour l'API Model-Driven Forms.

Pattern suivi: core/viewset.py
- ViewSets avec permissions appropriées
- Actions personnalisées (@action)
- Filtres et recherche
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from core.permissions import IsManagerOrAbove, IsComptableOrAbove
from .models import FormConfiguration, ModelFieldMapping, FormSubmission, FormTemplate
from .serializers import (
    FormConfigurationListSerializer,
    FormConfigurationDetailSerializer,
    FormConfigurationWriteSerializer,
    ModelFieldMappingSerializer,
    FormSubmissionListSerializer,
    FormSubmissionDetailSerializer,
    FormSubmissionCreateSerializer,
    FormTemplateListSerializer,
    FormTemplateDetailSerializer,
    ModelInfoSerializer,
    ModelSchemaSerializer,
)
from .services.introspector import ModelIntrospector
from .services.submission_handler import SubmissionHandler


class FormConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les configurations de formulaires.

    Permissions:
    - Lecture: IsComptableOrAbove
    - Création/Modification: IsManagerOrAbove
    """

    queryset = FormConfiguration.objects.all()
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['status', 'category', 'target_model']
    search_fields = ['code', 'name', 'description', 'target_model']
    ordering_fields = ['name', 'created_at', 'category']
    ordering = ['category', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'duplicate']:
            return [IsManagerOrAbove()]
        return [IsComptableOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return FormConfigurationListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return FormConfigurationWriteSerializer
        return FormConfigurationDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.prefetch_related('field_mappings')

        # Filtrer par statut actif par défaut pour les non-managers
        if not self.request.user.is_manager():
            queryset = queryset.filter(status=FormConfiguration.Status.ACTIVE)

        return queryset

    @action(detail=True, methods=['get'])
    def schema(self, request, pk=None):
        """
        Retourne le schéma complet du formulaire pour le rendu frontend.

        Combine:
        - Configuration du formulaire
        - Schéma du modèle cible (introspection)
        - Mappings de champs personnalisés
        """
        config = self.get_object()

        # Introspection du modèle
        try:
            introspector = ModelIntrospector(config.target_model)
            model_schema = introspector.get_schema()
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer les mappings personnalisés
        field_mappings = {
            m.field_name: ModelFieldMappingSerializer(m).data
            for m in config.field_mappings.all()
        }

        # Fusionner les informations
        for field in model_schema['fields']:
            field_name = field['name']
            if field_name in field_mappings:
                mapping = field_mappings[field_name]
                # Appliquer les personnalisations
                if mapping.get('widget_type'):
                    field['widget_type'] = mapping['widget_type']
                if mapping.get('label'):
                    field['label'] = mapping['label']
                if mapping.get('help_text'):
                    field['help_text'] = mapping['help_text']
                if mapping.get('placeholder'):
                    field['placeholder'] = mapping['placeholder']
                if mapping.get('required') is not None:
                    field['required'] = mapping['required']
                if mapping.get('conditions'):
                    field['conditions'] = mapping['conditions']
                if mapping.get('options'):
                    field['options'] = mapping['options']
                field['order'] = mapping.get('order', 999)
                field['section'] = mapping.get('section', '')

        # Trier par ordre
        model_schema['fields'].sort(key=lambda f: f.get('order', 999))

        return Response({
            'config': FormConfigurationDetailSerializer(config).data,
            'model_schema': model_schema,
            'form_schema': config.form_schema,
            'default_values': config.default_values,
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplique une configuration existante.
        """
        original = self.get_object()

        # Générer un nouveau code
        base_code = f"{original.code}_COPY"
        counter = 1
        new_code = base_code
        while FormConfiguration.objects.filter(code=new_code).exists():
            new_code = f"{base_code}_{counter}"
            counter += 1

        # Créer la copie
        new_config = FormConfiguration.objects.create(
            code=new_code,
            name=f"{original.name} (copie)",
            description=original.description,
            category=original.category,
            target_model=original.target_model,
            related_models=original.related_models,
            form_schema=original.form_schema,
            default_values=original.default_values,
            validation_rules=original.validation_rules,
            post_actions=original.post_actions,
            status=FormConfiguration.Status.DRAFT,
            require_validation=original.require_validation,
            icon=original.icon,
            created_by=request.user,
        )

        # Copier les mappings
        for mapping in original.field_mappings.all():
            ModelFieldMapping.objects.create(
                form_config=new_config,
                field_name=mapping.field_name,
                model_path=mapping.model_path,
                widget_type=mapping.widget_type,
                label=mapping.label,
                help_text=mapping.help_text,
                placeholder=mapping.placeholder,
                required=mapping.required,
                min_value=mapping.min_value,
                max_value=mapping.max_value,
                min_length=mapping.min_length,
                max_length=mapping.max_length,
                regex_pattern=mapping.regex_pattern,
                conditions=mapping.conditions,
                order=mapping.order,
                section=mapping.section,
                options=mapping.options,
            )

        return Response(
            FormConfigurationDetailSerializer(new_config).data,
            status=status.HTTP_201_CREATED
        )


class FormSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les soumissions de formulaires.

    Permissions:
    - Lecture de ses propres soumissions: IsComptableOrAbove
    - Lecture de toutes les soumissions: IsManagerOrAbove
    - Validation/Rejet: IsManagerOrAbove
    """

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['form_config', 'status', 'submitted_by', 'mandat']
    search_fields = ['form_config__code', 'form_config__name']
    ordering_fields = ['submitted_at', 'status']
    ordering = ['-submitted_at']

    def get_permissions(self):
        if self.action in ['validate', 'reject']:
            return [IsManagerOrAbove()]
        return [IsComptableOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return FormSubmissionListSerializer
        if self.action == 'create':
            return FormSubmissionCreateSerializer
        return FormSubmissionDetailSerializer

    def get_queryset(self):
        queryset = FormSubmission.objects.select_related(
            'form_config',
            'submitted_by',
            'validated_by',
            'mandat',
        )

        # Non-managers ne voient que leurs soumissions
        if not self.request.user.is_manager():
            queryset = queryset.filter(submitted_by=self.request.user)

        return queryset

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """
        Valide une soumission en attente et crée les enregistrements.
        """
        submission = self.get_object()

        if submission.status != FormSubmission.Status.PENDING:
            return Response(
                {'error': 'Seules les soumissions en attente peuvent être validées'},
                status=status.HTTP_400_BAD_REQUEST
            )

        notes = request.data.get('notes', '')

        # Traiter la soumission
        handler = SubmissionHandler(
            form_config=submission.form_config,
            submitted_data=submission.submitted_data,
            user=submission.submitted_by,
            mandat=submission.mandat,
        )

        success, records, errors = handler.process()

        if success:
            submission.status = FormSubmission.Status.COMPLETED
            submission.created_records = records
            submission.validated_by = request.user
            submission.validated_at = timezone.now()
            submission.validation_notes = notes
            submission.save()

            return Response(FormSubmissionDetailSerializer(submission).data)
        else:
            submission.status = FormSubmission.Status.FAILED
            submission.error_message = '; '.join(errors)
            submission.error_details = {'errors': errors}
            submission.save()

            return Response(
                {'error': 'Échec de la validation', 'details': errors},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Rejette une soumission en attente.
        """
        submission = self.get_object()

        if submission.status != FormSubmission.Status.PENDING:
            return Response(
                {'error': 'Seules les soumissions en attente peuvent être rejetées'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Une raison de rejet est requise'},
                status=status.HTTP_400_BAD_REQUEST
            )

        submission.status = FormSubmission.Status.REJECTED
        submission.validated_by = request.user
        submission.validated_at = timezone.now()
        submission.validation_notes = reason
        submission.save()

        return Response(FormSubmissionDetailSerializer(submission).data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Liste les soumissions en attente de validation.
        """
        queryset = self.get_queryset().filter(
            status=FormSubmission.Status.PENDING
        )
        serializer = FormSubmissionListSerializer(queryset, many=True)
        return Response(serializer.data)


class IntrospectionViewSet(viewsets.ViewSet):
    """
    ViewSet pour l'introspection des modèles Django.

    Endpoints lecture seule pour explorer les modèles disponibles.
    """

    permission_classes = [IsManagerOrAbove]

    @action(detail=False, methods=['get'])
    def models(self, request):
        """
        Liste tous les modèles disponibles pour les formulaires.
        """
        models = ModelIntrospector.get_allowed_models()
        serializer = ModelInfoSerializer(models, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='schema/(?P<model_path>[^/.]+\\.[^/.]+)')
    def schema(self, request, model_path=None):
        """
        Retourne le schéma complet d'un modèle.

        Args:
            model_path: Chemin du modèle (ex: core.Client)
        """
        try:
            introspector = ModelIntrospector(model_path)
            schema = introspector.get_schema()
            return Response(schema)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='json-schema/(?P<model_path>[^/.]+\\.[^/.]+)')
    def json_schema(self, request, model_path=None):
        """
        Retourne le JSON Schema d'un modèle.

        Utile pour la validation côté client.
        """
        try:
            introspector = ModelIntrospector(model_path)
            json_schema = introspector.get_json_schema()
            return Response(json_schema)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class FormTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les templates de formulaires.

    Les templates système ne peuvent pas être modifiés ou supprimés.
    """

    queryset = FormTemplate.objects.filter(is_active=True)
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['category', 'is_system']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['name', 'category']
    ordering = ['category', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManagerOrAbove()]
        return [IsComptableOrAbove()]

    def get_serializer_class(self):
        if self.action == 'list':
            return FormTemplateListSerializer
        return FormTemplateDetailSerializer

    def destroy(self, request, *args, **kwargs):
        """Empêche la suppression des templates système."""
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {'error': 'Les templates système ne peuvent pas être supprimés'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Empêche la modification des templates système."""
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {'error': 'Les templates système ne peuvent pas être modifiés'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def instantiate(self, request, pk=None):
        """
        Crée une nouvelle configuration à partir d'un template.
        """
        template = self.get_object()
        config_data = template.template_config.copy()

        # Générer un code unique
        base_code = config_data.get('code', template.code)
        counter = 1
        new_code = base_code
        while FormConfiguration.objects.filter(code=new_code).exists():
            new_code = f"{base_code}_{counter}"
            counter += 1

        # Extraire les field_mappings si présents
        field_mappings_data = config_data.pop('field_mappings', [])

        # Créer la configuration
        config = FormConfiguration.objects.create(
            code=new_code,
            name=config_data.get('name', template.name),
            description=config_data.get('description', template.description),
            category=config_data.get('category', template.category),
            target_model=config_data.get('target_model'),
            related_models=config_data.get('related_models', []),
            form_schema=config_data.get('form_schema', {}),
            default_values=config_data.get('default_values', {}),
            validation_rules=config_data.get('validation_rules', []),
            post_actions=config_data.get('post_actions', []),
            status=FormConfiguration.Status.DRAFT,
            require_validation=config_data.get('require_validation', False),
            icon=template.icon,
            created_by=request.user,
        )

        # Créer les mappings
        for mapping_data in field_mappings_data:
            ModelFieldMapping.objects.create(
                form_config=config,
                **mapping_data
            )

        return Response(
            FormConfigurationDetailSerializer(config).data,
            status=status.HTTP_201_CREATED
        )
