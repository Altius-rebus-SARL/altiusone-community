# apps/comptabilite/models.py
from django.db import models
from core.models import BaseModel, Mandat, User, ExerciceComptable
from decimal import Decimal


# =============================================================================
# TYPE DE PLAN COMPTABLE (référentiel)
# =============================================================================

class TypePlanComptable(BaseModel):
    """
    Type de plan comptable (PME Suisse, OHADA, Swiss GAAP, etc.)

    Définit la structure standard d'un type de plan comptable:
    - Les classes et leur signification
    - Le pays/région d'application
    - Les normes comptables associées
    """

    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Code unique (PME, OHADA, SWISSGAAP, etc.)"
    )
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Région/Pays d'application
    pays = models.CharField(
        max_length=100,
        blank=True,
        help_text="Pays d'application (Suisse, Zone OHADA, etc.)"
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        help_text="Région ou zone économique"
    )

    # Normes
    norme_comptable = models.CharField(
        max_length=100,
        blank=True,
        help_text="Norme comptable de référence (CO, OHADA, IFRS, etc.)"
    )

    # Métadonnées
    version = models.CharField(max_length=20, blank=True, help_text="Version du plan")
    date_publication = models.DateField(null=True, blank=True)

    # Ordre d'affichage
    ordre = models.IntegerField(default=0, help_text="Ordre d'affichage dans les listes")

    class Meta:
        db_table = 'types_plans_comptables'
        verbose_name = 'Type de plan comptable'
        verbose_name_plural = 'Types de plans comptables'
        ordering = ['ordre', 'code']

    def __str__(self):
        return f"{self.nom} ({self.code})"

    @property
    def nombre_classes(self):
        return self.classes.count()

    @property
    def nombre_plans(self):
        return self.plans.count()


class ClasseComptable(BaseModel):
    """
    Classe comptable pour un type de plan.

    Chaque type de plan a sa propre définition des classes:
    - PME Suisse: Classe 1 = Actifs, Classe 2 = Passifs, etc.
    - OHADA: Classe 1 = Capitaux propres, Classe 2 = Actifs immobilisés, etc.
    """

    TYPE_COMPTE_CHOICES = [
        ('ACTIF', 'Actif'),
        ('PASSIF', 'Passif'),
        ('CHARGE', 'Charge'),
        ('PRODUIT', 'Produit'),
        ('RESULTAT', 'Résultat'),
    ]

    type_plan = models.ForeignKey(
        TypePlanComptable,
        on_delete=models.CASCADE,
        related_name='classes'
    )

    numero = models.IntegerField(help_text="Numéro de la classe (1, 2, 3...)")
    libelle = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Type de comptes dans cette classe
    type_compte = models.CharField(
        max_length=10,
        choices=TYPE_COMPTE_CHOICES,
        help_text="Nature des comptes de cette classe"
    )

    # Plage de numéros de comptes
    numero_debut = models.CharField(
        max_length=10,
        blank=True,
        help_text="Premier numéro de compte (ex: 1000)"
    )
    numero_fin = models.CharField(
        max_length=10,
        blank=True,
        help_text="Dernier numéro de compte (ex: 1999)"
    )

    class Meta:
        db_table = 'classes_comptables'
        verbose_name = 'Classe comptable'
        verbose_name_plural = 'Classes comptables'
        unique_together = [['type_plan', 'numero']]
        ordering = ['type_plan', 'numero']

    def __str__(self):
        return f"Classe {self.numero} - {self.libelle}"


# =============================================================================
# PLAN COMPTABLE (instance pour un mandat)
# =============================================================================

class PlanComptable(BaseModel):
    """
    Instance d'un plan comptable pour un mandat.

    Peut être:
    - Un template (is_template=True): Plan de référence réutilisable
    - Une instance (is_template=False): Plan spécifique à un mandat
    """

    # Lien vers le type de plan (remplace le CharField type_plan)
    type_plan = models.ForeignKey(
        TypePlanComptable,
        on_delete=models.PROTECT,
        related_name='plans',
        help_text="Type de plan comptable (PME, OHADA, etc.)"
    )

    nom = models.CharField(max_length=300)
    description = models.TextField(blank=True)

    # Template de base ou instance spécifique
    is_template = models.BooleanField(default=False, db_index=True)
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='plans_comptables',
        null=True,
        blank=True
    )

    # Héritage de template
    base_sur = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derives',
        help_text="Plan template de base"
    )

    class Meta:
        db_table = 'plans_comptables'
        verbose_name = 'Plan comptable'
        verbose_name_plural = 'Plans comptables'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nom} ({self.type_plan.code})"

    @property
    def nombre_comptes(self):
        return self.comptes.count()

    def get_type_plan_display(self):
        """Compatibilité avec l'ancien code."""
        return self.type_plan.nom if self.type_plan else ''


# =============================================================================
# COMPTE
# =============================================================================

class Compte(BaseModel):
    """Compte du plan comptable"""

    TYPE_COMPTE_CHOICES = [
        ('ACTIF', 'Actif'),
        ('PASSIF', 'Passif'),
        ('CHARGE', 'Charge'),
        ('PRODUIT', 'Produit'),
    ]

    plan_comptable = models.ForeignKey(
        PlanComptable,
        on_delete=models.CASCADE,
        related_name='comptes'
    )

    # Lien optionnel vers la classe (pour cohérence)
    classe_comptable = models.ForeignKey(
        ClasseComptable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comptes',
        help_text="Classe comptable de référence"
    )

    # Numérotation
    numero = models.CharField(max_length=20, db_index=True)
    libelle = models.CharField(max_length=255)
    libelle_court = models.CharField(max_length=100, blank=True)

    # Classification
    type_compte = models.CharField(max_length=10, choices=TYPE_COMPTE_CHOICES)
    classe = models.IntegerField(help_text="Numéro de classe (1-9)")
    niveau = models.IntegerField(default=1, help_text="Niveau hiérarchique")

    # Hiérarchie
    compte_parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sous_comptes'
    )

    # Propriétés
    est_collectif = models.BooleanField(default=False, help_text="Compte collectif (total)")
    imputable = models.BooleanField(default=True, help_text="Peut recevoir des écritures")
    lettrable = models.BooleanField(default=False, help_text="Lettrage possible")
    obligatoire_tiers = models.BooleanField(default=False)

    # TVA
    soumis_tva = models.BooleanField(default=False)
    code_tva_defaut = models.CharField(
        max_length=10,
        blank=True,
        help_text="Code TVA par défaut (200, 205, etc.)"
    )

    # Soldes
    solde_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    solde_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = 'comptes'
        verbose_name = 'Compte'
        verbose_name_plural = 'Comptes'
        unique_together = [['plan_comptable', 'numero']]
        ordering = ['numero']
        indexes = [
            models.Index(fields=['plan_comptable', 'numero']),
            models.Index(fields=['type_compte', 'classe']),
        ]

    def __str__(self):
        return f"{self.numero} - {self.libelle}"

    @property
    def solde(self):
        """Calcul du solde"""
        if self.type_compte in ['ACTIF', 'CHARGE']:
            return self.solde_debit - self.solde_credit
        else:  # PASSIF, PRODUIT
            return self.solde_credit - self.solde_debit

    def get_solde_display(self):
        """Affichage du solde avec signe"""
        solde = self.solde
        if solde >= 0:
            return f"{solde:,.2f} CHF"
        else:
            return f"-{abs(solde):,.2f} CHF"


# =============================================================================
# JOURNAL
# =============================================================================

class Journal(BaseModel):
    """Journal comptable"""

    TYPE_CHOICES = [
        ('VTE', 'Ventes'),
        ('ACH', 'Achats'),
        ('BNQ', 'Banque'),
        ('CAS', 'Caisse'),
        ('OD', 'Opérations diverses'),
        ('ANO', 'A-nouveaux'),
        ('EXT', 'Extourne'),
    ]

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE, related_name='journaux')

    code = models.CharField(max_length=10, db_index=True)
    libelle = models.CharField(max_length=100)
    type_journal = models.CharField(max_length=10, choices=TYPE_CHOICES)

    compte_contrepartie_defaut = models.ForeignKey(
        Compte,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    numerotation_auto = models.BooleanField(default=True)
    prefixe_piece = models.CharField(max_length=10, blank=True)
    dernier_numero = models.IntegerField(default=0)

    class Meta:
        db_table = 'journaux'
        verbose_name = 'Journal'
        verbose_name_plural = 'Journaux'
        unique_together = [['mandat', 'code']]
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.libelle}"

    def get_next_numero(self):
        """Génère le prochain numéro de pièce"""
        self.dernier_numero += 1
        self.save(update_fields=['dernier_numero'])
        return f"{self.prefixe_piece}{self.dernier_numero:05d}"


# =============================================================================
# ÉCRITURE COMPTABLE
# =============================================================================

class EcritureComptable(BaseModel):
    """Écriture comptable (ligne)"""

    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('VALIDE', 'Validée'),
        ('LETTRE', 'Lettrée'),
        ('CLOTURE', 'Clôturée'),
        ('EXTOURNE', 'Extournée'),
    ]

    # Identification
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='ecritures'
    )
    exercice = models.ForeignKey(
        ExerciceComptable,
        on_delete=models.PROTECT,
        related_name='ecritures'
    )
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT)

    # Lien vers la pièce comptable (nouveau)
    piece = models.ForeignKey(
        'PieceComptable',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ecritures',
        help_text="Pièce comptable regroupant les écritures"
    )

    numero_piece = models.CharField(max_length=50, db_index=True)
    numero_ligne = models.IntegerField(default=1)

    # Dates
    date_ecriture = models.DateField(db_index=True)
    date_valeur = models.DateField(null=True, blank=True)
    date_echeance = models.DateField(null=True, blank=True)

    # Comptes
    compte = models.ForeignKey(
        Compte,
        on_delete=models.PROTECT,
        related_name='ecritures'
    )
    compte_auxiliaire = models.CharField(max_length=50, blank=True)

    # Libellé
    libelle = models.TextField()
    libelle_complement = models.CharField(max_length=255, blank=True)

    # Montants
    montant_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    montant_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    devise = models.CharField(max_length=3, default='CHF')
    taux_change = models.DecimalField(max_digits=10, decimal_places=6, default=1)

    # TVA
    code_tva = models.CharField(max_length=10, blank=True)
    montant_tva = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Lettrage
    code_lettrage = models.CharField(max_length=20, blank=True, db_index=True)
    date_lettrage = models.DateField(null=True, blank=True)

    # Statut et validation
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='BROUILLON',
        db_index=True
    )
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    date_validation = models.DateTimeField(null=True, blank=True)

    # Document justificatif
    piece_justificative = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecritures'
    )

    # Extourne
    ecriture_extournee = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extournes'
    )

    class Meta:
        db_table = 'ecritures_comptables'
        verbose_name = 'Écriture comptable'
        verbose_name_plural = 'Écritures comptables'
        ordering = ['date_ecriture', 'numero_piece', 'numero_ligne']
        indexes = [
            models.Index(fields=['mandat', 'date_ecriture']),
            models.Index(fields=['compte', 'date_ecriture']),
            models.Index(fields=['numero_piece']),
            models.Index(fields=['code_lettrage']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return f"{self.numero_piece}-{self.numero_ligne} - {self.libelle[:50]}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Une écriture doit être soit au débit, soit au crédit
        if self.montant_debit and self.montant_credit:
            raise ValidationError("Une écriture ne peut pas avoir débit ET crédit")

        if not self.montant_debit and not self.montant_credit:
            raise ValidationError("Une écriture doit avoir un montant")

    @property
    def sens(self):
        return 'D' if self.montant_debit > 0 else 'C'

    @property
    def montant(self):
        return self.montant_debit if self.montant_debit > 0 else self.montant_credit


# =============================================================================
# TYPE DE PIÈCE COMPTABLE (référentiel personnalisable)
# =============================================================================

class TypePieceComptable(BaseModel):
    """
    Type de pièce comptable (facture, avoir, note de frais, etc.)

    Permet aux utilisateurs de définir leurs propres types de pièces
    avec des paramètres de numérotation et comptabilisation par défaut.
    """

    # Code unique pour identification
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Code unique (FAC_ACH, FAC_VTE, NDF, etc.)"
    )
    libelle = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Catégorie pour regroupement
    CATEGORIE_CHOICES = [
        ('ACHAT', 'Achats'),
        ('VENTE', 'Ventes'),
        ('BANQUE', 'Banque'),
        ('CAISSE', 'Caisse'),
        ('OD', 'Opérations diverses'),
        ('SALAIRE', 'Salaires'),
        ('AUTRE', 'Autre'),
    ]
    categorie = models.CharField(
        max_length=20,
        choices=CATEGORIE_CHOICES,
        default='AUTRE',
        db_index=True
    )

    # Paramètres de numérotation
    prefixe_numero = models.CharField(
        max_length=10,
        blank=True,
        help_text="Préfixe pour la numérotation automatique (ex: FAC, AVR)"
    )

    # Compte par défaut (pour pré-remplissage)
    compte_charge_defaut = models.ForeignKey(
        'Compte',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="Compte de charge par défaut"
    )
    compte_produit_defaut = models.ForeignKey(
        'Compte',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="Compte de produit par défaut"
    )

    # Taux de TVA par défaut
    taux_tva_defaut = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Taux de TVA par défaut (ex: 8.10)"
    )

    # Ordre d'affichage
    ordre = models.IntegerField(default=0, help_text="Ordre d'affichage dans les listes")

    # Est un type système (non supprimable)
    is_system = models.BooleanField(
        default=False,
        help_text="Type système créé par défaut"
    )

    class Meta:
        db_table = 'types_pieces_comptables'
        verbose_name = 'Type de pièce comptable'
        verbose_name_plural = 'Types de pièces comptables'
        ordering = ['ordre', 'code']

    def __str__(self):
        return f"{self.code} - {self.libelle}"

    @classmethod
    def get_default_types(cls):
        """Retourne la liste des types par défaut à créer"""
        return [
            {'code': 'FAC_ACH', 'libelle': "Facture d'achat", 'categorie': 'ACHAT', 'prefixe_numero': 'FA', 'ordre': 1},
            {'code': 'FAC_VTE', 'libelle': "Facture de vente", 'categorie': 'VENTE', 'prefixe_numero': 'FV', 'ordre': 2},
            {'code': 'AVOIR_ACH', 'libelle': "Avoir reçu", 'categorie': 'ACHAT', 'prefixe_numero': 'AA', 'ordre': 3},
            {'code': 'AVOIR_VTE', 'libelle': "Avoir émis", 'categorie': 'VENTE', 'prefixe_numero': 'AV', 'ordre': 4},
            {'code': 'NDF', 'libelle': "Note de frais", 'categorie': 'ACHAT', 'prefixe_numero': 'NF', 'ordre': 5},
            {'code': 'REL_BNQ', 'libelle': "Relevé bancaire", 'categorie': 'BANQUE', 'prefixe_numero': 'BQ', 'ordre': 6},
            {'code': 'CAISSE', 'libelle': "Pièce de caisse", 'categorie': 'CAISSE', 'prefixe_numero': 'CA', 'ordre': 7},
            {'code': 'SALAIRE', 'libelle': "Fiche de salaire", 'categorie': 'SALAIRE', 'prefixe_numero': 'SA', 'ordre': 8},
            {'code': 'OD', 'libelle': "Opération diverse", 'categorie': 'OD', 'prefixe_numero': 'OD', 'ordre': 9},
            {'code': 'AUTRE', 'libelle': "Autre", 'categorie': 'AUTRE', 'prefixe_numero': 'AU', 'ordre': 99},
        ]


# =============================================================================
# PIÈCE COMPTABLE
# =============================================================================

class PieceComptable(BaseModel):
    """Regroupement d'écritures (pièce comptable)"""

    STATUT_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("VALIDE", "Validé"),
        ("COMPTABILISE", "Comptabilisé"),
    ]

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE, related_name='pieces_comptables')
    journal = models.ForeignKey(
        Journal,
        on_delete=models.PROTECT,
        related_name='pieces',
        null=True,
        blank=True,
        help_text="Journal comptable (optionnel si le mandat n'en a pas)"
    )
    numero_piece = models.CharField(max_length=50, db_index=True)
    date_piece = models.DateField(db_index=True)
    libelle = models.TextField()

    # Type de pièce - FK vers TypePieceComptable
    type_piece = models.ForeignKey(
        TypePieceComptable,
        on_delete=models.PROTECT,
        related_name='pieces',
        help_text="Type de pièce comptable"
    )

    # Documents justificatifs (nouveau champ ManyToMany)
    documents_justificatifs = models.ManyToManyField(
        'documents.Document',
        blank=True,
        related_name='pieces_comptables',
        help_text="Documents justificatifs attachés à cette pièce"
    )

    # Dossier de classement (optionnel)
    dossier = models.ForeignKey(
        'documents.Dossier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pieces_comptables',
        help_text="Dossier de classement des justificatifs"
    )

    # Informations extraites par OCR (stockées pour référence)
    metadata_ocr = models.JSONField(
        default=dict,
        blank=True,
        help_text="Métadonnées extraites automatiquement par OCR"
    )

    # Référence externe (numéro facture fournisseur, etc.)
    reference_externe = models.CharField(
        max_length=100,
        blank=True,
        help_text="Référence externe (ex: numéro facture fournisseur)"
    )

    # Tiers (fournisseur/client)
    tiers_nom = models.CharField(max_length=200, blank=True)
    tiers_numero_tva = models.CharField(max_length=50, blank=True)

    # Montants (peuvent être pré-remplis par OCR)
    montant_ht = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    montant_tva = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    montant_ttc = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Totaux (dénormalisé pour perf)
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    equilibree = models.BooleanField(default=True, db_index=True)

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="BROUILLON",
        db_index=True
    )

    # Validation
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pieces_validees'
    )
    date_validation = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pieces_comptables"
        verbose_name = "Pièce comptable"
        verbose_name_plural = "Pièces comptables"
        ordering = ["-date_piece", "-numero_piece"]
        # Numéro unique par mandat (journal peut être null)
        # La contrainte unique est gérée différemment pour permettre journal=null
        unique_together = []
        indexes = [
            models.Index(fields=["mandat", "date_piece"]),
            models.Index(fields=["journal", "date_piece"]),
            models.Index(fields=["type_piece", "statut"]),
        ]

    def __str__(self):
        return f"{self.numero_piece} - {self.date_piece}"

    def calculer_equilibre(self):
        """Vérifie l'équilibre débit/crédit"""
        ecritures = self.ecritures.all()
        self.total_debit = sum(e.montant_debit for e in ecritures)
        self.total_credit = sum(e.montant_credit for e in ecritures)
        self.equilibree = self.total_debit == self.total_credit
        self.save(update_fields=['total_debit', 'total_credit', 'equilibree'])
        return self.equilibree

    def generer_numero(self):
        """Génère automatiquement le numéro de pièce"""
        from django.db.models import Max

        # Format: PREFIXE-AAAA-NNNNN (ex: FA-2024-00001)
        # Priorité: préfixe du type de pièce > préfixe du journal > code du journal > "PC"
        if self.type_piece and self.type_piece.prefixe_numero:
            prefixe = self.type_piece.prefixe_numero
        elif self.journal:
            prefixe = self.journal.prefixe_piece or self.journal.code
        else:
            # Fallback si pas de journal : utiliser un préfixe par défaut
            prefixe = "PC"  # Pièce Comptable

        annee = self.date_piece.year

        # Chercher le dernier numéro pour ce mandat et cette année avec ce préfixe
        filter_kwargs = {
            'mandat': self.mandat,
            'numero_piece__startswith': f"{prefixe}-{annee}-"
        }
        # Si on a un type de pièce, filtrer aussi par type
        if self.type_piece:
            filter_kwargs['type_piece'] = self.type_piece

        dernier = PieceComptable.objects.filter(
            **filter_kwargs
        ).aggregate(Max('numero_piece'))['numero_piece__max']

        if dernier:
            try:
                dernier_num = int(dernier.split('-')[-1])
                nouveau_num = dernier_num + 1
            except (ValueError, IndexError):
                nouveau_num = 1
        else:
            nouveau_num = 1

        self.numero_piece = f"{prefixe}-{annee}-{nouveau_num:05d}"
        return self.numero_piece

    def valider(self, user):
        """Valide la pièce comptable"""
        from django.utils import timezone

        if not self.equilibree:
            raise ValueError("La pièce n'est pas équilibrée")

        self.statut = "VALIDE"
        self.valide_par = user
        self.date_validation = timezone.now()
        self.save(update_fields=['statut', 'valide_par', 'date_validation'])

    @property
    def nombre_documents(self):
        """Retourne le nombre de documents justificatifs"""
        return self.documents_justificatifs.count()

    @property
    def nombre_ecritures(self):
        """Retourne le nombre d'écritures liées"""
        return self.ecritures.count()


# =============================================================================
# LETTRAGE
# =============================================================================

class Lettrage(BaseModel):
    """Lettrage de comptes (rapprochement)"""

    STATUT_CHOICES = [
        ("ACTIF", "Actif"),
        ("ANNULE", "Annulé"),
    ]

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE)
    compte = models.ForeignKey(Compte, on_delete=models.PROTECT)
    code_lettrage = models.CharField(max_length=20, unique=True)

    montant_total = models.DecimalField(max_digits=15, decimal_places=2)
    solde = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    date_lettrage = models.DateField()
    lettre_par = models.ForeignKey(User, on_delete=models.PROTECT)

    complet = models.BooleanField(default=False)

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="ACTIF")

    class Meta:
        db_table = "lettrages"
        verbose_name = "Lettrage"
        verbose_name_plural = "Lettrages"
        unique_together = [["mandat", "compte", "code_lettrage"]]

    def __str__(self):
        return f"{self.code_lettrage} - {self.compte.numero}"
