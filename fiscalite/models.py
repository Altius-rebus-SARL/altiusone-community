# apps/fiscalite/models.py
from django.db import models
from core.models import BaseModel, Mandat, Client, User, ExerciceComptable, SwissCantons
from decimal import Decimal


class DeclarationFiscale(BaseModel):
    """Déclaration fiscale (impôts)"""

    TYPE_DECLARATION_CHOICES = [
        ('PERSONNE_PHYSIQUE', 'Personne physique'),
        ('PERSONNE_MORALE', 'Personne morale'),
    ]

    TYPE_IMPOT_CHOICES = [
        ('IFD', 'Impôt fédéral direct (IFD)'),
        ('ICC', 'Impôt cantonal et communal (ICC)'),
        ('FORTUNE', 'Impôt sur la fortune'),
        ('BENEFICE', 'Impôt sur le bénéfice'),
        ('CAPITAL', 'Impôt sur le capital'),
    ]

    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('EN_PREPARATION', 'En préparation'),
        ('A_VALIDER', 'À valider'),
        ('VALIDE', 'Validé'),
        ('DEPOSE', 'Déposé'),
        ('ACCEPTE', 'Accepté'),
        ('TAXATION_RECUE', 'Taxation reçue'),
        ('CONTESTE', 'Contesté'),
        ('CLOTURE', 'Clôturé'),
    ]

    # Identification
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='declarations_fiscales')
    numero_declaration = models.CharField(max_length=50, unique=True, db_index=True)

    # Type
    type_declaration = models.CharField(max_length=30, choices=TYPE_DECLARATION_CHOICES)
    type_impot = models.CharField(max_length=20, choices=TYPE_IMPOT_CHOICES)

    # Période
    exercice_comptable = models.ForeignKey(ExerciceComptable, on_delete=models.PROTECT,
                                           related_name='declarations_fiscales',
                                           null=True, blank=True)
    annee_fiscale = models.IntegerField(db_index=True)
    periode_debut = models.DateField()
    periode_fin = models.DateField()

    # Autorité fiscale
    canton = models.CharField(max_length=2, choices=SwissCantons.choices, verbose_name='Canton')
    commune = models.CharField(max_length=100, blank=True)
    numero_contribuable = models.CharField(max_length=50, blank=True,
                                           help_text='Numéro de contribuable')

    # Montants clés (dénormalisé pour perf)
    benefice_avant_impots = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    benefice_imposable = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    capital_propre = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    capital_imposable = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    impot_federal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impot_cantonal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impot_communal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impot_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Statut
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES,
                              default='BROUILLON', db_index=True)

    # Dates importantes
    date_creation = models.DateField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='declarations_validees')

    date_depot = models.DateField(null=True, blank=True)
    date_limite_depot = models.DateField(null=True, blank=True)

    date_taxation = models.DateField(null=True, blank=True)
    numero_taxation = models.CharField(max_length=50, blank=True)

    # Fichiers
    fichier_declaration = models.FileField(upload_to='fiscalite/declarations/',
                                           null=True, blank=True)
    fichier_taxation = models.FileField(upload_to='fiscalite/taxations/',
                                        null=True, blank=True)

    # Notes
    remarques = models.TextField(blank=True)

    class Meta:
        db_table = 'declarations_fiscales'
        verbose_name = 'Déclaration fiscale'
        ordering = ['-annee_fiscale', '-date_creation']
        indexes = [
            models.Index(fields=['mandat', 'annee_fiscale']),
            models.Index(fields=['type_impot', 'statut']),
            models.Index(fields=['canton', 'annee_fiscale']),
        ]

    def __str__(self):
        return f"{self.numero_declaration} - {self.get_type_impot_display()} {self.annee_fiscale}"

    def save(self, *args, **kwargs):
        if not self.numero_declaration:
            # Format: FISC-IFD-2024-001
            type_code = self.type_impot
            last = DeclarationFiscale.objects.filter(
                type_impot=self.type_impot,
                annee_fiscale=self.annee_fiscale
            ).order_by('numero_declaration').last()

            seq = 1 if not last else int(last.numero_declaration.split('-')[-1]) + 1
            self.numero_declaration = f"FISC-{type_code}-{self.annee_fiscale}-{seq:03d}"

        # Calcul impôt total
        self.impot_total = self.impot_federal + self.impot_cantonal + self.impot_communal

        super().save(*args, **kwargs)


class AnnexeFiscale(BaseModel):
    """Annexes et formulaires fiscaux"""

    TYPE_ANNEXE_CHOICES = [
        ('BILAN', 'Bilan fiscal'),
        ('COMPTE_RESULTATS', 'Compte de résultats'),
        ('TABLEAU_AMORTISSEMENTS', 'Tableau des amortissements'),
        ('PARTICIPATIONS', 'Participations'),
        ('IMMOBILIER', 'Immobilier'),
        ('PROVISIONS', 'Provisions et réserves'),
        ('CHARGES_PERSONNEL', 'Charges de personnel'),
        ('AUTRE', 'Autre annexe'),
    ]

    declaration = models.ForeignKey(DeclarationFiscale, on_delete=models.CASCADE,
                                    related_name='annexes')

    type_annexe = models.CharField(max_length=50, choices=TYPE_ANNEXE_CHOICES)
    titre = models.CharField(max_length=255)

    # Contenu structuré
    donnees = models.JSONField(default=dict, blank=True, help_text="""
    Données structurées de l'annexe
    """)

    # Ordre d'affichage
    ordre = models.IntegerField(default=0)

    # Fichier associé
    fichier = models.FileField(upload_to='fiscalite/annexes/',
                               null=True, blank=True)

    class Meta:
        db_table = 'annexes_fiscales'
        verbose_name = 'Annexe fiscale'
        ordering = ['declaration', 'ordre']

    def __str__(self):
        return f"{self.declaration.numero_declaration} - {self.titre}"


class CorrectionFiscale(BaseModel):
    """Corrections fiscales (différences compta/fiscal)"""

    TYPE_CORRECTION_CHOICES = [
        ('AMORTISSEMENT', 'Amortissement supplémentaire'),
        ('PROVISION', 'Provision non admise'),
        ('CHARGE_NON_DEDUCTIBLE', 'Charge non déductible'),
        ('PRODUIT_NON_IMPOSABLE', 'Produit non imposable'),
        ('PERTE_REPORT', 'Report de pertes'),
        ('DEPRECIATION', 'Dépréciation'),
        ('PARTICIPATION', 'Réduction pour participations'),
        ('AUTRE', 'Autre correction'),
    ]

    declaration = models.ForeignKey(DeclarationFiscale, on_delete=models.CASCADE,
                                    related_name='corrections')

    type_correction = models.CharField(max_length=50, choices=TYPE_CORRECTION_CHOICES)
    description = models.TextField()

    # Montants
    montant_comptable = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    montant_correction = models.DecimalField(max_digits=15, decimal_places=2,
                                             help_text='Positif = augmentation, Négatif = diminution')
    montant_fiscal = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Référence comptable
    compte = models.ForeignKey('comptabilite.Compte', on_delete=models.SET_NULL,
                               null=True, blank=True)

    # Justification
    justification = models.TextField(blank=True)
    reference_legale = models.CharField(max_length=255, blank=True,
                                        help_text='Article de loi, circulaire AFC')

    class Meta:
        db_table = 'corrections_fiscales'
        verbose_name = 'Correction fiscale'
        ordering = ['declaration', 'type_correction']

    def __str__(self):
        return f"{self.get_type_correction_display()} - {self.montant_correction} CHF"

    def save(self, *args, **kwargs):
        self.montant_fiscal = self.montant_comptable + self.montant_correction
        super().save(*args, **kwargs)


class ReportPerte(BaseModel):
    """Report de pertes fiscales"""

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='reports_pertes')

    annee_origine = models.IntegerField(db_index=True,
                                        help_text='Année de la perte')
    montant_perte = models.DecimalField(max_digits=15, decimal_places=2)

    montant_utilise = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    montant_restant = models.DecimalField(max_digits=15, decimal_places=2)

    annee_expiration = models.IntegerField(help_text='Année d\'expiration (7 ans)')
    expire = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = 'reports_pertes'
        verbose_name = 'Report de perte'
        ordering = ['annee_origine']
        indexes = [
            models.Index(fields=['mandat', 'expire']),
        ]

    def __str__(self):
        return f"Perte {self.annee_origine} - {self.montant_restant} CHF restant"

    def save(self, *args, **kwargs):
        self.montant_restant = self.montant_perte - self.montant_utilise

        # Vérification expiration
        from datetime import date
        if date.today().year > self.annee_expiration:
            self.expire = True

        super().save(*args, **kwargs)


class UtilisationPerte(BaseModel):
    """Utilisation d'un report de perte"""

    report_perte = models.ForeignKey(ReportPerte, on_delete=models.CASCADE,
                                     related_name='utilisations')
    declaration_fiscale = models.ForeignKey(DeclarationFiscale, on_delete=models.CASCADE,
                                            related_name='pertes_utilisees')

    montant_utilise = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        db_table = 'utilisations_perte'
        verbose_name = 'Utilisation de perte'

    def __str__(self):
        return f"Utilisation {self.montant_utilise} CHF - Perte {self.report_perte.annee_origine}"


class TauxImposition(BaseModel):
    """Taux d'imposition par canton/commune"""

    TYPE_IMPOT_CHOICES = [
        ('IFD_BENEFICE', 'IFD Bénéfice'),
        ('ICC_BENEFICE', 'ICC Bénéfice'),
        ('ICC_CAPITAL', 'ICC Capital'),
    ]

    canton = models.CharField(max_length=2, choices=SwissCantons.choices, verbose_name='Canton')
    commune = models.CharField(max_length=100, blank=True)

    type_impot = models.CharField(max_length=20, choices=TYPE_IMPOT_CHOICES)
    annee = models.IntegerField(db_index=True)

    # Taux ou barème
    taux_fixe = models.DecimalField(max_digits=5, decimal_places=2,
                                    null=True, blank=True,
                                    help_text='Taux en %')

    bareme = models.JSONField(default=dict, blank=True, help_text="""
    Barème progressif si applicable:
    {
        "tranches": [
            {"min": 0, "max": 100000, "taux": 3.5},
            {"min": 100000, "max": 500000, "taux": 5.0}
        ]
    }
    """)

    # Multiplicateurs cantonaux/communaux
    multiplicateur_cantonal = models.DecimalField(max_digits=6, decimal_places=2,
                                                  null=True, blank=True)
    multiplicateur_communal = models.DecimalField(max_digits=6, decimal_places=2,
                                                  null=True, blank=True)

    actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'taux_imposition'
        verbose_name = 'Taux d\'imposition'
        unique_together = [['canton', 'commune', 'type_impot', 'annee']]
        ordering = ['canton', 'annee']

    def __str__(self):
        return f"{self.canton} - {self.get_type_impot_display()} {self.annee}"

    def calculer_impot(self, base_imposable):
        """Calcule l'impôt sur une base imposable"""
        if self.taux_fixe:
            return (base_imposable * self.taux_fixe / 100).quantize(Decimal('0.01'))

        # Application barème progressif
        if self.bareme and 'tranches' in self.bareme:
            impot = Decimal('0')
            for tranche in self.bareme['tranches']:
                min_tranche = Decimal(str(tranche['min']))
                max_tranche = Decimal(str(tranche['max']))
                taux = Decimal(str(tranche['taux']))

                if base_imposable > min_tranche:
                    montant_tranche = min(base_imposable, max_tranche) - min_tranche
                    impot += montant_tranche * taux / 100

            # Application multiplicateurs
            if self.multiplicateur_cantonal:
                impot *= self.multiplicateur_cantonal
            if self.multiplicateur_communal:
                impot *= self.multiplicateur_communal

            return impot.quantize(Decimal('0.01'))

        return Decimal('0')


class ReclamationFiscale(BaseModel):
    """Réclamation/Contestation fiscale"""

    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('DEPOSEE', 'Déposée'),
        ('EN_TRAITEMENT', 'En traitement'),
        ('ACCEPTEE', 'Acceptée'),
        ('PARTIELLEMENT_ACCEPTEE', 'Partiellement acceptée'),
        ('REFUSEE', 'Refusée'),
        ('RETIREE', 'Retirée'),
    ]

    declaration = models.ForeignKey(DeclarationFiscale, on_delete=models.CASCADE,
                                    related_name='reclamations')

    date_reclamation = models.DateField()
    motif = models.TextField()

    montant_conteste = models.DecimalField(max_digits=12, decimal_places=2)
    montant_demande = models.DecimalField(max_digits=12, decimal_places=2)

    statut = models.CharField(max_length=30, choices=STATUT_CHOICES,
                              default='BROUILLON')

    date_reponse = models.DateField(null=True, blank=True)
    montant_accorde = models.DecimalField(max_digits=12, decimal_places=2,
                                          null=True, blank=True)

    decision = models.TextField(blank=True)

    fichier_reclamation = models.FileField(upload_to='fiscalite/reclamations/',
                                           null=True, blank=True)
    fichier_decision = models.FileField(upload_to='fiscalite/decisions/',
                                        null=True, blank=True)

    class Meta:
        db_table = 'reclamations_fiscales'
        verbose_name = 'Réclamation fiscale'
        ordering = ['-date_reclamation']

    def __str__(self):
        return f"Réclamation {self.declaration.numero_declaration} - {self.montant_conteste} CHF"


class OptimisationFiscale(BaseModel):
    """Opportunités d'optimisation fiscale identifiées"""

    CATEGORIE_CHOICES = [
        ('AMORTISSEMENT', 'Amortissement accéléré'),
        ('PROVISION', 'Constitution provisions'),
        ('INVESTISSEMENT', 'Investissements déductibles'),
        ('STRUCTURE', 'Optimisation structure'),
        ('TIMING', 'Timing charges/produits'),
        ('AUTRE', 'Autre optimisation'),
    ]

    STATUT_CHOICES = [
        ('IDENTIFIEE', 'Identifiée'),
        ('EN_ANALYSE', 'En analyse'),
        ('VALIDEE', 'Validée'),
        ('EN_COURS', 'Mise en œuvre en cours'),
        ('REALISEE', 'Réalisée'),
        ('ABANDONNEE', 'Abandonnée'),
    ]

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='optimisations_fiscales')

    categorie = models.CharField(max_length=30, choices=CATEGORIE_CHOICES)
    titre = models.CharField(max_length=255)
    description = models.TextField()

    # Impact estimé
    economie_estimee = models.DecimalField(max_digits=12, decimal_places=2,
                                           help_text='Économie d\'impôt estimée')
    annee_application = models.IntegerField()

    # Risque et conformité
    niveau_risque = models.CharField(max_length=20, choices=[
        ('FAIBLE', 'Faible'),
        ('MOYEN', 'Moyen'),
        ('ELEVE', 'Élevé'),
    ], default='FAIBLE')

    reference_legale = models.CharField(max_length=255, blank=True)

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES,
                              default='IDENTIFIEE')

    date_identification = models.DateField(auto_now_add=True)
    date_realisation = models.DateField(null=True, blank=True)

    economie_reelle = models.DecimalField(max_digits=12, decimal_places=2,
                                          null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'optimisations_fiscales'
        verbose_name = 'Optimisation fiscale'
        ordering = ['-economie_estimee']

    def __str__(self):
        return f"{self.titre} - Économie: {self.economie_estimee} CHF"