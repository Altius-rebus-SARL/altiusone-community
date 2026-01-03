# apps/core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
import uuid


class BaseModel(models.Model):
    """Modèle abstrait de base pour tous les modèles"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL,
                                   null=True, related_name='+', verbose_name=_('Créé par'))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_('Actif'))

    class Meta:
        abstract = True
        ordering = ['-created_at']


class SwissCantons(models.TextChoices):
    """
    Liste des 26 cantons suisses avec leurs codes officiels à deux lettres.
    Les noms des cantons sont en français.
    """

    AG = "AG", _("Argovie")
    AI = "AI", _("Appenzell Rhodes-Intérieures")
    AR = "AR", _("Appenzell Rhodes-Extérieures")
    BE = "BE", _("Berne")
    BL = "BL", _("Bâle-Campagne")
    BS = "BS", _("Bâle-Ville")
    FR = "FR", _("Fribourg")
    GE = "GE", _("Genève")
    GL = "GL", _("Glaris")
    GR = "GR", _("Grisons")
    JU = "JU", _("Jura")
    LU = "LU", _("Lucerne")
    NE = "NE", _("Neuchâtel")
    NW = "NW", _("Nidwald")
    OW = "OW", _("Obwald")
    SG = "SG", _("Saint-Gall")
    SH = "SH", _("Schaffhouse")
    SO = "SO", _("Soleure")
    SZ = "SZ", _("Schwyz")
    TG = "TG", _("Thurgovie")
    TI = "TI", _("Tessin")
    UR = "UR", _("Uri")
    VD = "VD", _("Vaud")
    VS = "VS", _("Valais")
    ZG = "ZG", _("Zoug")
    ZH = "ZH", _("Zurich")


# =============================================================================
# DEVISE (CURRENCY)
# =============================================================================

class Devise(models.Model):
    """
    Devise monétaire pour l'internationalisation.

    Permet de gérer plusieurs devises avec leurs taux de change
    et paramètres de formatage.
    """
    code = models.CharField(
        max_length=3,
        primary_key=True,
        verbose_name=_('Code ISO'),
        help_text=_('Code ISO 4217 (ex: CHF, EUR, USD)')
    )
    nom = models.CharField(max_length=50, verbose_name=_('Nom'))
    symbole = models.CharField(max_length=5, verbose_name=_('Symbole'), help_text=_('Ex: Fr., €, $'))

    # Formatage
    decimales = models.PositiveSmallIntegerField(
        default=2,
        validators=[MaxValueValidator(4)],
        verbose_name=_('Décimales')
    )
    separateur_milliers = models.CharField(
        max_length=1,
        default="'",
        verbose_name=_('Séparateur milliers'),
        help_text=_("Ex: ' pour 1'000 ou , pour 1,000")
    )
    separateur_decimal = models.CharField(
        max_length=1,
        default='.',
        verbose_name=_('Séparateur décimal')
    )
    symbole_avant = models.BooleanField(
        default=False,
        verbose_name=_('Symbole avant le montant'),
        help_text=_('True pour $100, False pour 100 CHF')
    )

    # Taux de change (par rapport à la devise de base CHF)
    taux_change = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=1,
        verbose_name=_('Taux de change'),
        help_text=_('Taux par rapport au CHF (1 CHF = X devise)')
    )
    date_taux = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date du taux')
    )

    # Statut
    est_devise_base = models.BooleanField(
        default=False,
        verbose_name=_('Devise de base'),
        help_text=_('Devise principale de comptabilité')
    )
    actif = models.BooleanField(default=True, verbose_name=_('Actif'))

    class Meta:
        db_table = 'devises'
        verbose_name = _('Devise')
        verbose_name_plural = _('Devises')
        ordering = ['-est_devise_base', 'code']

    def __str__(self):
        return f"{self.code} - {self.nom}"

    def formater(self, montant):
        """Formate un montant selon les paramètres de la devise"""
        from decimal import Decimal, ROUND_HALF_UP

        # Arrondir selon le nombre de décimales
        quantize_str = '0.' + '0' * self.decimales if self.decimales > 0 else '0'
        montant_arrondi = Decimal(str(montant)).quantize(
            Decimal(quantize_str), rounding=ROUND_HALF_UP
        )

        # Formater avec séparateurs
        parties = str(montant_arrondi).split('.')
        partie_entiere = parties[0]
        partie_decimale = parties[1] if len(parties) > 1 else '00'

        # Ajouter séparateur milliers
        partie_entiere_formatee = ''
        for i, chiffre in enumerate(reversed(partie_entiere)):
            if i > 0 and i % 3 == 0:
                partie_entiere_formatee = self.separateur_milliers + partie_entiere_formatee
            partie_entiere_formatee = chiffre + partie_entiere_formatee

        # Assembler
        montant_formate = f"{partie_entiere_formatee}{self.separateur_decimal}{partie_decimale}"

        if self.symbole_avant:
            return f"{self.symbole}{montant_formate}"
        else:
            return f"{montant_formate} {self.symbole}"

    def convertir_vers(self, montant, devise_cible):
        """Convertit un montant de cette devise vers une autre"""
        if self.code == devise_cible.code:
            return montant
        # Convertir via CHF comme devise pivot
        montant_chf = montant / self.taux_change if self.taux_change else montant
        return montant_chf * devise_cible.taux_change

    @classmethod
    def get_devise_base(cls):
        """Retourne la devise de base (CHF par défaut)"""
        return cls.objects.filter(est_devise_base=True).first() or cls.objects.get(code='CHF')


# =============================================================================
# ROLE (avec intégration Django Permissions)
# =============================================================================

class Role(models.Model):
    """
    Rôle utilisateur avec intégration complète du système de permissions Django.

    Permet de:
    - Définir des rôles avec une hiérarchie (niveau)
    - Associer des permissions Django natives
    - Gérer les accès de manière centralisée
    """

    # Codes de rôles prédéfinis (pour référence dans le code)
    ADMIN = 'ADMIN'
    MANAGER = 'MANAGER'
    COMPTABLE = 'COMPTABLE'
    ASSISTANT = 'ASSISTANT'
    CLIENT = 'CLIENT'

    ROLE_CODES = [
        (ADMIN, _('Administrateur')),
        (MANAGER, _('Chef de bureau')),
        (COMPTABLE, _('Comptable')),
        (ASSISTANT, _('Assistant')),
        (CLIENT, _('Client')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_('Code'),
        help_text=_('Code unique du rôle (ex: ADMIN, MANAGER)')
    )
    nom = models.CharField(max_length=100, verbose_name=_('Nom'))
    description = models.TextField(blank=True, verbose_name=_('Description'))

    # Hiérarchie - plus le niveau est élevé, plus le rôle a de pouvoir
    niveau = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
        verbose_name=_('Niveau hiérarchique'),
        help_text=_('0=plus bas, 100=plus haut. Un utilisateur peut gérer les rôles de niveau inférieur.')
    )

    # Permissions Django natives
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        verbose_name=_('Permissions'),
        help_text=_('Permissions Django associées à ce rôle')
    )

    # Permissions personnalisées (pour des cas spécifiques non couverts par Django)
    permissions_custom = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Permissions personnalisées'),
        help_text=_('Liste de codes de permissions custom: ["can_export_data", "can_view_reports"]')
    )

    # Configuration
    peut_etre_assigne = models.BooleanField(
        default=True,
        verbose_name=_('Peut être assigné'),
        help_text=_('Si False, ce rôle ne peut pas être assigné manuellement')
    )
    est_role_defaut = models.BooleanField(
        default=False,
        verbose_name=_('Rôle par défaut'),
        help_text=_('Rôle assigné automatiquement aux nouveaux utilisateurs')
    )

    # Statut
    actif = models.BooleanField(default=True, verbose_name=_('Actif'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))

    class Meta:
        db_table = 'roles'
        verbose_name = _('Rôle')
        verbose_name_plural = _('Rôles')
        ordering = ['-niveau', 'nom']

    def __str__(self):
        return f"{self.nom} (niveau {self.niveau})"

    def save(self, *args, **kwargs):
        # S'assurer qu'il n'y a qu'un seul rôle par défaut
        if self.est_role_defaut:
            Role.objects.filter(est_role_defaut=True).exclude(pk=self.pk).update(est_role_defaut=False)
        super().save(*args, **kwargs)

    def get_all_permissions(self):
        """Retourne toutes les permissions (Django + custom)"""
        django_perms = set(self.permissions.values_list('codename', flat=True))
        custom_perms = set(self.permissions_custom or [])
        return django_perms | custom_perms

    def has_permission(self, permission_code):
        """Vérifie si le rôle a une permission spécifique"""
        return permission_code in self.get_all_permissions()

    def has_module_permission(self, app_label):
        """Vérifie si le rôle a des permissions sur un module Django"""
        return self.permissions.filter(
            content_type__app_label=app_label
        ).exists()

    def peut_gerer_role(self, autre_role):
        """Vérifie si ce rôle peut gérer (assigner/modifier) un autre rôle"""
        if not autre_role:
            return True
        return self.niveau > autre_role.niveau

    @classmethod
    def get_role_defaut(cls):
        """Retourne le rôle par défaut"""
        return cls.objects.filter(est_role_defaut=True, actif=True).first()

    @classmethod
    def get_by_code(cls, code):
        """Retourne un rôle par son code"""
        return cls.objects.filter(code=code, actif=True).first()


class User(AbstractUser):
    """Utilisateur étendu avec intégration du système de rôles"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Nouveau système de rôles basé sur le modèle Role
    role = models.ForeignKey(
        'Role',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='utilisateurs',
        verbose_name=_('Rôle')
    )

    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Téléphone'))
    mobile = models.CharField(max_length=20, blank=True, verbose_name=_('Mobile'))
    signature = models.ImageField(upload_to='signatures/', null=True, blank=True, verbose_name=_('Signature'))
    two_factor_enabled = models.BooleanField(default=False, verbose_name=_('Authentification à deux facteurs'))
    preferences = models.JSONField(default=dict, blank=True, verbose_name=_('Préférences'))

    # IMPORTANT: Résoudre les conflits avec auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('Groupes'),
        blank=True,
        related_name='core_user_set',
        related_query_name='core_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('Permissions'),
        blank=True,
        related_name='core_user_set',
        related_query_name='core_user',
    )

    class Meta:
        db_table = 'users'
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')

    def save(self, *args, **kwargs):
        """Assure que les superusers ont automatiquement le rôle ADMIN."""
        if self.is_superuser:
            admin_role = Role.objects.filter(code=Role.ADMIN).first()
            if admin_role and self.role != admin_role:
                self.role = admin_role
        # Assigner le rôle par défaut si aucun rôle
        if not self.role:
            self.role = Role.get_role_defaut()
        super().save(*args, **kwargs)

    # =========================================================================
    # Méthodes de vérification des permissions basées sur le rôle
    # =========================================================================

    def get_role_permissions(self):
        """Retourne toutes les permissions du rôle de l'utilisateur"""
        if self.role:
            return self.role.get_all_permissions()
        return set()

    def has_role_permission(self, permission_code):
        """Vérifie si l'utilisateur a une permission via son rôle"""
        if self.is_superuser:
            return True
        if self.role:
            return self.role.has_permission(permission_code)
        return False

    def has_role_level(self, min_level):
        """Vérifie si l'utilisateur a au moins un certain niveau de rôle"""
        if self.is_superuser:
            return True
        if self.role:
            return self.role.niveau >= min_level
        return False

    def peut_gerer_utilisateur(self, autre_user):
        """Vérifie si cet utilisateur peut gérer un autre utilisateur"""
        if self.is_superuser:
            return True
        if not self.role:
            return False
        return self.role.peut_gerer_role(autre_user.role if autre_user else None)

    @property
    def role_code(self):
        """Retourne le code du rôle pour compatibilité"""
        return self.role.code if self.role else None

    @property
    def role_nom(self):
        """Retourne le nom du rôle"""
        return self.role.nom if self.role else _('Aucun rôle')

    @property
    def role_niveau(self):
        """Retourne le niveau du rôle"""
        return self.role.niveau if self.role else 0

    def is_admin(self):
        """Vérifie si l'utilisateur est admin"""
        return self.is_superuser or (self.role and self.role.code == Role.ADMIN)

    def is_manager(self):
        """Vérifie si l'utilisateur est manager ou supérieur"""
        return self.is_superuser or (self.role and self.role.niveau >= 80)

    def is_comptable(self):
        """Vérifie si l'utilisateur est comptable ou supérieur"""
        return self.is_superuser or (self.role and self.role.niveau >= 60)

    def is_client(self):
        """Vérifie si l'utilisateur est un client"""
        return self.role and self.role.code == Role.CLIENT


class Adresse(models.Model):
    """Adresse réutilisable avec support international"""

    rue = models.CharField(max_length=255, verbose_name=_('Rue'))
    numero = models.CharField(max_length=10, blank=True, verbose_name=_('Numéro'))
    complement = models.CharField(max_length=100, blank=True, verbose_name=_('Complément'))

    # Code postal - format flexible pour international
    code_postal = models.CharField(
        max_length=20,
        default='',
        verbose_name=_('Code postal'),
        help_text=_('NPA pour la Suisse, ZIP pour USA, etc.')
    )
    localite = models.CharField(max_length=100, verbose_name=_('Localité/Ville'))

    # Région/Canton/État - optionnel selon le pays
    region = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Région/Canton/État')
    )
    canton = models.CharField(
        max_length=2,
        choices=SwissCantons.choices,
        blank=True,
        verbose_name=_('Canton'),
        help_text=_('Uniquement pour les adresses suisses')
    )

    # Pays avec django-countries
    pays = CountryField(
        default='CH',
        verbose_name=_('Pays')
    )

    class Meta:
        db_table = 'adresses'
        verbose_name = _('Adresse')
        verbose_name_plural = _('Adresses')

    def __str__(self):
        return f"{self.rue} {self.numero}, {self.code_postal} {self.localite}"

    @property
    def npa(self):
        """Alias pour compatibilité avec l'ancien champ NPA"""
        return self.code_postal

    @npa.setter
    def npa(self, value):
        self.code_postal = value

    @property
    def adresse_complete(self):
        """Retourne l'adresse formatée complète"""
        lignes = [f"{self.rue} {self.numero}".strip()]
        if self.complement:
            lignes.append(self.complement)
        lignes.append(f"{self.code_postal} {self.localite}")
        if self.region:
            lignes[-1] += f", {self.region}"
        if self.pays and self.pays.code != 'CH':
            lignes.append(str(self.pays.name))
        return "\n".join(lignes)

    def clean(self):
        """Validation selon le pays"""
        from django.core.exceptions import ValidationError

        # Validation spécifique Suisse
        if self.pays and self.pays.code == 'CH':
            # NPA suisse: 4 chiffres
            if self.code_postal and not self.code_postal.isdigit() or len(self.code_postal) != 4:
                raise ValidationError({
                    'code_postal': _('Le NPA suisse doit contenir 4 chiffres.')
                })
            # Canton obligatoire pour la Suisse
            if not self.canton:
                raise ValidationError({
                    'canton': _('Le canton est obligatoire pour les adresses suisses.')
                })


class CompteBancaire(models.Model):
    """
    Compte bancaire réutilisable.

    Peut être associé à:
    - Un Client (compte du client)
    - Un User (compte personnel d'un employé)
    - Un Mandat (compte spécifique pour un mandat)
    - L'application elle-même (compte principal de la fiduciaire)

    Utilisé pour:
    - Génération des QR-Bills suisses
    - Informations de paiement sur les factures
    - Versement des salaires
    """

    TYPE_COMPTE_CHOICES = [
        ('COURANT', _('Compte courant')),
        ('EPARGNE', _('Compte épargne')),
        ('SALAIRE', _('Compte salaire')),
        ('POSTAL', _('Compte postal (PostFinance)')),
        ('QR', _('Compte QR-IBAN')),
    ]

    DEVISE_CHOICES = [
        ('CHF', 'CHF - Franc suisse'),
        ('EUR', 'EUR - Euro'),
        ('USD', 'USD - Dollar américain'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identification du compte
    libelle = models.CharField(
        max_length=100,
        verbose_name=_('Libellé'),
        help_text=_('Ex: Compte principal, Compte salaires, etc.')
    )
    type_compte = models.CharField(
        max_length=20,
        choices=TYPE_COMPTE_CHOICES,
        default='COURANT',
        verbose_name=_('Type de compte')
    )

    # Informations bancaires
    iban = models.CharField(
        max_length=34,
        verbose_name=_('IBAN'),
        validators=[
            RegexValidator(
                r'^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$',
                _('Format IBAN invalide. Ex: CH93 0076 2011 6238 5295 7')
            )
        ],
        help_text=_('International Bank Account Number (sans espaces)')
    )
    bic_swift = models.CharField(
        max_length=11,
        blank=True,
        verbose_name=_('BIC/SWIFT'),
        validators=[
            RegexValidator(
                r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$',
                _('Format BIC/SWIFT invalide. Ex: POFICHBEXXX')
            )
        ],
        help_text=_('Bank Identifier Code')
    )

    # Informations de la banque
    nom_banque = models.CharField(
        max_length=100,
        verbose_name=_('Nom de la banque')
    )
    adresse_banque = models.TextField(
        blank=True,
        verbose_name=_('Adresse de la banque')
    )
    clearing = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Numéro clearing'),
        help_text=_('Numéro de compensation bancaire suisse')
    )

    # Titulaire du compte
    titulaire_nom = models.CharField(
        max_length=100,
        verbose_name=_('Nom du titulaire'),
        help_text=_('Nom tel qu\'il apparaît sur le compte')
    )
    titulaire_adresse = models.ForeignKey(
        Adresse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Adresse du titulaire'),
        related_name='comptes_bancaires'
    )

    # Devise
    devise = models.CharField(
        max_length=3,
        choices=DEVISE_CHOICES,
        default='CHF',
        verbose_name=_('Devise')
    )

    # Relations (un compte peut appartenir à plusieurs entités)
    client = models.ForeignKey(
        'Client',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comptes_bancaires',
        verbose_name=_('Client')
    )
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comptes_bancaires',
        verbose_name=_('Utilisateur')
    )
    mandat = models.ForeignKey(
        'Mandat',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comptes_bancaires',
        verbose_name=_('Mandat')
    )

    # Pour le compte principal de la fiduciaire (l'application)
    est_compte_principal = models.BooleanField(
        default=False,
        verbose_name=_('Compte principal'),
        help_text=_('Compte principal de la fiduciaire pour les factures')
    )

    # QR-Bill spécifique
    est_qr_iban = models.BooleanField(
        default=False,
        verbose_name=_('QR-IBAN'),
        help_text=_('IBAN spécifique pour les QR-Bills (commence par CH30-CH31)')
    )
    qr_reference_type = models.CharField(
        max_length=10,
        choices=[
            ('QRR', _('Référence QR (QRR)')),
            ('SCOR', _('Référence SCOR (Creditor Reference)')),
            ('NON', _('Sans référence')),
        ],
        default='QRR',
        verbose_name=_('Type de référence QR')
    )

    # Métadonnées
    actif = models.BooleanField(default=True, verbose_name=_('Actif'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))

    class Meta:
        db_table = 'comptes_bancaires'
        verbose_name = _('Compte bancaire')
        verbose_name_plural = _('Comptes bancaires')
        ordering = ['-est_compte_principal', 'libelle']
        constraints = [
            # Un seul compte principal par défaut
            models.UniqueConstraint(
                fields=['est_compte_principal'],
                condition=models.Q(est_compte_principal=True),
                name='unique_compte_principal'
            )
        ]

    def __str__(self):
        iban_formate = self.iban_formate
        if self.client:
            return f"{self.libelle} - {self.client.raison_sociale} ({iban_formate})"
        elif self.utilisateur:
            return f"{self.libelle} - {self.utilisateur.get_full_name()} ({iban_formate})"
        elif self.est_compte_principal:
            return f"{self.libelle} - Compte principal ({iban_formate})"
        return f"{self.libelle} ({iban_formate})"

    @property
    def iban_formate(self):
        """Retourne l'IBAN formaté avec des espaces tous les 4 caractères"""
        iban = self.iban.replace(' ', '').upper()
        return ' '.join([iban[i:i+4] for i in range(0, len(iban), 4)])

    def clean(self):
        """Validation du modèle"""
        from django.core.exceptions import ValidationError

        # Nettoyer l'IBAN (supprimer espaces)
        if self.iban:
            self.iban = self.iban.replace(' ', '').upper()

        # Nettoyer le BIC
        if self.bic_swift:
            self.bic_swift = self.bic_swift.replace(' ', '').upper()

        # Vérifier que le compte appartient à au moins une entité
        # (sauf si c'est le compte principal)
        if not self.est_compte_principal:
            if not any([self.client, self.utilisateur, self.mandat]):
                raise ValidationError(
                    _('Un compte bancaire doit être associé à un client, un utilisateur, '
                      'un mandat, ou être marqué comme compte principal.')
                )

        # Vérifier format QR-IBAN pour la Suisse
        if self.est_qr_iban and self.iban.startswith('CH'):
            # Les QR-IBAN suisses ont un IID entre 30000-31999
            if len(self.iban) >= 9:
                iid = self.iban[4:9]
                if not (30000 <= int(iid) <= 31999):
                    raise ValidationError(
                        _('Un QR-IBAN suisse doit avoir un IID entre 30000 et 31999. '
                          f'IID actuel: {iid}')
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_compte_principal(cls):
        """Retourne le compte principal de la fiduciaire"""
        return cls.objects.filter(est_compte_principal=True, actif=True).first()

    @classmethod
    def get_compte_qr_default(cls):
        """Retourne le compte QR-IBAN par défaut pour les factures"""
        # Priorité: compte principal QR > premier compte QR actif
        compte = cls.objects.filter(
            est_compte_principal=True,
            est_qr_iban=True,
            actif=True
        ).first()

        if not compte:
            compte = cls.objects.filter(est_qr_iban=True, actif=True).first()

        return compte


class Client(BaseModel):
    """Client de la fiduciaire"""

    FORME_JURIDIQUE_CHOICES = [
        ('EI', _('Entreprise individuelle')),
        ('RC', _('Raison collective')),
        ('SC', _('Société en commandite')),
        ('SNC', _('Société en nom collectif')),
        ('SARL', _('Société à responsabilité limitée')),
        ('SA', _('Société anonyme')),
        ('SC_SIMPLE', _('Société en commandite simple')),
        ('SC_ACTIONS', _('Société en commandite par actions')),
        ('COOP', _('Société coopérative')),
        ('ASSOC', _('Association')),
        ('FOND', _('Fondation')),
    ]

    STATUT_CHOICES = [
        ('PROSPECT', _('Prospect')),
        ('ACTIF', _('Actif')),
        ('SUSPENDU', _('Suspendu')),
        ('RESILIE', _('Résilié')),
        ('ARCHIVE', _('Archivé')),
    ]

    # Identification
    raison_sociale = models.CharField(max_length=255, db_index=True, verbose_name=_('Raison sociale'))
    nom_commercial = models.CharField(max_length=255, blank=True, verbose_name=_('Nom commercial'))
    forme_juridique = models.CharField(max_length=20, choices=FORME_JURIDIQUE_CHOICES, verbose_name=_('Forme juridique'))
    description = models.TextField(blank=True, verbose_name=_('Description'))

    # Numéros officiels
    ide_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^CHE-\d{3}\.\d{3}\.\d{3}$',
                                   'Format IDE invalide (CHE-XXX.XXX.XXX)')],
        help_text='Format: CHE-123.456.789',
        verbose_name=_('Numéro IDE')
    )
    tva_number = models.CharField(max_length=20, blank=True, db_index=True, verbose_name=_('Numéro TVA'))
    rc_number = models.CharField(max_length=50, blank=True, verbose_name=_('Numéro RC'))

    # Coordonnées
    adresse_siege = models.ForeignKey(Adresse, on_delete=models.PROTECT,
                                      related_name='clients_siege',
                                      verbose_name=_('Adresse de siège'))
    adresse_correspondance = models.ForeignKey(Adresse, on_delete=models.PROTECT,
                                               related_name='clients_correspondance',
                                               null=True, blank=True,
                                               verbose_name=_('Adresse de correspondance'))

    email = models.EmailField(verbose_name=_('Email'))
    telephone = models.CharField(max_length=20, verbose_name=_('Téléphone'))
    site_web = models.URLField(blank=True, verbose_name=_('Site web'))

    # Dates importantes
    date_creation = models.DateField(verbose_name=_('Date de création entreprise'))
    date_inscription_rc = models.DateField(null=True, blank=True, verbose_name=_('Date inscription RC'))
    date_debut_exercice = models.DateField(verbose_name=_('Début exercice comptable'))
    date_fin_exercice = models.DateField(verbose_name=_('Fin exercice comptable'))

    # Statut
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES,
                              default='PROSPECT', db_index=True, verbose_name=_('Statut'))

    # Contacts
    contact_principal = models.ForeignKey('Contact', on_delete=models.SET_NULL,
                                          null=True, related_name='clients_principal',
                                          verbose_name=_('Contact principal'))

    # Gestion interne
    responsable = models.ForeignKey(User, on_delete=models.PROTECT,
                                    related_name='clients_responsable',
                                    verbose_name=_('Responsable'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        db_table = 'clients'
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')
        ordering = ['raison_sociale']
        indexes = [
            models.Index(fields=['raison_sociale', 'statut']),
            models.Index(fields=['ide_number']),
        ]

    def __str__(self):
        return f"{self.raison_sociale} ({self.ide_number})"

    @property
    def mandats_actifs(self):
        return self.mandats.filter(statut='ACTIF')


class Contact(BaseModel):
    """Contact d'un client"""

    FONCTION_CHOICES = [
        ('DIRECTEUR', _('Directeur')),
        ('GERANT', _('Gérant')),
        ('ADMIN', _('Administrateur')),
        ('COMPTABLE', _('Comptable')),
        ('RH', _('Ressources Humaines')),
        ('AUTRE', _('Autre')),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contacts', verbose_name=_('Client'))

    civilite = models.CharField(max_length=10, choices=[
        ('M', _('Monsieur')),
        ('MME', _('Madame')),
        ('DR', _('Docteur')),
        ('PROF', _('Professeur')),
    ], verbose_name=_('Civilité'))
    nom = models.CharField(max_length=100, verbose_name=_('Nom'))
    prenom = models.CharField(max_length=100, verbose_name=_('Prénom'))
    fonction = models.CharField(max_length=20, choices=FONCTION_CHOICES, verbose_name=_('Fonction'))

    email = models.EmailField(verbose_name=_('Email'))
    telephone = models.CharField(max_length=20, blank=True, verbose_name=_('Téléphone'))
    mobile = models.CharField(max_length=20, blank=True, verbose_name=_('Mobile'))

    principal = models.BooleanField(default=False, verbose_name=_('Contact principal'))

    class Meta:
        db_table = 'contacts'
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.client.raison_sociale}"


class Mandat(BaseModel):
    """Mandat de prestation"""

    TYPE_CHOICES = [
        ('COMPTA', _('Comptabilité')),
        ('TVA', _('TVA')),
        ('SALAIRES', _('Salaires')),
        ('FISCAL', _('Conseil fiscal')),
        ('REVISION', _('Révision')),
        ('CONSEIL', _('Conseil général')),
        ('CREATION', _('Création entreprise')),
        ('GLOBAL', _('Mandat global')),
    ]

    PERIODICITE_CHOICES = [
        ('MENSUEL', _('Mensuel')),
        ('TRIMESTRIEL', _('Trimestriel')),
        ('SEMESTRIEL', _('Semestriel')),
        ('ANNUEL', _('Annuel')),
        ('PONCTUEL', _('Ponctuel')),
    ]

    STATUT_CHOICES = [
        ('BROUILLON', _('Brouillon')),
        ('EN_ATTENTE', _('En attente validation')),
        ('ACTIF', _('Actif')),
        ('SUSPENDU', _('Suspendu')),
        ('TERMINE', _('Terminé')),
        ('RESILIE', _('Résilié')),
    ]

    # Identification
    numero = models.CharField(max_length=50, unique=True, db_index=True, verbose_name=_('Numéro'))
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='mandats', verbose_name=_('Client'))
    type_mandat = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True, verbose_name=_('Type de mandat'))

    # Période
    date_debut = models.DateField(verbose_name=_('Date de début'))
    date_fin = models.DateField(null=True, blank=True, verbose_name=_('Date de fin'))
    periodicite = models.CharField(max_length=20, choices=PERIODICITE_CHOICES, verbose_name=_('Périodicité'))

    # Honoraires
    type_facturation = models.CharField(max_length=20, choices=[
        ('FORFAIT', _('Forfait')),
        ('HORAIRE', _('Taux horaire')),
        ('MIXTE', _('Mixte')),
    ], default='HORAIRE', verbose_name=_('Type de facturation'))
    montant_forfait = models.DecimalField(max_digits=10, decimal_places=2,
                                          null=True, blank=True, verbose_name=_('Montant forfait'))
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2,
                                       null=True, blank=True, verbose_name=_('Taux horaire'))

    # Configuration
    configuration = models.JSONField(default=dict, blank=True, verbose_name=_('Configuration'), help_text="""
    {
        "plan_comptable": "PME",
        "methode_tva": "EFFECTIVE",
        "periodicite_tva": "TRIMESTRIEL",
        "cloture_mois": 12,
        "devise": "CHF",
        "langues": ["fr"],
        "modules_actifs": ["compta", "tva", "salaires"]
    }
    """)

    # Gestion
    responsable = models.ForeignKey(User, on_delete=models.PROTECT,
                                    related_name='mandats_responsable', verbose_name=_('Responsable'))
    equipe = models.ManyToManyField(User, related_name='mandats_equipe', blank=True, verbose_name=_('Équipe'))
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES,
                              default='BROUILLON', db_index=True, verbose_name=_('Statut'))

    description = models.TextField(blank=True, verbose_name=_('Description'))
    conditions_particulieres = models.TextField(blank=True, verbose_name=_('Conditions particulières'))

    class Meta:
        db_table = 'mandats'
        verbose_name = _('Mandat')
        verbose_name_plural = _('Mandats')
        ordering = ['-date_debut']
        indexes = [
            models.Index(fields=['client', 'statut']),
            models.Index(fields=['type_mandat', 'statut']),
        ]

    def __str__(self):
        return f"{self.numero} - {self.client.raison_sociale} - {self.get_type_mandat_display()}"

    def save(self, *args, **kwargs):
        if not self.numero:
            # Génération auto du numéro: MAN-2025-001
            year = self.date_debut.year
            last = Mandat.objects.filter(
                numero__startswith=f'MAN-{year}'
            ).order_by('numero').last()

            if last:
                last_num = int(last.numero.split('-')[-1])
                self.numero = f'MAN-{year}-{last_num + 1:03d}'
            else:
                self.numero = f'MAN-{year}-001'

        super().save(*args, **kwargs)


class ExerciceComptable(BaseModel):
    """Exercice comptable"""

    STATUT_CHOICES = [
        ('OUVERT', _('Ouvert')),
        ('CLOTURE_PROVISOIRE', _('Clôture provisoire')),
        ('CLOTURE_DEFINITIVE', _('Clôture définitive')),
    ]

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='exercices',
                               verbose_name=_('Mandat'))
    annee = models.IntegerField(db_index=True, verbose_name=_('Année'))
    date_debut = models.DateField(verbose_name=_('Date de début'))
    date_fin = models.DateField(verbose_name=_('Date de fin'))
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES,
                              default='OUVERT', db_index=True,
                              verbose_name=_('Statut'))

    date_cloture = models.DateTimeField(null=True, blank=True,
                                        verbose_name=_('Date de clôture'))
    cloture_par = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, related_name='+',
                                    verbose_name=_('Clôturé par'))

    resultat_exercice = models.DecimalField(max_digits=15, decimal_places=2,
                                            null=True, blank=True,
                                            verbose_name=_('Résultat exercice'))

    class Meta:
        db_table = 'exercices_comptables'
        verbose_name = _('Exercice comptable')
        verbose_name_plural = _('Exercices comptables')
        unique_together = [['mandat', 'annee']]
        ordering = ['-annee']

    def __str__(self):
        return f"{self.mandat.numero} - Exercice {self.annee}"


class AuditLog(models.Model):
    """Log d'audit de toutes les actions"""

    ACTION_CHOICES = [
        ('CREATE', _('Création')),
        ('UPDATE', _('Modification')),
        ('DELETE', _('Suppression')),
        ('VIEW', _('Consultation')),
        ('EXPORT', _('Export')),
        ('IMPORT', _('Import')),
        ('VALIDATE', _('Validation')),
        ('SUBMIT', _('Soumission')),
    ]

    # Qui
    utilisateur = models.ForeignKey(User, on_delete=models.PROTECT,
                                    verbose_name=_('Utilisateur'))

    # Quoi
    action = models.CharField(max_length=20, choices=ACTION_CHOICES,
                             verbose_name=_('Action'))
    table_name = models.CharField(max_length=100, db_index=True,
                                  verbose_name=_('Nom de la table'))
    object_id = models.CharField(max_length=100, verbose_name=_('ID objet'))
    object_repr = models.CharField(max_length=255,
                                   verbose_name=_('Représentation objet'))

    # Détails
    changements = models.JSONField(default=dict, blank=True,
                                   verbose_name=_('Changements'),
                                   help_text=_("""
    Détails des changements:
    {
        "before": {"field1": "old_value"},
        "after": {"field1": "new_value"}
    }
    """))

    # Quand et où
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True,
                                    verbose_name=_('Horodatage'))
    ip_address = models.GenericIPAddressField(null=True, blank=True,
                                              verbose_name=_('Adresse IP'))
    user_agent = models.TextField(blank=True, verbose_name=_('User Agent'))

    # Contexte
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True,
                               verbose_name=_('Mandat'))

    class Meta:
        db_table = 'audit_log'
        verbose_name = _('Log d\'audit')
        verbose_name_plural = _('Logs d\'audit')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['utilisateur', 'timestamp']),
            models.Index(fields=['table_name', 'object_id']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.utilisateur.username} - {self.action} - {self.object_repr}"


class Notification(BaseModel):
    """Notifications utilisateur"""

    TYPE_CHOICES = [
        ('INFO', _('Information')),
        ('SUCCESS', _('Succès')),
        ('WARNING', _('Avertissement')),
        ('ERROR', _('Erreur')),
        ('TASK', _('Tâche')),
    ]

    destinataire = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name='notifications',
                                     verbose_name=_('Destinataire'))

    type_notification = models.CharField(max_length=20, choices=TYPE_CHOICES,
                                         verbose_name=_('Type de notification'))
    titre = models.CharField(max_length=255, verbose_name=_('Titre'))
    message = models.TextField(verbose_name=_('Message'))
    # Lien
    lien_action = models.CharField(max_length=500, blank=True, verbose_name=_('Lien action'))
    lien_texte = models.CharField(max_length=100, blank=True, verbose_name=_('Texte du lien'))

    # Statut
    lue = models.BooleanField(default=False, db_index=True, verbose_name=_('Lue'))
    date_lecture = models.DateTimeField(null=True, blank=True, verbose_name=_('Date de lecture'))

    archivee = models.BooleanField(default=False, verbose_name=_('Archivée'))

    # Contexte
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True,
                               verbose_name=_('Mandat'))

    class Meta:
        db_table = 'notifications'
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['destinataire', 'lue']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.destinataire.username} - {self.titre}"


class Tache(BaseModel):
    """Tâche à effectuer"""

    PRIORITE_CHOICES = [
        ('BASSE', _('Basse')),
        ('NORMALE', _('Normale')),
        ('HAUTE', _('Haute')),
        ('URGENTE', _('Urgente')),
    ]

    STATUT_CHOICES = [
        ('A_FAIRE', _('À faire')),
        ('EN_COURS', _('En cours')),
        ('EN_ATTENTE', _('En attente')),
        ('TERMINEE', _('Terminée')),
        ('ANNULEE', _('Annulée')),
    ]

    titre = models.CharField(max_length=255, verbose_name=_('Titre'))
    description = models.TextField(blank=True, verbose_name=_('Description'))

    # Assignation
    assigne_a = models.ForeignKey(User, on_delete=models.PROTECT,
                                  related_name='taches_assignees',
                                  verbose_name=_('Assigné à'))
    cree_par = models.ForeignKey(User, on_delete=models.PROTECT,
                                 related_name='taches_creees',
                                 verbose_name=_('Créé par'))

    # Rattachement
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='taches',
                               verbose_name=_('Mandat'))

    # Priorité et échéance
    priorite = models.CharField(max_length=20, choices=PRIORITE_CHOICES,
                                default='NORMALE', verbose_name=_('Priorité'))
    date_echeance = models.DateField(null=True, blank=True, db_index=True,
                                     verbose_name=_('Date d\'échéance'))

    # Statut
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES,
                              default='A_FAIRE', db_index=True,
                              verbose_name=_('Statut'))

    date_debut = models.DateTimeField(null=True, blank=True,
                                      verbose_name=_('Date de début'))
    date_fin = models.DateTimeField(null=True, blank=True,
                                    verbose_name=_('Date de fin'))

    # Temps estimé/réel
    temps_estime_heures = models.DecimalField(max_digits=6, decimal_places=2,
                                              null=True, blank=True,
                                              verbose_name=_('Temps estimé (heures)'))
    temps_reel_heures = models.DecimalField(max_digits=6, decimal_places=2,
                                            null=True, blank=True,
                                            verbose_name=_('Temps réel (heures)'))

    # Tags
    tags = models.JSONField(default=list, blank=True, verbose_name=_('Tags'))

    class Meta:
        db_table = 'taches'
        verbose_name = _('Tâche')
        verbose_name_plural = _('Tâches')
        ordering = ['-priorite', 'date_echeance']
        indexes = [
            models.Index(fields=['assigne_a', 'statut']),
            models.Index(fields=['date_echeance', 'statut']),
        ]

    def __str__(self):
        return f"{self.titre} - {self.assigne_a.username}"