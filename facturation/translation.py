# facturation/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import Prestation


@register(Prestation)
class PrestationTranslationOptions(TranslationOptions):
    fields = ("libelle", "description")
