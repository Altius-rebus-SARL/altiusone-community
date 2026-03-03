# graph/models.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.contrib.postgres.indexes import GistIndex
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from pgvector.django import VectorField, HnswIndex

from core.models import BaseModel


class OntologieType(BaseModel):
    """Définition d'un type d'entité ou de relation dans l'ontologie."""

    class Categorie(models.TextChoices):
        ENTITY = 'entity', _('Entité')
        RELATION = 'relation', _('Relation')

    categorie = models.CharField(
        max_length=10,
        choices=Categorie.choices,
        verbose_name=_('Catégorie'),
    )
    nom = models.CharField(max_length=100, verbose_name=_('Nom'))
    nom_pluriel = models.CharField(
        max_length=100, blank=True, verbose_name=_('Nom pluriel'),
    )
    description = models.TextField(blank=True, verbose_name=_('Description'))
    icone = models.CharField(
        max_length=50, blank=True, default='ph-circle',
        verbose_name=_('Icône'),
        help_text=_('Classe Phosphor Icons (ex: ph-user, ph-building)'),
    )
    couleur = models.CharField(
        max_length=7, default='#6366f1',
        verbose_name=_('Couleur'),
        help_text=_('Code hexadécimal (ex: #6366f1)'),
    )
    schema_attributs = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Schéma des attributs'),
        help_text=_('Schéma JSON décrivant les champs dynamiques'),
    )

    # Contraintes pour les relations (types source/cible autorisés)
    source_types_autorises = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='relation_sources',
        verbose_name=_('Types source autorisés'),
        help_text=_('Types d\'entités pouvant être source de cette relation'),
    )
    cible_types_autorises = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='relation_cibles',
        verbose_name=_('Types cible autorisés'),
        help_text=_('Types d\'entités pouvant être cible de cette relation'),
    )

    # Verbes pour les relations
    verbe = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Verbe'),
        help_text=_('Ex: "emploie", "possède"'),
    )
    verbe_inverse = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Verbe inverse'),
        help_text=_('Ex: "est employé par", "est possédé par"'),
    )
    bidirectionnel = models.BooleanField(
        default=False,
        verbose_name=_('Bidirectionnel'),
    )
    ordre_affichage = models.PositiveIntegerField(
        default=0, verbose_name=_('Ordre d\'affichage'),
    )

    class Meta:
        ordering = ['ordre_affichage', 'nom']
        verbose_name = _('Type d\'ontologie')
        verbose_name_plural = _('Types d\'ontologie')
        indexes = [
            models.Index(fields=['categorie', 'nom'], name='graph_onttype_cat_nom_idx'),
        ]

    def __str__(self):
        return f"{self.get_categorie_display()}: {self.nom}"


class Entite(BaseModel):
    """Nœud du graphe relationnel."""

    class Source(models.TextChoices):
        MANUELLE = 'manuelle', _('Saisie manuelle')
        IMPORT = 'import', _('Import CSV/Excel')
        OCR = 'ocr', _('Extraction OCR')
        API = 'api', _('API externe')
        SYSTEME = 'systeme', _('Système')

    type = models.ForeignKey(
        OntologieType,
        on_delete=models.PROTECT,
        related_name='entites',
        limit_choices_to={'categorie': OntologieType.Categorie.ENTITY},
        verbose_name=_('Type'),
    )
    nom = models.CharField(max_length=255, verbose_name=_('Nom'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    attributs = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Attributs'),
        help_text=_('Attributs dynamiques selon le schéma du type'),
    )

    # Géolocalisation
    geom = gis_models.PointField(
        srid=4326, null=True, blank=True,
        verbose_name=_('Géolocalisation'),
    )

    # Embedding vectoriel pour recherche sémantique
    embedding = VectorField(dimensions=768, null=True, blank=True)
    embedding_updated_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Embedding mis à jour le'),
    )

    # Provenance et confiance
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUELLE,
        verbose_name=_('Source'),
    )
    confiance = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_('Score de confiance'),
    )
    verifie = models.BooleanField(default=False, verbose_name=_('Vérifié'))
    verifie_par = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='entites_verifiees',
        verbose_name=_('Vérifié par'),
    )
    verifie_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Vérifié le'),
    )

    # Lien générique vers un objet Django existant
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    tags = models.JSONField(
        default=list, blank=True, verbose_name=_('Tags'),
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Entité')
        verbose_name_plural = _('Entités')
        indexes = [
            models.Index(fields=['type', 'nom'], name='graph_entite_type_nom_idx'),
            models.Index(fields=['source', 'confiance'], name='graph_entite_src_conf_idx'),
            models.Index(fields=['content_type', 'object_id'], name='graph_entite_gfk_idx'),
            GistIndex(fields=['geom'], name='graph_entite_geom_gist_idx'),
            HnswIndex(
                fields=['embedding'],
                name='graph_entite_emb_hnsw_idx',
                m=16, ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]

    def __str__(self):
        return self.nom

    def texte_pour_embedding(self):
        """Concatène les champs pertinents pour générer un embedding."""
        parts = [self.type.nom, self.nom]
        if self.description:
            parts.append(self.description)
        if self.attributs:
            for key, val in self.attributs.items():
                if val:
                    parts.append(f"{key}: {val}")
        if self.tags:
            parts.append(" ".join(str(t) for t in self.tags))
        return " | ".join(parts)


class Relation(BaseModel):
    """Lien typé entre deux entités du graphe."""

    type = models.ForeignKey(
        OntologieType,
        on_delete=models.PROTECT,
        related_name='relations',
        limit_choices_to={'categorie': OntologieType.Categorie.RELATION},
        verbose_name=_('Type de relation'),
    )
    source = models.ForeignKey(
        Entite,
        on_delete=models.CASCADE,
        related_name='relations_sortantes',
        verbose_name=_('Entité source'),
    )
    cible = models.ForeignKey(
        Entite,
        on_delete=models.CASCADE,
        related_name='relations_entrantes',
        verbose_name=_('Entité cible'),
    )
    attributs = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Attributs'),
    )
    poids = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0)],
        verbose_name=_('Poids'),
    )
    date_debut = models.DateField(
        null=True, blank=True, verbose_name=_('Date de début'),
    )
    date_fin = models.DateField(
        null=True, blank=True, verbose_name=_('Date de fin'),
    )
    en_cours = models.BooleanField(
        default=True, verbose_name=_('En cours'),
    )
    document_preuve = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='relations_graphe',
        verbose_name=_('Document preuve'),
    )
    confiance = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_('Score de confiance'),
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Relation')
        verbose_name_plural = _('Relations')
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'cible', 'type'],
                name='graph_relation_unique_src_cbl_type',
            ),
        ]
        indexes = [
            models.Index(fields=['type', 'en_cours'], name='graph_rel_type_encours_idx'),
            models.Index(fields=['date_debut', 'date_fin'], name='graph_rel_dates_idx'),
        ]

    def __str__(self):
        verbe = self.type.verbe or self.type.nom
        return f"{self.source.nom} → {verbe} → {self.cible.nom}"


class Anomalie(BaseModel):
    """Anomalie détectée automatiquement dans le graphe."""

    class TypeAnomalie(models.TextChoices):
        DOUBLON = 'doublon', _('Doublon potentiel')
        FLUX_SUSPECT = 'flux_suspect', _('Flux suspect')
        INCOHERENCE = 'incoherence', _('Incohérence temporelle')
        CONNEXION_CACHEE = 'connexion_cachee', _('Connexion cachée')
        ORPHELIN = 'orphelin', _('Entité orpheline')

    class Statut(models.TextChoices):
        NOUVEAU = 'nouveau', _('Nouveau')
        EN_COURS = 'en_cours', _('En cours d\'analyse')
        CONFIRME = 'confirme', _('Confirmé')
        REJETE = 'rejete', _('Rejeté')
        RESOLU = 'resolu', _('Résolu')

    type = models.CharField(
        max_length=20,
        choices=TypeAnomalie.choices,
        verbose_name=_('Type d\'anomalie'),
    )
    entite = models.ForeignKey(
        Entite,
        on_delete=models.CASCADE,
        related_name='anomalies',
        verbose_name=_('Entité concernée'),
    )
    entite_liee = models.ForeignKey(
        Entite,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='anomalies_liees',
        verbose_name=_('Entité liée'),
    )
    titre = models.CharField(max_length=255, verbose_name=_('Titre'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_('Score de confiance'),
    )
    details = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Détails'),
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.NOUVEAU,
        verbose_name=_('Statut'),
    )
    traite_par = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='anomalies_traitees',
        verbose_name=_('Traité par'),
    )
    traite_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Traité le'),
    )
    commentaire_resolution = models.TextField(
        blank=True, verbose_name=_('Commentaire de résolution'),
    )

    class Meta:
        ordering = ['-score', '-created_at']
        verbose_name = _('Anomalie')
        verbose_name_plural = _('Anomalies')
        indexes = [
            models.Index(fields=['type', 'statut'], name='graph_anom_type_statut_idx'),
            models.Index(fields=['score'], name='graph_anom_score_idx'),
        ]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.titre}"


class RequeteSauvegardee(BaseModel):
    """Requête sauvegardée pour exploration du graphe."""

    nom = models.CharField(max_length=200, verbose_name=_('Nom'))
    description = models.TextField(blank=True, verbose_name=_('Description'))

    # Paramètres de la requête
    entite_depart = models.ForeignKey(
        Entite,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name=_('Entité de départ'),
    )
    types_entites = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Types d\'entités'),
        help_text=_('Liste des IDs de types d\'entités à inclure'),
    )
    types_relations = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Types de relations'),
        help_text=_('Liste des IDs de types de relations à inclure'),
    )
    profondeur = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_('Profondeur'),
    )
    date_min = models.DateField(
        null=True, blank=True, verbose_name=_('Date minimum'),
    )
    date_max = models.DateField(
        null=True, blank=True, verbose_name=_('Date maximum'),
    )

    # Paramètres de vue D3.js
    parametres_vue = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Paramètres de vue'),
        help_text=_('Position caméra, zoom, filtres visuels, etc.'),
    )
    partage = models.BooleanField(
        default=False, verbose_name=_('Partagée'),
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Requête sauvegardée')
        verbose_name_plural = _('Requêtes sauvegardées')

    def __str__(self):
        return self.nom
