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
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='declarations_fiscales',
        verbose_name='Mandat',
        help_text='Mandat concerné par cette déclaration fiscale'
    )
    numero_declaration = models.CharField(
        max_length=50, unique=True, db_index=True,
        verbose_name='Numéro de déclaration',
        help_text='Identifiant unique de la déclaration (ex: FISC-IFD-2024-001)'
    )

    # Type
    type_declaration = models.CharField(
        max_length=30, choices=TYPE_DECLARATION_CHOICES,
        verbose_name='Type de déclaration',
        help_text='Personne physique ou morale'
    )
    type_impot = models.CharField(
        max_length=20, choices=TYPE_IMPOT_CHOICES,
        verbose_name='Type d\'impôt',
        help_text='Nature de l\'impôt concerné'
    )

    # Période
    exercice_comptable = models.ForeignKey(
        ExerciceComptable, on_delete=models.PROTECT,
        related_name='declarations_fiscales',
        null=True, blank=True,
        verbose_name='Exercice comptable',
        help_text='Exercice comptable lié à cette déclaration'
    )
    annee_fiscale = models.IntegerField(
        db_index=True,
        verbose_name='Année fiscale',
        help_text='Année d\'imposition'
    )
    periode_debut = models.DateField(
        verbose_name='Début de période',
        help_text='Date de début de la période fiscale'
    )
    periode_fin = models.DateField(
        verbose_name='Fin de période',
        help_text='Date de fin de la période fiscale'
    )

    # Autorité fiscale
    canton = models.CharField(
        max_length=2, choices=SwissCantons.choices,
        verbose_name='Canton',
        help_text='Canton de taxation'
    )
    commune = models.CharField(
        max_length=100, blank=True,
        verbose_name='Commune',
        help_text='Commune de taxation'
    )
    numero_contribuable = models.CharField(
        max_length=50, blank=True,
        verbose_name='Numéro de contribuable',
        help_text='Numéro attribué par l\'autorité fiscale'
    )

    # Montants clés (dénormalisé pour perf)
    benefice_avant_impots = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Bénéfice avant impôts',
        help_text='Bénéfice comptable avant impôts en CHF'
    )
    benefice_imposable = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Bénéfice imposable',
        help_text='Bénéfice après corrections fiscales en CHF'
    )

    capital_propre = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Capital propre',
        help_text='Capital propre comptable en CHF'
    )
    capital_imposable = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Capital imposable',
        help_text='Capital après corrections fiscales en CHF'
    )

    impot_federal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Impôt fédéral',
        help_text='Montant de l\'impôt fédéral direct en CHF'
    )
    impot_cantonal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Impôt cantonal',
        help_text='Montant de l\'impôt cantonal en CHF'
    )
    impot_communal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Impôt communal',
        help_text='Montant de l\'impôt communal en CHF'
    )
    impot_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Impôt total',
        help_text='Somme des impôts fédéral, cantonal et communal en CHF'
    )

    # Statut
    statut = models.CharField(
        max_length=30, choices=STATUT_CHOICES,
        default='BROUILLON', db_index=True,
        verbose_name='Statut',
        help_text='État d\'avancement de la déclaration'
    )

    # Dates importantes
    date_creation = models.DateField(
        auto_now_add=True,
        verbose_name='Date de création',
        help_text='Date de création de la déclaration'
    )
    date_validation = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date de validation',
        help_text='Date et heure de validation interne'
    )
    valide_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='declarations_validees',
        verbose_name='Validé par',
        help_text='Utilisateur ayant validé la déclaration'
    )

    date_depot = models.DateField(
        null=True, blank=True,
        verbose_name='Date de dépôt',
        help_text='Date de dépôt auprès de l\'autorité fiscale'
    )
    date_limite_depot = models.DateField(
        null=True, blank=True,
        verbose_name='Date limite de dépôt',
        help_text='Échéance pour le dépôt de la déclaration'
    )

    date_taxation = models.DateField(
        null=True, blank=True,
        verbose_name='Date de taxation',
        help_text='Date de réception de la taxation'
    )
    numero_taxation = models.CharField(
        max_length=50, blank=True,
        verbose_name='Numéro de taxation',
        help_text='Référence de la décision de taxation'
    )

    # Fichiers
    fichier_declaration = models.FileField(
        upload_to='fiscalite/declarations/',
        null=True, blank=True,
        verbose_name='Fichier déclaration',
        help_text='Document PDF de la déclaration déposée'
    )
    fichier_taxation = models.FileField(
        upload_to='fiscalite/taxations/',
        null=True, blank=True,
        verbose_name='Fichier taxation',
        help_text='Document PDF de la décision de taxation'
    )

    # Notes
    remarques = models.TextField(
        blank=True,
        verbose_name='Remarques',
        help_text='Notes et observations sur cette déclaration'
    )

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

    declaration = models.ForeignKey(
        DeclarationFiscale, on_delete=models.CASCADE,
        related_name='annexes',
        verbose_name='Déclaration',
        help_text='Déclaration fiscale à laquelle cette annexe est rattachée'
    )

    type_annexe = models.CharField(
        max_length=50, choices=TYPE_ANNEXE_CHOICES,
        verbose_name='Type d\'annexe',
        help_text='Catégorie de l\'annexe fiscale'
    )
    titre = models.CharField(
        max_length=255,
        verbose_name='Titre',
        help_text='Intitulé de l\'annexe'
    )

    # Contenu structuré
    donnees = models.JSONField(
        default=dict, blank=True,
        verbose_name='Données',
        help_text='Données structurées de l\'annexe au format JSON'
    )

    # Ordre d'affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name='Ordre',
        help_text='Position d\'affichage dans la liste des annexes'
    )

    # Fichier associé
    fichier = models.FileField(
        upload_to='fiscalite/annexes/',
        null=True, blank=True,
        verbose_name='Fichier',
        help_text='Document PDF ou autre pièce jointe'
    )

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

    declaration = models.ForeignKey(
        DeclarationFiscale, on_delete=models.CASCADE,
        related_name='corrections',
        verbose_name='Déclaration',
        help_text='Déclaration fiscale concernée'
    )

    type_correction = models.CharField(
        max_length=50, choices=TYPE_CORRECTION_CHOICES,
        verbose_name='Type de correction',
        help_text='Nature de la différence entre comptabilité et fiscalité'
    )
    description = models.TextField(
        verbose_name='Description',
        help_text='Explication détaillée de la correction'
    )

    # Montants
    montant_comptable = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Montant comptable',
        help_text='Valeur inscrite en comptabilité en CHF'
    )
    montant_correction = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Montant de correction',
        help_text='Positif = augmentation du bénéfice, Négatif = diminution'
    )
    montant_fiscal = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Montant fiscal',
        help_text='Valeur retenue fiscalement en CHF (calculé automatiquement)'
    )

    # Référence comptable
    compte = models.ForeignKey(
        'comptabilite.Compte', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Compte comptable',
        help_text='Compte du plan comptable concerné'
    )

    # Justification
    justification = models.TextField(
        blank=True,
        verbose_name='Justification',
        help_text='Argumentation et preuves supportant cette correction'
    )
    reference_legale = models.CharField(
        max_length=255, blank=True,
        verbose_name='Référence légale',
        help_text='Article de loi, circulaire AFC ou jurisprudence'
    )

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

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='reports_pertes',
        verbose_name='Mandat',
        help_text='Mandat concerné par ce report de perte'
    )

    annee_origine = models.IntegerField(
        db_index=True,
        verbose_name='Année d\'origine',
        help_text='Année durant laquelle la perte a été constatée'
    )
    montant_perte = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Montant de la perte',
        help_text='Montant initial de la perte fiscale en CHF'
    )

    montant_utilise = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Montant utilisé',
        help_text='Cumul des pertes déjà imputées en CHF'
    )
    montant_restant = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Montant restant',
        help_text='Solde de perte encore reportable en CHF'
    )

    annee_expiration = models.IntegerField(
        verbose_name='Année d\'expiration',
        help_text='Dernière année d\'utilisation possible (7 ans après l\'origine)'
    )
    expire = models.BooleanField(
        default=False, db_index=True,
        verbose_name='Expiré',
        help_text='Indique si le délai de report est dépassé'
    )

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

    report_perte = models.ForeignKey(
        ReportPerte, on_delete=models.CASCADE,
        related_name='utilisations',
        verbose_name='Report de perte',
        help_text='Perte reportée utilisée'
    )
    declaration_fiscale = models.ForeignKey(
        DeclarationFiscale, on_delete=models.CASCADE,
        related_name='pertes_utilisees',
        verbose_name='Déclaration fiscale',
        help_text='Déclaration dans laquelle la perte est imputée'
    )

    montant_utilise = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Montant utilisé',
        help_text='Montant de perte imputé sur cette déclaration en CHF'
    )

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

    canton = models.CharField(
        max_length=2, choices=SwissCantons.choices,
        verbose_name='Canton',
        help_text='Canton suisse concerné'
    )
    commune = models.CharField(
        max_length=100, blank=True,
        verbose_name='Commune',
        help_text='Commune (si taux spécifique)'
    )

    type_impot = models.CharField(
        max_length=20, choices=TYPE_IMPOT_CHOICES,
        verbose_name='Type d\'impôt',
        help_text='Nature de l\'impôt (IFD, ICC bénéfice ou capital)'
    )
    annee = models.IntegerField(
        db_index=True,
        verbose_name='Année',
        help_text='Année fiscale d\'application du taux'
    )

    # Taux ou barème
    taux_fixe = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name='Taux fixe',
        help_text='Taux d\'imposition en pourcentage (%)'
    )

    bareme = models.JSONField(
        default=dict, blank=True,
        verbose_name='Barème',
        help_text='Barème progressif au format JSON avec tranches et taux'
    )

    # Multiplicateurs cantonaux/communaux
    multiplicateur_cantonal = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        verbose_name='Multiplicateur cantonal',
        help_text='Coefficient multiplicateur cantonal'
    )
    multiplicateur_communal = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        verbose_name='Multiplicateur communal',
        help_text='Coefficient multiplicateur communal'
    )

    actif = models.BooleanField(
        default=True,
        verbose_name='Actif',
        help_text='Indique si ce taux est actuellement en vigueur'
    )

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

    declaration = models.ForeignKey(
        DeclarationFiscale, on_delete=models.CASCADE,
        related_name='reclamations',
        verbose_name='Déclaration',
        help_text='Déclaration fiscale contestée'
    )

    date_reclamation = models.DateField(
        verbose_name='Date de réclamation',
        help_text='Date de dépôt de la réclamation'
    )
    motif = models.TextField(
        verbose_name='Motif',
        help_text='Argumentation détaillée de la contestation'
    )

    montant_conteste = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Montant contesté',
        help_text='Montant d\'impôt remis en cause en CHF'
    )
    montant_demande = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Montant demandé',
        help_text='Montant d\'impôt souhaité après correction en CHF'
    )

    statut = models.CharField(
        max_length=30, choices=STATUT_CHOICES,
        default='BROUILLON',
        verbose_name='Statut',
        help_text='État d\'avancement de la réclamation'
    )

    date_reponse = models.DateField(
        null=True, blank=True,
        verbose_name='Date de réponse',
        help_text='Date de réception de la décision'
    )
    montant_accorde = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name='Montant accordé',
        help_text='Réduction d\'impôt finalement obtenue en CHF'
    )

    decision = models.TextField(
        blank=True,
        verbose_name='Décision',
        help_text='Contenu et motivation de la décision rendue'
    )

    fichier_reclamation = models.FileField(
        upload_to='fiscalite/reclamations/',
        null=True, blank=True,
        verbose_name='Fichier réclamation',
        help_text='Document PDF de la réclamation déposée'
    )
    fichier_decision = models.FileField(
        upload_to='fiscalite/decisions/',
        null=True, blank=True,
        verbose_name='Fichier décision',
        help_text='Document PDF de la décision reçue'
    )

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

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='optimisations_fiscales',
        verbose_name='Mandat',
        help_text='Mandat concerné par cette opportunité d\'optimisation'
    )

    categorie = models.CharField(
        max_length=30, choices=CATEGORIE_CHOICES,
        verbose_name='Catégorie',
        help_text='Type d\'optimisation fiscale'
    )
    titre = models.CharField(
        max_length=255,
        verbose_name='Titre',
        help_text='Intitulé court de l\'opportunité'
    )
    description = models.TextField(
        verbose_name='Description',
        help_text='Explication détaillée de l\'optimisation proposée'
    )

    # Impact estimé
    economie_estimee = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Économie estimée',
        help_text='Économie d\'impôt estimée en CHF'
    )
    annee_application = models.IntegerField(
        verbose_name='Année d\'application',
        help_text='Exercice fiscal concerné par l\'optimisation'
    )

    # Risque et conformité
    niveau_risque = models.CharField(
        max_length=20, choices=[
            ('FAIBLE', 'Faible'),
            ('MOYEN', 'Moyen'),
            ('ELEVE', 'Élevé'),
        ], default='FAIBLE',
        verbose_name='Niveau de risque',
        help_text='Évaluation du risque fiscal associé'
    )

    reference_legale = models.CharField(
        max_length=255, blank=True,
        verbose_name='Référence légale',
        help_text='Base légale supportant l\'optimisation'
    )

    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        default='IDENTIFIEE',
        verbose_name='Statut',
        help_text='État d\'avancement de l\'optimisation'
    )

    date_identification = models.DateField(
        auto_now_add=True,
        verbose_name='Date d\'identification',
        help_text='Date à laquelle l\'opportunité a été identifiée'
    )
    date_realisation = models.DateField(
        null=True, blank=True,
        verbose_name='Date de réalisation',
        help_text='Date effective de mise en œuvre'
    )

    economie_reelle = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name='Économie réelle',
        help_text='Économie d\'impôt effectivement réalisée en CHF'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text='Remarques et observations complémentaires'
    )

    class Meta:
        db_table = 'optimisations_fiscales'
        verbose_name = 'Optimisation fiscale'
        ordering = ['-economie_estimee']

    def __str__(self):
        return f"{self.titre} - Économie: {self.economie_estimee} CHF"