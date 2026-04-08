# apps/support/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class CategorieSupport(BaseModel):
    """
    Catégorie de support alignée sur les modules de l'application.
    Ex: Comptabilité, Facturation, Salaires, Documents, etc.
    """

    code = models.CharField(max_length=50, unique=True, verbose_name=_('Code'))
    nom = models.CharField(max_length=200, verbose_name=_('Nom'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    icone = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Icône'),
        help_text=_('Classe CSS icône (ex: ti ti-calculator, ph ph-file-text)')
    )
    couleur = models.CharField(
        max_length=20, blank=True, default='primary',
        verbose_name=_('Couleur'),
        help_text=_('Classe Bootstrap (primary, success, info, etc.)')
    )
    ordre = models.IntegerField(default=0, verbose_name=_('Ordre'))

    class Meta:
        db_table = 'support_categories'
        verbose_name = _('Catégorie support')
        verbose_name_plural = _('Catégories support')
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class ArticleSupport(BaseModel):
    """
    Article de documentation / guide utilisateur.
    Contenu Markdown multilingue (via modeltranslation), lié à une catégorie et un module.
    """

    categorie = models.ForeignKey(
        CategorieSupport, on_delete=models.CASCADE,
        related_name='articles',
        verbose_name=_('Catégorie')
    )
    titre = models.CharField(max_length=255, verbose_name=_('Titre'))
    slug = models.SlugField(
        max_length=255, unique=True,
        verbose_name=_('Slug URL')
    )
    resume = models.TextField(
        blank=True, verbose_name=_('Résumé'),
        help_text=_('Court résumé affiché dans les listes')
    )
    contenu = models.TextField(
        verbose_name=_('Contenu'),
        help_text=_('Contenu Markdown de l\'article')
    )
    module = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Module'),
        help_text=_('App Django associée (comptabilite, facturation, etc.)')
    )
    ordre = models.IntegerField(default=0, verbose_name=_('Ordre'))
    publie = models.BooleanField(default=True, verbose_name=_('Publié'))

    class Meta:
        db_table = 'support_articles'
        verbose_name = _('Article support')
        verbose_name_plural = _('Articles support')
        ordering = ['categorie', 'ordre', 'titre']
        indexes = [
            models.Index(fields=['module', 'publie']),
        ]

    def __str__(self):
        return self.titre

    def texte_pour_embedding(self):
        parts = [
            self.titre,
            self.resume,
            self.contenu[:500] if self.contenu else '',
            f"Module: {self.module}" if self.module else '',
            f"Catégorie: {self.categorie.nom}" if self.categorie_id else '',
        ]
        return ' '.join(filter(None, parts))


class VideoTutoriel(BaseModel):
    """
    Tutoriel vidéo YouTube.
    Stocke l'ID YouTube + métadonnées. La vidéo est sur YouTube.
    Titres/descriptions multilingues via modeltranslation.
    """

    categorie = models.ForeignKey(
        CategorieSupport, on_delete=models.CASCADE,
        related_name='videos',
        verbose_name=_('Catégorie')
    )
    titre = models.CharField(max_length=255, verbose_name=_('Titre'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    youtube_id = models.CharField(
        max_length=20, verbose_name=_('ID YouTube'),
        help_text=_('Ex: dQw4w9WgXcQ (partie après ?v= dans l\'URL)')
    )
    duree_secondes = models.IntegerField(
        null=True, blank=True, verbose_name=_('Durée (secondes)')
    )
    module = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Module')
    )
    ordre = models.IntegerField(default=0, verbose_name=_('Ordre'))
    publie = models.BooleanField(default=True, verbose_name=_('Publié'))

    class Meta:
        db_table = 'support_videos'
        verbose_name = _('Tutoriel vidéo')
        verbose_name_plural = _('Tutoriels vidéo')
        ordering = ['categorie', 'ordre']

    def __str__(self):
        return self.titre

    @property
    def youtube_url(self):
        return f"https://www.youtube.com/watch?v={self.youtube_id}"

    @property
    def youtube_embed_url(self):
        return f"https://www.youtube.com/embed/{self.youtube_id}"

    @property
    def thumbnail_url(self):
        return f"https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg"

    @property
    def duree_display(self):
        if not self.duree_secondes:
            return ''
        m, s = divmod(self.duree_secondes, 60)
        return f"{m}:{s:02d}"

    def texte_pour_embedding(self):
        parts = [
            f"Tutoriel vidéo: {self.titre}",
            self.description,
            f"Module: {self.module}" if self.module else '',
        ]
        return ' '.join(filter(None, parts))


class Nouveaute(BaseModel):
    """
    Note de version / changelog.
    Informe les utilisateurs des nouvelles fonctionnalités et corrections.
    Titres/contenus multilingues via modeltranslation.
    """

    TYPE_CHOICES = [
        ('NOUVEAU', _('Nouvelle fonctionnalité')),
        ('AMELIORATION', _('Amélioration')),
        ('CORRECTION', _('Correction de bug')),
        ('RUPTURE', _('Changement important')),
    ]

    version = models.CharField(max_length=20, verbose_name=_('Version'))
    date_publication = models.DateField(verbose_name=_('Date de publication'))
    titre = models.CharField(max_length=255, verbose_name=_('Titre'))
    contenu = models.TextField(
        verbose_name=_('Contenu'),
        help_text=_('Détails en Markdown')
    )
    type_changement = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='NOUVEAU',
        verbose_name=_('Type')
    )
    module = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Module concerné')
    )

    class Meta:
        db_table = 'support_nouveautes'
        verbose_name = _('Nouveauté')
        verbose_name_plural = _('Nouveautés')
        ordering = ['-date_publication', '-version']

    def __str__(self):
        return f"v{self.version} — {self.titre}"

    def texte_pour_embedding(self):
        parts = [
            f"Nouveauté v{self.version}: {self.titre}",
            self.contenu[:300] if self.contenu else '',
        ]
        return ' '.join(filter(None, parts))
