# apps/documents/models.py
from django.db import models
from core.models import BaseModel, Mandat, Client, User
import hashlib
import os


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
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='sous_dossiers')

    # Rattachement
    client = models.ForeignKey(Client, on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='dossiers')
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='dossiers')

    # Identification
    nom = models.CharField(max_length=255)
    type_dossier = models.CharField(max_length=20, choices=TYPE_CHOICES)

    # Chemin complet (dénormalisé pour performance)
    chemin_complet = models.CharField(max_length=1000, db_index=True)
    niveau = models.IntegerField(default=0, help_text='Profondeur dans l\'arborescence')

    # Métadonnées
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    # Droits d'accès
    proprietaire = models.ForeignKey(User, on_delete=models.PROTECT,
                                     related_name='dossiers_proprietaire')
    acces_restreint = models.BooleanField(default=False)
    utilisateurs_autorises = models.ManyToManyField(User, blank=True,
                                                    related_name='dossiers_autorises')

    # Statistiques (dénormalisé)
    nombre_documents = models.IntegerField(default=0)
    taille_totale = models.BigIntegerField(default=0, help_text='En octets')

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

    def get_path_display(self):
        """Retourne le chemin avec séparateurs visuels"""
        return self.chemin_complet.replace('/', ' > ')


class CategorieDocument(BaseModel):
    """Catégories de documents"""

    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Classification automatique
    mots_cles = models.JSONField(default=list, blank=True,
                                 help_text='Mots-clés pour classification auto')
    patterns_regex = models.JSONField(default=list, blank=True,
                                      help_text='Patterns regex pour détection')

    # Icône et couleur pour UI
    icone = models.CharField(max_length=50, blank=True)
    couleur = models.CharField(max_length=7, blank=True, help_text='Code hex')

    # Ordre affichage
    ordre = models.IntegerField(default=0)

    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='sous_categories')

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

    code = models.CharField(max_length=50, unique=True)
    libelle = models.CharField(max_length=100)
    type_document = models.CharField(max_length=50, choices=TYPE_CHOICES)

    categorie = models.ForeignKey(CategorieDocument, on_delete=models.PROTECT,
                                  related_name='types_document')

    # Extraction automatique
    champs_extraire = models.JSONField(default=list, blank=True, help_text="""
    Liste des champs à extraire automatiquement:
    ["montant", "date", "numero_facture", "fournisseur", "tva"]
    """)

    # Template OCR/AI
    template_extraction = models.JSONField(default=dict, blank=True)

    # Workflow
    validation_requise = models.BooleanField(default=False)
    validateurs = models.ManyToManyField(User, blank=True,
                                         related_name='types_doc_validation')

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
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='documents')
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE,
                                related_name='documents')

    # Fichier
    nom_fichier = models.CharField(max_length=255, db_index=True)
    nom_original = models.CharField(max_length=255)
    extension = models.CharField(max_length=10)
    mime_type = models.CharField(max_length=100)
    taille = models.BigIntegerField(help_text='Taille en octets')

    # Stockage
    path_storage = models.CharField(max_length=500, unique=True,
                                    help_text='Chemin S3/Minio')
    hash_fichier = models.CharField(max_length=64, unique=True, db_index=True,
                                    help_text='SHA-256 du fichier')

    # Classification
    type_document = models.ForeignKey(TypeDocument, on_delete=models.SET_NULL,
                                      null=True, blank=True)
    categorie = models.ForeignKey(CategorieDocument, on_delete=models.SET_NULL,
                                  null=True, blank=True)

    # Dates
    date_document = models.DateField(null=True, blank=True, db_index=True,
                                     help_text='Date du document (extraite ou saisie)')
    date_upload = models.DateTimeField(auto_now_add=True, db_index=True)
    date_modification = models.DateTimeField(auto_now=True)

    # OCR et extraction
    ocr_text = models.TextField(blank=True, help_text='Texte extrait par OCR')
    ocr_confidence = models.DecimalField(max_digits=5, decimal_places=2,
                                         null=True, blank=True,
                                         help_text='Score de confiance OCR (0-100)')

    metadata_extraite = models.JSONField(default=dict, blank=True, help_text="""
    Métadonnées extraites automatiquement:
    {
        "montant_ht": 1000.00,
        "montant_tva": 81.00,
        "montant_ttc": 1081.00,
        "numero_facture": "FAC-2025-001",
        "date_facture": "2025-01-15",
        "fournisseur": "Entreprise XYZ",
        "numero_tva_fournisseur": "CHE-123.456.789",
        "iban": "CH93 0076 2011 6238 5295 7"
    }
    """)

    # Classification AI
    prediction_type = models.CharField(max_length=100, blank=True,
                                       help_text='Type prédit par IA')
    prediction_confidence = models.DecimalField(max_digits=5, decimal_places=2,
                                                null=True, blank=True,
                                                help_text='Score confiance prédiction')

    # Tags et recherche
    tags = models.JSONField(default=list, blank=True)
    tags_auto = models.JSONField(default=list, blank=True,
                                 help_text='Tags générés automatiquement')

    # Statuts
    statut_traitement = models.CharField(max_length=30,
                                         choices=STATUT_TRAITEMENT_CHOICES,
                                         default='UPLOAD', db_index=True)
    statut_validation = models.CharField(max_length=20,
                                         choices=STATUT_VALIDATION_CHOICES,
                                         default='EN_ATTENTE',
                                         null=True, blank=True)

    # Validation
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='documents_valides')
    date_validation = models.DateTimeField(null=True, blank=True)
    commentaire_validation = models.TextField(blank=True)

    # Liens avec autres entités
    ecriture_comptable = models.ForeignKey('comptabilite.EcritureComptable',
                                           on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           related_name='documents')
    facture = models.ForeignKey('facturation.Facture', on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='documents')
    fiche_salaire = models.ForeignKey('salaires.FicheSalaire',
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True,
                                      related_name='documents')

    # Versioning
    version = models.IntegerField(default=1)
    document_parent = models.ForeignKey('self', on_delete=models.SET_NULL,
                                        null=True, blank=True,
                                        related_name='versions')

    # Sécurité
    confidentiel = models.BooleanField(default=False)

    # Description
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)

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

    document = models.ForeignKey(Document, on_delete=models.CASCADE,
                                 related_name='historique_versions')

    numero_version = models.IntegerField()
    path_storage = models.CharField(max_length=500)
    hash_fichier = models.CharField(max_length=64)

    taille = models.BigIntegerField()

    modifie_par = models.ForeignKey(User, on_delete=models.PROTECT)
    date_modification = models.DateTimeField(auto_now_add=True)

    commentaire = models.TextField(blank=True)

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

    document = models.ForeignKey(Document, on_delete=models.CASCADE,
                                 related_name='traitements')

    type_traitement = models.CharField(max_length=20, choices=TYPE_TRAITEMENT_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES)

    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    duree_secondes = models.IntegerField(null=True, blank=True)

    # Résultats
    resultat = models.JSONField(default=dict, blank=True)
    erreur = models.TextField(blank=True)

    # Moteur utilisé
    moteur = models.CharField(max_length=100, blank=True,
                              help_text='Ex: Tesseract 5.0, OpenAI GPT-4, etc.')

    class Meta:
        db_table = 'traitements_document'
        verbose_name = 'Traitement de document'
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.get_type_traitement_display()} - {self.document.nom_fichier}"


class RechercheDocument(models.Model):
    """Historique des recherches (pour analytics et amélioration)"""

    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True)

    requete = models.TextField()
    filtres = models.JSONField(default=dict, blank=True)

    nombre_resultats = models.IntegerField()
    documents_selectionnes = models.ManyToManyField(Document, blank=True)

    date_recherche = models.DateTimeField(auto_now_add=True, db_index=True)
    duree_ms = models.IntegerField(help_text='Durée de la recherche en ms')

    class Meta:
        db_table = 'recherches_document'
        verbose_name = 'Recherche de document'
        ordering = ['-date_recherche']

    def __str__(self):
        return f"{self.requete[:50]} - {self.utilisateur.username}"