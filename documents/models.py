# apps/documents/models.py
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import VectorField, HnswIndex
from core.models import BaseModel, Mandat, Client, User
from core.storage import DocumentStorage
import hashlib
import os
import uuid


def document_upload_path(instance, filename):
    """
    Génère le chemin d'upload pour un document.
    Format: {mandat_id}/{uuid}/{filename}
    """
    return f"{instance.mandat_id}/{uuid.uuid4()}/{filename}"


class Dossier(BaseModel):
    """Dossier/Répertoire dans la GED"""

    TYPE_CHOICES = [
        ('RACINE', 'Racine'),
        ('CLIENT', 'Dossier client'),
        ('MANDAT', 'Dossier mandat'),
        ('EXERCICE', 'Exercice comptable'),
        ('STANDARD', 'Dossier standard'),
        ('ARCHIVE', 'Archive'),
    ]

    # Hiérarchie
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='sous_dossiers',
        verbose_name='Dossier parent',
        help_text='Dossier contenant celui-ci'
    )

    # Rattachement
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='dossiers',
        verbose_name='Client',
        help_text='Client propriétaire du dossier'
    )
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='dossiers',
        verbose_name='Mandat',
        help_text='Mandat associé au dossier'
    )

    # Identification
    nom = models.CharField(
        max_length=255,
        verbose_name='Nom',
        help_text='Nom du dossier'
    )
    type_dossier = models.CharField(
        max_length=20, choices=TYPE_CHOICES,
        verbose_name='Type de dossier',
        help_text='Catégorie du dossier'
    )

    # Chemin complet (dénormalisé pour performance)
    chemin_complet = models.CharField(
        max_length=1000, db_index=True,
        verbose_name='Chemin complet',
        help_text='Chemin d\'accès complet dans l\'arborescence'
    )
    niveau = models.IntegerField(
        default=0,
        verbose_name='Niveau',
        help_text='Profondeur dans l\'arborescence'
    )

    # Métadonnées
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Description du contenu du dossier'
    )
    tags = models.JSONField(
        default=list, blank=True,
        verbose_name='Tags',
        help_text='Étiquettes pour faciliter la recherche'
    )

    # Droits d'accès
    proprietaire = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='dossiers_proprietaire',
        verbose_name='Propriétaire',
        help_text='Utilisateur propriétaire du dossier'
    )
    acces_restreint = models.BooleanField(
        default=False,
        verbose_name='Accès restreint',
        help_text='Limiter l\'accès aux utilisateurs autorisés'
    )
    utilisateurs_autorises = models.ManyToManyField(
        User, blank=True,
        related_name='dossiers_autorises',
        verbose_name='Utilisateurs autorisés',
        help_text='Utilisateurs ayant accès si accès restreint'
    )

    # Statistiques (dénormalisé)
    nombre_documents = models.IntegerField(
        default=0,
        verbose_name='Nombre de documents',
        help_text='Nombre de documents dans ce dossier'
    )
    taille_totale = models.BigIntegerField(
        default=0,
        verbose_name='Taille totale',
        help_text='Taille totale des documents en octets'
    )

    class Meta:
        db_table = 'dossiers'
        verbose_name = 'Dossier'
        ordering = ['chemin_complet']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['mandat']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        return self.chemin_complet

    def save(self, *args, **kwargs):
        # Calcul du chemin complet
        if self.parent:
            self.chemin_complet = f"{self.parent.chemin_complet}/{self.nom}"
            self.niveau = self.parent.niveau + 1
        else:
            self.chemin_complet = self.nom
            self.niveau = 0

        super().save(*args, **kwargs)

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


class CategorieDocument(BaseModel):
    """Catégories de documents"""

    nom = models.CharField(
        max_length=100, unique=True,
        verbose_name='Nom',
        help_text='Nom de la catégorie'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Description de la catégorie'
    )

    # Classification automatique
    mots_cles = models.JSONField(
        default=list, blank=True,
        verbose_name='Mots-clés',
        help_text='Mots-clés pour classification automatique'
    )
    patterns_regex = models.JSONField(
        default=list, blank=True,
        verbose_name='Patterns regex',
        help_text='Expressions régulières pour détection automatique'
    )

    # Icône et couleur pour UI
    icone = models.CharField(
        max_length=50, blank=True,
        verbose_name='Icône',
        help_text='Nom de l\'icône (ex: folder, file-text)'
    )
    couleur = models.CharField(
        max_length=7, blank=True,
        verbose_name='Couleur',
        help_text='Code couleur hexadécimal (ex: #FF5733)'
    )

    # Ordre affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name='Ordre',
        help_text='Position d\'affichage dans la liste'
    )

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='sous_categories',
        verbose_name='Catégorie parente',
        help_text='Catégorie de niveau supérieur'
    )

    class Meta:
        db_table = 'categories_document'
        verbose_name = 'Catégorie de document'
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class TypeDocument(BaseModel):
    """Types de documents spécifiques"""

    TYPE_CHOICES = [
        ('FACTURE_VENTE', 'Facture de vente'),
        ('FACTURE_ACHAT', 'Facture d\'achat'),
        ('DEVIS', 'Devis'),
        ('BON_COMMANDE', 'Bon de commande'),
        ('BON_LIVRAISON', 'Bon de livraison'),
        ('RELEVE_BANQUE', 'Relevé bancaire'),
        ('JUSTIFICATIF', 'Justificatif'),
        ('CONTRAT', 'Contrat'),
        ('STATUTS', 'Statuts'),
        ('PV_ASSEMBLEE', 'PV Assemblée'),
        ('DECLARATION_TVA', 'Déclaration TVA'),
        ('FICHE_SALAIRE', 'Fiche de salaire'),
        ('CERTIFICAT_SALAIRE', 'Certificat de salaire'),
        ('ATTESTATION', 'Attestation'),
        ('COURRIER', 'Courrier'),
        ('EMAIL', 'Email'),
        ('AUTRE', 'Autre'),
    ]

    code = models.CharField(
        max_length=50, unique=True,
        verbose_name='Code',
        help_text='Code unique du type de document'
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name='Libellé',
        help_text='Nom affiché du type de document'
    )
    type_document = models.CharField(
        max_length=50, choices=TYPE_CHOICES,
        verbose_name='Type de document',
        help_text='Catégorie prédéfinie du document'
    )

    categorie = models.ForeignKey(
        CategorieDocument, on_delete=models.PROTECT,
        related_name='types_document',
        verbose_name='Catégorie',
        help_text='Catégorie à laquelle appartient ce type'
    )

    # Extraction automatique
    champs_extraire = models.JSONField(
        default=list, blank=True,
        verbose_name='Champs à extraire',
        help_text='Liste des champs à extraire automatiquement (montant, date, etc.)'
    )

    # Template OCR/AI
    template_extraction = models.JSONField(
        default=dict, blank=True,
        verbose_name='Template d\'extraction',
        help_text='Configuration du template pour l\'extraction AI/OCR'
    )

    # Workflow
    validation_requise = models.BooleanField(
        default=False,
        verbose_name='Validation requise',
        help_text='Exiger une validation manuelle pour ce type'
    )
    validateurs = models.ManyToManyField(
        User, blank=True,
        related_name='types_doc_validation',
        verbose_name='Validateurs',
        help_text='Utilisateurs habilités à valider ce type de document'
    )

    class Meta:
        db_table = 'types_document'
        verbose_name = 'Type de document'
        ordering = ['libelle']

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class Document(BaseModel):
    """Document dans la GED"""

    STATUT_TRAITEMENT_CHOICES = [
        ('UPLOAD', 'Uploadé'),
        ('OCR_EN_COURS', 'OCR en cours'),
        ('OCR_TERMINE', 'OCR terminé'),
        ('CLASSIFICATION_EN_COURS', 'Classification en cours'),
        ('CLASSIFICATION_TERMINEE', 'Classification terminée'),
        ('EXTRACTION_EN_COURS', 'Extraction données en cours'),
        ('EXTRACTION_TERMINEE', 'Extraction terminée'),
        ('VALIDE', 'Validé'),
        ('ERREUR', 'Erreur traitement'),
    ]

    STATUT_VALIDATION_CHOICES = [
        ('EN_ATTENTE', 'En attente validation'),
        ('VALIDE', 'Validé'),
        ('REJETE', 'Rejeté'),
    ]

    # Rattachement
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Mandat',
        help_text='Mandat auquel appartient ce document'
    )
    dossier = models.ForeignKey(
        Dossier, on_delete=models.CASCADE,
        related_name='documents',
        null=True, blank=True,
        verbose_name='Dossier',
        help_text='Dossier de classement'
    )

    # Fichier
    nom_fichier = models.CharField(
        max_length=255, db_index=True,
        verbose_name='Nom du fichier',
        help_text='Nom du fichier stocké'
    )
    nom_original = models.CharField(
        max_length=255,
        verbose_name='Nom original',
        help_text='Nom du fichier lors de l\'upload'
    )
    extension = models.CharField(
        max_length=10,
        verbose_name='Extension',
        help_text='Extension du fichier (pdf, jpg, etc.)'
    )
    mime_type = models.CharField(
        max_length=100,
        verbose_name='Type MIME',
        help_text='Type MIME du fichier'
    )
    taille = models.BigIntegerField(
        verbose_name='Taille',
        help_text='Taille du fichier en octets'
    )

    # Stockage - FileField avec storage S3/MinIO
    fichier = models.FileField(
        storage=DocumentStorage,
        upload_to=document_upload_path,
        null=True,
        blank=True,
        verbose_name='Fichier',
        help_text='Fichier stocké dans S3/MinIO'
    )
    hash_fichier = models.CharField(
        max_length=64, unique=True, db_index=True,
        verbose_name='Hash du fichier',
        help_text='Empreinte SHA-256 pour déduplication'
    )

    # Classification
    type_document = models.ForeignKey(
        TypeDocument, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Type de document',
        help_text='Type de document identifié'
    )
    categorie = models.ForeignKey(
        CategorieDocument, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Catégorie',
        help_text='Catégorie de classement'
    )

    # Dates
    date_document = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name='Date du document',
        help_text='Date figurant sur le document'
    )
    date_upload = models.DateTimeField(
        auto_now_add=True, db_index=True,
        verbose_name='Date d\'upload',
        help_text='Date et heure de téléchargement'
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name='Date de modification',
        help_text='Dernière modification'
    )

    # OCR et extraction
    ocr_text = models.TextField(
        blank=True,
        verbose_name='Texte OCR',
        help_text='Texte extrait par reconnaissance optique'
    )
    ocr_confidence = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name='Confiance OCR',
        help_text='Score de confiance de l\'OCR (0-100)'
    )

    metadata_extraite = models.JSONField(
        default=dict, blank=True,
        verbose_name='Métadonnées extraites',
        help_text='Données extraites automatiquement (montants, dates, etc.)'
    )

    # Classification AI
    prediction_type = models.CharField(
        max_length=100, blank=True,
        verbose_name='Type prédit',
        help_text='Type de document prédit par l\'IA'
    )
    prediction_confidence = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name='Confiance prédiction',
        help_text='Score de confiance de la prédiction (0-100)'
    )

    # Tags et recherche
    tags = models.JSONField(
        default=list, blank=True,
        verbose_name='Tags',
        help_text='Étiquettes manuelles'
    )
    tags_auto = models.JSONField(
        default=list, blank=True,
        verbose_name='Tags automatiques',
        help_text='Étiquettes générées automatiquement'
    )

    # Statuts
    statut_traitement = models.CharField(
        max_length=30,
        choices=STATUT_TRAITEMENT_CHOICES,
        default='UPLOAD', db_index=True,
        verbose_name='Statut de traitement',
        help_text='État du traitement automatique'
    )
    statut_validation = models.CharField(
        max_length=20,
        choices=STATUT_VALIDATION_CHOICES,
        default='EN_ATTENTE',
        null=True, blank=True,
        verbose_name='Statut de validation',
        help_text='État de la validation manuelle'
    )

    # Validation
    valide_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents_valides',
        verbose_name='Validé par',
        help_text='Utilisateur ayant validé le document'
    )
    date_validation = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date de validation',
        help_text='Date et heure de validation'
    )
    commentaire_validation = models.TextField(
        blank=True,
        verbose_name='Commentaire de validation',
        help_text='Remarques du validateur'
    )

    # Liens avec autres entités
    ecriture_comptable = models.ForeignKey(
        'comptabilite.EcritureComptable',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name='Écriture comptable',
        help_text='Écriture comptable associée'
    )
    facture = models.ForeignKey(
        'facturation.Facture', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name='Facture',
        help_text='Facture associée'
    )
    fiche_salaire = models.ForeignKey(
        'salaires.FicheSalaire',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name='Fiche de salaire',
        help_text='Fiche de salaire associée'
    )

    # Versioning
    version = models.IntegerField(
        default=1,
        verbose_name='Version',
        help_text='Numéro de version du document'
    )
    document_parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='versions',
        verbose_name='Document parent',
        help_text='Version précédente du document'
    )

    # Sécurité
    confidentiel = models.BooleanField(
        default=False,
        verbose_name='Confidentiel',
        help_text='Marquer comme document confidentiel'
    )

    # Description
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Description du document'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text='Notes et remarques internes'
    )

    class Meta:
        db_table = 'documents'
        verbose_name = 'Document'
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

    def generer_path_storage(self):
        """Génère le chemin de stockage S3/Minio"""
        date = self.created_at
        # Structure: mandat_id/annee/mois/hash_8premiers_caracteres/nom_fichier
        return f"{self.mandat.id}/{date.year}/{date.month:02d}/{self.hash_fichier[:8]}/{self.nom_fichier}"


class VersionDocument(BaseModel):
    """Historique des versions d'un document"""

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE,
        related_name='historique_versions',
        verbose_name='Document',
        help_text='Document concerné'
    )

    numero_version = models.IntegerField(
        verbose_name='Numéro de version',
        help_text='Numéro séquentiel de la version'
    )
    path_storage = models.CharField(
        max_length=500,
        verbose_name='Chemin de stockage',
        help_text='Emplacement du fichier dans le stockage'
    )
    hash_fichier = models.CharField(
        max_length=64,
        verbose_name='Hash du fichier',
        help_text='Empreinte SHA-256 de cette version'
    )

    taille = models.BigIntegerField(
        verbose_name='Taille',
        help_text='Taille du fichier en octets'
    )

    modifie_par = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Modifié par',
        help_text='Utilisateur ayant créé cette version'
    )
    date_modification = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de modification',
        help_text='Date de création de cette version'
    )

    commentaire = models.TextField(
        blank=True,
        verbose_name='Commentaire',
        help_text='Description des modifications'
    )

    class Meta:
        db_table = 'versions_document'
        verbose_name = 'Version de document'
        ordering = ['-numero_version']
        unique_together = [['document', 'numero_version']]

    def __str__(self):
        return f"{self.document.nom_fichier} - v{self.numero_version}"


class TraitementDocument(BaseModel):
    """Log des traitements automatiques (OCR, AI, etc.)"""

    TYPE_TRAITEMENT_CHOICES = [
        ('OCR', 'OCR / Extraction texte'),
        ('CLASSIFICATION', 'Classification automatique'),
        ('EXTRACTION', 'Extraction métadonnées'),
        ('COMPRESSION', 'Compression'),
        ('CONVERSION', 'Conversion format'),
        ('WATERMARK', 'Ajout watermark'),
    ]

    STATUT_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('TERMINE', 'Terminé'),
        ('ERREUR', 'Erreur'),
    ]

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE,
        related_name='traitements',
        verbose_name='Document',
        help_text='Document traité'
    )

    type_traitement = models.CharField(
        max_length=20, choices=TYPE_TRAITEMENT_CHOICES,
        verbose_name='Type de traitement',
        help_text='Nature du traitement effectué'
    )
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        verbose_name='Statut',
        help_text='État du traitement'
    )

    date_debut = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de début',
        help_text='Début du traitement'
    )
    date_fin = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date de fin',
        help_text='Fin du traitement'
    )
    duree_secondes = models.IntegerField(
        null=True, blank=True,
        verbose_name='Durée',
        help_text='Durée du traitement en secondes'
    )

    # Résultats
    resultat = models.JSONField(
        default=dict, blank=True,
        verbose_name='Résultat',
        help_text='Données résultant du traitement'
    )
    erreur = models.TextField(
        blank=True,
        verbose_name='Erreur',
        help_text='Message d\'erreur en cas d\'échec'
    )

    # Moteur utilisé
    moteur = models.CharField(
        max_length=100, blank=True,
        verbose_name='Moteur',
        help_text='Outil utilisé (Tesseract, OpenAI GPT-4, etc.)'
    )

    class Meta:
        db_table = 'traitements_document'
        verbose_name = 'Traitement de document'
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.get_type_traitement_display()} - {self.document.nom_fichier}"


class RechercheDocument(models.Model):
    """Historique des recherches (pour analytics et amélioration)"""

    utilisateur = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name='Utilisateur',
        help_text='Utilisateur ayant effectué la recherche'
    )
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Mandat',
        help_text='Mandat dans lequel la recherche a été effectuée'
    )

    requete = models.TextField(
        verbose_name='Requête',
        help_text='Texte de la recherche'
    )
    filtres = models.JSONField(
        default=dict, blank=True,
        verbose_name='Filtres',
        help_text='Filtres appliqués à la recherche'
    )

    nombre_resultats = models.IntegerField(
        verbose_name='Nombre de résultats',
        help_text='Nombre de documents trouvés'
    )
    documents_selectionnes = models.ManyToManyField(
        Document, blank=True,
        verbose_name='Documents sélectionnés',
        help_text='Documents consultés parmi les résultats'
    )

    date_recherche = models.DateTimeField(
        auto_now_add=True, db_index=True,
        verbose_name='Date de recherche',
        help_text='Date et heure de la recherche'
    )
    duree_ms = models.IntegerField(
        verbose_name='Durée',
        help_text='Durée de la recherche en millisecondes'
    )

    class Meta:
        db_table = 'recherches_document'
        verbose_name = 'Recherche de document'
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
        verbose_name='Document',
        help_text='Document associé à cet embedding'
    )

    # Vecteur d'embedding - dimension 768 (AltiusOne AI SDK)
    embedding = VectorField(
        dimensions=768, null=True, blank=True,
        verbose_name='Embedding',
        help_text='Vecteur de représentation sémantique'
    )

    # Metadonnees
    model_used = models.CharField(
        max_length=50,
        choices=EMBEDDING_MODELS,
        default='altiusone-768',
        verbose_name='Modèle utilisé',
        help_text='Modèle d\'embedding utilisé'
    )
    dimensions = models.IntegerField(
        default=768,
        verbose_name='Dimensions',
        help_text='Nombre de dimensions du vecteur'
    )

    # Texte source utilisé pour l'embedding
    text_hash = models.CharField(
        max_length=64,
        verbose_name='Hash du texte',
        help_text='Empreinte SHA-256 du texte source'
    )
    text_length = models.IntegerField(
        verbose_name='Longueur du texte',
        help_text='Nombre de caractères du texte source'
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création',
        help_text='Date de génération de l\'embedding'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Date de mise à jour',
        help_text='Dernière mise à jour de l\'embedding'
    )

    class Meta:
        db_table = 'document_embeddings'
        verbose_name = 'Embedding de document'
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
        verbose_name='Document',
        help_text='Document source du chunk'
    )

    # Position du chunk dans le document
    chunk_index = models.IntegerField(
        verbose_name='Index du chunk',
        help_text='Position du chunk dans la séquence'
    )
    chunk_start = models.IntegerField(
        verbose_name='Début du chunk',
        help_text='Position de début dans le texte (caractères)'
    )
    chunk_end = models.IntegerField(
        verbose_name='Fin du chunk',
        help_text='Position de fin dans le texte (caractères)'
    )

    # Texte du chunk (pour affichage des resultats)
    chunk_text = models.TextField(
        verbose_name='Texte du chunk',
        help_text='Contenu textuel du chunk'
    )

    # Embedding du chunk - dimension 768 (AltiusOne AI SDK)
    embedding = VectorField(
        dimensions=768, null=True, blank=True,
        verbose_name='Embedding',
        help_text='Vecteur de représentation sémantique du chunk'
    )

    # Metadonnees
    model_used = models.CharField(
        max_length=50, default='altiusone-768',
        verbose_name='Modèle utilisé',
        help_text='Modèle d\'embedding utilisé'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création',
        help_text='Date de génération de l\'embedding'
    )

    class Meta:
        db_table = 'text_chunk_embeddings'
        verbose_name = 'Embedding de chunk'
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
        ('ACTIVE', 'Active'),
        ('ARCHIVEE', 'Archivee'),
        ('SUPPRIMEE', 'Supprimee'),
    ]

    # Rattachement
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name='Utilisateur',
        help_text='Utilisateur propriétaire de la conversation'
    )
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='conversations',
        verbose_name='Mandat',
        help_text='Mandat pour le contexte documentaire'
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        verbose_name='Document',
        help_text='Document spécifique comme contexte'
    )

    # Identification
    titre = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Titre',
        help_text='Titre de la conversation'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Description de la conversation'
    )

    # Configuration
    modele_ia = models.CharField(
        max_length=50,
        default='altiusone-chat',
        verbose_name='Modèle IA',
        help_text='Modèle d\'intelligence artificielle utilisé'
    )
    temperature = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.7,
        verbose_name='Température',
        help_text='Créativité des réponses (0=déterministe, 1=créatif)'
    )
    contexte_systeme = models.TextField(
        blank=True,
        verbose_name='Contexte système',
        help_text='Instructions personnalisées pour l\'assistant'
    )

    # Statut
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='ACTIVE',
        db_index=True,
        verbose_name='Statut',
        help_text='État de la conversation'
    )

    # Statistiques
    nombre_messages = models.IntegerField(
        default=0,
        verbose_name='Nombre de messages',
        help_text='Total des messages échangés'
    )
    tokens_utilises = models.IntegerField(
        default=0,
        verbose_name='Tokens utilisés',
        help_text='Consommation totale de tokens'
    )

    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['utilisateur', 'statut']),
            models.Index(fields=['mandat', 'statut']),
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

        if self.mandat:
            return Document.objects.filter(
                mandat=self.mandat,
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
        ('USER', 'Utilisateur'),
        ('ASSISTANT', 'Assistant'),
        ('SYSTEM', 'Systeme'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Conversation',
        help_text='Conversation contenant ce message'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        db_index=True,
        verbose_name='Rôle',
        help_text='Auteur du message (utilisateur, assistant ou système)'
    )
    contenu = models.TextField(
        verbose_name='Contenu',
        help_text='Texte du message'
    )

    # Metadonnees AI
    tokens_prompt = models.IntegerField(
        default=0,
        verbose_name='Tokens prompt',
        help_text='Nombre de tokens utilisés pour le prompt'
    )
    tokens_completion = models.IntegerField(
        default=0,
        verbose_name='Tokens réponse',
        help_text='Nombre de tokens générés en réponse'
    )
    duree_ms = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Durée',
        help_text='Durée de génération en millisecondes'
    )

    # Documents references
    documents_contexte = models.ManyToManyField(
        Document,
        blank=True,
        related_name='messages_contexte',
        verbose_name='Documents contexte',
        help_text='Documents utilisés comme contexte pour ce message'
    )

    # Sources citees dans la reponse
    sources = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Sources',
        help_text='Sources citées par l\'assistant'
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
        verbose_name='Feedback',
        help_text='Évaluation de la réponse par l\'utilisateur'
    )
    commentaire_feedback = models.TextField(
        blank=True,
        verbose_name='Commentaire feedback',
        help_text='Explication du feedback'
    )

    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
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