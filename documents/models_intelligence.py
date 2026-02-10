# documents/models_intelligence.py
"""
Modeles pour le moteur d'intelligence AI.

- DocumentRelation: Liens semantiques entre documents
- MandatInsight: Insights proactifs generes par IA
- MandatDigest: Resumes periodiques generes par IA
"""
from django.db import models
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
        verbose_name='Document source',
    )
    document_cible = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='relations_entrantes',
        verbose_name='Document cible',
    )
    type_relation = models.CharField(
        max_length=20,
        choices=TYPE_RELATION_CHOICES,
        verbose_name='Type de relation',
    )
    score_similarite = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        verbose_name='Score de similarité',
        help_text='Score cosinus entre 0 et 1',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Explication IA de la relation',
    )
    confirmee = models.BooleanField(
        default=False,
        verbose_name='Confirmée',
        help_text='Validation humaine de la relation',
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Métadonnées',
    )

    class Meta:
        db_table = 'document_relations'
        verbose_name = 'Relation de document'
        verbose_name_plural = 'Relations de documents'
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
        verbose_name='Mandat',
    )
    type_insight = models.CharField(
        max_length=20,
        choices=TYPE_INSIGHT_CHOICES,
        verbose_name='Type d\'insight',
    )
    severite = models.CharField(
        max_length=10,
        choices=SEVERITE_CHOICES,
        default='INFO',
        verbose_name='Sévérité',
    )
    titre = models.CharField(
        max_length=255,
        verbose_name='Titre',
    )
    description = models.TextField(
        verbose_name='Description',
        help_text='Explication IA détaillée',
    )
    donnees = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Données',
        help_text='Documents concernés, montants, dates, etc.',
    )
    documents = models.ManyToManyField(
        'documents.Document',
        blank=True,
        related_name='insights',
        verbose_name='Documents liés',
    )
    lu = models.BooleanField(
        default=False,
        verbose_name='Lu',
    )
    traite = models.BooleanField(
        default=False,
        verbose_name='Traité',
    )
    date_expiration = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date d\'expiration',
        help_text='Auto-archivage après cette date',
    )

    class Meta:
        db_table = 'mandat_insights'
        verbose_name = 'Insight de mandat'
        verbose_name_plural = 'Insights de mandat'
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
        verbose_name='Mandat',
    )
    type_digest = models.CharField(
        max_length=15,
        choices=TYPE_DIGEST_CHOICES,
        verbose_name='Type de digest',
    )
    periode_debut = models.DateField(
        verbose_name='Début de période',
    )
    periode_fin = models.DateField(
        verbose_name='Fin de période',
    )
    resume = models.TextField(
        verbose_name='Résumé',
        help_text='Résumé IA de la période',
    )
    points_cles = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Points clés',
        help_text='Liste de faits saillants',
    )
    statistiques = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Statistiques',
        help_text='Nombre de documents, montants, anomalies, etc.',
    )
    insights_periode = models.ManyToManyField(
        MandatInsight,
        blank=True,
        related_name='digests',
        verbose_name='Insights de la période',
    )
    documents_periode = models.ManyToManyField(
        'documents.Document',
        blank=True,
        related_name='digests',
        verbose_name='Documents de la période',
    )

    class Meta:
        db_table = 'mandat_digests'
        verbose_name = 'Digest de mandat'
        verbose_name_plural = 'Digests de mandat'
        unique_together = ['mandat', 'type_digest', 'periode_debut']
        ordering = ['-periode_fin']

    def __str__(self):
        return (
            f"{self.get_type_digest_display()} - "
            f"{self.mandat.numero} "
            f"({self.periode_debut} → {self.periode_fin})"
        )
