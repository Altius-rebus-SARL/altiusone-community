# apps/tva/models.py
from django.db import models
from core.models import BaseModel, Mandat, User, Periodicite
from decimal import Decimal
from django.db.models import Q
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import io
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from datetime import datetime
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django_countries.fields import CountryField


class RegimeFiscal(BaseModel):
    """Regime fiscal / juridiction TVA (Suisse, Cameroun, Senegal, etc.)"""

    code = models.CharField(
        max_length=20, unique=True,
        verbose_name=_('Code'),
        help_text=_('Code du regime (ex: CH, CM, SN, CI)')
    )
    nom = models.CharField(
        max_length=200,
        verbose_name=_('Nom'),
        help_text=_('Nom du regime fiscal (ex: Suisse, Cameroun OHADA)')
    )
    pays = CountryField(
        verbose_name=_('Pays'),
        help_text=_('Pays du regime fiscal')
    )
    devise_defaut = models.ForeignKey(
        'core.Devise', on_delete=models.PROTECT,
        verbose_name=_('Devise par défaut'),
        help_text=_('Devise utilisée par défaut pour ce regime')
    )
    type_plan_comptable = models.ForeignKey(
        'comptabilite.TypePlanComptable', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Type de plan comptable'),
        help_text=_('Plan comptable associé à ce regime')
    )
    nom_taxe = models.CharField(
        max_length=50, default='TVA',
        verbose_name=_('Nom de la taxe'),
        help_text=_('Nom local de la taxe (TVA, VAT, IVA)')
    )
    taux_normal = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=_('Taux normal'),
        help_text=_('Taux normal de la taxe en %')
    )
    a_taux_reduit = models.BooleanField(
        default=False,
        verbose_name=_('A un taux réduit'),
        help_text=_('Le regime propose-t-il un taux réduit ?')
    )
    a_taux_special = models.BooleanField(
        default=False,
        verbose_name=_('A un taux spécial'),
        help_text=_('Le regime propose-t-il un taux spécial ?')
    )
    format_numero_tva = models.CharField(
        max_length=255, blank=True,
        verbose_name=_('Format numéro TVA'),
        help_text=_('Expression régulière de validation du numéro TVA')
    )
    supporte_xml = models.BooleanField(
        default=False,
        verbose_name=_('Supporte export XML'),
        help_text=_('Seul le regime suisse supporte actuellement l\'export XML AFC')
    )
    methodes_disponibles = models.JSONField(
        default=list,
        verbose_name=_('Méthodes disponibles'),
        help_text=_('Liste des méthodes de calcul disponibles pour ce regime')
    )

    class Meta:
        db_table = 'regimes_fiscaux'
        verbose_name = _('Régime fiscal')
        verbose_name_plural = _('Régimes fiscaux')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.nom}"


class ConfigurationTVA(BaseModel):
    """Configuration TVA d'un mandat"""

    METHODE_CHOICES = [
        ('EFFECTIVE', _('Méthode effective')),
        ('TAUX_DETTE', _('Méthode des taux de la dette fiscale nette')),
        ('TAUX_FORFAITAIRE', _('Méthode des taux forfaitaires')),
        ('FORFAIT_BRANCHE', _('Forfait selon la branche')),
        ('REEL_NORMAL', _('Régime réel normal')),
        ('REEL_SIMPLIFIE', _('Régime réel simplifié')),
        ('FORFAITAIRE', _('Régime forfaitaire')),
    ]

    # Conservé pour compatibilité/migration
    PERIODICITE_CHOICES = [
        ('TRIMESTRIEL', _('Trimestriel')),
        ('SEMESTRIEL', _('Semestriel')),
    ]

    mandat = models.OneToOneField(
        Mandat, on_delete=models.CASCADE,
        related_name='config_tva',
        verbose_name=_('Mandat'),
        help_text=_('Mandat concerné par cette configuration TVA')
    )
    regime = models.ForeignKey(
        RegimeFiscal, on_delete=models.PROTECT,
        related_name='configurations',
        verbose_name=_('Régime fiscal'),
        help_text=_('Régime fiscal applicable à ce mandat')
    )

    # Assujettissement
    assujetti_tva = models.BooleanField(
        default=True,
        verbose_name=_('Assujetti TVA'),
        help_text=_('Indique si l\'entreprise est assujettie à la TVA')
    )
    numero_tva = models.CharField(
        max_length=20, blank=True,
        verbose_name=_('Numéro TVA'),
        help_text=_('Numéro IDE/TVA (ex: CHE-123.456.789 TVA)')
    )
    date_debut_assujettissement = models.DateField(
        null=True, blank=True,
        verbose_name=_('Début assujettissement'),
        help_text=_('Date de début d\'assujettissement à la TVA')
    )
    date_fin_assujettissement = models.DateField(
        null=True, blank=True,
        verbose_name=_('Fin assujettissement'),
        help_text=_('Date de fin d\'assujettissement (si applicable)')
    )

    # Méthode
    methode_calcul = models.CharField(
        max_length=20, choices=METHODE_CHOICES,
        default='EFFECTIVE',
        verbose_name=_('Méthode de calcul'),
        help_text=_('Méthode de décompte TVA utilisée')
    )

    # Nouveau: Référence vers Periodicite
    periodicite_ref = models.ForeignKey(
        Periodicite,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='configurations_tva',
        verbose_name=_('Périodicité'),
        help_text=_('Périodicité de déclaration TVA')
    )
    # Ancien champ conservé pour compatibilité/migration
    periodicite = models.CharField(
        max_length=20,
        choices=PERIODICITE_CHOICES,
        default='TRIMESTRIEL',
        verbose_name=_('Périodicité (ancien)'),
        blank=True
    )

    # Taux forfaitaires (si applicable)
    taux_forfaitaire_ventes = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Taux forfaitaire ventes'),
        help_text=_('Taux forfaitaire applicable aux ventes en %')
    )
    taux_forfaitaire_achats = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Taux forfaitaire achats'),
        help_text=_('Taux forfaitaire applicable aux achats en %')
    )

    # Options
    option_imposition_prestations = models.BooleanField(
        default=False,
        verbose_name=_('Option imposition prestations'),
        help_text=_('Option pour l\'imposition de prestations exclues du champ de l\'impôt')
    )
    option_reduction_deduction = models.BooleanField(
        default=False,
        verbose_name=_('Option réduction déduction'),
        help_text=_('Option pour la réduction de la déduction de l\'impôt préalable')
    )

    # Comptes de liaison
    compte_tva_due = models.ForeignKey(
        'comptabilite.Compte', on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name=_('Compte TVA due'),
        help_text=_('Compte de passif pour la TVA due (ex: 2200)')
    )
    compte_tva_prealable = models.ForeignKey(
        'comptabilite.Compte', on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name=_('Compte TVA préalable'),
        help_text=_('Compte d\'actif pour l\'impôt préalable (ex: 1170)')
    )

    class Meta:
        db_table = 'configurations_tva'
        verbose_name = _('Configuration TVA')

    def __str__(self):
        return f"Config TVA - {self.mandat.numero}"


class TauxTVA(BaseModel):
    """Taux de TVA en vigueur"""

    TYPE_CHOICES = [
        ('NORMAL', _('Taux normal')),
        ('REDUIT', _('Taux réduit')),
        ('SPECIAL', _('Taux spécial hébergement')),
        ('EXONERE', _('Exonéré')),
    ]

    regime = models.ForeignKey(
        RegimeFiscal, on_delete=models.CASCADE,
        related_name='taux',
        verbose_name=_('Régime fiscal'),
        help_text=_('Régime fiscal auquel appartient ce taux')
    )
    type_taux = models.CharField(
        max_length=10, choices=TYPE_CHOICES,
        verbose_name=_('Type de taux'),
        help_text=_('Catégorie du taux TVA')
    )
    taux = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=_('Taux'),
        help_text=_('Taux de TVA en pourcentage')
    )

    date_debut = models.DateField(
        verbose_name=_('Date de début'),
        help_text=_('Date d\'entrée en vigueur du taux')
    )
    date_fin = models.DateField(
        null=True, blank=True,
        verbose_name=_('Date de fin'),
        help_text=_('Date de fin de validité (vide si toujours en vigueur)')
    )

    description = models.CharField(
        max_length=255,
        verbose_name=_('Description'),
        help_text=_('Description du taux')
    )

    class Meta:
        db_table = 'taux_tva'
        verbose_name = _('Taux TVA')
        verbose_name_plural = _('Taux TVA')
        ordering = ['-date_debut', 'type_taux']

    def __str__(self):
        return f"{self.get_type_taux_display()} - {self.taux}%"

    @classmethod
    def get_taux_actif(cls, date, type_taux='NORMAL', regime=None):
        """Récupère le taux applicable à une date donnée"""
        qs = cls.objects.filter(
            type_taux=type_taux,
            date_debut__lte=date,
        ).filter(
            Q(date_fin__gte=date) | Q(date_fin__isnull=True)
        )
        if regime:
            qs = qs.filter(regime=regime)
        return qs.first()


class CodeTVA(BaseModel):
    """Codes TVA (chiffres du décompte AFC)"""

    CATEGORIE_CHOICES = [
        ('CHIFFRE_AFFAIRES', _('Chiffre d\'affaires')),
        ('PRESTATIONS_IMPOSABLES', _('Prestations imposables')),
        ('PRESTATIONS_EXCLUES', _('Prestations exclues')),
        ('TVA_DUE', _('TVA due')),
        ('TVA_PREALABLE', _('Impôt préalable')),
        ('DEDUCTIONS', _('Déductions')),
        ('CORRECTIONS', _('Corrections')),
    ]

    regime = models.ForeignKey(
        RegimeFiscal, on_delete=models.CASCADE,
        related_name='codes',
        verbose_name=_('Régime fiscal'),
        help_text=_('Régime fiscal auquel appartient ce code')
    )
    code = models.CharField(
        max_length=10, db_index=True,
        verbose_name=_('Code'),
        help_text=_('Code du chiffre (ex: 200, 302, 400)')
    )
    libelle = models.CharField(
        max_length=255,
        verbose_name=_('Libellé'),
        help_text=_('Intitulé du code TVA')
    )
    categorie = models.CharField(
        max_length=30, choices=CATEGORIE_CHOICES,
        verbose_name=_('Catégorie'),
        help_text=_('Section du décompte TVA')
    )

    ordre_affichage = models.IntegerField(
        default=0,
        verbose_name=_('Ordre d\'affichage'),
        help_text=_('Position dans le formulaire de décompte')
    )

    # Calcul automatique
    taux_applicable = models.ForeignKey(
        TauxTVA, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Taux applicable'),
        help_text=_('Taux TVA associé à ce code')
    )
    formule = models.CharField(
        max_length=255, blank=True,
        verbose_name=_('Formule'),
        help_text=_('Formule de calcul (ex: base * taux / 100)')
    )

    # Compte(s) de liaison
    comptes_associes = models.ManyToManyField(
        'comptabilite.Compte', blank=True,
        verbose_name=_('Comptes associés'),
        help_text=_('Comptes comptables liés à ce code TVA')
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_('Actif'),
        help_text=_('Indique si ce code est utilisable')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Explication détaillée du code')
    )

    class Meta:
        db_table = 'codes_tva'
        verbose_name = _('Code TVA')
        ordering = ['categorie', 'ordre_affichage', 'code']
        unique_together = [('regime', 'code')]

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class DeclarationTVA(BaseModel):
    """Décompte TVA trimestriel/semestriel"""

    STATUT_CHOICES = [
        ('BROUILLON', _('Brouillon')),
        ('EN_COURS', _('En cours de préparation')),
        ('A_VALIDER', _('À valider')),
        ('VALIDE', _('Validé')),
        ('SOUMIS', _('Soumis à l\'AFC')),
        ('ACCEPTE', _('Accepté par l\'AFC')),
        ('PAYE', _('Payé')),
        ('CLOTURE', _('Clôturé')),
    ]

    TYPE_DECOMPTE_CHOICES = [
        ('NORMAL', _('Décompte normal')),
        ('FINAL', _('Décompte final')),
        ('COMPLEMENTAIRE', _('Décompte complémentaire')),
        ('RECTIFICATIF', _('Décompte rectificatif')),
    ]

    # Identification
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='declarations_tva',
        verbose_name=_('Mandat'),
        help_text=_('Mandat concerné par cette déclaration')
    )
    regime_fiscal = models.ForeignKey(
        RegimeFiscal, on_delete=models.PROTECT,
        related_name='declarations_tva',
        null=True, blank=True,
        verbose_name=_('Régime fiscal'),
        help_text=_('Régime fiscal applicable à cette déclaration')
    )
    devise = models.ForeignKey(
        'core.Devise', on_delete=models.PROTECT,
        related_name='declarations_tva',
        null=True, blank=True,
        verbose_name=_('Devise'),
        help_text=_('Devise de la déclaration TVA')
    )
    numero_declaration = models.CharField(
        max_length=50, unique=True, db_index=True,
        verbose_name=_('Numéro de déclaration'),
        help_text=_('Identifiant unique de la déclaration')
    )

    # Période
    annee = models.IntegerField(
        db_index=True,
        verbose_name=_('Année'),
        help_text=_('Année fiscale')
    )
    trimestre = models.IntegerField(
        null=True, blank=True,
        verbose_name=_('Trimestre'),
        help_text=_('Trimestre (1, 2, 3 ou 4)')
    )
    semestre = models.IntegerField(
        null=True, blank=True,
        verbose_name=_('Semestre'),
        help_text=_('Semestre (1 ou 2)')
    )
    periode_debut = models.DateField(
        verbose_name=_('Début de période'),
        help_text=_('Premier jour de la période déclarée')
    )
    periode_fin = models.DateField(
        verbose_name=_('Fin de période'),
        help_text=_('Dernier jour de la période déclarée')
    )

    # Type
    type_decompte = models.CharField(
        max_length=20, choices=TYPE_DECOMPTE_CHOICES,
        default='NORMAL',
        verbose_name=_('Type de décompte'),
        help_text=_('Nature de la déclaration')
    )
    methode = models.CharField(
        max_length=20,
        verbose_name=_('Méthode'),
        help_text=_('Méthode de calcul utilisée')
    )

    # Montants globaux (dénormalisé pour performance)
    chiffre_affaires_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('CA total'),
        help_text=_('Chiffre d\'affaires total dans la devise du régime')
    )
    chiffre_affaires_imposable = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('CA imposable'),
        help_text=_('Chiffre d\'affaires soumis à la TVA dans la devise du régime')
    )

    tva_due_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('TVA due totale'),
        help_text=_('Total de la TVA due dans la devise du régime')
    )
    tva_prealable_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('TVA préalable totale'),
        help_text=_('Total de l\'impôt préalable déductible dans la devise du régime')
    )

    deductions_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Déductions totales'),
        help_text=_('Total des déductions dans la devise du régime')
    )
    corrections_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Corrections totales'),
        help_text=_('Total des corrections dans la devise du régime')
    )

    solde_tva = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Solde TVA'),
        help_text=_('Montant à payer (positif) ou à récupérer (négatif)')
    )

    # Statut et soumission
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        default='BROUILLON', db_index=True,
        verbose_name=_('Statut'),
        help_text=_('État d\'avancement de la déclaration')
    )

    date_creation_decompte = models.DateField(
        auto_now_add=True,
        verbose_name=_('Date de création'),
        help_text=_('Date de création du décompte')
    )
    date_validation = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Date de validation'),
        help_text=_('Date et heure de validation interne')
    )
    valide_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name=_('Validé par'),
        help_text=_('Utilisateur ayant validé la déclaration')
    )

    date_soumission = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Date de soumission'),
        help_text=_('Date et heure de soumission à l\'AFC')
    )
    soumis_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name=_('Soumis par'),
        help_text=_('Utilisateur ayant soumis la déclaration')
    )

    numero_reference_afc = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Référence AFC'),
        help_text=_('Numéro de référence attribué par l\'AFC')
    )

    date_echeance_paiement = models.DateField(
        null=True, blank=True,
        verbose_name=_('Échéance de paiement'),
        help_text=_('Date limite de paiement')
    )
    date_paiement = models.DateField(
        null=True, blank=True,
        verbose_name=_('Date de paiement'),
        help_text=_('Date effective du paiement')
    )

    # Fichiers
    fichier_xml = models.FileField(
        upload_to='tva/xml/', null=True, blank=True,
        verbose_name=_('Fichier XML'),
        help_text=_('Export XML pour soumission électronique')
    )
    fichier_pdf = models.FileField(
        upload_to='tva/pdf/', null=True, blank=True,
        verbose_name=_('Fichier PDF'),
        help_text=_('Version PDF de la déclaration')
    )

    # Notes
    remarques_internes = models.TextField(
        blank=True,
        verbose_name=_('Remarques internes'),
        help_text=_('Notes internes sur cette déclaration')
    )
    commentaires_afc = models.TextField(
        blank=True,
        verbose_name=_('Commentaires AFC'),
        help_text=_('Commentaires reçus de l\'AFC')
    )

    class Meta:
        db_table = 'declarations_tva'
        verbose_name = _('Déclaration TVA')
        ordering = ['-annee', '-trimestre', '-semestre']
        indexes = [
            models.Index(fields=['mandat', 'annee', 'trimestre']),
            models.Index(fields=['statut']),
        ]

    @property
    def devise_code(self):
        """Code de la devise, avec fallback via mandat"""
        return self.devise_id or self.mandat.devise_id

    def get_nom_taxe(self):
        """Nom de la taxe du régime fiscal, avec fallback TVA"""
        if self.regime_fiscal:
            return self.regime_fiscal.nom_taxe
        try:
            return self.mandat.config_tva.regime.nom_taxe
        except (AttributeError, Exception):
            return 'TVA'

    def __str__(self):
        if self.trimestre:
            return f"TVA {self.annee} T{self.trimestre} - {self.mandat.numero}"
        else:
            return f"TVA {self.annee} S{self.semestre} - {self.mandat.numero}"

    def save(self, *args, **kwargs):
        # Auto-populate regime_fiscal and devise from mandat if not set
        if not self.regime_fiscal_id:
            try:
                self.regime_fiscal = self.mandat.config_tva.regime
            except (AttributeError, Exception):
                pass
        if not self.devise_id and self.regime_fiscal:
            self.devise = self.regime_fiscal.devise_defaut

        if not self.numero_declaration:
            # Format: TVA-2025-T1-001
            periode = f"T{self.trimestre}" if self.trimestre else f"S{self.semestre}"
            last = DeclarationTVA.objects.filter(
                mandat=self.mandat,
                annee=self.annee
            ).order_by('numero_declaration').last()

            seq = 1 if not last else int(last.numero_declaration.split('-')[-1]) + 1
            self.numero_declaration = f"TVA-{self.annee}-{periode}-{seq:03d}"

        super().save(*args, **kwargs)

    def calculer_solde(self):
        """Calcule le solde TVA à payer ou à récupérer"""
        self.solde_tva = (
                self.tva_due_total
                - self.tva_prealable_total
                - self.deductions_total
                + self.corrections_total
        )
        self.save(update_fields=['solde_tva'])
        return self.solde_tva
    
    def calculer_automatiquement(self):
        """Calcule automatiquement la déclaration depuis les opérations"""
        from django.db.models import Sum

        # Récupérer les opérations non intégrées de la période
        operations = OperationTVA.objects.filter(
            mandat=self.mandat,
            date_operation__gte=self.periode_debut,
            date_operation__lte=self.periode_fin,
            integre_declaration=False,
        )

        if operations.exists():
            # Supprimer uniquement les lignes auto-calculées, préserver les manuelles
            self.lignes.filter(calcul_automatique=True).delete()

            # Grouper par code TVA
            operations_groupees = {}
            for op in operations:
                code = op.code_tva.code
                if code not in operations_groupees:
                    operations_groupees[code] = {
                        "code_tva": op.code_tva,
                        "base_imposable": Decimal("0"),
                        "montant_tva": Decimal("0"),
                        "operations": [],
                    }

                operations_groupees[code]["base_imposable"] += op.montant_ht
                operations_groupees[code]["montant_tva"] += op.montant_tva
                operations_groupees[code]["operations"].append(op)

            # Créer les lignes
            ordre = 0
            for code, data in operations_groupees.items():
                ordre += 1
                LigneTVA.objects.create(
                    declaration=self,
                    code_tva=data["code_tva"],
                    base_imposable=data["base_imposable"],
                    taux_tva=data["code_tva"].taux_applicable.taux
                    if data["code_tva"].taux_applicable
                    else Decimal("0"),
                    montant_tva=data["montant_tva"],
                    libelle=f"Opérations {self.periode_debut} - {self.periode_fin}",
                    calcul_automatique=True,
                    ordre=ordre,
                )

                # Marquer les opérations comme intégrées
                for op in data["operations"]:
                    op.integre_declaration = True
                    op.declaration_tva = self
                    op.date_integration = datetime.now()
                    op.save()

            # Recalculer les totaux depuis les lignes
            self.recalculer_totaux()
        else:
            # Pas d'opérations : calculer le solde depuis les montants saisis
            self.calculer_solde()

        return self

    def recalculer_totaux(self):
        """Recalcule tous les totaux de la déclaration depuis les lignes"""
        from django.db.models import Sum

        lignes = self.lignes.all()
        if not lignes.exists():
            # Pas de lignes : garder les montants saisis, juste recalculer le solde
            self.calculer_solde()
            return

        # Chiffre d'affaires
        self.chiffre_affaires_total = self.lignes.filter(
            code_tva__categorie="CHIFFRE_AFFAIRES"
        ).aggregate(Sum("base_imposable"))["base_imposable__sum"] or Decimal("0")

        self.chiffre_affaires_imposable = self.lignes.filter(
            code_tva__categorie="PRESTATIONS_IMPOSABLES"
        ).aggregate(Sum("base_imposable"))["base_imposable__sum"] or Decimal("0")

        # TVA
        self.tva_due_total = self.lignes.filter(
            code_tva__categorie="TVA_DUE"
        ).aggregate(Sum("montant_tva"))["montant_tva__sum"] or Decimal("0")

        self.tva_prealable_total = self.lignes.filter(
            code_tva__categorie="TVA_PREALABLE"
        ).aggregate(Sum("montant_tva"))["montant_tva__sum"] or Decimal("0")

        self.deductions_total = self.lignes.filter(
            code_tva__categorie="DEDUCTIONS"
        ).aggregate(Sum("montant_tva"))["montant_tva__sum"] or Decimal("0")

        self.corrections_total = self.corrections.aggregate(Sum("montant_correction"))[
            "montant_correction__sum"
        ] or Decimal("0")

        # Sauvegarder les totaux et calculer le solde
        self.save()
        self.calculer_solde()

    def valider(self, user):
        """Valide la déclaration"""
        if not self.lignes.exists():
            raise ValueError("La déclaration doit avoir au moins une ligne")

        self.recalculer_totaux()
        self.statut = "VALIDE"
        self.valide_par = user
        self.date_validation = datetime.now()
        self.save()

        return self

    def soumettre_afc(self, user, numero_reference=None):
        """Soumet la déclaration à l'AFC"""
        if self.statut != "VALIDE":
            raise ValueError("La déclaration doit être validée avant soumission")

        self.statut = "SOUMIS"
        self.soumis_par = user
        self.date_soumission = datetime.now()

        if numero_reference:
            self.numero_reference_afc = numero_reference

        self.save()
        return self

    def rouvrir(self):
        """Rouvre une déclaration validée pour la remettre en brouillon"""
        if self.statut != 'VALIDE':
            raise ValueError("Seule une déclaration validée peut être rouverte")
        self.statut = 'BROUILLON'
        self.valide_par = None
        self.date_validation = None
        self.save(update_fields=['statut', 'valide_par', 'date_validation'])

    def generer_xml(self):
        """Génère le fichier XML AFC (uniquement pour le régime suisse)"""
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        from django.core.files.base import ContentFile

        # Seul le régime suisse supporte l'export XML AFC
        regime_code = self.devise_code  # Utilise devise comme proxy
        try:
            regime_code = self.mandat.config_tva.regime.code
        except (AttributeError, Exception):
            pass
        if regime_code != 'CH':
            raise NotImplementedError(
                f"L'export XML n'est pas supporté pour le régime {regime_code}. "
                "Seul le régime suisse (CH) supporte l'export XML AFC."
            )

        # Créer la structure XML selon le format AFC
        root = Element("VATDeclaration")
        root.set("xmlns", "http://www.estv.admin.ch/xmlns/vat")
        root.set("version", "2.0")

        # En-tête
        header = SubElement(root, "Header")
        SubElement(header, "DeclarationNumber").text = self.numero_declaration
        SubElement(header, "Year").text = str(self.annee)

        if self.trimestre:
            SubElement(header, "Period").text = f"Q{self.trimestre}"
        else:
            SubElement(header, "Period").text = f"S{self.semestre}"

        SubElement(header, "Method").text = self.methode
        SubElement(header, "Type").text = self.type_decompte

        # Informations du mandat
        company = SubElement(root, "Company")
        SubElement(company, "Name").text = self.mandat.client.raison_sociale

        if hasattr(self.mandat, "config_tva") and self.mandat.config_tva.numero_tva:
            SubElement(company, "VATNumber").text = self.mandat.config_tva.numero_tva

        # Dates de période
        period = SubElement(root, "ReportingPeriod")
        SubElement(period, "StartDate").text = self.periode_debut.strftime("%Y-%m-%d")
        SubElement(period, "EndDate").text = self.periode_fin.strftime("%Y-%m-%d")

        # Chiffres d'affaires
        turnover = SubElement(root, "Turnover")
        SubElement(turnover, "TotalTurnover").text = f"{self.chiffre_affaires_total:.2f}"
        SubElement(turnover, "TaxableTurnover").text = f"{self.chiffre_affaires_imposable:.2f}"

        # Lignes de déclaration
        lines = SubElement(root, "DeclarationLines")

        for ligne in self.lignes.all().order_by("ordre"):
            line = SubElement(lines, "Line")
            SubElement(line, "Code").text = ligne.code_tva.code
            SubElement(line, "Label").text = ligne.code_tva.libelle
            SubElement(line, "TaxableAmount").text = f"{ligne.base_imposable:.2f}"
            SubElement(line, "Rate").text = f"{ligne.taux_tva:.2f}"
            SubElement(line, "TaxAmount").text = f"{ligne.montant_tva:.2f}"

        # Totaux
        totals = SubElement(root, "Totals")
        SubElement(totals, "TotalVATDue").text = f"{self.tva_due_total:.2f}"
        SubElement(totals, "TotalInputTax").text = f"{self.tva_prealable_total:.2f}"
        SubElement(totals, "TotalDeductions").text = f"{self.deductions_total:.2f}"
        SubElement(totals, "TotalCorrections").text = f"{self.corrections_total:.2f}"
        SubElement(totals, "NetAmount").text = f"{self.solde_tva:.2f}"

        # Corrections si présentes
        if self.corrections.exists():
            corrections = SubElement(root, "Corrections")
            for correction in self.corrections.all():
                corr = SubElement(corrections, "Correction")
                SubElement(corr, "Type").text = correction.type_correction
                SubElement(corr, "Code").text = correction.code_tva.code
                SubElement(corr, "Amount").text = f"{correction.montant_correction:.2f}"
                SubElement(corr, "Description").text = correction.description

        # Remarques
        if self.remarques_internes:
            SubElement(root, "InternalNotes").text = self.remarques_internes

        # Footer
        footer = SubElement(root, "Footer")
        SubElement(footer, "CreationDate").text = self.created_at.strftime("%Y-%m-%d")

        if self.valide_par:
            SubElement(footer, "ValidatedBy").text = self.valide_par.get_full_name()
        if self.date_validation:
            SubElement(footer, "ValidationDate").text = self.date_validation.strftime("%Y-%m-%d")

        # Convertir en string XML avec formatage
        rough_string = tostring(root, encoding="utf-8")
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding="utf-8")

        # Sauvegarder le fichier dans le modèle
        self.fichier_xml.save(
            f"TVA_{self.numero_declaration}.xml",
            ContentFile(pretty_xml),
            save=True
        )

        return self.fichier_xml


    def generer_pdf(self):
        """Génère un PDF de la déclaration"""
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        from django.core.files.base import ContentFile
        from datetime import datetime

        # Créer un buffer
        buffer = io.BytesIO()

        # Créer le PDF
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # En-tête
        p.setFont("Helvetica-Bold", 16)
        p.drawString(2 * cm, height - 2 * cm, f"DÉCLARATION {self.get_nom_taxe()}")

        p.setFont("Helvetica-Bold", 14)
        p.drawString(2 * cm, height - 3 * cm, self.numero_declaration)

        # Informations générales
        p.setFont("Helvetica-Bold", 12)
        p.drawString(2 * cm, height - 4.5 * cm, "Informations générales")

        p.setFont("Helvetica", 10)
        y = height - 5.2 * cm

        info_lines = [
            f"Entreprise: {self.mandat.client.raison_sociale}",
            f"Période: {self.periode_debut.strftime('%d.%m.%Y')} - {self.periode_fin.strftime('%d.%m.%Y')}",
            f"Année: {self.annee}",
        ]

        if self.trimestre:
            info_lines.append(f"Trimestre: {self.trimestre}")
        else:
            info_lines.append(f"Semestre: {self.semestre}")

        info_lines.extend([
            f"Méthode: {self.methode}",
            f"Type: {self.get_type_decompte_display()}",
            f"Statut: {self.get_statut_display()}",
        ])

        for line in info_lines:
            p.drawString(2 * cm, y, line)
            y -= 0.5 * cm

        # Tableau des lignes
        y -= 1 * cm
        p.setFont("Helvetica-Bold", 12)
        p.drawString(2 * cm, y, "Détail de la déclaration")
        y -= 0.7 * cm

        # Préparer les données du tableau
        table_data = [["Code", "Libellé", "Base HT", "Taux", "Montant TVA"]]

        # Grouper par catégorie
        categories = {}
        for ligne in self.lignes.all().order_by("ordre"):
            cat = ligne.code_tva.get_categorie_display()
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(ligne)

        for categorie, lignes in categories.items():
            # Ligne de catégorie
            table_data.append([categorie, "", "", "", ""])

            # Lignes de détail
            for ligne in lignes:
                table_data.append([
                    ligne.code_tva.code,
                    ligne.code_tva.libelle[:30],
                    f"{ligne.base_imposable:,.2f}",
                    f"{ligne.taux_tva:.1f}%",
                    f"{ligne.montant_tva:,.2f}",
                ])

        # Créer le tableau
        col_widths = [2 * cm, 7 * cm, 3 * cm, 2 * cm, 3 * cm]

        # Calculer la hauteur nécessaire
        row_height = 0.6 * cm
        table_height = len(table_data) * row_height

        # Si le tableau est trop grand, nouvelle page
        if y - table_height < 3 * cm:
            p.showPage()
            y = height - 2 * cm

        # Dessiner le tableau manuellement
        p.setFont("Helvetica", 9)

        for i, row in enumerate(table_data):
            x = 2 * cm

            # Ligne de catégorie en gras
            if row[1] == "":
                p.setFont("Helvetica-Bold", 9)
            else:
                p.setFont("Helvetica", 9)

            for j, cell in enumerate(row):
                if j == 0:  # Code
                    p.drawString(x, y, str(cell))
                    x += col_widths[0]
                elif j == 1:  # Libellé
                    p.drawString(x, y, str(cell))
                    x += col_widths[1]
                elif j == 2:  # Base
                    p.drawRightString(x + col_widths[2], y, str(cell))
                    x += col_widths[2]
                elif j == 3:  # Taux
                    p.drawRightString(x + col_widths[3], y, str(cell))
                    x += col_widths[3]
                elif j == 4:  # Montant
                    p.drawRightString(x + col_widths[4], y, str(cell))

            y -= row_height

        # Totaux
        y -= 1 * cm
        p.setFont("Helvetica-Bold", 11)

        devise = self.devise_code
        totaux = [
            ("TVA due:", f"{self.tva_due_total:,.2f} {devise}", colors.red),
            ("TVA préalable:", f"{self.tva_prealable_total:,.2f} {devise}", colors.green),
            ("Déductions:", f"{self.deductions_total:,.2f} {devise}", colors.black),
            ("Corrections:", f"{self.corrections_total:,.2f} {devise}", colors.black),
        ]

        for label, value, color in totaux:
            p.setFillColor(color)
            p.drawString(2 * cm, y, label)
            p.drawRightString(width - 2 * cm, y, value)
            y -= 0.7 * cm

        # Ligne de séparation
        y -= 0.3 * cm
        p.setStrokeColor(colors.black)
        p.line(2 * cm, y, width - 2 * cm, y)
        y -= 0.7 * cm

        # Solde final
        p.setFont("Helvetica-Bold", 14)

        if self.solde_tva > 0:
            p.setFillColor(colors.red)
            label = "SOLDE À PAYER:"
        elif self.solde_tva < 0:
            p.setFillColor(colors.green)
            label = "SOLDE À REMBOURSER:"
        else:
            p.setFillColor(colors.black)
            label = "SOLDE:"

        p.drawString(2 * cm, y, label)
        p.drawRightString(width - 2 * cm, y, f"{abs(self.solde_tva):,.2f} {devise}")

        # Pied de page
        p.setFont("Helvetica", 8)
        p.setFillColor(colors.black)
        footer_y = 2 * cm

        footer_text = f"Document généré le {datetime.now().strftime('%d.%m.%Y à %H:%M')}"
        if self.valide_par:
            footer_text += f" | Validé par: {self.valide_par.get_full_name()}"

        p.drawString(2 * cm, footer_y, footer_text)
        p.drawRightString(width - 2 * cm, footer_y, f"Page 1 | {self.numero_declaration}")

        # Finaliser
        p.showPage()
        p.save()

        # Récupérer le contenu du buffer
        pdf_content = buffer.getvalue()
        buffer.close()

        # Sauvegarder le fichier dans le modèle
        from core.pdf import save_pdf_overwrite
        return save_pdf_overwrite(
            self, 'fichier_pdf', pdf_content,
            f"TVA_{self.numero_declaration}.pdf"
        )


class LigneTVA(BaseModel):
    """Ligne de décompte TVA"""

    declaration = models.ForeignKey(
        DeclarationTVA, on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_('Déclaration'),
        help_text=_('Déclaration TVA contenant cette ligne')
    )
    code_tva = models.ForeignKey(
        CodeTVA, on_delete=models.PROTECT,
        verbose_name=_('Code TVA'),
        help_text=_('Code du chiffre AFC')
    )

    # Montants
    base_imposable = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Base imposable'),
        help_text=_('Montant hors taxe dans la devise du régime')
    )
    taux_tva = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Taux TVA'),
        help_text=_('Taux de TVA appliqué en %')
    )
    montant_tva = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Montant TVA'),
        help_text=_('Montant de TVA calculé dans la devise du régime')
    )

    # Détails
    libelle = models.CharField(
        max_length=255, blank=True,
        verbose_name=_('Libellé'),
        help_text=_('Description courte de la ligne')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Détails complémentaires')
    )

    # Calcul automatique ou manuel
    calcul_automatique = models.BooleanField(
        default=True,
        verbose_name=_('Calcul automatique'),
        help_text=_('Calculer automatiquement le montant TVA')
    )

    # Ordre d'affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name=_('Ordre'),
        help_text=_('Position d\'affichage dans la déclaration')
    )

    class Meta:
        db_table = 'lignes_tva'
        verbose_name = _('Ligne TVA')
        ordering = ['declaration', 'ordre', 'code_tva']

    def __str__(self):
        return f"{self.code_tva.code} - {self.montant_tva}"

    def calculer_montant(self):
        """Calcule automatiquement le montant de TVA"""
        if self.calcul_automatique and self.base_imposable and self.taux_tva:
            self.montant_tva = (self.base_imposable * self.taux_tva / 100).quantize(
                Decimal('0.01')
            )
            self.save(update_fields=['montant_tva'])
        return self.montant_tva


class OperationTVA(BaseModel):
    """Opération soumise à TVA (liée aux écritures comptables)"""

    TYPE_OPERATION_CHOICES = [
        ('VENTE', _('Vente')),
        ('ACHAT', _('Achat')),
        ('IMPORT', _('Importation')),
        ('EXPORT', _('Exportation')),
        ('INTRA_COM', _('Intracommunautaire')),
        ('AUTRE', _('Autre')),
    ]

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        verbose_name=_('Mandat'),
        help_text=_('Mandat concerné par cette opération')
    )
    declaration_tva = models.ForeignKey(
        DeclarationTVA, on_delete=models.CASCADE,
        related_name='operations',
        null=True, blank=True,
        verbose_name=_('Déclaration TVA'),
        help_text=_('Déclaration dans laquelle cette opération est intégrée')
    )

    # Lien avec comptabilité
    ecriture_comptable = models.ForeignKey(
        'comptabilite.EcritureComptable',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='operations_tva',
        verbose_name=_('Écriture comptable'),
        help_text=_('Écriture comptable associée')
    )

    # Détails opération
    date_operation = models.DateField(
        db_index=True,
        verbose_name=_('Date de l\'opération'),
        help_text=_('Date de l\'opération TVA')
    )
    type_operation = models.CharField(
        max_length=20, choices=TYPE_OPERATION_CHOICES,
        verbose_name=_('Type d\'opération'),
        help_text=_('Nature de l\'opération')
    )

    # Montants
    montant_ht = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_('Montant HT'),
        help_text=_('Montant hors taxe dans la devise du régime')
    )
    code_tva = models.ForeignKey(
        CodeTVA, on_delete=models.PROTECT,
        verbose_name=_('Code TVA'),
        help_text=_('Code du chiffre AFC applicable')
    )
    taux_tva = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=_('Taux TVA'),
        help_text=_('Taux de TVA appliqué en %')
    )
    montant_tva = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_('Montant TVA'),
        help_text=_('Montant de TVA dans la devise du régime')
    )
    montant_ttc = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_('Montant TTC'),
        help_text=_('Montant toutes taxes comprises dans la devise du régime')
    )

    # Tiers
    tiers = models.CharField(
        max_length=255, blank=True,
        verbose_name=_('Tiers'),
        help_text=_('Nom du client ou fournisseur')
    )
    tiers_ref = models.ForeignKey(
        'core.Tiers', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='operations_tva',
        verbose_name=_('Tiers (référence)'),
        help_text=_('Référence structurée vers le tiers centralisé')
    )
    numero_tva_tiers = models.CharField(
        max_length=20, blank=True,
        verbose_name=_('N° TVA tiers'),
        help_text=_('Numéro de TVA du tiers')
    )

    # Justification
    facture = models.ForeignKey(
        'facturation.Facture', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='operations_tva',
        verbose_name=_('Facture'),
        help_text=_('Facture liée à cette opération TVA')
    )
    numero_facture = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('N° facture'),
        help_text=_('Numéro de la facture correspondante')
    )
    libelle = models.TextField(
        verbose_name=_('Libellé'),
        help_text=_('Description de l\'opération')
    )

    # Traitement
    integre_declaration = models.BooleanField(
        default=False, db_index=True,
        verbose_name=_('Intégré à déclaration'),
        help_text=_('Indique si l\'opération a été intégrée à une déclaration')
    )
    date_integration = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Date d\'intégration'),
        help_text=_('Date et heure d\'intégration à la déclaration')
    )

    class Meta:
        db_table = 'operations_tva'
        verbose_name = _('Opération TVA')
        ordering = ['-date_operation']
        indexes = [
            models.Index(fields=['mandat', 'date_operation']),
            models.Index(fields=['declaration_tva']),
            models.Index(fields=['integre_declaration']),
        ]

    @property
    def devise_code(self):
        """Code de la devise via mandat"""
        return self.mandat.devise_id

    def __str__(self):
        return f"{self.date_operation} - {self.libelle[:50]} - {self.montant_tva} {self.devise_code}"


class CorrectionTVA(BaseModel):
    """Corrections TVA (ex: autoconsommation, usage privé)"""

    TYPE_CORRECTION_CHOICES = [
        ('AUTOCONSOMMATION', _('Autoconsommation')),
        ('USAGE_PRIVE', _('Usage privé')),
        ('CORRECTION_DEDUCTION', _('Correction déduction impôt préalable')),
        ('SUBVENTION', _('Correction subventions')),
        ('AUTRE', _('Autre correction')),
    ]

    declaration = models.ForeignKey(
        DeclarationTVA, on_delete=models.CASCADE,
        related_name='corrections',
        verbose_name=_('Déclaration'),
        help_text=_('Déclaration TVA concernée')
    )

    type_correction = models.CharField(
        max_length=30, choices=TYPE_CORRECTION_CHOICES,
        verbose_name=_('Type de correction'),
        help_text=_('Nature de la correction')
    )
    code_tva = models.ForeignKey(
        CodeTVA, on_delete=models.PROTECT,
        verbose_name=_('Code TVA'),
        help_text=_('Code du chiffre AFC concerné')
    )

    base_calcul = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_('Base de calcul'),
        help_text=_('Montant servant de base au calcul dans la devise du régime')
    )
    taux = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=_('Taux'),
        help_text=_('Taux appliqué pour la correction en %')
    )
    montant_correction = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_('Montant de correction'),
        help_text=_('Montant de la correction dans la devise du régime')
    )

    description = models.TextField(
        verbose_name=_('Description'),
        help_text=_('Explication de la correction')
    )
    justification = models.TextField(
        blank=True,
        verbose_name=_('Justification'),
        help_text=_('Éléments justifiant cette correction')
    )

    class Meta:
        db_table = 'corrections_tva'
        verbose_name = _('Correction TVA')

    @property
    def devise_code(self):
        """Code de la devise via déclaration ou mandat"""
        return self.declaration.devise_id or self.declaration.mandat.devise_id

    def __str__(self):
        return f"Correction {self.get_type_correction_display()} - {self.montant_correction} {self.devise_code}"