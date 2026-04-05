# apps/modelforms/urls.py
"""
URLs web pour la gestion des formulaires dynamiques.
"""
from django.urls import path
from . import views

app_name = 'modelforms'

urlpatterns = [
    # ==========================================================================
    # CONFIGURATIONS
    # ==========================================================================
    path(
        '',
        views.FormConfigurationListView.as_view(),
        name='configuration-list'
    ),
    path(
        'configurations/',
        views.FormConfigurationListView.as_view(),
        name='configurations'
    ),
    path(
        'configurations/nouveau/',
        views.FormConfigurationCreateView.as_view(),
        name='configuration-create'
    ),
    path(
        'configurations/<uuid:pk>/',
        views.FormConfigurationDetailView.as_view(),
        name='configuration-detail'
    ),
    path(
        'configurations/<uuid:pk>/modifier/',
        views.FormConfigurationUpdateView.as_view(),
        name='configuration-update'
    ),
    path(
        'configurations/<uuid:pk>/supprimer/',
        views.FormConfigurationDeleteView.as_view(),
        name='configuration-delete'
    ),
    path(
        'configurations/<uuid:pk>/dupliquer/',
        views.duplicate_configuration,
        name='configuration-duplicate'
    ),

    # Configuration avancée
    path(
        'configurations/<uuid:pk>/avance/',
        views.configuration_advanced,
        name='configuration-advanced'
    ),

    # Gestion des champs (ancien, redirige vers builder)
    path(
        'configurations/<uuid:pk>/champs/',
        views.configuration_fields,
        name='configuration-fields'
    ),
    path(
        'configurations/<uuid:pk>/champs/ajouter/',
        views.add_field_mapping,
        name='add-field-mapping'
    ),
    path(
        'configurations/<uuid:pk>/champs/<int:mapping_pk>/supprimer/',
        views.delete_field_mapping,
        name='delete-field-mapping'
    ),
    path(
        'configurations/<uuid:pk>/champs/reorder/',
        views.reorder_fields,
        name='reorder-fields'
    ),

    # Constructeur visuel (Builder)
    path(
        'configurations/<uuid:pk>/builder/',
        views.form_builder,
        name='form-builder'
    ),
    path(
        'configurations/<uuid:pk>/builder/sections/',
        views.builder_sections_panel,
        name='builder-sections'
    ),
    path(
        'configurations/<uuid:pk>/builder/sections/ajouter/',
        views.builder_add_section,
        name='builder-add-section'
    ),
    path(
        'configurations/<uuid:pk>/builder/sections/<str:section_id>/modifier/',
        views.builder_edit_section,
        name='builder-edit-section'
    ),
    path(
        'configurations/<uuid:pk>/builder/sections/<str:section_id>/supprimer/',
        views.builder_delete_section,
        name='builder-delete-section'
    ),
    path(
        'configurations/<uuid:pk>/builder/sections/reorder/',
        views.builder_reorder_sections,
        name='builder-reorder-sections'
    ),
    path(
        'configurations/<uuid:pk>/builder/champs/ajouter/',
        views.builder_add_field,
        name='builder-add-field'
    ),
    path(
        'configurations/<uuid:pk>/builder/champs/<int:mapping_pk>/config/',
        views.builder_field_config,
        name='builder-field-config'
    ),
    path(
        'configurations/<uuid:pk>/builder/champs/<int:mapping_pk>/supprimer/',
        views.builder_delete_field,
        name='builder-delete-field'
    ),
    path(
        'configurations/<uuid:pk>/builder/champs/reorder/',
        views.builder_reorder_fields,
        name='builder-reorder-fields'
    ),
    path(
        'configurations/<uuid:pk>/builder/preview/',
        views.builder_preview,
        name='builder-preview'
    ),

    # ==========================================================================
    # INTROSPECTION (HTMX)
    # ==========================================================================
    path(
        'introspection/<path:model_path>/',
        views.introspect_model,
        name='introspect-model'
    ),

    # ==========================================================================
    # TEMPLATES
    # ==========================================================================
    path(
        'templates/',
        views.FormTemplateListView.as_view(),
        name='template-list'
    ),
    path(
        'templates/<int:pk>/instancier/',
        views.instantiate_template,
        name='template-instantiate'
    ),

    # ==========================================================================
    # SOUMISSIONS
    # ==========================================================================
    path(
        'soumissions/',
        views.FormSubmissionListView.as_view(),
        name='submission-list'
    ),
    path(
        'soumissions/<uuid:pk>/',
        views.FormSubmissionDetailView.as_view(),
        name='submission-detail'
    ),
    path(
        'soumissions/<uuid:pk>/valider/',
        views.validate_submission,
        name='submission-validate'
    ),
    path(
        'soumissions/<uuid:pk>/rejeter/',
        views.reject_submission,
        name='submission-reject'
    ),

    # ==========================================================================
    # REMPLISSAGE DE FORMULAIRES (utilisateurs finaux)
    # ==========================================================================
    path(
        'remplir/',
        views.AvailableFormsListView.as_view(),
        name='available-forms'
    ),
    path(
        'remplir/<uuid:pk>/',
        views.FormFillView.as_view(),
        name='form-fill'
    ),
    path(
        'remplir/<uuid:pk>/soumettre/',
        views.submit_form,
        name='form-submit'
    ),

    # ==========================================================================
    # FORMULAIRES PUBLICS (pas de login requis)
    # ==========================================================================
    path(
        'f/<uuid:token>/',
        views.PublicFormFillView.as_view(),
        name='public-form'
    ),
    path(
        'f/<uuid:token>/soumettre/',
        views.PublicFormSubmitView.as_view(),
        name='public-form-submit'
    ),
    path(
        'f/<uuid:token>/code/',
        views.AccessCodeView.as_view(),
        name='public-form-code'
    ),
    path(
        'f/<uuid:token>/succes/',
        views.PublicFormSuccessView.as_view(),
        name='public-form-success'
    ),

    # ==========================================================================
    # QR CODE (login requis)
    # ==========================================================================
    path(
        'configurations/<uuid:pk>/qrcode/',
        views.FormQRCodeView.as_view(),
        name='configuration-qrcode'
    ),

    # ==========================================================================
    # API HTMX
    # ==========================================================================
    path(
        'api/fields/<path:model_path>/',
        views.get_field_options,
        name='api-field-options'
    ),

    # ==========================================================================
    # PROCESS ENGINE (PR2) — Definitions de processus metiers
    # ==========================================================================
    path(
        'processus/',
        views.ProcessDefinitionListView.as_view(),
        name='process-list',
    ),
    path(
        'processus/nouveau/',
        views.ProcessDefinitionCreateView.as_view(),
        name='process-create',
    ),
    path(
        'processus/<uuid:pk>/',
        views.ProcessDefinitionDetailView.as_view(),
        name='process-detail',
    ),
    path(
        'processus/<uuid:pk>/modifier/',
        views.ProcessDefinitionUpdateView.as_view(),
        name='process-update',
    ),
    path(
        'processus/<uuid:pk>/supprimer/',
        views.ProcessDefinitionDeleteView.as_view(),
        name='process-delete',
    ),
    path(
        'processus/<uuid:pk>/publier/',
        views.process_publish,
        name='process-publish',
    ),
    path(
        'processus/<uuid:pk>/nouvelle-version/',
        views.process_new_version,
        name='process-new-version',
    ),

    # Instances
    path(
        'processus-instances/',
        views.ProcessInstanceListView.as_view(),
        name='process-instance-list',
    ),
    path(
        'processus-instances/<uuid:pk>/',
        views.ProcessInstanceDetailView.as_view(),
        name='process-instance-detail',
    ),
]
