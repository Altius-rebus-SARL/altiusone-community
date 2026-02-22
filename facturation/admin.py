# facturation/admin.py
from django.contrib import admin
from .models import (
    TypePrestation, Prestation, TimeTracking, Facture, LigneFacture, Paiement, Relance,
    ZoneGeographique, TarifMandat,
)


@admin.register(TypePrestation)
class TypePrestationAdmin(admin.ModelAdmin):
    list_display = ["code", "libelle", "icone", "ordre", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "libelle"]
    ordering = ["ordre"]


@admin.register(Prestation)
class PrestationAdmin(admin.ModelAdmin):
    list_display = ["code", "libelle", "type_prestation", "prix_unitaire_ht", "actif"]
    list_filter = ["type_prestation", "actif", "soumis_tva"]
    search_fields = ["code", "libelle"]


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = [
        "numero_facture",
        "client",
        "date_emission",
        "montant_ttc",
        "statut",
        "montant_restant",
    ]
    list_filter = ["statut", "type_facture"]
    search_fields = ["numero_facture", "client__raison_sociale"]
    date_hierarchy = "date_emission"


class LigneFactureInline(admin.TabularInline):
    model = LigneFacture
    extra = 1


@admin.register(TimeTracking)
class TimeTrackingAdmin(admin.ModelAdmin):
    list_display = [
        "date_travail",
        "utilisateur",
        "mandat",
        "duree_minutes",
        "facturable",
    ]
    list_filter = ["facturable", "valide"]
    date_hierarchy = "date_travail"


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ["facture", "montant", "date_paiement", "mode_paiement", "valide"]
    list_filter = ["mode_paiement", "valide"]
    date_hierarchy = "date_paiement"


admin.site.register(LigneFacture)
admin.site.register(Relance)


@admin.register(ZoneGeographique)
class ZoneGeographiqueAdmin(admin.ModelAdmin):
    list_display = ["nom", "couleur", "created_at"]
    search_fields = ["nom"]


@admin.register(TarifMandat)
class TarifMandatAdmin(admin.ModelAdmin):
    list_display = ["mandat", "prestation", "taux_horaire", "devise", "date_debut", "date_fin"]
    list_filter = ["devise", "prestation"]
    search_fields = ["mandat__numero", "prestation__libelle"]
