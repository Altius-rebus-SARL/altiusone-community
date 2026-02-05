# apps/modelforms/admin.py
from django.contrib import admin
from .models import FormConfiguration, ModelFieldMapping, FormSubmission, FormTemplate


class ModelFieldMappingInline(admin.TabularInline):
    model = ModelFieldMapping
    extra = 0
    ordering = ['order', 'field_name']


@admin.register(FormConfiguration)
class FormConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'code',
        'name',
        'category',
        'target_model',
        'status',
        'require_validation',
        'created_at',
    ]
    list_filter = ['status', 'category', 'require_validation']
    search_fields = ['code', 'name', 'target_model', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    inlines = [ModelFieldMappingInline]

    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'description', 'category', 'icon')
        }),
        ('Modèle cible', {
            'fields': ('target_model', 'related_models')
        }),
        ('Configuration', {
            'fields': ('form_schema', 'default_values', 'validation_rules', 'post_actions'),
            'classes': ('collapse',),
        }),
        ('Statut', {
            'fields': ('status', 'require_validation')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',),
        }),
    )


@admin.register(ModelFieldMapping)
class ModelFieldMappingAdmin(admin.ModelAdmin):
    list_display = [
        'form_config',
        'field_name',
        'model_path',
        'widget_type',
        'required',
        'order',
    ]
    list_filter = ['form_config', 'widget_type', 'required']
    search_fields = ['field_name', 'label', 'form_config__code']
    ordering = ['form_config', 'order', 'field_name']


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'form_config',
        'submitted_by',
        'submitted_at',
        'status',
        'validated_by',
    ]
    list_filter = ['status', 'form_config', 'submitted_at']
    search_fields = ['form_config__code', 'submitted_by__username']
    readonly_fields = [
        'submitted_data',
        'submitted_by',
        'submitted_at',
        'created_records',
        'error_message',
        'error_details',
    ]
    date_hierarchy = 'submitted_at'

    fieldsets = (
        (None, {
            'fields': ('form_config', 'status', 'mandat')
        }),
        ('Soumission', {
            'fields': ('submitted_data', 'submitted_by', 'submitted_at')
        }),
        ('Résultat', {
            'fields': ('created_records', 'error_message', 'error_details'),
            'classes': ('collapse',),
        }),
        ('Validation', {
            'fields': ('validated_by', 'validated_at', 'validation_notes'),
            'classes': ('collapse',),
        }),
    )


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'code',
        'name',
        'category',
        'is_system',
        'is_active',
        'created_at',
    ]
    list_filter = ['category', 'is_system', 'is_active']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
