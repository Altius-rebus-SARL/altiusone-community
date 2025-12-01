# salaires/admin.py
from django.contrib import admin
from .models import (
    Employe,
    TauxCotisation,
    FicheSalaire,
    CertificatSalaire,
    DeclarationCotisations,
)


@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):
    list_display = [
        "matricule",
        "nom",
        "prenom",
        "fonction",
        "statut",
        "salaire_brut_mensuel",
    ]
    list_filter = ["statut", "type_contrat", "sexe"]
    search_fields = ["nom", "prenom", "matricule", "avs_number"]


@admin.register(FicheSalaire)
class FicheSalaireAdmin(admin.ModelAdmin):
    list_display = ["numero_fiche", "employe", "periode", "salaire_net", "statut"]
    list_filter = ["statut", "annee", "mois"]
    search_fields = ["numero_fiche", "employe__nom", "employe__prenom"]
    date_hierarchy = "periode"


@admin.register(TauxCotisation)
class TauxCotisationAdmin(admin.ModelAdmin):
    list_display = [
        "type_cotisation",
        "libelle",
        "taux_total",
        "taux_employeur",
        "taux_employe",
        "actif",
    ]
    list_filter = ["type_cotisation", "actif"]


admin.site.register(CertificatSalaire)
admin.site.register(DeclarationCotisations)
