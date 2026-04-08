# graph/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import (
    OntologieType,
    Entite,
    Anomalie,
    RequeteSauvegardee,
)


@register(OntologieType)
class OntologieTypeTranslationOptions(TranslationOptions):
    fields = ("nom", "nom_pluriel", "description", "verbe", "verbe_inverse")


@register(Entite)
class EntiteTranslationOptions(TranslationOptions):
    fields = ("nom", "description")


@register(Anomalie)
class AnomalieTranslationOptions(TranslationOptions):
    fields = ("titre", "description", "commentaire_resolution")


@register(RequeteSauvegardee)
class RequeteSauvegardeeTranslationOptions(TranslationOptions):
    fields = ("nom", "description")
