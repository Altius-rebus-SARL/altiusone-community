from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Operation, OperationNote, Position


class OperationInline(admin.TabularInline):
    model = Operation
    extra = 0
    fields = ("numero", "titre", "statut", "assigne_a", "date_debut", "date_fin", "budget_prevu", "cout_reel")
    readonly_fields = ("numero",)


class OperationNoteInline(admin.TabularInline):
    model = OperationNote
    extra = 0
    fields = ("auteur", "contenu", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Position)
class PositionAdmin(GISModelAdmin):
    list_display = ("numero", "titre", "mandat", "statut", "budget_prevu", "budget_reel", "date_debut", "date_fin")
    list_filter = ("statut", "est_sous_traite")
    search_fields = ("numero", "titre", "mandat__numero")
    inlines = [OperationInline]
    readonly_fields = ("numero",)


@admin.register(Operation)
class OperationAdmin(GISModelAdmin):
    list_display = ("numero", "titre", "position", "statut", "priorite", "assigne_a", "date_debut", "date_fin")
    list_filter = ("statut", "priorite")
    search_fields = ("numero", "titre", "position__numero")
    inlines = [OperationNoteInline]
    readonly_fields = ("numero",)


@admin.register(OperationNote)
class OperationNoteAdmin(admin.ModelAdmin):
    list_display = ("operation", "auteur", "created_at")
    list_filter = ("created_at",)
    search_fields = ("contenu",)
