# apps/modelforms/serializers.py
"""
Serializers pour l'API Model-Driven Forms.

Pattern List/Detail comme dans core/ et salaires/:
- ListSerializer: Champs essentiels pour les listes
- DetailSerializer: Tous les champs + relations imbriquées
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
            'field_name',
            'model_path',
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
            'status',
            'status_display',
            'require_validation',
            'icon',
            'field_count',
            'submission_count',
            'created_at',
            'updated_at',
        ]

    def get_field_count(self, obj) -> int:
        return obj.field_mappings.count()

    def get_submission_count(self, obj) -> int:
        return obj.submissions.count()


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

    class Meta:
        model = FormConfiguration
        fields = '__all__'


class FormConfigurationWriteSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification de configurations."""

    field_mappings = ModelFieldMappingSerializer(many=True, required=False)

    class Meta:
        model = FormConfiguration
        fields = [
            'code',
            'name',
            'description',
            'category',
            'target_model',
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
        """Vérifie que le modèle cible est autorisé."""
        from .services.introspector import ALLOWED_MODELS
        if value not in ALLOWED_MODELS:
            raise serializers.ValidationError(
                f"Modèle non autorisé. Modèles disponibles: {', '.join(sorted(ALLOWED_MODELS))}"
            )
        return value

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
        """Vérifie que la configuration existe et est active."""
        try:
            config = FormConfiguration.objects.get(id=value)
            if config.status != FormConfiguration.Status.ACTIVE:
                raise serializers.ValidationError(
                    "Cette configuration de formulaire n'est pas active"
                )
            return value
        except FormConfiguration.DoesNotExist:
            raise serializers.ValidationError("Configuration introuvable")

    def create(self, validated_data):
        """Crée et traite la soumission."""
        from .services.submission_handler import SubmissionHandler
        from core.models import Mandat

        config = FormConfiguration.objects.get(id=validated_data['form_config_id'])
        user = self.context['request'].user

        # Récupérer le mandat si spécifié
        mandat = None
        if validated_data.get('mandat_id'):
            try:
                mandat = Mandat.objects.get(id=validated_data['mandat_id'])
            except Mandat.DoesNotExist:
                pass

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
