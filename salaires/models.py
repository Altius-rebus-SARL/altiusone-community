# apps/salaires/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel, Mandat, User, Adresse
from core.storage import SalairesStorage
from decimal import Decimal
from django.db.models import Q
from django.core.validators import RegexValidator
from django_countries.fields import CountryField

class Employe(BaseModel):
    """Employé d'un mandat client"""
    
    SEXE_CHOICES = [
        ('M', _('Masculin')),
        ('F', _('Féminin')),
        ('X', _('Autre')),
    ]
    
    STATUT_CHOICES = [
        ('ACTIF', _('Actif')),
        ('SUSPENDU', _('Suspendu')),
        ('CONGE', _('En congé')),
        ('DEMISSION', _('Démission')),
        ('LICENCIE', _('Licencié')),
        ('RETRAITE', _('Retraité')),
    ]
    
    TYPE_CONTRAT_CHOICES = [
        ('CDI', _('Contrat durée indéterminée')),
        ('CDD', _('Contrat durée déterminée')),
        ('APPRENTI', _('Apprentissage')),
        ('STAGE', _('Stage')),
        ('TEMPORAIRE', _('Temporaire')),
    ]
    
    # Identification
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='employes',
        verbose_name=_('Mandat'),
        help_text=_('Mandat employeur')
    )
    matricule = models.CharField(
        max_length=50, db_index=True,
        verbose_name=_('Matricule'),
        help_text=_('Numéro d\'identification interne')
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
        verbose_name=_('Nom'),
        help_text=_('Nom de famille')
    )
    prenom = models.CharField(
        max_length=100,
        verbose_name=_('Prénom'),
        help_text=_('Prénom(s)')
    )
    nom_naissance = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Nom de naissance'),
        help_text=_('Nom de famille à la naissance (si différent)')
    )
    date_naissance = models.DateField(
        verbose_name=_('Date de naissance'),
        help_text=_('Date de naissance de l\'employé')
    )
    lieu_naissance = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Lieu de naissance'),
        help_text=_('Ville et pays de naissance')
    )
    nationalite = CountryField(
        verbose_name=_('Nationalité'),
        help_text=_('Nationalité de l\'employé')
    )
    sexe = models.CharField(
        max_length=1, choices=SEXE_CHOICES,
        verbose_name=_('Sexe'),
        help_text=_('Sexe de l\'employé')
    )
    
    # Numéros officiels
    avs_number = models.CharField(
        _('Numéro AVS'),
        max_length=16,
        unique=True,
        validators=[RegexValidator(
            r'^\d{3}\.\d{4}\.\d{4}\.\d{2}$',
            'Format AVS invalide (756.1234.5678.90)'
        )],
        help_text=_('Format: 756.1234.5678.90')
    )
    numero_permis = models.CharField(_('Numéro permis'), max_length=20, blank=True)
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
    date_validite_permis = models.DateField(_('Validité du permis'), null=True, blank=True)
    
    # Coordonnées
    adresse = models.ForeignKey(
        Adresse, on_delete=models.PROTECT,
        related_name='employes',
        verbose_name=_('Adresse'),
        help_text=_('Adresse de domicile')
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_('Email'),
        help_text=_('Adresse email personnelle')
    )
    telephone = models.CharField(
        max_length=20, blank=True,
        verbose_name=_('Téléphone'),
        help_text=_('Numéro de téléphone fixe')
    )
    mobile = models.CharField(
        max_length=20, blank=True,
        verbose_name=_('Mobile'),
        help_text=_('Numéro de téléphone portable')
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
        verbose_name=_('État civil'),
        help_text=_('Situation matrimoniale')
    )
    nombre_enfants = models.IntegerField(
        default=0,
        verbose_name=_('Nombre d\'enfants'),
        help_text=_('Nombre d\'enfants à charge')
    )
    conjoint_travaille = models.BooleanField(
        _('Conjoint actif'),
        default=False,
        help_text=_('Le conjoint exerce-t-il une activité lucrative?')
    )
    revenus_conjoint = models.DecimalField(
        _('Revenus annuels du conjoint'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Pour détermination du barème IS')
    )
    
    # Emploi
    type_contrat = models.CharField(
        max_length=20, choices=TYPE_CONTRAT_CHOICES,
        verbose_name=_('Type de contrat'),
        help_text=_('Nature du contrat de travail')
    )
    date_entree = models.DateField(
        db_index=True,
        verbose_name=_('Date d\'entrée'),
        help_text=_('Date de début du contrat')
    )
    date_sortie = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_('Date de sortie'),
        help_text=_('Date de fin du contrat')
    )
    date_fin_periode_essai = models.DateField(
        null=True, blank=True,
        verbose_name=_('Fin période d\'essai'),
        help_text=_('Date de fin de la période d\'essai')
    )

    fonction = models.CharField(
        max_length=100,
        verbose_name=_('Fonction'),
        help_text=_('Intitulé du poste')
    )
    departement = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Département'),
        help_text=_('Service ou département')
    )

    taux_occupation = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
        verbose_name=_('Taux d\'occupation'),
        help_text=_('Taux en % (100 = temps plein)')
    )

    # Régime fiscal
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='employes',
        verbose_name=_('Régime fiscal'),
        help_text=_('Régime fiscal pour le calcul des charges sociales')
    )

    # Salaire
    devise_salaire = models.ForeignKey(
        'core.Devise', on_delete=models.PROTECT,
        related_name='employes',
        verbose_name=_('Devise du salaire'),
        help_text=_('Devise de versement du salaire')
    )
    salaire_brut_mensuel = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name=_('Salaire brut mensuel'),
        help_text=_('Salaire brut mensuel')
    )
    salaire_horaire = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Salaire horaire'),
        help_text=_('Salaire horaire (si applicable)')
    )

    nombre_heures_semaine = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=_('Heures par semaine'),
        help_text=_('Nombre d\'heures de travail hebdomadaires')
    )
    jours_vacances_annuel = models.IntegerField(
        verbose_name=_('Jours de vacances'),
        help_text=_('Nombre de jours de vacances annuels')
    )

    # 13ème salaire
    treizieme_salaire = models.BooleanField(
        default=True,
        verbose_name=_('13ème salaire'),
        help_text=_('L\'employé bénéficie-t-il d\'un 13ème salaire ?')
    )
    montant_13eme = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Montant 13ème'),
        help_text=_('Montant du 13ème salaire (si différent du salaire mensuel)')
    )

    # Paiement
    iban = models.CharField(
        max_length=34, blank=True,
        verbose_name=_('IBAN'),
        help_text=_('Numéro IBAN pour le versement du salaire')
    )
    banque = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Banque'),
        help_text=_('Nom de l\'établissement bancaire')
    )

    # Statut
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        default='ACTIF', db_index=True,
        verbose_name=_('Statut'),
        help_text=_('Statut actuel de l\'employé')
    )
    
    # Impôt à la source
    soumis_is = models.BooleanField(_('Soumis impôt à la source'), default=False)
    barreme_is = models.CharField(_('Barème IS'), max_length=10, blank=True,
                                   help_text=_('Ex: A0, A1, B0, B1, C0, C1, etc.'))
    taux_is = models.DecimalField(_('Taux IS'), max_digits=5, decimal_places=2,
                                   null=True, blank=True)
    canton_imposition = models.CharField(
        _('Canton imposition IS'), max_length=2, blank=True,
        help_text=_('Canton pour le barème impôt source (ex: GE, VD, ZH)')
    )
    eglise_is = models.BooleanField(
        _('Impôt ecclésiastique'), default=False,
        help_text=_('Affecte le barème IS dans certains cantons')
    )
    nombre_enfants_is = models.IntegerField(
        _("Nombre d'enfants IS"), default=0,
        help_text=_("Nombre d'enfants pour le calcul du barème IS")
    )
    numero_securite_sociale = models.CharField(
        _('N° sécurité sociale'), max_length=50, blank=True,
        help_text=_('Numéro universel (N° AVS en CH, N° sécu en FR, INPS au Mali, etc.)')
    )
    
    # Configuration paie
    config_cotisations = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Configuration cotisations'),
        help_text=_('Paramétrage des cotisations sociales au format JSON')
    )

    # Notes
    remarques = models.TextField(
        blank=True,
        verbose_name=_('Remarques'),
        help_text=_('Notes et observations')
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            f"{self.prenom} {self.nom}",
            f"Matricule {self.matricule}",
            self.fonction,
            self.departement,
            self.remarques,
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'employes'
        verbose_name = _('Employé')
        unique_together = [['mandat', 'matricule']]
        ordering = ['nom', 'prenom']
        indexes = [
            models.Index(fields=['mandat', 'statut']),
            models.Index(fields=['avs_number']),
        ]
    
    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.matricule})"

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.date_sortie and self.date_entree and self.date_sortie < self.date_entree:
            errors['date_sortie'] = _("La date de sortie ne peut pas être antérieure à la date d'entrée.")
        if self.date_fin_periode_essai and self.date_entree and self.date_fin_periode_essai < self.date_entree:
            errors['date_fin_periode_essai'] = _("La fin de période d'essai ne peut pas être antérieure à la date d'entrée.")
        if self.salaire_brut_mensuel and self.salaire_brut_mensuel < 0:
            errors['salaire_brut_mensuel'] = _("Le salaire ne peut pas être négatif.")
        if errors:
            raise ValidationError(errors)

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
        ('NAISSANCE', _('Allocation de naissance')),
        ('ENFANT', _('Allocation pour enfant (0-16 ans)')),
        ('FORMATION', _('Allocation de formation (16-25 ans)')),
        ('AUCUNE', _('Pas d\'allocation')),
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
        _('Type d\'allocation'),
        max_length=20,
        choices=TYPE_ALLOCATION_CHOICES,
        default='ENFANT'
    )
    en_formation = models.BooleanField(
        _('En formation'),
        default=False,
        help_text=_('Suit une formation (apprentissage, études) - pour allocation formation jusqu\'à 25 ans')
    )
    date_fin_formation = models.DateField(
        _('Fin de formation prévue'),
        null=True,
        blank=True
    )

    # Garde et prise en charge
    garde_partagee = models.BooleanField(
        _('Garde partagée'),
        default=False,
        help_text=_('L\'enfant est en garde partagée avec l\'autre parent')
    )
    pourcentage_garde = models.IntegerField(
        _('% de garde'),
        default=100,
        help_text=_('Pourcentage de garde (100 si garde complète, 50 si partagée)')
    )
    autre_parent_recoit_allocation = models.BooleanField(
        _('Autre parent reçoit allocation'),
        default=False,
        help_text=_('L\'autre parent perçoit-il déjà des allocations pour cet enfant?')
    )

    # Montants (peuvent être personnalisés selon le canton)
    montant_allocation = models.DecimalField(
        _('Montant mensuel'),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Montant mensuel de l\'allocation (si différent du standard)')
    )

    remarques = models.TextField(blank=True)

    class Meta:
        db_table = 'enfants_employes'
        verbose_name = _('Enfant')
        verbose_name_plural = _('Enfants')
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

        Cherche d'abord dans AllocationFamiliale (DB), fallback sur les
        montants fédéraux minimaux si pas de configuration.
        """
        from datetime import date
        type_alloc = self.type_allocation or self.determiner_type_allocation()

        # Priorité 1 : DB (AllocationFamiliale)
        today = date.today()
        alloc = AllocationFamiliale.objects.filter(
            canton=canton,
            type_allocation=type_alloc,
            date_debut__lte=today,
            is_active=True,
        ).filter(
            Q(date_fin__isnull=True) | Q(date_fin__gte=today)
        ).order_by('-date_debut').first()
        if alloc:
            return alloc.montant

        # Priorité 2 : DB avec canton DEFAULT
        alloc_default = AllocationFamiliale.objects.filter(
            canton='DEFAULT',
            type_allocation=type_alloc,
            date_debut__lte=today,
            is_active=True,
        ).filter(
            Q(date_fin__isnull=True) | Q(date_fin__gte=today)
        ).order_by('-date_debut').first()
        if alloc_default:
            return alloc_default.montant

        # Fallback : montants fédéraux minimaux en dur (dernier recours)
        FALLBACK = {'ENFANT': 200, 'FORMATION': 250, 'NAISSANCE': 0}
        return FALLBACK.get(type_alloc, 0)


class TauxCotisation(BaseModel):
    """Taux de cotisations sociales"""

    TYPE_COTISATION_CHOICES = [
        # Suisse
        ('AVS', _('AVS/AI/APG')),
        ('AC', _('Assurance chômage')),
        ('AC_SUPP', _('AC supplément (>seuil plafond)')),
        ('LPP', _('LPP (2e pilier)')),
        ('LAA', _('LAA Accidents')),
        ('LAAC', _('LAAC Accidents complémentaire')),
        ('IJM', _('Indemnités journalières maladie')),
        ('AF', _('Allocations familiales')),
        # Cameroun (CEMAC / XAF)
        ('CNPS_VIE', _('CNPS Assurance vieillesse')),
        ('CNPS_AF', _('CNPS Allocations familiales')),
        ('CNPS_AT', _('CNPS Accidents du travail')),
        # Sénégal (UEMOA / XOF)
        ('CSS', _('CSS Sécurité sociale')),
        ('IPRES_GEN', _('IPRES Régime général')),
        ('IPRES_CAD', _('IPRES Régime cadre')),
        ('IPM', _('IPM Maladie')),
        ('CFCE', _('CFCE Formation professionnelle')),
        # Côte d'Ivoire (UEMOA / XOF)
        ('CNPS_CI_RET', _('CNPS-CI Retraite')),
        ('CNPS_CI_PF', _('CNPS-CI Prestations familiales')),
        ('CNPS_CI_AT', _('CNPS-CI Accidents du travail')),
        ('CMU_CI', _('CMU Couverture maladie universelle')),
        ('FNE', _('FNE Emploi')),
        # Mali (UEMOA / XOF)
        ('INPS_RET', _('INPS Retraite')),
        ('INPS_PF', _('INPS Prestations familiales')),
        ('INPS_AT', _('INPS Accidents du travail')),
        ('AMO_ML', _('AMO Assurance maladie obligatoire')),
        # Burkina Faso (UEMOA / XOF)
        ('CNSS_BF_RET', _('CNSS Retraite')),
        ('CNSS_BF_PF', _('CNSS Prestations familiales')),
        ('CNSS_BF_AT', _('CNSS Accidents du travail')),
        # Niger (UEMOA / XOF)
        ('CNSS_NE_RET', _('CNSS Retraite')),
        ('CNSS_NE_PF', _('CNSS Prestations familiales')),
        ('CNSS_NE_AT', _('CNSS Accidents du travail')),
        # Générique
        ('AUTRE', _('Autre cotisation')),
    ]

    REPARTITION_CHOICES = [
        ('EMPLOYEUR', _('Employeur uniquement')),
        ('EMPLOYE', _('Employé uniquement')),
        ('PARTAGE', _('Partagé employeur/employé')),
    ]

    type_cotisation = models.CharField(
        max_length=20, choices=TYPE_COTISATION_CHOICES,
        verbose_name=_('Type de cotisation'),
        help_text=_('Nature de la cotisation sociale')
    )
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='taux_cotisations',
        verbose_name=_('Régime fiscal'),
        help_text=_('Régime fiscal applicable pour ce taux')
    )
    devise = models.ForeignKey(
        'core.Devise', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='taux_cotisations',
        verbose_name=_('Devise'),
        help_text=_('Devise des seuils de salaire')
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_('Libellé'),
        help_text=_('Description de la cotisation')
    )

    # Taux
    taux_total = models.DecimalField(
        max_digits=5, decimal_places=4,
        verbose_name=_('Taux total'),
        help_text=_('Taux total en % (employeur + employé)')
    )
    taux_employeur = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        verbose_name=_('Taux employeur'),
        help_text=_('Part employeur en %')
    )
    taux_employe = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        verbose_name=_('Taux employé'),
        help_text=_('Part employé en %')
    )

    repartition = models.CharField(
        max_length=20, choices=REPARTITION_CHOICES,
        verbose_name=_('Répartition'),
        help_text=_('Mode de répartition de la cotisation')
    )

    # Limites
    salaire_min = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Salaire minimum'),
        help_text=_('Salaire minimum soumis à cotisation')
    )
    salaire_max = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Salaire maximum'),
        help_text=_('Plafond de salaire soumis')
    )

    # Validité
    date_debut = models.DateField(
        verbose_name=_('Date de début'),
        help_text=_('Date d\'entrée en vigueur')
    )
    date_fin = models.DateField(
        null=True, blank=True,
        verbose_name=_('Date de fin'),
        help_text=_('Date de fin de validité')
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_('Actif'),
        help_text=_('Indique si ce taux est actuellement applicable')
    )

    class Meta:
        db_table = 'taux_cotisations'
        verbose_name = _('Taux de cotisation')
        ordering = ['type_cotisation', '-date_debut']
        unique_together = [('type_cotisation', 'regime_fiscal', 'date_debut')]

    def __str__(self):
        regime = f" ({self.regime_fiscal})" if self.regime_fiscal_id else ""
        return f"{self.get_type_cotisation_display()} - {self.taux_total}%{regime}"

    def save(self, *args, **kwargs):
        # Auto-populate devise from regime_fiscal if not set
        if not self.devise_id and self.regime_fiscal_id:
            self.devise_id = self.regime_fiscal.devise_defaut_id
        super().save(*args, **kwargs)

    @classmethod
    def get_taux_actif(cls, type_cotisation, date, regime_fiscal=None):
        """Récupère le taux applicable à une date, optionnellement par régime"""
        qs = cls.objects.filter(
            type_cotisation=type_cotisation,
            date_debut__lte=date,
            actif=True
        ).filter(
            Q(date_fin__gte=date) | Q(date_fin__isnull=True)
        )
        if regime_fiscal is not None:
            qs = qs.filter(regime_fiscal=regime_fiscal)
        return qs.first()


class FicheSalaire(BaseModel):
    """Fiche de salaire mensuelle"""
    
    STATUT_CHOICES = [
        ('BROUILLON', _('Brouillon')),
        ('VALIDE', _('Validée')),
        ('PAYE', _('Payée')),
        ('COMPTABILISE', _('Comptabilisée')),
    ]
    
    # Identification
    employe = models.ForeignKey(
        Employe, on_delete=models.CASCADE,
        related_name='fiches_salaire',
        verbose_name=_('Employé'),
        help_text=_('Employé concerné')
    )
    devise = models.ForeignKey(
        'core.Devise', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='fiches_salaire',
        verbose_name=_('Devise'),
        help_text=_('Devise de la fiche de salaire')
    )
    numero_fiche = models.CharField(
        max_length=50, unique=True, db_index=True,
        verbose_name=_('Numéro de fiche'),
        help_text=_('Identifiant unique de la fiche')
    )

    # Période
    periode = models.DateField(
        db_index=True,
        verbose_name=_('Période'),
        help_text=_('Premier jour du mois concerné')
    )
    annee = models.IntegerField(
        verbose_name=_('Année'),
        help_text=_('Année de la fiche')
    )
    mois = models.IntegerField(
        verbose_name=_('Mois'),
        help_text=_('Mois de la fiche (1-12)')
    )

    # Présence
    jours_travailles = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Jours travaillés'),
        help_text=_('Nombre de jours effectivement travaillés')
    )
    heures_travaillees = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name=_('Heures travaillées'),
        help_text=_('Nombre d\'heures travaillées')
    )
    heures_supplementaires = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name=_('Heures supplémentaires'),
        help_text=_('Heures supplémentaires effectuées')
    )
    jours_absence = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Jours d\'absence'),
        help_text=_('Jours d\'absence (hors vacances et maladie)')
    )
    jours_vacances = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Jours de vacances'),
        help_text=_('Jours de vacances pris')
    )
    jours_maladie = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Jours de maladie'),
        help_text=_('Jours d\'absence pour maladie')
    )

    # Salaire brut
    salaire_base = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name=_('Salaire de base'),
        help_text=_('Salaire mensuel de base')
    )
    heures_supp_montant = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Montant heures supp.'),
        help_text=_('Rémunération des heures supplémentaires')
    )
    primes = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Primes'),
        help_text=_('Primes et bonus')
    )
    indemnites = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Indemnités'),
        help_text=_('Indemnités diverses')
    )
    treizieme_mois = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('13ème mois'),
        help_text=_('Part du 13ème salaire versée ce mois')
    )

    salaire_brut_total = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name=_('Salaire brut total'),
        help_text=_('Total du salaire brut')
    )
    
    # Cotisations salariales (part employé)
    avs_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('AVS/AI/APG'),
        help_text=_('Cotisation AVS/AI/APG employé')
    )
    ac_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('AC'),
        help_text=_('Assurance chômage employé')
    )
    ac_supp_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('AC supp.'),
        help_text=_('AC supplémentaire (salaires > seuil plafond)')
    )
    lpp_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('LPP'),
        help_text=_('Cotisation 2ème pilier employé')
    )
    laa_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('LAA'),
        help_text=_('Assurance accidents employé')
    )
    laac_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('LAAC'),
        help_text=_('Assurance accidents complémentaire')
    )
    ijm_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('IJM'),
        help_text=_('Indemnités journalières maladie employé')
    )

    total_cotisations_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Total cotisations employé'),
        help_text=_('Total des cotisations salariales')
    )

    # Impôt à la source
    impot_source = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Impôt à la source'),
        help_text=_('Retenue d\'impôt à la source')
    )

    # Autres déductions
    avance_salaire = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Avance sur salaire'),
        help_text=_('Retenue pour avance consentie')
    )
    saisie_salaire = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Saisie sur salaire'),
        help_text=_('Retenue pour saisie de salaire')
    )
    autres_deductions = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Autres déductions'),
        help_text=_('Autres retenues')
    )

    total_deductions = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Total déductions'),
        help_text=_('Total de toutes les déductions')
    )

    # Allocations
    allocations_familiales = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Allocations familiales'),
        help_text=_('Allocations familiales')
    )
    autres_allocations = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Autres allocations'),
        help_text=_('Autres allocations')
    )

    # Salaire net
    salaire_net = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name=_('Salaire net'),
        help_text=_('Salaire net à payer')
    )
    
    # Charges patronales (pour info)
    avs_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('AVS employeur'),
        help_text=_('Part patronale AVS/AI/APG')
    )
    ac_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('AC employeur'),
        help_text=_('Part patronale assurance chômage')
    )
    lpp_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('LPP employeur'),
        help_text=_('Part patronale 2ème pilier')
    )
    laa_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('LAA employeur'),
        help_text=_('Part patronale assurance accidents')
    )
    af_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('AF employeur'),
        help_text=_('Allocations familiales (charge patronale)')
    )

    total_charges_patronales = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Total charges patronales'),
        help_text=_('Total des charges employeur')
    )

    # Coût total employeur
    cout_total_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Coût total employeur'),
        help_text=_('Coût complet pour l\'employeur')
    )

    # Statut
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        default='BROUILLON', db_index=True,
        verbose_name=_('Statut'),
        help_text=_('État de la fiche de salaire')
    )

    date_validation = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Date de validation'),
        help_text=_('Date et heure de validation')
    )
    valide_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='+',
        verbose_name=_('Validé par'),
        help_text=_('Utilisateur ayant validé la fiche')
    )

    date_paiement = models.DateField(
        null=True, blank=True,
        verbose_name=_('Date de paiement'),
        help_text=_('Date effective du paiement')
    )

    # Fichier PDF
    fichier_pdf = models.FileField(
        upload_to='salaires/fiches/',
        storage=SalairesStorage(),
        max_length=500,
        null=True, blank=True,
        verbose_name=_('Fichier PDF'),
        help_text=_('Fiche de salaire au format PDF')
    )

    # Lien comptabilité
    ecriture_comptable = models.ForeignKey(
        'comptabilite.PieceComptable',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fiches_salaire',
        verbose_name=_('Pièce comptable'),
        help_text=_('Pièce comptable associée')
    )

    # Notes
    remarques = models.TextField(
        blank=True,
        verbose_name=_('Remarques'),
        help_text=_('Notes et observations')
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            f"Fiche salaire {self.numero_fiche}",
            f"{self.employe.prenom} {self.employe.nom}" if self.employe else '',
            f"{self.mois}/{self.annee}",
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'fiches_salaire'
        verbose_name = _('Fiche de salaire')
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

        # Auto-populate devise from employe if not set
        if not self.devise_id and self.employe_id:
            self.devise_id = self.employe.devise_salaire_id

        # Génération numéro
        if not self.numero_fiche:
            self.numero_fiche = f"SAL-{self.periode.strftime('%Y%m')}-{self.employe.matricule}"

        super().save(*args, **kwargs)

    def calculer(self):
        """
        Calcule tous les montants de la fiche.

        Utilise LigneCotisationFiche pour stocker les cotisations dynamiquement
        selon le régime fiscal (CH=AVS/AC/LPP, OHADA=CNPS/CSS/IPRES, etc.).
        Les champs legacy (avs_employe, lpp_employe...) sont remplis en parallèle
        pour la rétro-compatibilité suisse.
        """
        # Salaire brut total
        self.salaire_brut_total = (
            self.salaire_base
            + self.heures_supp_montant
            + self.primes
            + self.indemnites
            + self.treizieme_mois
        )

        # ── Cotisations dynamiques via LigneCotisationFiche ──────────
        regime = getattr(self.employe, 'regime_fiscal', None)
        taux_list = TauxCotisation.objects.filter(
            is_active=True,
        ).filter(
            Q(regime_fiscal=regime) | Q(regime_fiscal__isnull=True)
        ).filter(
            Q(date_debut__lte=self.periode) & (Q(date_fin__isnull=True) | Q(date_fin__gte=self.periode))
        ).order_by('ordre')

        if regime:
            taux_list = taux_list.filter(regime_fiscal=regime)

        # Supprimer les anciennes lignes et recalculer
        self.lignes_cotisations.all().delete()

        total_employe = Decimal('0')
        total_employeur = Decimal('0')

        # Mapping legacy CH pour rétro-compatibilité
        LEGACY_MAP_EMPLOYE = {
            'AVS': 'avs_employe', 'AC': 'ac_employe', 'AC_SUPP': 'ac_supp_employe',
            'LPP': 'lpp_employe', 'LAA': 'laa_employe', 'LAAC': 'laac_employe',
            'IJM': 'ijm_employe',
        }
        LEGACY_MAP_EMPLOYEUR = {
            'AVS': 'avs_employeur', 'AC': 'ac_employeur', 'LPP': 'lpp_employeur',
            'LAA': 'laa_employeur', 'AF': 'af_employeur',
        }
        # Reset legacy fields
        for field in LEGACY_MAP_EMPLOYE.values():
            setattr(self, field, Decimal('0'))
        for field in LEGACY_MAP_EMPLOYEUR.values():
            setattr(self, field, Decimal('0'))

        for taux_obj in taux_list:
            mt_employe = self._calculer_cotisation_montant(taux_obj, 'employe')
            mt_employeur = self._calculer_cotisation_montant(taux_obj, 'employeur')

            if mt_employe > 0 or mt_employeur > 0:
                LigneCotisationFiche.objects.create(
                    fiche=self,
                    taux_cotisation=taux_obj,
                    libelle=taux_obj.libelle,
                    base_calcul=self.salaire_brut_total,
                    taux_employe=taux_obj.taux_employe,
                    taux_employeur=taux_obj.taux_employeur,
                    montant_employe=mt_employe,
                    montant_employeur=mt_employeur,
                    ordre=taux_obj.ordre,
                )
                total_employe += mt_employe
                total_employeur += mt_employeur

                # Remplir les champs legacy suisses
                type_cot = taux_obj.type_cotisation
                if type_cot in LEGACY_MAP_EMPLOYE:
                    setattr(self, LEGACY_MAP_EMPLOYE[type_cot], mt_employe)
                if type_cot in LEGACY_MAP_EMPLOYEUR:
                    setattr(self, LEGACY_MAP_EMPLOYEUR[type_cot], mt_employeur)

        self.total_cotisations_employe = total_employe
        self.total_charges_patronales = total_employeur

        # Allocations familiales auto-calculées si non renseignées manuellement
        if self.allocations_familiales == Decimal('0') and self.employe_id:
            self.allocations_familiales = self._calculer_allocations_familiales()

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

        # Coût total
        self.cout_total_employeur = (
            self.salaire_brut_total
            + self.total_charges_patronales
        )

        return self.salaire_net

    def _calculer_cotisation_montant(self, taux_obj, part):
        """
        Calcule le montant d'une cotisation pour un TauxCotisation donné.

        Gère les seuils (salaire_min/max) et le cas spécial AC_SUPP
        (cotisation sur la part au-dessus du seuil).
        """
        base = self.salaire_brut_total
        type_cot = taux_obj.type_cotisation

        if type_cot == 'AC_SUPP':
            # AC supplément suisse : s'applique sur la part au-dessus du seuil
            seuil_mensuel = taux_obj.salaire_min or Decimal('0')
            if seuil_mensuel <= 0 or base <= seuil_mensuel:
                return Decimal('0.00')
            base = base - seuil_mensuel
        else:
            if taux_obj.salaire_max and base > taux_obj.salaire_max:
                base = taux_obj.salaire_max
            if taux_obj.salaire_min and base < taux_obj.salaire_min:
                return Decimal('0.00')

        taux = taux_obj.taux_employe if part == 'employe' else taux_obj.taux_employeur
        if taux <= 0:
            return Decimal('0.00')
        return (base * taux / 100).quantize(Decimal('0.01'))

    def _calculer_allocations_familiales(self):
        """Calcule les allocations familiales basées sur les enfants de l'employé"""
        total = Decimal('0')
        canton = 'DEFAULT'
        if hasattr(self.employe, 'adresse') and self.employe.adresse_id:
            canton = getattr(self.employe.adresse, 'canton', 'DEFAULT') or 'DEFAULT'
        for enfant in self.employe.enfants.all():
            if enfant.autre_parent_recoit_allocation:
                continue
            montant = enfant.montant_allocation
            if not montant:
                montant = Decimal(str(enfant.get_montant_allocation_standard(canton)))
            if enfant.garde_partagee and enfant.pourcentage_garde < 100:
                montant = (montant * Decimal(str(enfant.pourcentage_garde)) / 100).quantize(Decimal('0.01'))
            total += montant
        return total

    def generer_pdf(self):
        """
        Génère le PDF de la fiche de salaire.

        Returns:
            FileField: Le fichier PDF généré et sauvegardé
        """
        from salaires.services.pdf_fiche_salaire import FicheSalairePDF
        from core.pdf import save_pdf_overwrite

        service = FicheSalairePDF(self)
        pdf_bytes = service.generer()

        filename = f"fiche_salaire_{self.numero_fiche}_{self.periode.strftime('%Y%m')}.pdf"
        return save_pdf_overwrite(self, 'fichier_pdf', pdf_bytes, filename)


class CertificatSalaire(BaseModel):
    """
    Certificat de salaire annuel - Formulaire 11 officiel suisse
    Conforme aux directives de l'Administration fédérale des contributions (AFC)
    """

    # Choix pour le type d'occupation (Section F)
    TYPE_OCCUPATION_CHOICES = [
        ('PLEIN_TEMPS', _('Plein temps')),
        ('TEMPS_PARTIEL', _('Temps partiel')),
        ('HORAIRE', _('Travail à l\'heure')),
    ]

    # Statut du certificat
    STATUT_CHOICES = [
        ('BROUILLON', _('Brouillon')),
        ('CALCULE', _('Calculé')),
        ('VERIFIE', _('Vérifié')),
        ('SIGNE', _('Signé')),
        ('ENVOYE', _('Envoyé')),
    ]

    # ==================== SECTION A-B: EMPLOYEUR ====================
    # (Les données employeur sont récupérées via employe.mandat.client)

    employe = models.ForeignKey(
        Employe, on_delete=models.CASCADE,
        related_name='certificats_salaire',
        verbose_name=_('Employé'),
        help_text=_('Employé concerné')
    )
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='certificats_salaire',
        verbose_name=_('Régime fiscal'),
        help_text=_('Régime fiscal applicable')
    )
    devise = models.ForeignKey(
        'core.Devise', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='certificats_salaire',
        verbose_name=_('Devise'),
        help_text=_('Devise du certificat')
    )
    annee = models.IntegerField(
        db_index=True,
        verbose_name=_('Année'),
        help_text=_('Année fiscale du certificat')
    )

    # ==================== SECTION C-E: PÉRIODE ET EMPLOYÉ ====================
    date_debut = models.DateField(
        verbose_name=_('Date de début'),
        help_text=_('Début de la période d\'emploi pour cette année (Section C)')
    )
    date_fin = models.DateField(
        verbose_name=_('Date de fin'),
        help_text=_('Fin de la période d\'emploi pour cette année (Section C)')
    )

    # ==================== SECTION F-G: OCCUPATION ET TRANSPORT ====================
    type_occupation = models.CharField(
        max_length=20, choices=TYPE_OCCUPATION_CHOICES, default='PLEIN_TEMPS',
        verbose_name=_('Type d\'occupation'),
        help_text=_('Section F: Type de rapport de travail')
    )
    taux_occupation = models.DecimalField(
        max_digits=5, decimal_places=2, default=100,
        verbose_name=_('Taux d\'occupation (%)'),
        help_text=_('Section F: Taux d\'occupation en pourcentage')
    )
    transport_public_disponible = models.BooleanField(
        default=True,
        verbose_name=_('Transport public disponible'),
        help_text=_('Section G: Des transports publics sont disponibles pour le trajet domicile-travail')
    )
    transport_gratuit_fourni = models.BooleanField(
        default=False,
        verbose_name=_('Transport gratuit fourni'),
        help_text=_('Section G: L\'employeur fournit un transport gratuit')
    )

    # ==================== CHIFFRE 1: SALAIRE ====================
    chiffre_1_salaire = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('1. Salaire / Rente'),
        help_text=_('Salaire, rente (y.c. allocations pour perte de gain)')
    )

    # ==================== CHIFFRE 2: PRESTATIONS EN NATURE ====================
    # 2.1 Repas
    chiffre_2_1_repas = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('2.1 Repas'),
        help_text=_('Valeur des repas gratuits')
    )
    repas_midi_gratuit = models.BooleanField(
        default=False,
        verbose_name=_('Repas de midi gratuit'),
        help_text=_('Case 2.1: L\'employé bénéficie de repas de midi gratuits')
    )
    repas_soir_gratuit = models.BooleanField(
        default=False,
        verbose_name=_('Repas du soir gratuit'),
        help_text=_('Case 2.1: L\'employé bénéficie de repas du soir gratuits')
    )

    # 2.2 Voiture de service
    chiffre_2_2_voiture = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('2.2 Véhicule de service'),
        help_text=_('Valeur de l\'utilisation privée du véhicule (0.9% par mois du prix d\'achat)')
    )
    voiture_disponible = models.BooleanField(
        default=False,
        verbose_name=_('Voiture de service disponible'),
        help_text=_('Case 2.2: Un véhicule de service est mis à disposition pour usage privé')
    )
    voiture_prix_achat = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('Prix d\'achat du véhicule'),
        help_text=_('Prix d\'achat du véhicule (hors TVA) pour calcul de la part privée')
    )

    # 2.3 Autres prestations
    chiffre_2_3_autres = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('2.3 Autres prestations en nature'),
        help_text=_('Autres prestations en nature (logement, etc.)')
    )
    autres_prestations_nature_detail = models.TextField(
        blank=True,
        verbose_name=_('Détail autres prestations'),
        help_text=_('Description des autres prestations en nature')
    )

    # ==================== CHIFFRE 3: PRESTATIONS IRRÉGULIÈRES ====================
    chiffre_3_irregulier = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('3. Prestations irrégulières'),
        help_text=_('Bonus, gratifications, 13ème salaire, indemnités de vacances non prises')
    )

    # ==================== CHIFFRE 4: PRESTATIONS EN CAPITAL ====================
    chiffre_4_capital = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('4. Prestations en capital'),
        help_text=_('Indemnités de départ, prestations provenant d\'institutions de prévoyance')
    )

    # ==================== CHIFFRE 5: PARTICIPATIONS ====================
    chiffre_5_participations = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('5. Droits de participation'),
        help_text=_('Actions de collaborateurs, options, etc.')
    )
    participations_detail = models.TextField(
        blank=True,
        verbose_name=_('Détail participations'),
        help_text=_('Description des participations (type, nombre, valeur)')
    )

    # ==================== CHIFFRE 6: CONSEIL D'ADMINISTRATION ====================
    chiffre_6_ca = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('6. Conseil d\'administration'),
        help_text=_('Indemnités de membre d\'organe de direction')
    )

    # ==================== CHIFFRE 7: AUTRES PRESTATIONS ====================
    chiffre_7_autres = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('7. Autres prestations'),
        help_text=_('Toutes autres prestations non mentionnées ailleurs')
    )
    autres_prestations_detail = models.TextField(
        blank=True,
        verbose_name=_('Détail autres prestations'),
        help_text=_('Description des autres prestations')
    )

    # ==================== CHIFFRE 8: TOTAL BRUT (CALCULÉ) ====================
    chiffre_8_total_brut = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('8. Salaire brut total'),
        help_text=_('Total des chiffres 1 à 7 (calculé automatiquement)')
    )

    # ==================== CHIFFRE 9: COTISATIONS AVS/AI/APG/AC/AANP ====================
    chiffre_9_cotisations = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('9. Cotisations AVS/AI/APG/AC/AANP'),
        help_text=_('Cotisations employé aux assurances sociales obligatoires')
    )

    # ==================== CHIFFRE 10: PRÉVOYANCE PROFESSIONNELLE ====================
    chiffre_10_1_lpp_ordinaire = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('10.1 LPP cotisations ordinaires'),
        help_text=_('Cotisations ordinaires à la prévoyance professionnelle')
    )
    chiffre_10_2_lpp_rachat = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('10.2 LPP rachats'),
        help_text=_('Rachats d\'années de cotisation LPP')
    )

    # ==================== CHIFFRE 11: SALAIRE NET (CALCULÉ) ====================
    chiffre_11_net = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('11. Salaire net'),
        help_text=_('Chiffre 8 moins chiffres 9 et 10 (calculé automatiquement)')
    )

    # ==================== CHIFFRE 12: FRAIS DE TRANSPORT ====================
    chiffre_12_transport = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('12. Frais effectifs de transport'),
        help_text=_('Frais de déplacement domicile-lieu de travail remboursés')
    )

    # ==================== CHIFFRE 13: FRAIS DE REPAS ET NUITÉES ====================
    chiffre_13_1_1_repas_effectif = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('13.1.1 Frais de repas effectifs'),
        help_text=_('Frais de repas effectifs pour travail en dehors')
    )
    chiffre_13_1_2_repas_forfait = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('13.1.2 Frais de repas forfaitaires'),
        help_text=_('Indemnité forfaitaire pour repas de midi')
    )
    chiffre_13_2_nuitees = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('13.2 Nuitées'),
        help_text=_('Frais d\'hébergement pour déplacements professionnels')
    )
    chiffre_13_3_repas_externes = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('13.3 Repas à l\'extérieur'),
        help_text=_('Frais de repas lors de déplacements externes')
    )

    # ==================== CHIFFRE 14: AUTRES FRAIS ====================
    chiffre_14_autres_frais = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('14. Autres frais'),
        help_text=_('Autres frais professionnels remboursés')
    )
    autres_frais_detail = models.TextField(
        blank=True,
        verbose_name=_('Détail autres frais'),
        help_text=_('Description des autres frais professionnels')
    )

    # ==================== CHIFFRE 15: JOURS DE TRAVAIL AVEC DÉPLACEMENT ====================
    chiffre_15_jours_transport = models.IntegerField(
        default=0,
        verbose_name=_('15. Jours avec déplacement'),
        help_text=_('Nombre de jours de travail avec déplacement domicile-travail')
    )

    # ==================== SECTION I: REMARQUES ====================
    remarques = models.TextField(
        blank=True,
        verbose_name=_('Remarques'),
        help_text=_('Section I: Remarques diverses (expatriés, détachés, etc.)')
    )

    # ==================== SIGNATURE ====================
    lieu_signature = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Lieu de signature'),
        help_text=_('Lieu où le certificat est signé')
    )
    date_signature = models.DateField(
        null=True, blank=True,
        verbose_name=_('Date de signature'),
        help_text=_('Date de signature du certificat')
    )
    nom_signataire = models.CharField(
        max_length=200, blank=True,
        verbose_name=_('Nom du signataire'),
        help_text=_('Nom de la personne autorisée à signer')
    )
    telephone_signataire = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Téléphone du signataire'),
        help_text=_('Numéro de téléphone pour questions')
    )
    est_signe = models.BooleanField(
        default=False,
        verbose_name=_('Signé'),
        help_text=_('Indique si le certificat a été signé')
    )

    # ==================== STATUT ET MÉTADONNÉES ====================
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='BROUILLON',
        verbose_name=_('Statut'),
        help_text=_('État actuel du certificat')
    )

    # ==================== CHAMPS LEGACY (maintenu pour compatibilité) ====================
    salaire_brut_annuel = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('Salaire brut annuel (legacy)'),
        help_text=_('[Obsolète] Utiliser chiffre_1_salaire')
    )
    treizieme_salaire_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('13ème salaire annuel (legacy)'),
        help_text=_('[Obsolète] Inclus dans chiffre_3_irregulier')
    )
    primes_annuelles = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Primes annuelles (legacy)'),
        help_text=_('[Obsolète] Inclus dans chiffre_3_irregulier')
    )
    avs_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('AVS annuel (legacy)'),
        help_text=_('[Obsolète] Utiliser chiffre_9_cotisations')
    )
    ac_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('AC annuel (legacy)'),
        help_text=_('[Obsolète] Inclus dans chiffre_9_cotisations')
    )
    lpp_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('LPP annuel (legacy)'),
        help_text=_('[Obsolète] Utiliser chiffre_10_1_lpp_ordinaire')
    )
    allocations_familiales_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Allocations familiales annuelles (legacy)'),
        help_text=_('[Obsolète] Les allocations ne figurent pas sur le formulaire 11')
    )
    frais_deplacement = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Frais de déplacement (legacy)'),
        help_text=_('[Obsolète] Utiliser chiffre_12_transport')
    )
    frais_repas = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Frais de repas (legacy)'),
        help_text=_('[Obsolète] Utiliser chiffre_13_*')
    )
    impot_source_annuel = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Impôt à la source annuel'),
        help_text=_('Total impôt à la source retenu (info uniquement, pas sur formulaire 11)')
    )

    # ==================== FICHIER PDF ====================
    fichier_pdf = models.FileField(
        upload_to='salaires/certificats/',
        storage=SalairesStorage(),
        max_length=500,
        null=True, blank=True,
        verbose_name=_('Fichier PDF'),
        help_text=_('Certificat de salaire au format PDF')
    )

    date_generation = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de génération'),
        help_text=_('Date de création du certificat')
    )
    genere_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        verbose_name=_('Généré par'),
        help_text=_('Utilisateur ayant généré le certificat')
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            f"Certificat salaire {self.annee}",
            f"{self.employe.prenom} {self.employe.nom}" if self.employe else '',
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'certificats_salaire'
        verbose_name = _('Certificat de salaire')
        verbose_name_plural = _('Certificats de salaire')
        unique_together = [['employe', 'annee']]
        ordering = ['-annee']

    def __str__(self):
        return f"Certificat {self.annee} - {self.employe}"

    def save(self, *args, **kwargs):
        """Recalcule les totaux avant sauvegarde"""
        # Auto-populate regime_fiscal and devise from employe
        if self.employe_id:
            if not self.regime_fiscal_id:
                self.regime_fiscal_id = getattr(self.employe, 'regime_fiscal_id', None) or \
                    getattr(self.employe.mandat, 'regime_fiscal_id', None)
            if not self.devise_id:
                self.devise_id = self.employe.devise_salaire_id
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

        Returns:
            FileField: Le fichier PDF généré et sauvegardé
        """
        from salaires.services.pdf_certificat_salaire import CertificatSalairePDF
        from core.pdf import save_pdf_overwrite

        service = CertificatSalairePDF(self)
        pdf_bytes = service.generer()

        filename = f"certificat_salaire_f11_{self.employe.matricule}_{self.annee}.pdf"
        return save_pdf_overwrite(self, 'fichier_pdf', pdf_bytes, filename)


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
        ('AVS', _('Caisse AVS/AI/APG/AC')),
        ('LPP', _('Institution de prévoyance LPP')),
        ('LAA', _('Assurance accidents LAA/LAAC')),
        ('AF', _('Caisse allocations familiales')),
        ('IJM', _('Assurance indemnités journalières maladie')),
    ]

    PERIODE_TYPE_CHOICES = [
        ('MENSUEL', _('Mensuelle')),
        ('TRIMESTRIEL', _('Trimestrielle')),
        ('ANNUEL', _('Annuelle')),
    ]

    STATUT_CHOICES = [
        ('BROUILLON', _('Brouillon')),
        ('CALCULEE', _('Calculée')),
        ('VERIFIEE', _('Vérifiée')),
        ('TRANSMISE', _('Transmise')),
        ('PAYEE', _('Payée')),
    ]

    # Identification
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='declarations_cotisations',
        verbose_name=_('Mandat'),
        help_text=_('Mandat employeur concerné')
    )
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='declarations_cotisations',
        verbose_name=_('Régime fiscal'),
        help_text=_('Régime fiscal applicable')
    )
    devise = models.ForeignKey(
        'core.Devise', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='declarations_cotisations',
        verbose_name=_('Devise'),
        help_text=_('Devise de la déclaration')
    )
    organisme = models.CharField(
        max_length=10, choices=ORGANISME_CHOICES,
        verbose_name=_('Organisme'),
        help_text=_('Organisme destinataire de la déclaration')
    )

    # Informations caisse (selon l'organisme)
    nom_caisse = models.CharField(
        max_length=200, blank=True,
        verbose_name=_('Nom de la caisse'),
        help_text=_('Dénomination officielle de la caisse')
    )
    numero_affilie = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('N° affilié'),
        help_text=_('Numéro d\'affiliation de l\'employeur')
    )
    numero_contrat = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('N° contrat/police'),
        help_text=_('Numéro de contrat ou police')
    )

    # Période
    periode_type = models.CharField(
        max_length=15, choices=PERIODE_TYPE_CHOICES,
        default='MENSUEL',
        verbose_name=_('Type de période'),
        help_text=_('Fréquence de déclaration')
    )
    periode_debut = models.DateField(
        verbose_name=_('Début de période'),
        help_text=_('Premier jour de la période déclarée')
    )
    periode_fin = models.DateField(
        verbose_name=_('Fin de période'),
        help_text=_('Dernier jour de la période déclarée')
    )
    annee = models.IntegerField(
        verbose_name=_('Année'),
        help_text=_('Année de la déclaration')
    )
    mois = models.IntegerField(
        null=True, blank=True,
        verbose_name=_('Mois'),
        help_text=_('Mois (1-12) pour déclaration mensuelle')
    )
    trimestre = models.IntegerField(
        null=True, blank=True,
        verbose_name=_('Trimestre'),
        help_text=_('Trimestre (1-4) pour déclaration trimestrielle')
    )

    # Effectifs
    nombre_employes = models.IntegerField(
        default=0,
        verbose_name=_('Nombre d\'employés'),
        help_text=_('Nombre d\'employés déclarés')
    )

    # Masse salariale
    masse_salariale_brute = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Masse salariale brute'),
        help_text=_('Total des salaires bruts')
    )
    masse_salariale_soumise = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Masse salariale soumise'),
        help_text=_('Total des salaires soumis à cotisation')
    )

    # Cotisations détaillées (selon organisme)
    # Pour AVS
    cotisation_avs = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('AVS'),
        help_text=_('Cotisation AVS (employeur + employé)')
    )
    cotisation_ai = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('AI'),
        help_text=_('Cotisation AI (employeur + employé)')
    )
    cotisation_apg = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('APG'),
        help_text=_('Cotisation APG (employeur + employé)')
    )
    cotisation_ac = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('AC'),
        help_text=_('Cotisation AC (employeur + employé)')
    )
    cotisation_ac_supp = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('AC supplémentaire'),
        help_text=_('AC sur salaires dépassant le seuil plafond')
    )
    frais_administration = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('Frais d\'administration'),
        help_text=_('Frais de gestion de la caisse')
    )

    # Pour LPP
    cotisation_lpp_employe = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('LPP employé'),
        help_text=_('Part employé LPP')
    )
    cotisation_lpp_employeur = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('LPP employeur'),
        help_text=_('Part employeur LPP')
    )

    # Pour LAA
    cotisation_laa_pro = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('LAA professionnelle'),
        help_text=_('Prime accidents professionnels')
    )
    cotisation_laa_non_pro = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('LAA non professionnelle'),
        help_text=_('Prime accidents non professionnels')
    )
    cotisation_laac = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('LAAC complémentaire'),
        help_text=_('Assurance accidents complémentaire')
    )

    # Pour AF
    cotisation_af = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('Allocations familiales'),
        help_text=_('Cotisation allocations familiales')
    )

    # Pour IJM
    cotisation_ijm = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('IJM'),
        help_text=_('Prime indemnités journalières maladie')
    )

    # Totaux
    total_cotisations_employe = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('Total part employé'),
        help_text=_('Total des cotisations part employé')
    )
    total_cotisations_employeur = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('Total part employeur'),
        help_text=_('Total des cotisations part employeur')
    )
    montant_cotisations = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('Montant total'),
        help_text=_('Total des cotisations dues')
    )

    # Dates et statut
    statut = models.CharField(
        max_length=15, choices=STATUT_CHOICES,
        default='BROUILLON', db_index=True,
        verbose_name=_('Statut'),
        help_text=_('État de la déclaration')
    )
    date_declaration = models.DateField(
        null=True, blank=True,
        verbose_name=_('Date de déclaration'),
        help_text=_('Date de création de la déclaration')
    )
    date_echeance = models.DateField(
        null=True, blank=True,
        verbose_name=_('Date d\'échéance'),
        help_text=_('Date limite de paiement')
    )
    date_transmission = models.DateField(
        null=True, blank=True,
        verbose_name=_('Date de transmission'),
        help_text=_('Date d\'envoi à la caisse')
    )
    date_paiement = models.DateField(
        null=True, blank=True,
        verbose_name=_('Date de paiement'),
        help_text=_('Date effective du paiement')
    )

    # Références
    numero_reference = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Numéro de référence'),
        help_text=_('Référence attribuée par l\'organisme')
    )
    numero_bvr = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('N° BVR/QR'),
        help_text=_('Numéro de référence de paiement')
    )
    iban_caisse = models.CharField(
        max_length=34, blank=True,
        verbose_name=_('IBAN caisse'),
        help_text=_('IBAN pour le paiement')
    )

    # Documents
    fichier_declaration = models.FileField(
        upload_to='salaires/declarations/',
        storage=SalairesStorage(),
        max_length=500,
        null=True, blank=True,
        verbose_name=_('Fichier déclaration'),
        help_text=_('Document de déclaration généré')
    )

    # Remarques
    remarques = models.TextField(
        blank=True,
        verbose_name=_('Remarques'),
        help_text=_('Notes et observations')
    )

    class Meta:
        db_table = 'declarations_cotisations'
        verbose_name = _('Déclaration de cotisations')
        verbose_name_plural = _('Déclarations de cotisations')
        ordering = ['-annee', '-periode_fin', 'organisme']
        unique_together = ['mandat', 'organisme', 'annee', 'mois', 'trimestre']

    def __str__(self):
        periode = f"{self.mois}/{self.annee}" if self.mois else f"T{self.trimestre}/{self.annee}" if self.trimestre else str(self.annee)
        return f"{self.get_organisme_display()} - {periode} - {self.mandat}"

    def save(self, *args, **kwargs):
        # Auto-populate regime_fiscal and devise from mandat
        if self.mandat_id:
            if not self.regime_fiscal_id:
                self.regime_fiscal_id = getattr(self.mandat, 'regime_fiscal_id', None)
            if not self.devise_id:
                self.devise_id = self.mandat.devise_id
        super().save(*args, **kwargs)

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
        from salaires.services.pdf_declaration import DeclarationCotisationsPDF
        from core.pdf import save_pdf_overwrite

        service = DeclarationCotisationsPDF(self)
        pdf_bytes = service.generer()

        filename = f"declaration_{self.organisme}_{self.annee}_{self.mois or self.trimestre or 'annuel'}_{self.mandat.numero}.pdf"
        return save_pdf_overwrite(self, 'fichier_declaration', pdf_bytes, filename)


class DeclarationCotisationsLigne(BaseModel):
    """Ligne détaillée de déclaration par employé"""

    declaration = models.ForeignKey(
        DeclarationCotisations,
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_('Déclaration')
    )
    employe = models.ForeignKey(
        Employe,
        on_delete=models.CASCADE,
        related_name='lignes_declarations',
        verbose_name=_('Employé')
    )

    # Salaires
    salaire_brut = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('Salaire brut'),
        help_text=_('Total salaire brut sur la période')
    )
    salaire_soumis = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_('Salaire soumis'),
        help_text=_('Salaire soumis à cotisation')
    )

    # Cotisations
    cotisation_employe = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Cotisation employé'),
        help_text=_('Part employé')
    )
    cotisation_employeur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Cotisation employeur'),
        help_text=_('Part employeur')
    )
    cotisation_totale = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Cotisation totale'),
        help_text=_('Total (employé + employeur)')
    )

    class Meta:
        db_table = 'declarations_cotisations_lignes'
        verbose_name = _('Ligne de déclaration')
        verbose_name_plural = _('Lignes de déclaration')
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
        ('COMPLET', _('Certificat complet (qualifié)')),
        ('SIMPLE', _('Attestation de travail (simple)')),
        ('INTERMEDIAIRE', _('Certificat intermédiaire')),
    ]

    MOTIF_DEPART_CHOICES = [
        ('DEMISSION', _('Démission')),
        ('FIN_CONTRAT', _('Fin de contrat')),
        ('LICENCIEMENT', _('Licenciement')),
        ('LICENCIEMENT_ECO', _('Licenciement économique')),
        ('RETRAITE', _('Retraite')),
        ('ACCORD_MUTUEL', _('Résiliation d\'un commun accord')),
        ('DECES', _('Décès')),
        ('', _('Non spécifié')),
    ]

    # Relations
    employe = models.ForeignKey(
        Employe,
        on_delete=models.CASCADE,
        related_name='certificats_travail'
    )
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='certificats_travail',
        verbose_name=_('Régime fiscal'),
        help_text=_('Régime fiscal applicable')
    )

    # Type et période
    type_certificat = models.CharField(
        _('Type de certificat'),
        max_length=20,
        choices=TYPE_CERTIFICAT_CHOICES,
        default='COMPLET'
    )
    date_debut_emploi = models.DateField(_('Date de début d\'emploi'))
    date_fin_emploi = models.DateField(_('Date de fin d\'emploi'), null=True, blank=True)

    # Informations professionnelles
    fonction_principale = models.CharField(_('Fonction principale'), max_length=150)
    departement = models.CharField(_('Département'), max_length=100, blank=True)
    taux_occupation = models.DecimalField(
        _('Taux d\'occupation (%)'),
        max_digits=5,
        decimal_places=2,
        default=100
    )

    # Description du poste et des tâches (pour certificat complet)
    description_taches = models.TextField(
        _('Description des tâches'),
        blank=True,
        help_text=_('Description détaillée des principales responsabilités et tâches')
    )

    # Évaluations (pour certificat complet - échelle standard suisse)
    # Échelle: 1=insuffisant, 2=satisfaisant, 3=bien, 4=très bien, 5=excellent
    NOTE_CHOICES = [
        (1, _('Insuffisant')),
        (2, _('Satisfaisant')),
        (3, _('Bien')),
        (4, _('Très bien')),
        (5, _('Excellent')),
    ]

    evaluation_qualite_travail = models.IntegerField(
        _('Qualité du travail'),
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_quantite_travail = models.IntegerField(
        _('Quantité de travail'),
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_competences = models.IntegerField(
        _('Compétences professionnelles'),
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_comportement = models.IntegerField(
        _('Comportement'),
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_relations = models.IntegerField(
        _('Relations avec collègues/clients'),
        choices=NOTE_CHOICES,
        null=True, blank=True
    )
    evaluation_autonomie = models.IntegerField(
        _('Autonomie et initiative'),
        choices=NOTE_CHOICES,
        null=True, blank=True
    )

    # Texte de l'évaluation (généré ou personnalisé)
    texte_evaluation = models.TextField(
        _('Texte d\'évaluation'),
        blank=True,
        help_text=_('Évaluation rédigée des performances et du comportement')
    )

    # Motif de départ
    motif_depart = models.CharField(
        _('Motif de départ'),
        max_length=20,
        choices=MOTIF_DEPART_CHOICES,
        blank=True
    )

    # Formule de fin (vœux pour l'avenir)
    formule_fin = models.TextField(
        _('Formule de fin'),
        blank=True,
        help_text=_('Remerciements et vœux pour l\'avenir')
    )

    # Informations complémentaires
    formations_suivies = models.TextField(
        _('Formations suivies'),
        blank=True,
        help_text=_('Formations internes ou externes suivies durant l\'emploi')
    )
    projets_speciaux = models.TextField(
        _('Projets spéciaux'),
        blank=True,
        help_text=_('Projets particuliers ou missions spéciales')
    )

    # Métadonnées
    date_demande = models.DateField(_('Date de demande'), null=True, blank=True)
    date_emission = models.DateField(_('Date d\'émission'), auto_now_add=True)
    emis_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='certificats_travail_emis'
    )

    # Fichier
    fichier_pdf = models.FileField(
        upload_to='salaires/certificats_travail/',
        storage=SalairesStorage(),
        max_length=500,
        null=True, blank=True
    )

    class Meta:
        db_table = 'certificats_travail'
        verbose_name = _('Certificat de travail')
        verbose_name_plural = _('Certificats de travail')
        ordering = ['-date_emission']

    def __str__(self):
        return f"Certificat travail - {self.employe} ({self.type_certificat})"

    def save(self, *args, **kwargs):
        # Auto-populate regime_fiscal from employe's mandat
        if not self.regime_fiscal_id and self.employe_id:
            self.regime_fiscal_id = getattr(self.employe.mandat, 'regime_fiscal_id', None)
        super().save(*args, **kwargs)

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
        from datetime import date
        from salaires.services.pdf_certificat_travail import CertificatTravailPDF
        from core.pdf import save_pdf_overwrite

        service = CertificatTravailPDF(self)
        pdf_bytes = service.generer()

        type_suffix = self.type_certificat.lower()
        filename = f"certificat_travail_{self.employe.matricule}_{type_suffix}_{date.today().strftime('%Y%m%d')}.pdf"
        return save_pdf_overwrite(self, 'fichier_pdf', pdf_bytes, filename)


# ══════════════════════════════════════════════════════════════
# LIGNES DE COTISATION — remplace les colonnes hardcodées sur FicheSalaire
# ══════════════════════════════════════════════════════════════

class LigneCotisationFiche(BaseModel):
    """
    Ligne de cotisation sur une fiche de salaire.

    Remplace les 15+ colonnes hardcodées suisses (avs_employe, ac_employe, etc.)
    par un modèle générique lié à TauxCotisation.
    Fonctionne pour tous les régimes : CH (AVS/AC/LPP), FR (URSSAF/CSG),
    OHADA (CNPS/IPRES/CSS), etc.
    """

    fiche = models.ForeignKey(
        FicheSalaire, on_delete=models.CASCADE,
        related_name='lignes_cotisations',
        verbose_name=_('Fiche de salaire')
    )
    taux_cotisation = models.ForeignKey(
        TauxCotisation, on_delete=models.PROTECT,
        related_name='lignes_fiches',
        verbose_name=_('Type de cotisation'),
        help_text=_('Référence au taux configuré (type, régime, taux)')
    )
    libelle = models.CharField(
        max_length=200, blank=True,
        verbose_name=_('Libellé'),
        help_text=_('Auto-rempli depuis TauxCotisation si vide')
    )
    base_calcul = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Base de calcul'),
        help_text=_('Salaire soumis à cette cotisation')
    )
    taux_employe = models.DecimalField(
        max_digits=6, decimal_places=3, default=0,
        verbose_name=_('Taux employé (%)')
    )
    taux_employeur = models.DecimalField(
        max_digits=6, decimal_places=3, default=0,
        verbose_name=_('Taux employeur (%)')
    )
    montant_employe = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Montant employé')
    )
    montant_employeur = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('Montant employeur')
    )
    ordre = models.IntegerField(default=0, verbose_name=_('Ordre'))

    class Meta:
        db_table = 'lignes_cotisation_fiche'
        verbose_name = _('Ligne de cotisation')
        verbose_name_plural = _('Lignes de cotisation')
        ordering = ['fiche', 'ordre']
        indexes = [
            models.Index(fields=['fiche', 'taux_cotisation']),
        ]

    def __str__(self):
        return f"{self.libelle or self.taux_cotisation.libelle} — {self.montant_employe + self.montant_employeur}"

    def save(self, *args, **kwargs):
        if not self.libelle and self.taux_cotisation_id:
            self.libelle = self.taux_cotisation.libelle
        super().save(*args, **kwargs)


class AllocationFamiliale(BaseModel):
    """
    Montants d'allocations familiales par canton/région.

    Remplace le dict MONTANTS hardcodé dans EnfantEmploye.get_montant_allocation_standard().
    Permet la mise à jour via l'interface sans modifier le code.
    """
    TYPE_CHOICES = [
        ('ENFANT', _("Allocation pour enfant")),
        ('FORMATION', _("Allocation de formation")),
        ('NAISSANCE', _("Allocation de naissance")),
        ('ADOPTION', _("Allocation d'adoption")),
    ]
    canton = models.CharField(
        max_length=5,
        verbose_name=_("Canton / Région"),
        help_text=_("Code canton (GE, VD, ZH…) ou 'DEFAULT' pour le minimum fédéral"),
    )
    type_allocation = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name=_("Type d'allocation"),
    )
    montant = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name=_("Montant mensuel"),
    )
    date_debut = models.DateField(
        verbose_name=_("Valide dès"),
        help_text=_("Date de début de validité de ce barème"),
    )
    date_fin = models.DateField(
        null=True, blank=True,
        verbose_name=_("Valide jusqu'au"),
        help_text=_("Laisser vide si toujours en vigueur"),
    )

    class Meta:
        db_table = 'allocations_familiales'
        verbose_name = _("Allocation familiale")
        verbose_name_plural = _("Allocations familiales")
        ordering = ['canton', 'type_allocation', '-date_debut']
        unique_together = ['canton', 'type_allocation', 'date_debut']

    def __str__(self):
        return f"{self.canton} — {self.get_type_allocation_display()}: {self.montant}"