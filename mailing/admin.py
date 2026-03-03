from django.contrib import admin
from .models import ConfigurationEmail, TemplateEmail, EmailEnvoye, EmailRecu


@admin.register(ConfigurationEmail)
class ConfigurationEmailAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_config', 'usage', 'email_address', 'est_defaut', 'actif']
    list_filter = ['type_config', 'usage', 'actif', 'est_defaut']
    search_fields = ['nom', 'email_address']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TemplateEmail)
class TemplateEmailAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'type_template', 'actif']
    list_filter = ['type_template', 'actif']
    search_fields = ['nom', 'code', 'sujet']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EmailEnvoye)
class EmailEnvoyeAdmin(admin.ModelAdmin):
    list_display = ['sujet', 'destinataire', 'statut', 'date_envoi', 'created_at']
    list_filter = ['statut', 'created_at']
    search_fields = ['sujet', 'destinataire']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(EmailRecu)
class EmailRecuAdmin(admin.ModelAdmin):
    list_display = ['sujet', 'expediteur', 'statut', 'date_reception', 'analyse_effectuee']
    list_filter = ['statut', 'analyse_effectuee', 'date_reception']
    search_fields = ['sujet', 'expediteur', 'corps_texte']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date_reception'
