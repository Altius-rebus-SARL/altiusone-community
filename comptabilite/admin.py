# comptabilite/admin.py
from django.contrib import admin
from .models import (
    PlanComptable,
    Compte,
    Journal,
    EcritureComptable,
    PieceComptable,
    Lettrage,
)


@admin.register(PlanComptable)
class PlanComptableAdmin(admin.ModelAdmin):
    list_display = ["nom", "type_plan", "mandat", "is_template"]
    list_filter = ["type_plan", "is_template"]
    search_fields = ["nom"]


@admin.register(Compte)
class CompteAdmin(admin.ModelAdmin):
    list_display = ["numero", "libelle", "type_compte", "classe", "solde"]
    list_filter = ["type_compte", "classe", "imputable"]
    search_fields = ["numero", "libelle"]
    ordering = ["numero"]


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ["code", "libelle", "type_journal", "mandat"]
    list_filter = ["type_journal"]
    search_fields = ["code", "libelle"]


@admin.register(EcritureComptable)
class EcritureComptableAdmin(admin.ModelAdmin):
    list_display = [
        "numero_piece",
        "date_ecriture",
        "compte",
        "libelle",
        "montant_debit",
        "montant_credit",
        "statut",
    ]
    list_filter = ["statut", "journal"]
    search_fields = ["numero_piece", "libelle"]
    date_hierarchy = "date_ecriture"


admin.site.register(PieceComptable)
admin.site.register(Lettrage)
