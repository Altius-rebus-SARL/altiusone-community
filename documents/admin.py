# documents/admin.py
from django.contrib import admin
from .models import (
    Dossier,
    CategorieDocument,
    TypeDocument,
    Document,
    VersionDocument,
    TraitementDocument,
    RechercheDocument,
)


@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    list_display = ["nom", "type_dossier", "client", "chemin_complet"]
    list_filter = ["type_dossier"]
    search_fields = ["nom", "chemin_complet"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        "nom_fichier",
        "mandat",
        "type_document",
        "date_document",
        "statut_traitement",
    ]
    list_filter = ["statut_traitement", "type_document"]
    search_fields = ["nom_fichier", "description"]
    date_hierarchy = "date_document"


@admin.register(CategorieDocument)
class CategorieDocumentAdmin(admin.ModelAdmin):
    list_display = ["nom", "ordre"]
    ordering = ["ordre", "nom"]


admin.site.register(TypeDocument)
admin.site.register(VersionDocument)
admin.site.register(TraitementDocument)
