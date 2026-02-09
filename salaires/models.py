# apps/salaires/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
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

    # Lien vers le compte utilisateur (si accès application)
    utilisateur = models.OneToOneField(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employe_record',
        verbose_name=_('Compte utilisateur'),
        help_text=_('Compte utilisateur lié (si accès application)')
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
    """
    Certificat de salaire annuel - Formulaire 11 officiel suisse
    Conforme aux directives de l'Administration fédérale des contributions (AFC)
    """

    # Choix pour le type d'occupation (Section F)
    TYPE_OCCUPATION_CHOICES = [
        ('PLEIN_TEMPS', 'Plein temps'),
        ('TEMPS_PARTIEL', 'Temps partiel'),
        ('HORAIRE', 'Travail à l\'heure'),
    ]

    # Statut du certificat
    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('CALCULE', 'Calculé'),
        ('VERIFIE', 'Vérifié'),
        ('SIGNE', 'Signé'),
        ('ENVOYE', 'Envoyé'),
    ]

    # ==================== SECTION A-B: EMPLOYEUR ====================
    # (Les données employeur sont récupérées via employe.mandat.client)

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

    # ==================== SECTION C-E: PÉRIODE ET EMPLOYÉ ====================
    date_debut = models.DateField(
        verbose_name='Date de début',
        help_text='Début de la période d\'emploi pour cette année (Section C)'
    )
    date_fin = models.DateField(
        verbose_name='Date de fin',
        help_text='Fin de la période d\'emploi pour cette année (Section C)'
    )

    # ==================== SECTION F-G: OCCUPATION ET TRANSPORT ====================
    type_occupation = models.CharField(
        max_length=20, choices=TYPE_OCCUPATION_CHOICES, default='PLEIN_TEMPS',
        verbose_name='Type d\'occupation',
        help_text='Section F: Type de rapport de travail'
    )
    taux_occupation = models.DecimalField(
        max_digits=5, decimal_places=2, default=100,
        verbose_name='Taux d\'occupation (%)',
        help_text='Section F: Taux d\'occupation en pourcentage'
    )
    transport_public_disponible = models.BooleanField(
        default=True,
        verbose_name='Transport public disponible',
        help_text='Section G: Des transports publics sont disponibles pour le trajet domicile-travail'
    )
    transport_gratuit_fourni = models.BooleanField(
        default=False,
        verbose_name='Transport gratuit fourni',
        help_text='Section G: L\'employeur fournit un transport gratuit'
    )

    # ==================== CHIFFRE 1: SALAIRE ====================
    chiffre_1_salaire = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='1. Salaire / Rente',
        help_text='Salaire, rente (y.c. allocations pour perte de gain)'
    )

    # ==================== CHIFFRE 2: PRESTATIONS EN NATURE ====================
    # 2.1 Repas
    chiffre_2_1_repas = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='2.1 Repas',
        help_text='Valeur des repas gratuits (CHF 180/mois midi, CHF 180/mois soir)'
    )
    repas_midi_gratuit = models.BooleanField(
        default=False,
        verbose_name='Repas de midi gratuit',
        help_text='Case 2.1: L\'employé bénéficie de repas de midi gratuits'
    )
    repas_soir_gratuit = models.BooleanField(
        default=False,
        verbose_name='Repas du soir gratuit',
        help_text='Case 2.1: L\'employé bénéficie de repas du soir gratuits'
    )

    # 2.2 Voiture de service
    chiffre_2_2_voiture = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='2.2 Véhicule de service',
        help_text='Valeur de l\'utilisation privée du véhicule (0.9% par mois du prix d\'achat)'
    )
    voiture_disponible = models.BooleanField(
        default=False,
        verbose_name='Voiture de service disponible',
        help_text='Case 2.2: Un véhicule de service est mis à disposition pour usage privé'
    )
    voiture_prix_achat = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Prix d\'achat du véhicule',
        help_text='Prix d\'achat du véhicule (hors TVA) pour calcul de la part privée'
    )

    # 2.3 Autres prestations
    chiffre_2_3_autres = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='2.3 Autres prestations en nature',
        help_text='Autres prestations en nature (logement, etc.)'
    )
    autres_prestations_nature_detail = models.TextField(
        blank=True,
        verbose_name='Détail autres prestations',
        help_text='Description des autres prestations en nature'
    )

    # ==================== CHIFFRE 3: PRESTATIONS IRRÉGULIÈRES ====================
    chiffre_3_irregulier = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='3. Prestations irrégulières',
        help_text='Bonus, gratifications, 13ème salaire, indemnités de vacances non prises'
    )

    # ==================== CHIFFRE 4: PRESTATIONS EN CAPITAL ====================
    chiffre_4_capital = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='4. Prestations en capital',
        help_text='Indemnités de départ, prestations provenant d\'institutions de prévoyance'
    )

    # ==================== CHIFFRE 5: PARTICIPATIONS ====================
    chiffre_5_participations = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='5. Droits de participation',
        help_text='Actions de collaborateurs, options, etc.'
    )
    participations_detail = models.TextField(
        blank=True,
        verbose_name='Détail participations',
        help_text='Description des participations (type, nombre, valeur)'
    )

    # ==================== CHIFFRE 6: CONSEIL D'ADMINISTRATION ====================
    chiffre_6_ca = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='6. Conseil d\'administration',
        help_text='Indemnités de membre d\'organe de direction'
    )

    # ==================== CHIFFRE 7: AUTRES PRESTATIONS ====================
    chiffre_7_autres = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='7. Autres prestations',
        help_text='Toutes autres prestations non mentionnées ailleurs'
    )
    autres_prestations_detail = models.TextField(
        blank=True,
        verbose_name='Détail autres prestations',
        help_text='Description des autres prestations'
    )

    # ==================== CHIFFRE 8: TOTAL BRUT (CALCULÉ) ====================
    chiffre_8_total_brut = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='8. Salaire brut total',
        help_text='Total des chiffres 1 à 7 (calculé automatiquement)'
    )

    # ==================== CHIFFRE 9: COTISATIONS AVS/AI/APG/AC/AANP ====================
    chiffre_9_cotisations = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='9. Cotisations AVS/AI/APG/AC/AANP',
        help_text='Cotisations employé aux assurances sociales obligatoires'
    )

    # ==================== CHIFFRE 10: PRÉVOYANCE PROFESSIONNELLE ====================
    chiffre_10_1_lpp_ordinaire = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='10.1 LPP cotisations ordinaires',
        help_text='Cotisations ordinaires à la prévoyance professionnelle'
    )
    chiffre_10_2_lpp_rachat = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='10.2 LPP rachats',
        help_text='Rachats d\'années de cotisation LPP'
    )

    # ==================== CHIFFRE 11: SALAIRE NET (CALCULÉ) ====================
    chiffre_11_net = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='11. Salaire net',
        help_text='Chiffre 8 moins chiffres 9 et 10 (calculé automatiquement)'
    )

    # ==================== CHIFFRE 12: FRAIS DE TRANSPORT ====================
    chiffre_12_transport = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='12. Frais effectifs de transport',
        help_text='Frais de déplacement domicile-lieu de travail remboursés'
    )

    # ==================== CHIFFRE 13: FRAIS DE REPAS ET NUITÉES ====================
    chiffre_13_1_1_repas_effectif = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='13.1.1 Frais de repas effectifs',
        help_text='Frais de repas effectifs pour travail en dehors'
    )
    chiffre_13_1_2_repas_forfait = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='13.1.2 Frais de repas forfaitaires',
        help_text='Indemnité forfaitaire pour repas de midi'
    )
    chiffre_13_2_nuitees = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='13.2 Nuitées',
        help_text='Frais d\'hébergement pour déplacements professionnels'
    )
    chiffre_13_3_repas_externes = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='13.3 Repas à l\'extérieur',
        help_text='Frais de repas lors de déplacements externes'
    )

    # ==================== CHIFFRE 14: AUTRES FRAIS ====================
    chiffre_14_autres_frais = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='14. Autres frais',
        help_text='Autres frais professionnels remboursés'
    )
    autres_frais_detail = models.TextField(
        blank=True,
        verbose_name='Détail autres frais',
        help_text='Description des autres frais professionnels'
    )

    # ==================== CHIFFRE 15: JOURS DE TRAVAIL AVEC DÉPLACEMENT ====================
    chiffre_15_jours_transport = models.IntegerField(
        default=0,
        verbose_name='15. Jours avec déplacement',
        help_text='Nombre de jours de travail avec déplacement domicile-travail'
    )

    # ==================== SECTION I: REMARQUES ====================
    remarques = models.TextField(
        blank=True,
        verbose_name='Remarques',
        help_text='Section I: Remarques diverses (expatriés, détachés, etc.)'
    )

    # ==================== SIGNATURE ====================
    lieu_signature = models.CharField(
        max_length=100, blank=True,
        verbose_name='Lieu de signature',
        help_text='Lieu où le certificat est signé'
    )
    date_signature = models.DateField(
        null=True, blank=True,
        verbose_name='Date de signature',
        help_text='Date de signature du certificat'
    )
    nom_signataire = models.CharField(
        max_length=200, blank=True,
        verbose_name='Nom du signataire',
        help_text='Nom de la personne autorisée à signer'
    )
    telephone_signataire = models.CharField(
        max_length=50, blank=True,
        verbose_name='Téléphone du signataire',
        help_text='Numéro de téléphone pour questions'
    )
    est_signe = models.BooleanField(
        default=False,
        verbose_name='Signé',
        help_text='Indique si le certificat a été signé'
    )

    # ==================== STATUT ET MÉTADONNÉES ====================
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='BROUILLON',
        verbose_name='Statut',
        help_text='État actuel du certificat'
    )

    # ==================== CHAMPS LEGACY (maintenu pour compatibilité) ====================
    salaire_brut_annuel = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Salaire brut annuel (legacy)',
        help_text='[Obsolète] Utiliser chiffre_1_salaire'
    )
    treizieme_salaire_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='13ème salaire annuel (legacy)',
        help_text='[Obsolète] Inclus dans chiffre_3_irregulier'
    )
    primes_annuelles = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Primes annuelles (legacy)',
        help_text='[Obsolète] Inclus dans chiffre_3_irregulier'
    )
    avs_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AVS annuel (legacy)',
        help_text='[Obsolète] Utiliser chiffre_9_cotisations'
    )
    ac_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='AC annuel (legacy)',
        help_text='[Obsolète] Inclus dans chiffre_9_cotisations'
    )
    lpp_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='LPP annuel (legacy)',
        help_text='[Obsolète] Utiliser chiffre_10_1_lpp_ordinaire'
    )
    allocations_familiales_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Allocations familiales annuelles (legacy)',
        help_text='[Obsolète] Les allocations ne figurent pas sur le formulaire 11'
    )
    frais_deplacement = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Frais de déplacement (legacy)',
        help_text='[Obsolète] Utiliser chiffre_12_transport'
    )
    frais_repas = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Frais de repas (legacy)',
        help_text='[Obsolète] Utiliser chiffre_13_*'
    )
    impot_source_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Impôt à la source annuel',
        help_text='Total impôt à la source retenu (info uniquement, pas sur formulaire 11)'
    )

    # ==================== FICHIER PDF ====================
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
        verbose_name_plural = 'Certificats de salaire'
        unique_together = [['employe', 'annee']]
        ordering = ['-annee']

    def __str__(self):
        return f"Certificat {self.annee} - {self.employe}"

    def save(self, *args, **kwargs):
        """Recalcule les totaux avant sauvegarde"""
        self.calculer_totaux()
        super().save(*args, **kwargs)

    def calculer_totaux(self):
        """Calcule les chiffres 8 (brut total) et 11 (net)"""
        # Chiffre 8: Total brut = somme des chiffres 1 à 7
        self.chiffre_8_total_brut = (
            (self.chiffre_1_salaire or Decimal('0')) +
            (self.chiffre_2_1_repas or Decimal('0')) +
            (self.chiffre_2_2_voiture or Decimal('0')) +
            (self.chiffre_2_3_autres or Decimal('0')) +
            (self.chiffre_3_irregulier or Decimal('0')) +
            (self.chiffre_4_capital or Decimal('0')) +
            (self.chiffre_5_participations or Decimal('0')) +
            (self.chiffre_6_ca or Decimal('0')) +
            (self.chiffre_7_autres or Decimal('0'))
        )

        # Chiffre 11: Net = Brut - Cotisations - LPP
        self.chiffre_11_net = (
            self.chiffre_8_total_brut -
            (self.chiffre_9_cotisations or Decimal('0')) -
            (self.chiffre_10_1_lpp_ordinaire or Decimal('0')) -
            (self.chiffre_10_2_lpp_rachat or Decimal('0'))
        )

    def calculer_depuis_fiches(self, save=True):
        """
        Calcule automatiquement le certificat depuis les fiches de salaire validées.

        Agrège les données des FicheSalaire de l'année pour remplir les champs
        du formulaire 11 officiel suisse.

        Args:
            save: Si True, sauvegarde le certificat après calcul

        Returns:
            self: L'instance mise à jour
        """
        from django.db.models import Sum, Min, Max
        from datetime import date

        # Récupérer les fiches validées de l'année
        fiches = FicheSalaire.objects.filter(
            employe=self.employe,
            annee=self.annee,
            statut__in=['VALIDE', 'PAYE', 'COMPTABILISE']
        )

        if not fiches.exists():
            raise ValueError(f"Aucune fiche de salaire validée pour {self.employe} en {self.annee}")

        # Agréger les données
        agregats = fiches.aggregate(
            # Salaires
            total_salaire_base=Sum('salaire_base'),
            total_heures_supp=Sum('heures_supp_montant'),
            total_primes=Sum('primes'),
            total_indemnites=Sum('indemnites'),
            total_treizieme=Sum('treizieme_mois'),
            # Cotisations
            total_avs=Sum('avs_employe'),
            total_ac=Sum('ac_employe'),
            total_ac_supp=Sum('ac_supp_employe'),
            total_laa=Sum('laa_employe'),
            total_laac=Sum('laac_employe'),
            total_ijm=Sum('ijm_employe'),
            total_lpp=Sum('lpp_employe'),
            # Impôt source
            total_is=Sum('impot_source'),
            # Allocations (info)
            total_alloc_fam=Sum('allocations_familiales'),
            # Période
            premiere_periode=Min('periode'),
            derniere_periode=Max('periode'),
        )

        # === Déterminer la période d'emploi ===
        # Utiliser les dates de l'employé si disponibles, sinon les périodes des fiches
        employe = self.employe

        if employe.date_entree and employe.date_entree.year <= self.annee:
            debut_annee = date(self.annee, 1, 1)
            self.date_debut = max(employe.date_entree, debut_annee)
        else:
            self.date_debut = agregats['premiere_periode']

        if employe.date_sortie and employe.date_sortie.year == self.annee:
            self.date_fin = employe.date_sortie
        else:
            # Dernier jour du dernier mois avec fiche
            derniere = agregats['derniere_periode']
            import calendar
            dernier_jour = calendar.monthrange(derniere.year, derniere.month)[1]
            self.date_fin = date(derniere.year, derniere.month, dernier_jour)

        # === Chiffre 1: Salaire régulier ===
        self.chiffre_1_salaire = (
            (agregats['total_salaire_base'] or Decimal('0')) +
            (agregats['total_heures_supp'] or Decimal('0'))
        )

        # === Chiffre 3: Prestations irrégulières ===
        # 13ème salaire, primes, gratifications
        self.chiffre_3_irregulier = (
            (agregats['total_treizieme'] or Decimal('0')) +
            (agregats['total_primes'] or Decimal('0'))
        )

        # === Chiffre 9: Cotisations AVS/AI/APG/AC/AANP ===
        self.chiffre_9_cotisations = (
            (agregats['total_avs'] or Decimal('0')) +
            (agregats['total_ac'] or Decimal('0')) +
            (agregats['total_ac_supp'] or Decimal('0')) +
            (agregats['total_laa'] or Decimal('0')) +
            (agregats['total_laac'] or Decimal('0')) +
            (agregats['total_ijm'] or Decimal('0'))
        )

        # === Chiffre 10: Prévoyance professionnelle ===
        self.chiffre_10_1_lpp_ordinaire = agregats['total_lpp'] or Decimal('0')

        # === Impôt à la source (info, pas sur formulaire 11) ===
        self.impot_source_annuel = agregats['total_is'] or Decimal('0')

        # === Allocations familiales (info, pas sur formulaire 11) ===
        self.allocations_familiales_annuel = agregats['total_alloc_fam'] or Decimal('0')

        # === Taux d'occupation ===
        self.taux_occupation = employe.taux_occupation or Decimal('100')

        # === Chiffres 15: Jours de travail ===
        # Estimation basée sur les fiches
        jours_travailles = fiches.aggregate(total=Sum('jours_travailles'))['total']
        self.chiffre_15_jours_transport = int(jours_travailles or 0)

        # === Mise à jour du statut ===
        self.statut = 'CALCULE'

        # === Compatibilité legacy ===
        self.salaire_brut_annuel = self.chiffre_1_salaire
        self.treizieme_salaire_annuel = agregats['total_treizieme'] or Decimal('0')
        self.primes_annuelles = agregats['total_primes'] or Decimal('0')
        self.avs_annuel = agregats['total_avs'] or Decimal('0')
        self.ac_annuel = (
            (agregats['total_ac'] or Decimal('0')) +
            (agregats['total_ac_supp'] or Decimal('0'))
        )
        self.lpp_annuel = self.chiffre_10_1_lpp_ordinaire

        # Calculer les totaux
        self.calculer_totaux()

        if save:
            self.save()

        return self

    def valider(self, user=None):
        """Marque le certificat comme vérifié"""
        if self.statut not in ['CALCULE', 'BROUILLON']:
            raise ValueError(f"Impossible de valider un certificat en statut {self.statut}")
        self.statut = 'VERIFIE'
        self.save()
        return self

    def signer(self, lieu, nom_signataire, telephone=None, user=None):
        """Signe le certificat"""
        from datetime import date as date_class

        if self.statut not in ['VERIFIE', 'CALCULE']:
            raise ValueError(f"Impossible de signer un certificat en statut {self.statut}")

        self.lieu_signature = lieu
        self.date_signature = date_class.today()
        self.nom_signataire = nom_signataire
        self.telephone_signataire = telephone or ''
        self.est_signe = True
        self.statut = 'SIGNE'
        self.save()
        return self

    @staticmethod
    def _format_montant_suisse(montant):
        """Formate un montant au format suisse: 1'234.56"""
        if montant is None:
            return ""
        val = Decimal(str(montant))
        if val == 0:
            return ""
        # Format avec apostrophe comme séparateur de milliers
        formatted = f"{val:,.2f}".replace(',', "'")
        return formatted

    def generer_pdf(self):
        """
        Génère le PDF du certificat de salaire (ancienne méthode, conservée pour compatibilité).
        Appelle generer_pdf_formulaire11().
        """
        return self.generer_pdf_formulaire11()

    def generer_pdf_formulaire11(self):
        """
        Génère le PDF du certificat de salaire au format Formulaire 11 officiel suisse.

        Le formulaire 11 est structuré avec:
        - Sections A-B: Informations employeur
        - Sections C-H: Informations employé, période, occupation, transport
        - Chiffres 1-7: Revenus (salaire, prestations en nature, irréguliers, capital, participations)
        - Chiffre 8: Total brut
        - Chiffres 9-10: Déductions (cotisations sociales, LPP)
        - Chiffre 11: Salaire net
        - Chiffres 12-15: Frais professionnels et jours de transport
        - Section I: Remarques
        - Signature

        Returns:
            FileField: Le fichier PDF généré et sauvegardé
        """
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as pdf_canvas
        from django.core.files.base import ContentFile
        from datetime import date as date_class

        buffer = io.BytesIO()
        width, height = A4

        # Marges
        margin_left = 1.2 * cm
        margin_right = 1.2 * cm
        margin_top = 1.0 * cm

        # Colonnes pour les montants
        col_numero = margin_left
        col_libelle = margin_left + 1.0 * cm
        col_montant = width - margin_right - 3.0 * cm
        col_montant_end = width - margin_right

        # Créer le canvas
        p = pdf_canvas.Canvas(buffer, pagesize=A4)

        def format_montant(val):
            return self._format_montant_suisse(val)

        def draw_checkbox(x, y, checked=False, size=3*mm):
            """Dessine une case à cocher"""
            p.setStrokeColor(colors.black)
            p.setLineWidth(0.5)
            p.rect(x, y - size, size, size, fill=0)
            if checked:
                p.setFont("Helvetica-Bold", 8)
                p.drawString(x + 0.5*mm, y - size + 0.5*mm, "X")

        def draw_amount_line(y, numero, libelle, montant, indent=0):
            """Dessine une ligne avec numéro, libellé et montant"""
            p.setFont("Helvetica", 8)
            if numero:
                p.drawString(col_numero + indent, y, numero)
            p.drawString(col_libelle + indent, y, libelle)
            if montant is not None and montant != 0:
                p.drawRightString(col_montant_end, y, format_montant(montant))
            return y - 0.35 * cm

        # ==================== EN-TÊTE ====================
        y = height - margin_top

        # Titre
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(width / 2, y, "CERTIFICAT DE SALAIRE")
        p.setFont("Helvetica", 8)
        p.drawCentredString(width / 2, y - 0.4*cm, "Attestation de rentes, pensions et prestations en capital")

        # Année (encadré à droite)
        p.setFont("Helvetica-Bold", 12)
        p.drawRightString(width - margin_right, y, str(self.annee))

        y -= 1.2 * cm

        # ==================== SECTION A-B: EMPLOYEUR ====================
        client = self.employe.mandat.client
        adresse_client = client.adresse_siege

        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin_left, y, "A. Employeur / Caisse de compensation AVS:")

        p.setFont("Helvetica", 8)
        y -= 0.35 * cm
        p.drawString(margin_left, y, client.raison_sociale)

        if adresse_client:
            y -= 0.3 * cm
            p.drawString(margin_left, y, f"{adresse_client.rue} {adresse_client.numero or ''}")
            y -= 0.3 * cm
            p.drawString(margin_left, y, f"{adresse_client.code_postal} {adresse_client.localite}")

        # Section B: IDE et N° AVS employeur
        p.setFont("Helvetica-Bold", 8)
        y -= 0.5 * cm
        p.drawString(margin_left, y, "B.")

        p.setFont("Helvetica", 8)
        ide = client.ide_number or ''
        p.drawString(margin_left + 0.5*cm, y, f"N° IDE: {ide}")

        # N° AVS employeur (si disponible via le mandat)
        avs_employeur = getattr(client, 'numero_ahv_employeur', '') or ''
        y -= 0.3 * cm
        p.drawString(margin_left + 0.5*cm, y, f"N° AVS employeur: {avs_employeur}")

        # ==================== SECTION C-E: EMPLOYÉ ====================
        y -= 0.6 * cm
        employe = self.employe

        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin_left, y, "C. N° AVS de l'employé:")
        p.setFont("Helvetica", 8)
        p.drawString(margin_left + 4*cm, y, employe.avs_number or '-')

        # Période d'emploi
        p.setFont("Helvetica-Bold", 8)
        p.drawString(width/2, y, "du")
        p.setFont("Helvetica", 8)
        p.drawString(width/2 + 0.6*cm, y, self.date_debut.strftime('%d.%m.%Y') if self.date_debut else '')
        p.setFont("Helvetica-Bold", 8)
        p.drawString(width/2 + 3*cm, y, "au")
        p.setFont("Helvetica", 8)
        p.drawString(width/2 + 3.6*cm, y, self.date_fin.strftime('%d.%m.%Y') if self.date_fin else '')

        y -= 0.4 * cm
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin_left, y, "D. Nom, prénom:")
        p.setFont("Helvetica", 8)
        p.drawString(margin_left + 3*cm, y, f"{employe.nom} {employe.prenom}")

        y -= 0.35 * cm
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin_left, y, "E. Adresse:")
        p.setFont("Helvetica", 8)
        adresse_emp = employe.adresse
        if adresse_emp:
            p.drawString(margin_left + 2*cm, y, f"{adresse_emp.rue} {adresse_emp.numero or ''}, {adresse_emp.code_postal} {adresse_emp.localite}")

        # ==================== SECTION F-G: OCCUPATION ET TRANSPORT ====================
        y -= 0.5 * cm

        # F. Type d'occupation et taux
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin_left, y, "F. Activité:")

        # Cases à cocher pour le type
        x_check = margin_left + 2*cm
        draw_checkbox(x_check, y, self.type_occupation == 'PLEIN_TEMPS')
        p.setFont("Helvetica", 7)
        p.drawString(x_check + 4*mm, y - 2*mm, "Plein temps")

        x_check += 3*cm
        draw_checkbox(x_check, y, self.type_occupation == 'TEMPS_PARTIEL')
        p.drawString(x_check + 4*mm, y - 2*mm, "Temps partiel")

        x_check += 3*cm
        draw_checkbox(x_check, y, self.type_occupation == 'HORAIRE')
        p.drawString(x_check + 4*mm, y - 2*mm, "À l'heure")

        # Taux d'occupation
        p.setFont("Helvetica", 8)
        p.drawString(width - 4*cm, y, f"Taux: {self.taux_occupation}%")

        # G. Transport
        y -= 0.4 * cm
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin_left, y, "G. Transport:")

        x_check = margin_left + 2.2*cm
        draw_checkbox(x_check, y, self.transport_public_disponible)
        p.setFont("Helvetica", 7)
        p.drawString(x_check + 4*mm, y - 2*mm, "Transport public disponible")

        x_check += 4.5*cm
        draw_checkbox(x_check, y, self.transport_gratuit_fourni)
        p.drawString(x_check + 4*mm, y - 2*mm, "Transport gratuit fourni")

        # ==================== LIGNE DE SÉPARATION ====================
        y -= 0.6 * cm
        p.setStrokeColor(colors.black)
        p.setLineWidth(0.5)
        p.line(margin_left, y, width - margin_right, y)

        # ==================== CHIFFRES 1-7: REVENUS ====================
        y -= 0.5 * cm
        p.setFont("Helvetica-Bold", 9)
        p.drawString(margin_left, y, "REVENUS")
        p.drawRightString(col_montant_end, y, "CHF")

        y -= 0.4 * cm

        # Chiffre 1: Salaire
        y = draw_amount_line(y, "1.", "Salaire (y.c. allocations, commissions, primes à l'ancienneté)", self.chiffre_1_salaire)

        # Chiffre 2: Prestations en nature
        y = draw_amount_line(y, "2.", "Prestations en nature", None)

        # 2.1 Repas
        total_2_1 = self.chiffre_2_1_repas or Decimal('0')
        if self.repas_midi_gratuit or self.repas_soir_gratuit or total_2_1 > 0:
            y = draw_amount_line(y, "2.1", "Repas / Logement", total_2_1, indent=0.3*cm)

        # 2.2 Voiture
        if self.voiture_disponible or (self.chiffre_2_2_voiture and self.chiffre_2_2_voiture > 0):
            y = draw_amount_line(y, "2.2", "Part privée véhicule de service", self.chiffre_2_2_voiture, indent=0.3*cm)

        # 2.3 Autres
        if self.chiffre_2_3_autres and self.chiffre_2_3_autres > 0:
            y = draw_amount_line(y, "2.3", "Autres prestations en nature", self.chiffre_2_3_autres, indent=0.3*cm)

        # Chiffre 3: Prestations irrégulières
        y = draw_amount_line(y, "3.", "Prestations irrégulières (13ème, bonus, gratifications)", self.chiffre_3_irregulier)

        # Chiffre 4: Prestations en capital
        if self.chiffre_4_capital and self.chiffre_4_capital > 0:
            y = draw_amount_line(y, "4.", "Prestations en capital", self.chiffre_4_capital)

        # Chiffre 5: Participations
        if self.chiffre_5_participations and self.chiffre_5_participations > 0:
            y = draw_amount_line(y, "5.", "Droits de participation (actions, options)", self.chiffre_5_participations)

        # Chiffre 6: Conseil d'administration
        if self.chiffre_6_ca and self.chiffre_6_ca > 0:
            y = draw_amount_line(y, "6.", "Indemnités conseil d'administration", self.chiffre_6_ca)

        # Chiffre 7: Autres
        if self.chiffre_7_autres and self.chiffre_7_autres > 0:
            y = draw_amount_line(y, "7.", "Autres prestations", self.chiffre_7_autres)

        # ==================== CHIFFRE 8: TOTAL BRUT ====================
        y -= 0.2 * cm
        p.setStrokeColor(colors.black)
        p.setLineWidth(0.3)
        p.line(col_montant - 1*cm, y + 0.15*cm, col_montant_end, y + 0.15*cm)

        p.setFont("Helvetica-Bold", 9)
        p.drawString(col_numero, y, "8.")
        p.drawString(col_libelle, y, "Salaire brut total (somme des chiffres 1 à 7)")
        p.drawRightString(col_montant_end, y, format_montant(self.chiffre_8_total_brut))

        # ==================== CHIFFRES 9-10: DÉDUCTIONS ====================
        y -= 0.6 * cm
        p.setFont("Helvetica-Bold", 9)
        p.drawString(margin_left, y, "DÉDUCTIONS")

        y -= 0.4 * cm
        p.setFont("Helvetica", 8)

        # Chiffre 9: Cotisations
        y = draw_amount_line(y, "9.", "Cotisations AVS/AI/APG/AC/AANP", self.chiffre_9_cotisations)

        # Chiffre 10: LPP
        y = draw_amount_line(y, "10.", "Prévoyance professionnelle", None)
        y = draw_amount_line(y, "10.1", "Cotisations ordinaires", self.chiffre_10_1_lpp_ordinaire, indent=0.3*cm)

        if self.chiffre_10_2_lpp_rachat and self.chiffre_10_2_lpp_rachat > 0:
            y = draw_amount_line(y, "10.2", "Rachats d'années", self.chiffre_10_2_lpp_rachat, indent=0.3*cm)

        # ==================== CHIFFRE 11: SALAIRE NET ====================
        y -= 0.2 * cm
        p.setStrokeColor(colors.black)
        p.setLineWidth(0.3)
        p.line(col_montant - 1*cm, y + 0.15*cm, col_montant_end, y + 0.15*cm)

        p.setFont("Helvetica-Bold", 9)
        p.drawString(col_numero, y, "11.")
        p.drawString(col_libelle, y, "Salaire net (chiffre 8 moins chiffres 9 et 10)")
        p.drawRightString(col_montant_end, y, format_montant(self.chiffre_11_net))

        p.setLineWidth(0.5)
        p.line(col_montant - 1*cm, y - 0.15*cm, col_montant_end, y - 0.15*cm)

        # ==================== CHIFFRES 12-15: FRAIS PROFESSIONNELS ====================
        y -= 0.7 * cm
        p.setFont("Helvetica-Bold", 9)
        p.drawString(margin_left, y, "FRAIS EFFECTIFS")

        y -= 0.4 * cm
        p.setFont("Helvetica", 8)

        # Chiffre 12: Transport
        if self.chiffre_12_transport and self.chiffre_12_transport > 0:
            y = draw_amount_line(y, "12.", "Frais de déplacement (trajet domicile-travail)", self.chiffre_12_transport)

        # Chiffre 13: Repas et nuitées
        has_13 = any([
            self.chiffre_13_1_1_repas_effectif,
            self.chiffre_13_1_2_repas_forfait,
            self.chiffre_13_2_nuitees,
            self.chiffre_13_3_repas_externes
        ])

        if has_13:
            y = draw_amount_line(y, "13.", "Frais de repas et nuitées", None)

            if self.chiffre_13_1_1_repas_effectif and self.chiffre_13_1_1_repas_effectif > 0:
                y = draw_amount_line(y, "13.1.1", "Repas effectifs", self.chiffre_13_1_1_repas_effectif, indent=0.3*cm)

            if self.chiffre_13_1_2_repas_forfait and self.chiffre_13_1_2_repas_forfait > 0:
                y = draw_amount_line(y, "13.1.2", "Repas forfaitaires", self.chiffre_13_1_2_repas_forfait, indent=0.3*cm)

            if self.chiffre_13_2_nuitees and self.chiffre_13_2_nuitees > 0:
                y = draw_amount_line(y, "13.2", "Nuitées", self.chiffre_13_2_nuitees, indent=0.3*cm)

            if self.chiffre_13_3_repas_externes and self.chiffre_13_3_repas_externes > 0:
                y = draw_amount_line(y, "13.3", "Repas externes", self.chiffre_13_3_repas_externes, indent=0.3*cm)

        # Chiffre 14: Autres frais
        if self.chiffre_14_autres_frais and self.chiffre_14_autres_frais > 0:
            y = draw_amount_line(y, "14.", "Autres frais professionnels", self.chiffre_14_autres_frais)

        # Chiffre 15: Jours de transport
        y -= 0.3 * cm
        p.setFont("Helvetica", 8)
        p.drawString(col_numero, y, "15.")
        p.drawString(col_libelle, y, "Nombre de jours avec déplacement domicile-travail:")
        if self.chiffre_15_jours_transport and self.chiffre_15_jours_transport > 0:
            p.drawRightString(col_montant_end, y, str(self.chiffre_15_jours_transport))

        # ==================== SECTION I: REMARQUES ====================
        y -= 0.7 * cm
        p.setStrokeColor(colors.grey)
        p.setLineWidth(0.3)
        p.line(margin_left, y, width - margin_right, y)

        y -= 0.4 * cm
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin_left, y, "I. Remarques:")

        if self.remarques:
            p.setFont("Helvetica", 7)
            y -= 0.3 * cm
            # Découper les remarques en lignes
            for ligne in self.remarques.split('\n')[:3]:  # Max 3 lignes
                p.drawString(margin_left + 0.5*cm, y, ligne[:90])  # Max 90 caractères
                y -= 0.25 * cm

        # ==================== SIGNATURE ====================
        y = min(y, 4.5 * cm)  # S'assurer qu'on a assez de place

        y -= 0.3 * cm
        p.setStrokeColor(colors.black)
        p.setLineWidth(0.3)
        p.line(margin_left, y, width - margin_right, y)

        y -= 0.5 * cm
        p.setFont("Helvetica", 8)

        # Lieu et date
        lieu = self.lieu_signature or (adresse_client.localite if adresse_client else '')
        date_sig = self.date_signature or date_class.today()
        p.drawString(margin_left, y, f"{lieu}, le {date_sig.strftime('%d.%m.%Y')}")

        # Téléphone
        if self.telephone_signataire:
            p.drawString(width/2, y, f"Tél.: {self.telephone_signataire}")

        y -= 0.8 * cm

        # Ligne de signature
        p.setStrokeColor(colors.black)
        p.line(margin_left, y, margin_left + 6*cm, y)

        y -= 0.3 * cm
        p.setFont("Helvetica", 7)
        p.drawString(margin_left, y, "Signature de l'employeur / Timbre")

        if self.nom_signataire:
            p.drawString(margin_left, y - 0.3*cm, self.nom_signataire)

        # ==================== PIED DE PAGE ====================
        p.setFont("Helvetica", 6)
        p.setFillColor(colors.grey)
        p.drawCentredString(width / 2, 1.2 * cm, "Formulaire 11 - Certificat de salaire")
        p.drawCentredString(width / 2, 0.9 * cm, f"Généré le {date_class.today().strftime('%d.%m.%Y')} - {client.raison_sociale}")

        # Finaliser le PDF
        p.showPage()
        p.save()

        # Sauvegarder le fichier
        buffer.seek(0)
        filename = f"certificat_salaire_f11_{self.employe.matricule}_{self.annee}.pdf"

        self.fichier_pdf.save(filename, ContentFile(buffer.read()), save=True)

        return self.fichier_pdf


class DeclarationCotisations(BaseModel):
    """
    Déclaration des cotisations sociales suisses

    Regroupe les cotisations à déclarer aux différentes caisses:
    - AVS/AI/APG/AC: Caisse de compensation
    - LPP: Institution de prévoyance
    - LAA/LAAC: Assureur accidents
    - AF: Caisse d'allocations familiales
    - IJM: Assureur maladie perte de gain
    """

    ORGANISME_CHOICES = [
        ('AVS', 'Caisse AVS/AI/APG/AC'),
        ('LPP', 'Institution de prévoyance LPP'),
        ('LAA', 'Assurance accidents LAA/LAAC'),
        ('AF', 'Caisse allocations familiales'),
        ('IJM', 'Assurance indemnités journalières maladie'),
    ]

    PERIODE_TYPE_CHOICES = [
        ('MENSUEL', 'Mensuelle'),
        ('TRIMESTRIEL', 'Trimestrielle'),
        ('ANNUEL', 'Annuelle'),
    ]

    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('CALCULEE', 'Calculée'),
        ('VERIFIEE', 'Vérifiée'),
        ('TRANSMISE', 'Transmise'),
        ('PAYEE', 'Payée'),
    ]

    # Identification
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='declarations_cotisations',
        verbose_name='Mandat',
        help_text='Mandat employeur concerné'
    )
    organisme = models.CharField(
        max_length=10, choices=ORGANISME_CHOICES,
        verbose_name='Organisme',
        help_text='Organisme destinataire de la déclaration'
    )

    # Informations caisse (selon l'organisme)
    nom_caisse = models.CharField(
        max_length=200, blank=True,
        verbose_name='Nom de la caisse',
        help_text='Dénomination officielle de la caisse'
    )
    numero_affilie = models.CharField(
        max_length=50, blank=True,
        verbose_name='N° affilié',
        help_text='Numéro d\'affiliation de l\'employeur'
    )
    numero_contrat = models.CharField(
        max_length=50, blank=True,
        verbose_name='N° contrat/police',
        help_text='Numéro de contrat ou police'
    )

    # Période
    periode_type = models.CharField(
        max_length=15, choices=PERIODE_TYPE_CHOICES,
        default='MENSUEL',
        verbose_name='Type de période',
        help_text='Fréquence de déclaration'
    )
    periode_debut = models.DateField(
        verbose_name='Début de période',
        help_text='Premier jour de la période déclarée'
    )
    periode_fin = models.DateField(
        verbose_name='Fin de période',
        help_text='Dernier jour de la période déclarée'
    )
    annee = models.IntegerField(
        verbose_name='Année',
        help_text='Année de la déclaration'
    )
    mois = models.IntegerField(
        null=True, blank=True,
        verbose_name='Mois',
        help_text='Mois (1-12) pour déclaration mensuelle'
    )
    trimestre = models.IntegerField(
        null=True, blank=True,
        verbose_name='Trimestre',
        help_text='Trimestre (1-4) pour déclaration trimestrielle'
    )

    # Effectifs
    nombre_employes = models.IntegerField(
        default=0,
        verbose_name='Nombre d\'employés',
        help_text='Nombre d\'employés déclarés'
    )

    # Masse salariale
    masse_salariale_brute = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Masse salariale brute',
        help_text='Total des salaires bruts en CHF'
    )
    masse_salariale_soumise = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Masse salariale soumise',
        help_text='Total des salaires soumis à cotisation en CHF'
    )

    # Cotisations détaillées (selon organisme)
    # Pour AVS
    cotisation_avs = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='AVS',
        help_text='Cotisation AVS (employeur + employé)'
    )
    cotisation_ai = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='AI',
        help_text='Cotisation AI (employeur + employé)'
    )
    cotisation_apg = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='APG',
        help_text='Cotisation APG (employeur + employé)'
    )
    cotisation_ac = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='AC',
        help_text='Cotisation AC (employeur + employé)'
    )
    cotisation_ac_supp = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='AC supplémentaire',
        help_text='AC sur salaires > 148\'200 CHF'
    )
    frais_administration = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Frais d\'administration',
        help_text='Frais de gestion de la caisse'
    )

    # Pour LPP
    cotisation_lpp_employe = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='LPP employé',
        help_text='Part employé LPP'
    )
    cotisation_lpp_employeur = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='LPP employeur',
        help_text='Part employeur LPP'
    )

    # Pour LAA
    cotisation_laa_pro = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='LAA professionnelle',
        help_text='Prime accidents professionnels'
    )
    cotisation_laa_non_pro = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='LAA non professionnelle',
        help_text='Prime accidents non professionnels'
    )
    cotisation_laac = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='LAAC complémentaire',
        help_text='Assurance accidents complémentaire'
    )

    # Pour AF
    cotisation_af = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Allocations familiales',
        help_text='Cotisation allocations familiales'
    )

    # Pour IJM
    cotisation_ijm = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='IJM',
        help_text='Prime indemnités journalières maladie'
    )

    # Totaux
    total_cotisations_employe = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total part employé',
        help_text='Total des cotisations part employé'
    )
    total_cotisations_employeur = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total part employeur',
        help_text='Total des cotisations part employeur'
    )
    montant_cotisations = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Montant total',
        help_text='Total des cotisations dues en CHF'
    )

    # Dates et statut
    statut = models.CharField(
        max_length=15, choices=STATUT_CHOICES,
        default='BROUILLON', db_index=True,
        verbose_name='Statut',
        help_text='État de la déclaration'
    )
    date_declaration = models.DateField(
        null=True, blank=True,
        verbose_name='Date de déclaration',
        help_text='Date de création de la déclaration'
    )
    date_echeance = models.DateField(
        null=True, blank=True,
        verbose_name='Date d\'échéance',
        help_text='Date limite de paiement'
    )
    date_transmission = models.DateField(
        null=True, blank=True,
        verbose_name='Date de transmission',
        help_text='Date d\'envoi à la caisse'
    )
    date_paiement = models.DateField(
        null=True, blank=True,
        verbose_name='Date de paiement',
        help_text='Date effective du paiement'
    )

    # Références
    numero_reference = models.CharField(
        max_length=50, blank=True,
        verbose_name='Numéro de référence',
        help_text='Référence attribuée par l\'organisme'
    )
    numero_bvr = models.CharField(
        max_length=50, blank=True,
        verbose_name='N° BVR/QR',
        help_text='Numéro de référence de paiement'
    )
    iban_caisse = models.CharField(
        max_length=34, blank=True,
        verbose_name='IBAN caisse',
        help_text='IBAN pour le paiement'
    )

    # Documents
    fichier_declaration = models.FileField(
        upload_to='salaires/declarations/',
        null=True, blank=True,
        verbose_name='Fichier déclaration',
        help_text='Document de déclaration généré'
    )

    # Remarques
    remarques = models.TextField(
        blank=True,
        verbose_name='Remarques',
        help_text='Notes et observations'
    )

    class Meta:
        db_table = 'declarations_cotisations'
        verbose_name = 'Déclaration de cotisations'
        verbose_name_plural = 'Déclarations de cotisations'
        ordering = ['-annee', '-periode_fin', 'organisme']
        unique_together = ['mandat', 'organisme', 'annee', 'mois', 'trimestre']

    def __str__(self):
        periode = f"{self.mois}/{self.annee}" if self.mois else f"T{self.trimestre}/{self.annee}" if self.trimestre else str(self.annee)
        return f"{self.get_organisme_display()} - {periode} - {self.mandat}"

    def get_periode_display(self):
        """Affichage formaté de la période"""
        if self.periode_type == 'MENSUEL' and self.mois:
            from calendar import month_name
            import locale
            try:
                locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
            except:
                pass
            return f"{month_name[self.mois].capitalize()} {self.annee}"
        elif self.periode_type == 'TRIMESTRIEL' and self.trimestre:
            return f"{self.trimestre}ᵉ trimestre {self.annee}"
        else:
            return str(self.annee)

    def calculer_depuis_fiches(self):
        """
        Calcule les montants depuis les fiches de salaire validées
        de la période concernée.
        """
        from django.db.models import Sum, Count

        # Récupérer les fiches validées de la période
        fiches = FicheSalaire.objects.filter(
            employe__mandat=self.mandat,
            periode__gte=self.periode_debut,
            periode__lte=self.periode_fin,
            statut__in=['VALIDE', 'PAYE', 'COMPTABILISE']
        ).select_related('employe')

        # Agréger les données
        aggregats = fiches.aggregate(
            total_brut=Sum('salaire_brut_total'),
            # Part employé
            sum_avs_emp=Sum('avs_employe'),
            sum_ac_emp=Sum('ac_employe'),
            sum_ac_supp_emp=Sum('ac_supp_employe'),
            sum_lpp_emp=Sum('lpp_employe'),
            sum_laa_emp=Sum('laa_employe'),
            sum_laac_emp=Sum('laac_employe'),
            sum_ijm_emp=Sum('ijm_employe'),
            # Part employeur
            sum_avs_empr=Sum('avs_employeur'),
            sum_ac_empr=Sum('ac_employeur'),
            sum_lpp_empr=Sum('lpp_employeur'),
            sum_laa_empr=Sum('laa_employeur'),
            sum_af_empr=Sum('af_employeur'),
            # Effectifs
            nb_employes=Count('employe', distinct=True),
        )

        self.nombre_employes = aggregats['nb_employes'] or 0
        self.masse_salariale_brute = aggregats['total_brut'] or Decimal('0')
        self.masse_salariale_soumise = aggregats['total_brut'] or Decimal('0')

        # Calcul selon l'organisme
        if self.organisme == 'AVS':
            # AVS/AI/APG = 10.6% dont 5.3% employé et 5.3% employeur
            # AC = 2.2% dont 1.1% employé et 1.1% employeur
            avs_total = (aggregats['sum_avs_emp'] or Decimal('0')) + (aggregats['sum_avs_empr'] or Decimal('0'))
            ac_total = (aggregats['sum_ac_emp'] or Decimal('0')) + (aggregats['sum_ac_empr'] or Decimal('0'))

            # Répartition approximative AVS/AI/APG (8.7% / 1.4% / 0.5%)
            self.cotisation_avs = avs_total * Decimal('0.821')  # 8.7/10.6
            self.cotisation_ai = avs_total * Decimal('0.132')   # 1.4/10.6
            self.cotisation_apg = avs_total * Decimal('0.047')  # 0.5/10.6
            self.cotisation_ac = ac_total
            self.cotisation_ac_supp = (aggregats['sum_ac_supp_emp'] or Decimal('0')) * 2

            self.total_cotisations_employe = (aggregats['sum_avs_emp'] or Decimal('0')) + \
                                              (aggregats['sum_ac_emp'] or Decimal('0')) + \
                                              (aggregats['sum_ac_supp_emp'] or Decimal('0'))
            self.total_cotisations_employeur = (aggregats['sum_avs_empr'] or Decimal('0')) + \
                                                (aggregats['sum_ac_empr'] or Decimal('0'))
            self.montant_cotisations = self.total_cotisations_employe + self.total_cotisations_employeur

        elif self.organisme == 'LPP':
            self.cotisation_lpp_employe = aggregats['sum_lpp_emp'] or Decimal('0')
            self.cotisation_lpp_employeur = aggregats['sum_lpp_empr'] or Decimal('0')
            self.total_cotisations_employe = self.cotisation_lpp_employe
            self.total_cotisations_employeur = self.cotisation_lpp_employeur
            self.montant_cotisations = self.cotisation_lpp_employe + self.cotisation_lpp_employeur

        elif self.organisme == 'LAA':
            laa_emp = aggregats['sum_laa_emp'] or Decimal('0')
            laa_empr = aggregats['sum_laa_empr'] or Decimal('0')
            laac = aggregats['sum_laac_emp'] or Decimal('0')

            self.cotisation_laa_pro = laa_empr  # Généralement à charge de l'employeur
            self.cotisation_laa_non_pro = laa_emp  # Généralement à charge de l'employé
            self.cotisation_laac = laac
            self.total_cotisations_employe = laa_emp + laac
            self.total_cotisations_employeur = laa_empr
            self.montant_cotisations = laa_emp + laa_empr + laac

        elif self.organisme == 'AF':
            self.cotisation_af = aggregats['sum_af_empr'] or Decimal('0')
            self.total_cotisations_employe = Decimal('0')
            self.total_cotisations_employeur = self.cotisation_af
            self.montant_cotisations = self.cotisation_af

        elif self.organisme == 'IJM':
            self.cotisation_ijm = aggregats['sum_ijm_emp'] or Decimal('0')
            # IJM souvent partagé 50/50
            self.total_cotisations_employe = self.cotisation_ijm
            self.total_cotisations_employeur = self.cotisation_ijm
            self.montant_cotisations = self.cotisation_ijm * 2

        # Créer/mettre à jour les lignes par employé
        self._generer_lignes(fiches)

        # Mettre à jour le statut
        if self.statut == 'BROUILLON':
            self.statut = 'CALCULEE'

        self.save()
        return self

    def _generer_lignes(self, fiches):
        """Génère les lignes détaillées par employé"""
        from django.db.models import Sum

        # Supprimer les anciennes lignes
        self.lignes.all().delete()

        # Agréger par employé
        employes_data = fiches.values('employe').annotate(
            total_brut=Sum('salaire_brut_total'),
            avs_emp=Sum('avs_employe'),
            avs_empr=Sum('avs_employeur'),
            ac_emp=Sum('ac_employe'),
            ac_empr=Sum('ac_employeur'),
            ac_supp_emp=Sum('ac_supp_employe'),
            lpp_emp=Sum('lpp_employe'),
            lpp_empr=Sum('lpp_employeur'),
            laa_emp=Sum('laa_employe'),
            laa_empr=Sum('laa_employeur'),
            laac_emp=Sum('laac_employe'),
            ijm_emp=Sum('ijm_employe'),
            af_empr=Sum('af_employeur'),
        )

        for data in employes_data:
            employe = Employe.objects.get(pk=data['employe'])

            # Calculer les montants selon l'organisme
            if self.organisme == 'AVS':
                cotisation_employe = (data['avs_emp'] or 0) + (data['ac_emp'] or 0) + (data['ac_supp_emp'] or 0)
                cotisation_employeur = (data['avs_empr'] or 0) + (data['ac_empr'] or 0)
            elif self.organisme == 'LPP':
                cotisation_employe = data['lpp_emp'] or 0
                cotisation_employeur = data['lpp_empr'] or 0
            elif self.organisme == 'LAA':
                cotisation_employe = (data['laa_emp'] or 0) + (data['laac_emp'] or 0)
                cotisation_employeur = data['laa_empr'] or 0
            elif self.organisme == 'AF':
                cotisation_employe = 0
                cotisation_employeur = data['af_empr'] or 0
            elif self.organisme == 'IJM':
                cotisation_employe = data['ijm_emp'] or 0
                cotisation_employeur = data['ijm_emp'] or 0  # Même montant supposé
            else:
                cotisation_employe = 0
                cotisation_employeur = 0

            DeclarationCotisationsLigne.objects.create(
                declaration=self,
                employe=employe,
                salaire_brut=data['total_brut'] or 0,
                salaire_soumis=data['total_brut'] or 0,
                cotisation_employe=cotisation_employe,
                cotisation_employeur=cotisation_employeur,
                cotisation_totale=cotisation_employe + cotisation_employeur,
            )

    def calculer_echeance(self):
        """Calcule la date d'échéance selon l'organisme et la période"""
        from datetime import date
        from dateutil.relativedelta import relativedelta

        # Par défaut, échéance à M+1 le 10 du mois
        if self.periode_type == 'MENSUEL':
            self.date_echeance = self.periode_fin + relativedelta(months=1, day=10)
        elif self.periode_type == 'TRIMESTRIEL':
            self.date_echeance = self.periode_fin + relativedelta(months=1, day=15)
        else:
            self.date_echeance = date(self.annee + 1, 1, 31)

        self.save(update_fields=['date_echeance'])

    def marquer_transmise(self, date_transmission=None):
        """Marque la déclaration comme transmise"""
        from datetime import date

        if self.statut not in ['CALCULEE', 'VERIFIEE']:
            raise ValueError("La déclaration doit être calculée ou vérifiée avant transmission")

        self.date_transmission = date_transmission or date.today()
        self.statut = 'TRANSMISE'
        self.save()

    def marquer_payee(self, date_paiement=None):
        """Marque la déclaration comme payée"""
        from datetime import date

        self.date_paiement = date_paiement or date.today()
        self.statut = 'PAYEE'
        self.save()

    def generer_pdf(self):
        """Génère le PDF de la déclaration"""
        from django.core.files.base import ContentFile
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=10*mm
        )

        elements = []

        # Titre
        elements.append(Paragraph(
            f"DÉCLARATION DE COTISATIONS - {self.get_organisme_display()}",
            title_style
        ))
        elements.append(Spacer(1, 5*mm))

        # Informations employeur
        client = self.mandat.client
        info_data = [
            ['Employeur:', client.raison_sociale],
            ['N° IDE:', client.numero_ide or '-'],
            ['N° affilié:', self.numero_affilie or '-'],
            ['Période:', f"{self.periode_debut.strftime('%d.%m.%Y')} au {self.periode_fin.strftime('%d.%m.%Y')}"],
        ]

        info_table = Table(info_data, colWidths=[40*mm, 100*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 10*mm))

        # Récapitulatif
        recap_data = [
            ['RÉCAPITULATIF', ''],
            ['Nombre d\'employés:', str(self.nombre_employes)],
            ['Masse salariale brute:', f"{self.masse_salariale_brute:,.2f} CHF".replace(',', "'")],
            ['Masse salariale soumise:', f"{self.masse_salariale_soumise:,.2f} CHF".replace(',', "'")],
        ]

        # Ajouter détails selon organisme
        if self.organisme == 'AVS':
            recap_data.extend([
                ['', ''],
                ['Cotisation AVS:', f"{self.cotisation_avs:,.2f} CHF".replace(',', "'")],
                ['Cotisation AI:', f"{self.cotisation_ai:,.2f} CHF".replace(',', "'")],
                ['Cotisation APG:', f"{self.cotisation_apg:,.2f} CHF".replace(',', "'")],
                ['Cotisation AC:', f"{self.cotisation_ac:,.2f} CHF".replace(',', "'")],
            ])
            if self.cotisation_ac_supp > 0:
                recap_data.append(['Cotisation AC suppl.:', f"{self.cotisation_ac_supp:,.2f} CHF".replace(',', "'")])
            if self.frais_administration > 0:
                recap_data.append(['Frais administration:', f"{self.frais_administration:,.2f} CHF".replace(',', "'")])
        elif self.organisme == 'LPP':
            recap_data.extend([
                ['', ''],
                ['Cotisation employé:', f"{self.cotisation_lpp_employe:,.2f} CHF".replace(',', "'")],
                ['Cotisation employeur:', f"{self.cotisation_lpp_employeur:,.2f} CHF".replace(',', "'")],
            ])
        elif self.organisme == 'LAA':
            recap_data.extend([
                ['', ''],
                ['LAA professionnelle:', f"{self.cotisation_laa_pro:,.2f} CHF".replace(',', "'")],
                ['LAA non professionnelle:', f"{self.cotisation_laa_non_pro:,.2f} CHF".replace(',', "'")],
            ])
            if self.cotisation_laac > 0:
                recap_data.append(['LAAC complémentaire:', f"{self.cotisation_laac:,.2f} CHF".replace(',', "'")])
        elif self.organisme == 'AF':
            recap_data.append(['Cotisation AF:', f"{self.cotisation_af:,.2f} CHF".replace(',', "'")])
        elif self.organisme == 'IJM':
            recap_data.append(['Cotisation IJM:', f"{self.cotisation_ijm:,.2f} CHF".replace(',', "'")])

        recap_data.extend([
            ['', ''],
            ['Part employé:', f"{self.total_cotisations_employe:,.2f} CHF".replace(',', "'")],
            ['Part employeur:', f"{self.total_cotisations_employeur:,.2f} CHF".replace(',', "'")],
            ['TOTAL À PAYER:', f"{self.montant_cotisations:,.2f} CHF".replace(',', "'")],
        ])

        recap_table = Table(recap_data, colWidths=[60*mm, 60*mm])
        recap_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        elements.append(recap_table)
        elements.append(Spacer(1, 10*mm))

        # Détail par employé
        elements.append(Paragraph('DÉTAIL PAR EMPLOYÉ', styles['Heading2']))
        elements.append(Spacer(1, 3*mm))

        lignes = self.lignes.select_related('employe').order_by('employe__nom')
        if lignes.exists():
            emp_data = [['N° AVS', 'Nom Prénom', 'Salaire', 'Part emp.', 'Part empr.', 'Total']]
            for ligne in lignes:
                emp_data.append([
                    ligne.employe.avs_number,
                    f"{ligne.employe.nom} {ligne.employe.prenom}",
                    f"{ligne.salaire_brut:,.0f}".replace(',', "'"),
                    f"{ligne.cotisation_employe:,.2f}".replace(',', "'"),
                    f"{ligne.cotisation_employeur:,.2f}".replace(',', "'"),
                    f"{ligne.cotisation_totale:,.2f}".replace(',', "'"),
                ])

            emp_table = Table(emp_data, colWidths=[35*mm, 50*mm, 25*mm, 25*mm, 25*mm, 25*mm])
            emp_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 3),
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ]))
            elements.append(emp_table)

        # Construire le PDF
        doc.build(elements)

        # Sauvegarder
        pdf_content = buffer.getvalue()
        buffer.close()

        filename = f"declaration_{self.organisme}_{self.annee}_{self.mois or self.trimestre or 'annuel'}_{self.mandat.numero}.pdf"
        self.fichier_declaration.save(filename, ContentFile(pdf_content), save=True)

        return self.fichier_declaration


class DeclarationCotisationsLigne(BaseModel):
    """Ligne détaillée de déclaration par employé"""

    declaration = models.ForeignKey(
        DeclarationCotisations,
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name='Déclaration'
    )
    employe = models.ForeignKey(
        Employe,
        on_delete=models.CASCADE,
        related_name='lignes_declarations',
        verbose_name='Employé'
    )

    # Salaires
    salaire_brut = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Salaire brut',
        help_text='Total salaire brut sur la période'
    )
    salaire_soumis = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Salaire soumis',
        help_text='Salaire soumis à cotisation'
    )

    # Cotisations
    cotisation_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Cotisation employé',
        help_text='Part employé'
    )
    cotisation_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Cotisation employeur',
        help_text='Part employeur'
    )
    cotisation_totale = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Cotisation totale',
        help_text='Total (employé + employeur)'
    )

    class Meta:
        db_table = 'declarations_cotisations_lignes'
        verbose_name = 'Ligne de déclaration'
        verbose_name_plural = 'Lignes de déclaration'
        unique_together = ['declaration', 'employe']

    def __str__(self):
        return f"{self.declaration} - {self.employe}"


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