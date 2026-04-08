# salaires/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import Employe


@register(Employe)
class EmployeTranslationOptions(TranslationOptions):
    fields = ("fonction", "remarques", "departement")
