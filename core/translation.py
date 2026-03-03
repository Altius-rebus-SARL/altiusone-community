# core/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import Client, Mandat, Contact, Tache, Notification


@register(Client)
class ClientTranslationOptions(TranslationOptions):
    fields = ("description", "notes")


@register(Mandat)
class MandatTranslationOptions(TranslationOptions):
    fields = ("description", "conditions_particulieres")


@register(Tache)
class TacheTranslationOptions(TranslationOptions):
    fields = ("titre", "description")


@register(Notification)
class NotificationTranslationOptions(TranslationOptions):
    fields = ("titre", "message", "lien_texte")
