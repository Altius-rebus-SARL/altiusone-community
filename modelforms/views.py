# apps/modelforms/views.py
"""
Vues web pour la gestion des formulaires dynamiques.

Interface HTMX pour créer, modifier et gérer les configurations de formulaires.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from django.utils import timezone

from core.permissions import BusinessPermissionMixin, permission_required_business
from .models import (
    FormConfiguration,
    ModelFieldMapping,
    FormSubmission,
    FormTemplate,
    ProcessDefinition,
    ProcessStep,
    ProcessTransition,
    ProcessInstance,
    StepExecution,
)
from .forms import (
    FormConfigurationForm,
    FormConfigurationAdvancedForm,
    ModelFieldMappingForm,
    ModelFieldMappingFormSet,
    FormTemplateSelectForm,
    BuilderFieldMappingForm,
)
from .services.introspector import ModelIntrospector
from .services.submission_handler import SubmissionHandler
from .permissions import (
    scope_form_configs_by_user,
    scope_form_submissions_by_user,
    scope_process_definitions_by_user,
    scope_process_instances_by_user,
    user_can_access_mandat,
    user_can_access_form_config,
)


# =============================================================================
# CONFIGURATIONS
# =============================================================================

class FormConfigurationListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des configurations de formulaires."""

    model = FormConfiguration
    business_permission = 'modelforms.view_configurations'
    template_name = 'modelforms/configuration_list.html'
    context_object_name = 'configurations'
    paginate_by = 20

    def get_queryset(self):
        queryset = FormConfiguration.objects.annotate(
            submission_count=Count('submissions'),
            field_count=Count('field_mappings'),
        ).order_by('category', 'name')

        # SECURITE: mandat-scoping (configs globales + mandats accessibles)
        queryset = scope_form_configs_by_user(queryset, self.request.user)

        # Filtres
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)

        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(code__icontains=q) |
                Q(name__icontains=q) |
                Q(target_model__icontains=q)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'total': FormConfiguration.objects.count(),
            'active': FormConfiguration.objects.filter(status='ACTIVE').count(),
            'draft': FormConfiguration.objects.filter(status='DRAFT').count(),
        }
        context['categories'] = FormConfiguration.Category.choices
        context['statuses'] = FormConfiguration.Status.choices
        return context


class FormConfigurationDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une configuration de formulaire."""

    model = FormConfiguration
    business_permission = 'modelforms.view_configurations'
    template_name = 'modelforms/configuration_detail.html'
    context_object_name = 'configuration'

    def get_queryset(self):
        # SECURITE: ne pas exposer les configs de mandats non-accessibles
        return scope_form_configs_by_user(
            FormConfiguration.objects.all(),
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = self.object

        # Introspection du modèle
        try:
            introspector = ModelIntrospector(config.target_model)
            context['model_schema'] = introspector.get_schema()
            context['json_schema'] = introspector.get_json_schema()
        except ValueError:
            context['model_schema'] = None
            context['json_schema'] = {}

        # Mappings de champs
        context['field_mappings'] = config.field_mappings.all().order_by('order')

        # Soumissions récentes
        context['recent_submissions'] = config.submissions.order_by('-submitted_at')[:5]

        # Stats
        context['submission_count'] = config.submissions.count()

        # Public access info
        public_url = self.request.build_absolute_uri(
            reverse('modelforms:public-form', kwargs={'token': config.public_token})
        )
        context['public_url'] = public_url

        # QR code (inline base64)
        if config.status == FormConfiguration.Status.ACTIVE:
            from .services.qr_service import get_qr_code_base64
            try:
                context['qr_code_data_uri'] = get_qr_code_base64(public_url)
            except Exception:
                context['qr_code_data_uri'] = None

        # Mandats associés
        context['mandats'] = config.mandats.all()

        return context


class FormConfigurationCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'une configuration de formulaire."""

    model = FormConfiguration
    business_permission = 'modelforms.add_configuration'
    template_name = 'modelforms/configuration_form.html'
    form_class = FormConfigurationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = FormTemplate.objects.filter(is_active=True)
        context['template_form'] = FormTemplateSelectForm()
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Configuration créée avec succès.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('modelforms:configuration-detail', kwargs={'pk': self.object.pk})


class FormConfigurationUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'une configuration de formulaire."""

    model = FormConfiguration
    business_permission = 'modelforms.change_configuration'
    template_name = 'modelforms/configuration_form.html'
    form_class = FormConfigurationForm

    def form_valid(self, form):
        messages.success(self.request, _('Configuration modifiée avec succès.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('modelforms:configuration-detail', kwargs={'pk': self.object.pk})


class FormConfigurationDeleteView(LoginRequiredMixin, BusinessPermissionMixin, DeleteView):
    """Suppression d'une configuration de formulaire."""

    model = FormConfiguration
    business_permission = 'modelforms.delete_configuration'
    template_name = 'modelforms/configuration_confirm_delete.html'
    success_url = reverse_lazy('modelforms:configuration-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Configuration supprimée avec succès.'))
        return super().delete(request, *args, **kwargs)


# =============================================================================
# CONFIGURATION AVANCÉE (JSON)
# =============================================================================

@login_required
@permission_required_business('modelforms.change_configuration')
def configuration_advanced(request, pk):
    """Édition avancée de la configuration JSON."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)

    if request.method == 'POST':
        form = FormConfigurationAdvancedForm(request.POST, instance=configuration)
        if form.is_valid():
            form.save()
            messages.success(request, _('Configuration avancée enregistrée.'))
            return redirect('modelforms:configuration-detail', pk=pk)
    else:
        form = FormConfigurationAdvancedForm(instance=configuration)

    return render(request, 'modelforms/configuration_advanced.html', {
        'configuration': configuration,
        'form': form,
    })


# =============================================================================
# FIELD MAPPINGS (HTMX)
# =============================================================================

@login_required
@permission_required_business('modelforms.change_configuration')
def configuration_fields(request, pk):
    """Gestion des mappings de champs avec HTMX."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)

    if request.method == 'POST':
        formset = ModelFieldMappingFormSet(request.POST, instance=configuration)
        if formset.is_valid():
            formset.save()
            messages.success(request, _('Champs mis à jour avec succès.'))
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    status=200,
                    headers={'HX-Trigger': 'fieldsUpdated'}
                )
            return redirect('modelforms:configuration-detail', pk=pk)
    else:
        formset = ModelFieldMappingFormSet(instance=configuration)

    # Récupérer les champs du modèle pour suggestion
    try:
        introspector = ModelIntrospector(configuration.target_model)
        model_fields = introspector.get_fields()
    except ValueError:
        model_fields = []

    # Field mappings for display
    field_mappings = configuration.field_mappings.all().order_by('order')

    template = 'modelforms/partials/field_mappings.html' if request.headers.get('HX-Request') else 'modelforms/configuration_fields.html'

    return render(request, template, {
        'configuration': configuration,
        'formset': formset,
        'model_fields': model_fields,
        'field_mappings': field_mappings,
    })


@login_required
@require_http_methods(['GET', 'POST'])
@permission_required_business('modelforms.change_configuration')
def add_field_mapping(request, pk):
    """Ajoute ou modifie un mapping de champ (HTMX)."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)

    # Edit existing mapping
    mapping_id = request.GET.get('mapping_id') or request.POST.get('mapping_id')
    if mapping_id:
        mapping = get_object_or_404(ModelFieldMapping, pk=mapping_id, form_config=configuration)
    else:
        mapping = None

    if request.method == 'POST':
        form = ModelFieldMappingForm(request.POST, instance=mapping)
        if form.is_valid():
            new_mapping = form.save(commit=False)
            new_mapping.form_config = configuration
            if not new_mapping.order:
                new_mapping.order = configuration.field_mappings.count()
            new_mapping.save()

            # Return the updated list
            field_mappings = configuration.field_mappings.all().order_by('order')
            return render(request, 'modelforms/partials/field_mappings.html', {
                'configuration': configuration,
                'field_mappings': field_mappings,
            })
    else:
        # Pre-fill field_name if provided
        initial = {}
        field_name = request.GET.get('field_name')
        if field_name:
            initial['field_name'] = field_name
        form = ModelFieldMappingForm(instance=mapping, initial=initial)

    return render(request, 'modelforms/partials/add_field_form.html', {
        'configuration': configuration,
        'form': form,
    })


@login_required
@require_http_methods(['DELETE', 'POST'])
@permission_required_business('modelforms.change_configuration')
def delete_field_mapping(request, pk, mapping_pk):
    """Supprime un mapping de champ (HTMX)."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)
    mapping = get_object_or_404(ModelFieldMapping, pk=mapping_pk, form_config=configuration)
    mapping.delete()

    if request.headers.get('HX-Request'):
        # Return updated list
        field_mappings = configuration.field_mappings.all().order_by('order')
        return render(request, 'modelforms/partials/field_mappings.html', {
            'configuration': configuration,
            'field_mappings': field_mappings,
        })

    return redirect('modelforms:configuration-fields', pk=pk)


# =============================================================================
# CONSTRUCTEUR VISUEL (BUILDER)
# =============================================================================

@login_required
@permission_required_business('modelforms.change_configuration')
def form_builder(request, pk):
    """Page principale du constructeur 3 panneaux."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)

    # Collect all models to introspect (target + source_models)
    models_to_introspect = []
    if configuration.target_model:
        models_to_introspect.append(configuration.target_model)
    for sm in (configuration.source_models or []):
        if sm and sm not in models_to_introspect:
            models_to_introspect.append(sm)

    # Introspect all models
    model_fields = []
    suggested_groups = []
    catalogue_models = []  # [{model_path, fields, groups}]
    for model_path in models_to_introspect:
        try:
            introspector = ModelIntrospector(model_path)
            fields = introspector.get_fields()
            groups = introspector.get_suggested_groups()
            # Tag each field with its source model
            for f in fields:
                f['source_model'] = model_path
            model_fields.extend(fields)
            suggested_groups.extend(groups)
            catalogue_models.append({
                'path': model_path,
                'fields': fields,
                'groups': groups,
            })
        except ValueError:
            pass

    field_mappings = list(configuration.field_mappings.all().order_by('order'))
    configured_field_names = {m.field_name for m in field_mappings}

    # Sections depuis form_schema
    sections = (configuration.form_schema or {}).get('sections', [])

    # Grouper les champs du modèle par groupe suggéré
    grouped_fields = {}
    ungrouped_fields = []
    grouped_field_names = set()
    for group in suggested_groups:
        group_fields = [f for f in model_fields if f['name'] in group['fields']]
        if group_fields:
            grouped_fields[group['id']] = {
                'title': group['title'],
                'fields': group_fields,
            }
            grouped_field_names.update(f['name'] for f in group_fields)

    ungrouped_fields = [f for f in model_fields if f['name'] not in grouped_field_names]

    # Organiser les champs par section pour le panel central
    fields_by_section = {s['id']: [] for s in sections}
    fields_by_section['_unsectioned'] = []
    for mapping in field_mappings:
        section_id = mapping.section or '_unsectioned'
        if section_id in fields_by_section:
            fields_by_section[section_id].append(mapping)
        else:
            fields_by_section['_unsectioned'].append(mapping)

    return render(request, 'modelforms/form_builder.html', {
        'configuration': configuration,
        'model_fields': model_fields,
        'suggested_groups': suggested_groups,
        'grouped_fields': grouped_fields,
        'ungrouped_fields': ungrouped_fields,
        'field_mappings': field_mappings,
        'configured_field_names': configured_field_names,
        'sections': sections,
        'fields_by_section': fields_by_section,
        'catalogue_models': catalogue_models,
    })


@login_required
@permission_required_business('modelforms.change_configuration')
def builder_sections_panel(request, pk):
    """Retourne le panel central (sections + champs). HTMX partial."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)
    field_mappings = list(configuration.field_mappings.all().order_by('order'))
    sections = (configuration.form_schema or {}).get('sections', [])

    # Organiser les champs par section
    fields_by_section = {s['id']: [] for s in sections}
    fields_by_section['_unsectioned'] = []
    for mapping in field_mappings:
        section_id = mapping.section or '_unsectioned'
        if section_id in fields_by_section:
            fields_by_section[section_id].append(mapping)
        else:
            fields_by_section['_unsectioned'].append(mapping)

    return render(request, 'modelforms/partials/builder_sections.html', {
        'configuration': configuration,
        'sections': sections,
        'fields_by_section': fields_by_section,
        'field_mappings': field_mappings,
    })


@login_required
@require_POST
@permission_required_business('modelforms.change_configuration')
def builder_add_section(request, pk):
    """Ajoute une section dans form_schema.sections."""
    import unicodedata
    import re
    configuration = get_object_or_404(FormConfiguration, pk=pk)
    title = request.POST.get('title', '').strip()
    icon = request.POST.get('icon', '').strip()

    if not title:
        return HttpResponse('Titre requis', status=400)

    # Générer un id: slugify (normalise les accents puis nettoie)
    nfkd = unicodedata.normalize('NFKD', title.lower())
    ascii_text = nfkd.encode('ascii', 'ignore').decode('ascii')
    section_id = re.sub(r'[^a-z0-9]+', '_', ascii_text).strip('_')
    if not section_id:
        import uuid
        section_id = uuid.uuid4().hex[:8]

    # Vérifier unicité
    schema = configuration.form_schema or {}
    sections = schema.get('sections', [])
    existing_ids = {s['id'] for s in sections}
    base_id = section_id
    counter = 1
    while section_id in existing_ids:
        section_id = f"{base_id}_{counter}"
        counter += 1

    new_section = {'id': section_id, 'title': title}
    if icon:
        new_section['icon'] = icon
    sections.append(new_section)
    schema['sections'] = sections
    configuration.form_schema = schema
    configuration.save(update_fields=['form_schema'])

    response = _builder_sections_response(request, configuration)
    response['HX-Trigger'] = 'previewUpdated'
    return response


@login_required
@require_POST
@permission_required_business('modelforms.change_configuration')
def builder_edit_section(request, pk, section_id):
    """Modifie title/icon d'une section."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)
    title = request.POST.get('title', '').strip()
    icon = request.POST.get('icon', '').strip()

    schema = configuration.form_schema or {}
    sections = schema.get('sections', [])
    for section in sections:
        if section['id'] == section_id:
            if title:
                section['title'] = title
            if icon:
                section['icon'] = icon
            elif 'icon' in section:
                del section['icon']
            break

    schema['sections'] = sections
    configuration.form_schema = schema
    configuration.save(update_fields=['form_schema'])

    response = _builder_sections_response(request, configuration)
    response['HX-Trigger'] = 'previewUpdated'
    return response


@login_required
@require_http_methods(['DELETE', 'POST'])
@permission_required_business('modelforms.change_configuration')
def builder_delete_section(request, pk, section_id):
    """Supprime une section. Déplace ses champs vers '_unsectioned'."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)

    schema = configuration.form_schema or {}
    sections = schema.get('sections', [])
    schema['sections'] = [s for s in sections if s['id'] != section_id]
    configuration.form_schema = schema
    configuration.save(update_fields=['form_schema'])

    # Déplacer les champs de cette section
    configuration.field_mappings.filter(section=section_id).update(section='')

    response = _builder_sections_response(request, configuration)
    response['HX-Trigger'] = 'previewUpdated, catalogueUpdated'
    return response


@login_required
@require_POST
@permission_required_business('modelforms.change_configuration')
def builder_reorder_sections(request, pk):
    """Sauvegarde l'ordre des sections (Sortable.js)."""
    import json
    configuration = get_object_or_404(FormConfiguration, pk=pk)

    try:
        data = json.loads(request.body)
        order_list = data.get('order', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    schema = configuration.form_schema or {}
    sections = schema.get('sections', [])
    section_map = {s['id']: s for s in sections}
    reordered = [section_map[sid] for sid in order_list if sid in section_map]
    # Append any sections not in the order list
    remaining = [s for s in sections if s['id'] not in set(order_list)]
    schema['sections'] = reordered + remaining
    configuration.form_schema = schema
    configuration.save(update_fields=['form_schema'])

    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
@permission_required_business('modelforms.change_configuration')
def builder_add_field(request, pk):
    """Ajoute un champ au formulaire (dans une section donnée)."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)
    field_name = request.POST.get('field_name', '').strip()
    source_model = request.POST.get('source_model', '').strip() or configuration.target_model
    section_id = request.POST.get('section_id', '').strip()

    if not field_name:
        return HttpResponse('field_name requis', status=400)

    # Vérifier si le champ existe déjà
    if configuration.field_mappings.filter(field_name=field_name, source_model=source_model).exists():
        return HttpResponse('Ce champ est déjà ajouté', status=400)

    # Détecter les métadonnées via introspector
    widget_type = 'text'
    label = field_name
    help_text = ''
    required = None
    max_length = None
    choices = None
    related_model = None
    try:
        introspector = ModelIntrospector(source_model)
        for field_info in introspector.get_fields(include_system=True):
            if field_info['name'] == field_name:
                widget_type = field_info.get('widget_type', 'text')
                label = field_info.get('label', field_name)
                help_text = field_info.get('help_text', '')
                required = field_info.get('required', None)
                max_length = field_info.get('max_length')
                choices = field_info.get('choices')
                related_model = field_info.get('related_model')
                break
    except ValueError:
        pass

    # Ordre: après le dernier champ
    max_order = configuration.field_mappings.count()

    # Construire les options du widget
    options = {}
    if choices:
        options['choices'] = choices
    if related_model:
        options['endpoint'] = f'/api/v1/{related_model.replace(".", "/").lower()}/'
        options['display_field'] = 'nom'

    mapping_kwargs = {
        'form_config': configuration,
        'source_model': source_model,
        'field_name': field_name,
        'widget_type': widget_type,
        'label': label,
        'help_text': help_text,
        'order': max_order,
        'section': section_id,
    }
    if required is not None:
        mapping_kwargs['required'] = required
    if max_length:
        mapping_kwargs['max_length'] = max_length
    if options:
        mapping_kwargs['options'] = options

    ModelFieldMapping.objects.create(**mapping_kwargs)

    response = _builder_sections_response(request, configuration)
    response['HX-Trigger'] = 'previewUpdated, catalogueUpdated'
    return response


@login_required
@require_http_methods(['GET', 'POST'])
@permission_required_business('modelforms.change_configuration')
def builder_field_config(request, pk, mapping_pk):
    """GET: formulaire inline de config du champ. POST: sauvegarde."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)
    mapping = get_object_or_404(ModelFieldMapping, pk=mapping_pk, form_config=configuration)

    # Determine compatible widgets from model introspection
    compatible_widgets = None
    try:
        introspector = ModelIntrospector(mapping.source_model)
        for field_info in introspector.get_fields(include_system=True):
            if field_info['name'] == mapping.field_name:
                detected_widget = field_info.get('widget_type', 'text')
                compatible_widgets = ModelFieldMapping.WIDGET_COMPATIBILITY.get(
                    detected_widget, [detected_widget, 'hidden']
                )
                break
    except (ValueError, LookupError):
        pass

    if request.method == 'POST':
        form = BuilderFieldMappingForm(request.POST, instance=mapping, compatible_widgets=compatible_widgets)
        if form.is_valid():
            form.save()
            response = render(request, 'modelforms/partials/builder_field_item.html', {
                'mapping': mapping,
                'configuration': configuration,
            })
            response['HX-Trigger'] = 'previewUpdated'
            return response
    else:
        form = BuilderFieldMappingForm(instance=mapping, compatible_widgets=compatible_widgets)

    return render(request, 'modelforms/partials/builder_field_config.html', {
        'form': form,
        'mapping': mapping,
        'configuration': configuration,
    })


@login_required
@require_http_methods(['DELETE', 'POST'])
@permission_required_business('modelforms.change_configuration')
def builder_delete_field(request, pk, mapping_pk):
    """Supprime un champ. Retourne le panel central."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)
    mapping = get_object_or_404(ModelFieldMapping, pk=mapping_pk, form_config=configuration)
    mapping.delete()

    response = _builder_sections_response(request, configuration)
    response['HX-Trigger'] = 'previewUpdated, catalogueUpdated'
    return response


@login_required
@require_POST
@permission_required_business('modelforms.change_configuration')
def builder_reorder_fields(request, pk):
    """Sauvegarde l'ordre des champs dans une section (Sortable.js)."""
    import json
    configuration = get_object_or_404(FormConfiguration, pk=pk)

    try:
        data = json.loads(request.body)
        items = data if isinstance(data, list) else data.get('items', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    for item in items:
        ModelFieldMapping.objects.filter(
            pk=item['id'],
            form_config=configuration,
        ).update(order=item['order'], section=item.get('section', ''))

    return JsonResponse({'status': 'ok'}, headers={'HX-Trigger': 'previewUpdated'})


@login_required
@permission_required_business('modelforms.change_configuration')
def builder_preview(request, pk):
    """Retourne le rendu HTML du formulaire tel qu'il sera vu par l'utilisateur."""
    configuration = get_object_or_404(FormConfiguration, pk=pk)
    context = _build_form_context(configuration)
    return render(request, 'modelforms/partials/builder_preview.html', context)


def _builder_sections_response(request, configuration):
    """Helper: retourne le panel central mis à jour."""
    field_mappings = list(configuration.field_mappings.all().order_by('order'))
    sections = (configuration.form_schema or {}).get('sections', [])
    fields_by_section = {s['id']: [] for s in sections}
    fields_by_section['_unsectioned'] = []
    for mapping in field_mappings:
        section_id = mapping.section or '_unsectioned'
        if section_id in fields_by_section:
            fields_by_section[section_id].append(mapping)
        else:
            fields_by_section['_unsectioned'].append(mapping)

    return render(request, 'modelforms/partials/builder_sections.html', {
        'configuration': configuration,
        'sections': sections,
        'fields_by_section': fields_by_section,
        'field_mappings': field_mappings,
    })


# =============================================================================
# INTROSPECTION (HTMX)
# =============================================================================

@login_required
@permission_required_business('modelforms.introspect_models')
def introspect_model(request, model_path):
    """Retourne le schéma d'un modèle pour HTMX."""
    try:
        introspector = ModelIntrospector(model_path)
        schema = introspector.get_schema()
        return render(request, 'modelforms/partials/model_schema.html', {
            'schema': schema,
        })
    except ValueError as e:
        return HttpResponse(f'Erreur: {e}', status=400)


# =============================================================================
# TEMPLATES
# =============================================================================

class FormTemplateListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des templates de formulaires."""

    model = FormTemplate
    business_permission = 'modelforms.view_templates'
    template_name = 'modelforms/template_list.html'
    context_object_name = 'templates'

    def get_queryset(self):
        return FormTemplate.objects.filter(is_active=True).order_by('category', 'name')


@login_required
@require_POST
@permission_required_business('modelforms.add_configuration')
def instantiate_template(request, pk):
    """Crée une configuration à partir d'un template."""
    template = get_object_or_404(FormTemplate, pk=pk)
    config_data = template.template_config.copy()

    # Générer un code unique
    base_code = config_data.get('code', template.code)
    counter = 1
    new_code = base_code
    while FormConfiguration.objects.filter(code=new_code).exists():
        new_code = f"{base_code}_{counter}"
        counter += 1

    # Extraire les field_mappings
    field_mappings_data = config_data.pop('field_mappings', [])

    # Créer la configuration
    config = FormConfiguration.objects.create(
        code=new_code,
        name=config_data.get('name', template.name),
        description=config_data.get('description', template.description),
        category=config_data.get('category', template.category),
        target_model=config_data.get('target_model', ''),
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

    messages.success(request, _('Configuration créée à partir du template.'))
    return redirect('modelforms:configuration-detail', pk=config.pk)


# =============================================================================
# SOUMISSIONS
# =============================================================================

class FormSubmissionListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des soumissions de formulaires."""

    model = FormSubmission
    business_permission = 'modelforms.view_submissions'
    template_name = 'modelforms/submission_list.html'
    context_object_name = 'submissions'
    paginate_by = 30

    def get_queryset(self):
        queryset = FormSubmission.objects.select_related(
            'form_config',
            'submitted_by',
            'validated_by',
            'mandat',
        ).order_by('-submitted_at')

        # SECURITE: mandat-scoping (ses propres + celles sur ses mandats)
        queryset = scope_form_submissions_by_user(queryset, self.request.user)

        # Filtres
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        form_config = self.request.GET.get('form_config')
        if form_config:
            queryset = queryset.filter(form_config_id=form_config)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'total': FormSubmission.objects.count(),
            'pending': FormSubmission.objects.filter(status='PENDING').count(),
            'completed': FormSubmission.objects.filter(status='COMPLETED').count(),
            'failed': FormSubmission.objects.filter(status='FAILED').count(),
        }
        context['statuses'] = FormSubmission.Status.choices
        context['configurations'] = FormConfiguration.objects.filter(status='ACTIVE')
        return context


class FormSubmissionDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une soumission."""

    model = FormSubmission
    business_permission = 'modelforms.view_submissions'
    template_name = 'modelforms/submission_detail.html'
    context_object_name = 'submission'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'form_config',
            'submitted_by',
            'validated_by',
            'mandat',
        )
        # SECURITE: mandat-scoping
        return scope_form_submissions_by_user(queryset, self.request.user)

    def get_context_data(self, **kwargs):
        import json
        context = super().get_context_data(**kwargs)
        context['submitted_data'] = self.object.submitted_data or {}
        context['raw_json'] = json.dumps(self.object.submitted_data or {}, indent=2, ensure_ascii=False)
        return context


@login_required
@require_POST
@permission_required_business('modelforms.validate_submission')
def validate_submission(request, pk):
    """Valide une soumission en attente."""
    # SECURITE: on recupere la soumission dans le queryset filtre par mandats.
    # Un manager de mandat A ne doit pas pouvoir valider une soumission
    # attachee uniquement au mandat B.
    scoped = scope_form_submissions_by_user(
        FormSubmission.objects.all(),
        request.user,
    )
    submission = get_object_or_404(scoped, pk=pk)

    if submission.status != FormSubmission.Status.PENDING:
        messages.error(request, _('Seules les soumissions en attente peuvent être validées.'))
        return redirect('modelforms:submission-detail', pk=pk)

    notes = request.POST.get('notes', '')

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
        if handler.post_action_errors:
            submission.error_details = {
                'post_actions': handler.post_action_errors,
            }
        submission.save()
        if handler.post_action_errors:
            messages.warning(
                request,
                _("Soumission validée, mais %(pa)d action(s) post-soumission ont échoué.")
                % {'pa': len(handler.post_action_errors)},
            )
        else:
            messages.success(request, _('Soumission validée et enregistrements créés.'))
    else:
        submission.status = FormSubmission.Status.FAILED
        submission.error_message = '; '.join(errors)
        submission.error_details = {'errors': errors}
        submission.save()
        messages.error(request, _('Échec de la validation: ') + '; '.join(errors))

    return redirect('modelforms:submission-detail', pk=pk)


@login_required
@require_POST
@permission_required_business('modelforms.reject_submission')
def reject_submission(request, pk):
    """Rejette une soumission en attente."""
    # SECURITE: idem validate_submission, on scope par mandats accessibles.
    scoped = scope_form_submissions_by_user(
        FormSubmission.objects.all(),
        request.user,
    )
    submission = get_object_or_404(scoped, pk=pk)

    if submission.status != FormSubmission.Status.PENDING:
        messages.error(request, _('Seules les soumissions en attente peuvent être rejetées.'))
        return redirect('modelforms:submission-detail', pk=pk)

    reason = request.POST.get('validation_notes', '')
    if not reason:
        messages.error(request, _('Une raison de rejet est requise.'))
        return redirect('modelforms:submission-detail', pk=pk)

    submission.status = FormSubmission.Status.REJECTED
    submission.validated_by = request.user
    submission.validated_at = timezone.now()
    submission.validation_notes = reason
    submission.save()

    messages.success(request, _('Soumission rejetée.'))
    return redirect('modelforms:submission-detail', pk=pk)


# =============================================================================
# DUPLICATION
# =============================================================================

@login_required
@require_POST
@permission_required_business('modelforms.add_configuration')
def duplicate_configuration(request, pk):
    """Duplique une configuration existante."""
    original = get_object_or_404(FormConfiguration, pk=pk)

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

    messages.success(request, _('Configuration dupliquée avec succès.'))
    return redirect('modelforms:configuration-detail', pk=new_config.pk)


# =============================================================================
# REMPLISSAGE DE FORMULAIRES (pour les utilisateurs finaux)
# =============================================================================

class AvailableFormsListView(LoginRequiredMixin, ListView):
    """Liste des formulaires disponibles à remplir."""

    model = FormConfiguration
    template_name = 'modelforms/available_forms_list.html'
    context_object_name = 'forms'

    def get_queryset(self):
        """Retourne uniquement les formulaires actifs accessibles par l'utilisateur."""
        queryset = FormConfiguration.objects.filter(
            status=FormConfiguration.Status.ACTIVE
        ).order_by('category', 'name')
        # SECURITE: mandat-scoping
        return scope_form_configs_by_user(queryset, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Grouper par catégorie (category est un CharField libre)
        forms_by_category = {}
        for form in context['forms']:
            cat = form.category or _('Autre')
            if cat not in forms_by_category:
                forms_by_category[cat] = []
            forms_by_category[cat].append(form)
        context['forms_by_category'] = forms_by_category
        return context


class FormFillView(LoginRequiredMixin, DetailView):
    """Affiche un formulaire dynamique à remplir."""

    model = FormConfiguration
    template_name = 'modelforms/form_fill.html'
    context_object_name = 'form_config'

    def get_queryset(self):
        """Seuls les formulaires actifs accessibles par l'utilisateur peuvent etre remplis."""
        queryset = FormConfiguration.objects.filter(
            status=FormConfiguration.Status.ACTIVE
        )
        # SECURITE: mandat-scoping
        return scope_form_configs_by_user(queryset, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = self.object

        # Récupérer les mappings de champs ordonnés
        field_mappings = config.field_mappings.all().order_by('order')
        context['field_mappings'] = field_mappings

        # Grouper les champs par section si form_schema est défini
        sections = config.form_schema.get('sections', [])
        if sections:
            # Créer un dictionnaire de champs par section
            fields_by_section = {s['id']: [] for s in sections}
            fields_by_section['other'] = []  # Champs sans section

            for mapping in field_mappings:
                section_id = mapping.section or 'other'
                if section_id in fields_by_section:
                    fields_by_section[section_id].append(mapping)
                else:
                    fields_by_section['other'].append(mapping)

            context['sections'] = sections
            context['fields_by_section'] = fields_by_section
        else:
            context['sections'] = []
            context['fields_by_section'] = {'all': list(field_mappings)}

        # Valeurs par défaut avec résolution des variables
        default_values = self._resolve_default_values(config.default_values)
        context['default_values'] = default_values

        # Générer le schéma JSON pour le frontend (si multi-modèle)
        if config.is_multi_model:
            context['source_models'] = config.source_models

        # Mandats accessibles pour le sélecteur
        user = self.request.user
        if hasattr(user, 'get_accessible_mandats'):
            accessible_mandats = user.get_accessible_mandats()
            # Filtrer sur les mandats associés au formulaire si définis
            config_mandats = config.mandats.all()
            if config_mandats.exists():
                accessible_mandats = accessible_mandats.filter(pk__in=config_mandats)
            context['accessible_mandats'] = accessible_mandats

        return context

    def _resolve_default_values(self, default_values):
        """Résout les variables dynamiques dans les valeurs par défaut."""
        from django.utils import timezone
        import re

        resolved = {}
        user = self.request.user

        for key, value in default_values.items():
            if isinstance(value, str):
                # Remplacer les variables
                value = value.replace('{{today}}', timezone.now().strftime('%Y-%m-%d'))
                value = value.replace('{{now}}', timezone.now().strftime('%Y-%m-%dT%H:%M'))
                value = value.replace('{{current_user}}', str(user.pk))
                value = value.replace('{{current_user.id}}', str(user.pk))
                value = value.replace('{{current_user.username}}', user.username)
                if hasattr(user, 'get_full_name'):
                    value = value.replace('{{current_user.full_name}}', user.get_full_name())
            resolved[key] = value

        return resolved


@login_required
@require_http_methods(['POST'])
def submit_form(request, pk):
    """Traite la soumission d'un formulaire."""
    config = get_object_or_404(
        FormConfiguration,
        pk=pk,
        status=FormConfiguration.Status.ACTIVE
    )

    # SECURITE: verifier que l'utilisateur a acces a cette config
    if not user_can_access_form_config(request.user, config):
        messages.error(
            request,
            _("Vous n'avez pas acces a ce formulaire.")
        )
        return redirect('modelforms:available-forms')

    # Récupérer les données du formulaire
    import json

    # Gérer les données JSON ou POST standard
    if request.content_type == 'application/json':
        try:
            submitted_data = json.loads(request.body)
        except json.JSONDecodeError:
            messages.error(request, _('Données JSON invalides.'))
            return redirect('modelforms:form-fill', pk=pk)
    else:
        # Convertir POST en dictionnaire
        submitted_data = {}
        for key in request.POST:
            if key != 'csrfmiddlewaretoken':
                values = request.POST.getlist(key)
                submitted_data[key] = values[0] if len(values) == 1 else values

    # Récupérer le mandat si présent
    mandat_id = submitted_data.pop('mandat', None)
    mandat = None
    if mandat_id:
        from core.models import Mandat
        try:
            mandat = Mandat.objects.get(pk=mandat_id)
        except Mandat.DoesNotExist:
            mandat = None

        # SECURITE: un utilisateur ne peut pas attacher une soumission a un
        # mandat auquel il n'a pas acces (faille d'escalade de privilege).
        if mandat is not None and not user_can_access_mandat(request.user, mandat):
            messages.error(
                request,
                _("Vous n'avez pas acces au mandat selectionne.")
            )
            return redirect('modelforms:form-fill', pk=pk)

    # Créer la soumission
    submission = FormSubmission.objects.create(
        form_config=config,
        submitted_data=submitted_data,
        submitted_by=request.user,
        mandat=mandat,
        status=FormSubmission.Status.PENDING if config.require_validation else FormSubmission.Status.PROCESSING,
    )

    # Si validation requise, on s'arrête là
    if config.require_validation:
        messages.success(
            request,
            _('Formulaire soumis avec succès. En attente de validation.')
        )
        return redirect('modelforms:submission-detail', pk=submission.pk)

    # Sinon, traiter immédiatement
    handler = SubmissionHandler(
        form_config=config,
        submitted_data=submitted_data,
        user=request.user,
        mandat=mandat,
    )

    success, records, errors = handler.process()

    if success:
        submission.status = FormSubmission.Status.COMPLETED
        submission.created_records = records
        # Enregistrer les erreurs non-bloquantes des post_actions (si existent)
        if handler.post_action_errors:
            submission.error_details = {
                'post_actions': handler.post_action_errors,
            }
        submission.save()
        if handler.post_action_errors:
            messages.warning(
                request,
                _(
                    "Formulaire traité (%(count)d enregistrement(s)) mais "
                    "%(pa)d action(s) post-soumission ont échoué (voir détail)."
                ) % {'count': len(records), 'pa': len(handler.post_action_errors)}
            )
        else:
            messages.success(
                request,
                _('Formulaire traité avec succès. %(count)d enregistrement(s) créé(s).') % {'count': len(records)}
            )
    else:
        submission.status = FormSubmission.Status.FAILED
        submission.error_message = '; '.join(errors)
        submission.error_details = {'errors': errors}
        submission.save()
        messages.error(
            request,
            _('Erreur lors du traitement: %(errors)s') % {'errors': '; '.join(errors)}
        )

    return redirect('modelforms:submission-detail', pk=submission.pk)


@login_required
@require_POST
@permission_required_business('modelforms.change_configuration')
def reorder_fields(request, pk):
    """Sauvegarde le nouvel ordre des champs (AJAX)."""
    import json
    configuration = get_object_or_404(FormConfiguration, pk=pk)

    try:
        data = json.loads(request.body)
        order_list = data.get('order', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    for item in order_list:
        ModelFieldMapping.objects.filter(
            pk=item['id'],
            form_config=configuration,
        ).update(order=item['order'])

    return JsonResponse({'status': 'ok'})


@login_required
def get_field_options(request, model_path):
    """Retourne les options HTML pour un select de champs (HTMX)."""
    try:
        introspector = ModelIntrospector(model_path)
        fields = introspector.get_fields()

        options_html = '<option value="">-- Sélectionner un champ --</option>'
        for field in fields:
            options_html += f'<option value="{field["name"]}">{field["verbose_name"]} ({field["name"]})</option>'

        return HttpResponse(options_html)
    except ValueError as e:
        return HttpResponse(f'<option value="">Erreur: {e}</option>')


# =============================================================================
# FORMULAIRES PUBLICS (pas de login requis)
# =============================================================================

def _get_public_config(token):
    """Récupère une configuration publique active par son token."""
    return get_object_or_404(
        FormConfiguration,
        public_token=token,
        status=FormConfiguration.Status.ACTIVE,
    )


def _build_form_context(config):
    """Construit le contexte commun pour le rendu d'un formulaire (sections, champs, défauts)."""
    field_mappings = config.field_mappings.all().order_by('order')
    sections = config.form_schema.get('sections', [])
    context = {
        'form_config': config,
        'field_mappings': field_mappings,
    }

    if sections:
        fields_by_section = {s['id']: [] for s in sections}
        fields_by_section['other'] = []
        for mapping in field_mappings:
            section_id = mapping.section or 'other'
            if section_id in fields_by_section:
                fields_by_section[section_id].append(mapping)
            else:
                fields_by_section['other'].append(mapping)
        context['sections'] = sections
        context['fields_by_section'] = fields_by_section
    else:
        context['sections'] = []
        context['fields_by_section'] = {'all': list(field_mappings)}

    # Résoudre les valeurs par défaut (sans variables utilisateur pour le public)
    resolved = {}
    for key, value in config.default_values.items():
        if isinstance(value, str):
            value = value.replace('{{today}}', timezone.now().strftime('%Y-%m-%d'))
            value = value.replace('{{now}}', timezone.now().strftime('%Y-%m-%dT%H:%M'))
        resolved[key] = value
    context['default_values'] = resolved

    return context


class PublicFormFillView(View):
    """Formulaire accessible via token public."""

    def get(self, request, token):
        config = _get_public_config(token)

        # Vérifier le niveau d'accès
        if config.access_level == 'authenticated':
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())

        if config.access_level == 'code':
            session_key = f'form_access_{config.pk}'
            if not request.session.get(session_key):
                return redirect('modelforms:public-form-code', token=token)

        context = _build_form_context(config)
        return render(request, 'modelforms/form_fill_public.html', context)


class PublicFormSubmitView(View):
    """Soumission d'un formulaire public."""

    def post(self, request, token):
        import json as json_module

        config = _get_public_config(token)

        # Vérifier le niveau d'accès
        if config.access_level == 'authenticated':
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())

        if config.access_level == 'code':
            session_key = f'form_access_{config.pk}'
            if not request.session.get(session_key):
                return redirect('modelforms:public-form-code', token=token)

        # Extraire les données
        if request.content_type == 'application/json':
            try:
                submitted_data = json_module.loads(request.body)
            except json_module.JSONDecodeError:
                messages.error(request, _('Données JSON invalides.'))
                return redirect('modelforms:public-form', token=token)
        else:
            submitted_data = {}
            for key in request.POST:
                if key != 'csrfmiddlewaretoken':
                    values = request.POST.getlist(key)
                    submitted_data[key] = values[0] if len(values) == 1 else values

        # Mandat
        mandat_id = submitted_data.pop('mandat', None)
        mandat = None
        if mandat_id:
            from core.models import Mandat
            try:
                mandat = Mandat.objects.get(pk=mandat_id)
            except Mandat.DoesNotExist:
                pass

        # Utilisateur (null si anonyme)
        user = request.user if request.user.is_authenticated else None

        # Créer la soumission
        submission = FormSubmission.objects.create(
            form_config=config,
            submitted_data=submitted_data,
            submitted_by=user,
            mandat=mandat,
            status=FormSubmission.Status.PENDING if config.require_validation else FormSubmission.Status.PROCESSING,
        )

        # Si validation requise, rediriger vers succès
        if config.require_validation:
            return redirect('modelforms:public-form-success', token=token)

        # Sinon, traiter immédiatement
        handler = SubmissionHandler(
            form_config=config,
            submitted_data=submitted_data,
            user=user,
            mandat=mandat,
        )

        success, records, errors = handler.process()

        if success:
            submission.status = FormSubmission.Status.COMPLETED
            submission.created_records = records
            submission.save()
        else:
            submission.status = FormSubmission.Status.FAILED
            submission.error_message = '; '.join(errors)
            submission.error_details = {'errors': errors}
            submission.save()

        return redirect('modelforms:public-form-success', token=token)


class PublicFormSuccessView(View):
    """Page de succès après soumission d'un formulaire public."""

    def get(self, request, token):
        config = _get_public_config(token)
        return render(request, 'modelforms/form_fill_success.html', {
            'form_config': config,
            'success_message': config.success_message,
        })


class AccessCodeView(View):
    """Vérifie le code d'accès pour les formulaires protégés."""

    def get(self, request, token):
        config = _get_public_config(token)
        if config.access_level != 'code':
            return redirect('modelforms:public-form', token=token)
        return render(request, 'modelforms/form_access_code.html', {
            'form_config': config,
        })

    def post(self, request, token):
        config = _get_public_config(token)
        if config.access_level != 'code':
            return redirect('modelforms:public-form', token=token)

        code = request.POST.get('access_code', '').strip()
        if code == config.access_code:
            request.session[f'form_access_{config.pk}'] = True
            return redirect('modelforms:public-form', token=token)

        return render(request, 'modelforms/form_access_code.html', {
            'form_config': config,
            'error': _('Code d\'accès incorrect. Veuillez réessayer.'),
        })


class FormQRCodeView(LoginRequiredMixin, View):
    """Génère le QR code PNG d'un formulaire (téléchargement)."""

    def get(self, request, pk):
        config = get_object_or_404(FormConfiguration, pk=pk)
        public_url = request.build_absolute_uri(
            reverse('modelforms:public-form', kwargs={'token': config.public_token})
        )

        from .services.qr_service import generate_qr_code
        png_bytes = generate_qr_code(public_url)

        response = HttpResponse(png_bytes, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="qrcode-{config.code}.png"'
        return response


# =============================================================================
# Process Engine Views (PR2)
# =============================================================================
#
# Vues HTMX minimales pour Phase 1: liste, detail, creation/edition en JSON,
# suppression, publication et nouvelle version. L'editeur drag-and-drop
# (django-d3-bridge Force Graph) arrive en PR4.
# =============================================================================


class ProcessDefinitionListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des definitions de processus metiers."""

    model = ProcessDefinition
    business_permission = 'modelforms.view_configurations'
    template_name = 'modelforms/process_list.html'
    context_object_name = 'processes'
    paginate_by = 30

    def get_queryset(self):
        queryset = ProcessDefinition.objects.prefetch_related(
            'steps', 'mandats',
        ).order_by('category', 'name', '-version')

        # SECURITE: mandat-scoping
        queryset = scope_process_definitions_by_user(queryset, self.request.user)

        # Filtres optionnels
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)

        show_drafts = self.request.GET.get('drafts') == '1'
        if not show_drafts and not self.request.user.is_manager():
            queryset = queryset.filter(is_draft=False)

        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(code__icontains=q) | Q(name__icontains=q)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ProcessDefinition.Category.choices
        context['stats'] = {
            'total': ProcessDefinition.objects.count(),
            'published': ProcessDefinition.objects.filter(is_draft=False).count(),
            'drafts': ProcessDefinition.objects.filter(is_draft=True).count(),
            'instances': ProcessInstance.objects.count(),
        }
        return context


class ProcessDefinitionDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Detail d'une definition de processus."""

    model = ProcessDefinition
    business_permission = 'modelforms.view_configurations'
    template_name = 'modelforms/process_detail.html'
    context_object_name = 'process'

    def get_queryset(self):
        return scope_process_definitions_by_user(
            ProcessDefinition.objects.prefetch_related(
                'steps', 'mandats',
            ),
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        import json
        context = super().get_context_data(**kwargs)
        process = self.object
        context['steps'] = process.steps.all().order_by('order', 'code')
        context['transitions'] = ProcessTransition.objects.filter(
            from_step__process=process,
        ).select_related('from_step', 'to_step').order_by('from_step__order', 'order')
        context['recent_instances'] = process.instances.order_by(
            '-created_at',
        )[:10]
        context['steps_json'] = json.dumps(
            [
                {
                    'code': s.code,
                    'name': s.name,
                    'step_type': s.step_type,
                    'configuration': s.configuration,
                    'conditions': s.conditions,
                    'order': s.order,
                    'position_x': s.position_x,
                    'position_y': s.position_y,
                }
                for s in context['steps']
            ],
            indent=2,
            ensure_ascii=False,
        )
        context['transitions_json'] = json.dumps(
            [
                {
                    'from': t.from_step.code,
                    'to': t.to_step.code,
                    'label': t.label,
                    'condition': t.condition,
                    'order': t.order,
                }
                for t in context['transitions']
            ],
            indent=2,
            ensure_ascii=False,
        )
        return context


def _parse_process_json_fields(request):
    """
    Parse les fields JSON (steps, transitions) depuis le POST.

    Retourne (steps_data, transitions_data, errors) ou (None, None, errors).
    """
    import json

    errors = []
    steps_raw = request.POST.get('steps_json', '[]')
    transitions_raw = request.POST.get('transitions_json', '[]')

    try:
        steps_data = json.loads(steps_raw) if steps_raw.strip() else []
    except json.JSONDecodeError as e:
        errors.append(f"Format JSON steps invalide: {e}")
        steps_data = None

    try:
        transitions_data = json.loads(transitions_raw) if transitions_raw.strip() else []
    except json.JSONDecodeError as e:
        errors.append(f"Format JSON transitions invalide: {e}")
        transitions_data = None

    return steps_data, transitions_data, errors


def _apply_steps_and_transitions(process, steps_data, transitions_data):
    """
    Applique (remplace) les steps et transitions d'un processus.

    Supprime les anciens et recree a partir des donnees JSON.
    """
    from django.db import transaction

    with transaction.atomic():
        ProcessTransition.objects.filter(from_step__process=process).delete()
        process.steps.all().delete()

        step_map = {}  # code → instance
        for s in steps_data or []:
            step = ProcessStep.objects.create(
                process=process,
                code=s.get('code', ''),
                name=s.get('name', s.get('code', '')),
                description=s.get('description', ''),
                step_type=s.get('step_type', 'START'),
                configuration=s.get('configuration', {}),
                order=s.get('order', 0),
                conditions=s.get('conditions', {}),
                max_retries=s.get('max_retries', 0),
                retry_delay_seconds=s.get('retry_delay_seconds', 60),
                timeout_seconds=s.get('timeout_seconds'),
                position_x=s.get('position_x', 0),
                position_y=s.get('position_y', 0),
            )
            step_map[step.code] = step

        for t in transitions_data or []:
            from_code = t.get('from')
            to_code = t.get('to')
            if from_code not in step_map or to_code not in step_map:
                continue
            ProcessTransition.objects.create(
                from_step=step_map[from_code],
                to_step=step_map[to_code],
                label=t.get('label', ''),
                condition=t.get('condition', {}),
                order=t.get('order', 0),
            )


class ProcessDefinitionCreateView(LoginRequiredMixin, BusinessPermissionMixin, View):
    """Creation d'une definition de processus."""

    business_permission = 'modelforms.add_configuration'

    def get(self, request):
        return render(request, 'modelforms/process_form.html', {
            'process': None,
            'steps_json': '[]',
            'transitions_json': '[]',
            'categories': ProcessDefinition.Category.choices,
            'step_types': ProcessStep.StepType.choices,
        })

    def post(self, request):
        code = request.POST.get('code', '').strip()
        name = request.POST.get('name', '').strip()
        if not code or not name:
            messages.error(request, _('Le code et le nom sont obligatoires.'))
            return redirect('modelforms:process-create')

        if ProcessDefinition.objects.filter(code=code, version=1).exists():
            messages.error(
                request,
                _("Un processus avec le code '%(code)s' et version 1 existe déjà.") % {'code': code},
            )
            return redirect('modelforms:process-create')

        steps_data, transitions_data, errors = _parse_process_json_fields(request)
        if errors:
            for err in errors:
                messages.error(request, err)
            return redirect('modelforms:process-create')

        process = ProcessDefinition.objects.create(
            code=code,
            name=name,
            description=request.POST.get('description', ''),
            category=request.POST.get('category', 'WORKFLOW'),
            icon=request.POST.get('icon', 'ph-flow-arrow'),
            version=1,
            is_draft=True,
            created_by=request.user,
        )

        _apply_steps_and_transitions(process, steps_data, transitions_data)

        messages.success(request, _('Processus créé avec succès.'))
        return redirect('modelforms:process-detail', pk=process.pk)


class ProcessDefinitionUpdateView(LoginRequiredMixin, BusinessPermissionMixin, View):
    """Modification d'une definition de processus."""

    business_permission = 'modelforms.change_configuration'

    def _get_object(self, request, pk):
        return get_object_or_404(
            scope_process_definitions_by_user(
                ProcessDefinition.objects.all(), request.user,
            ),
            pk=pk,
        )

    def get(self, request, pk):
        import json
        process = self._get_object(request, pk)
        steps = process.steps.all().order_by('order', 'code')
        transitions = ProcessTransition.objects.filter(
            from_step__process=process,
        ).select_related('from_step', 'to_step').order_by('order')

        steps_json = json.dumps(
            [
                {
                    'code': s.code,
                    'name': s.name,
                    'description': s.description,
                    'step_type': s.step_type,
                    'configuration': s.configuration,
                    'conditions': s.conditions,
                    'order': s.order,
                    'max_retries': s.max_retries,
                    'retry_delay_seconds': s.retry_delay_seconds,
                    'timeout_seconds': s.timeout_seconds,
                    'position_x': s.position_x,
                    'position_y': s.position_y,
                }
                for s in steps
            ],
            indent=2,
            ensure_ascii=False,
        )
        transitions_json = json.dumps(
            [
                {
                    'from': t.from_step.code,
                    'to': t.to_step.code,
                    'label': t.label,
                    'condition': t.condition,
                    'order': t.order,
                }
                for t in transitions
            ],
            indent=2,
            ensure_ascii=False,
        )

        return render(request, 'modelforms/process_form.html', {
            'process': process,
            'steps_json': steps_json,
            'transitions_json': transitions_json,
            'categories': ProcessDefinition.Category.choices,
            'step_types': ProcessStep.StepType.choices,
        })

    def post(self, request, pk):
        process = self._get_object(request, pk)

        if not process.is_draft:
            messages.error(
                request,
                _("Impossible de modifier une version publiée. Créez une nouvelle version."),
            )
            return redirect('modelforms:process-detail', pk=process.pk)

        process.name = request.POST.get('name', process.name)
        process.description = request.POST.get('description', process.description)
        process.category = request.POST.get('category', process.category)
        process.icon = request.POST.get('icon', process.icon)
        process.save()

        steps_data, transitions_data, errors = _parse_process_json_fields(request)
        if errors:
            for err in errors:
                messages.error(request, err)
            return redirect('modelforms:process-update', pk=pk)

        _apply_steps_and_transitions(process, steps_data, transitions_data)

        messages.success(request, _('Processus mis à jour.'))
        return redirect('modelforms:process-detail', pk=process.pk)


class ProcessDefinitionDeleteView(LoginRequiredMixin, BusinessPermissionMixin, View):
    """Suppression d'une definition de processus."""

    business_permission = 'modelforms.delete_configuration'

    def post(self, request, pk):
        process = get_object_or_404(
            scope_process_definitions_by_user(
                ProcessDefinition.objects.all(), request.user,
            ),
            pk=pk,
        )
        if process.instances.exists():
            messages.error(
                request,
                _("Impossible de supprimer un processus qui a des instances."),
            )
            return redirect('modelforms:process-detail', pk=pk)

        process.delete()
        messages.success(request, _('Processus supprimé.'))
        return redirect('modelforms:process-list')


@login_required
@require_POST
@permission_required_business('modelforms.change_configuration')
def process_publish(request, pk):
    """Publie un processus (is_draft=False)."""
    process = get_object_or_404(
        scope_process_definitions_by_user(
            ProcessDefinition.objects.all(), request.user,
        ),
        pk=pk,
    )
    if not process.is_draft:
        messages.info(request, _('Ce processus est déjà publié.'))
    else:
        if not process.steps.exists():
            messages.error(
                request,
                _("Impossible de publier un processus sans aucune étape."),
            )
            return redirect('modelforms:process-detail', pk=pk)
        process.is_draft = False
        process.save(update_fields=['is_draft', 'updated_at'])
        messages.success(request, _('Processus publié.'))
    return redirect('modelforms:process-detail', pk=pk)


@login_required
@require_POST
@permission_required_business('modelforms.add_configuration')
def process_new_version(request, pk):
    """Crée une nouvelle version draft à partir d'un processus existant."""
    from django.db import transaction

    source = get_object_or_404(
        scope_process_definitions_by_user(
            ProcessDefinition.objects.all(), request.user,
        ),
        pk=pk,
    )

    with transaction.atomic():
        latest_version = ProcessDefinition.objects.filter(
            code=source.code,
        ).order_by('-version').values_list('version', flat=True).first()
        new_version_num = (latest_version or source.version) + 1

        new_def = ProcessDefinition.objects.create(
            code=source.code,
            name=source.name,
            description=source.description,
            category=source.category,
            version=new_version_num,
            is_draft=True,
            icon=source.icon,
            created_by=request.user,
        )
        new_def.mandats.set(source.mandats.all())

        step_map = {}
        for old_step in source.steps.all():
            new_step = ProcessStep.objects.create(
                process=new_def,
                code=old_step.code,
                name=old_step.name,
                description=old_step.description,
                step_type=old_step.step_type,
                configuration=old_step.configuration,
                order=old_step.order,
                conditions=old_step.conditions,
                max_retries=old_step.max_retries,
                retry_delay_seconds=old_step.retry_delay_seconds,
                timeout_seconds=old_step.timeout_seconds,
                position_x=old_step.position_x,
                position_y=old_step.position_y,
            )
            step_map[old_step.pk] = new_step

        for old_step in source.steps.all():
            for old_trans in old_step.outgoing_transitions.all():
                ProcessTransition.objects.create(
                    from_step=step_map[old_trans.from_step_id],
                    to_step=step_map[old_trans.to_step_id],
                    label=old_trans.label,
                    condition=old_trans.condition,
                    order=old_trans.order,
                )

    messages.success(
        request,
        _('Nouvelle version %(v)d créée (brouillon).') % {'v': new_version_num},
    )
    return redirect('modelforms:process-update', pk=new_def.pk)


class ProcessInstanceListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des instances de processus (historique d'exécutions)."""

    model = ProcessInstance
    business_permission = 'modelforms.view_submissions'
    template_name = 'modelforms/process_instance_list.html'
    context_object_name = 'instances'
    paginate_by = 30

    def get_queryset(self):
        queryset = ProcessInstance.objects.select_related(
            'process_def', 'current_step', 'triggered_by', 'mandat',
        ).order_by('-created_at')
        queryset = scope_process_instances_by_user(queryset, self.request.user)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = ProcessInstance.Status.choices
        return context


class ProcessInstanceDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une instance de processus avec son historique d'exécutions."""

    model = ProcessInstance
    business_permission = 'modelforms.view_submissions'
    template_name = 'modelforms/process_instance_detail.html'
    context_object_name = 'instance'

    def get_queryset(self):
        return scope_process_instances_by_user(
            ProcessInstance.objects.select_related(
                'process_def', 'current_step', 'triggered_by', 'mandat',
            ).prefetch_related('step_executions__step', 'step_executions__form_submission'),
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        import json
        context = super().get_context_data(**kwargs)
        instance = self.object
        process = instance.process_def
        executions = instance.step_executions.all().order_by('created_at')
        context['executions'] = executions
        context['variables_pretty'] = json.dumps(
            instance.variables, indent=2, ensure_ascii=False,
        )

        # Graph data for live Force Graph
        steps = process.steps.all().order_by('order', 'code')
        transitions = ProcessTransition.objects.filter(
            from_step__process=process,
        ).select_related('from_step', 'to_step')

        exec_status = {}
        for ex in executions:
            exec_status[ex.step.code] = ex.status

        context['graph_steps_json'] = json.dumps([
            {
                'code': s.code,
                'name': s.name,
                'step_type': s.step_type,
                'order': s.order,
                'position_x': s.position_x,
                'position_y': s.position_y,
                'status': exec_status.get(s.code, 'PENDING'),
                'is_current': (instance.current_step_id == s.pk),
            }
            for s in steps
        ], ensure_ascii=False)

        context['graph_transitions_json'] = json.dumps([
            {
                'from': t.from_step.code,
                'to': t.to_step.code,
                'label': t.label or '',
            }
            for t in transitions
        ], ensure_ascii=False)

        return context
