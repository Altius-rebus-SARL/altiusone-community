# apps/comptabilite/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel, Devise, Mandat, User, ExerciceComptable
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
        verbose_name=_("Code"),
        help_text=_("Code unique du type de plan (PME, OHADA, SWISSGAAP, etc.)")
    )
    nom = models.CharField(
        max_length=200,
        verbose_name=_("Nom"),
        help_text=_("Nom complet du type de plan comptable")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description détaillée du plan comptable")
    )

    # Région/Pays d'application
    pays = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Pays"),
        help_text=_("Pays d'application (Suisse, Zone OHADA, etc.)")
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Région"),
        help_text=_("Région ou zone économique d'application")
    )

    # Normes
    norme_comptable = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Norme comptable"),
        help_text=_("Norme comptable de référence (CO, OHADA, IFRS, etc.)")
    )

    # Métadonnées
    version = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Version"),
        help_text=_("Version du plan comptable")
    )
    date_publication = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de publication"),
        help_text=_("Date de publication officielle de cette version")
    )

    # Ordre d'affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name=_("Ordre"),
        help_text=_("Ordre d'affichage dans les listes de sélection")
    )

    class Meta:
        db_table = 'types_plans_comptables'
        verbose_name = _('Type de plan comptable')
        verbose_name_plural = _('Types de plans comptables')
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
        ('ACTIF', _('Actif')),
        ('PASSIF', _('Passif')),
        ('CHARGE', _('Charge')),
        ('PRODUIT', _('Produit')),
        ('RESULTAT', _('Résultat')),
    ]

    type_plan = models.ForeignKey(
        TypePlanComptable,
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name=_("Type de plan"),
        help_text=_("Type de plan comptable auquel appartient cette classe")
    )

    numero = models.IntegerField(
        verbose_name=_("Numéro"),
        help_text=_("Numéro de la classe comptable (1, 2, 3...)")
    )
    libelle = models.CharField(
        max_length=200,
        verbose_name=_("Libellé"),
        help_text=_("Libellé de la classe (ex: Actifs, Passifs)")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description détaillée de la classe comptable")
    )

    # Type de comptes dans cette classe
    type_compte = models.CharField(
        max_length=10,
        choices=TYPE_COMPTE_CHOICES,
        verbose_name=_("Type de compte"),
        help_text=_("Nature des comptes de cette classe (Actif, Passif, etc.)")
    )

    # Plage de numéros de comptes
    numero_debut = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Numéro de début"),
        help_text=_("Premier numéro de compte de cette classe (ex: 1000)")
    )
    numero_fin = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Numéro de fin"),
        help_text=_("Dernier numéro de compte de cette classe (ex: 1999)")
    )

    class Meta:
        db_table = 'classes_comptables'
        verbose_name = _('Classe comptable')
        verbose_name_plural = _('Classes comptables')
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
        verbose_name=_("Type de plan"),
        help_text=_("Type de plan comptable (PME, OHADA, Swiss GAAP, etc.)")
    )

    nom = models.CharField(
        max_length=300,
        verbose_name=_("Nom"),
        help_text=_("Nom du plan comptable")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description du plan comptable")
    )

    # Template de base ou instance spécifique
    is_template = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Est un template"),
        help_text=_("Indique si ce plan est un modèle réutilisable")
    )
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='plans_comptables',
        null=True,
        blank=True,
        verbose_name=_("Mandat"),
        help_text=_("Mandat utilisant ce plan comptable (vide pour les templates)")
    )

    # Devise du plan comptable
    devise = models.ForeignKey(
        Devise,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='plans_comptables',
        verbose_name=_("Devise"),
        help_text=_("Devise dans laquelle sont exprimés les soldes de ce plan")
    )

    # Héritage de template
    base_sur = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derives',
        verbose_name=_("Basé sur"),
        help_text=_("Plan template de base dont celui-ci dérive")
    )

    class Meta:
        db_table = 'plans_comptables'
        verbose_name = _('Plan comptable')
        verbose_name_plural = _('Plans comptables')
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
        ('ACTIF', _('Actif')),
        ('PASSIF', _('Passif')),
        ('CHARGE', _('Charge')),
        ('PRODUIT', _('Produit')),
    ]

    plan_comptable = models.ForeignKey(
        PlanComptable,
        on_delete=models.CASCADE,
        related_name='comptes',
        verbose_name=_("Plan comptable"),
        help_text=_("Plan comptable auquel appartient ce compte")
    )

    # Lien optionnel vers la classe (pour cohérence)
    classe_comptable = models.ForeignKey(
        ClasseComptable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comptes',
        verbose_name=_("Classe comptable"),
        help_text=_("Classe comptable de référence (1=Actifs, 2=Passifs, etc.)")
    )

    # Numérotation
    numero = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name=_("Numéro"),
        help_text=_("Numéro du compte (ex: 1000, 1100, 6000)")
    )
    libelle = models.CharField(
        max_length=255,
        verbose_name=_("Libellé"),
        help_text=_("Libellé complet du compte")
    )
    libelle_court = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Libellé court"),
        help_text=_("Libellé abrégé pour les états financiers")
    )

    # Classification
    type_compte = models.CharField(
        max_length=10,
        choices=TYPE_COMPTE_CHOICES,
        verbose_name=_("Type de compte"),
        help_text=_("Nature du compte (Actif, Passif, Charge, Produit)")
    )
    classe = models.IntegerField(
        verbose_name=_("Classe"),
        help_text=_("Numéro de classe comptable (1-9)")
    )
    niveau = models.IntegerField(
        default=1,
        verbose_name=_("Niveau"),
        help_text=_("Niveau hiérarchique du compte (1=principal, 2=sous-compte, etc.)")
    )

    # Hiérarchie
    compte_parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sous_comptes',
        verbose_name=_("Compte parent"),
        help_text=_("Compte de niveau supérieur pour la hiérarchie")
    )

    # Propriétés
    est_collectif = models.BooleanField(
        default=False,
        verbose_name=_("Compte collectif"),
        help_text=_("Compte collectif (total) qui regroupe des sous-comptes")
    )
    imputable = models.BooleanField(
        default=True,
        verbose_name=_("Imputable"),
        help_text=_("Indique si le compte peut recevoir des écritures comptables")
    )
    lettrable = models.BooleanField(
        default=False,
        verbose_name=_("Lettrable"),
        help_text=_("Indique si le lettrage est possible sur ce compte")
    )
    obligatoire_tiers = models.BooleanField(
        default=False,
        verbose_name=_("Tiers obligatoire"),
        help_text=_("Exige la saisie d'un tiers lors des écritures")
    )

    # TVA
    soumis_tva = models.BooleanField(
        default=False,
        verbose_name=_("Soumis à TVA"),
        help_text=_("Indique si les opérations sur ce compte sont soumises à TVA")
    )
    code_tva_defaut = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Code TVA par défaut"),
        help_text=_("Code TVA appliqué par défaut (200, 205, 300, etc.)")
    )
    code_tva_defaut_ref = models.ForeignKey(
        'tva.CodeTVA',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='comptes_defaut',
        verbose_name=_("Code TVA par défaut (référence)"),
        help_text=_("Référence structurée vers le code TVA du régime fiscal")
    )

    # Soldes
    solde_debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Solde débit"),
        help_text=_("Cumul des montants au débit")
    )
    solde_credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Solde crédit"),
        help_text=_("Cumul des montants au crédit")
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            f"{self.numero} {self.libelle}",
            self.libelle_court,
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'comptes'
        verbose_name = _('Compte')
        verbose_name_plural = _('Comptes')
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
        """Affichage du solde avec signe et devise du plan comptable"""
        solde = self.solde
        devise_code = (
            getattr(self.plan_comptable, 'devise_id', None)
            or getattr(self.plan_comptable, 'mandat', None) and self.plan_comptable.mandat.devise_id
            or Devise.get_devise_base().code
        )
        if solde >= 0:
            return f"{solde:,.2f} {devise_code}"
        else:
            return f"-{abs(solde):,.2f} {devise_code}"


# =============================================================================
# JOURNAL
# =============================================================================

class Journal(BaseModel):
    """Journal comptable"""

    TYPE_CHOICES = [
        ('VTE', _('Ventes')),
        ('ACH', _('Achats')),
        ('BNQ', _('Banque')),
        ('CAS', _('Caisse')),
        ('OD', _('Opérations diverses')),
        ('ANO', _('A-nouveaux')),
        ('EXT', _('Extourne')),
    ]

    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='journaux',
        verbose_name=_("Mandat"),
        help_text=_("Mandat auquel appartient ce journal")
    )

    code = models.CharField(
        max_length=10,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Code unique du journal (VTE, ACH, BNQ, etc.)")
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_("Libellé"),
        help_text=_("Libellé du journal")
    )
    type_journal = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name=_("Type de journal"),
        help_text=_("Type de journal (Ventes, Achats, Banque, etc.)")
    )

    devise = models.ForeignKey(
        Devise,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='journaux',
        verbose_name=_("Devise"),
        help_text=_("Devise de référence du journal (vide si multi-devise)")
    )
    compte_contrepartie_defaut = models.ForeignKey(
        Compte,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Compte de contrepartie par défaut"),
        help_text=_("Compte utilisé par défaut pour la contrepartie des écritures")
    )

    numerotation_auto = models.BooleanField(
        default=True,
        verbose_name=_("Numérotation automatique"),
        help_text=_("Active la numérotation automatique des pièces")
    )
    prefixe_piece = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Préfixe des pièces"),
        help_text=_("Préfixe ajouté aux numéros de pièces (ex: FA, AV)")
    )
    dernier_numero = models.IntegerField(
        default=0,
        verbose_name=_("Dernier numéro"),
        help_text=_("Dernier numéro de pièce utilisé dans ce journal")
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        return f"Journal {self.code} {self.libelle}"

    class Meta:
        db_table = 'journaux'
        verbose_name = _('Journal')
        verbose_name_plural = _('Journaux')
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
        ('BROUILLON', _('Brouillon')),
        ('VALIDE', _('Validée')),
        ('LETTRE', _('Lettrée')),
        ('CLOTURE', _('Clôturée')),
        ('EXTOURNE', _('Extournée')),
    ]

    # Identification
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='ecritures',
        verbose_name=_("Mandat"),
        help_text=_("Mandat concerné par cette écriture")
    )
    exercice = models.ForeignKey(
        ExerciceComptable,
        on_delete=models.PROTECT,
        related_name='ecritures',
        verbose_name=_("Exercice comptable"),
        help_text=_("Exercice comptable de l'écriture")
    )
    journal = models.ForeignKey(
        Journal,
        on_delete=models.PROTECT,
        verbose_name=_("Journal"),
        help_text=_("Journal comptable dans lequel est enregistrée l'écriture")
    )

    # Lien vers la pièce comptable (nouveau)
    piece = models.ForeignKey(
        'PieceComptable',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ecritures',
        verbose_name=_("Pièce comptable"),
        help_text=_("Pièce comptable regroupant les écritures")
    )

    numero_piece = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Numéro de pièce"),
        help_text=_("Numéro de la pièce comptable")
    )
    numero_ligne = models.IntegerField(
        default=1,
        verbose_name=_("Numéro de ligne"),
        help_text=_("Numéro de ligne dans la pièce")
    )

    # Dates
    date_ecriture = models.DateField(
        db_index=True,
        verbose_name=_("Date d'écriture"),
        help_text=_("Date de l'écriture comptable")
    )
    date_valeur = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de valeur"),
        help_text=_("Date de valeur bancaire")
    )
    date_echeance = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date d'échéance"),
        help_text=_("Date d'échéance du paiement")
    )

    # Comptes
    compte = models.ForeignKey(
        Compte,
        on_delete=models.PROTECT,
        related_name='ecritures',
        verbose_name=_("Compte"),
        help_text=_("Compte comptable mouvementé")
    )
    compte_auxiliaire = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Compte auxiliaire"),
        help_text=_("Compte auxiliaire (tiers, analytique)")
    )

    # Libellé
    libelle = models.TextField(
        verbose_name=_("Libellé"),
        help_text=_("Libellé de l'écriture comptable")
    )
    libelle_complement = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Complément de libellé"),
        help_text=_("Informations complémentaires sur l'écriture")
    )

    # Montants
    montant_debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant débit"),
        help_text=_("Montant au débit (en devise du compte)")
    )
    montant_credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant crédit"),
        help_text=_("Montant au crédit (en devise du compte)")
    )
    devise = models.ForeignKey(
        Devise,
        on_delete=models.PROTECT,
        db_column='devise',
        verbose_name=_("Devise"),
        help_text=_("Code ISO de la devise")
    )
    taux_change = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=1,
        verbose_name=_("Taux de change"),
        help_text=_("Taux de change vers la devise de référence")
    )

    # TVA
    code_tva = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Code TVA"),
        help_text=_("Code TVA applicable (200, 205, 300, etc.)")
    )
    code_tva_ref = models.ForeignKey(
        'tva.CodeTVA',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ecritures_comptables',
        verbose_name=_("Code TVA (référence)"),
        help_text=_("Référence structurée vers le code TVA du régime fiscal")
    )
    tiers = models.ForeignKey(
        'core.Tiers',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ecritures_comptables',
        verbose_name=_("Tiers"),
        help_text=_("Tiers associé à cette écriture")
    )
    montant_tva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant TVA"),
        help_text=_("Montant de TVA calculé")
    )

    # Lettrage
    code_lettrage = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        verbose_name=_("Code de lettrage"),
        help_text=_("Code identifiant le groupe de lettrage")
    )
    date_lettrage = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de lettrage"),
        help_text=_("Date à laquelle l'écriture a été lettrée")
    )

    # Statut et validation
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='BROUILLON',
        db_index=True,
        verbose_name=_("Statut"),
        help_text=_("Statut de l'écriture (Brouillon, Validée, etc.)")
    )
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
        verbose_name=_("Validé par"),
        help_text=_("Utilisateur ayant validé l'écriture")
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de validation"),
        help_text=_("Date et heure de validation de l'écriture")
    )

    # Document justificatif
    piece_justificative = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecritures',
        verbose_name=_("Pièce justificative"),
        help_text=_("Document justificatif associé à l'écriture")
    )

    # Extourne
    ecriture_extournee = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extournes',
        verbose_name=_("Écriture extournée"),
        help_text=_("Écriture d'origine si celle-ci est une extourne")
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            self.libelle,
            self.libelle_complement,
            f"Pièce {self.numero_piece}" if self.numero_piece else '',
            f"Compte {self.compte.numero} {self.compte.libelle}" if self.compte else '',
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'ecritures_comptables'
        verbose_name = _('Écriture comptable')
        verbose_name_plural = _('Écritures comptables')
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
            raise ValidationError(_("Une écriture ne peut pas avoir débit ET crédit"))

        if not self.montant_debit and not self.montant_credit:
            raise ValidationError(_("Une écriture doit avoir un montant"))

    def save(self, *args, **kwargs):
        # Auto-populate devise from mandat if not set
        if not self.devise_id and self.mandat_id:
            self.devise_id = self.mandat.devise_id
        super().save(*args, **kwargs)

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

    CATEGORIE_CHOICES = [
        ('ACHAT', _('Achats')),
        ('VENTE', _('Ventes')),
        ('BANQUE', _('Banque')),
        ('CAISSE', _('Caisse')),
        ('OD', _('Opérations diverses')),
        ('SALAIRE', _('Salaires')),
        ('AUTRE', _('Autre')),
    ]

    # Code unique pour identification
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Code unique du type de pièce (FAC_ACH, FAC_VTE, NDF, etc.)")
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_("Libellé"),
        help_text=_("Libellé du type de pièce")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description détaillée du type de pièce")
    )

    # Catégorie pour regroupement
    categorie = models.CharField(
        max_length=20,
        choices=CATEGORIE_CHOICES,
        default='AUTRE',
        db_index=True,
        verbose_name=_("Catégorie"),
        help_text=_("Catégorie de la pièce (Achats, Ventes, Banque, etc.)")
    )

    # Paramètres de numérotation
    prefixe_numero = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Préfixe de numéro"),
        help_text=_("Préfixe pour la numérotation automatique (ex: FAC, AVR)")
    )

    # Compte par défaut (pour pré-remplissage)
    compte_charge_defaut = models.ForeignKey(
        'Compte',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Compte de charge par défaut"),
        help_text=_("Compte de charge utilisé par défaut pour ce type de pièce")
    )
    compte_produit_defaut = models.ForeignKey(
        'Compte',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Compte de produit par défaut"),
        help_text=_("Compte de produit utilisé par défaut pour ce type de pièce")
    )

    # Taux de TVA par défaut
    taux_tva_defaut = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Taux TVA par défaut"),
        help_text=_("Taux de TVA appliqué par défaut (ex: 8.10)")
    )

    # Ordre d'affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name=_("Ordre"),
        help_text=_("Ordre d'affichage dans les listes de sélection")
    )

    # Dossier de classement automatique
    dossier_classement = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Dossier de classement"),
        help_text=_("Nom du sous-dossier cible pour le classement automatique (ex: Comptabilité, Salaires)")
    )

    # Est un type système (non supprimable)
    is_system = models.BooleanField(
        default=False,
        verbose_name=_("Type système"),
        help_text=_("Indique si ce type est créé par défaut et non supprimable")
    )

    class Meta:
        db_table = 'types_pieces_comptables'
        verbose_name = _('Type de pièce comptable')
        verbose_name_plural = _('Types de pièces comptables')
        ordering = ['ordre', 'code']

    def __str__(self):
        return f"{self.code} - {self.libelle}"

    # Mapping catégorie → type_journal
    CATEGORIE_JOURNAL_MAP = {
        'ACHAT': 'ACH',
        'VENTE': 'VTE',
        'BANQUE': 'BNQ',
        'CAISSE': 'CAS',
        'OD': 'OD',
        'SALAIRE': 'OD',
        'AUTRE': 'OD',
    }

    def resoudre_journal(self, mandat):
        """Résout le journal depuis la catégorie du type de pièce.

        Résolution : type exact → OD fallback → premier journal.
        """
        type_journal = self.CATEGORIE_JOURNAL_MAP.get(self.categorie, 'OD')
        journal = Journal.objects.filter(
            mandat=mandat, type_journal=type_journal
        ).first()
        if not journal:
            # Fallback : journal OD, puis n'importe quel journal
            journal = Journal.objects.filter(
                mandat=mandat, type_journal='OD'
            ).first() or Journal.objects.filter(mandat=mandat).first()
        return journal

    def resoudre_compte_charge(self, plan):
        """Résout le compte de charge par défaut dans le plan du mandat.

        Les comptes par défaut sont des comptes template. On les résout
        par numéro dans le plan actif du mandat.
        """
        if not self.compte_charge_defaut or not plan:
            return None
        return plan.comptes.filter(
            numero=self.compte_charge_defaut.numero
        ).first()

    def resoudre_compte_produit(self, plan):
        """Résout le compte de produit par défaut dans le plan du mandat."""
        if not self.compte_produit_defaut or not plan:
            return None
        return plan.comptes.filter(
            numero=self.compte_produit_defaut.numero
        ).first()

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
        ("BROUILLON", _("Brouillon")),
        ("VALIDE", _("Validé")),
        ("COMPTABILISE", _("Comptabilisé")),
    ]

    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='pieces_comptables',
        verbose_name=_("Mandat"),
        help_text=_("Mandat concerné par cette pièce")
    )
    journal = models.ForeignKey(
        Journal,
        on_delete=models.PROTECT,
        related_name='pieces',
        null=True,
        blank=True,
        verbose_name=_("Journal"),
        help_text=_("Journal comptable (optionnel si le mandat n'en a pas)")
    )
    numero_piece = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Numéro de pièce"),
        help_text=_("Numéro unique de la pièce comptable")
    )
    date_piece = models.DateField(
        db_index=True,
        verbose_name=_("Date de pièce"),
        help_text=_("Date de la pièce comptable")
    )
    libelle = models.TextField(
        verbose_name=_("Libellé"),
        help_text=_("Description de la pièce comptable")
    )

    # Type de pièce - FK vers TypePieceComptable
    type_piece = models.ForeignKey(
        TypePieceComptable,
        on_delete=models.PROTECT,
        related_name='pieces',
        verbose_name=_("Type de pièce"),
        help_text=_("Type de pièce comptable (facture, avoir, etc.)")
    )

    # Documents justificatifs (nouveau champ ManyToMany)
    documents_justificatifs = models.ManyToManyField(
        'documents.Document',
        blank=True,
        related_name='pieces_comptables',
        verbose_name=_("Documents justificatifs"),
        help_text=_("Documents justificatifs attachés à cette pièce")
    )

    # Dossier de classement (optionnel)
    dossier = models.ForeignKey(
        'documents.Dossier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pieces_comptables',
        verbose_name=_("Dossier"),
        help_text=_("Dossier de classement des justificatifs")
    )

    # Informations extraites par OCR (stockées pour référence)
    metadata_ocr = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Métadonnées OCR"),
        help_text=_("Métadonnées extraites automatiquement par OCR")
    )

    # Référence externe (numéro facture fournisseur, etc.)
    reference_externe = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Référence externe"),
        help_text=_("Référence externe (ex: numéro facture fournisseur)")
    )

    # Tiers (fournisseur/client)
    tiers_nom = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Nom du tiers"),
        help_text=_("Nom du fournisseur ou client")
    )
    tiers_numero_tva = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("N° TVA du tiers"),
        help_text=_("Numéro de TVA du fournisseur ou client")
    )
    tiers = models.ForeignKey(
        'core.Tiers',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pieces_comptables',
        verbose_name=_("Tiers (référence)"),
        help_text=_("Référence structurée vers le tiers centralisé")
    )

    # Devise
    devise = models.ForeignKey(
        Devise,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='pieces_comptables',
        verbose_name=_("Devise"),
        help_text=_("Devise des montants de cette pièce")
    )

    # Montants (peuvent être pré-remplis par OCR)
    montant_ht = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Montant HT"),
        help_text=_("Montant hors taxes")
    )
    montant_tva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Montant TVA"),
        help_text=_("Montant de la TVA")
    )
    montant_ttc = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Montant TTC"),
        help_text=_("Montant toutes taxes comprises")
    )

    # Totaux (dénormalisé pour perf)
    total_debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Total débit"),
        help_text=_("Somme des montants au débit")
    )
    total_credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Total crédit"),
        help_text=_("Somme des montants au crédit")
    )
    equilibree = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Équilibrée"),
        help_text=_("Indique si la pièce est équilibrée (débit = crédit)")
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="BROUILLON",
        db_index=True,
        verbose_name=_("Statut"),
        help_text=_("Statut de la pièce comptable")
    )

    # Validation
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pieces_validees',
        verbose_name=_("Validé par"),
        help_text=_("Utilisateur ayant validé la pièce")
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de validation"),
        help_text=_("Date et heure de validation de la pièce")
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            f"Pièce {self.numero_piece}",
            self.libelle,
            self.reference_externe,
            self.tiers_nom,
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = "pieces_comptables"
        verbose_name = _("Pièce comptable")
        verbose_name_plural = _("Pièces comptables")
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

    def save(self, *args, **kwargs):
        # Auto-résoudre le journal depuis le type de pièce si non défini
        if not self.journal_id and self.type_piece_id and self.mandat_id:
            self.journal = self.type_piece.resoudre_journal(self.mandat)
        super().save(*args, **kwargs)

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
            raise ValueError(_("La pièce n'est pas équilibrée"))

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
        ("ACTIF", _("Actif")),
        ("ANNULE", _("Annulé")),
    ]

    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        verbose_name=_("Mandat"),
        help_text=_("Mandat concerné par ce lettrage")
    )
    compte = models.ForeignKey(
        Compte,
        on_delete=models.PROTECT,
        verbose_name=_("Compte"),
        help_text=_("Compte comptable concerné par le lettrage")
    )
    code_lettrage = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Code de lettrage"),
        help_text=_("Code unique identifiant ce lettrage")
    )

    montant_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("Montant total"),
        help_text=_("Montant total des écritures lettrées")
    )
    solde = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Solde"),
        help_text=_("Solde résiduel du lettrage (0 si complet)")
    )

    date_lettrage = models.DateField(
        verbose_name=_("Date de lettrage"),
        help_text=_("Date à laquelle le lettrage a été effectué")
    )
    lettre_par = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_("Lettré par"),
        help_text=_("Utilisateur ayant effectué le lettrage")
    )

    complet = models.BooleanField(
        default=False,
        verbose_name=_("Complet"),
        help_text=_("Indique si le lettrage est complet (solde = 0)")
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="ACTIF",
        verbose_name=_("Statut"),
        help_text=_("Statut du lettrage (Actif ou Annulé)")
    )

    class Meta:
        db_table = "lettrages"
        verbose_name = _("Lettrage")
        verbose_name_plural = _("Lettrages")
        unique_together = [["mandat", "compte", "code_lettrage"]]

    def __str__(self):
        return f"{self.code_lettrage} - {self.compte.numero}"


# ══════════════════════════════════════════════════════════════
# COMPTABILITE ANALYTIQUE
# ══════════════════════════════════════════════════════════════

class AxeAnalytique(BaseModel):
    """
    Dimension d'analyse : centre de coût, département, projet, etc.

    Chaque mandat peut définir ses propres axes. Un axe regroupe
    des sections analytiques qui servent à ventiler les écritures.
    """

    mandat = models.ForeignKey(
        'core.Mandat', on_delete=models.CASCADE,
        related_name='axes_analytiques',
        verbose_name=_('Mandat')
    )
    code = models.CharField(max_length=50, verbose_name=_('Code'))
    libelle = models.CharField(max_length=200, verbose_name=_('Libellé'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    obligatoire = models.BooleanField(
        default=False,
        verbose_name=_('Obligatoire'),
        help_text=_('Si coché, chaque écriture doit être ventilée sur cet axe')
    )
    ordre = models.IntegerField(default=0, verbose_name=_('Ordre'))

    class Meta:
        db_table = 'axes_analytiques'
        verbose_name = _('Axe analytique')
        verbose_name_plural = _('Axes analytiques')
        ordering = ['ordre', 'code']
        unique_together = [['mandat', 'code']]

    def __str__(self):
        return f"{self.code} - {self.libelle}"

    def texte_pour_embedding(self):
        parts = [
            f"Axe analytique: {self.libelle}",
            f"Code: {self.code}",
            self.description,
        ]
        return ' '.join(filter(None, parts))


class SectionAnalytique(BaseModel):
    """
    Valeur dans un axe analytique.

    Ex: axe "Département" → sections "Marketing", "R&D", "Direction".
    Hiérarchique (parent optionnel) pour les structures arborescentes.
    """

    axe = models.ForeignKey(
        AxeAnalytique, on_delete=models.CASCADE,
        related_name='sections',
        verbose_name=_('Axe')
    )
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True, related_name='sous_sections',
        verbose_name=_('Section parente')
    )
    code = models.CharField(max_length=50, verbose_name=_('Code'))
    libelle = models.CharField(max_length=200, verbose_name=_('Libellé'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    budget_annuel = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name=_('Budget annuel')
    )
    responsable = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
        verbose_name=_('Responsable')
    )
    ordre = models.IntegerField(default=0, verbose_name=_('Ordre'))

    class Meta:
        db_table = 'sections_analytiques'
        verbose_name = _('Section analytique')
        verbose_name_plural = _('Sections analytiques')
        ordering = ['axe', 'ordre', 'code']
        unique_together = [['axe', 'code']]

    def __str__(self):
        return f"{self.axe.code}/{self.code} - {self.libelle}"

    def texte_pour_embedding(self):
        parts = [
            f"Section analytique: {self.libelle}",
            f"Axe: {self.axe.libelle}",
            f"Code: {self.axe.code}/{self.code}",
            f"Budget: {self.budget_annuel}" if self.budget_annuel else '',
            self.description,
        ]
        return ' '.join(filter(None, parts))


class VentilationAnalytique(BaseModel):
    """
    Répartition d'une écriture comptable sur une section analytique.

    Une écriture peut être ventilée sur plusieurs sections
    (ex: 60% Marketing, 40% R&D). Le total des pourcentages
    par axe doit faire 100% (vérifié côté applicatif).
    """

    ecriture = models.ForeignKey(
        'comptabilite.EcritureComptable', on_delete=models.CASCADE,
        related_name='ventilations_analytiques',
        verbose_name=_('Écriture')
    )
    section = models.ForeignKey(
        SectionAnalytique, on_delete=models.CASCADE,
        related_name='ventilations',
        verbose_name=_('Section')
    )
    pourcentage = models.DecimalField(
        max_digits=6, decimal_places=2,
        verbose_name=_('Pourcentage'),
        help_text=_('Part de l\'écriture affectée à cette section (0-100)')
    )
    montant = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_('Montant'),
        help_text=_('Montant calculé (écriture × pourcentage / 100)')
    )

    class Meta:
        db_table = 'ventilations_analytiques'
        verbose_name = _('Ventilation analytique')
        verbose_name_plural = _('Ventilations analytiques')
        indexes = [
            models.Index(fields=['ecriture', 'section']),
        ]

    def __str__(self):
        return f"{self.ecriture} → {self.section} ({self.pourcentage}%)"


# ══════════════════════════════════════════════════════════════
# IMMOBILISATIONS & AMORTISSEMENTS
# ══════════════════════════════════════════════════════════════

class Immobilisation(BaseModel):
    """
    Actif immobilisé (matériel, véhicule, licence, etc.).

    Suit le plan comptable suisse : immobilisations corporelles (1500-1599)
    et incorporelles (1700-1799). Génère les écritures d'amortissement.
    """

    METHODE_CHOICES = [
        ('LINEAIRE', _('Linéaire')),
        ('DEGRESSIF', _('Dégressif')),
        ('UNITE_PRODUCTION', _('Unités de production')),
    ]

    STATUT_CHOICES = [
        ('ACTIF', _('Actif')),
        ('AMORTI', _('Totalement amorti')),
        ('CEDE', _('Cédé')),
        ('MIS_AU_REBUT', _('Mis au rebut')),
    ]

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='immobilisations',
        verbose_name=_('Mandat')
    )
    numero = models.CharField(
        max_length=50, verbose_name=_('Numéro inventaire')
    )
    designation = models.CharField(
        max_length=255, verbose_name=_('Désignation')
    )
    description = models.TextField(blank=True, verbose_name=_('Description'))
    categorie = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Catégorie'),
        help_text=_('Code ParametreMetier (module=comptabilite, categorie=type_immobilisation)')
    )

    # Acquisition
    date_acquisition = models.DateField(verbose_name=_("Date d'acquisition"))
    date_mise_en_service = models.DateField(
        null=True, blank=True, verbose_name=_('Date de mise en service')
    )
    valeur_acquisition = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_("Valeur d'acquisition")
    )
    fournisseur = models.CharField(
        max_length=255, blank=True, verbose_name=_('Fournisseur')
    )
    numero_facture = models.CharField(
        max_length=100, blank=True, verbose_name=_('N° facture')
    )

    # Comptes
    compte_immobilisation = models.ForeignKey(
        'comptabilite.Compte', on_delete=models.PROTECT,
        related_name='immobilisations_actif',
        verbose_name=_('Compte immobilisation'),
        help_text=_('Compte actif au bilan (ex: 1500)')
    )
    compte_amortissement = models.ForeignKey(
        'comptabilite.Compte', on_delete=models.PROTECT,
        related_name='immobilisations_amort',
        verbose_name=_('Compte amortissement'),
        help_text=_('Compte de charge (ex: 6800)')
    )
    compte_amort_cumule = models.ForeignKey(
        'comptabilite.Compte', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='immobilisations_amort_cumule',
        verbose_name=_('Compte amort. cumulé'),
        help_text=_('Correctif actif, si méthode indirecte (ex: 1509)')
    )

    # Amortissement
    methode_amortissement = models.CharField(
        max_length=20, choices=METHODE_CHOICES, default='LINEAIRE',
        verbose_name=_("Méthode d'amortissement")
    )
    duree_amortissement_mois = models.IntegerField(
        verbose_name=_('Durée amort. (mois)'),
        help_text=_('Durée de vie utile en mois')
    )
    taux_amortissement = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name=_("Taux d'amortissement (%)"),
        help_text=_('Pour méthode dégressive (ex: 25.00)')
    )
    valeur_residuelle = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Valeur résiduelle')
    )

    # État actuel
    amortissement_cumule = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Amortissement cumulé')
    )
    valeur_nette_comptable = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Valeur nette comptable')
    )

    # Cession
    date_cession = models.DateField(
        null=True, blank=True, verbose_name=_('Date de cession')
    )
    prix_cession = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name=_('Prix de cession')
    )

    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='ACTIF',
        db_index=True, verbose_name=_('Statut')
    )
    devise = models.ForeignKey(
        Devise, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
        verbose_name=_('Devise')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        db_table = 'immobilisations'
        verbose_name = _('Immobilisation')
        verbose_name_plural = _('Immobilisations')
        ordering = ['numero']
        indexes = [
            models.Index(fields=['mandat', 'statut']),
        ]
        unique_together = [['mandat', 'numero']]

    def __str__(self):
        return f"{self.numero} - {self.designation}"

    def texte_pour_embedding(self):
        parts = [
            f"Immobilisation: {self.designation}",
            f"N° {self.numero}",
            f"Catégorie: {self.categorie}" if self.categorie else '',
            f"Acquisition: {self.date_acquisition} — {self.valeur_acquisition}",
            f"Amort. {self.get_methode_amortissement_display()} {self.duree_amortissement_mois} mois",
            f"VNC: {self.valeur_nette_comptable}",
            f"Statut: {self.get_statut_display()}",
            self.description,
        ]
        return ' '.join(filter(None, parts))


# ══════════════════════════════════════════════════════════════
# RAPPROCHEMENT BANCAIRE
# ══════════════════════════════════════════════════════════════

class ReleveBancaire(BaseModel):
    """
    Relevé de compte bancaire importé (CSV, MT940, CAMT.053).

    Contient les lignes brutes du relevé. Le rapprochement consiste
    à matcher chaque ligne avec une écriture comptable existante.
    """

    STATUT_CHOICES = [
        ('IMPORTE', _('Importé')),
        ('EN_COURS', _('Rapprochement en cours')),
        ('RAPPROCHE', _('Rapproché')),
        ('VALIDE', _('Validé')),
    ]

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='releves_bancaires',
        verbose_name=_('Mandat')
    )
    compte_bancaire = models.ForeignKey(
        'core.CompteBancaire', on_delete=models.CASCADE,
        related_name='releves',
        verbose_name=_('Compte bancaire')
    )
    journal = models.ForeignKey(
        'comptabilite.Journal', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='releves_bancaires',
        verbose_name=_('Journal bancaire')
    )

    # Période
    date_debut = models.DateField(verbose_name=_('Date début'))
    date_fin = models.DateField(verbose_name=_('Date fin'))
    reference = models.CharField(
        max_length=100, blank=True, verbose_name=_('Référence')
    )

    # Soldes
    solde_debut = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_('Solde début')
    )
    solde_fin = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_('Solde fin')
    )
    devise = models.ForeignKey(
        Devise, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
        verbose_name=_('Devise')
    )

    # Import
    format_import = models.CharField(
        max_length=20, blank=True,
        verbose_name=_('Format'),
        help_text=_('CSV, MT940, CAMT.053, etc.')
    )
    fichier_source = models.ForeignKey(
        'documents.Document', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='releves_bancaires',
        verbose_name=_('Fichier source')
    )

    # Statistiques
    nb_lignes = models.IntegerField(default=0, verbose_name=_('Nb lignes'))
    nb_rapprochees = models.IntegerField(
        default=0, verbose_name=_('Nb rapprochées')
    )
    ecart = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Écart'),
        help_text=_('Différence entre solde relevé et solde comptable')
    )

    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='IMPORTE',
        db_index=True, verbose_name=_('Statut')
    )

    class Meta:
        db_table = 'releves_bancaires'
        verbose_name = _('Relevé bancaire')
        verbose_name_plural = _('Relevés bancaires')
        ordering = ['-date_fin']
        indexes = [
            models.Index(fields=['mandat', 'compte_bancaire']),
        ]

    def __str__(self):
        return f"Relevé {self.compte_bancaire} {self.date_debut}—{self.date_fin}"

    def texte_pour_embedding(self):
        parts = [
            f"Relevé bancaire: {self.compte_bancaire}" if self.compte_bancaire_id else 'Relevé bancaire',
            f"Période: {self.date_debut} au {self.date_fin}",
            f"Solde: {self.solde_debut} → {self.solde_fin}",
            f"Statut: {self.get_statut_display()}",
            f"{self.nb_rapprochees}/{self.nb_lignes} lignes rapprochées",
        ]
        return ' '.join(filter(None, parts))


class LigneReleve(BaseModel):
    """
    Ligne d'un relevé bancaire.

    Chaque ligne peut être rapprochée avec une écriture comptable
    existante, ou générer une nouvelle écriture.
    """

    STATUT_CHOICES = [
        ('NON_RAPPROCHEE', _('Non rapprochée')),
        ('RAPPROCHEE', _('Rapprochée')),
        ('IGNOREE', _('Ignorée')),
    ]

    releve = models.ForeignKey(
        ReleveBancaire, on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_('Relevé')
    )
    date_valeur = models.DateField(verbose_name=_('Date valeur'))
    date_operation = models.DateField(
        null=True, blank=True, verbose_name=_('Date opération')
    )
    libelle = models.CharField(max_length=500, verbose_name=_('Libellé'))
    reference = models.CharField(
        max_length=200, blank=True, verbose_name=_('Référence')
    )
    montant = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_('Montant'),
        help_text=_('Positif = crédit, négatif = débit')
    )

    # Rapprochement
    ecriture = models.ForeignKey(
        'comptabilite.EcritureComptable', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lignes_releve',
        verbose_name=_('Écriture rapprochée')
    )
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='NON_RAPPROCHEE',
        db_index=True, verbose_name=_('Statut')
    )
    date_rapprochement = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date rapprochement')
    )

    class Meta:
        db_table = 'lignes_releve'
        verbose_name = _('Ligne de relevé')
        verbose_name_plural = _('Lignes de relevé')
        ordering = ['date_valeur']
        indexes = [
            models.Index(fields=['releve', 'statut']),
        ]

    def __str__(self):
        return f"{self.date_valeur} | {self.libelle[:40]} | {self.montant}"
