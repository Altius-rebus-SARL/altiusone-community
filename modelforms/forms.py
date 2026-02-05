# apps/modelforms/forms.py
"""
Formulaires Django pour la gestion des configurations de formulaires dynamiques.
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import FormConfiguration, ModelFieldMapping, FormTemplate
from .services.introspector import ALLOWED_MODELS


class FormConfigurationForm(forms.ModelForm):
    """Formulaire pour créer/modifier une configuration de formulaire."""

    target_model = forms.ChoiceField(
        label=_('Modèle cible'),
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select select-basic'}),
        help_text=_('Sélectionnez le modèle Django pour ce formulaire')
    )

    class Meta:
        model = FormConfiguration
        fields = [
            'code',
            'name',
            'description',
            'category',
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
        # Construire les choix de modèles depuis la whitelist
        model_choices = [('', _('-- Sélectionner un modèle --'))]
        for model_path in sorted(ALLOWED_MODELS):
            model_choices.append((model_path, model_path))
        self.fields['target_model'].choices = model_choices


class FormConfigurationAdvancedForm(forms.ModelForm):
    """Formulaire avancé pour la configuration JSON."""

    class Meta:
        model = FormConfiguration
        fields = [
            'related_models',
            'form_schema',
            'default_values',
            'validation_rules',
            'post_actions',
        ]
        widgets = {
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

    class Meta:
        model = ModelFieldMapping
        fields = [
            'field_name',
            'model_path',
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
            'field_name': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'model_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('adresse_siege (optionnel)'),
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
