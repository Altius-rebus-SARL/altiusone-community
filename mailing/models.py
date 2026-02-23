"""
Modèles pour la gestion des emails.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

try:
    from fernet_fields import EncryptedTextField
except ImportError:
    # Fallback si django-fernet-fields n'est pas installé
    EncryptedTextField = models.TextField


class ConfigurationEmail(models.Model):
    """
    Configuration SMTP/IMAP pour l'envoi et la réception d'emails.
    Permet de configurer plusieurs comptes email (no-reply, newsletter, support, etc.)
    """

    class TypeConfig(models.TextChoices):
        SMTP = 'SMTP', _('Envoi (SMTP)')
        IMAP = 'IMAP', _('Réception (IMAP)')
        POP3 = 'POP3', _('Réception (POP3)')

    class Usage(models.TextChoices):
        NOREPLY = 'NOREPLY', _('No-reply (transactionnel)')
        NEWSLETTER = 'NEWSLETTER', _('Newsletter')
        SUPPORT = 'SUPPORT', _('Support')
        NOTIFICATIONS = 'NOTIFICATIONS', _('Notifications')
        RECEPTION = 'RECEPTION', _('Réception et analyse')
        GENERAL = 'GENERAL', _('Général')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    nom = models.CharField(
        max_length=100,
        verbose_name=_('Nom de la configuration'),
        help_text=_('Ex: No-Reply Production, Newsletter Marketing')
    )
    type_config = models.CharField(
        max_length=10,
        choices=TypeConfig.choices,
        default=TypeConfig.SMTP,
        verbose_name=_('Type de configuration')
    )
    usage = models.CharField(
        max_length=20,
        choices=Usage.choices,
        default=Usage.GENERAL,
        verbose_name=_('Usage')
    )

    # Configuration SMTP (envoi)
    smtp_host = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Serveur SMTP'),
        help_text=_('Ex: smtp.gmail.com, smtp.office365.com')
    )
    smtp_port = models.PositiveIntegerField(
        default=587,
        verbose_name=_('Port SMTP'),
        help_text=_('587 pour TLS, 465 pour SSL, 25 pour non sécurisé')
    )
    smtp_use_tls = models.BooleanField(
        default=True,
        verbose_name=_('Utiliser TLS')
    )
    smtp_use_ssl = models.BooleanField(
        default=False,
        verbose_name=_('Utiliser SSL')
    )

    # Configuration IMAP/POP3 (réception)
    imap_host = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Serveur IMAP/POP3'),
        help_text=_('Ex: imap.gmail.com')
    )
    imap_port = models.PositiveIntegerField(
        default=993,
        verbose_name=_('Port IMAP/POP3')
    )
    imap_use_ssl = models.BooleanField(
        default=True,
        verbose_name=_('Utiliser SSL pour IMAP')
    )
    imap_dossier = models.CharField(
        max_length=100,
        default='INBOX',
        blank=True,
        verbose_name=_('Dossier à surveiller')
    )

    # Authentification (champs chiffrés)
    email_address = models.EmailField(
        verbose_name=_('Adresse email')
    )
    username = models.CharField(
        max_length=255,
        verbose_name=_('Nom d\'utilisateur'),
        help_text=_('Généralement identique à l\'adresse email')
    )
    password = EncryptedTextField(
        verbose_name=_('Mot de passe'),
        help_text=_('Mot de passe ou mot de passe d\'application')
    )

    # Affichage
    from_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Nom d\'expéditeur'),
        help_text=_('Ex: AltiusOne Support')
    )
    reply_to = models.EmailField(
        blank=True,
        verbose_name=_('Adresse de réponse'),
        help_text=_('Si différente de l\'adresse d\'envoi')
    )

    # Analyse IA (pour emails entrants)
    analyse_ai_activee = models.BooleanField(
        default=False,
        verbose_name=_('Activer l\'analyse IA'),
        help_text=_('Analyser automatiquement les emails reçus avec l\'IA')
    )
    extraire_pieces_jointes = models.BooleanField(
        default=False,
        verbose_name=_('Extraire les pièces jointes'),
        help_text=_('Sauvegarder automatiquement les pièces jointes')
    )

    # Statut
    est_defaut = models.BooleanField(
        default=False,
        verbose_name=_('Configuration par défaut')
    )
    actif = models.BooleanField(
        default=True,
        verbose_name=_('Actif')
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
        verbose_name=_('Créé par')
    )

    class Meta:
        db_table = 'configurations_email'
        verbose_name = _('Configuration email')
        verbose_name_plural = _('Configurations email')
        ordering = ['-est_defaut', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.get_usage_display()})"

    def save(self, *args, **kwargs):
        # S'assurer qu'il n'y a qu'une seule configuration par défaut par usage
        if self.est_defaut:
            ConfigurationEmail.objects.filter(
                usage=self.usage,
                est_defaut=True
            ).exclude(pk=self.pk).update(est_defaut=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_default(cls, usage='NOREPLY'):
        """Retourne la configuration par défaut pour un usage donné."""
        return cls.objects.filter(
            usage=usage,
            actif=True,
            est_defaut=True
        ).first() or cls.objects.filter(
            usage=usage,
            actif=True
        ).first()


class TemplateEmail(models.Model):
    """
    Templates d'emails avec support des variables.
    """

    class TypeTemplate(models.TextChoices):
        INVITATION = 'INVITATION', _('Invitation')
        PASSWORD_RESET = 'PASSWORD_RESET', _('Réinitialisation mot de passe')
        WELCOME = 'WELCOME', _('Bienvenue')
        NOTIFICATION = 'NOTIFICATION', _('Notification')
        RAPPEL = 'RAPPEL', _('Rappel')
        FACTURE = 'FACTURE', _('Facture')
        RAPPORT = 'RAPPORT', _('Rapport')
        CUSTOM = 'CUSTOM', _('Personnalisé')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Code'),
        help_text=_('Identifiant unique (ex: INVITATION_STAFF)')
    )
    nom = models.CharField(
        max_length=100,
        verbose_name=_('Nom du template')
    )
    type_template = models.CharField(
        max_length=20,
        choices=TypeTemplate.choices,
        default=TypeTemplate.CUSTOM,
        verbose_name=_('Type')
    )

    # Contenu
    sujet = models.CharField(
        max_length=255,
        verbose_name=_('Sujet'),
        help_text=_('Supporte les variables: {{nom}}, {{entreprise}}, etc.')
    )
    corps_html = models.TextField(
        verbose_name=_('Contenu HTML')
    )
    corps_texte = models.TextField(
        blank=True,
        verbose_name=_('Contenu texte'),
        help_text=_('Version texte brut (optionnel)')
    )

    # Variables disponibles (documentation)
    variables_disponibles = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Variables disponibles'),
        help_text=_('Liste des variables: ["nom", "email", "lien"]')
    )

    # Configuration associée
    configuration = models.ForeignKey(
        ConfigurationEmail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates',
        verbose_name=_('Configuration email'),
        help_text=_('Configuration SMTP à utiliser')
    )

    # Statut
    actif = models.BooleanField(default=True, verbose_name=_('Actif'))

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
        verbose_name=_('Créé par')
    )

    class Meta:
        db_table = 'templates_email'
        verbose_name = _('Template email')
        verbose_name_plural = _('Templates email')
        ordering = ['type_template', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.code})"

    def render(self, context: dict) -> tuple:
        """
        Rend le template avec le contexte fourni.
        Retourne (sujet, corps_html, corps_texte)
        """
        from django.template import Template, Context

        ctx = Context(context)

        sujet = Template(self.sujet).render(ctx)
        corps_html = Template(self.corps_html).render(ctx)
        corps_texte = Template(self.corps_texte).render(ctx) if self.corps_texte else ''

        return sujet, corps_html, corps_texte


class EmailEnvoye(models.Model):
    """
    Historique des emails envoyés.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', _('En attente')
        ENVOYE = 'ENVOYE', _('Envoyé')
        ECHEC = 'ECHEC', _('Échec')
        BOUNCE = 'BOUNCE', _('Bounce')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    configuration = models.ForeignKey(
        ConfigurationEmail,
        on_delete=models.SET_NULL,
        null=True,
        related_name='emails_envoyes',
        verbose_name=_('Configuration utilisée')
    )
    template = models.ForeignKey(
        TemplateEmail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails_envoyes',
        verbose_name=_('Template utilisé')
    )

    # Destinataires
    destinataire = models.EmailField(verbose_name=_('Destinataire'))
    destinataires_cc = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('CC')
    )
    destinataires_bcc = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('BCC')
    )

    # Contenu
    sujet = models.CharField(max_length=255, verbose_name=_('Sujet'))
    corps_html = models.TextField(verbose_name=_('Contenu HTML'))
    corps_texte = models.TextField(blank=True, verbose_name=_('Contenu texte'))
    pieces_jointes = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Pièces jointes'),
        help_text=_('[{"nom": "doc.pdf", "cle_s3": "abc123_doc.pdf", "taille": 1024, "type_mime": "application/pdf"}]')
    )

    # Statut
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        db_index=True,
        verbose_name=_('Statut')
    )
    date_envoi = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date d\'envoi')
    )
    erreur = models.TextField(
        blank=True,
        verbose_name=_('Message d\'erreur')
    )
    tentatives = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Nombre de tentatives')
    )

    # Contexte (pour traçabilité)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails_envoyes',
        verbose_name=_('Envoyé par')
    )
    mandat = models.ForeignKey(
        'core.Mandat',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails_envoyes',
        verbose_name=_('Mandat associé')
    )
    content_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Type de contenu'),
        help_text=_('Ex: facture, invitation, rappel')
    )
    object_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('ID de l\'objet'),
        help_text=_('UUID de l\'objet associé')
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'emails_envoyes'
        verbose_name = _('Email envoyé')
        verbose_name_plural = _('Emails envoyés')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['destinataire', 'statut']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.sujet} → {self.destinataire}"


class EmailRecu(models.Model):
    """
    Emails reçus (si analyse IA activée).
    """

    class Statut(models.TextChoices):
        NON_LU = 'NON_LU', _('Non lu')
        LU = 'LU', _('Lu')
        TRAITE = 'TRAITE', _('Traité')
        ARCHIVE = 'ARCHIVE', _('Archivé')
        SPAM = 'SPAM', _('Spam')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    configuration = models.ForeignKey(
        ConfigurationEmail,
        on_delete=models.CASCADE,
        related_name='emails_recus',
        verbose_name=_('Configuration')
    )

    # Identifiant unique de l'email
    message_id = models.CharField(
        max_length=500,
        unique=True,
        verbose_name=_('Message-ID'),
        help_text=_('Identifiant unique du serveur')
    )

    # Expéditeur
    expediteur = models.EmailField(verbose_name=_('Expéditeur'))
    expediteur_nom = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Nom de l\'expéditeur')
    )

    # Destinataires
    destinataires = models.JSONField(
        default=list,
        verbose_name=_('Destinataires')
    )
    destinataires_cc = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('CC')
    )

    # Contenu
    sujet = models.CharField(max_length=500, verbose_name=_('Sujet'))
    corps_html = models.TextField(blank=True, verbose_name=_('Contenu HTML'))
    corps_texte = models.TextField(blank=True, verbose_name=_('Contenu texte'))

    # Pièces jointes
    pieces_jointes = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Pièces jointes'),
        help_text=_('[{"nom": "doc.pdf", "taille": 1024, "type": "application/pdf", "path": "..."}]')
    )

    # Dates
    date_reception = models.DateTimeField(verbose_name=_('Date de réception'))
    date_lecture = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date de lecture')
    )

    # Statut
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.NON_LU,
        db_index=True,
        verbose_name=_('Statut')
    )
    est_important = models.BooleanField(
        default=False,
        verbose_name=_('Important')
    )

    # Analyse IA
    analyse_effectuee = models.BooleanField(
        default=False,
        verbose_name=_('Analyse IA effectuée')
    )
    analyse_resultat = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Résultat de l\'analyse'),
        help_text=_('{"type": "demande_info", "urgence": "haute", "resume": "...", "actions": [...]}')
    )

    # Liaison automatique (si détecté par IA)
    mandat_detecte = models.ForeignKey(
        'core.Mandat',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails_recus',
        verbose_name=_('Mandat détecté')
    )
    client_detecte = models.ForeignKey(
        'core.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails_recus',
        verbose_name=_('Client détecté')
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'emails_recus'
        verbose_name = _('Email reçu')
        verbose_name_plural = _('Emails reçus')
        ordering = ['-date_reception']
        indexes = [
            models.Index(fields=['expediteur', 'statut']),
            models.Index(fields=['date_reception']),
            models.Index(fields=['configuration', 'statut']),
        ]

    def __str__(self):
        return f"{self.sujet} ← {self.expediteur}"

    def marquer_comme_lu(self):
        """Marque l'email comme lu."""
        from django.utils import timezone
        if self.statut == self.Statut.NON_LU:
            self.statut = self.Statut.LU
            self.date_lecture = timezone.now()
            self.save(update_fields=['statut', 'date_lecture', 'updated_at'])
