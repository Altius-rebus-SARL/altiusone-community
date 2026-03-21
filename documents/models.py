# apps/documents/models.py
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.utils.translation import gettext_lazy as _
from pgvector.django import VectorField, HnswIndex
from core.models import BaseModel, Mandat, Client, User
from core.storage import DocumentStorage
import hashlib
import os
import uuid


def document_upload_path(instance, filename):
    """
    Génère le chemin d'upload pour un document dans MinIO/S3.
    Format: {client_id}/{mandat_id}/{dossier_chemin_ou_non_classes}/{uuid}/{filename}

    L'arborescence MinIO reflète la hiérarchie métier :
    Client → Mandat → Dossier (ou _non_classes) → fichier
    """
    parts = []

    # Client (via le mandat)
    if instance.mandat_id:
        if hasattr(instance, 'mandat') and instance.mandat:
            parts.append(str(instance.mandat.client_id))
        parts.append(str(instance.mandat_id))

    # Dossier ou non classé
    if instance.dossier_id and hasattr(instance, 'dossier') and instance.dossier:
        # Utiliser le chemin du dossier (remplacer / par _ pour compatibilité S3)
        chemin = instance.dossier.chemin_complet.replace('/', '_')
        parts.append(chemin)
    else:
        parts.append('_non_classes')

    # UUID unique pour éviter les collisions de noms
    parts.append(str(uuid.uuid4()))
    parts.append(filename)

    return '/'.join(parts)


class Dossier(BaseModel):
    """Dossier/Répertoire dans la GED"""

    TYPE_CHOICES = [
        ('RACINE', _('Racine')),
        ('CLIENT', _('Dossier client')),
        ('MANDAT', _('Dossier mandat')),
        ('EXERCICE', _('Exercice comptable')),
        ('STANDARD', _('Dossier standard')),
        ('ARCHIVE', _('Archive')),
    ]

    # Hiérarchie
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='sous_dossiers',
        verbose_name=_('Dossier parent'),
        help_text=_('Dossier contenant celui-ci')
    )

    # Rattachement
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='dossiers',
        verbose_name=_('Client'),
        help_text=_('Client propriétaire du dossier')
    )
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='dossiers',
        verbose_name=_('Mandat'),
        help_text=_('Mandat associé au dossier')
    )

    # Identification
    nom = models.CharField(
        max_length=255,
        verbose_name=_('Nom'),
        help_text=_('Nom du dossier')
    )
    type_dossier = models.CharField(
        max_length=20, choices=TYPE_CHOICES,
        verbose_name=_('Type de dossier'),
        help_text=_('Catégorie du dossier')
    )

    # Chemin complet (dénormalisé pour performance)
    chemin_complet = models.CharField(
        max_length=1000, db_index=True,
        verbose_name=_('Chemin complet'),
        help_text=_('Chemin d\'accès complet dans l\'arborescence')
    )
    niveau = models.IntegerField(
        default=0,
        verbose_name=_('Niveau'),
        help_text=_('Profondeur dans l\'arborescence')
    )

    # Métadonnées
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description du contenu du dossier')
    )
    tags = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Tags'),
        help_text=_('Étiquettes pour faciliter la recherche')
    )

    # Droits d'accès
    proprietaire = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='dossiers_proprietaire',
        verbose_name=_('Propriétaire'),
        help_text=_('Utilisateur propriétaire du dossier')
    )
    acces_restreint = models.BooleanField(
        default=False,
        verbose_name=_('Accès restreint'),
        help_text=_('Limiter l\'accès aux utilisateurs autorisés')
    )
    utilisateurs_autorises = models.ManyToManyField(
        User, blank=True,
        related_name='dossiers_autorises',
        verbose_name=_('Utilisateurs autorisés'),
        help_text=_('Utilisateurs ayant accès si accès restreint')
    )

    # Statistiques (dénormalisé)
    nombre_documents = models.IntegerField(
        default=0,
        verbose_name=_('Nombre de documents'),
        help_text=_('Nombre de documents dans ce dossier')
    )
    taille_totale = models.BigIntegerField(
        default=0,
        verbose_name=_('Taille totale'),
        help_text=_('Taille totale des documents en octets')
    )

    class Meta:
        db_table = 'dossiers'
        verbose_name = _('Dossier')
        verbose_name_plural = _('Dossiers')
        ordering = ['chemin_complet']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['mandat']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        return self.chemin_complet

    def clean(self):
        """Validation métier : cohérence client/mandat."""
        from django.core.exceptions import ValidationError

        # Si mandat et client sont fournis, vérifier la cohérence
        if self.mandat_id and self.client_id:
            if self.mandat.client_id != self.client_id:
                raise ValidationError({
                    'client': _('Le client doit correspondre au client du mandat.'),
                })

        # Si mandat est fourni sans client, auto-remplir le client
        if self.mandat_id and not self.client_id:
            self.client = self.mandat.client

    def save(self, *args, **kwargs):
        # Auto-remplir le client depuis le mandat
        if self.mandat_id and not self.client_id:
            self.client_id = self.mandat.client_id

        # Calcul du chemin complet
        old_chemin = None
        if self.pk:
            try:
                old = Dossier.objects.only('chemin_complet').get(pk=self.pk)
                old_chemin = old.chemin_complet
            except Dossier.DoesNotExist:
                pass

        if self.parent:
            self.chemin_complet = f"{self.parent.chemin_complet}/{self.nom}"
            self.niveau = self.parent.niveau + 1
        else:
            self.chemin_complet = self.nom
            self.niveau = 0

        super().save(*args, **kwargs)

        # Propager le changement de chemin aux sous-dossiers
        if old_chemin and old_chemin != self.chemin_complet:
            self._propager_chemin_enfants(old_chemin, self.chemin_complet)

    def _propager_chemin_enfants(self, ancien_prefixe, nouveau_prefixe):
        """Propage le changement de chemin à tous les sous-dossiers."""
        for enfant in self.sous_dossiers.all():
            enfant.chemin_complet = enfant.chemin_complet.replace(
                ancien_prefixe, nouveau_prefixe, 1
            )
            enfant.save(update_fields=['chemin_complet'])

    def mettre_a_jour_stats(self):
        """Met à jour les champs dénormalisés nombre_documents et taille_totale."""
        from django.db.models import Count, Sum
        stats = self.documents.filter(is_active=True).aggregate(
            count=Count('id'),
            size=Sum('taille')
        )
        self.nombre_documents = stats['count'] or 0
        self.taille_totale = stats['size'] or 0
        self.save(update_fields=['nombre_documents', 'taille_totale'])

    def get_path_display(self, include_context=True):
        """
        Retourne le chemin avec séparateurs visuels.

        Args:
            include_context: Si True, ajoute le contexte (mandat/client) pour
                            éviter la confusion entre dossiers homonymes
        """
        path = self.chemin_complet.replace('/', ' > ')
        if include_context:
            if self.mandat_id:
                return f"{path} [{self.mandat.numero if hasattr(self, '_mandat_cache') or self.mandat else '...'}]"
            elif self.client_id:
                return f"{path} [{self.client.nom if hasattr(self, '_client_cache') or self.client else '...'}]"
        return path

    def get_display_with_context(self):
        """
        Retourne un affichage complet avec contexte pour les select.
        Utile pour distinguer les dossiers homonymes.
        """
        if self.mandat_id:
            try:
                mandat_info = self.mandat.numero
            except:
                mandat_info = "?"
            return f"{self.nom} [{mandat_info}]"
        elif self.client_id:
            try:
                client_info = self.client.nom
            except:
                client_info = "?"
            return f"{self.nom} [{client_info}]"
        return self.nom

    def get_total_documents_recursive(self):
        """
        Calcule le nombre total de documents dans ce dossier
        et tous ses sous-dossiers récursivement.
        """
        # Documents directs dans ce dossier
        total = self.documents.filter(is_active=True).count()
        # Ajouter les documents de tous les sous-dossiers
        for sous_dossier in self.sous_dossiers.filter(is_active=True):
            total += sous_dossier.get_total_documents_recursive()
        return total

    def get_total_size_recursive(self):
        """
        Calcule la taille totale des documents dans ce dossier
        et tous ses sous-dossiers récursivement.
        """
        from django.db.models import Sum
        # Taille des documents directs
        total = self.documents.filter(is_active=True).aggregate(
            total=Sum('taille')
        )['total'] or 0
        # Ajouter la taille des sous-dossiers
        for sous_dossier in self.sous_dossiers.filter(is_active=True):
            total += sous_dossier.get_total_size_recursive()
        return total


class SourceDocument(BaseModel):
    """
    Source/origine d'un document dans la GED.

    Table dynamique avec données prédéfinies. La distinction interne/externe
    reflète le type d'utilisateur à l'origine du document :

    - INTERNE : document produit par un collaborateur STAFF de la fiduciaire
      (employé ou prestataire). Inclut les uploads manuels, les PDF générés
      par les modules (facturation, salaires, comptabilité, etc.), les exports.

    - EXTERNE : document produit par un utilisateur CLIENT (client externe
      ou ses collaborateurs) via le portail client, par email, par scan, etc.
      Ces documents ne sont visibles que sur les mandats concernés (AccesMandat).
    """

    ORIGINE_INTERNE = 'INTERNE'
    ORIGINE_EXTERNE = 'EXTERNE'
    ORIGINE_CHOICES = [
        (ORIGINE_INTERNE, _('Interne (collaborateur fiduciaire)')),
        (ORIGINE_EXTERNE, _('Externe (client et ses collaborateurs)')),
    ]

    code = models.CharField(
        max_length=50, unique=True,
        verbose_name=_('Code'),
        help_text=_('Code technique unique de la source')
    )
    libelle = models.CharField(
        max_length=150,
        verbose_name=_('Libellé'),
        help_text=_('Nom affiché de la source')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description détaillée de la source')
    )
    origine = models.CharField(
        max_length=10,
        choices=ORIGINE_CHOICES,
        verbose_name=_('Origine'),
        help_text=_(
            'Interne = collaborateur STAFF de la fiduciaire, '
            'Externe = utilisateur CLIENT et ses collaborateurs'
        )
    )

    # Module applicatif associé (si la source est liée à un module)
    module_applicatif = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Module applicatif'),
        help_text=_('Nom du module Django associé (ex: facturation, salaires)')
    )

    # Icône pour UI
    icone = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Icône'),
        help_text=_('Nom de l\'icône (ex: upload, file-invoice)')
    )

    # Ordre d'affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name=_('Ordre'),
        help_text=_('Position d\'affichage dans les listes')
    )

    class Meta:
        db_table = 'sources_document'
        verbose_name = _('Source de document')
        verbose_name_plural = _('Sources de document')
        ordering = ['origine', 'ordre', 'libelle']

    def __str__(self):
        return f"[{self.get_origine_display()}] {self.libelle}"

    @property
    def est_interne(self):
        """Source provenant d'un collaborateur STAFF de la fiduciaire."""
        return self.origine == self.ORIGINE_INTERNE

    @property
    def est_externe(self):
        """Source provenant d'un utilisateur CLIENT externe."""
        return self.origine == self.ORIGINE_EXTERNE


class CategorieDocument(BaseModel):
    """Catégories de documents"""

    nom = models.CharField(
        max_length=100, unique=True,
        verbose_name=_('Nom'),
        help_text=_('Nom de la catégorie')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description de la catégorie')
    )

    # Classification automatique
    mots_cles = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Mots-clés'),
        help_text=_('Mots-clés pour classification automatique')
    )
    patterns_regex = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Patterns regex'),
        help_text=_('Expressions régulières pour détection automatique')
    )

    # Icône et couleur pour UI
    icone = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Icône'),
        help_text=_('Nom de l\'icône (ex: folder, file-text)')
    )
    couleur = models.CharField(
        max_length=7, blank=True,
        verbose_name=_('Couleur'),
        help_text=_('Code couleur hexadécimal (ex: #FF5733)')
    )

    # Ordre affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name=_('Ordre'),
        help_text=_('Position d\'affichage dans la liste')
    )

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='sous_categories',
        verbose_name=_('Catégorie parente'),
        help_text=_('Catégorie de niveau supérieur')
    )

    class Meta:
        db_table = 'categories_document'
        verbose_name = _('Catégorie de document')
        verbose_name_plural = _('Catégories de document')
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class TypeDocument(BaseModel):
    """Types de documents spécifiques"""

    TYPE_CHOICES = [
        ('FACTURE_VENTE', _('Facture de vente')),
        ('FACTURE_ACHAT', _("Facture d\'achat")),
        ('DEVIS', _('Devis')),
        ('BON_COMMANDE', _('Bon de commande')),
        ('BON_LIVRAISON', _('Bon de livraison')),
        ('RELEVE_BANQUE', _('Relevé bancaire')),
        ('JUSTIFICATIF', _('Justificatif')),
        ('CONTRAT', _('Contrat')),
        ('STATUTS', _('Statuts')),
        ('PV_ASSEMBLEE', _('PV Assemblée')),
        ('DECLARATION_TVA', _('Déclaration TVA')),
        ('FICHE_SALAIRE', _('Fiche de salaire')),
        ('CERTIFICAT_SALAIRE', _('Certificat de salaire')),
        ('ATTESTATION', _('Attestation')),
        ('COURRIER', _('Courrier')),
        ('EMAIL', _('Email')),
        ('AUTRE', _('Autre')),
    ]

    code = models.CharField(
        max_length=50, unique=True,
        verbose_name=_('Code'),
        help_text=_('Code unique du type de document')
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_('Libellé'),
        help_text=_('Nom affiché du type de document')
    )
    type_document = models.CharField(
        max_length=50, choices=TYPE_CHOICES,
        verbose_name=_('Type de document'),
        help_text=_('Catégorie prédéfinie du document')
    )

    categorie = models.ForeignKey(
        CategorieDocument, on_delete=models.PROTECT,
        related_name='types_document',
        verbose_name=_('Catégorie'),
        help_text=_('Catégorie à laquelle appartient ce type')
    )

    # Extraction automatique
    champs_extraire = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Champs à extraire'),
        help_text=_('Liste des champs à extraire automatiquement (montant, date, etc.)')
    )

    # Template OCR/AI
    template_extraction = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Template d\'extraction'),
        help_text=_('Configuration du template pour l\'extraction AI/OCR')
    )

    # Workflow
    validation_requise = models.BooleanField(
        default=False,
        verbose_name=_('Validation requise'),
        help_text=_('Exiger une validation manuelle pour ce type')
    )
    validateurs = models.ManyToManyField(
        User, blank=True,
        related_name='types_doc_validation',
        verbose_name=_('Validateurs'),
        help_text=_('Utilisateurs habilités à valider ce type de document')
    )

    class Meta:
        db_table = 'types_document'
        verbose_name = _('Type de document')
        verbose_name_plural = _('Types de document')
        ordering = ['libelle']

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class Document(BaseModel):
    """Document dans la GED"""

    STATUT_TRAITEMENT_CHOICES = [
        ('UPLOAD', _('Uploadé')),
        ('OCR_EN_COURS', _('OCR en cours')),
        ('OCR_TERMINE', _('OCR terminé')),
        ('CLASSIFICATION_EN_COURS', _('Classification en cours')),
        ('CLASSIFICATION_TERMINEE', _('Classification terminée')),
        ('EXTRACTION_EN_COURS', _('Extraction données en cours')),
        ('EXTRACTION_TERMINEE', _('Extraction terminée')),
        ('VALIDE', _('Validé')),
        ('ERREUR', _('Erreur traitement')),
    ]

    STATUT_VALIDATION_CHOICES = [
        ('EN_ATTENTE', _('En attente validation')),
        ('VALIDE', _('Validé')),
        ('REJETE', _('Rejeté')),
    ]

    # Rattachement
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('Mandat'),
        help_text=_('Mandat auquel appartient ce document')
    )
    dossier = models.ForeignKey(
        Dossier, on_delete=models.SET_NULL,
        related_name='documents',
        null=True, blank=True,
        verbose_name=_('Dossier'),
        help_text=_('Dossier de classement. SET_NULL si le dossier est supprimé (le document reste).')
    )

    # Fichier
    nom_fichier = models.CharField(
        max_length=255, db_index=True,
        verbose_name=_('Nom du fichier'),
        help_text=_('Nom du fichier stocké')
    )
    nom_original = models.CharField(
        max_length=255,
        verbose_name=_('Nom original'),
        help_text=_('Nom du fichier lors de l\'upload')
    )
    extension = models.CharField(
        max_length=10,
        verbose_name=_('Extension'),
        help_text=_('Extension du fichier (pdf, jpg, etc.)')
    )
    mime_type = models.CharField(
        max_length=100,
        verbose_name=_('Type MIME'),
        help_text=_('Type MIME du fichier')
    )
    taille = models.BigIntegerField(
        verbose_name=_('Taille'),
        help_text=_('Taille du fichier en octets')
    )

    # Stockage - FileField avec storage S3/MinIO
    fichier = models.FileField(
        storage=DocumentStorage(),
        upload_to=document_upload_path,
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_('Fichier'),
        help_text=_('Fichier stocké dans S3/MinIO')
    )
    hash_fichier = models.CharField(
        max_length=64, db_index=True,
        verbose_name=_('Hash du fichier'),
        help_text=_('Empreinte SHA-256 pour déduplication (non unique : un même fichier peut être dans plusieurs mandats)')
    )

    # Source / Origine
    source = models.ForeignKey(
        SourceDocument, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name=_('Source'),
        help_text=_('Origine du document (upload, module interne, import, etc.)')
    )

    # Classification
    type_document = models.ForeignKey(
        TypeDocument, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Type de document'),
        help_text=_('Type de document identifié')
    )
    categorie = models.ForeignKey(
        CategorieDocument, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Catégorie'),
        help_text=_('Catégorie de classement')
    )

    # Dates
    date_document = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_('Date du document'),
        help_text=_('Date figurant sur le document')
    )
    date_upload = models.DateTimeField(
        auto_now_add=True, db_index=True,
        verbose_name=_('Date d\'upload'),
        help_text=_('Date et heure de téléchargement')
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Date de modification'),
        help_text=_('Dernière modification')
    )

    # OCR et extraction
    ocr_text = models.TextField(
        blank=True,
        verbose_name=_('Texte OCR'),
        help_text=_('Texte extrait par reconnaissance optique')
    )
    ocr_confidence = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Confiance OCR'),
        help_text=_('Score de confiance de l\'OCR (0-100)')
    )

    metadata_extraite = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Métadonnées extraites'),
        help_text=_('Données extraites automatiquement (montants, dates, etc.)')
    )

    # Classification AI
    prediction_type = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Type prédit'),
        help_text=_('Type de document prédit par l\'IA')
    )
    prediction_confidence = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Confiance prédiction'),
        help_text=_('Score de confiance de la prédiction (0-100)')
    )

    # Tags et recherche
    tags = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Tags'),
        help_text=_('Étiquettes manuelles')
    )
    tags_auto = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Tags automatiques'),
        help_text=_('Étiquettes générées automatiquement')
    )

    # Statuts
    statut_traitement = models.CharField(
        max_length=30,
        choices=STATUT_TRAITEMENT_CHOICES,
        default='UPLOAD', db_index=True,
        verbose_name=_('Statut de traitement'),
        help_text=_('État du traitement automatique')
    )
    statut_validation = models.CharField(
        max_length=20,
        choices=STATUT_VALIDATION_CHOICES,
        default='EN_ATTENTE',
        null=True, blank=True,
        verbose_name=_('Statut de validation'),
        help_text=_('État de la validation manuelle')
    )

    # Validation
    valide_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents_valides',
        verbose_name=_('Validé par'),
        help_text=_('Utilisateur ayant validé le document')
    )
    date_validation = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Date de validation'),
        help_text=_('Date et heure de validation')
    )
    commentaire_validation = models.TextField(
        blank=True,
        verbose_name=_('Commentaire de validation'),
        help_text=_('Remarques du validateur')
    )

    # Liens avec autres entités
    ecriture_comptable = models.ForeignKey(
        'comptabilite.EcritureComptable',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name=_('Écriture comptable'),
        help_text=_('Écriture comptable associée')
    )
    facture = models.ForeignKey(
        'facturation.Facture', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name=_('Facture'),
        help_text=_('Facture associée')
    )
    fiche_salaire = models.ForeignKey(
        'salaires.FicheSalaire',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name=_('Fiche de salaire'),
        help_text=_('Fiche de salaire associée')
    )

    # Sécurité
    confidentiel = models.BooleanField(
        default=False,
        verbose_name=_('Confidentiel'),
        help_text=_('Marquer comme document confidentiel')
    )

    # Description
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description du document')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes'),
        help_text=_('Notes et remarques internes')
    )

    class Meta:
        db_table = 'documents'
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-date_upload']
        indexes = [
            models.Index(fields=['mandat', 'date_upload']),
            models.Index(fields=['type_document', 'date_document']),
            models.Index(fields=['statut_traitement']),
            models.Index(fields=['hash_fichier']),
        ]

    def __str__(self):
        return f"{self.nom_fichier} - {self.mandat.numero}"

    def save(self, *args, **kwargs):
        # Calcul hash si pas déjà fait
        if not self.hash_fichier and hasattr(self, '_file_content'):
            self.hash_fichier = hashlib.sha256(self._file_content).hexdigest()

        # Extension à partir du nom
        if not self.extension:
            self.extension = os.path.splitext(self.nom_original)[1].lower()

        super().save(*args, **kwargs)

    def get_s3_path(self):
        """Retourne le chemin actuel du fichier dans S3/MinIO."""
        if self.fichier:
            return self.fichier.name
        return None


def version_upload_path(instance, filename):
    """Chemin de stockage pour les versions de documents dans MinIO."""
    return f"versions/{instance.document.mandat_id}/{instance.document_id}/{instance.numero_version}/{filename}"


class VersionDocument(BaseModel):
    """
    Historique des versions d'un document.

    Seul système de versioning : stocke une copie du fichier dans MinIO
    à chaque modification, avec les métadonnées de la version.
    """

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE,
        related_name='historique_versions',
        verbose_name=_('Document'),
        help_text=_('Document concerné')
    )

    numero_version = models.IntegerField(
        verbose_name=_('Numéro de version'),
        help_text=_('Numéro séquentiel de la version')
    )
    fichier = models.FileField(
        storage=DocumentStorage(),
        upload_to=version_upload_path,
        null=True,
        blank=True,
        verbose_name=_('Fichier de cette version'),
        help_text=_('Copie du fichier dans MinIO/S3 pour cette version')
    )
    hash_fichier = models.CharField(
        max_length=64,
        verbose_name=_('Hash du fichier'),
        help_text=_('Empreinte SHA-256 de cette version')
    )

    taille = models.BigIntegerField(
        verbose_name=_('Taille'),
        help_text=_('Taille du fichier en octets')
    )

    modifie_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Modifié par'),
        help_text=_('Utilisateur ayant créé cette version')
    )
    date_modification = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de modification'),
        help_text=_('Date de création de cette version')
    )

    commentaire = models.TextField(
        blank=True,
        verbose_name=_('Commentaire'),
        help_text=_('Description des modifications')
    )

    class Meta:
        db_table = 'versions_document'
        verbose_name = _('Version de document')
        verbose_name_plural = _('Versions de document')
        ordering = ['-numero_version']
        unique_together = [['document', 'numero_version']]

    def __str__(self):
        return f"{self.document.nom_fichier} - v{self.numero_version}"

    @classmethod
    def creer_version(cls, document, user, commentaire=''):
        """
        Crée une nouvelle version à partir de l'état actuel du document.
        Copie le fichier dans MinIO avant toute modification.
        """
        dernier = cls.objects.filter(document=document).order_by('-numero_version').first()
        nouveau_numero = (dernier.numero_version + 1) if dernier else 1

        version = cls.objects.create(
            document=document,
            numero_version=nouveau_numero,
            hash_fichier=document.hash_fichier,
            taille=document.taille,
            modifie_par=user,
            commentaire=commentaire,
        )

        # Copier le fichier actuel dans la version
        if document.fichier:
            from django.core.files.base import ContentFile
            try:
                content = document.fichier.read()
                document.fichier.seek(0)
                version.fichier.save(
                    document.nom_fichier,
                    ContentFile(content),
                    save=True
                )
            except Exception:
                pass

        return version


class TraitementDocument(BaseModel):
    """Log des traitements automatiques (OCR, AI, etc.)"""

    TYPE_TRAITEMENT_CHOICES = [
        ('OCR', _('OCR / Extraction texte')),
        ('CLASSIFICATION', _('Classification automatique')),
        ('EXTRACTION', _('Extraction métadonnées')),
        ('COMPRESSION', _('Compression')),
        ('CONVERSION', _('Conversion format')),
        ('WATERMARK', _('Ajout watermark')),
    ]

    STATUT_CHOICES = [
        ('EN_COURS', _('En cours')),
        ('TERMINE', _('Terminé')),
        ('ERREUR', _('Erreur')),
    ]

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE,
        related_name='traitements',
        verbose_name=_('Document'),
        help_text=_('Document traité')
    )

    type_traitement = models.CharField(
        max_length=20, choices=TYPE_TRAITEMENT_CHOICES,
        verbose_name=_('Type de traitement'),
        help_text=_('Nature du traitement effectué')
    )
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        verbose_name=_('Statut'),
        help_text=_('État du traitement')
    )

    date_debut = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de début'),
        help_text=_('Début du traitement')
    )
    date_fin = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Date de fin'),
        help_text=_('Fin du traitement')
    )
    duree_secondes = models.IntegerField(
        null=True, blank=True,
        verbose_name=_('Durée'),
        help_text=_('Durée du traitement en secondes')
    )

    # Résultats
    resultat = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Résultat'),
        help_text=_('Données résultant du traitement')
    )
    erreur = models.TextField(
        blank=True,
        verbose_name=_('Erreur'),
        help_text=_('Message d\'erreur en cas d\'échec')
    )

    # Moteur utilisé
    moteur = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Moteur'),
        help_text=_('Outil utilisé (Tesseract, OpenAI GPT-4, etc.)')
    )

    class Meta:
        db_table = 'traitements_document'
        verbose_name = _('Traitement de document')
        verbose_name_plural = _('Traitements de document')
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.get_type_traitement_display()} - {self.document.nom_fichier}"


class RechercheDocument(models.Model):
    """Historique des recherches (pour analytics et amélioration)"""

    utilisateur = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name=_('Utilisateur'),
        help_text=_('Utilisateur ayant effectué la recherche')
    )
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name=_('Mandat'),
        help_text=_('Mandat dans lequel la recherche a été effectuée')
    )

    requete = models.TextField(
        verbose_name=_('Requête'),
        help_text=_('Texte de la recherche')
    )
    filtres = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Filtres'),
        help_text=_('Filtres appliqués à la recherche')
    )

    nombre_resultats = models.IntegerField(
        verbose_name=_('Nombre de résultats'),
        help_text=_('Nombre de documents trouvés')
    )
    documents_selectionnes = models.ManyToManyField(
        Document, blank=True,
        verbose_name=_('Documents sélectionnés'),
        help_text=_('Documents consultés parmi les résultats')
    )

    date_recherche = models.DateTimeField(
        auto_now_add=True, db_index=True,
        verbose_name=_('Date de recherche'),
        help_text=_('Date et heure de la recherche')
    )
    duree_ms = models.IntegerField(
        verbose_name=_('Durée'),
        help_text=_('Durée de la recherche en millisecondes')
    )

    class Meta:
        db_table = 'recherches_document'
        verbose_name = _('Recherche de document')
        verbose_name_plural = _('Recherches de document')
        ordering = ['-date_recherche']

    def __str__(self):
        return f"{self.requete[:50]} - {self.utilisateur.username}"


class DocumentEmbedding(models.Model):
    """
    Embeddings vectoriels pour la recherche semantique.

    Utilise PGVector pour stocker et rechercher des vecteurs.
    Genere via le SDK AltiusOne AI (768 dimensions).
    """

    EMBEDDING_MODELS = [
        ('altiusone-768', 'AltiusOne AI SDK (768d)'),
        ('openai-small', 'OpenAI text-embedding-3-small (1536d)'),
        ('openai-large', 'OpenAI text-embedding-3-large (3072d)'),
        ('multilingual-mini', 'Multilingual MiniLM (384d)'),
        ('multilingual-mpnet', 'Multilingual MPNet (768d)'),
    ]

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='embedding',
        primary_key=True,
        verbose_name=_('Document'),
        help_text=_('Document associé à cet embedding')
    )

    # Vecteur d'embedding - dimension 768 (AltiusOne AI SDK)
    embedding = VectorField(
        dimensions=768, null=True, blank=True,
        verbose_name=_('Embedding'),
        help_text=_('Vecteur de représentation sémantique')
    )

    # Metadonnees
    model_used = models.CharField(
        max_length=50,
        choices=EMBEDDING_MODELS,
        default='altiusone-768',
        verbose_name=_('Modèle utilisé'),
        help_text=_('Modèle d\'embedding utilisé')
    )
    dimensions = models.IntegerField(
        default=768,
        verbose_name=_('Dimensions'),
        help_text=_('Nombre de dimensions du vecteur')
    )

    # Texte source utilisé pour l'embedding
    text_hash = models.CharField(
        max_length=64,
        verbose_name=_('Hash du texte'),
        help_text=_('Empreinte SHA-256 du texte source')
    )
    text_length = models.IntegerField(
        verbose_name=_('Longueur du texte'),
        help_text=_('Nombre de caractères du texte source')
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de création'),
        help_text=_('Date de génération de l\'embedding')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Date de mise à jour'),
        help_text=_('Dernière mise à jour de l\'embedding')
    )

    class Meta:
        db_table = 'document_embeddings'
        verbose_name = _('Embedding de document')
        verbose_name_plural = _('Embeddings de document')
        managed = False  # Table créée via migration SQL brut (0004)
        indexes = [
            # Index HNSW pour recherche rapide de similarité
            HnswIndex(
                name='document_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops']
            ),
        ]

    def __str__(self):
        return f"Embedding {self.document.nom_fichier} ({self.dimensions}d)"

    @classmethod
    def search_similar(cls, query_embedding, limit=20, threshold=0.5, mandat_id=None):
        """
        Recherche les documents similaires à un embedding donné.

        Args:
            query_embedding: Vecteur de requête (liste de floats)
            limit: Nombre max de résultats
            threshold: Seuil de similarité minimum (0-1)
            mandat_id: Filtrer par mandat (optionnel)

        Returns:
            QuerySet avec annotation 'similarity'
        """
        from django.db.models import F
        from pgvector.django import CosineDistance

        qs = cls.objects.select_related('document', 'document__mandat', 'document__type_document')

        # Filtrer par mandat si spécifié
        if mandat_id:
            qs = qs.filter(document__mandat_id=mandat_id)

        # Recherche par similarité cosinus
        qs = qs.annotate(
            distance=CosineDistance('embedding', query_embedding)
        ).filter(
            distance__lt=(1 - threshold)  # Cosine distance = 1 - similarity
        ).order_by('distance')[:limit]

        # Ajouter le score de similarité
        return qs

    @classmethod
    def create_or_update(cls, document, text: str, embedding: list, model_used: str = 'openai-small'):
        """
        Crée ou met à jour l'embedding d'un document.

        Args:
            document: Instance Document
            text: Texte source
            embedding: Vecteur d'embedding
            model_used: Modèle utilisé

        Returns:
            Instance DocumentEmbedding
        """
        import hashlib

        text_hash = hashlib.sha256(text.encode()).hexdigest()

        obj, created = cls.objects.update_or_create(
            document=document,
            defaults={
                'embedding': embedding,
                'model_used': model_used,
                'dimensions': len(embedding),
                'text_hash': text_hash,
                'text_length': len(text),
            }
        )

        return obj


class TextChunkEmbedding(models.Model):
    """
    Embeddings pour des chunks de texte (pour documents longs).

    Permet une recherche plus precise en decoupant les documents.
    Genere via le SDK AltiusOne AI (768 dimensions).
    """

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunk_embeddings',
        verbose_name=_('Document'),
        help_text=_('Document source du chunk')
    )

    # Position du chunk dans le document
    chunk_index = models.IntegerField(
        verbose_name=_('Index du chunk'),
        help_text=_('Position du chunk dans la séquence')
    )
    chunk_start = models.IntegerField(
        verbose_name=_('Début du chunk'),
        help_text=_('Position de début dans le texte (caractères)')
    )
    chunk_end = models.IntegerField(
        verbose_name=_('Fin du chunk'),
        help_text=_('Position de fin dans le texte (caractères)')
    )

    # Texte du chunk (pour affichage des resultats)
    chunk_text = models.TextField(
        verbose_name=_('Texte du chunk'),
        help_text=_('Contenu textuel du chunk')
    )

    # Embedding du chunk - dimension 768 (AltiusOne AI SDK)
    embedding = VectorField(
        dimensions=768, null=True, blank=True,
        verbose_name=_('Embedding'),
        help_text=_('Vecteur de représentation sémantique du chunk')
    )

    # Metadonnees
    model_used = models.CharField(
        max_length=50, default='altiusone-768',
        verbose_name=_('Modèle utilisé'),
        help_text=_('Modèle d\'embedding utilisé')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de création'),
        help_text=_('Date de génération de l\'embedding')
    )

    class Meta:
        db_table = 'text_chunk_embeddings'
        verbose_name = _('Embedding de chunk')
        verbose_name_plural = _('Embeddings de chunk')
        managed = False  # Table créée via migration SQL brut (0004)
        unique_together = [['document', 'chunk_index']]
        indexes = [
            HnswIndex(
                name='chunk_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops']
            ),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} - {self.document.nom_fichier}"

    @classmethod
    def search_similar_chunks(cls, query_embedding, limit=20, threshold=0.5, mandat_id=None):
        """
        Recherche les chunks similaires à un embedding donné.
        """
        from pgvector.django import CosineDistance

        qs = cls.objects.select_related('document', 'document__mandat')

        if mandat_id:
            qs = qs.filter(document__mandat_id=mandat_id)

        qs = qs.annotate(
            distance=CosineDistance('embedding', query_embedding)
        ).filter(
            distance__lt=(1 - threshold)
        ).order_by('distance')[:limit]

        return qs


# ============================================================================
# MODELES CHAT - Conversations avec contexte documentaire
# ============================================================================

class Conversation(BaseModel):
    """
    Conversation de chat avec l'assistant AI.

    Peut etre liee a:
    - Un mandat (contexte documentaire)
    - Un document specifique
    - Ou etre generale (sans contexte)
    """

    STATUT_CHOICES = [
        ('ACTIVE', _('Active')),
        ('ARCHIVEE', _('Archivee')),
        ('SUPPRIMEE', _('Supprimee')),
    ]

    # Rattachement
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name=_('Utilisateur'),
        help_text=_('Utilisateur propriétaire de la conversation')
    )
    mandats = models.ManyToManyField(
        Mandat,
        blank=True,
        related_name='conversations',
        verbose_name=_('Mandats'),
        help_text=_('Mandats pour le contexte documentaire')
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        verbose_name=_('Document'),
        help_text=_('Document spécifique comme contexte')
    )

    # Identification
    titre = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Titre'),
        help_text=_('Titre de la conversation')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description de la conversation')
    )

    # Configuration
    modele_ia = models.CharField(
        max_length=50,
        default='altiusone-chat',
        verbose_name=_('Modèle IA'),
        help_text=_('Modèle d\'intelligence artificielle utilisé')
    )
    temperature = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.7,
        verbose_name=_('Température'),
        help_text=_('Créativité des réponses (0=déterministe, 1=créatif)')
    )
    contexte_systeme = models.TextField(
        blank=True,
        verbose_name=_('Contexte système'),
        help_text=_('Instructions personnalisées pour l\'assistant')
    )

    # Statut
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='ACTIVE',
        db_index=True,
        verbose_name=_('Statut'),
        help_text=_('État de la conversation')
    )

    # Statistiques
    nombre_messages = models.IntegerField(
        default=0,
        verbose_name=_('Nombre de messages'),
        help_text=_('Total des messages échangés')
    )
    tokens_utilises = models.IntegerField(
        default=0,
        verbose_name=_('Tokens utilisés'),
        help_text=_('Consommation totale de tokens')
    )

    class Meta:
        db_table = 'conversations'
        verbose_name = _('Conversation')
        verbose_name_plural = _('Conversations')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['utilisateur', 'statut']),
        ]

    def __str__(self):
        titre = self.titre or f"Conversation {self.id}"
        return f"{titre} - {self.utilisateur.username}"

    def generer_titre(self):
        """Genere un titre a partir du premier message."""
        premier_message = self.messages.filter(role='USER').first()
        if premier_message:
            # Tronquer a 50 caracteres
            contenu = premier_message.contenu[:50]
            if len(premier_message.contenu) > 50:
                contenu += '...'
            self.titre = contenu
            self.save(update_fields=['titre'])

    def get_contexte_documents(self, limit=5):
        """
        Recupere les documents pertinents pour le contexte.

        Returns:
            Liste de documents avec leur texte OCR
        """
        if self.document:
            return [self.document]

        mandat_ids = list(self.mandats.values_list('id', flat=True))
        if mandat_ids:
            return Document.objects.filter(
                mandat_id__in=mandat_ids,
                is_active=True,
                ocr_text__isnull=False
            ).exclude(ocr_text='').order_by('-date_upload')[:limit]

        return []


class Message(BaseModel):
    """
    Message dans une conversation.

    Types:
    - USER: Message de l'utilisateur
    - ASSISTANT: Reponse de l'AI
    - SYSTEM: Message systeme (context, erreur)
    """

    ROLE_CHOICES = [
        ('USER', _('Utilisateur')),
        ('ASSISTANT', _('Assistant')),
        ('SYSTEM', _('Système')),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Conversation'),
        help_text=_('Conversation contenant ce message')
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        db_index=True,
        verbose_name=_('Rôle'),
        help_text=_('Auteur du message (utilisateur, assistant ou système)')
    )
    contenu = models.TextField(
        verbose_name=_('Contenu'),
        help_text=_('Texte du message')
    )

    # Metadonnees AI
    tokens_prompt = models.IntegerField(
        default=0,
        verbose_name=_('Tokens prompt'),
        help_text=_('Nombre de tokens utilisés pour le prompt')
    )
    tokens_completion = models.IntegerField(
        default=0,
        verbose_name=_('Tokens réponse'),
        help_text=_('Nombre de tokens générés en réponse')
    )
    duree_ms = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Durée'),
        help_text=_('Durée de génération en millisecondes')
    )

    # Documents references
    documents_contexte = models.ManyToManyField(
        Document,
        blank=True,
        related_name='messages_contexte',
        verbose_name=_('Documents contexte'),
        help_text=_('Documents utilisés comme contexte pour ce message')
    )

    # Sources citees dans la reponse
    sources = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Sources'),
        help_text=_('Sources citées par l\'assistant')
    )

    # Feedback utilisateur
    feedback = models.CharField(
        max_length=20,
        choices=[
            ('POSITIF', 'Positif'),
            ('NEGATIF', 'Négatif'),
        ],
        null=True,
        blank=True,
        verbose_name=_('Feedback'),
        help_text=_('Évaluation de la réponse par l\'utilisateur')
    )
    commentaire_feedback = models.TextField(
        blank=True,
        verbose_name=_('Commentaire feedback'),
        help_text=_('Explication du feedback')
    )

    class Meta:
        db_table = 'messages'
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.role}: {self.contenu[:50]}..."

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Mettre a jour les compteurs de la conversation
        if is_new:
            self.conversation.nombre_messages = self.conversation.messages.count()
            self.conversation.tokens_utilises += self.tokens_prompt + self.tokens_completion
            self.conversation.save(update_fields=['nombre_messages', 'tokens_utilises', 'updated_at'])


# Import intelligence models so Django discovers them for migrations
from documents.models_intelligence import DocumentRelation, MandatInsight, MandatDigest  # noqa: F401, E402