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


class ConfigurationTVA(BaseModel):
    """Configuration TVA d'un mandat"""

    METHODE_CHOICES = [
        ('EFFECTIVE', 'Méthode effective'),
        ('TAUX_DETTE', 'Méthode des taux de la dette fiscale nette'),
        ('TAUX_FORFAITAIRE', 'Méthode des taux forfaitaires'),
        ('FORFAIT_BRANCHE', 'Forfait selon la branche'),
    ]

    # Conservé pour compatibilité/migration
    PERIODICITE_CHOICES = [
        ('TRIMESTRIEL', 'Trimestriel'),
        ('SEMESTRIEL', 'Semestriel'),
    ]

    mandat = models.OneToOneField(
        Mandat, on_delete=models.CASCADE,
        related_name='config_tva',
        verbose_name='Mandat',
        help_text='Mandat concerné par cette configuration TVA'
    )

    # Assujettissement
    assujetti_tva = models.BooleanField(
        default=True,
        verbose_name='Assujetti TVA',
        help_text='Indique si l\'entreprise est assujettie à la TVA'
    )
    numero_tva = models.CharField(
        max_length=20, blank=True,
        verbose_name='Numéro TVA',
        help_text='Numéro IDE/TVA (ex: CHE-123.456.789 TVA)'
    )
    date_debut_assujettissement = models.DateField(
        null=True, blank=True,
        verbose_name='Début assujettissement',
        help_text='Date de début d\'assujettissement à la TVA'
    )
    date_fin_assujettissement = models.DateField(
        null=True, blank=True,
        verbose_name='Fin assujettissement',
        help_text='Date de fin d\'assujettissement (si applicable)'
    )

    # Méthode
    methode_calcul = models.CharField(
        max_length=20, choices=METHODE_CHOICES,
        default='EFFECTIVE',
        verbose_name='Méthode de calcul',
        help_text='Méthode de décompte TVA utilisée'
    )

    # Nouveau: Référence vers Periodicite
    periodicite_ref = models.ForeignKey(
        Periodicite,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='configurations_tva',
        verbose_name='Périodicité',
        help_text='Périodicité de déclaration TVA'
    )
    # Ancien champ conservé pour compatibilité/migration
    periodicite = models.CharField(
        max_length=20,
        choices=PERIODICITE_CHOICES,
        default='TRIMESTRIEL',
        verbose_name='Périodicité (ancien)',
        blank=True
    )

    # Taux forfaitaires (si applicable)
    taux_forfaitaire_ventes = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name='Taux forfaitaire ventes',
        help_text='Taux forfaitaire applicable aux ventes en %'
    )
    taux_forfaitaire_achats = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name='Taux forfaitaire achats',
        help_text='Taux forfaitaire applicable aux achats en %'
    )

    # Options
    option_imposition_prestations = models.BooleanField(
        default=False,
        verbose_name='Option imposition prestations',
        help_text='Option pour l\'imposition de prestations exclues du champ de l\'impôt'
    )
    option_reduction_deduction = models.BooleanField(
        default=False,
        verbose_name='Option réduction déduction',
        help_text='Option pour la réduction de la déduction de l\'impôt préalable'
    )

    # Comptes de liaison
    compte_tva_due = models.ForeignKey(
        'comptabilite.Compte', on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name='Compte TVA due',
        help_text='Compte de passif pour la TVA due (ex: 2200)'
    )
    compte_tva_prealable = models.ForeignKey(
        'comptabilite.Compte', on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name='Compte TVA préalable',
        help_text='Compte d\'actif pour l\'impôt préalable (ex: 1170)'
    )

    class Meta:
        db_table = 'configurations_tva'
        verbose_name = 'Configuration TVA'

    def __str__(self):
        return f"Config TVA - {self.mandat.numero}"


class TauxTVA(BaseModel):
    """Taux de TVA en vigueur"""

    TYPE_CHOICES = [
        ('NORMAL', 'Taux normal'),
        ('REDUIT', 'Taux réduit'),
        ('SPECIAL', 'Taux spécial hébergement'),
    ]

    type_taux = models.CharField(
        max_length=10, choices=TYPE_CHOICES,
        verbose_name='Type de taux',
        help_text='Catégorie du taux TVA'
    )
    taux = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='Taux',
        help_text='Taux de TVA en pourcentage'
    )

    date_debut = models.DateField(
        verbose_name='Date de début',
        help_text='Date d\'entrée en vigueur du taux'
    )
    date_fin = models.DateField(
        null=True, blank=True,
        verbose_name='Date de fin',
        help_text='Date de fin de validité (vide si toujours en vigueur)'
    )

    description = models.CharField(
        max_length=255,
        verbose_name='Description',
        help_text='Description du taux'
    )

    class Meta:
        db_table = 'taux_tva'
        verbose_name = 'Taux TVA'
        verbose_name_plural = 'Taux TVA'
        ordering = ['-date_debut', 'type_taux']

    def __str__(self):
        return f"{self.get_type_taux_display()} - {self.taux}%"

    @classmethod
    def get_taux_actif(cls, date, type_taux='NORMAL'):
        """Récupère le taux applicable à une date donnée"""
        return cls.objects.filter(
            type_taux=type_taux,
            date_debut__lte=date,
        ).filter(
            Q(date_fin__gte=date) | Q(date_fin__isnull=True)
        ).first()


class CodeTVA(BaseModel):
    """Codes TVA (chiffres du décompte AFC)"""

    CATEGORIE_CHOICES = [
        ('CHIFFRE_AFFAIRES', 'Chiffre d\'affaires'),
        ('PRESTATIONS_IMPOSABLES', 'Prestations imposables'),
        ('PRESTATIONS_EXCLUES', 'Prestations exclues'),
        ('TVA_DUE', 'TVA due'),
        ('TVA_PREALABLE', 'Impôt préalable'),
        ('DEDUCTIONS', 'Déductions'),
        ('CORRECTIONS', 'Corrections'),
    ]

    code = models.CharField(
        max_length=10, unique=True, db_index=True,
        verbose_name='Code',
        help_text='Code du chiffre AFC (ex: 200, 302, 400)'
    )
    libelle = models.CharField(
        max_length=255,
        verbose_name='Libellé',
        help_text='Intitulé du code TVA'
    )
    categorie = models.CharField(
        max_length=30, choices=CATEGORIE_CHOICES,
        verbose_name='Catégorie',
        help_text='Section du décompte TVA'
    )

    ordre_affichage = models.IntegerField(
        default=0,
        verbose_name='Ordre d\'affichage',
        help_text='Position dans le formulaire de décompte'
    )

    # Calcul automatique
    taux_applicable = models.ForeignKey(
        TauxTVA, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Taux applicable',
        help_text='Taux TVA associé à ce code'
    )
    formule = models.CharField(
        max_length=255, blank=True,
        verbose_name='Formule',
        help_text='Formule de calcul (ex: base * taux / 100)'
    )

    # Compte(s) de liaison
    comptes_associes = models.ManyToManyField(
        'comptabilite.Compte', blank=True,
        verbose_name='Comptes associés',
        help_text='Comptes comptables liés à ce code TVA'
    )

    actif = models.BooleanField(
        default=True,
        verbose_name='Actif',
        help_text='Indique si ce code est utilisable'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Explication détaillée du code'
    )

    class Meta:
        db_table = 'codes_tva'
        verbose_name = 'Code TVA'
        ordering = ['categorie', 'ordre_affichage', 'code']

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class DeclarationTVA(BaseModel):
    """Décompte TVA trimestriel/semestriel"""

    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('EN_COURS', 'En cours de préparation'),
        ('A_VALIDER', 'À valider'),
        ('VALIDE', 'Validé'),
        ('SOUMIS', 'Soumis à l\'AFC'),
        ('ACCEPTE', 'Accepté par l\'AFC'),
        ('PAYE', 'Payé'),
        ('CLOTURE', 'Clôturé'),
    ]

    TYPE_DECOMPTE_CHOICES = [
        ('NORMAL', 'Décompte normal'),
        ('FINAL', 'Décompte final'),
        ('COMPLEMENTAIRE', 'Décompte complémentaire'),
        ('RECTIFICATIF', 'Décompte rectificatif'),
    ]

    # Identification
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='declarations_tva',
        verbose_name='Mandat',
        help_text='Mandat concerné par cette déclaration'
    )
    numero_declaration = models.CharField(
        max_length=50, unique=True, db_index=True,
        verbose_name='Numéro de déclaration',
        help_text='Identifiant unique de la déclaration'
    )

    # Période
    annee = models.IntegerField(
        db_index=True,
        verbose_name='Année',
        help_text='Année fiscale'
    )
    trimestre = models.IntegerField(
        null=True, blank=True,
        verbose_name='Trimestre',
        help_text='Trimestre (1, 2, 3 ou 4)'
    )
    semestre = models.IntegerField(
        null=True, blank=True,
        verbose_name='Semestre',
        help_text='Semestre (1 ou 2)'
    )
    periode_debut = models.DateField(
        verbose_name='Début de période',
        help_text='Premier jour de la période déclarée'
    )
    periode_fin = models.DateField(
        verbose_name='Fin de période',
        help_text='Dernier jour de la période déclarée'
    )

    # Type
    type_decompte = models.CharField(
        max_length=20, choices=TYPE_DECOMPTE_CHOICES,
        default='NORMAL',
        verbose_name='Type de décompte',
        help_text='Nature de la déclaration'
    )
    methode = models.CharField(
        max_length=20,
        verbose_name='Méthode',
        help_text='Méthode de calcul utilisée'
    )

    # Montants globaux (dénormalisé pour performance)
    chiffre_affaires_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='CA total',
        help_text='Chiffre d\'affaires total en CHF'
    )
    chiffre_affaires_imposable = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='CA imposable',
        help_text='Chiffre d\'affaires soumis à la TVA en CHF'
    )

    tva_due_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='TVA due totale',
        help_text='Total de la TVA due en CHF'
    )
    tva_prealable_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='TVA préalable totale',
        help_text='Total de l\'impôt préalable déductible en CHF'
    )

    deductions_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Déductions totales',
        help_text='Total des déductions en CHF'
    )
    corrections_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Corrections totales',
        help_text='Total des corrections en CHF'
    )

    solde_tva = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Solde TVA',
        help_text='Montant à payer (positif) ou à récupérer (négatif)'
    )

    # Statut et soumission
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        default='BROUILLON', db_index=True,
        verbose_name='Statut',
        help_text='État d\'avancement de la déclaration'
    )

    date_creation_decompte = models.DateField(
        auto_now_add=True,
        verbose_name='Date de création',
        help_text='Date de création du décompte'
    )
    date_validation = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date de validation',
        help_text='Date et heure de validation interne'
    )
    valide_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name='Validé par',
        help_text='Utilisateur ayant validé la déclaration'
    )

    date_soumission = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date de soumission',
        help_text='Date et heure de soumission à l\'AFC'
    )
    soumis_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name='Soumis par',
        help_text='Utilisateur ayant soumis la déclaration'
    )

    numero_reference_afc = models.CharField(
        max_length=50, blank=True,
        verbose_name='Référence AFC',
        help_text='Numéro de référence attribué par l\'AFC'
    )

    date_echeance_paiement = models.DateField(
        null=True, blank=True,
        verbose_name='Échéance de paiement',
        help_text='Date limite de paiement'
    )
    date_paiement = models.DateField(
        null=True, blank=True,
        verbose_name='Date de paiement',
        help_text='Date effective du paiement'
    )

    # Fichiers
    fichier_xml = models.FileField(
        upload_to='tva/xml/', null=True, blank=True,
        verbose_name='Fichier XML',
        help_text='Export XML pour soumission électronique'
    )
    fichier_pdf = models.FileField(
        upload_to='tva/pdf/', null=True, blank=True,
        verbose_name='Fichier PDF',
        help_text='Version PDF de la déclaration'
    )

    # Notes
    remarques_internes = models.TextField(
        blank=True,
        verbose_name='Remarques internes',
        help_text='Notes internes sur cette déclaration'
    )
    commentaires_afc = models.TextField(
        blank=True,
        verbose_name='Commentaires AFC',
        help_text='Commentaires reçus de l\'AFC'
    )

    class Meta:
        db_table = 'declarations_tva'
        verbose_name = 'Déclaration TVA'
        ordering = ['-annee', '-trimestre', '-semestre']
        indexes = [
            models.Index(fields=['mandat', 'annee', 'trimestre']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        if self.trimestre:
            return f"TVA {self.annee} T{self.trimestre} - {self.mandat.numero}"
        else:
            return f"TVA {self.annee} S{self.semestre} - {self.mandat.numero}"

    def save(self, *args, **kwargs):
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

        # Supprimer les lignes existantes
        self.lignes.all().delete()

        # Récupérer les opérations non intégrées de la période
        operations = OperationTVA.objects.filter(
            mandat=self.mandat,
            date_operation__gte=self.periode_debut,
            date_operation__lte=self.periode_fin,
            integre_declaration=False,
        )

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
            ligne = LigneTVA.objects.create(
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

        # Recalculer les totaux (via signals ou manuellement)
        self.recalculer_totaux()

        return self

    def recalculer_totaux(self):
        """Recalcule tous les totaux de la déclaration"""
        from django.db.models import Sum

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

        # Solde
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

    def generer_xml(self):
        """Génère le fichier XML AFC"""
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        from django.core.files.base import ContentFile

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
        p.drawString(2 * cm, height - 2 * cm, "DÉCLARATION TVA SUISSE")

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

        totaux = [
            ("TVA due:", f"{self.tva_due_total:,.2f} CHF", colors.red),
            ("TVA préalable:", f"{self.tva_prealable_total:,.2f} CHF", colors.green),
            ("Déductions:", f"{self.deductions_total:,.2f} CHF", colors.black),
            ("Corrections:", f"{self.corrections_total:,.2f} CHF", colors.black),
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
        p.drawRightString(width - 2 * cm, y, f"{abs(self.solde_tva):,.2f} CHF")

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
        self.fichier_pdf.save(
            f"TVA_{self.numero_declaration}.pdf",
            ContentFile(pdf_content),
            save=True
        )

        return self.fichier_pdf


class LigneTVA(BaseModel):
    """Ligne de décompte TVA"""

    declaration = models.ForeignKey(
        DeclarationTVA, on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name='Déclaration',
        help_text='Déclaration TVA contenant cette ligne'
    )
    code_tva = models.ForeignKey(
        CodeTVA, on_delete=models.PROTECT,
        verbose_name='Code TVA',
        help_text='Code du chiffre AFC'
    )

    # Montants
    base_imposable = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Base imposable',
        help_text='Montant hors taxe en CHF'
    )
    taux_tva = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Taux TVA',
        help_text='Taux de TVA appliqué en %'
    )
    montant_tva = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Montant TVA',
        help_text='Montant de TVA calculé en CHF'
    )

    # Détails
    libelle = models.CharField(
        max_length=255, blank=True,
        verbose_name='Libellé',
        help_text='Description courte de la ligne'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Détails complémentaires'
    )

    # Calcul automatique ou manuel
    calcul_automatique = models.BooleanField(
        default=True,
        verbose_name='Calcul automatique',
        help_text='Calculer automatiquement le montant TVA'
    )

    # Ordre d'affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name='Ordre',
        help_text='Position d\'affichage dans la déclaration'
    )

    class Meta:
        db_table = 'lignes_tva'
        verbose_name = 'Ligne TVA'
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
        ('VENTE', 'Vente'),
        ('ACHAT', 'Achat'),
        ('IMPORT', 'Importation'),
        ('EXPORT', 'Exportation'),
        ('INTRA_COM', 'Intracommunautaire'),
        ('AUTRE', 'Autre'),
    ]

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        verbose_name='Mandat',
        help_text='Mandat concerné par cette opération'
    )
    declaration_tva = models.ForeignKey(
        DeclarationTVA, on_delete=models.CASCADE,
        related_name='operations',
        null=True, blank=True,
        verbose_name='Déclaration TVA',
        help_text='Déclaration dans laquelle cette opération est intégrée'
    )

    # Lien avec comptabilité
    ecriture_comptable = models.ForeignKey(
        'comptabilite.EcritureComptable',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='operations_tva',
        verbose_name='Écriture comptable',
        help_text='Écriture comptable associée'
    )

    # Détails opération
    date_operation = models.DateField(
        db_index=True,
        verbose_name='Date de l\'opération',
        help_text='Date de l\'opération TVA'
    )
    type_operation = models.CharField(
        max_length=20, choices=TYPE_OPERATION_CHOICES,
        verbose_name='Type d\'opération',
        help_text='Nature de l\'opération'
    )

    # Montants
    montant_ht = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Montant HT',
        help_text='Montant hors taxe en CHF'
    )
    code_tva = models.ForeignKey(
        CodeTVA, on_delete=models.PROTECT,
        verbose_name='Code TVA',
        help_text='Code du chiffre AFC applicable'
    )
    taux_tva = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='Taux TVA',
        help_text='Taux de TVA appliqué en %'
    )
    montant_tva = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Montant TVA',
        help_text='Montant de TVA en CHF'
    )
    montant_ttc = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Montant TTC',
        help_text='Montant toutes taxes comprises en CHF'
    )

    # Tiers
    tiers = models.CharField(
        max_length=255, blank=True,
        verbose_name='Tiers',
        help_text='Nom du client ou fournisseur'
    )
    numero_tva_tiers = models.CharField(
        max_length=20, blank=True,
        verbose_name='N° TVA tiers',
        help_text='Numéro de TVA du tiers'
    )

    # Justification
    numero_facture = models.CharField(
        max_length=50, blank=True,
        verbose_name='N° facture',
        help_text='Numéro de la facture correspondante'
    )
    libelle = models.TextField(
        verbose_name='Libellé',
        help_text='Description de l\'opération'
    )

    # Traitement
    integre_declaration = models.BooleanField(
        default=False, db_index=True,
        verbose_name='Intégré à déclaration',
        help_text='Indique si l\'opération a été intégrée à une déclaration'
    )
    date_integration = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date d\'intégration',
        help_text='Date et heure d\'intégration à la déclaration'
    )

    class Meta:
        db_table = 'operations_tva'
        verbose_name = 'Opération TVA'
        ordering = ['-date_operation']
        indexes = [
            models.Index(fields=['mandat', 'date_operation']),
            models.Index(fields=['declaration_tva']),
            models.Index(fields=['integre_declaration']),
        ]

    def __str__(self):
        return f"{self.date_operation} - {self.libelle[:50]} - {self.montant_tva} CHF"


class CorrectionTVA(BaseModel):
    """Corrections TVA (ex: autoconsommation, usage privé)"""

    TYPE_CORRECTION_CHOICES = [
        ('AUTOCONSOMMATION', 'Autoconsommation'),
        ('USAGE_PRIVE', 'Usage privé'),
        ('CORRECTION_DEDUCTION', 'Correction déduction impôt préalable'),
        ('SUBVENTION', 'Correction subventions'),
        ('AUTRE', 'Autre correction'),
    ]

    declaration = models.ForeignKey(
        DeclarationTVA, on_delete=models.CASCADE,
        related_name='corrections',
        verbose_name='Déclaration',
        help_text='Déclaration TVA concernée'
    )

    type_correction = models.CharField(
        max_length=30, choices=TYPE_CORRECTION_CHOICES,
        verbose_name='Type de correction',
        help_text='Nature de la correction'
    )
    code_tva = models.ForeignKey(
        CodeTVA, on_delete=models.PROTECT,
        verbose_name='Code TVA',
        help_text='Code du chiffre AFC concerné'
    )

    base_calcul = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Base de calcul',
        help_text='Montant servant de base au calcul en CHF'
    )
    taux = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='Taux',
        help_text='Taux appliqué pour la correction en %'
    )
    montant_correction = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Montant de correction',
        help_text='Montant de la correction en CHF'
    )

    description = models.TextField(
        verbose_name='Description',
        help_text='Explication de la correction'
    )
    justification = models.TextField(
        blank=True,
        verbose_name='Justification',
        help_text='Éléments justifiant cette correction'
    )

    class Meta:
        db_table = 'corrections_tva'
        verbose_name = 'Correction TVA'

    def __str__(self):
        return f"Correction {self.get_type_correction_display()} - {self.montant_correction} CHF"