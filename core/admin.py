# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Adresse,
    Client,
    Contact,
    Mandat,
    ExerciceComptable,
    AuditLog,
    Notification,
    Tache,
    Tiers,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "role", "is_active"]
    list_filter = ["role", "is_active", "is_staff"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Informations supplémentaires", {"fields": ("role", "phone", "mobile")}),
    )


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["raison_sociale", "ide_number", "forme_juridique", "statut"]
    list_filter = ["forme_juridique", "statut"]
    search_fields = ["raison_sociale", "ide_number", "tva_number"]


@admin.register(Mandat)
class MandatAdmin(admin.ModelAdmin):
    list_display = ["numero", "client", "type_mandat", "statut", "date_debut"]
    list_filter = ["type_mandat", "statut", "periodicite"]
    search_fields = ["numero", "client__raison_sociale"]
    date_hierarchy = "date_debut"


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["nom", "prenom", "client", "fonction", "email"]
    list_filter = ["fonction", "principal"]
    search_fields = ["nom", "prenom", "email"]


@admin.register(Adresse)
class AdresseAdmin(admin.ModelAdmin):
    list_display = ["rue", "code_postal", "localite", "canton", "pays"]
    list_filter = ["canton", "pays"]
    search_fields = ["rue", "localite", "code_postal"]


@admin.register(ExerciceComptable)
class ExerciceComptableAdmin(admin.ModelAdmin):
    list_display = ["mandat", "annee", "statut", "resultat_exercice"]
    list_filter = ["statut", "annee"]


@admin.register(Tache)
class TacheAdmin(admin.ModelAdmin):
    list_display = ["titre", "priorite", "statut", "date_echeance"]
    list_filter = ["priorite", "statut"]
    date_hierarchy = "date_echeance"


@admin.register(Tiers)
class TiersAdmin(admin.ModelAdmin):
    list_display = ["code", "nom", "type_tiers", "mandat", "devise"]
    list_filter = ["type_tiers"]
    search_fields = ["code", "nom", "numero_tva"]


admin.site.register(AuditLog)
admin.site.register(Notification)
