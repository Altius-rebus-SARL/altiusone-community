"""
Modèles pour l'application Éditeur Collaboratif.

Intégration de Docs (La Suite Numérique) dans AltiusOne.
Ces modèles servent de pont entre AltiusOne et l'instance Docs auto-hébergée.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class DocumentCollaboratif(models.Model):
    """
    Document collaboratif créé dans l'éditeur Docs.

    Ce modèle fait le lien entre un document dans Docs (via docs_id)
    et les entités AltiusOne (mandat, client, dossier).
    """

    class TypeDocument(models.TextChoices):
        NOTE = 'NOTE', _('Note')
        RAPPORT = 'RAPPORT', _('Rapport')
        PROCES_VERBAL = 'PV', _('Procès-verbal')
        COURRIER = 'COURRIER', _('Courrier')
        CONTRAT = 'CONTRAT', _('Contrat')
        MEMO = 'MEMO', _('Mémo interne')
        DOCUMENTATION = 'DOC', _('Documentation')
        WIKI = 'WIKI', _('Wiki')
        AUTRE = 'AUTRE', _('Autre')

    class Statut(models.TextChoices):
        BROUILLON = 'BROUILLON', _('Brouillon')
        EN_COURS = 'EN_COURS', _('En cours de rédaction')
        EN_REVISION = 'REVISION', _('En révision')
        VALIDE = 'VALIDE', _('Validé')
        ARCHIVE = 'ARCHIVE', _('Archivé')

    # Identifiant unique AltiusOne
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Identifiant du document dans Docs (La Suite Numérique)
    docs_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("ID Docs"),
        help_text=_("Identifiant du document dans l'instance Docs")
    )

    # Métadonnées
    titre = models.CharField(
        max_length=500,
        verbose_name=_("Titre")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    type_document = models.CharField(
        max_length=20,
        choices=TypeDocument.choices,
        default=TypeDocument.NOTE,
        verbose_name=_("Type de document")
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.BROUILLON,
        verbose_name=_("Statut")
    )

    # Liens vers les entités AltiusOne
    mandat = models.ForeignKey(
        'core.Mandat',
        on_delete=models.CASCADE,
        related_name='documents_collaboratifs',
        verbose_name=_("Mandat"),
        null=True,
        blank=True
    )
    client = models.ForeignKey(
        'core.Client',
        on_delete=models.CASCADE,
        related_name='documents_collaboratifs',
        verbose_name=_("Client"),
        null=True,
        blank=True
    )
    dossier = models.ForeignKey(
        'documents.Dossier',
        on_delete=models.SET_NULL,
        related_name='documents_collaboratifs',
        verbose_name=_("Dossier GED"),
        null=True,
        blank=True,
        help_text=_("Dossier de classement dans la GED")
    )

    # Lien vers le document exporté dans la GED (après finalisation)
    document_exporte = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        related_name='document_source_collaboratif',
        verbose_name=_("Document exporté"),
        null=True,
        blank=True,
        help_text=_("Version PDF/Word archivée dans la GED")
    )

    # Propriétaire et accès
    createur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='documents_collaboratifs_crees',
        verbose_name=_("Créateur"),
        null=True
    )
    est_public = models.BooleanField(
        default=False,
        verbose_name=_("Public dans le mandat"),
        help_text=_("Si activé, tous les utilisateurs du mandat peuvent voir ce document")
    )

    # Dates
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Dernière modification")
    )
    date_derniere_edition = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Dernière édition collaborative"),
        help_text=_("Mise à jour via webhook depuis Docs")
    )

    # Statistiques (synchronisées depuis Docs)
    nombre_collaborateurs = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Nombre de collaborateurs")
    )
    nombre_versions = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Nombre de versions")
    )
    taille_contenu = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Taille du contenu (caractères)")
    )

    # Configuration
    langue = models.CharField(
        max_length=5,
        choices=[
            ('fr', 'Français'),
            ('de', 'Deutsch'),
            ('it', 'Italiano'),
            ('en', 'English'),
        ],
        default='fr',
        verbose_name=_("Langue")
    )

    class Meta:
        verbose_name = _("Document collaboratif")
        verbose_name_plural = _("Documents collaboratifs")
        ordering = ['-date_modification']
        indexes = [
            models.Index(fields=['docs_id']),
            models.Index(fields=['mandat', '-date_modification']),
            models.Index(fields=['client', '-date_modification']),
            models.Index(fields=['createur', '-date_modification']),
            models.Index(fields=['statut']),
            models.Index(fields=['type_document']),
        ]

    def __str__(self):
        return self.titre

    @property
    def url_edition(self):
        """URL pour éditer le document dans Docs."""
        docs_url = getattr(settings, 'DOCS_FRONTEND_URL', 'http://localhost:3000')
        return f"{docs_url}/docs/{self.docs_id}"

    @property
    def est_editable(self):
        """Le document peut-il être édité ?"""
        return self.statut not in [self.Statut.VALIDE, self.Statut.ARCHIVE]

    def marquer_modifie(self):
        """Met à jour la date de dernière édition."""
        self.date_derniere_edition = timezone.now()
        self.save(update_fields=['date_derniere_edition', 'date_modification'])


class PartageDocument(models.Model):
    """
    Partage d'un document collaboratif avec un utilisateur.

    Gère les permissions d'accès au document.
    """

    class NiveauAcces(models.TextChoices):
        LECTURE = 'LECTURE', _('Lecture seule')
        COMMENTAIRE = 'COMMENTAIRE', _('Commentaire')
        EDITION = 'EDITION', _('Édition')
        ADMIN = 'ADMIN', _('Administration')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    document = models.ForeignKey(
        DocumentCollaboratif,
        on_delete=models.CASCADE,
        related_name='partages',
        verbose_name=_("Document")
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents_partages',
        verbose_name=_("Utilisateur")
    )
    niveau_acces = models.CharField(
        max_length=20,
        choices=NiveauAcces.choices,
        default=NiveauAcces.LECTURE,
        verbose_name=_("Niveau d'accès")
    )

    # Qui a partagé
    partage_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='partages_effectues',
        verbose_name=_("Partagé par"),
        null=True
    )

    # Dates
    date_partage = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de partage")
    )
    date_expiration = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date d'expiration"),
        help_text=_("Laisser vide pour un accès permanent")
    )

    # Notifications
    notifier_modifications = models.BooleanField(
        default=True,
        verbose_name=_("Notifier des modifications")
    )

    class Meta:
        verbose_name = _("Partage de document")
        verbose_name_plural = _("Partages de documents")
        unique_together = ['document', 'utilisateur']
        indexes = [
            models.Index(fields=['utilisateur', '-date_partage']),
        ]

    def __str__(self):
        return f"{self.document.titre} → {self.utilisateur}"

    @property
    def est_expire(self):
        """Le partage a-t-il expiré ?"""
        if self.date_expiration is None:
            return False
        return timezone.now() > self.date_expiration

    @property
    def peut_editer(self):
        """L'utilisateur peut-il éditer ?"""
        return self.niveau_acces in [
            self.NiveauAcces.EDITION,
            self.NiveauAcces.ADMIN
        ] and not self.est_expire


class LienPartagePublic(models.Model):
    """
    Lien de partage public pour un document.

    Permet de partager un document avec des personnes externes
    via un lien unique (avec ou sans mot de passe).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    document = models.ForeignKey(
        DocumentCollaboratif,
        on_delete=models.CASCADE,
        related_name='liens_publics',
        verbose_name=_("Document")
    )

    # Token unique pour le lien
    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("Token")
    )

    # Permissions
    permet_edition = models.BooleanField(
        default=False,
        verbose_name=_("Permettre l'édition")
    )
    permet_commentaire = models.BooleanField(
        default=True,
        verbose_name=_("Permettre les commentaires")
    )
    permet_telechargement = models.BooleanField(
        default=True,
        verbose_name=_("Permettre le téléchargement")
    )

    # Sécurité
    mot_de_passe_hash = models.CharField(
        max_length=128,
        blank=True,
        verbose_name=_("Hash du mot de passe"),
        help_text=_("Laisser vide pour un accès sans mot de passe")
    )

    # Limites
    date_expiration = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date d'expiration")
    )
    nombre_acces_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Nombre d'accès maximum")
    )
    nombre_acces = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Nombre d'accès")
    )

    # Métadonnées
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='liens_publics_crees',
        verbose_name=_("Créé par"),
        null=True
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    est_actif = models.BooleanField(
        default=True,
        verbose_name=_("Actif")
    )

    class Meta:
        verbose_name = _("Lien de partage public")
        verbose_name_plural = _("Liens de partage publics")
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['document', 'est_actif']),
        ]

    def __str__(self):
        return f"Lien public: {self.document.titre}"

    @property
    def est_valide(self):
        """Le lien est-il encore valide ?"""
        if not self.est_actif:
            return False
        if self.date_expiration and timezone.now() > self.date_expiration:
            return False
        if self.nombre_acces_max and self.nombre_acces >= self.nombre_acces_max:
            return False
        return True

    @property
    def url_complet(self):
        """URL complète du lien public."""
        from django.urls import reverse
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        return f"{base_url}/editeur/public/{self.token}/"

    def incrementer_acces(self):
        """Incrémente le compteur d'accès."""
        self.nombre_acces += 1
        self.save(update_fields=['nombre_acces'])

    def save(self, *args, **kwargs):
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class SessionEdition(models.Model):
    """
    Session d'édition en cours sur un document.

    Permet de tracker qui est en train d'éditer en temps réel.
    Synchronisé avec HocusPocus via webhook.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    document = models.ForeignKey(
        DocumentCollaboratif,
        on_delete=models.CASCADE,
        related_name='sessions_edition',
        verbose_name=_("Document")
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions_edition',
        verbose_name=_("Utilisateur")
    )

    # Session HocusPocus
    session_id = models.CharField(
        max_length=255,
        verbose_name=_("ID de session"),
        help_text=_("Identifiant de connexion WebSocket")
    )

    # Dates
    debut = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Début de session")
    )
    derniere_activite = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Dernière activité")
    )
    fin = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Fin de session")
    )

    # État
    est_active = models.BooleanField(
        default=True,
        verbose_name=_("Session active")
    )

    # Informations client
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("User Agent")
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Adresse IP")
    )

    class Meta:
        verbose_name = _("Session d'édition")
        verbose_name_plural = _("Sessions d'édition")
        indexes = [
            models.Index(fields=['document', 'est_active']),
            models.Index(fields=['utilisateur', 'est_active']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        return f"{self.utilisateur} sur {self.document.titre}"

    def terminer(self):
        """Termine la session."""
        self.est_active = False
        self.fin = timezone.now()
        self.save(update_fields=['est_active', 'fin'])


class VersionExportee(models.Model):
    """
    Version exportée d'un document collaboratif.

    Garde un historique des exports (PDF, Word, ODT).
    """

    class FormatExport(models.TextChoices):
        PDF = 'PDF', _('PDF')
        DOCX = 'DOCX', _('Word (.docx)')
        ODT = 'ODT', _('OpenDocument (.odt)')
        HTML = 'HTML', _('HTML')
        MARKDOWN = 'MD', _('Markdown')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    document = models.ForeignKey(
        DocumentCollaboratif,
        on_delete=models.CASCADE,
        related_name='versions_exportees',
        verbose_name=_("Document")
    )

    # Export
    format_export = models.CharField(
        max_length=10,
        choices=FormatExport.choices,
        verbose_name=_("Format")
    )
    fichier = models.FileField(
        upload_to='editeur/exports/%Y/%m/',
        verbose_name=_("Fichier")
    )
    taille = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Taille (octets)")
    )

    # Version du contenu
    numero_version = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Numéro de version")
    )
    hash_contenu = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("Hash du contenu"),
        help_text=_("SHA-256 du contenu source")
    )

    # Métadonnées
    exporte_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='exports_documents',
        verbose_name=_("Exporté par"),
        null=True
    )
    date_export = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date d'export")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes de version")
    )

    # Lien vers GED (si archivé)
    document_ged = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        related_name='versions_source_editeur',
        verbose_name=_("Document GED"),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _("Version exportée")
        verbose_name_plural = _("Versions exportées")
        ordering = ['-date_export']
        indexes = [
            models.Index(fields=['document', '-date_export']),
        ]

    def __str__(self):
        return f"{self.document.titre} v{self.numero_version} ({self.format_export})"


class ModeleDocument(models.Model):
    """
    Modèle (template) de document réutilisable.

    Permet de créer des documents avec un contenu pré-rempli.
    """

    class Categorie(models.TextChoices):
        FIDUCIAIRE = 'FIDUCIAIRE', _('Entreprise')
        COMPTABLE = 'COMPTABLE', _('Comptabilité')
        FISCAL = 'FISCAL', _('Fiscalité')
        RH = 'RH', _('Ressources Humaines')
        JURIDIQUE = 'JURIDIQUE', _('Juridique')
        COMMERCIAL = 'COMMERCIAL', _('Commercial')
        INTERNE = 'INTERNE', _('Usage interne')
        AUTRE = 'AUTRE', _('Autre')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Informations
    nom = models.CharField(
        max_length=200,
        verbose_name=_("Nom du modèle")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    categorie = models.CharField(
        max_length=20,
        choices=Categorie.choices,
        default=Categorie.AUTRE,
        verbose_name=_("Catégorie")
    )
    type_document = models.CharField(
        max_length=20,
        choices=DocumentCollaboratif.TypeDocument.choices,
        default=DocumentCollaboratif.TypeDocument.NOTE,
        verbose_name=_("Type de document")
    )

    # Contenu du modèle (JSON BlockNote)
    contenu_json = models.JSONField(
        default=dict,
        verbose_name=_("Contenu (BlockNote JSON)")
    )

    # Aperçu
    apercu_html = models.TextField(
        blank=True,
        verbose_name=_("Aperçu HTML")
    )

    # Métadonnées
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='modeles_crees',
        verbose_name=_("Créé par"),
        null=True
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Dernière modification")
    )

    # Visibilité
    est_public = models.BooleanField(
        default=False,
        verbose_name=_("Public"),
        help_text=_("Visible par tous les utilisateurs")
    )
    est_systeme = models.BooleanField(
        default=False,
        verbose_name=_("Modèle système"),
        help_text=_("Modèle fourni par AltiusOne")
    )

    # Langue
    langue = models.CharField(
        max_length=5,
        choices=[
            ('fr', 'Français'),
            ('de', 'Deutsch'),
            ('it', 'Italiano'),
            ('en', 'English'),
        ],
        default='fr',
        verbose_name=_("Langue")
    )

    # Statistiques
    nombre_utilisations = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Nombre d'utilisations")
    )

    class Meta:
        verbose_name = _("Modèle de document")
        verbose_name_plural = _("Modèles de documents")
        ordering = ['categorie', 'nom']
        indexes = [
            models.Index(fields=['categorie']),
            models.Index(fields=['est_public', 'categorie']),
        ]

    def __str__(self):
        return f"{self.nom} ({self.get_categorie_display()})"

    def incrementer_utilisation(self):
        """Incrémente le compteur d'utilisation."""
        self.nombre_utilisations += 1
        self.save(update_fields=['nombre_utilisations'])
