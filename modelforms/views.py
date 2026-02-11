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
from .models import FormConfiguration, ModelFieldMapping, FormSubmission, FormTemplate
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

    # Introspection du modèle
    try:
        introspector = ModelIntrospector(configuration.target_model)
        model_fields = introspector.get_fields()
        suggested_groups = introspector.get_suggested_groups()
    except ValueError:
        model_fields = []
        suggested_groups = []

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
    import re
    configuration = get_object_or_404(FormConfiguration, pk=pk)
    title = request.POST.get('title', '').strip()
    icon = request.POST.get('icon', '').strip()

    if not title:
        return HttpResponse('Titre requis', status=400)

    # Générer un id: slugify
    section_id = re.sub(r'[^a-z0-9]+', '_', title.lower().strip('_'))
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

    # Détecter le widget_type via introspector
    widget_type = 'text'
    label = field_name
    try:
        introspector = ModelIntrospector(source_model)
        for field_info in introspector.get_fields(include_system=True):
            if field_info['name'] == field_name:
                widget_type = field_info.get('widget_type', 'text')
                label = field_info.get('label', field_name)
                break
    except ValueError:
        pass

    # Ordre: après le dernier champ
    max_order = configuration.field_mappings.count()

    ModelFieldMapping.objects.create(
        form_config=configuration,
        source_model=source_model,
        field_name=field_name,
        widget_type=widget_type,
        label=label,
        order=max_order,
        section=section_id,
    )

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

    if request.method == 'POST':
        form = BuilderFieldMappingForm(request.POST, instance=mapping)
        if form.is_valid():
            form.save()
            # Retourner la ligne compacte du champ
            response = render(request, 'modelforms/partials/builder_field_item.html', {
                'mapping': mapping,
                'configuration': configuration,
            })
            response['HX-Trigger'] = 'previewUpdated'
            return response
    else:
        form = BuilderFieldMappingForm(instance=mapping)

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
        ).order_by('-submitted_at')

        # Non-managers ne voient que leurs soumissions
        if not self.request.user.is_manager():
            queryset = queryset.filter(submitted_by=self.request.user)

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
        # Non-managers ne voient que leurs soumissions
        if not self.request.user.is_manager():
            queryset = queryset.filter(submitted_by=self.request.user)
        return queryset

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
    submission = get_object_or_404(FormSubmission, pk=pk)

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
        submission.save()
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
    submission = get_object_or_404(FormSubmission, pk=pk)

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
        """Retourne uniquement les formulaires actifs."""
        return FormConfiguration.objects.filter(
            status=FormConfiguration.Status.ACTIVE
        ).order_by('category', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Grouper par catégorie
        forms_by_category = {}
        for form in context['forms']:
            category_display = form.get_category_display()
            if category_display not in forms_by_category:
                forms_by_category[category_display] = []
            forms_by_category[category_display].append(form)
        context['forms_by_category'] = forms_by_category
        context['categories'] = FormConfiguration.Category.choices
        return context


class FormFillView(LoginRequiredMixin, DetailView):
    """Affiche un formulaire dynamique à remplir."""

    model = FormConfiguration
    template_name = 'modelforms/form_fill.html'
    context_object_name = 'form_config'

    def get_queryset(self):
        """Seuls les formulaires actifs peuvent être remplis."""
        return FormConfiguration.objects.filter(
            status=FormConfiguration.Status.ACTIVE
        )

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
            pass

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
        submission.save()
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
