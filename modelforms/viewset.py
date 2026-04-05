# apps/modelforms/viewset.py
"""
ViewSets pour l'API Model-Driven Forms.

Pattern suivi: core/viewset.py
- ViewSets avec permissions appropriées
- Actions personnalisées (@action)
- Filtres et recherche

Supporte les formulaires multi-modèles avec champs provenant de différentes apps Django.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import models as db_models

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
    ModelInfoGroupedSerializer,
    ModelSchemaSerializer,
    MobileFormSchemaSerializer,
)
from .services.introspector import ModelIntrospector
from .services.submission_handler import SubmissionHandler
from .permissions import (
    scope_form_configs_by_user,
    scope_form_submissions_by_user,
    user_can_access_mandat,
    user_can_access_form_config,
)


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
    filterset_fields = ['status', 'category', 'target_model', 'is_multi_model']
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
        queryset = queryset.prefetch_related('field_mappings', 'mandats')

        # Filtrer par statut actif par défaut pour les non-managers
        if not self.request.user.is_manager():
            queryset = queryset.filter(status=FormConfiguration.Status.ACTIVE)

        # SECURITE: filtrer par les mandats accessibles (configs globales visibles)
        queryset = scope_form_configs_by_user(queryset, self.request.user)

        return queryset

    @action(detail=True, methods=['get'], url_path='schema')
    def form_schema(self, request, pk=None):
        """
        Retourne le schéma complet du formulaire pour le rendu frontend.

        Pour les formulaires multi-modèles:
        - Combine les schémas de tous les modèles sources
        - Groupe les champs par modèle

        Pour les formulaires mono-modèle:
        - Retourne le schéma du modèle cible
        - Fusionne avec les mappings personnalisés
        """
        config = self.get_object()

        if config.is_multi_model:
            # Formulaire multi-modèle: combiner les schémas
            model_schemas = {}
            for model_path in (config.source_models or []):
                try:
                    introspector = ModelIntrospector(model_path, validate=False)
                    model_schemas[model_path] = introspector.get_schema()
                except ValueError as e:
                    model_schemas[model_path] = {'error': str(e)}

            # Récupérer les mappings personnalisés groupés par modèle
            field_mappings_by_model = {}
            for mapping in config.field_mappings.all():
                model = mapping.source_model
                if model not in field_mappings_by_model:
                    field_mappings_by_model[model] = {}
                field_mappings_by_model[model][mapping.field_name] = ModelFieldMappingSerializer(mapping).data

            return Response({
                'config': FormConfigurationDetailSerializer(config).data,
                'is_multi_model': True,
                'model_schemas': model_schemas,
                'field_mappings_by_model': field_mappings_by_model,
                'form_schema': config.form_schema,
                'default_values': config.default_values,
            })

        # Formulaire mono-modèle: comportement classique
        if not config.target_model:
            return Response(
                {'error': 'Aucun modèle cible défini pour ce formulaire'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            introspector = ModelIntrospector(config.target_model, validate=False)
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
            'is_multi_model': False,
            'model_schema': model_schema,
            'form_schema': config.form_schema,
            'default_values': config.default_values,
        })

    @action(detail=True, methods=['get'], url_path='mobile-schema')
    def mobile_schema(self, request, pk=None):
        """
        Retourne le schéma pré-mergé pour le rendu mobile.

        Fusionne introspection Django + field_mappings en une liste
        de champs ordonnée et organisée par sections, prête à rendre.
        Ne retourne QUE les champs présents dans field_mappings.
        """
        config = self.get_object()

        if not config.target_model and not config.is_multi_model:
            return Response(
                {'error': 'Aucun modèle cible défini pour ce formulaire'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer les schémas introspectés par modèle source
        introspected = {}
        model_paths = set()
        for mapping in config.field_mappings.all():
            model_paths.add(mapping.source_model or config.target_model)

        for model_path in model_paths:
            try:
                introspector = ModelIntrospector(model_path, validate=False)
                schema = introspector.get_schema()
                introspected[model_path] = {
                    f['name']: f for f in schema['fields']
                }
            except ValueError:
                introspected[model_path] = {}

        # Pré-calculer les choices canton/country
        canton_choices = ModelIntrospector.get_canton_choices()
        country_choices = ModelIntrospector.get_country_choices()

        # Construire les sections depuis form_schema
        sections_config = (config.form_schema or {}).get('sections', [])
        sections_map = {}
        for sec in sections_config:
            sections_map[sec.get('id', '')] = {
                'id': sec.get('id', ''),
                'title': sec.get('title', sec.get('id', '')),
                'fields': [],
            }

        # Section par défaut pour les champs sans section
        default_section = {'id': '_default', 'title': 'Général', 'fields': []}

        # Fusionner chaque mapping avec l'introspection
        default_values = config.default_values or {}

        for mapping in config.field_mappings.select_related('form_config').order_by('order', 'field_name'):
            source = mapping.source_model or config.target_model
            introspected_fields = introspected.get(source, {})
            intro_field = introspected_fields.get(mapping.field_name, {})

            # Résoudre le widget_type: mapping prime sur introspection
            widget_type = mapping.widget_type or intro_field.get('widget_type', 'text')

            # Résoudre required: mapping (si non-null) prime sur introspection
            required = mapping.required if mapping.required is not None else intro_field.get('required', False)

            # Résoudre choices
            choices = intro_field.get('choices', None)
            if widget_type == 'canton' and not choices:
                choices = canton_choices
            elif widget_type == 'country' and not choices:
                choices = country_choices

            # Résoudre max_length
            max_length = mapping.max_length or intro_field.get('max_length', None)

            field_data = {
                'name': mapping.field_name,
                'source_model': source,
                'widget_type': widget_type,
                'label': mapping.label or intro_field.get('label', mapping.field_name),
                'required': required,
                'placeholder': mapping.placeholder or '',
                'help_text': mapping.help_text or intro_field.get('help_text', ''),
                'choices': choices,
                'conditions': mapping.conditions or {},
                'options': mapping.options or {},
                'min_length': mapping.min_length,
                'max_length': max_length,
                'min_value': mapping.min_value or '',
                'max_value': mapping.max_value or '',
                'regex_pattern': mapping.regex_pattern or '',
                'default_value': default_values.get(mapping.field_name),
                'order': mapping.order,
            }

            # Placer dans la bonne section
            section_id = mapping.section or ''
            if section_id and section_id in sections_map:
                sections_map[section_id]['fields'].append(field_data)
            else:
                default_section['fields'].append(field_data)

        # Assembler les sections dans l'ordre du form_schema
        sections = []
        for sec in sections_config:
            sec_id = sec.get('id', '')
            if sec_id in sections_map and sections_map[sec_id]['fields']:
                sections.append(sections_map[sec_id])

        # Ajouter la section par défaut si elle a des champs
        if default_section['fields']:
            sections.append(default_section)

        result = {
            'id': config.id,
            'code': config.code,
            'name': config.name,
            'description': config.description or '',
            'icon': config.icon or 'ph-file-text',
            'category': config.category,
            'success_message': config.success_message or 'Formulaire soumis avec succès.',
            'sections': sections,
            'default_values': default_values,
            'validation_rules': config.validation_rules or [],
            'related_models': config.related_models or [],
        }

        serializer = MobileFormSchemaSerializer(result)
        return Response(serializer.data)

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
            is_multi_model=original.is_multi_model,
            source_models=original.source_models,
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

        # Copier les mappings avec les nouveaux noms de champs
        for mapping in original.field_mappings.all():
            ModelFieldMapping.objects.create(
                form_config=new_config,
                source_model=mapping.source_model,
                field_name=mapping.field_name,
                field_path=mapping.field_path,
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

    @action(detail=True, methods=['post'])
    def add_field(self, request, pk=None):
        """
        Ajoute un champ au formulaire.

        Body:
        {
            "source_model": "core.Client",
            "field_name": "raison_sociale",
            "widget_type": "text",  // optionnel
            "label": "Nom de l'entreprise",  // optionnel
            ...
        }
        """
        config = self.get_object()
        data = request.data.copy()
        data['form_config'] = config.id

        # Valider le modèle source
        source_model = data.get('source_model')
        if not source_model:
            return Response(
                {'error': 'source_model est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculer l'ordre si non fourni
        if 'order' not in data:
            max_order = config.field_mappings.aggregate(
                max_order=db_models.Max('order')
            )['max_order'] or 0
            data['order'] = max_order + 10

        # Créer le mapping
        mapping = ModelFieldMapping.objects.create(
            form_config=config,
            source_model=source_model,
            field_name=data.get('field_name', ''),
            field_path=data.get('field_path', ''),
            widget_type=data.get('widget_type', 'text'),
            label=data.get('label', ''),
            help_text=data.get('help_text', ''),
            placeholder=data.get('placeholder', ''),
            required=data.get('required'),
            order=data.get('order', 0),
            section=data.get('section', ''),
            options=data.get('options', {}),
        )

        # Mettre à jour source_models si multi-modèle
        if config.is_multi_model:
            models_set = set(config.source_models or [])
            models_set.add(source_model)
            config.source_models = list(models_set)
            config.save(update_fields=['source_models'])

        return Response(
            ModelFieldMappingSerializer(mapping).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path='remove-field/(?P<mapping_id>[0-9]+)')
    def remove_field(self, request, pk=None, mapping_id=None):
        """
        Supprime un champ du formulaire.
        """
        config = self.get_object()
        try:
            mapping = config.field_mappings.get(id=mapping_id)
            mapping.delete()

            # Recalculer source_models si multi-modèle
            if config.is_multi_model:
                models_set = set(m.source_model for m in config.field_mappings.all())
                config.source_models = list(models_set)
                config.save(update_fields=['source_models'])

            return Response(status=status.HTTP_204_NO_CONTENT)
        except ModelFieldMapping.DoesNotExist:
            return Response(
                {'error': 'Mapping non trouvé'},
                status=status.HTTP_404_NOT_FOUND
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

        # SECURITE: filtrer par mandats accessibles (ses propres soumissions
        # + celles attachees a un mandat auquel il a acces)
        queryset = scope_form_submissions_by_user(queryset, self.request.user)

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
            # Stocker les erreurs non-bloquantes des post_actions
            if handler.post_action_errors:
                submission.error_details = {
                    'post_actions': handler.post_action_errors,
                }
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

    Endpoints pour explorer TOUS les modèles de TOUTES les applications Django.
    Supporte la recherche pour intégration Select2.
    """

    permission_classes = [IsManagerOrAbove]

    @action(detail=False, methods=['get'])
    def models(self, request):
        """
        Liste tous les modèles disponibles pour les formulaires.

        Query params:
        - grouped: Si 'true', retourne les modèles groupés par application
        - q: Terme de recherche pour filtrer les modèles (pour Select2)
        """
        grouped = request.query_params.get('grouped', 'false').lower() == 'true'
        query = request.query_params.get('q', '').strip()

        if query:
            # Mode recherche (pour Select2)
            models = ModelIntrospector.search_models(query)
            return Response({
                'results': [
                    {
                        'id': m['path'],
                        'text': f"{m['verbose_name']} ({m['path']})",
                        'path': m['path'],
                        'app': m['app'],
                        'name': m['name'],
                        'verbose_name': m['verbose_name'],
                    }
                    for m in models
                ]
            })

        if grouped:
            # Mode groupé par application
            models = ModelIntrospector.get_all_models()
            serializer = ModelInfoGroupedSerializer(models, many=True)
            return Response(serializer.data)

        # Mode flat (liste simple)
        models = ModelIntrospector.get_allowed_models()
        serializer = ModelInfoSerializer(models, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='schema/(?P<model_path>[^/.]+\\.[^/.]+)')
    def model_schema(self, request, model_path=None):
        """
        Retourne le schéma complet d'un modèle.

        Args:
            model_path: Chemin du modèle (ex: core.Client)
        """
        try:
            introspector = ModelIntrospector(model_path, validate=False)
            schema = introspector.get_schema()
            return Response(schema)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='fields/(?P<model_path>[^/.]+\\.[^/.]+)')
    def fields(self, request, model_path=None):
        """
        Retourne les champs d'un modèle avec recherche optionnelle.

        Query params:
        - q: Terme de recherche pour filtrer les champs (pour Select2)
        - include_system: Si 'true', inclut les champs système (id, created_at, etc.)

        Args:
            model_path: Chemin du modèle (ex: core.Client)
        """
        query = request.query_params.get('q', '').strip()
        include_system = request.query_params.get('include_system', 'false').lower() == 'true'

        try:
            introspector = ModelIntrospector(model_path, validate=False)

            if query:
                # Mode recherche
                fields = introspector.search_fields(query)
            else:
                fields = introspector.get_fields(include_system=include_system)

            # Format Select2
            return Response({
                'model': model_path,
                'results': [
                    {
                        'id': f['name'],
                        'text': f"{f['label']} ({f['name']})",
                        'name': f['name'],
                        'type': f['type'],
                        'widget_type': f['widget_type'],
                        'label': f['label'],
                        'required': f['required'],
                        'help_text': f.get('help_text', ''),
                        'choices': f.get('choices'),
                        'related_model': f.get('related_model'),
                    }
                    for f in fields
                ]
            })
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
            introspector = ModelIntrospector(model_path, validate=False)
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
            target_model=config_data.get('target_model', ''),
            is_multi_model=config_data.get('is_multi_model', False),
            source_models=config_data.get('source_models', []),
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
