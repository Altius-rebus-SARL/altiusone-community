# comptabilite/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import PlanComptable, Compte


@register(PlanComptable)
class PlanComptableTranslationOptions(TranslationOptions):
    fields = ("nom", "description")


@register(Compte)
class CompteTranslationOptions(TranslationOptions):
    fields = ("libelle", "libelle_court")
