# analytics/admin.py
from django.contrib import admin
from .models import (
    TableauBord,
    Indicateur,
    ValeurIndicateur,
    Rapport,
    PlanificationRapport,
    ComparaisonPeriode,
    AlerteMetrique,
    ExportDonnees,
)


@admin.register(TableauBord)
class TableauBordAdmin(admin.ModelAdmin):
    list_display = ["nom", "proprietaire", "visibilite", "favori"]
    list_filter = ["visibilite", "favori", "auto_refresh"]


@admin.register(Indicateur)
class IndicateurAdmin(admin.ModelAdmin):
    list_display = ["code", "nom", "categorie", "type_calcul", "periodicite", "actif"]
    list_filter = ["categorie", "type_calcul", "periodicite", "actif"]
    search_fields = ["code", "nom"]


@admin.register(Rapport)
class RapportAdmin(admin.ModelAdmin):
    list_display = ["nom", "type_rapport", "mandat", "statut", "date_generation"]
    list_filter = ["type_rapport", "statut", "format_fichier"]
    date_hierarchy = "date_generation"


admin.site.register(ValeurIndicateur)
admin.site.register(PlanificationRapport)
admin.site.register(AlerteMetrique)
admin.site.register(ExportDonnees)
