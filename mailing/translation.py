# mailing/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import (
    ConfigurationEmail,
    TemplateEmail,
)


@register(ConfigurationEmail)
class ConfigurationEmailTranslationOptions(TranslationOptions):
    fields = ("nom",)


@register(TemplateEmail)
class TemplateEmailTranslationOptions(TranslationOptions):
    fields = ("nom", "sujet", "corps_html", "corps_texte")
