# analytics/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import TableauBord, Indicateur, Rapport


@register(TableauBord)
class TableauBordTranslationOptions(TranslationOptions):
    fields = ("nom", "description")


@register(Indicateur)
class IndicateurTranslationOptions(TranslationOptions):
    fields = ("nom", "description")


@register(Rapport)
class RapportTranslationOptions(TranslationOptions):
    fields = ("nom",)
