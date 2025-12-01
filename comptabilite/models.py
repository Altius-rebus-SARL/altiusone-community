# apps/comptabilite/models.py
from django.db import models
from core.models import BaseModel, Mandat, User, ExerciceComptable
from decimal import Decimal


class PlanComptable(BaseModel):
    """Plan comptable de référence"""

    TYPE_CHOICES = [
        ('PME', 'Plan comptable PME'),
        ('GENERAL', 'Plan comptable général'),
        ('ENTREPRISE', 'Plan comptable entreprise'),
        ('PERSONNALISE', 'Personnalisé'),
        ('OHADA', 'Plan comptable OHADA'),
        ('SWISSGAAP', 'Plan comptable Swiss GAAP') ,
    ]

    nom = models.CharField(max_length=300)
    type_plan = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)

    # Template de base ou instance spécifique
    is_template = models.BooleanField(default=False, db_index=True)
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='plans_comptables',
                               null=True, blank=True)
    base_sur = models.ForeignKey('self', on_delete=models.SET_NULL,
                                 null=True, blank=True,
                                 related_name='derives')

    class Meta:
        db_table = 'plans_comptables'
        verbose_name = 'Plan comptable'

    def __str__(self):
        return f"{self.nom} ({self.get_type_plan_display()})"


class Compte(BaseModel):
    """Compte du plan comptable"""

    TYPE_COMPTE_CHOICES = [
        ('ACTIF', 'Actif'),
        ('PASSIF', 'Passif'),
        ('CHARGE', 'Charge'),
        ('PRODUIT', 'Produit'),
    ]

    CLASSE_CHOICES = [
        (1, 'Classe 1 - Actifs circulants'),
        (2, 'Classe 2 - Actifs immobilisés'),
        (3, 'Classe 3 - Capitaux de tiers à court terme'),
        (4, 'Classe 4 - Capitaux de tiers à long terme'),
        (5, 'Classe 5 - Capitaux propres'),
        (6, 'Classe 6 - Charges'),
        (7, 'Classe 7 - Produits'),
        (8, 'Classe 8 - Résultats'),
        (9, 'Classe 9 - Comptes de bouclements'),
    ]

    plan_comptable = models.ForeignKey(PlanComptable, on_delete=models.CASCADE,
                                       related_name='comptes')

    # Numérotation
    numero = models.CharField(max_length=20, db_index=True)
    libelle = models.CharField(max_length=255)
    libelle_court = models.CharField(max_length=100, blank=True)

    # Classification
    type_compte = models.CharField(max_length=10, choices=TYPE_COMPTE_CHOICES)
    classe = models.IntegerField(choices=CLASSE_CHOICES)
    niveau = models.IntegerField(default=1, help_text="Niveau hiérarchique")

    # Hiérarchie
    compte_parent = models.ForeignKey('self', on_delete=models.CASCADE,
                                      null=True, blank=True,
                                      related_name='sous_comptes')

    # Propriétés
    est_collectif = models.BooleanField(default=False, help_text="Compte collectif (total)")
    imputable = models.BooleanField(default=True, help_text="Peut recevoir des écritures")
    lettrable = models.BooleanField(default=False, help_text="Lettrage possible")
    obligatoire_tiers = models.BooleanField(default=False)

    # TVA
    soumis_tva = models.BooleanField(default=False)
    code_tva_defaut = models.CharField(max_length=10, blank=True,
                                       help_text="Code TVA par défaut (200, 205, etc.)")

    # Soldes
    solde_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    solde_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = 'comptes'
        verbose_name = 'Compte'
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

    compte_contrepartie_defaut = models.ForeignKey(Compte, on_delete=models.SET_NULL,
                                                   null=True, blank=True,
                                                   related_name='+')

    numerotation_auto = models.BooleanField(default=True)
    prefixe_piece = models.CharField(max_length=10, blank=True)
    dernier_numero = models.IntegerField(default=0)

    class Meta:
        db_table = 'journaux'
        verbose_name = 'Journal'
        unique_together = [['mandat', 'code']]
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.libelle}"

    def get_next_numero(self):
        """Génère le prochain numéro de pièce"""
        self.dernier_numero += 1
        self.save(update_fields=['dernier_numero'])
        return f"{self.prefixe_piece}{self.dernier_numero:05d}"


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
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='ecritures')
    exercice = models.ForeignKey(ExerciceComptable, on_delete=models.PROTECT,
                                 related_name='ecritures')
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT)

    numero_piece = models.CharField(max_length=50, db_index=True)
    numero_ligne = models.IntegerField(default=1)

    # Dates
    date_ecriture = models.DateField(db_index=True)
    date_valeur = models.DateField(null=True, blank=True)
    date_echeance = models.DateField(null=True, blank=True)

    # Comptes
    compte = models.ForeignKey(Compte, on_delete=models.PROTECT,
                               related_name='ecritures')
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
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES,
                              default='BROUILLON', db_index=True)
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, related_name='+')
    date_validation = models.DateTimeField(null=True, blank=True)

    # Document justificatif
    piece_justificative = models.ForeignKey('documents.Document',
                                            on_delete=models.SET_NULL,
                                            null=True, blank=True,
                                            related_name='ecritures')

    # Extourne
    ecriture_extournee = models.ForeignKey('self', on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           related_name='extournes')

    class Meta:
        db_table = 'ecritures_comptables'
        verbose_name = 'Écriture comptable'
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


# comptabilite/models.py - Modifier la classe PieceComptable


class PieceComptable(BaseModel):
    """Regroupement d'écritures (pièce comptable)"""

    STATUT_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("VALIDE", "Validé"),
        ("COMPTABILISE", "Comptabilisé"),
    ]

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT)
    numero_piece = models.CharField(max_length=50, unique=True, db_index=True)
    date_piece = models.DateField(db_index=True)
    libelle = models.TextField()

    # Totaux (dénormalisé pour perf)
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    equilibree = models.BooleanField(default=True, db_index=True)

    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default="BROUILLON", db_index=True
    )

    class Meta:
        db_table = "pieces_comptables"
        verbose_name = "Pièce comptable"
        verbose_name_plural = "Pièces comptables"
        ordering = ["-date_piece", "numero_piece"]
        indexes = [
            models.Index(fields=["mandat", "date_piece"]),
            models.Index(fields=["journal", "date_piece"]),
        ]

    def __str__(self):
        return f"{self.numero_piece} - {self.date_piece}"

    def calculer_equilibre(self):
        """Vérifie l'équilibre débit/crédit"""
        ecritures = self.mandat.ecritures.filter(numero_piece=self.numero_piece)
        self.total_debit = sum(e.montant_debit for e in ecritures)
        self.total_credit = sum(e.montant_credit for e in ecritures)
        self.equilibree = self.total_debit == self.total_credit
        self.save()
        return self.equilibree


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