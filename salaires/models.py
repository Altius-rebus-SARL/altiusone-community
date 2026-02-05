# apps/salaires/models.py
from django.db import models
from core.models import BaseModel, Mandat, User, Adresse
from decimal import Decimal
from django.db.models import Q
from django.core.validators import RegexValidator
from django_countries.fields import CountryField

class Employe(BaseModel):
    """Employé d'un mandat client"""
    
    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
        ('X', 'Autre'),
    ]
    
    STATUT_CHOICES = [
        ('ACTIF', 'Actif'),
        ('SUSPENDU', 'Suspendu'),
        ('CONGE', 'En congé'),
        ('DEMISSION', 'Démission'),
        ('LICENCIE', 'Licencié'),
        ('RETRAITE', 'Retraité'),
    ]
    
    TYPE_CONTRAT_CHOICES = [
        ('CDI', 'Contrat durée indéterminée'),
        ('CDD', 'Contrat durée déterminée'),
        ('APPRENTI', 'Apprentissage'),
        ('STAGE', 'Stage'),
        ('TEMPORAIRE', 'Temporaire'),
    ]
    
    # Identification
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='employes',
        verbose_name='Mandat',
        help_text='Mandat employeur'
    )
    matricule = models.CharField(
        max_length=50, db_index=True,
        verbose_name='Matricule',
        help_text='Numéro d\'identification interne'
    )

    # Identité
    nom = models.CharField(
        max_length=100, db_index=True,
        verbose_name='Nom',
        help_text='Nom de famille'
    )
    prenom = models.CharField(
        max_length=100,
        verbose_name='Prénom',
        help_text='Prénom(s)'
    )
    nom_naissance = models.CharField(
        max_length=100, blank=True,
        verbose_name='Nom de naissance',
        help_text='Nom de famille à la naissance (si différent)'
    )
    date_naissance = models.DateField(
        verbose_name='Date de naissance',
        help_text='Date de naissance de l\'employé'
    )
    lieu_naissance = models.CharField(
        max_length=100, blank=True,
        verbose_name='Lieu de naissance',
        help_text='Ville et pays de naissance'
    )
    nationalite = CountryField(
        default='CH',
        verbose_name='Nationalité',
        help_text='Nationalité de l\'employé'
    )
    sexe = models.CharField(
        max_length=1, choices=SEXE_CHOICES,
        verbose_name='Sexe',
        help_text='Sexe de l\'employé'
    )
    
    # Numéros officiels
    avs_number = models.CharField(
        'Numéro AVS',
        max_length=16,
        unique=True,
        validators=[RegexValidator(
            r'^\d{3}\.\d{4}\.\d{4}\.\d{2}$',
            'Format AVS invalide (756.1234.5678.90)'
        )],
        help_text='Format: 756.1234.5678.90'
    )
    numero_permis = models.CharField('Numéro permis', max_length=20, blank=True)
    type_permis = models.CharField(max_length=2, blank=True,
                                    choices=[
                                        ('B', 'Permis B - Autorisation de séjour'),
                                        ('C', 'Permis C - Autorisation d\'établissement'),
                                        ('L', 'Permis L - Autorisation de courte durée'),
                                        ('G', 'Permis G - Frontalier'),
                                        ('F', 'Permis F - Admission provisoire'),
                                        ('N', 'Permis N - Requérant d\'asile'),
                                        ('S', 'Permis S - Protection provisoire'),
                                    ])
    date_validite_permis = models.DateField('Validité du permis', null=True, blank=True)
    
    # Coordonnées
    adresse = models.ForeignKey(
        Adresse, on_delete=models.PROTECT,
        related_name='employes',
        verbose_name='Adresse',
        help_text='Adresse de domicile'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email',
        help_text='Adresse email personnelle'
    )
    telephone = models.CharField(
        max_length=20, blank=True,
        verbose_name='Téléphone',
        help_text='Numéro de téléphone fixe'
    )
    mobile = models.CharField(
        max_length=20, blank=True,
        verbose_name='Mobile',
        help_text='Numéro de téléphone portable'
    )

    # Situation familiale
    etat_civil = models.CharField(
        max_length=20, choices=[
            ('CELIBATAIRE', 'Célibataire'),
            ('MARIE', 'Marié(e)'),
            ('DIVORCE', 'Divorcé(e)'),
            ('VEUF', 'Veuf/Veuve'),
            ('SEPARE', 'Séparé(e)'),
            ('PARTENARIAT', 'Partenariat enregistré'),
        ],
        verbose_name='État civil',
        help_text='Situation matrimoniale'
    )
    nombre_enfants = models.IntegerField(
        default=0,
        verbose_name='Nombre d\'enfants',
        help_text='Nombre d\'enfants à charge'
    )
    conjoint_travaille = models.BooleanField(
        'Conjoint actif',
        default=False,
        help_text='Le conjoint exerce-t-il une activité lucrative?'
    )
    revenus_conjoint = models.DecimalField(
        'Revenus annuels du conjoint',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Pour détermination du barème IS'
    )
    
    # Emploi
    type_contrat = models.CharField(
        max_length=20, choices=TYPE_CONTRAT_CHOICES,
        verbose_name='Type de contrat',
        help_text='Nature du contrat de travail'
    )
    date_entree = models.DateField(
        db_index=True,
        verbose_name='Date d\'entrée',
        help_text='Date de début du contrat'
    )
    date_sortie = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name='Date de sortie',
        help_text='Date de fin du contrat'
    )
    date_fin_periode_essai = models.DateField(
        null=True, blank=True,
        verbose_name='Fin période d\'essai',
        help_text='Date de fin de la période d\'essai'
    )

    fonction = models.CharField(
        max_length=100,
        verbose_name='Fonction',
        help_text='Intitulé du poste'
    )
    departement = models.CharField(
        max_length=100, blank=True,
        verbose_name='Département',
        help_text='Service ou département'
    )

    taux_occupation = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
        verbose_name='Taux d\'occupation',
        help_text='Taux en % (100 = temps plein)'
    )

    # Salaire
    salaire_brut_mensuel = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Salaire brut mensuel',
        help_text='Salaire brut mensuel en CHF'
    )
    salaire_horaire = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='Salaire horaire',
        help_text='Salaire horaire en CHF (si applicable)'
    )

    nombre_heures_semaine = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=42,
        verbose_name='Heures par semaine',
        help_text='Nombre d\'heures de travail hebdomadaires'
    )
    jours_vacances_annuel = models.IntegerField(
        default=20,
        verbose_name='Jours de vacances',
        help_text='Nombre de jours de vacances annuels'
    )

    # 13ème salaire
    treizieme_salaire = models.BooleanField(
        default=True,
        verbose_name='13ème salaire',
        help_text='L\'employé bénéficie-t-il d\'un 13ème salaire ?'
    )
    montant_13eme = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='Montant 13ème',
        help_text='Montant du 13ème salaire (si différent du salaire mensuel)'
    )

    # Paiement
    iban = models.CharField(
        max_length=34, blank=True,
        verbose_name='IBAN',
        help_text='Numéro IBAN pour le versement du salaire'
    )
    banque = models.CharField(
        max_length=100, blank=True,
        verbose_name='Banque',
        help_text='Nom de l\'établissement bancaire'
    )

    # Statut
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        default='ACTIF', db_index=True,
        verbose_name='Statut',
        help_text='Statut actuel de l\'employé'
    )
    
    # Impôt à la source
    soumis_is = models.BooleanField('Soumis impôt à la source', default=False)
    barreme_is = models.CharField('Barème IS', max_length=10, blank=True,
                                   help_text='Ex: A, B, C, etc.')
    taux_is = models.DecimalField('Taux IS', max_digits=5, decimal_places=2,
                                   null=True, blank=True)
    
    # Configuration paie
    config_cotisations = models.JSONField(
        default=dict, blank=True,
        verbose_name='Configuration cotisations',
        help_text='Paramétrage des cotisations sociales au format JSON'
    )

    # Notes
    remarques = models.TextField(
        blank=True,
        verbose_name='Remarques',
        help_text='Notes et observations'
    )
    
    class Meta:
        db_table = 'employes'
        verbose_name = 'Employé'
        unique_together = [['mandat', 'matricule']]
        ordering = ['nom', 'prenom']
        indexes = [
            models.Index(fields=['mandat', 'statut']),
            models.Index(fields=['avs_number']),
        ]
    
    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.matricule})"
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_naissance.year - (
            (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
        )
    
    @property
    def salaire_annuel_brut(self):
        base = self.salaire_brut_mensuel * 12
        if self.treizieme_salaire:
            base += self.montant_13eme or self.salaire_brut_mensuel
        return base

    def civilite(self):
        """Retourne la civilité (Monsieur/Madame)"""
        return "Monsieur" if self.sexe == 'M' else "Madame"


class EnfantEmploye(BaseModel):
    """
    Enfant d'un employé - pour les allocations familiales et le barème IS.
    En Suisse, les allocations dépendent de l'âge et du statut de formation.
    """

    TYPE_ALLOCATION_CHOICES = [
        ('NAISSANCE', 'Allocation de naissance'),
        ('ENFANT', 'Allocation pour enfant (0-16 ans)'),
        ('FORMATION', 'Allocation de formation (16-25 ans)'),
        ('AUCUNE', 'Pas d\'allocation'),
    ]

    employe = models.ForeignKey(
        Employe,
        on_delete=models.CASCADE,
        related_name='enfants'
    )

    # Identité de l'enfant
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField()
    sexe = models.CharField(max_length=1, choices=[('M', 'Masculin'), ('F', 'Féminin')])

    # Droit aux allocations
    type_allocation = models.CharField(
        'Type d\'allocation',
        max_length=20,
        choices=TYPE_ALLOCATION_CHOICES,
        default='ENFANT'
    )
    en_formation = models.BooleanField(
        'En formation',
        default=False,
        help_text='Suit une formation (apprentissage, études) - pour allocation formation jusqu\'à 25 ans'
    )
    date_fin_formation = models.DateField(
        'Fin de formation prévue',
        null=True,
        blank=True
    )

    # Garde et prise en charge
    garde_partagee = models.BooleanField(
        'Garde partagée',
        default=False,
        help_text='L\'enfant est en garde partagée avec l\'autre parent'
    )
    pourcentage_garde = models.IntegerField(
        '% de garde',
        default=100,
        help_text='Pourcentage de garde (100 si garde complète, 50 si partagée)'
    )
    autre_parent_recoit_allocation = models.BooleanField(
        'Autre parent reçoit allocation',
        default=False,
        help_text='L\'autre parent perçoit-il déjà des allocations pour cet enfant?'
    )

    # Montants (peuvent être personnalisés selon le canton)
    montant_allocation = models.DecimalField(
        'Montant mensuel',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Montant mensuel de l\'allocation (si différent du standard)'
    )

    remarques = models.TextField(blank=True)

    class Meta:
        db_table = 'enfants_employes'
        verbose_name = 'Enfant'
        verbose_name_plural = 'Enfants'
        ordering = ['date_naissance']

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.date_naissance.strftime('%d.%m.%Y')})"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_naissance.year - (
            (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
        )

    def determiner_type_allocation(self):
        """Détermine automatiquement le type d'allocation selon l'âge"""
        age = self.age
        if age < 0:
            return 'NAISSANCE'
        elif age < 16:
            return 'ENFANT'
        elif age <= 25 and self.en_formation:
            return 'FORMATION'
        return 'AUCUNE'

    def get_montant_allocation_standard(self, canton='GE'):
        """
        Retourne le montant standard d'allocation selon le canton et le type.
        Ces montants sont indicatifs et doivent être mis à jour régulièrement.
        """
        # Montants 2024 approximatifs (varient selon les cantons)
        MONTANTS = {
            'GE': {'ENFANT': 311, 'FORMATION': 415, 'NAISSANCE': 2000},
            'VD': {'ENFANT': 300, 'FORMATION': 400, 'NAISSANCE': 1500},
            'VS': {'ENFANT': 305, 'FORMATION': 440, 'NAISSANCE': 2000},
            'NE': {'ENFANT': 250, 'FORMATION': 320, 'NAISSANCE': 1200},
            'JU': {'ENFANT': 275, 'FORMATION': 325, 'NAISSANCE': 1500},
            'FR': {'ENFANT': 285, 'FORMATION': 365, 'NAISSANCE': 1500},
            'BE': {'ENFANT': 230, 'FORMATION': 290, 'NAISSANCE': 0},
            'ZH': {'ENFANT': 200, 'FORMATION': 250, 'NAISSANCE': 0},
            # Montants fédéraux minimaux par défaut
            'DEFAULT': {'ENFANT': 200, 'FORMATION': 250, 'NAISSANCE': 0},
        }
        montants_canton = MONTANTS.get(canton, MONTANTS['DEFAULT'])
        type_alloc = self.type_allocation or self.determiner_type_allocation()
        return montants_canton.get(type_alloc, 0)


class TauxCotisation(BaseModel):
    """Taux de cotisations sociales"""
    
    TYPE_COTISATION_CHOICES = [
        ('AVS', 'AVS/AI/APG'),
        ('AC', 'Assurance chômage'),
        ('AC_SUPP', 'AC supplément (>148\'200)'),
        ('LPP', 'LPP (2e pilier)'),
        ('LAA', 'LAA Accidents'),
        ('LAAC', 'LAAC Accidents complémentaire'),
        ('IJM', 'Indemnités journalières maladie'),
        ('AF', 'Allocations familiales'),
    ]
    
    REPARTITION_CHOICES = [
        ('EMPLOYEUR', 'Employeur uniquement'),
        ('EMPLOYE', 'Employé uniquement'),
        ('PARTAGE', 'Partagé employeur/employé'),
    ]
    
    type_cotisation = models.CharField(
        max_length=20, choices=TYPE_COTISATION_CHOICES,
        unique=True,
        verbose_name='Type de cotisation',
        help_text='Nature de la cotisation sociale'
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name='Libellé',
        help_text='Description de la cotisation'
    )

    # Taux
    taux_total = models.DecimalField(
        max_digits=5, decimal_places=4,
        verbose_name='Taux total',
        help_text='Taux total en % (employeur + employé)'
    )
    taux_employeur = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        verbose_name='Taux employeur',
        help_text='Part employeur en %'
    )
    taux_employe = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        verbose_name='Taux employé',
        help_text='Part employé en %'
    )

    repartition = models.CharField(
        max_length=20, choices=REPARTITION_CHOICES,
        verbose_name='Répartition',
        help_text='Mode de répartition de la cotisation'
    )

    # Limites
    salaire_min = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='Salaire minimum',
        help_text='Salaire minimum soumis à cotisation en CHF'
    )
    salaire_max = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='Salaire maximum',
        help_text='Plafond de salaire soumis en CHF'
    )

    # Validité
    date_debut = models.DateField(
        verbose_name='Date de début',
        help_text='Date d\'entrée en vigueur'
    )
    date_fin = models.DateField(
        null=True, blank=True,
        verbose_name='Date de fin',
        help_text='Date de fin de validité'
    )

    actif = models.BooleanField(
        default=True,
        verbose_name='Actif',
        help_text='Indique si ce taux est actuellement applicable'
    )
    
    class Meta:
        db_table = 'taux_cotisations'
        verbose_name = 'Taux de cotisation'
        ordering = ['type_cotisation', '-date_debut']
    
    def __str__(self):
        return f"{self.get_type_cotisation_display()} - {self.taux_total}%"
    
    @classmethod
    def get_taux_actif(cls, type_cotisation, date):
        """Récupère le taux applicable à une date"""
        return cls.objects.filter(
            type_cotisation=type_cotisation,
            date_debut__lte=date,
            actif=True
        ).filter(
            Q(date_fin__gte=date) | Q(date_fin__isnull=True)
        ).first()


class FicheSalaire(BaseModel):
    """Fiche de salaire mensuelle"""
    
    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('VALIDE', 'Validée'),
        ('PAYE', 'Payée'),
        ('COMPTABILISE', 'Comptabilisée'),
    ]
    
    # Identification
    employe = models.ForeignKey(
        Employe, on_delete=models.CASCADE,
        related_name='fiches_salaire',
        verbose_name='Employé',
        help_text='Employé concerné'
    )
    numero_fiche = models.CharField(
        max_length=50, unique=True, db_index=True,
        verbose_name='Numéro de fiche',
        help_text='Identifiant unique de la fiche'
    )

    # Période
    periode = models.DateField(
        db_index=True,
        verbose_name='Période',
        help_text='Premier jour du mois concerné'
    )
    annee = models.IntegerField(
        verbose_name='Année',
        help_text='Année de la fiche'
    )
    mois = models.IntegerField(
        verbose_name='Mois',
        help_text='Mois de la fiche (1-12)'
    )

    # Présence
    jours_travailles = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Jours travaillés',
        help_text='Nombre de jours effectivement travaillés'
    )
    heures_travaillees = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name='Heures travaillées',
        help_text='Nombre d\'heures travaillées'
    )
    heures_supplementaires = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name='Heures supplémentaires',
        help_text='Heures supplémentaires effectuées'
    )
    jours_absence = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Jours d\'absence',
        help_text='Jours d\'absence (hors vacances et maladie)'
    )
    jours_vacances = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Jours de vacances',
        help_text='Jours de vacances pris'
    )
    jours_maladie = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Jours de maladie',
        help_text='Jours d\'absence pour maladie'
    )

    # Salaire brut
    salaire_base = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Salaire de base',
        help_text='Salaire mensuel de base en CHF'
    )
    heures_supp_montant = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Montant heures supp.',
        help_text='Rémunération des heures supplémentaires en CHF'
    )
    primes = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Primes',
        help_text='Primes et bonus en CHF'
    )
    indemnites = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Indemnités',
        help_text='Indemnités diverses en CHF'
    )
    treizieme_mois = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='13ème mois',
        help_text='Part du 13ème salaire versée ce mois'
    )

    salaire_brut_total = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Salaire brut total',
        help_text='Total du salaire brut en CHF'
    )
    
    # Cotisations salariales (part employé)
    avs_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AVS/AI/APG',
        help_text='Cotisation AVS/AI/APG employé en CHF'
    )
    ac_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AC',
        help_text='Assurance chômage employé en CHF'
    )
    ac_supp_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AC supp.',
        help_text='AC supplémentaire (salaires > 148\'200) en CHF'
    )
    lpp_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='LPP',
        help_text='Cotisation 2ème pilier employé en CHF'
    )
    laa_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='LAA',
        help_text='Assurance accidents employé en CHF'
    )
    laac_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='LAAC',
        help_text='Assurance accidents complémentaire en CHF'
    )
    ijm_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='IJM',
        help_text='Indemnités journalières maladie employé en CHF'
    )

    total_cotisations_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Total cotisations employé',
        help_text='Total des cotisations salariales en CHF'
    )

    # Impôt à la source
    impot_source = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Impôt à la source',
        help_text='Retenue d\'impôt à la source en CHF'
    )

    # Autres déductions
    avance_salaire = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Avance sur salaire',
        help_text='Retenue pour avance consentie en CHF'
    )
    saisie_salaire = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Saisie sur salaire',
        help_text='Retenue pour saisie de salaire en CHF'
    )
    autres_deductions = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Autres déductions',
        help_text='Autres retenues en CHF'
    )

    total_deductions = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Total déductions',
        help_text='Total de toutes les déductions en CHF'
    )

    # Allocations
    allocations_familiales = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Allocations familiales',
        help_text='Allocations familiales en CHF'
    )
    autres_allocations = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Autres allocations',
        help_text='Autres allocations en CHF'
    )

    # Salaire net
    salaire_net = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Salaire net',
        help_text='Salaire net à payer en CHF'
    )
    
    # Charges patronales (pour info)
    avs_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AVS employeur',
        help_text='Part patronale AVS/AI/APG en CHF'
    )
    ac_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AC employeur',
        help_text='Part patronale assurance chômage en CHF'
    )
    lpp_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='LPP employeur',
        help_text='Part patronale 2ème pilier en CHF'
    )
    laa_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='LAA employeur',
        help_text='Part patronale assurance accidents en CHF'
    )
    af_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AF employeur',
        help_text='Allocations familiales (charge patronale) en CHF'
    )

    total_charges_patronales = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Total charges patronales',
        help_text='Total des charges employeur en CHF'
    )

    # Coût total employeur
    cout_total_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Coût total employeur',
        help_text='Coût complet pour l\'employeur en CHF'
    )

    # Statut
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        default='BROUILLON', db_index=True,
        verbose_name='Statut',
        help_text='État de la fiche de salaire'
    )

    date_validation = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date de validation',
        help_text='Date et heure de validation'
    )
    valide_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name='Validé par',
        help_text='Utilisateur ayant validé la fiche'
    )

    date_paiement = models.DateField(
        null=True, blank=True,
        verbose_name='Date de paiement',
        help_text='Date effective du paiement'
    )

    # Fichier PDF
    fichier_pdf = models.FileField(
        upload_to='salaires/fiches/', null=True, blank=True,
        verbose_name='Fichier PDF',
        help_text='Fiche de salaire au format PDF'
    )

    # Lien comptabilité
    ecriture_comptable = models.ForeignKey(
        'comptabilite.PieceComptable',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fiches_salaire',
        verbose_name='Pièce comptable',
        help_text='Pièce comptable associée'
    )

    # Notes
    remarques = models.TextField(
        blank=True,
        verbose_name='Remarques',
        help_text='Notes et observations'
    )
    
    class Meta:
        db_table = 'fiches_salaire'
        verbose_name = 'Fiche de salaire'
        unique_together = [['employe', 'periode']]
        ordering = ['-periode', 'employe__nom']
        indexes = [
            models.Index(fields=['employe', 'periode']),
            models.Index(fields=['periode', 'statut']),
        ]
    
    def __str__(self):
        return f"Fiche {self.employe} - {self.periode.strftime('%m/%Y')}"
    
    def save(self, *args, **kwargs):
        # Extraction année/mois
        self.annee = self.periode.year
        self.mois = self.periode.month
        
        # Génération numéro
        if not self.numero_fiche:
            self.numero_fiche = f"SAL-{self.periode.strftime('%Y%m')}-{self.employe.matricule}"
        
        super().save(*args, **kwargs)
    
    def calculer(self):
        """Calcule tous les montants de la fiche"""
        # Salaire brut total
        self.salaire_brut_total = (
            self.salaire_base 
            + self.heures_supp_montant 
            + self.primes 
            + self.indemnites
            + self.treizieme_mois
        )
        
        # Cotisations employé
        self.avs_employe = self._calculer_cotisation('AVS', 'employe')
        self.ac_employe = self._calculer_cotisation('AC', 'employe')
        self.lpp_employe = self._calculer_cotisation('LPP', 'employe')
        # ... autres cotisations
        
        self.total_cotisations_employe = (
            self.avs_employe 
            + self.ac_employe 
            + self.ac_supp_employe
            + self.lpp_employe 
            + self.laa_employe 
            + self.laac_employe
            + self.ijm_employe
        )
        
        # Déductions totales
        self.total_deductions = (
            self.total_cotisations_employe
            + self.impot_source
            + self.avance_salaire
            + self.saisie_salaire
            + self.autres_deductions
        )
        
        # Salaire net
        self.salaire_net = (
            self.salaire_brut_total
            - self.total_deductions
            + self.allocations_familiales
            + self.autres_allocations
        )
        
        # Charges patronales
        self.avs_employeur = self._calculer_cotisation('AVS', 'employeur')
        self.ac_employeur = self._calculer_cotisation('AC', 'employeur')
        # ... autres charges
        
        self.total_charges_patronales = (
            self.avs_employeur
            + self.ac_employeur
            + self.lpp_employeur
            + self.laa_employeur
            + self.af_employeur
        )
        
        # Coût total
        self.cout_total_employeur = (
            self.salaire_brut_total
            + self.total_charges_patronales
        )
        
        self.save()
        return self.salaire_net
    
    def _calculer_cotisation(self, type_cot, part):
        """Calcule une cotisation spécifique"""
        taux_obj = TauxCotisation.get_taux_actif(type_cot, self.periode)
        if not taux_obj:
            return Decimal('0.00')
        
        base = self.salaire_brut_total
        
        # Appliquer plafonds si nécessaire
        if taux_obj.salaire_max and base > taux_obj.salaire_max:
            base = taux_obj.salaire_max
        if taux_obj.salaire_min and base < taux_obj.salaire_min:
            return Decimal('0.00')
        
        taux = taux_obj.taux_employe if part == 'employe' else taux_obj.taux_employeur
        return (base * taux / 100).quantize(Decimal('0.01'))

    def generer_pdf(self):
        """
        Génère le PDF de la fiche de salaire.

        Returns:
            FileField: Le fichier PDF généré et sauvegardé
        """
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as pdf_canvas
        from django.core.files.base import ContentFile

        buffer = io.BytesIO()
        width, height = A4

        # Marges
        margin_left = 1.5 * cm
        margin_right = 1.5 * cm
        margin_top = 1.5 * cm

        # Créer le canvas
        p = pdf_canvas.Canvas(buffer, pagesize=A4)

        # ==================== EN-TÊTE ====================
        y = height - margin_top

        # Logo / Entreprise (à gauche)
        p.setFont("Helvetica-Bold", 12)
        client = self.employe.mandat.client
        p.drawString(margin_left, y, client.raison_sociale)

        adresse = client.adresse_siege
        p.setFont("Helvetica", 9)
        y -= 0.4 * cm
        if adresse:
            p.drawString(margin_left, y, f"{adresse.rue} {adresse.numero}")
            y -= 0.35 * cm
            p.drawString(margin_left, y, f"{adresse.code_postal} {adresse.localite}")
            y -= 0.35 * cm

        # Titre FICHE DE SALAIRE (centré)
        y_title = height - margin_top - 0.5 * cm
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width / 2, y_title, "FICHE DE SALAIRE")

        # Période (à droite)
        y_right = height - margin_top
        p.setFont("Helvetica-Bold", 10)
        mois_noms = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                     'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        periode_str = f"{mois_noms[self.mois]} {self.annee}"
        p.drawRightString(width - margin_right, y_right, periode_str)

        p.setFont("Helvetica", 9)
        y_right -= 0.4 * cm
        p.drawRightString(width - margin_right, y_right, f"N° {self.numero_fiche}")

        # Ligne séparatrice
        y = height - 3.5 * cm
        p.setStrokeColor(colors.grey)
        p.line(margin_left, y, width - margin_right, y)

        # ==================== INFORMATIONS EMPLOYÉ ====================
        y -= 0.8 * cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin_left, y, "EMPLOYÉ")

        p.setFont("Helvetica", 9)
        y -= 0.5 * cm
        col1 = margin_left
        col2 = 6 * cm
        col3 = 11 * cm
        col4 = 15 * cm

        # Ligne 1
        p.drawString(col1, y, "Nom:")
        p.setFont("Helvetica-Bold", 9)
        p.drawString(col2, y, f"{self.employe.prenom} {self.employe.nom}")
        p.setFont("Helvetica", 9)
        p.drawString(col3, y, "Matricule:")
        p.drawString(col4, y, self.employe.matricule)

        y -= 0.4 * cm
        p.drawString(col1, y, "N° AVS:")
        p.drawString(col2, y, self.employe.avs_number or '-')
        p.drawString(col3, y, "Fonction:")
        p.drawString(col4, y, self.employe.fonction[:20] if self.employe.fonction else '-')

        y -= 0.4 * cm
        p.drawString(col1, y, "Date entrée:")
        p.drawString(col2, y, self.employe.date_entree.strftime('%d.%m.%Y'))
        p.drawString(col3, y, "Taux:")
        p.drawString(col4, y, f"{self.employe.taux_occupation}%")

        # Ligne séparatrice
        y -= 0.6 * cm
        p.setStrokeColor(colors.grey)
        p.line(margin_left, y, width - margin_right, y)

        # ==================== PRÉSENCE ====================
        y -= 0.6 * cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin_left, y, "PRÉSENCE")

        p.setFont("Helvetica", 9)
        y -= 0.5 * cm
        p.drawString(col1, y, "Jours travaillés:")
        p.drawRightString(col2 - 0.5*cm, y, f"{self.jours_travailles:.1f}")
        p.drawString(col3, y, "Heures supp.:")
        p.drawRightString(col4, y, f"{self.heures_supplementaires:.2f}")

        y -= 0.4 * cm
        p.drawString(col1, y, "Jours absence:")
        p.drawRightString(col2 - 0.5*cm, y, f"{self.jours_absence:.1f}")
        p.drawString(col3, y, "Jours vacances:")
        p.drawRightString(col4, y, f"{self.jours_vacances:.1f}")

        y -= 0.4 * cm
        p.drawString(col1, y, "Jours maladie:")
        p.drawRightString(col2 - 0.5*cm, y, f"{self.jours_maladie:.1f}")

        # Ligne séparatrice
        y -= 0.6 * cm
        p.setStrokeColor(colors.grey)
        p.line(margin_left, y, width - margin_right, y)

        # ==================== SALAIRE BRUT ====================
        y -= 0.6 * cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin_left, y, "SALAIRE BRUT")
        p.drawRightString(width - margin_right, y, "CHF")

        p.setFont("Helvetica", 9)
        y -= 0.5 * cm

        # Détails salaire brut
        lignes_brut = [
            ("Salaire de base", self.salaire_base),
            ("Heures supplémentaires", self.heures_supp_montant),
            ("Primes", self.primes),
            ("Indemnités", self.indemnites),
            ("13ème salaire", self.treizieme_mois),
        ]

        for libelle, montant in lignes_brut:
            if montant and montant > 0:
                p.drawString(margin_left + 0.5*cm, y, libelle)
                p.drawRightString(width - margin_right, y, f"{montant:,.2f}".replace(',', "'"))
                y -= 0.4 * cm

        # Total brut
        y -= 0.2 * cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin_left, y, "TOTAL BRUT")
        p.drawRightString(width - margin_right, y, f"{self.salaire_brut_total:,.2f}".replace(',', "'"))

        # Ligne séparatrice
        y -= 0.6 * cm
        p.setStrokeColor(colors.grey)
        p.line(margin_left, y, width - margin_right, y)

        # ==================== COTISATIONS SALARIALES ====================
        y -= 0.6 * cm
        p.setFont("Helvetica-Bold", 10)
        p.setFillColor(colors.red)
        p.drawString(margin_left, y, "COTISATIONS (part employé)")
        p.setFillColor(colors.black)

        p.setFont("Helvetica", 9)
        y -= 0.5 * cm

        cotisations = [
            ("AVS/AI/APG", self.avs_employe),
            ("AC (Assurance chômage)", self.ac_employe),
            ("AC supplémentaire", self.ac_supp_employe),
            ("LPP (2ème pilier)", self.lpp_employe),
            ("LAA (Accident)", self.laa_employe),
            ("LAAC (Complémentaire)", self.laac_employe),
            ("IJM (Indemnités journalières)", self.ijm_employe),
        ]

        for libelle, montant in cotisations:
            if montant and montant > 0:
                p.drawString(margin_left + 0.5*cm, y, libelle)
                p.setFillColor(colors.red)
                p.drawRightString(width - margin_right, y, f"-{montant:,.2f}".replace(',', "'"))
                p.setFillColor(colors.black)
                y -= 0.4 * cm

        # Total cotisations
        y -= 0.2 * cm
        p.setFont("Helvetica-Bold", 9)
        p.drawString(margin_left + 0.5*cm, y, "Total cotisations")
        p.setFillColor(colors.red)
        p.drawRightString(width - margin_right, y, f"-{self.total_cotisations_employe:,.2f}".replace(',', "'"))
        p.setFillColor(colors.black)

        # ==================== AUTRES DÉDUCTIONS ====================
        y -= 0.6 * cm

        autres_deductions = [
            ("Impôt à la source", self.impot_source),
            ("Avance sur salaire", self.avance_salaire),
            ("Saisie sur salaire", self.saisie_salaire),
            ("Autres déductions", self.autres_deductions),
        ]

        has_other_deductions = any(d[1] and d[1] > 0 for d in autres_deductions)

        if has_other_deductions:
            p.setFont("Helvetica-Bold", 10)
            p.setFillColor(colors.red)
            p.drawString(margin_left, y, "AUTRES DÉDUCTIONS")
            p.setFillColor(colors.black)

            p.setFont("Helvetica", 9)
            y -= 0.5 * cm

            for libelle, montant in autres_deductions:
                if montant and montant > 0:
                    p.drawString(margin_left + 0.5*cm, y, libelle)
                    p.setFillColor(colors.red)
                    p.drawRightString(width - margin_right, y, f"-{montant:,.2f}".replace(',', "'"))
                    p.setFillColor(colors.black)
                    y -= 0.4 * cm

        # ==================== ALLOCATIONS ====================
        has_allocations = (self.allocations_familiales and self.allocations_familiales > 0) or \
                          (self.autres_allocations and self.autres_allocations > 0)

        if has_allocations:
            y -= 0.4 * cm
            p.setFont("Helvetica-Bold", 10)
            p.setFillColor(colors.darkgreen)
            p.drawString(margin_left, y, "ALLOCATIONS")
            p.setFillColor(colors.black)

            p.setFont("Helvetica", 9)
            y -= 0.5 * cm

            if self.allocations_familiales and self.allocations_familiales > 0:
                p.drawString(margin_left + 0.5*cm, y, "Allocations familiales")
                p.setFillColor(colors.darkgreen)
                p.drawRightString(width - margin_right, y, f"+{self.allocations_familiales:,.2f}".replace(',', "'"))
                p.setFillColor(colors.black)
                y -= 0.4 * cm

            if self.autres_allocations and self.autres_allocations > 0:
                p.drawString(margin_left + 0.5*cm, y, "Autres allocations")
                p.setFillColor(colors.darkgreen)
                p.drawRightString(width - margin_right, y, f"+{self.autres_allocations:,.2f}".replace(',', "'"))
                p.setFillColor(colors.black)
                y -= 0.4 * cm

        # ==================== SALAIRE NET ====================
        y -= 0.6 * cm
        p.setStrokeColor(colors.black)
        p.setLineWidth(2)
        p.line(margin_left, y + 0.3*cm, width - margin_right, y + 0.3*cm)

        p.setFont("Helvetica-Bold", 12)
        p.drawString(margin_left, y, "SALAIRE NET À PAYER")
        p.setFillColor(colors.darkgreen)
        p.drawRightString(width - margin_right, y, f"CHF {self.salaire_net:,.2f}".replace(',', "'"))
        p.setFillColor(colors.black)

        p.setLineWidth(2)
        p.line(margin_left, y - 0.3*cm, width - margin_right, y - 0.3*cm)

        # ==================== INFORMATIONS BANCAIRES ====================
        y -= 1.2 * cm
        p.setFont("Helvetica", 8)
        p.drawString(margin_left, y, f"Versement sur: {self.employe.iban or 'IBAN non renseigné'}")
        if self.employe.banque:
            y -= 0.35 * cm
            p.drawString(margin_left, y, f"Banque: {self.employe.banque}")

        # ==================== CHARGES PATRONALES (info) ====================
        y -= 1 * cm
        p.setFont("Helvetica-Bold", 8)
        p.setFillColor(colors.grey)
        p.drawString(margin_left, y, "Charges patronales (pour information)")

        p.setFont("Helvetica", 7)
        y -= 0.4 * cm
        charges_info = f"AVS: {self.avs_employeur:,.2f} | AC: {self.ac_employeur:,.2f} | LPP: {self.lpp_employeur:,.2f} | LAA: {self.laa_employeur:,.2f} | AF: {self.af_employeur:,.2f}".replace(',', "'")
        p.drawString(margin_left, y, charges_info)
        y -= 0.35 * cm
        p.drawString(margin_left, y, f"Total charges patronales: CHF {self.total_charges_patronales:,.2f} | Coût total employeur: CHF {self.cout_total_employeur:,.2f}".replace(',', "'"))
        p.setFillColor(colors.black)

        # ==================== PIED DE PAGE ====================
        p.setFont("Helvetica", 7)
        p.setFillColor(colors.grey)
        p.drawCentredString(width / 2, 1.5 * cm, f"Document généré le {self.created_at.strftime('%d.%m.%Y') if self.created_at else '-'} - {client.raison_sociale}")
        p.drawCentredString(width / 2, 1.1 * cm, "Ce document est confidentiel et destiné uniquement à l'employé concerné.")

        # Finaliser le PDF
        p.showPage()
        p.save()

        # Sauvegarder le fichier
        buffer.seek(0)
        filename = f"fiche_salaire_{self.numero_fiche}_{self.periode.strftime('%Y%m')}.pdf"

        self.fichier_pdf.save(filename, ContentFile(buffer.read()), save=True)

        return self.fichier_pdf


class CertificatSalaire(BaseModel):
    """Certificat de salaire annuel"""
    
    employe = models.ForeignKey(
        Employe, on_delete=models.CASCADE,
        related_name='certificats_salaire',
        verbose_name='Employé',
        help_text='Employé concerné'
    )
    annee = models.IntegerField(
        db_index=True,
        verbose_name='Année',
        help_text='Année fiscale du certificat'
    )

    # Périodes
    date_debut = models.DateField(
        verbose_name='Date de début',
        help_text='Début de la période d\'emploi pour cette année'
    )
    date_fin = models.DateField(
        verbose_name='Date de fin',
        help_text='Fin de la période d\'emploi pour cette année'
    )

    # Salaires bruts
    salaire_brut_annuel = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Salaire brut annuel',
        help_text='Total des salaires bruts en CHF'
    )
    treizieme_salaire_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='13ème salaire annuel',
        help_text='13ème salaire versé en CHF'
    )
    primes_annuelles = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Primes annuelles',
        help_text='Total des primes et gratifications en CHF'
    )

    # Cotisations annuelles
    avs_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AVS annuel',
        help_text='Total cotisations AVS/AI/APG employé en CHF'
    )
    ac_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AC annuel',
        help_text='Total assurance chômage employé en CHF'
    )
    lpp_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='LPP annuel',
        help_text='Total cotisations 2ème pilier employé en CHF'
    )

    # Allocations
    allocations_familiales_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Allocations familiales annuelles',
        help_text='Total allocations familiales reçues en CHF'
    )

    # Frais
    frais_deplacement = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Frais de déplacement',
        help_text='Indemnités de déplacement en CHF'
    )
    frais_repas = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Frais de repas',
        help_text='Indemnités de repas en CHF'
    )

    # Impôt source
    impot_source_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Impôt à la source annuel',
        help_text='Total impôt à la source retenu en CHF'
    )

    # Fichier
    fichier_pdf = models.FileField(
        upload_to='salaires/certificats/', null=True, blank=True,
        verbose_name='Fichier PDF',
        help_text='Certificat de salaire au format PDF'
    )

    date_generation = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de génération',
        help_text='Date de création du certificat'
    )
    genere_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        verbose_name='Généré par',
        help_text='Utilisateur ayant généré le certificat'
    )
    
    class Meta:
        db_table = 'certificats_salaire'
        verbose_name = 'Certificat de salaire'
        unique_together = [['employe', 'annee']]
        ordering = ['-annee']
    
    def __str__(self):
        return f"Certificat {self.annee} - {self.employe}"

    def generer_pdf(self):
        """
        Génère le PDF du certificat de salaire annuel (format suisse officiel).

        Returns:
            FileField: Le fichier PDF généré et sauvegardé
        """
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as pdf_canvas
        from django.core.files.base import ContentFile

        buffer = io.BytesIO()
        width, height = A4

        # Marges
        margin_left = 1.5 * cm
        margin_right = 1.5 * cm
        margin_top = 1.5 * cm

        # Créer le canvas
        p = pdf_canvas.Canvas(buffer, pagesize=A4)

        # ==================== EN-TÊTE ====================
        y = height - margin_top

        # Logo / Entreprise (à gauche)
        p.setFont("Helvetica-Bold", 12)
        client = self.employe.mandat.client
        p.drawString(margin_left, y, client.raison_sociale)

        adresse_client = client.adresse_siege
        p.setFont("Helvetica", 9)
        y -= 0.4 * cm
        if adresse_client:
            p.drawString(margin_left, y, f"{adresse_client.rue} {adresse_client.numero}")
            y -= 0.35 * cm
            p.drawString(margin_left, y, f"{adresse_client.code_postal} {adresse_client.localite}")
            y -= 0.35 * cm

        # IDE de l'employeur
        if client.ide_number:
            p.drawString(margin_left, y, f"IDE: {client.ide_number}")
            y -= 0.35 * cm

        # Titre CERTIFICAT DE SALAIRE (centré)
        y_title = height - margin_top - 0.5 * cm
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width / 2, y_title, "CERTIFICAT DE SALAIRE")

        # Sous-titre année
        p.setFont("Helvetica-Bold", 12)
        p.drawCentredString(width / 2, y_title - 0.6 * cm, f"Année {self.annee}")

        # Ligne séparatrice
        y = height - 4 * cm
        p.setStrokeColor(colors.grey)
        p.line(margin_left, y, width - margin_right, y)

        # ==================== INFORMATIONS EMPLOYÉ ====================
        y -= 0.8 * cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin_left, y, "EMPLOYÉ")

        p.setFont("Helvetica", 9)
        y -= 0.5 * cm
        col1 = margin_left
        col2 = 6 * cm
        col3 = 11 * cm
        col4 = 15 * cm

        # Ligne 1 - Nom
        p.drawString(col1, y, "Nom, Prénom:")
        p.setFont("Helvetica-Bold", 9)
        p.drawString(col2, y, f"{self.employe.nom} {self.employe.prenom}")
        p.setFont("Helvetica", 9)

        # Date de naissance
        p.drawString(col3, y, "Date de naissance:")
        date_naissance = self.employe.date_naissance.strftime('%d.%m.%Y') if self.employe.date_naissance else '-'
        p.drawString(col4, y, date_naissance)

        y -= 0.4 * cm
        # Adresse employé
        adresse_emp = self.employe.adresse
        if adresse_emp:
            p.drawString(col1, y, "Adresse:")
            p.drawString(col2, y, f"{adresse_emp.rue} {adresse_emp.numero}")
            y -= 0.35 * cm
            p.drawString(col2, y, f"{adresse_emp.code_postal} {adresse_emp.localite}")

        y -= 0.4 * cm
        # N° AVS
        p.drawString(col1, y, "N° AVS:")
        p.setFont("Helvetica-Bold", 9)
        p.drawString(col2, y, self.employe.avs_number or '-')
        p.setFont("Helvetica", 9)

        # Nationalité
        p.drawString(col3, y, "Nationalité:")
        nationalite = str(self.employe.nationalite.name) if self.employe.nationalite else 'Suisse'
        p.drawString(col4, y, nationalite)

        y -= 0.4 * cm
        # Période d'emploi
        p.drawString(col1, y, "Période d'emploi:")
        p.drawString(col2, y, f"Du {self.date_debut.strftime('%d.%m.%Y')} au {self.date_fin.strftime('%d.%m.%Y')}")

        # Taux d'occupation
        p.drawString(col3, y, "Taux d'occupation:")
        p.drawString(col4, y, f"{self.employe.taux_occupation}%")

        # Ligne séparatrice
        y -= 0.8 * cm
        p.setStrokeColor(colors.grey)
        p.line(margin_left, y, width - margin_right, y)

        # ==================== REVENUS ====================
        y -= 0.8 * cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin_left, y, "REVENUS")
        p.drawRightString(width - margin_right, y, "CHF")

        p.setFont("Helvetica", 9)
        y -= 0.5 * cm

        # Fonction helper pour formater les montants
        def format_montant(val):
            if val is None:
                return "0.00"
            return f"{val:,.2f}".replace(',', "'")

        # Détails revenus
        revenus = [
            ("1. Salaire brut (y.c. salaire horaire)", self.salaire_brut_annuel),
            ("2. 13ème salaire", self.treizieme_salaire_annuel),
            ("3. Primes et gratifications", self.primes_annuelles),
            ("4. Allocations familiales", self.allocations_familiales_annuel),
        ]

        for num, (libelle, montant) in enumerate(revenus):
            if montant and montant > 0:
                p.drawString(margin_left + 0.3*cm, y, libelle)
                p.drawRightString(width - margin_right, y, format_montant(montant))
                y -= 0.4 * cm

        # Total revenus bruts
        total_revenus = (
            (self.salaire_brut_annuel or 0) +
            (self.treizieme_salaire_annuel or 0) +
            (self.primes_annuelles or 0) +
            (self.allocations_familiales_annuel or 0)
        )

        y -= 0.2 * cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin_left, y, "TOTAL REVENUS BRUTS")
        p.drawRightString(width - margin_right, y, format_montant(total_revenus))

        # Ligne séparatrice
        y -= 0.6 * cm
        p.setStrokeColor(colors.grey)
        p.line(margin_left, y, width - margin_right, y)

        # ==================== DÉDUCTIONS ====================
        y -= 0.6 * cm
        p.setFont("Helvetica-Bold", 10)
        p.setFillColor(colors.red)
        p.drawString(margin_left, y, "COTISATIONS SOCIALES (part employé)")
        p.setFillColor(colors.black)

        p.setFont("Helvetica", 9)
        y -= 0.5 * cm

        cotisations = [
            ("5. AVS/AI/APG", self.avs_annuel),
            ("6. Assurance chômage (AC)", self.ac_annuel),
            ("7. LPP (2ème pilier)", self.lpp_annuel),
        ]

        for libelle, montant in cotisations:
            if montant and montant > 0:
                p.drawString(margin_left + 0.3*cm, y, libelle)
                p.setFillColor(colors.red)
                p.drawRightString(width - margin_right, y, f"-{format_montant(montant)}")
                p.setFillColor(colors.black)
                y -= 0.4 * cm

        # Total cotisations
        total_cotisations = (self.avs_annuel or 0) + (self.ac_annuel or 0) + (self.lpp_annuel or 0)

        y -= 0.2 * cm
        p.setFont("Helvetica-Bold", 9)
        p.drawString(margin_left + 0.3*cm, y, "Total cotisations sociales")
        p.setFillColor(colors.red)
        p.drawRightString(width - margin_right, y, f"-{format_montant(total_cotisations)}")
        p.setFillColor(colors.black)

        # ==================== IMPÔT À LA SOURCE ====================
        if self.impot_source_annuel and self.impot_source_annuel > 0:
            y -= 0.6 * cm
            p.setFont("Helvetica-Bold", 10)
            p.setFillColor(colors.red)
            p.drawString(margin_left, y, "IMPÔT À LA SOURCE")
            p.setFillColor(colors.black)

            p.setFont("Helvetica", 9)
            y -= 0.5 * cm
            p.drawString(margin_left + 0.3*cm, y, "8. Retenue impôt à la source")
            p.setFillColor(colors.red)
            p.drawRightString(width - margin_right, y, f"-{format_montant(self.impot_source_annuel)}")
            p.setFillColor(colors.black)

        # ==================== FRAIS PROFESSIONNELS ====================
        if (self.frais_deplacement and self.frais_deplacement > 0) or (self.frais_repas and self.frais_repas > 0):
            y -= 0.6 * cm
            p.setFont("Helvetica-Bold", 10)
            p.drawString(margin_left, y, "FRAIS PROFESSIONNELS")

            p.setFont("Helvetica", 9)
            y -= 0.5 * cm

            if self.frais_deplacement and self.frais_deplacement > 0:
                p.drawString(margin_left + 0.3*cm, y, "9. Frais de déplacement")
                p.drawRightString(width - margin_right, y, format_montant(self.frais_deplacement))
                y -= 0.4 * cm

            if self.frais_repas and self.frais_repas > 0:
                p.drawString(margin_left + 0.3*cm, y, "10. Frais de repas")
                p.drawRightString(width - margin_right, y, format_montant(self.frais_repas))
                y -= 0.4 * cm

        # ==================== SALAIRE NET ====================
        y -= 0.6 * cm
        p.setStrokeColor(colors.black)
        p.setLineWidth(2)
        p.line(margin_left, y + 0.3*cm, width - margin_right, y + 0.3*cm)

        salaire_net = total_revenus - total_cotisations - (self.impot_source_annuel or 0)

        p.setFont("Helvetica-Bold", 12)
        p.drawString(margin_left, y, "SALAIRE NET ANNUEL")
        p.setFillColor(colors.darkgreen)
        p.drawRightString(width - margin_right, y, f"CHF {format_montant(salaire_net)}")
        p.setFillColor(colors.black)

        p.setLineWidth(2)
        p.line(margin_left, y - 0.3*cm, width - margin_right, y - 0.3*cm)

        # ==================== REMARQUES ====================
        y -= 1.5 * cm
        p.setFont("Helvetica-Bold", 9)
        p.drawString(margin_left, y, "Remarques:")
        p.setFont("Helvetica", 8)
        y -= 0.4 * cm
        p.drawString(margin_left, y, "Ce certificat est établi conformément aux directives de l'Administration fédérale des contributions.")
        y -= 0.35 * cm
        p.drawString(margin_left, y, "Les montants indiqués correspondent aux données effectives de l'année fiscale concernée.")

        # ==================== SIGNATURES ====================
        y -= 1.5 * cm
        p.setFont("Helvetica", 9)

        # Date et lieu
        from datetime import date
        p.drawString(margin_left, y, f"{adresse_client.localite if adresse_client else ''}, le {date.today().strftime('%d.%m.%Y')}")

        y -= 1.5 * cm
        # Signature employeur
        p.drawString(margin_left, y, "_" * 35)
        y -= 0.4 * cm
        p.drawString(margin_left, y, "Signature de l'employeur")

        # Signature employé (à droite)
        p.drawString(width - margin_right - 6*cm, y + 0.4*cm, "_" * 35)
        p.drawString(width - margin_right - 6*cm, y, "Signature de l'employé")

        # ==================== PIED DE PAGE ====================
        p.setFont("Helvetica", 7)
        p.setFillColor(colors.grey)
        p.drawCentredString(width / 2, 2 * cm, f"Document généré le {self.date_generation.strftime('%d.%m.%Y') if self.date_generation else date.today().strftime('%d.%m.%Y')}")
        p.drawCentredString(width / 2, 1.6 * cm, f"par {client.raison_sociale}")
        p.drawCentredString(width / 2, 1.2 * cm, "Ce document est confidentiel et destiné uniquement aux autorités fiscales et à l'employé concerné.")

        # Finaliser le PDF
        p.showPage()
        p.save()

        # Sauvegarder le fichier
        buffer.seek(0)
        filename = f"certificat_salaire_{self.employe.matricule}_{self.annee}.pdf"

        self.fichier_pdf.save(filename, ContentFile(buffer.read()), save=True)

        return self.fichier_pdf


class DeclarationCotisations(BaseModel):
    """Déclaration des cotisations sociales (AVS, etc.)"""
    
    ORGANISME_CHOICES = [
        ('AVS', 'Caisse AVS'),
        ('LPP', 'Institution LPP'),
        ('LAA', 'Assurance LAA'),
        ('AF', 'Caisse allocations familiales'),
    ]
    
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        verbose_name='Mandat',
        help_text='Mandat employeur concerné'
    )
    organisme = models.CharField(
        max_length=10, choices=ORGANISME_CHOICES,
        verbose_name='Organisme',
        help_text='Organisme destinataire de la déclaration'
    )

    periode_debut = models.DateField(
        verbose_name='Début de période',
        help_text='Premier jour de la période déclarée'
    )
    periode_fin = models.DateField(
        verbose_name='Fin de période',
        help_text='Dernier jour de la période déclarée'
    )

    masse_salariale = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Masse salariale',
        help_text='Total des salaires soumis en CHF'
    )
    montant_cotisations = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Montant cotisations',
        help_text='Total des cotisations dues en CHF'
    )

    date_declaration = models.DateField(
        auto_now_add=True,
        verbose_name='Date de déclaration',
        help_text='Date de création de la déclaration'
    )
    date_echeance = models.DateField(
        verbose_name='Date d\'échéance',
        help_text='Date limite de paiement'
    )
    date_paiement = models.DateField(
        null=True, blank=True,
        verbose_name='Date de paiement',
        help_text='Date effective du paiement'
    )

    numero_reference = models.CharField(
        max_length=50, blank=True,
        verbose_name='Numéro de référence',
        help_text='Référence attribuée par l\'organisme'
    )

    fichier_declaration = models.FileField(
        upload_to='salaires/declarations/',
        null=True, blank=True,
        verbose_name='Fichier déclaration',
        help_text='Document de déclaration'
    )
    
    class Meta:
        db_table = 'declarations_cotisations'
        verbose_name = 'Déclaration de cotisations'


class CertificatTravail(BaseModel):
    """
    Certificat de travail (Arbeitszeugnis / Certificat d'employeur)

    Document légalement obligatoire en Suisse (art. 330a CO).
    L'employeur doit le délivrer à la demande de l'employé.
    """

    TYPE_CERTIFICAT_CHOICES = [
        ('COMPLET', 'Certificat complet (qualifié)'),
        ('SIMPLE', 'Attestation de travail (simple)'),
        ('INTERMEDIAIRE', 'Certificat intermédiaire'),
    ]

    MOTIF_DEPART_CHOICES = [
        ('DEMISSION', 'Démission'),
        ('FIN_CONTRAT', 'Fin de contrat'),
        ('LICENCIEMENT', 'Licenciement'),
        ('LICENCIEMENT_ECO', 'Licenciement économique'),
        ('RETRAITE', 'Retraite'),
        ('ACCORD_MUTUEL', 'Résiliation d\'un commun accord'),
        ('DECES', 'Décès'),
        ('', 'Non spécifié'),
    ]

    # Relations
    employe = models.ForeignKey(
        Employe,
        on_delete=models.CASCADE,
        related_name='certificats_travail'
    )

    # Type et période
    type_certificat = models.CharField(
        'Type de certificat',
        max_length=20,
        choices=TYPE_CERTIFICAT_CHOICES,
        default='COMPLET'
    )
    date_debut_emploi = models.DateField('Date de début d\'emploi')
    date_fin_emploi = models.DateField('Date de fin d\'emploi', null=True, blank=True)

    # Informations professionnelles
    fonction_principale = models.CharField('Fonction principale', max_length=150)
    departement = models.CharField('Département', max_length=100, blank=True)
    taux_occupation = models.DecimalField(
        'Taux d\'occupation (%)',
        max_digits=5,
        decimal_places=2,
        default=100
    )

    # Description du poste et des tâches (pour certificat complet)
    description_taches = models.TextField(
        'Description des tâches',
        blank=True,
        help_text='Description détaillée des principales responsabilités et tâches'
    )

    # Évaluations (pour certificat complet - échelle standard suisse)
    # Échelle: 1=insuffisant, 2=satisfaisant, 3=bien, 4=très bien, 5=excellent
    NOTE_CHOICES = [
        (1, 'Insuffisant'),
        (2, 'Satisfaisant'),
        (3, 'Bien'),
        (4, 'Très bien'),
        (5, 'Excellent'),
    ]

    evaluation_qualite_travail = models.IntegerField(
        'Qualité du travail',
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_quantite_travail = models.IntegerField(
        'Quantité de travail',
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_competences = models.IntegerField(
        'Compétences professionnelles',
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_comportement = models.IntegerField(
        'Comportement',
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_relations = models.IntegerField(
        'Relations avec collègues/clients',
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_autonomie = models.IntegerField(
        'Autonomie et initiative',
        choices=NOTE_CHOICES,
        null=True, blank=True
    )

    # Texte de l'évaluation (généré ou personnalisé)
    texte_evaluation = models.TextField(
        'Texte d\'évaluation',
        blank=True,
        help_text='Évaluation rédigée des performances et du comportement'
    )

    # Motif de départ
    motif_depart = models.CharField(
        'Motif de départ',
        max_length=20,
        choices=MOTIF_DEPART_CHOICES,
        blank=True
    )

    # Formule de fin (vœux pour l'avenir)
    formule_fin = models.TextField(
        'Formule de fin',
        blank=True,
        help_text='Remerciements et vœux pour l\'avenir'
    )

    # Informations complémentaires
    formations_suivies = models.TextField(
        'Formations suivies',
        blank=True,
        help_text='Formations internes ou externes suivies durant l\'emploi'
    )
    projets_speciaux = models.TextField(
        'Projets spéciaux',
        blank=True,
        help_text='Projets particuliers ou missions spéciales'
    )

    # Métadonnées
    date_demande = models.DateField('Date de demande', null=True, blank=True)
    date_emission = models.DateField('Date d\'émission', auto_now_add=True)
    emis_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='certificats_travail_emis'
    )

    # Fichier
    fichier_pdf = models.FileField(
        upload_to='salaires/certificats_travail/',
        null=True, blank=True
    )

    class Meta:
        db_table = 'certificats_travail'
        verbose_name = 'Certificat de travail'
        verbose_name_plural = 'Certificats de travail'
        ordering = ['-date_emission']

    def __str__(self):
        return f"Certificat travail - {self.employe} ({self.type_certificat})"

    def get_evaluation_moyenne(self):
        """Calcule la note moyenne des évaluations"""
        notes = [
            self.evaluation_qualite_travail,
            self.evaluation_quantite_travail,
            self.evaluation_competences,
            self.evaluation_comportement,
            self.evaluation_relations,
            self.evaluation_autonomie,
        ]
        notes_valides = [n for n in notes if n is not None]
        if notes_valides:
            return sum(notes_valides) / len(notes_valides)
        return None

    def generer_texte_evaluation(self):
        """
        Génère automatiquement le texte d'évaluation selon les notes.
        Utilise des formules standards suisses.
        """
        moyenne = self.get_evaluation_moyenne()
        if moyenne is None:
            return ""

        nom_complet = f"{self.employe.civilite()} {self.employe.prenom} {self.employe.nom}"
        pronom = "il" if self.employe.sexe == 'M' else "elle"
        accord = "" if self.employe.sexe == 'M' else "e"

        # Formules standards selon la note moyenne
        if moyenne >= 4.5:
            qualite = f"{nom_complet} a toujours exécuté ses tâches à notre entière satisfaction et a fait preuve d'un engagement exceptionnel."
            comportement = f"Son comportement envers ses supérieurs, collègues et clients a toujours été irréprochable."
        elif moyenne >= 3.5:
            qualite = f"{nom_complet} a exécuté ses tâches à notre entière satisfaction."
            comportement = f"Son comportement envers ses supérieurs, collègues et clients a été très bon."
        elif moyenne >= 2.5:
            qualite = f"{nom_complet} a exécuté ses tâches à notre satisfaction."
            comportement = f"Son comportement envers ses supérieurs et collègues a été correct."
        else:
            qualite = f"{nom_complet} s'est efforcé{accord} d'exécuter ses tâches."
            comportement = f"Son comportement a été acceptable."

        return f"{qualite} {comportement}"

    def generer_formule_fin_standard(self):
        """Génère une formule de fin standard selon le motif de départ"""
        nom = f"{self.employe.prenom} {self.employe.nom}"
        pronom = "le" if self.employe.sexe == 'M' else "la"

        if self.motif_depart == 'DEMISSION':
            return f"Nous regrettons {pronom} départ de {nom} et {pronom} remercions pour son travail. Nous lui souhaitons plein succès dans sa future carrière."
        elif self.motif_depart == 'RETRAITE':
            return f"Nous remercions {nom} pour ses années de collaboration et lui souhaitons une heureuse retraite."
        elif self.motif_depart == 'LICENCIEMENT_ECO':
            return f"La fin de notre collaboration est due à des raisons économiques indépendantes de la qualité du travail de {nom}. Nous {pronom} remercions et lui souhaitons plein succès."
        elif self.motif_depart == 'FIN_CONTRAT':
            return f"Nous remercions {nom} pour sa collaboration et lui souhaitons plein succès pour la suite de sa carrière."
        else:
            return f"Nous remercions {nom} pour sa collaboration et lui souhaitons le meilleur pour l'avenir."

    def generer_pdf(self):
        """
        Génère le PDF du certificat de travail.

        Returns:
            FileField: Le fichier PDF généré et sauvegardé
        """
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph
        from django.core.files.base import ContentFile
        from datetime import date

        buffer = io.BytesIO()
        width, height = A4

        # Marges
        margin_left = 2.5 * cm
        margin_right = 2.5 * cm
        margin_top = 2 * cm
        usable_width = width - margin_left - margin_right

        # Créer le canvas
        p = pdf_canvas.Canvas(buffer, pagesize=A4)

        # Récupérer les infos
        client = self.employe.mandat.client
        adresse_client = client.adresse_siege
        employe = self.employe

        # ==================== EN-TÊTE EMPLOYEUR ====================
        y = height - margin_top

        p.setFont("Helvetica-Bold", 12)
        p.drawString(margin_left, y, client.raison_sociale)

        p.setFont("Helvetica", 10)
        y -= 0.5 * cm
        if adresse_client:
            p.drawString(margin_left, y, f"{adresse_client.rue} {adresse_client.numero}")
            y -= 0.4 * cm
            p.drawString(margin_left, y, f"{adresse_client.code_postal} {adresse_client.localite}")
            y -= 0.4 * cm

        if client.ide_number:
            p.drawString(margin_left, y, f"IDE: {client.ide_number}")
            y -= 0.4 * cm

        # ==================== TITRE ====================
        y -= 1.5 * cm
        p.setFont("Helvetica-Bold", 16)

        if self.type_certificat == 'SIMPLE':
            titre = "ATTESTATION DE TRAVAIL"
        elif self.type_certificat == 'INTERMEDIAIRE':
            titre = "CERTIFICAT DE TRAVAIL INTERMÉDIAIRE"
        else:
            titre = "CERTIFICAT DE TRAVAIL"

        p.drawCentredString(width / 2, y, titre)

        # ==================== INFORMATIONS EMPLOYÉ ====================
        y -= 1.5 * cm
        p.setFont("Helvetica", 11)

        # Ligne d'introduction
        civilite = "Monsieur" if employe.sexe == 'M' else "Madame"
        nom_complet = f"{civilite} {employe.prenom} {employe.nom}"

        # Date de naissance
        date_naissance = employe.date_naissance.strftime('%d.%m.%Y') if employe.date_naissance else ''

        # Nationalité
        nationalite = str(employe.nationalite.name) if employe.nationalite else 'Suisse'

        # Texte d'introduction
        intro_text = f"{nom_complet}, né{'e' if employe.sexe == 'F' else ''} le {date_naissance}, de nationalité {nationalite.lower()}, "

        # Période d'emploi
        date_debut = self.date_debut_emploi.strftime('%d.%m.%Y')
        if self.date_fin_emploi:
            date_fin = self.date_fin_emploi.strftime('%d.%m.%Y')
            periode = f"a été employé{'e' if employe.sexe == 'F' else ''} dans notre entreprise du {date_debut} au {date_fin}"
        else:
            periode = f"est employé{'e' if employe.sexe == 'F' else ''} dans notre entreprise depuis le {date_debut}"

        # Fonction
        fonction_text = f"en qualité de {self.fonction_principale}"
        if self.taux_occupation < 100:
            fonction_text += f" à {self.taux_occupation}%"
        fonction_text += "."

        # Dessiner le paragraphe d'introduction
        full_intro = f"{intro_text}{periode} {fonction_text}"

        # Créer un style pour les paragraphes
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY

        style = ParagraphStyle(
            'Normal',
            fontName='Helvetica',
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY
        )

        # Dessiner ligne par ligne (simplifié)
        lines = self._wrap_text(full_intro, p, 'Helvetica', 11, usable_width)
        for line in lines:
            p.drawString(margin_left, y, line)
            y -= 0.5 * cm

        # ==================== DESCRIPTION DES TÂCHES (certificat complet) ====================
        if self.type_certificat != 'SIMPLE' and self.description_taches:
            y -= 0.5 * cm
            p.setFont("Helvetica-Bold", 11)
            p.drawString(margin_left, y, "Principales responsabilités:")
            y -= 0.5 * cm

            p.setFont("Helvetica", 11)
            taches_lines = self._wrap_text(self.description_taches, p, 'Helvetica', 11, usable_width)
            for line in taches_lines:
                p.drawString(margin_left, y, line)
                y -= 0.5 * cm

        # ==================== FORMATIONS (si présentes) ====================
        if self.type_certificat != 'SIMPLE' and self.formations_suivies:
            y -= 0.3 * cm
            p.setFont("Helvetica", 11)
            formations_intro = f"Durant son emploi, {civilite.lower()} {employe.nom} a suivi les formations suivantes:"
            p.drawString(margin_left, y, formations_intro)
            y -= 0.5 * cm

            formation_lines = self._wrap_text(self.formations_suivies, p, 'Helvetica', 11, usable_width)
            for line in formation_lines:
                p.drawString(margin_left, y, line)
                y -= 0.5 * cm

        # ==================== ÉVALUATION (certificat complet) ====================
        if self.type_certificat != 'SIMPLE':
            y -= 0.5 * cm

            # Utiliser le texte d'évaluation personnalisé ou le générer
            texte_eval = self.texte_evaluation or self.generer_texte_evaluation()
            if texte_eval:
                eval_lines = self._wrap_text(texte_eval, p, 'Helvetica', 11, usable_width)
                for line in eval_lines:
                    p.drawString(margin_left, y, line)
                    y -= 0.5 * cm

        # ==================== MOTIF DE DÉPART ====================
        if self.date_fin_emploi and self.motif_depart:
            y -= 0.3 * cm
            motifs_textes = {
                'DEMISSION': f"{civilite} {employe.nom} nous quitte de sa propre initiative.",
                'FIN_CONTRAT': "Le contrat à durée déterminée est arrivé à son terme.",
                'LICENCIEMENT_ECO': "La fin des rapports de travail est due à des raisons économiques.",
                'RETRAITE': f"{civilite} {employe.nom} prend une retraite bien méritée.",
                'ACCORD_MUTUEL': "Les rapports de travail ont pris fin d'un commun accord.",
            }
            motif_text = motifs_textes.get(self.motif_depart, "")
            if motif_text:
                p.drawString(margin_left, y, motif_text)
                y -= 0.5 * cm

        # ==================== FORMULE DE FIN ====================
        y -= 0.3 * cm
        formule = self.formule_fin or self.generer_formule_fin_standard()
        if formule:
            formule_lines = self._wrap_text(formule, p, 'Helvetica', 11, usable_width)
            for line in formule_lines:
                p.drawString(margin_left, y, line)
                y -= 0.5 * cm

        # ==================== DATE ET LIEU ====================
        y -= 1 * cm
        p.setFont("Helvetica", 11)
        lieu = adresse_client.localite if adresse_client else ""
        date_emission = self.date_emission.strftime('%d %B %Y') if self.date_emission else date.today().strftime('%d %B %Y')
        p.drawString(margin_left, y, f"{lieu}, le {date_emission}")

        # ==================== SIGNATURE ====================
        y -= 2 * cm
        p.drawString(margin_left, y, "_" * 40)
        y -= 0.4 * cm
        p.drawString(margin_left, y, client.raison_sociale)
        if self.emis_par:
            y -= 0.4 * cm
            p.drawString(margin_left, y, self.emis_par.get_full_name())

        # ==================== PIED DE PAGE ====================
        p.setFont("Helvetica", 8)
        p.setFillColor(colors.grey)
        p.drawCentredString(width / 2, 1.5 * cm, "Ce document est confidentiel.")

        # Finaliser
        p.showPage()
        p.save()

        # Sauvegarder
        buffer.seek(0)
        type_suffix = self.type_certificat.lower()
        filename = f"certificat_travail_{employe.matricule}_{type_suffix}_{date.today().strftime('%Y%m%d')}.pdf"

        self.fichier_pdf.save(filename, ContentFile(buffer.read()), save=True)

        return self.fichier_pdf

    def _wrap_text(self, text, canvas, font_name, font_size, max_width):
        """Découpe le texte en lignes qui rentrent dans la largeur max"""
        canvas.setFont(font_name, font_size)
        words = text.replace('\n', ' ').split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if canvas.stringWidth(test_line, font_name, font_size) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines