"""
Configuration Django Admin pour l'application Éditeur Collaboratif.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    DocumentCollaboratif,
    PartageDocument,
    LienPartagePublic,
    SessionEdition,
    VersionExportee,
    ModeleDocument
)


@admin.register(DocumentCollaboratif)
class DocumentCollaboratifAdmin(admin.ModelAdmin):
    """Admin pour les documents collaboratifs."""
    list_display = [
        'titre',
        'type_document',
        'statut',
        'createur',
        'mandat',
        'nombre_collaborateurs',
        'date_modification',
    ]
    list_filter = ['statut', 'type_document', 'langue', 'date_creation']
    search_fields = ['titre', 'description', 'docs_id']
    readonly_fields = [
        'id', 'docs_id', 'date_creation', 'date_modification',
        'date_derniere_edition', 'nombre_collaborateurs', 'nombre_versions',
        'taille_contenu', 'lien_edition'
    ]
    raw_id_fields = ['createur', 'mandat', 'client', 'dossier', 'document_exporte']
    date_hierarchy = 'date_creation'

    fieldsets = (
        (None, {
            'fields': ('titre', 'description', 'type_document', 'statut')
        }),
        (_('Liens'), {
            'fields': ('id', 'docs_id', 'lien_edition')
        }),
        (_('Organisation'), {
            'fields': ('mandat', 'client', 'dossier', 'document_exporte')
        }),
        (_('Accès'), {
            'fields': ('createur', 'est_public', 'langue')
        }),
        (_('Statistiques'), {
            'fields': (
                'nombre_collaborateurs', 'nombre_versions', 'taille_contenu',
                'date_creation', 'date_modification', 'date_derniere_edition'
            )
        }),
    )

    def lien_edition(self, obj):
        if obj.docs_id:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.url_edition,
                _("Ouvrir dans l'éditeur")
            )
        return '-'
    lien_edition.short_description = _("Lien d'édition")


@admin.register(PartageDocument)
class PartageDocumentAdmin(admin.ModelAdmin):
    """Admin pour les partages."""
    list_display = [
        'document',
        'utilisateur',
        'niveau_acces',
        'partage_par',
        'date_partage',
        'est_expire_display',
    ]
    list_filter = ['niveau_acces', 'date_partage']
    search_fields = ['document__titre', 'utilisateur__email']
    raw_id_fields = ['document', 'utilisateur', 'partage_par']

    def est_expire_display(self, obj):
        if obj.est_expire:
            return format_html('<span style="color: red;">✗</span>')
        return format_html('<span style="color: green;">✓</span>')
    est_expire_display.short_description = _("Actif")


@admin.register(LienPartagePublic)
class LienPartagePublicAdmin(admin.ModelAdmin):
    """Admin pour les liens publics."""
    list_display = [
        'document',
        'token_court',
        'permet_edition',
        'nombre_acces',
        'est_actif',
        'date_creation',
    ]
    list_filter = ['est_actif', 'permet_edition', 'date_creation']
    search_fields = ['document__titre', 'token']
    readonly_fields = ['token', 'nombre_acces', 'date_creation']
    raw_id_fields = ['document', 'cree_par']

    def token_court(self, obj):
        return f"{obj.token[:8]}..."
    token_court.short_description = _("Token")


@admin.register(SessionEdition)
class SessionEditionAdmin(admin.ModelAdmin):
    """Admin pour les sessions d'édition."""
    list_display = [
        'document',
        'utilisateur',
        'debut',
        'derniere_activite',
        'est_active',
    ]
    list_filter = ['est_active', 'debut']
    search_fields = ['document__titre', 'utilisateur__email', 'session_id']
    readonly_fields = ['debut', 'derniere_activite', 'fin']
    raw_id_fields = ['document', 'utilisateur']


@admin.register(VersionExportee)
class VersionExporteeAdmin(admin.ModelAdmin):
    """Admin pour les versions exportées."""
    list_display = [
        'document',
        'format_export',
        'numero_version',
        'taille_formatee',
        'exporte_par',
        'date_export',
    ]
    list_filter = ['format_export', 'date_export']
    search_fields = ['document__titre']
    readonly_fields = ['date_export', 'hash_contenu']
    raw_id_fields = ['document', 'exporte_par', 'document_ged']

    def taille_formatee(self, obj):
        if obj.taille < 1024:
            return f"{obj.taille} B"
        elif obj.taille < 1024 * 1024:
            return f"{obj.taille / 1024:.1f} KB"
        else:
            return f"{obj.taille / (1024 * 1024):.1f} MB"
    taille_formatee.short_description = _("Taille")


@admin.register(ModeleDocument)
class ModeleDocumentAdmin(admin.ModelAdmin):
    """Admin pour les modèles de documents."""
    list_display = [
        'nom',
        'categorie',
        'type_document',
        'langue',
        'est_public',
        'est_systeme',
        'nombre_utilisations',
    ]
    list_filter = ['categorie', 'type_document', 'langue', 'est_public', 'est_systeme']
    search_fields = ['nom', 'description']
    readonly_fields = ['date_creation', 'date_modification', 'nombre_utilisations']
    raw_id_fields = ['cree_par']

    fieldsets = (
        (None, {
            'fields': ('nom', 'description', 'categorie', 'type_document')
        }),
        (_('Contenu'), {
            'fields': ('contenu_json', 'apercu_html'),
            'classes': ('collapse',)
        }),
        (_('Paramètres'), {
            'fields': ('langue', 'est_public', 'est_systeme')
        }),
        (_('Métadonnées'), {
            'fields': ('cree_par', 'date_creation', 'date_modification', 'nombre_utilisations')
        }),
    )
