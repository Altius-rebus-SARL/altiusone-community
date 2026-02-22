# tva/admin.py
from django.contrib import admin
from .models import (
    RegimeFiscal,
    ConfigurationTVA,
    TauxTVA,
    CodeTVA,
    DeclarationTVA,
    LigneTVA,
    OperationTVA,
    CorrectionTVA,
)


@admin.register(RegimeFiscal)
class RegimeFiscalAdmin(admin.ModelAdmin):
    list_display = ["code", "nom", "pays", "devise_defaut", "taux_normal"]
    list_filter = ["pays"]
    search_fields = ["code", "nom"]


@admin.register(ConfigurationTVA)
class ConfigurationTVAAdmin(admin.ModelAdmin):
    list_display = ["mandat", "assujetti_tva", "numero_tva", "methode_calcul"]
    list_filter = ["assujetti_tva", "methode_calcul", "periodicite"]


@admin.register(TauxTVA)
class TauxTVAAdmin(admin.ModelAdmin):
    list_display = ["type_taux", "taux", "date_debut", "date_fin"]
    list_filter = ["type_taux"]


@admin.register(CodeTVA)
class CodeTVAAdmin(admin.ModelAdmin):
    list_display = ["code", "libelle", "categorie", "actif"]
    list_filter = ["categorie", "actif"]
    search_fields = ["code", "libelle"]


@admin.register(DeclarationTVA)
class DeclarationTVAAdmin(admin.ModelAdmin):
    list_display = [
        "numero_declaration",
        "mandat",
        "regime_fiscal",
        "devise",
        "annee",
        "trimestre",
        "statut",
        "solde_tva",
    ]
    list_filter = ["statut", "annee", "type_decompte", "regime_fiscal"]
    search_fields = ["numero_declaration"]
    date_hierarchy = "periode_debut"


class LigneTVAInline(admin.TabularInline):
    model = LigneTVA
    extra = 1


admin.site.register(LigneTVA)
admin.site.register(OperationTVA)
admin.site.register(CorrectionTVA)
