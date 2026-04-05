# apps/modelforms/serializers.py
"""
Serializers pour l'API Model-Driven Forms.

Pattern List/Detail comme dans core/ et salaires/:
- ListSerializer: Champs essentiels pour les listes
- DetailSerializer: Tous les champs + relations imbriquées

Supporte les formulaires multi-modèles avec champs provenant de différentes apps.
"""
from rest_framework import serializers
from .models import FormConfiguration, ModelFieldMapping, FormSubmission, FormTemplate
from core.serializers import UserSerializer, MandatListSerializer


# =============================================================================
# FormConfiguration Serializers
# =============================================================================

class ModelFieldMappingSerializer(serializers.ModelSerializer):
    """Serializer pour les mappings de champs."""

    widget_type_display = serializers.CharField(
        source='get_widget_type_display',
        read_only=True
    )

    class Meta:
        model = ModelFieldMapping
        fields = [
            'id',
            'source_model',
            'field_name',
            'field_path',
            'widget_type',
            'widget_type_display',
            'label',
            'help_text',
            'placeholder',
            'required',
            'min_value',
            'max_value',
            'min_length',
            'max_length',
            'regex_pattern',
            'conditions',
            'order',
            'section',
            'options',
        ]


class ModelFieldMappingWriteSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification des mappings."""

    class Meta:
        model = ModelFieldMapping
        fields = [
            'source_model',
            'field_name',
            'field_path',
            'widget_type',
            'label',
            'help_text',
            'placeholder',
            'required',
            'min_value',
            'max_value',
            'min_length',
            'max_length',
            'regex_pattern',
            'conditions',
            'order',
            'section',
            'options',
        ]

    def validate_source_model(self, value):
        """Vérifie que le modèle source existe."""
        from .services.introspector import ModelIntrospector, EXCLUDED_MODELS
        if value in EXCLUDED_MODELS:
            raise serializers.ValidationError(
                f"Modèle système non autorisé: {value}"
            )
        try:
            ModelIntrospector(value, validate=False)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return value


class FormConfigurationListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des configurations."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    field_count = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    model_count = serializers.SerializerMethodField()

    class Meta:
        model = FormConfiguration
        fields = [
            'id',
            'code',
            'name',
            'description',
            'category',
            'category_display',
            'target_model',
            'is_multi_model',
            'source_models',
            'status',
            'status_display',
            'require_validation',
            'icon',
            'success_message',
            'field_count',
            'submission_count',
            'model_count',
            'created_at',
            'updated_at',
        ]

    def get_field_count(self, obj) -> int:
        return obj.field_mappings.count()

    def get_submission_count(self, obj) -> int:
        return obj.submissions.count()

    def get_model_count(self, obj) -> int:
        """Retourne le nombre de modèles utilisés dans le formulaire."""
        if obj.is_multi_model:
            return len(obj.source_models or [])
        return 1 if obj.target_model else 0


class FormConfigurationDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une configuration."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    field_mappings = ModelFieldMappingSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    fields_by_model = serializers.SerializerMethodField()

    class Meta:
        model = FormConfiguration
        fields = '__all__'

    def get_fields_by_model(self, obj) -> dict:
        """Groupe les champs par modèle source pour les formulaires multi-modèles."""
        result = {}
        for mapping in obj.field_mappings.all():
            model = mapping.source_model
            if model not in result:
                result[model] = []
            result[model].append(ModelFieldMappingSerializer(mapping).data)
        return result


class FormConfigurationWriteSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification de configurations."""

    field_mappings = ModelFieldMappingWriteSerializer(many=True, required=False)

    class Meta:
        model = FormConfiguration
        fields = [
            'code',
            'name',
            'description',
            'category',
            'target_model',
            'is_multi_model',
            'source_models',
            'related_models',
            'form_schema',
            'default_values',
            'validation_rules',
            'post_actions',
            'status',
            'require_validation',
            'icon',
            'field_mappings',
        ]

    def validate_target_model(self, value):
        """Vérifie que le modèle cible existe (si fourni)."""
        if not value:
            return value
        from .services.introspector import ModelIntrospector, EXCLUDED_MODELS
        if value in EXCLUDED_MODELS:
            raise serializers.ValidationError(
                f"Modèle système non autorisé: {value}"
            )
        try:
            ModelIntrospector(value, validate=False)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return value

    def validate_source_models(self, value):
        """Vérifie que tous les modèles sources existent."""
        if not value:
            return value
        from .services.introspector import ModelIntrospector, EXCLUDED_MODELS
        errors = []
        for model_path in value:
            if model_path in EXCLUDED_MODELS:
                errors.append(f"Modèle système non autorisé: {model_path}")
                continue
            try:
                ModelIntrospector(model_path, validate=False)
            except ValueError as e:
                errors.append(str(e))
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate(self, data):
        """Validation croisée des champs."""
        is_multi_model = data.get('is_multi_model', False)
        target_model = data.get('target_model', '')
        source_models = data.get('source_models', [])

        # Pour un formulaire mono-modèle, target_model est requis
        if not is_multi_model and not target_model:
            raise serializers.ValidationError({
                'target_model': 'Le modèle cible est requis pour un formulaire mono-modèle'
            })

        # Pour un formulaire multi-modèle, source_models devrait être renseigné
        if is_multi_model and not source_models:
            # On peut le calculer automatiquement depuis les field_mappings
            pass

        return data

    def create(self, validated_data):
        """Crée la configuration avec ses mappings."""
        field_mappings_data = validated_data.pop('field_mappings', [])

        # Ajouter created_by
        if 'request' in self.context:
            validated_data['created_by'] = self.context['request'].user

        config = FormConfiguration.objects.create(**validated_data)

        # Créer les mappings
        for mapping_data in field_mappings_data:
            ModelFieldMapping.objects.create(form_config=config, **mapping_data)

        # Auto-calculer source_models si multi-modèle
        if config.is_multi_model:
            models = set(m.source_model for m in config.field_mappings.all())
            config.source_models = list(models)
            config.save(update_fields=['source_models'])

        return config

    def update(self, instance, validated_data):
        """Met à jour la configuration avec ses mappings."""
        field_mappings_data = validated_data.pop('field_mappings', None)

        # Mettre à jour les champs de base
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Mettre à jour les mappings si fournis
        if field_mappings_data is not None:
            # Supprimer les anciens mappings
            instance.field_mappings.all().delete()
            # Créer les nouveaux
            for mapping_data in field_mappings_data:
                ModelFieldMapping.objects.create(form_config=instance, **mapping_data)

            # Auto-calculer source_models si multi-modèle
            if instance.is_multi_model:
                models = set(m.source_model for m in instance.field_mappings.all())
                instance.source_models = list(models)
                instance.save(update_fields=['source_models'])

        return instance


# =============================================================================
# FormSubmission Serializers
# =============================================================================

class FormSubmissionListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des soumissions."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    form_config_code = serializers.CharField(
        source='form_config.code',
        read_only=True
    )
    form_config_name = serializers.CharField(
        source='form_config.name',
        read_only=True
    )
    submitted_by_name = serializers.SerializerMethodField()
    record_count = serializers.SerializerMethodField()

    class Meta:
        model = FormSubmission
        fields = [
            'id',
            'form_config',
            'form_config_code',
            'form_config_name',
            'submitted_by',
            'submitted_by_name',
            'submitted_at',
            'status',
            'status_display',
            'record_count',
            'validated_by',
            'validated_at',
        ]

    def get_submitted_by_name(self, obj) -> str:
        return obj.submitted_by.get_full_name() or obj.submitted_by.username

    def get_record_count(self, obj) -> int:
        return len(obj.created_records or [])


class FormSubmissionDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une soumission."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    form_config = FormConfigurationListSerializer(read_only=True)
    submitted_by = UserSerializer(read_only=True)
    validated_by = UserSerializer(read_only=True)
    mandat = MandatListSerializer(read_only=True)

    class Meta:
        model = FormSubmission
        fields = '__all__'


class FormSubmissionCreateSerializer(serializers.Serializer):
    """Serializer pour créer une soumission."""

    form_config_id = serializers.UUIDField()
    data = serializers.JSONField()
    mandat_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_form_config_id(self, value):
        """Vérifie que la configuration existe, est active, et est accessible."""
        from .permissions import user_can_access_form_config

        try:
            config = FormConfiguration.objects.get(id=value)
        except FormConfiguration.DoesNotExist:
            raise serializers.ValidationError("Configuration introuvable")

        if config.status != FormConfiguration.Status.ACTIVE:
            raise serializers.ValidationError(
                "Cette configuration de formulaire n'est pas active"
            )

        # SECURITE: verifier l'acces au formulaire pour cet utilisateur
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if user is not None and not user_can_access_form_config(user, config):
            raise serializers.ValidationError(
                "Vous n'avez pas acces a ce formulaire."
            )

        return value

    def validate_mandat_id(self, value):
        """Verifie que l'utilisateur peut acceder au mandat demande."""
        from .permissions import user_can_access_mandat
        from core.models import Mandat

        if value is None:
            return value

        try:
            mandat = Mandat.objects.get(id=value)
        except Mandat.DoesNotExist:
            raise serializers.ValidationError("Mandat introuvable")

        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if user is not None and not user_can_access_mandat(user, mandat):
            raise serializers.ValidationError(
                "Vous n'avez pas acces a ce mandat."
            )

        return value

    def create(self, validated_data):
        """Crée et traite la soumission."""
        from .services.submission_handler import SubmissionHandler
        from core.models import Mandat

        config = FormConfiguration.objects.get(id=validated_data['form_config_id'])
        user = self.context['request'].user

        # Récupérer le mandat si spécifié (déjà validé par validate_mandat_id)
        mandat = None
        if validated_data.get('mandat_id'):
            try:
                mandat = Mandat.objects.get(id=validated_data['mandat_id'])
            except Mandat.DoesNotExist:
                mandat = None

        # Créer la soumission
        submission = FormSubmission.objects.create(
            form_config=config,
            submitted_data=validated_data['data'],
            submitted_by=user,
            mandat=mandat,
            status=FormSubmission.Status.PROCESSING,
        )

        # Si validation requise, laisser en attente
        if config.require_validation:
            submission.status = FormSubmission.Status.PENDING
            submission.save()
            return submission

        # Sinon, traiter immédiatement
        handler = SubmissionHandler(
            form_config=config,
            submitted_data=validated_data['data'],
            user=user,
            mandat=mandat,
        )

        success, records, errors = handler.process()

        if success:
            submission.status = FormSubmission.Status.COMPLETED
            submission.created_records = records
            if handler.post_action_errors:
                submission.error_details = {
                    'post_actions': handler.post_action_errors,
                }
        else:
            submission.status = FormSubmission.Status.FAILED
            submission.error_message = '; '.join(errors)
            submission.error_details = {'errors': errors}

        submission.save()
        return submission


# =============================================================================
# FormTemplate Serializers
# =============================================================================

class FormTemplateListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des templates."""

    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )

    class Meta:
        model = FormTemplate
        fields = [
            'id',
            'code',
            'name',
            'description',
            'category',
            'category_display',
            'icon',
            'is_system',
            'is_active',
        ]


class FormTemplateDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un template."""

    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )

    class Meta:
        model = FormTemplate
        fields = '__all__'


# =============================================================================
# Introspection Serializers
# =============================================================================

class ModelInfoSerializer(serializers.Serializer):
    """Serializer pour les informations d'un modèle."""

    path = serializers.CharField()
    app = serializers.CharField()
    name = serializers.CharField()
    verbose_name = serializers.CharField()
    verbose_name_plural = serializers.CharField()
    field_count = serializers.IntegerField(required=False)


class ModelInfoGroupedSerializer(serializers.Serializer):
    """Serializer pour les modèles groupés par application."""

    app_label = serializers.CharField()
    app_name = serializers.CharField()
    models = ModelInfoSerializer(many=True)


class FieldInfoSerializer(serializers.Serializer):
    """Serializer pour les informations d'un champ."""

    name = serializers.CharField()
    type = serializers.CharField()
    widget_type = serializers.CharField()
    label = serializers.CharField()
    help_text = serializers.CharField(allow_blank=True)
    required = serializers.BooleanField()
    editable = serializers.BooleanField()
    max_length = serializers.IntegerField(required=False)
    choices = serializers.ListField(required=False)
    related_model = serializers.CharField(required=False)
    related_verbose_name = serializers.CharField(required=False)
    validators = serializers.ListField(required=False)


class ModelSchemaSerializer(serializers.Serializer):
    """Serializer pour le schéma complet d'un modèle."""

    model = serializers.CharField()
    verbose_name = serializers.CharField()
    verbose_name_plural = serializers.CharField()
    fields = FieldInfoSerializer(many=True)
    suggested_groups = serializers.ListField()


# =============================================================================
# Mobile Schema Serializers
# =============================================================================

class MobileFieldSerializer(serializers.Serializer):
    """Serializer pour un champ dans le schéma mobile pré-mergé."""

    name = serializers.CharField()
    source_model = serializers.CharField()
    widget_type = serializers.CharField()
    label = serializers.CharField()
    required = serializers.BooleanField()
    placeholder = serializers.CharField(allow_blank=True, default='')
    help_text = serializers.CharField(allow_blank=True, default='')
    choices = serializers.ListField(child=serializers.DictField(), allow_null=True, default=None)
    conditions = serializers.DictField(default=dict)
    options = serializers.DictField(default=dict)
    min_length = serializers.IntegerField(allow_null=True, default=None)
    max_length = serializers.IntegerField(allow_null=True, default=None)
    min_value = serializers.CharField(allow_blank=True, default='')
    max_value = serializers.CharField(allow_blank=True, default='')
    regex_pattern = serializers.CharField(allow_blank=True, default='')
    default_value = serializers.JSONField(allow_null=True, default=None)
    order = serializers.IntegerField(default=0)


class MobileSectionSerializer(serializers.Serializer):
    """Serializer pour une section dans le schéma mobile."""

    id = serializers.CharField()
    title = serializers.CharField()
    fields = MobileFieldSerializer(many=True)


class MobileFormSchemaSerializer(serializers.Serializer):
    """Serializer pour le schéma complet mobile pré-mergé."""

    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    icon = serializers.CharField()
    category = serializers.CharField()
    success_message = serializers.CharField()
    sections = MobileSectionSerializer(many=True)
    default_values = serializers.DictField()
    validation_rules = serializers.ListField()
    related_models = serializers.ListField()
