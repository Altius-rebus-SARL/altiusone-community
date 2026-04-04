# documents/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import CategorieDocument, TypeDocument, Document, SourceDocument, Dossier


@register(SourceDocument)
class SourceDocumentTranslationOptions(TranslationOptions):
    fields = ("libelle", "description")


@register(CategorieDocument)
class CategorieDocumentTranslationOptions(TranslationOptions):
    fields = ("nom", "description")


@register(TypeDocument)
class TypeDocumentTranslationOptions(TranslationOptions):
    fields = ("libelle",)


@register(Document)
class DocumentTranslationOptions(TranslationOptions):
    fields = ("description", "notes", "commentaire_validation")


@register(Dossier)
class DossierTranslationOptions(TranslationOptions):
    fields = ("nom", "description")
