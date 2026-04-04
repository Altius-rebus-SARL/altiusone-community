# editeur/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import (
    DocumentCollaboratif,
    ModeleDocument,
    VersionExportee,
)


@register(DocumentCollaboratif)
class DocumentCollaboratifTranslationOptions(TranslationOptions):
    fields = ("titre", "description")


@register(ModeleDocument)
class ModeleDocumentTranslationOptions(TranslationOptions):
    fields = ("nom", "description")


@register(VersionExportee)
class VersionExporteeTranslationOptions(TranslationOptions):
    fields = ("notes",)
