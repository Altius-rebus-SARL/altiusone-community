# mailing/serializers.py
"""
Serializers pour l'API REST du module mailing.
Django 6 - Utilisation des pratiques modernes.
"""
from rest_framework import serializers
from .models import ConfigurationEmail, TemplateEmail, EmailEnvoye, EmailRecu


# =============================================================================
# CONFIGURATION EMAIL SERIALIZERS
# =============================================================================

class ConfigurationEmailListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de configurations"""

    type_config_display = serializers.CharField(source='get_type_config_display', read_only=True)
    usage_display = serializers.CharField(source='get_usage_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = ConfigurationEmail
        fields = [
            'id',
            'nom',
            'type_config',
            'type_config_display',
            'usage',
            'usage_display',
            'email_address',
            'from_name',
            'est_defaut',
            'actif',
            'analyse_ai_activee',
            'created_by_name',
            'created_at',
        ]


class ConfigurationEmailDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une configuration"""

    type_config_display = serializers.CharField(source='get_type_config_display', read_only=True)
    usage_display = serializers.CharField(source='get_usage_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    # Statistiques
    emails_envoyes_count = serializers.SerializerMethodField()
    emails_recus_count = serializers.SerializerMethodField()

    class Meta:
        model = ConfigurationEmail
        fields = [
            'id',
            'nom',
            'type_config',
            'type_config_display',
            'usage',
            'usage_display',
            # SMTP
            'smtp_host',
            'smtp_port',
            'smtp_use_tls',
            'smtp_use_ssl',
            # IMAP
            'imap_host',
            'imap_port',
            'imap_use_ssl',
            'imap_dossier',
            # Auth (lecture seule, pas de mot de passe exposé)
            'email_address',
            'username',
            'from_name',
            'reply_to',
            # Options
            'analyse_ai_activee',
            'extraire_pieces_jointes',
            'est_defaut',
            'actif',
            # Stats
            'emails_envoyes_count',
            'emails_recus_count',
            # Audit
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_emails_envoyes_count(self, obj):
        return obj.emails_envoyes.count()

    def get_emails_recus_count(self, obj):
        return obj.emails_recus.count()


class ConfigurationEmailCreateSerializer(serializers.ModelSerializer):
    """Serializer pour création/modification de configuration"""

    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ConfigurationEmail
        fields = [
            'nom',
            'type_config',
            'usage',
            'smtp_host',
            'smtp_port',
            'smtp_use_tls',
            'smtp_use_ssl',
            'imap_host',
            'imap_port',
            'imap_use_ssl',
            'imap_dossier',
            'email_address',
            'username',
            'password',
            'from_name',
            'reply_to',
            'analyse_ai_activee',
            'extraire_pieces_jointes',
            'est_defaut',
            'actif',
        ]

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Ne pas écraser le mot de passe si non fourni
        password = validated_data.pop('password', None)
        if password:
            instance.password = password
        return super().update(instance, validated_data)


# =============================================================================
# TEMPLATE EMAIL SERIALIZERS
# =============================================================================

class TemplateEmailListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de templates"""

    type_template_display = serializers.CharField(source='get_type_template_display', read_only=True)
    configuration_nom = serializers.CharField(source='configuration.nom', read_only=True)

    class Meta:
        model = TemplateEmail
        fields = [
            'id',
            'code',
            'nom',
            'type_template',
            'type_template_display',
            'sujet',
            'configuration',
            'configuration_nom',
            'actif',
            'created_at',
        ]


class TemplateEmailDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un template"""

    type_template_display = serializers.CharField(source='get_type_template_display', read_only=True)
    configuration_nom = serializers.CharField(source='configuration.nom', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    emails_count = serializers.SerializerMethodField()

    class Meta:
        model = TemplateEmail
        fields = [
            'id',
            'code',
            'nom',
            'type_template',
            'type_template_display',
            'sujet',
            'corps_html',
            'corps_texte',
            'variables_disponibles',
            'configuration',
            'configuration_nom',
            'actif',
            'emails_count',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_emails_count(self, obj):
        return obj.emails_envoyes.count()


class TemplateEmailCreateSerializer(serializers.ModelSerializer):
    """Serializer pour création/modification de template"""

    class Meta:
        model = TemplateEmail
        fields = [
            'code',
            'nom',
            'type_template',
            'sujet',
            'corps_html',
            'corps_texte',
            'variables_disponibles',
            'configuration',
            'actif',
        ]

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


# =============================================================================
# EMAIL ENVOYE SERIALIZERS
# =============================================================================

class EmailEnvoyeListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste d'emails envoyés"""

    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    configuration_nom = serializers.CharField(source='configuration.nom', read_only=True)
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    mandat_numero = serializers.CharField(source='mandat.numero', read_only=True)

    class Meta:
        model = EmailEnvoye
        fields = [
            'id',
            'destinataire',
            'sujet',
            'statut',
            'statut_display',
            'date_envoi',
            'tentatives',
            'configuration',
            'configuration_nom',
            'template',
            'utilisateur',
            'utilisateur_name',
            'mandat',
            'mandat_numero',
            'content_type',
            'created_at',
        ]


class EmailEnvoyeDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un email envoyé"""

    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    configuration_nom = serializers.CharField(source='configuration.nom', read_only=True)
    template_nom = serializers.CharField(source='template.nom', read_only=True)
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    mandat_numero = serializers.CharField(source='mandat.numero', read_only=True)

    class Meta:
        model = EmailEnvoye
        fields = [
            'id',
            'configuration',
            'configuration_nom',
            'template',
            'template_nom',
            'destinataire',
            'destinataires_cc',
            'destinataires_bcc',
            'sujet',
            'corps_html',
            'corps_texte',
            'pieces_jointes',
            'statut',
            'statut_display',
            'date_envoi',
            'erreur',
            'tentatives',
            'utilisateur',
            'utilisateur_name',
            'mandat',
            'mandat_numero',
            'content_type',
            'object_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'date_envoi', 'erreur', 'tentatives']


class EmailEnvoyeCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un email à envoyer"""

    class Meta:
        model = EmailEnvoye
        fields = [
            'configuration',
            'template',
            'destinataire',
            'destinataires_cc',
            'destinataires_bcc',
            'sujet',
            'corps_html',
            'corps_texte',
            'pieces_jointes',
            'mandat',
            'content_type',
            'object_id',
        ]

    def create(self, validated_data):
        validated_data['utilisateur'] = self.context['request'].user
        validated_data['statut'] = EmailEnvoye.Statut.EN_ATTENTE
        return super().create(validated_data)


# =============================================================================
# EMAIL RECU SERIALIZERS
# =============================================================================

class EmailRecuListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste d'emails reçus"""

    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    configuration_nom = serializers.CharField(source='configuration.nom', read_only=True)
    mandat_numero = serializers.CharField(source='mandat_detecte.numero', read_only=True)
    client_nom = serializers.CharField(source='client_detecte.raison_sociale', read_only=True)
    est_lu = serializers.SerializerMethodField()
    pieces_jointes_count = serializers.SerializerMethodField()

    class Meta:
        model = EmailRecu
        fields = [
            'id',
            'expediteur',
            'expediteur_nom',
            'sujet',
            'date_reception',
            'date_lecture',
            'est_lu',
            'statut',
            'statut_display',
            'est_important',
            'analyse_effectuee',
            'pieces_jointes_count',
            'configuration',
            'configuration_nom',
            'mandat_detecte',
            'mandat_numero',
            'client_detecte',
            'client_nom',
        ]

    def get_est_lu(self, obj):
        return obj.date_lecture is not None

    def get_pieces_jointes_count(self, obj):
        return len(obj.pieces_jointes) if obj.pieces_jointes else 0


class EmailRecuDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un email reçu"""

    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    configuration_nom = serializers.CharField(source='configuration.nom', read_only=True)
    mandat_numero = serializers.CharField(source='mandat_detecte.numero', read_only=True)
    client_nom = serializers.CharField(source='client_detecte.raison_sociale', read_only=True)
    est_lu = serializers.SerializerMethodField()

    class Meta:
        model = EmailRecu
        fields = [
            'id',
            'configuration',
            'configuration_nom',
            'message_id',
            'expediteur',
            'expediteur_nom',
            'destinataires',
            'destinataires_cc',
            'sujet',
            'corps_html',
            'corps_texte',
            'pieces_jointes',
            'date_reception',
            'date_lecture',
            'est_lu',
            'statut',
            'statut_display',
            'est_important',
            'analyse_effectuee',
            'analyse_resultat',
            'mandat_detecte',
            'mandat_numero',
            'client_detecte',
            'client_nom',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'message_id']

    def get_est_lu(self, obj):
        return obj.date_lecture is not None


class EmailRecuUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour mise à jour d'un email reçu"""

    class Meta:
        model = EmailRecu
        fields = [
            'statut',
            'est_important',
            'mandat_detecte',
            'client_detecte',
        ]
