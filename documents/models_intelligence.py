# documents/models_intelligence.py
"""
Modeles pour le moteur d'intelligence AI.

- DocumentRelation: Liens semantiques entre documents
- MandatInsight: Insights proactifs generes par IA
- MandatDigest: Resumes periodiques generes par IA
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel, Mandat


class DocumentRelation(BaseModel):
    """
    Relation semantique entre deux documents detectee par IA.

    Types de relations:
    - DOUBLON: Documents quasi-identiques
    - VERSION: Versions successives d'un meme document
    - REFERENCE: Document qui en reference un autre
    - COMPLEMENT: Documents complementaires
    - CONTRADICTION: Informations contradictoires
    - REPONSE: Document repondant a un autre
    """

    TYPE_RELATION_CHOICES = [
        ('DOUBLON', 'Doublon potentiel'),
        ('VERSION', 'Version successive'),
        ('REFERENCE', 'Référence croisée'),
        ('COMPLEMENT', 'Document complémentaire'),
        ('CONTRADICTION', 'Contradiction détectée'),
        ('REPONSE', 'Réponse à'),
    ]

    document_source = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='relations_sortantes',
        verbose_name=_('Document source'),
    )
    document_cible = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='relations_entrantes',
        verbose_name=_('Document cible'),
    )
    type_relation = models.CharField(
        max_length=20,
        choices=TYPE_RELATION_CHOICES,
        verbose_name=_('Type de relation'),
    )
    score_similarite = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        verbose_name=_('Score de similarité'),
        help_text=_('Score cosinus entre 0 et 1'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Explication IA de la relation'),
    )
    confirmee = models.BooleanField(
        default=False,
        verbose_name=_('Confirmée'),
        help_text=_('Validation humaine de la relation'),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Métadonnées'),
    )

    class Meta:
        db_table = 'document_relations'
        verbose_name = _('Relation de document')
        verbose_name_plural = _('Relations de documents')
        unique_together = ['document_source', 'document_cible', 'type_relation']
        indexes = [
            models.Index(fields=['document_source', 'type_relation']),
            models.Index(fields=['score_similarite']),
        ]

    def __str__(self):
        return (
            f"{self.document_source.nom_fichier} → "
            f"{self.document_cible.nom_fichier} "
            f"({self.get_type_relation_display()})"
        )


class MandatInsight(BaseModel):
    """
    Insight proactif genere automatiquement par analyse IA.

    Detecte anomalies, doublons, documents manquants,
    tendances et recommandations pour un mandat.
    """

    TYPE_INSIGHT_CHOICES = [
        ('ANOMALIE', 'Anomalie détectée'),
        ('DOUBLON', 'Doublons détectés'),
        ('MANQUANT', 'Document manquant'),
        ('TENDANCE', 'Tendance observée'),
        ('RECOMMANDATION', 'Recommandation'),
        ('ALERTE', 'Alerte importante'),
        ('OPPORTUNITE', 'Opportunité'),
    ]

    SEVERITE_CHOICES = [
        ('INFO', 'Information'),
        ('WARNING', 'Avertissement'),
        ('CRITICAL', 'Critique'),
    ]

    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='insights',
        verbose_name=_('Mandat'),
    )
    type_insight = models.CharField(
        max_length=20,
        choices=TYPE_INSIGHT_CHOICES,
        verbose_name=_('Type d\'insight'),
    )
    severite = models.CharField(
        max_length=10,
        choices=SEVERITE_CHOICES,
        default='INFO',
        verbose_name=_('Sévérité'),
    )
    titre = models.CharField(
        max_length=255,
        verbose_name=_('Titre'),
    )
    description = models.TextField(
        verbose_name=_('Description'),
        help_text=_('Explication IA détaillée'),
    )
    donnees = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Données'),
        help_text=_('Documents concernés, montants, dates, etc.'),
    )
    documents = models.ManyToManyField(
        'documents.Document',
        blank=True,
        related_name='insights',
        verbose_name=_('Documents liés'),
    )
    lu = models.BooleanField(
        default=False,
        verbose_name=_('Lu'),
    )
    traite = models.BooleanField(
        default=False,
        verbose_name=_('Traité'),
    )
    date_expiration = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date d\'expiration'),
        help_text=_('Auto-archivage après cette date'),
    )

    class Meta:
        db_table = 'mandat_insights'
        verbose_name = _('Insight de mandat')
        verbose_name_plural = _('Insights de mandat')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mandat', 'type_insight']),
            models.Index(fields=['severite']),
            models.Index(fields=['lu']),
            models.Index(fields=['traite']),
        ]

    def __str__(self):
        return f"[{self.get_severite_display()}] {self.titre}"


class MandatDigest(BaseModel):
    """
    Resume periodique genere par IA pour un mandat.

    Types: hebdomadaire, mensuel, trimestriel.
    """

    TYPE_DIGEST_CHOICES = [
        ('HEBDOMADAIRE', 'Hebdomadaire'),
        ('MENSUEL', 'Mensuel'),
        ('TRIMESTRIEL', 'Trimestriel'),
    ]

    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='digests',
        verbose_name=_('Mandat'),
    )
    type_digest = models.CharField(
        max_length=15,
        choices=TYPE_DIGEST_CHOICES,
        verbose_name=_('Type de digest'),
    )
    periode_debut = models.DateField(
        verbose_name=_('Début de période'),
    )
    periode_fin = models.DateField(
        verbose_name=_('Fin de période'),
    )
    resume = models.TextField(
        verbose_name=_('Résumé'),
        help_text=_('Résumé IA de la période'),
    )
    points_cles = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Points clés'),
        help_text=_('Liste de faits saillants'),
    )
    statistiques = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Statistiques'),
        help_text=_('Nombre de documents, montants, anomalies, etc.'),
    )
    insights_periode = models.ManyToManyField(
        MandatInsight,
        blank=True,
        related_name='digests',
        verbose_name=_('Insights de la période'),
    )
    documents_periode = models.ManyToManyField(
        'documents.Document',
        blank=True,
        related_name='digests',
        verbose_name=_('Documents de la période'),
    )

    class Meta:
        db_table = 'mandat_digests'
        verbose_name = _('Digest de mandat')
        verbose_name_plural = _('Digests de mandat')
        unique_together = ['mandat', 'type_digest', 'periode_debut']
        ordering = ['-periode_fin']

    def __str__(self):
        return (
            f"{self.get_type_digest_display()} - "
            f"{self.mandat.numero} "
            f"({self.periode_debut} → {self.periode_fin})"
        )
