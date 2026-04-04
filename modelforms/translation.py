# modelforms/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import (
    FormConfiguration,
    ModelFieldMapping,
    FormTemplate,
)


@register(FormConfiguration)
class FormConfigurationTranslationOptions(TranslationOptions):
    fields = ("name", "description", "success_message")


@register(ModelFieldMapping)
class ModelFieldMappingTranslationOptions(TranslationOptions):
    fields = ("label", "help_text", "placeholder")


@register(FormTemplate)
class FormTemplateTranslationOptions(TranslationOptions):
    fields = ("name", "description")
