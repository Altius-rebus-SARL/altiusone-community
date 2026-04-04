# projets/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import Position, Operation, OperationNote


@register(Position)
class PositionTranslationOptions(TranslationOptions):
    fields = ("titre", "description")


@register(Operation)
class OperationTranslationOptions(TranslationOptions):
    fields = ("titre", "description")


@register(OperationNote)
class OperationNoteTranslationOptions(TranslationOptions):
    fields = ("contenu",)
