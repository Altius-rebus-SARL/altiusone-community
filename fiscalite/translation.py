# fiscalite/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import OptimisationFiscale


@register(OptimisationFiscale)
class OptimisationFiscaleTranslationOptions(TranslationOptions):
    fields = ("titre", "description", "notes")
