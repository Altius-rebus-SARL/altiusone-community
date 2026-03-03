# fiscalite/admin.py
from django.contrib import admin
from .models import (
    DeclarationFiscale,
    AnnexeFiscale,
    CorrectionFiscale,
    ReportPerte,
    UtilisationPerte,
    TauxImposition,
    ReclamationFiscale,
    OptimisationFiscale,
)


@admin.register(DeclarationFiscale)
class DeclarationFiscaleAdmin(admin.ModelAdmin):
    list_display = [
        "numero_declaration",
        "mandat",
        "annee_fiscale",
        "type_impot",
        "statut",
        "impot_total",
    ]
    list_filter = ["type_declaration", "type_impot", "statut", "canton"]
    search_fields = ["numero_declaration", "numero_contribuable"]


@admin.register(TauxImposition)
class TauxImpositionAdmin(admin.ModelAdmin):
    list_display = ["regime_fiscal", "canton", "type_impot", "annee", "taux_fixe", "actif"]
    list_filter = ["regime_fiscal", "canton", "type_impot", "actif"]
    search_fields = ["canton", "commune", "subdivision"]


admin.site.register(AnnexeFiscale)
admin.site.register(CorrectionFiscale)
admin.site.register(ReportPerte)
admin.site.register(OptimisationFiscale)
