# apps/modelforms/forms.py
"""
Formulaires Django pour la gestion des configurations de formulaires dynamiques.

Supporte les formulaires multi-modèles avec champs provenant de différentes apps.
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import FormConfiguration, ModelFieldMapping, FormTemplate
from .services.introspector import ModelIntrospector


class FormConfigurationForm(forms.ModelForm):
    """Formulaire pour créer/modifier une configuration de formulaire."""

    target_model = forms.ChoiceField(
        label=_('Modèle cible'),
        choices=[],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': _('Rechercher un modèle...'),
        }),
        help_text=_('Sélectionnez le modèle Django principal (optionnel pour multi-modèles)')
    )

    class Meta:
        model = FormConfiguration
        fields = [
            'code',
            'name',
            'description',
            'category',
            'is_multi_model',
            'target_model',
            'icon',
            'status',
            'require_validation',
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CLIENT_RAPIDE',
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Création rapide client'),
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Description du formulaire...'),
            }),
            'category': forms.Select(attrs={
                'class': 'form-select select-basic',
            }),
            'is_multi_model': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-bs-toggle': 'collapse',
                'data-bs-target': '#multiModelOptions',
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ph-file-text',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select select-basic',
            }),
            'require_validation': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Construire les choix de modèles depuis l'introspection
        model_choices = [('', _('-- Sélectionner un modèle --'))]
        for model_info in ModelIntrospector.get_allowed_models():
            model_choices.append((model_info['path'], f"{model_info['verbose_name']} ({model_info['path']})"))
        self.fields['target_model'].choices = model_choices

    def clean(self):
        cleaned_data = super().clean()
        is_multi_model = cleaned_data.get('is_multi_model', False)
        target_model = cleaned_data.get('target_model', '')

        # Pour un formulaire mono-modèle, target_model est requis
        if not is_multi_model and not target_model:
            self.add_error('target_model', _('Le modèle cible est requis pour un formulaire mono-modèle'))

        return cleaned_data


class FormConfigurationAdvancedForm(forms.ModelForm):
    """Formulaire avancé pour la configuration JSON."""

    class Meta:
        model = FormConfiguration
        fields = [
            'source_models',
            'related_models',
            'form_schema',
            'default_values',
            'validation_rules',
            'post_actions',
        ]
        widgets = {
            'source_models': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 4,
                'placeholder': '["core.Client", "core.Contact", "tva.Declaration"]',
            }),
            'related_models': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 6,
                'placeholder': '[]',
            }),
            'form_schema': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 10,
                'placeholder': '{"sections": []}',
            }),
            'default_values': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 6,
                'placeholder': '{}',
            }),
            'validation_rules': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 6,
                'placeholder': '[]',
            }),
            'post_actions': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 6,
                'placeholder': '[]',
            }),
        }


class ModelFieldMappingForm(forms.ModelForm):
    """Formulaire pour personnaliser un champ."""

    source_model = forms.ChoiceField(
        label=_('Modèle source'),
        choices=[],
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': _('Rechercher un modèle...'),
        }),
        help_text=_('Modèle Django d\'où provient le champ')
    )

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
            'order',
            'section',
        ]
        widgets = {
            'field_name': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': _('Rechercher un champ...'),
            }),
            'field_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('adresse_siege.rue (optionnel)'),
            }),
            'widget_type': forms.Select(attrs={
                'class': 'form-select select-basic',
            }),
            'label': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'help_text': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'placeholder': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'required': forms.Select(
                choices=[(None, _('Par défaut')), (True, _('Oui')), (False, _('Non'))],
                attrs={'class': 'form-select select-basic'}
            ),
            'min_value': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'max_value': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'min_length': forms.NumberInput(attrs={
                'class': 'form-control',
            }),
            'max_length': forms.NumberInput(attrs={
                'class': 'form-control',
            }),
            'regex_pattern': forms.TextInput(attrs={
                'class': 'form-control font-monospace',
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'section': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'identity',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Construire les choix de modèles depuis l'introspection
        model_choices = [('', _('-- Sélectionner un modèle --'))]
        for model_info in ModelIntrospector.get_allowed_models():
            model_choices.append((model_info['path'], f"{model_info['verbose_name']} ({model_info['path']})"))
        self.fields['source_model'].choices = model_choices

        # Les choix de field_name seront remplis dynamiquement via AJAX/HTMX
        self.fields['field_name'].widget = forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': _('Sélectionnez d\'abord un modèle...'),
        })


class FieldMappingFormSet(forms.BaseInlineFormSet):
    """FormSet pour gérer plusieurs mappings de champs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# Créer le formset
ModelFieldMappingFormSet = forms.inlineformset_factory(
    FormConfiguration,
    ModelFieldMapping,
    form=ModelFieldMappingForm,
    formset=FieldMappingFormSet,
    extra=1,
    can_delete=True,
)


class FormTemplateSelectForm(forms.Form):
    """Formulaire pour sélectionner un template."""

    template = forms.ModelChoiceField(
        queryset=FormTemplate.objects.filter(is_active=True),
        label=_('Template'),
        widget=forms.Select(attrs={'class': 'form-select select-basic'}),
        empty_label=_('-- Sélectionner un template --'),
    )


class FormSubmissionFilterForm(forms.Form):
    """Formulaire de filtre pour les soumissions."""

    status = forms.ChoiceField(
        required=False,
        label=_('Statut'),
        choices=[('', _('Tous les statuts'))] + list(FormConfiguration.Status.choices),
        widget=forms.Select(attrs={
            'class': 'form-select select-basic',
            'onchange': 'this.form.submit()',
        }),
    )

    form_config = forms.ModelChoiceField(
        required=False,
        queryset=FormConfiguration.objects.filter(status='ACTIVE'),
        label=_('Formulaire'),
        empty_label=_('Tous les formulaires'),
        widget=forms.Select(attrs={
            'class': 'form-select select-basic',
            'onchange': 'this.form.submit()',
        }),
    )


class AddFieldForm(forms.Form):
    """Formulaire pour ajouter un champ au formulaire dynamiquement."""

    source_model = forms.ChoiceField(
        label=_('Modèle source'),
        choices=[],
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'add-field-source-model',
            'hx-get': '/modelforms/api/fields/',
            'hx-trigger': 'change',
            'hx-target': '#add-field-name',
            'hx-swap': 'innerHTML',
        }),
    )

    field_name = forms.ChoiceField(
        label=_('Champ'),
        choices=[('', _('Sélectionnez d\'abord un modèle'))],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'add-field-name',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model_choices = [('', _('-- Sélectionner un modèle --'))]
        for model_info in ModelIntrospector.get_allowed_models():
            model_choices.append((model_info['path'], f"{model_info['verbose_name']} ({model_info['path']})"))
        self.fields['source_model'].choices = model_choices
