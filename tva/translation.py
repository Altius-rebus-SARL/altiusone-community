# tva/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import CodeTVA


@register(CodeTVA)
class CodeTVATranslationOptions(TranslationOptions):
    fields = ("libelle", "description")
