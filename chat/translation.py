# chat/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import Conversation


@register(Conversation)
class ConversationTranslationOptions(TranslationOptions):
    fields = ("title",)
