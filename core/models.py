# apps/core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Permission
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
import hashlib
import json
import os
import secrets
import uuid


class BaseModel(models.Model):
    """Modèle abstrait de base pour tous les modèles"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL,
                                   null=True, related_name='+', verbose_name=_('Créé par'))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_('Actif'))
    langue_saisie = models.CharField(
        max_length=5, blank=True, default='',
        db_index=True,
        verbose_name=_('Langue de saisie'),
        help_text=_('Langue dans laquelle les données ont été saisies (auto-détecté)')
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Auto-remplir la langue de saisie si non définie
        if not self.langue_saisie:
            from django.utils.translation import get_language
            self.langue_saisie = get_language() or 'fr'
        super().save(*args, **kwargs)


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

        # Séparer partie entière et décimale
        parties = str(montant_arrondi).split('.')
        partie_entiere = parties[0].lstrip('-')
        signe = '-' if montant_arrondi < 0 else ''

        # Ajouter séparateur milliers
        partie_entiere_formatee = ''
        for i, chiffre in enumerate(reversed(partie_entiere)):
            if i > 0 and i % 3 == 0:
                partie_entiere_formatee = self.separateur_milliers + partie_entiere_formatee
            partie_entiere_formatee = chiffre + partie_entiere_formatee

        # Assembler — sans décimales si decimales=0
        if self.decimales > 0:
            partie_decimale = parties[1] if len(parties) > 1 else '0' * self.decimales
            montant_formate = f"{signe}{partie_entiere_formatee}{self.separateur_decimal}{partie_decimale}"
        else:
            montant_formate = f"{signe}{partie_entiere_formatee}"

        if self.symbole_avant:
            return f"{self.symbole} {montant_formate}"
        else:
            return f"{montant_formate} {self.symbole}"

    def convertir_vers(self, montant, devise_cible):
        """Convertit un montant de cette devise vers une autre"""
        from decimal import Decimal, ROUND_HALF_UP

        if self.code == devise_cible.code:
            return Decimal(str(montant))
        # Convertir via CHF comme devise pivot
        montant_decimal = Decimal(str(montant))
        montant_chf = montant_decimal / self.taux_change if self.taux_change else montant_decimal
        resultat = montant_chf * devise_cible.taux_change
        # Quantize selon les décimales de la devise cible
        quantize_str = '0.' + '0' * devise_cible.decimales if devise_cible.decimales > 0 else '0'
        return resultat.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

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


class TypeCollaborateur(models.TextChoices):
    """
    Type de collaborateur: employé interne ou prestataire externe.
    S'applique aussi bien aux STAFF (fiduciaire) qu'aux CLIENT (leurs employés/prestataires).
    """
    EMPLOYE = 'EMPLOYE', _('Employé')
    PRESTATAIRE = 'PRESTATAIRE', _('Prestataire')


class User(AbstractUser):
    """Utilisateur étendu avec intégration du système de rôles"""

    class TypeUtilisateur(models.TextChoices):
        STAFF = 'STAFF', _('Collaborateur interne')
        CLIENT = 'CLIENT', _('Client externe')

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

    # Type d'utilisateur (STAFF = interne, CLIENT = externe)
    type_utilisateur = models.CharField(
        max_length=10,
        choices=TypeUtilisateur.choices,
        default=TypeUtilisateur.STAFF,
        db_index=True,
        verbose_name=_('Type d\'utilisateur')
    )

    # Type de collaborateur (EMPLOYE = salarié/interne, PRESTATAIRE = externe/contractor)
    type_collaborateur = models.CharField(
        max_length=15,
        choices=TypeCollaborateur.choices,
        default=TypeCollaborateur.EMPLOYE,
        db_index=True,
        verbose_name=_("Type de collaborateur"),
        help_text=_("Employé = salarié/interne, Prestataire = externe/contractor")
    )

    # Changement de mot de passe obligatoire (première connexion après invitation)
    doit_changer_mot_de_passe = models.BooleanField(
        default=False,
        verbose_name=_('Doit changer le mot de passe'),
        help_text=_('Force l\'utilisateur à changer son mot de passe à la prochaine connexion')
    )

    # Lien vers un contact (pour les utilisateurs CLIENT)
    contact_lie = models.ForeignKey(
        'Contact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateur_lie',
        verbose_name=_('Contact lié'),
        help_text=_('Contact associé pour les utilisateurs clients')
    )

    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name=_('Photo de profil'))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Téléphone'))
    mobile = models.CharField(max_length=20, blank=True, verbose_name=_('Mobile'))
    signature = models.ImageField(upload_to='signatures/', null=True, blank=True, verbose_name=_('Signature'))
    two_factor_enabled = models.BooleanField(default=False, verbose_name=_('Authentification à deux facteurs'))
    totp_secret = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name=_('Secret TOTP (chiffré)'),
        help_text=_('Secret TOTP chiffré pour l\'authentification à deux facteurs')
    )
    backup_codes = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Codes de secours (hashés)'),
        help_text=_('Liste de codes de secours hashés pour la 2FA')
    )
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

    # =========================================================================
    # Méthodes pour le type d'utilisateur (STAFF/CLIENT)
    # =========================================================================

    def is_staff_user(self):
        """Vérifie si l'utilisateur est un collaborateur interne"""
        return self.type_utilisateur == self.TypeUtilisateur.STAFF

    def is_client_user(self):
        """Vérifie si l'utilisateur est un client externe"""
        return self.type_utilisateur == self.TypeUtilisateur.CLIENT

    # =========================================================================
    # Méthodes pour le type de collaborateur (EMPLOYE/PRESTATAIRE)
    # =========================================================================

    def is_employe(self):
        """Vérifie si l'utilisateur est un employé (salarié/interne)"""
        return self.type_collaborateur == TypeCollaborateur.EMPLOYE

    def is_prestataire(self):
        """Vérifie si l'utilisateur est un prestataire (externe/contractor)"""
        return self.type_collaborateur == TypeCollaborateur.PRESTATAIRE

    def is_fiduciaire_prestataire(self):
        """Vérifie si l'utilisateur est un prestataire de la fiduciaire"""
        return self.is_staff_user() and self.is_prestataire()

    def get_employe_record(self):
        """Retourne l'enregistrement Employe lié (si existe)"""
        return getattr(self, 'employe_record', None)

    def get_accessible_mandats(self):
        """
        Retourne les mandats accessibles par cet utilisateur.

        Logique:
        - Superuser / Manager STAFF: tous les mandats actifs
        - STAFF Employé: mandats où il est responsable ou dans l'équipe
        - STAFF Prestataire: mandats via CollaborateurFiduciaire
        - CLIENT: mandats via AccesMandat
        """
        from django.db.models import Q

        if self.is_superuser:
            return Mandat.objects.filter(statut='ACTIF')

        if self.is_staff_user():
            if self.is_manager():
                # Manager staff: tous les mandats actifs
                return Mandat.objects.filter(statut='ACTIF')

            if self.is_employe():
                # Employé interne: responsable ou équipe
                return Mandat.objects.filter(
                    Q(responsable=self) | Q(equipe=self),
                    statut='ACTIF'
                ).distinct()
            else:
                # Prestataire fiduciaire: via affectations
                return Mandat.objects.filter(
                    prestataires_affectes__utilisateur=self,
                    prestataires_affectes__is_active=True,
                    statut='ACTIF'
                ).distinct()

        # Client externe: uniquement via AccesMandat
        return Mandat.objects.filter(
            acces_utilisateurs__utilisateur=self,
            acces_utilisateurs__is_active=True,
            statut='ACTIF'
        ).distinct()

    @property
    def mandats_accessibles(self):
        """Alias de get_accessible_mandats() pour compatibilité"""
        return self.get_accessible_mandats()

    def get_acces_mandats(self):
        """Retourne les AccesMandat actifs de cet utilisateur"""
        return self.acces_mandats.filter(is_active=True).select_related('mandat')

    def est_responsable_mandat(self, mandat):
        """Vérifie si l'utilisateur est responsable d'un mandat (côté client)"""
        if self.is_staff_user():
            return mandat.responsable == self
        return self.acces_mandats.filter(
            mandat=mandat,
            est_responsable=True,
            is_active=True
        ).exists()

    def peut_inviter_pour_mandat(self, mandat):
        """Vérifie si l'utilisateur peut inviter d'autres personnes pour un mandat"""
        if self.is_superuser or self.is_manager():
            return True
        if self.is_client_user():
            acces = self.acces_mandats.filter(
                mandat=mandat,
                est_responsable=True,
                is_active=True
            ).first()
            return acces and acces.invitations_restantes > 0
        return False

    # =========================================================================
    # Méthodes pour l'authentification à deux facteurs (TOTP)
    # =========================================================================

    def _get_fernet(self):
        """Retourne une instance Fernet pour chiffrer/déchiffrer le secret TOTP."""
        from cryptography.fernet import Fernet
        from django.conf import settings
        import base64
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    def generate_totp_secret(self):
        """Génère un nouveau secret TOTP et le stocke chiffré."""
        import pyotp
        raw_secret = pyotp.random_base32()
        fernet = self._get_fernet()
        self.totp_secret = fernet.encrypt(raw_secret.encode()).decode()
        return raw_secret

    def get_totp_secret(self):
        """Déchiffre et retourne le secret TOTP brut."""
        if not self.totp_secret:
            return None
        fernet = self._get_fernet()
        return fernet.decrypt(self.totp_secret.encode()).decode()

    def get_totp_uri(self):
        """Retourne l'URI otpauth:// pour le QR code."""
        import pyotp
        raw_secret = self.get_totp_secret()
        if not raw_secret:
            return None
        return pyotp.totp.TOTP(raw_secret).provisioning_uri(
            name=self.email or self.username,
            issuer_name='AltiusOne'
        )

    def verify_totp(self, code):
        """Vérifie un code TOTP (accepte ±1 intervalle pour le décalage horloge)."""
        import pyotp
        raw_secret = self.get_totp_secret()
        if not raw_secret:
            return False
        totp = pyotp.TOTP(raw_secret)
        return totp.verify(code, valid_window=1)

    def generate_backup_codes(self):
        """Génère 8 codes de secours, stocke les hash, retourne les codes en clair."""
        codes = [secrets.token_hex(4).upper() for _ in range(8)]
        self.backup_codes = [
            hashlib.sha256(code.encode()).hexdigest() for code in codes
        ]
        return codes

    def verify_backup_code(self, code):
        """Vérifie et consume un code de secours. Retourne True si valide."""
        code_hash = hashlib.sha256(code.strip().upper().encode()).hexdigest()
        if code_hash in self.backup_codes:
            self.backup_codes.remove(code_hash)
            self.save(update_fields=['backup_codes'])
            return True
        return False

    def enable_2fa(self):
        """Active la 2FA (après vérification du premier code)."""
        self.two_factor_enabled = True
        self.save(update_fields=['two_factor_enabled'])

    def disable_2fa(self):
        """Désactive la 2FA et efface les données associées."""
        self.two_factor_enabled = False
        self.totp_secret = ''
        self.backup_codes = []
        self.save(update_fields=['two_factor_enabled', 'totp_secret', 'backup_codes'])


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
        help_text=_('International Bank Account Number')
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
    devise = models.ForeignKey(
        Devise,
        on_delete=models.PROTECT,
        db_column='devise',
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

    # Entreprise propriétaire (pour les comptes principaux multi-entité)
    entreprise = models.ForeignKey(
        'Entreprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comptes_bancaires',
        verbose_name=_('Entreprise')
    )

    # Pour le compte principal de la fiduciaire (l'application)
    est_compte_principal = models.BooleanField(
        default=False,
        verbose_name=_('Compte principal'),
        help_text=_('Compte principal de l\'entreprise pour les factures')
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
            # Un seul compte principal par entreprise
            models.UniqueConstraint(
                fields=['entreprise', 'est_compte_principal'],
                condition=models.Q(est_compte_principal=True),
                name='unique_compte_principal_par_entreprise'
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
        from core.validators import clean_iban, validate_iban_format, validate_iban_checksum

        # Nettoyer l'IBAN (supprimer espaces, corriger O→0)
        if self.iban:
            self.iban = clean_iban(self.iban)
            if not validate_iban_format(self.iban):
                raise ValidationError({'iban': _('Format IBAN invalide. Ex: CH9300762011623852957')})
            if not validate_iban_checksum(self.iban):
                raise ValidationError({'iban': _('IBAN invalide (erreur de checksum). Vérifiez les chiffres.')})

        # Nettoyer le BIC
        if self.bic_swift:
            self.bic_swift = self.bic_swift.replace(' ', '').upper()

        # Vérifier que le compte appartient à au moins une entité
        # (sauf si c'est le compte principal ou lié à une entreprise)
        if not self.est_compte_principal:
            if not any([self.client, self.utilisateur, self.mandat, self.entreprise]):
                raise ValidationError(
                    _('Un compte bancaire doit être associé à un client, un utilisateur, '
                      'un mandat, une entreprise, ou être marqué comme compte principal.')
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
        # Auto-populate devise from mandat if not set
        if not self.devise_id:
            if self.mandat_id:
                self.devise_id = self.mandat.devise_id
            else:
                self.devise_id = Devise.get_devise_base().code
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_compte_principal(cls, entreprise=None):
        """Retourne le compte principal, optionnellement filtré par entreprise."""
        qs = cls.objects.filter(est_compte_principal=True, actif=True)
        if entreprise:
            return qs.filter(entreprise=entreprise).first() or qs.first()
        return qs.first()

    @classmethod
    def get_compte_qr_default(cls, entreprise=None):
        """Retourne le compte QR-IBAN par défaut pour les factures."""
        qs = cls.objects.filter(est_qr_iban=True, actif=True)
        if entreprise:
            # Priorité: compte principal QR de l'entreprise > QR de l'entreprise > global
            compte = qs.filter(entreprise=entreprise, est_compte_principal=True).first()
            if not compte:
                compte = qs.filter(entreprise=entreprise).first()
            if not compte:
                compte = qs.filter(est_compte_principal=True).first()
            if not compte:
                compte = qs.first()
            return compte

        # Sans entreprise: compte principal QR > premier QR actif
        compte = qs.filter(est_compte_principal=True).first()
        if not compte:
            compte = qs.first()
        return compte


# =============================================================================
# TIERS (Fournisseur, débiteur, créditeur centralisé)
# =============================================================================

class Tiers(BaseModel):
    """Tiers centralisé (fournisseur, débiteur, créditeur)"""

    TYPE_TIERS_CHOICES = [
        ('FOURNISSEUR', _('Fournisseur')),
        ('CLIENT', _('Client')),
        ('EMPLOYE', _('Employé')),
        ('ADMINISTRATION', _('Administration')),
        ('ASSOCIE', _('Associé')),
        ('AUTRE', _('Autre')),
    ]

    mandat = models.ForeignKey(
        'Mandat', on_delete=models.CASCADE,
        related_name='tiers',
        verbose_name=_('Mandat')
    )
    code = models.CharField(
        max_length=50, db_index=True,
        verbose_name=_('Code')
    )
    nom = models.CharField(
        max_length=255,
        verbose_name=_('Nom')
    )
    type_tiers = models.CharField(
        max_length=20, choices=TYPE_TIERS_CHOICES,
        default='FOURNISSEUR',
        verbose_name=_('Type de tiers')
    )
    numero_tva = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Numéro TVA')
    )
    numero_ide = models.CharField(
        max_length=20, blank=True,
        verbose_name=_('Numéro IDE')
    )
    adresse = models.ForeignKey(
        Adresse, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Adresse')
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_('Email')
    )
    telephone = models.CharField(
        max_length=20, blank=True,
        verbose_name=_('Téléphone')
    )
    compte_associe = models.ForeignKey(
        'comptabilite.Compte', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Compte associé')
    )
    devise = models.ForeignKey(
        Devise, on_delete=models.PROTECT,
        verbose_name=_('Devise')
    )
    client_lie = models.ForeignKey(
        'Client', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Client lié')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            self.nom,
            self.code,
            f"TVA: {self.numero_tva}" if self.numero_tva else '',
            self.email or '',
            self.notes,
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'tiers'
        verbose_name = _('Tiers')
        verbose_name_plural = _('Tiers')
        unique_together = [('mandat', 'code')]
        ordering = ['nom']

    def __str__(self):
        return f"{self.code} - {self.nom}"

    def save(self, *args, **kwargs):
        # Auto-populate devise from mandat if not set
        if not self.devise_id and self.mandat_id:
            self.devise_id = self.mandat.devise_id
        super().save(*args, **kwargs)


# =============================================================================
# ENTREPRISE (Entités juridiques de la fiduciaire)
# =============================================================================

class Entreprise(models.Model):
    """
    Entité juridique de la fiduciaire.

    Permet de gérer plusieurs entités juridiques (ex: "Altius Academy SNC"
    + "Altius Conseil SA"). L'entreprise marquée `est_defaut=True` est
    l'entité principale utilisée par défaut.
    """

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
        ('ACTIVE', _('Active')),
        ('INACTIVE', _('Inactive')),
        ('EN_LIQUIDATION', _('En liquidation')),
        ('RADIEE', _('Radiée')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identification
    raison_sociale = models.CharField(
        max_length=255,
        verbose_name=_('Raison sociale'),
        help_text=_('Nom officiel de l\'entreprise')
    )
    nom_commercial = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Nom commercial'),
        help_text=_('Nom utilisé commercialement si différent')
    )
    forme_juridique = models.CharField(
        max_length=20,
        choices=FORME_JURIDIQUE_CHOICES,
        verbose_name=_('Forme juridique')
    )

    # Numéros officiels suisses
    ide_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(
            r'^CHE-\d{3}\.\d{3}\.\d{3}$',
            'Format IDE invalide (CHE-XXX.XXX.XXX)'
        )],
        verbose_name=_('Numéro IDE'),
        help_text=_('Numéro d\'identification des entreprises (CHE-XXX.XXX.XXX)')
    )
    ch_id = models.CharField(
        max_length=30,
        blank=True,
        verbose_name=_('CH-ID'),
        help_text=_('Numéro CH-ID (CH-XXX-XXXXXXX-X)')
    )
    ofrc_id = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('OFRC-ID'),
        help_text=_('Numéro de l\'Office fédéral du registre du commerce')
    )
    tva_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Numéro TVA'),
        help_text=_('Numéro TVA si assujetti')
    )

    # Adresse
    adresse = models.ForeignKey(
        Adresse,
        on_delete=models.PROTECT,
        related_name='entreprises',
        verbose_name=_('Adresse du siège'),
        null=True,
        blank=True
    )
    siege = models.CharField(
        max_length=100,
        verbose_name=_('Siège'),
        help_text=_('Localité du siège social')
    )

    # Contact
    email = models.EmailField(
        blank=True,
        verbose_name=_('Email')
    )
    telephone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Téléphone')
    )
    site_web = models.URLField(
        blank=True,
        verbose_name=_('Site web')
    )

    # Informations légales
    but = models.TextField(
        blank=True,
        verbose_name=_('But'),
        help_text=_('But de l\'entreprise tel qu\'inscrit au RC')
    )
    date_creation = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de création'),
        help_text=_('Date de création/commencement de l\'entreprise')
    )
    date_inscription_rc = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date d\'inscription RC'),
        help_text=_('Date d\'inscription au registre du commerce')
    )
    canton_rc = models.CharField(
        max_length=2,
        choices=SwissCantons.choices,
        blank=True,
        verbose_name=_('Canton du RC'),
        help_text=_('Canton du registre du commerce')
    )

    # Publications FOSC
    derniere_publication_fosc = models.TextField(
        blank=True,
        verbose_name=_('Dernière publication FOSC'),
        help_text=_('Dernière publication à la Feuille officielle suisse du commerce')
    )

    # Statut
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='ACTIVE',
        verbose_name=_('Statut')
    )

    # Logo et branding
    logo = models.ImageField(
        upload_to='entreprise/logo/',
        blank=True,
        null=True,
        verbose_name=_('Logo'),
        help_text=_('Logo de l\'entreprise (utilisé sur les documents)')
    )

    # Entreprise par défaut
    est_defaut = models.BooleanField(
        default=False,
        verbose_name=_('Entreprise par défaut'),
        help_text=_('Entreprise utilisée par défaut (une seule autorisée)')
    )

    # Associés/Propriétaires (stocké en JSON pour flexibilité)
    associes = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Associés'),
        help_text=_('Liste des associés avec leurs informations')
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))

    class Meta:
        db_table = 'entreprise'
        verbose_name = _('Entreprise')
        verbose_name_plural = _('Entreprises')
        constraints = [
            models.UniqueConstraint(
                fields=['est_defaut'],
                condition=models.Q(est_defaut=True),
                name='unique_entreprise_defaut'
            )
        ]

    def __str__(self):
        return f"{self.raison_sociale} ({self.ide_number})"

    @classmethod
    def get_default(cls):
        """Retourne l'entreprise par défaut, ou la première si aucune n'est marquée."""
        return cls.objects.filter(est_defaut=True).first() or cls.objects.first()

    @classmethod
    def get_instance(cls):
        """Alias rétrocompatible pour get_default()."""
        return cls.get_default()

    @classmethod
    def get_or_create_default(cls):
        """Retourne l'entreprise par défaut ou crée une instance par défaut."""
        instance = cls.objects.filter(est_defaut=True).first()
        if not instance:
            instance = cls.objects.first()
        if instance and not instance.est_defaut:
            instance.est_defaut = True
            instance.save(update_fields=['est_defaut'])
            return instance
        if not instance:
            instance = cls.objects.create(
                raison_sociale='Altius Academy SNC',
                forme_juridique='SNC',
                ide_number='CHE-138.647.564',
                est_defaut=True,
                ch_id='CH-550-1237137-3',
                ofrc_id='1613327',
                siege='Echallens',
                canton_rc='VD',
                but='offrir des services de haute qualité aux particuliers et aux entreprises '
                    'dans des domaines variés tels que l\'ingénierie, l\'éducation et d\'autres '
                    'prestations de services, en visant l\'excellence et la satisfaction du client.',
                date_creation='2023-11-01',
                date_inscription_rc='2023-11-16',
                statut='ACTIVE',
                associes=[
                    {
                        'nom': 'Guindo',
                        'prenom': 'Paul dit Akouni',
                        'origine': 'du Mali',
                        'domicile': 'Echallens',
                        'signature': 'individuelle'
                    },
                    {
                        'nom': 'Guindo',
                        'prenom': 'Sandy',
                        'origine': 'de Lausanne',
                        'domicile': 'Echallens',
                        'signature': 'individuelle'
                    }
                ],
                derniere_publication_fosc='No. 1005890308 de 21.11.2023 - Nouvelle inscription'
            )
        return instance


class Client(BaseModel):
    """Client de la fiduciaire"""

    FORME_JURIDIQUE_CHOICES = [
        # Formes suisses
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
        # Formes internationales / sans registre
        ('PP', _('Personne physique')),
        ('AUTRE', _('Autre')),
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

    # Entreprise (fiduciaire) rattachée
    entreprise = models.ForeignKey(
        Entreprise,
        on_delete=models.PROTECT,
        related_name='clients',
        null=True,
        blank=True,
        verbose_name=_('Entreprise')
    )

    # Numéros officiels (tous optionnels — clients sans registre du commerce,
    # personnes physiques, clients européens/africains)
    ide_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^CHE-\d{3}\.\d{3}\.\d{3}$',
                                   'Format IDE invalide (CHE-XXX.XXX.XXX)')],
        help_text='Format: CHE-123.456.789 (optionnel)',
        verbose_name=_('Numéro IDE')
    )
    ch_id = models.CharField(
        max_length=30,
        blank=True,
        help_text='Numéro CH-ID (CH-XXX-XXXXXXX-X)',
        verbose_name=_('CH-ID')
    )
    ofrc_id = models.CharField(
        max_length=20,
        blank=True,
        help_text="Numéro de l'Office fédéral du registre du commerce",
        verbose_name=_('OFRC-ID')
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

    # Logo
    logo = models.ImageField(
        upload_to='clients/logos/',
        blank=True,
        null=True,
        verbose_name=_('Logo'),
        help_text=_('Logo du client (utilisé sur les documents)')
    )

    # Dates importantes
    date_creation = models.DateField(null=True, blank=True, verbose_name=_('Date de création entreprise'))
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
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    related_name='clients_responsable',
                                    null=True, blank=True,
                                    verbose_name=_('Responsable interne'),
                                    help_text=_('Collaborateur interne en charge de ce dossier client'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    # Régime fiscal par défaut (pour les mandats de ce client)
    regime_fiscal_defaut = models.ForeignKey(
        'tva.RegimeFiscal', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='clients',
        verbose_name=_('Régime fiscal par défaut')
    )

    # Hiérarchie clients (fiduciaire → client → sous-client)
    parent_client = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sous_clients_set', verbose_name=_('Client parent')
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            self.raison_sociale,
            self.nom_commercial,
            self.description,
            f"IDE: {self.ide_number}" if self.ide_number else '',
            f"TVA: {self.tva_number}" if self.tva_number else '',
            self.email or '',
            self.notes,
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'clients'
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')
        ordering = ['raison_sociale']
        indexes = [
            models.Index(fields=['raison_sociale', 'statut']),
            models.Index(fields=['ide_number']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['ide_number'],
                condition=~models.Q(ide_number=''),
                name='unique_ide_number_non_vide',
            ),
        ]

    def __str__(self):
        if self.ide_number:
            return f"{self.raison_sociale} ({self.ide_number})"
        return self.raison_sociale

    @property
    def mandats_actifs(self):
        return self.mandats.filter(statut='ACTIF')

    @property
    def sous_clients(self):
        return self.sous_clients_set.filter(is_active=True)

    @property
    def is_sous_client(self):
        return self.parent_client_id is not None

    def get_logo(self):
        """Retourne le logo du client, ou celui de son entreprise, ou None."""
        if self.logo:
            return self.logo
        if self.entreprise_id and self.entreprise.logo:
            return self.entreprise.logo
        return None


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

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            f"{self.prenom} {self.nom}",
            self.fonction or '',
            self.email or '',
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'contacts'
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.client.raison_sociale}"


# =============================================================================
# TABLES DE RÉFÉRENCE GÉNÉRIQUES
# =============================================================================

class Periodicite(models.Model):
    """
    Table générique pour les périodicités.

    Réutilisable dans:
    - Mandats (périodicité de facturation)
    - TVA (déclaration trimestrielle, semestrielle, annuelle)
    - Rapports (génération périodique)
    - Tâches récurrentes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_('Code'),
        help_text=_('Code unique (ex: MENSUEL, TRIMESTRIEL)')
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_('Libellé')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )

    # Paramètres de calcul
    nombre_mois = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_('Nombre de mois'),
        help_text=_('Nombre de mois entre chaque occurrence')
    )
    nombre_par_an = models.PositiveSmallIntegerField(
        default=12,
        verbose_name=_('Occurrences par an'),
        help_text=_('Nombre de fois par an (12=mensuel, 4=trimestriel, etc.)')
    )

    # Ordre d'affichage
    ordre = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Ordre d\'affichage')
    )

    # Statut
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Actif')
    )

    class Meta:
        db_table = 'periodicites'
        verbose_name = _('Périodicité')
        verbose_name_plural = _('Périodicités')
        ordering = ['ordre', 'nombre_mois']

    def __str__(self):
        return self.libelle

    @classmethod
    def get_default(cls):
        """Retourne la périodicité par défaut (mensuelle)"""
        return cls.objects.filter(code='MENSUEL', is_active=True).first()


class TypeMandat(models.Model):
    """
    Types de mandats de la fiduciaire.

    Exemples:
    - Comptabilité
    - TVA
    - Salaires
    - Conseil fiscal
    - Révision
    - Création d'entreprise
    - Mandat global
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_('Code'),
        help_text=_('Code unique (ex: COMPTA, TVA, SALAIRES)')
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_('Libellé')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )

    # Icône et couleur pour l'interface
    icone = models.CharField(
        max_length=50,
        blank=True,
        default='ph-briefcase',
        verbose_name=_('Icône'),
        help_text=_('Classe CSS de l\'icône (Phosphor Icons)')
    )
    couleur = models.CharField(
        max_length=20,
        blank=True,
        default='primary',
        verbose_name=_('Couleur'),
        help_text=_('Classe Bootstrap (primary, success, warning, etc.)')
    )

    # Périodicité par défaut pour ce type
    periodicite_defaut = models.ForeignKey(
        Periodicite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Périodicité par défaut'),
        help_text=_('Périodicité suggérée par défaut pour ce type de mandat')
    )

    # Modules associés
    modules_actifs = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Modules actifs'),
        help_text=_('Liste des modules activés par défaut: ["compta", "tva", "salaires"]')
    )

    # Ordre d'affichage
    ordre = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Ordre d\'affichage')
    )

    # Statut
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Actif')
    )

    class Meta:
        db_table = 'types_mandats'
        verbose_name = _('Type de mandat')
        verbose_name_plural = _('Types de mandats')
        ordering = ['ordre', 'libelle']

    def __str__(self):
        return self.libelle


class TypeFacturation(models.Model):
    """
    Types de facturation pour les mandats.

    Exemples:
    - Forfait (montant fixe)
    - Taux horaire
    - Mixte (forfait + dépassement horaire)
    - Abonnement
    - Au résultat
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_('Code'),
        help_text=_('Code unique (ex: FORFAIT, HORAIRE, MIXTE)')
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_('Libellé')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )

    # Configuration
    necessite_forfait = models.BooleanField(
        default=False,
        verbose_name=_('Nécessite un montant forfait'),
        help_text=_('Si coché, le montant forfaitaire est obligatoire')
    )
    necessite_taux_horaire = models.BooleanField(
        default=False,
        verbose_name=_('Nécessite un taux horaire'),
        help_text=_('Si coché, le taux horaire est obligatoire')
    )

    # Ordre d'affichage
    ordre = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Ordre d\'affichage')
    )

    # Statut
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Actif')
    )

    class Meta:
        db_table = 'types_facturation'
        verbose_name = _('Type de facturation')
        verbose_name_plural = _('Types de facturation')
        ordering = ['ordre', 'libelle']

    def __str__(self):
        return self.libelle

    @classmethod
    def get_default(cls):
        """Retourne le type de facturation par défaut (horaire)"""
        return cls.objects.filter(code='HORAIRE', is_active=True).first()


# =============================================================================
# MANDAT
# =============================================================================

class Mandat(BaseModel):
    """Mandat de prestation"""

    # Conserver les choices pour compatibilité et migration
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

    TYPE_FACTURATION_CHOICES = [
        ('FORFAIT', _('Forfait')),
        ('HORAIRE', _('Taux horaire')),
        ('MIXTE', _('Mixte')),
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

    # Nouveau: Référence vers TypeMandat
    type_mandat_ref = models.ForeignKey(
        TypeMandat,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='mandats',
        verbose_name=_('Type de mandat'),
        help_text=_('Type de mandat (nouvelle table)')
    )
    # Ancien champ conservé pour compatibilité/migration
    type_mandat = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
        verbose_name=_('Type de mandat (ancien)'),
        blank=True
    )

    # Période
    date_debut = models.DateField(verbose_name=_('Date de début'))
    date_fin = models.DateField(null=True, blank=True, verbose_name=_('Date de fin'))

    # Nouveau: Référence vers Periodicite
    periodicite_ref = models.ForeignKey(
        Periodicite,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='mandats',
        verbose_name=_('Périodicité'),
        help_text=_('Périodicité (nouvelle table)')
    )
    # Ancien champ conservé pour compatibilité/migration
    periodicite = models.CharField(
        max_length=20,
        choices=PERIODICITE_CHOICES,
        verbose_name=_('Périodicité (ancien)'),
        blank=True
    )

    # Honoraires
    # Nouveau: Référence vers TypeFacturation
    type_facturation_ref = models.ForeignKey(
        TypeFacturation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='mandats',
        verbose_name=_('Type de facturation'),
        help_text=_('Type de facturation (nouvelle table)')
    )
    # Ancien champ conservé pour compatibilité/migration
    type_facturation = models.CharField(
        max_length=20,
        choices=TYPE_FACTURATION_CHOICES,
        default='HORAIRE',
        verbose_name=_('Type de facturation (ancien)'),
        blank=True
    )
    budget_prevu = models.DecimalField(max_digits=15, decimal_places=2,
                                       null=True, blank=True, verbose_name=_('Budget prévu'))
    budget_reel = models.DecimalField(max_digits=15, decimal_places=2,
                                      default=0, verbose_name=_('Budget réel'))
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

    # Support international
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal', on_delete=models.PROTECT,
        related_name='mandats',
        verbose_name=_('Régime fiscal')
    )
    devise = models.ForeignKey(
        Devise, on_delete=models.PROTECT,
        related_name='mandats',
        verbose_name=_('Devise'),
        db_column='devise_mandat'
    )

    # Plan comptable actif (lien direct pour cohérence régime fiscal)
    plan_comptable_actif = models.ForeignKey(
        'comptabilite.PlanComptable',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='mandats_actifs',
        verbose_name=_('Plan comptable actif'),
        help_text=_('Plan comptable utilisé par ce mandat')
    )

    @property
    def plan_comptable(self):
        """Retourne le plan comptable actif ou le premier plan disponible."""
        if self.plan_comptable_actif_id:
            return self.plan_comptable_actif
        return self.plans_comptables.first()

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        # Vérifier cohérence entre régime fiscal et plan comptable actif
        if self.plan_comptable_actif and self.regime_fiscal_id:
            type_plan_attendu = self.regime_fiscal.type_plan_comptable
            if type_plan_attendu and self.plan_comptable_actif.type_plan != type_plan_attendu:
                raise ValidationError({
                    'plan_comptable_actif': _(
                        "Le plan comptable doit être de type « %(attendu)s » "
                        "pour le régime fiscal « %(regime)s »."
                    ) % {
                        'attendu': type_plan_attendu,
                        'regime': self.regime_fiscal,
                    }
                })

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            f"Mandat {self.numero}",
            self.client.raison_sociale if self.client else '',
            self.description,
            self.conditions_particulieres,
        ]
        return ' '.join(filter(None, parts))

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

    @property
    def budget_consomme_pourcent(self):
        from decimal import Decimal
        if self.budget_prevu and self.budget_prevu > 0:
            return (self.budget_reel / self.budget_prevu * 100).quantize(Decimal("0.1"))
        return Decimal("0")

    def recalculer_budget_reel(self):
        """Recalcule le budget réel à partir des budgets réels des positions."""
        from decimal import Decimal
        total = self.positions.filter(is_active=True).aggregate(
            total=models.Sum("budget_reel")
        )["total"] or Decimal("0")
        self.budget_reel = total
        self.save(update_fields=["budget_reel"])


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

    # Assignation multiple
    assignes = models.ManyToManyField(
        User, related_name='taches_assignees', blank=True,
        verbose_name=_('Assignés à')
    )
    cree_par = models.ForeignKey(User, on_delete=models.PROTECT,
                                 related_name='taches_creees',
                                 verbose_name=_('Créé par'))

    # Rattachement
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='taches',
                               verbose_name=_('Mandat'))

    # Prestation associée
    prestation = models.ForeignKey(
        'facturation.Prestation', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='taches',
        verbose_name=_('Prestation')
    )

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
            models.Index(fields=['date_echeance', 'statut']),
        ]

    def __str__(self):
        return self.titre


# =============================================================================
# ACCES MANDAT (Permissions clients externes sur les mandats)
# =============================================================================

class AccesMandat(BaseModel):
    """
    Lie un utilisateur CLIENT externe à un mandat avec des permissions granulaires.

    Permet de:
    - Définir quels mandats un client externe peut voir
    - Configurer les permissions spécifiques (documents, factures, etc.)
    - Gérer la responsabilité et les invitations
    """

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='acces_mandats',
        verbose_name=_('Utilisateur')
    )
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='acces_utilisateurs',
        verbose_name=_('Mandat')
    )

    # Responsabilité côté client
    est_responsable = models.BooleanField(
        default=False,
        verbose_name=_('Est responsable'),
        help_text=_('Le responsable peut inviter d\'autres utilisateurs pour ce mandat')
    )

    # Permissions granulaires utilisant les permissions Django
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        verbose_name=_('Permissions'),
        help_text=_('Permissions Django sur ce mandat')
    )

    # Limites d'invitation (configurable par le staff)
    limite_invitations = models.PositiveIntegerField(
        default=5,
        verbose_name=_('Limite d\'invitations'),
        help_text=_('Nombre maximum d\'utilisateurs que ce responsable peut inviter')
    )
    invitations_restantes = models.PositiveIntegerField(
        default=5,
        verbose_name=_('Invitations restantes')
    )

    # Période d'accès (optionnel)
    date_debut_acces = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de début d\'accès')
    )
    date_fin_acces = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de fin d\'accès')
    )

    # Qui a accordé l'accès
    accorde_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='acces_accordes',
        verbose_name=_('Accès accordé par')
    )

    # Notes internes
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes'),
        help_text=_('Notes internes sur cet accès')
    )

    class Meta:
        db_table = 'acces_mandats'
        verbose_name = _('Accès mandat')
        verbose_name_plural = _('Accès mandats')
        unique_together = ['utilisateur', 'mandat']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['utilisateur', 'is_active']),
            models.Index(fields=['mandat', 'is_active']),
        ]

    def __str__(self):
        return f"{self.utilisateur.get_full_name() or self.utilisateur.username} → {self.mandat.numero}"

    def save(self, *args, **kwargs):
        # S'assurer que invitations_restantes ne dépasse pas la limite
        if self.invitations_restantes > self.limite_invitations:
            self.invitations_restantes = self.limite_invitations
        super().save(*args, **kwargs)

    def peut_inviter(self):
        """Vérifie si l'utilisateur peut encore inviter"""
        return self.est_responsable and self.invitations_restantes > 0 and self.is_active

    def utiliser_invitation(self):
        """Décrémente le compteur d'invitations"""
        if self.peut_inviter():
            self.invitations_restantes -= 1
            self.save(update_fields=['invitations_restantes', 'updated_at'])
            return True
        return False

    def est_acces_valide(self):
        """Vérifie si l'accès est actuellement valide"""
        from django.utils import timezone
        today = timezone.now().date()

        if not self.is_active:
            return False

        if self.date_debut_acces and today < self.date_debut_acces:
            return False

        if self.date_fin_acces and today > self.date_fin_acces:
            return False

        return True

    def has_permission(self, permission_codename):
        """Vérifie si l'accès inclut une permission spécifique"""
        return self.permissions.filter(codename=permission_codename).exists()


# =============================================================================
# COLLABORATEUR FIDUCIAIRE (Affectations prestataires → mandats)
# =============================================================================

class CollaborateurFiduciaire(BaseModel):
    """
    Affectation d'un prestataire fiduciaire à des mandats spécifiques.
    Différent de AccesMandat qui gère les utilisateurs CLIENT.

    Ce modèle permet de:
    - Affecter des prestataires externes (type_collaborateur=PRESTATAIRE) à des mandats
    - Définir des périodes d'affectation
    - Optionnellement configurer un taux horaire spécifique au mandat
    """

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='affectations_mandats',
        verbose_name=_("Prestataire"),
        limit_choices_to={'type_utilisateur': 'STAFF', 'type_collaborateur': 'PRESTATAIRE'}
    )
    mandat = models.ForeignKey(
        'Mandat',
        on_delete=models.CASCADE,
        related_name='prestataires_affectes',
        verbose_name=_("Mandat")
    )

    role_sur_mandat = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Rôle sur ce mandat"),
        help_text=_("Ex: Comptable externe, Réviseur, Conseiller fiscal")
    )

    date_debut = models.DateField(verbose_name=_("Date de début"))
    date_fin = models.DateField(null=True, blank=True, verbose_name=_("Date de fin"))

    taux_horaire = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name=_("Taux horaire spécifique"),
        help_text=_("Taux horaire pour ce mandat (si différent du taux global)")
    )

    notes = models.TextField(blank=True, verbose_name=_("Notes"))

    class Meta:
        db_table = 'collaborateurs_fiduciaire'
        verbose_name = _("Affectation prestataire")
        verbose_name_plural = _("Affectations prestataires")
        unique_together = ['utilisateur', 'mandat']
        indexes = [
            models.Index(fields=['utilisateur', 'is_active']),
            models.Index(fields=['mandat', 'is_active']),
        ]

    def __str__(self):
        return f"{self.utilisateur.get_full_name() or self.utilisateur.username} → {self.mandat.numero}"

    def est_affectation_valide(self):
        """Vérifie si l'affectation est actuellement valide"""
        from django.utils import timezone
        today = timezone.now().date()

        if not self.is_active:
            return False

        if self.date_debut and today < self.date_debut:
            return False

        if self.date_fin and today > self.date_fin:
            return False

        return True


# =============================================================================
# INVITATION (Système d'invitation par email)
# =============================================================================

class Invitation(BaseModel):
    """
    Invitation à rejoindre la plateforme ou à accéder à un mandat.

    Quatre types d'invitation:
    1. STAFF: Collaborateur interne (employé fiduciaire)
    2. STAFF_PRESTATAIRE: Prestataire externe fiduciaire
    3. CLIENT: Client externe (employé d'un client)
    4. CLIENT_PRESTATAIRE: Prestataire d'un client
    """

    class TypeInvitation(models.TextChoices):
        STAFF = 'STAFF', _('Collaborateur interne')
        STAFF_PRESTATAIRE = 'STAFF_PRESTATAIRE', _('Prestataire externe')
        CLIENT = 'CLIENT', _('Client externe')
        CLIENT_PRESTATAIRE = 'CLIENT_PRESTATAIRE', _('Prestataire client')

    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', _('En attente')
        ACCEPTEE = 'ACCEPTEE', _('Acceptée')
        EXPIREE = 'EXPIREE', _('Expirée')
        ANNULEE = 'ANNULEE', _('Annulée')

    # Informations de base
    email = models.EmailField(verbose_name=_('Email'))
    type_invitation = models.CharField(
        max_length=20,
        choices=TypeInvitation.choices,
        verbose_name=_('Type d\'invitation')
    )

    # Token sécurisé pour le lien d'invitation
    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_('Token')
    )
    # Code court pour partage verbal/SMS (6 caractères alphanumériques majuscules)
    code_court = models.CharField(
        max_length=8,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Code d\'invitation'),
        help_text=_('Code court à partager (ex: AB3K7X)')
    )
    date_expiration = models.DateTimeField(
        verbose_name=_('Date d\'expiration')
    )

    # Qui a invité
    invite_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='invitations_envoyees',
        verbose_name=_('Invité par')
    )

    # Pour les invitations CLIENT: le mandat concerné
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invitations',
        verbose_name=_('Mandat'),
        help_text=_('Mandat auquel l\'invité aura accès (pour les clients)')
    )

    # Pour les invitations STAFF_PRESTATAIRE: mandats assignés
    mandats_assignes = models.ManyToManyField(
        'Mandat',
        blank=True,
        related_name='invitations_prestataires',
        verbose_name=_('Mandats assignés'),
        help_text=_('Mandats auxquels le prestataire sera affecté')
    )

    # Rôle pré-assigné (pour STAFF) ou permissions (pour CLIENT)
    role_preassigne = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitations',
        verbose_name=_('Rôle pré-assigné'),
        help_text=_('Rôle attribué à l\'utilisateur lors de l\'acceptation')
    )

    # Permissions AccesMandat à appliquer (pour CLIENT)
    permissions_acces = models.ManyToManyField(
        Permission,
        blank=True,
        verbose_name=_('Permissions'),
        help_text=_('Permissions à accorder sur le mandat')
    )

    # Configuration de l'accès (pour CLIENT)
    est_responsable_prevu = models.BooleanField(
        default=False,
        verbose_name=_('Sera responsable'),
        help_text=_('L\'invité sera responsable du mandat côté client')
    )
    limite_invitations_prevue = models.PositiveIntegerField(
        default=5,
        verbose_name=_('Limite d\'invitations prévue')
    )

    # Statut
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        db_index=True,
        verbose_name=_('Statut')
    )

    # Résultat
    utilisateur_cree = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitation_origine',
        verbose_name=_('Utilisateur créé')
    )
    date_acceptation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date d\'acceptation')
    )

    # Forcer le changement de mot de passe
    forcer_changement_mdp = models.BooleanField(
        default=True,
        verbose_name=_('Forcer changement mot de passe'),
        help_text=_('L\'utilisateur devra changer son mot de passe à la première connexion')
    )

    # Message personnalisé
    message_personnalise = models.TextField(
        blank=True,
        verbose_name=_('Message personnalisé'),
        help_text=_('Message inclus dans l\'email d\'invitation')
    )

    class Meta:
        db_table = 'invitations'
        verbose_name = _('Invitation')
        verbose_name_plural = _('Invitations')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'statut']),
            models.Index(fields=['token']),
            models.Index(fields=['code_court']),
            models.Index(fields=['date_expiration', 'statut']),
        ]

    def __str__(self):
        return f"Invitation {self.email} ({self.get_type_invitation_display()})"

    def save(self, *args, **kwargs):
        # Générer le token si nécessaire
        if not self.token:
            self.token = self.generer_token()
        # Générer le code court si nécessaire
        if not self.code_court:
            self.code_court = self.generer_code_court()
        super().save(*args, **kwargs)

    @staticmethod
    def generer_token():
        """Génère un token sécurisé unique"""
        import secrets
        return secrets.token_urlsafe(48)

    @staticmethod
    def generer_code_court():
        """Génère un code court unique de 6 caractères alphanumériques majuscules"""
        import secrets
        import string
        alphabet = string.ascii_uppercase + string.digits
        # Exclure les caractères ambigus (0/O, 1/I/L)
        alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
        for _ in range(100):  # Max tentatives
            code = ''.join(secrets.choice(alphabet) for _ in range(6))
            if not Invitation.objects.filter(code_court=code).exists():
                return code
        raise ValueError("Impossible de générer un code court unique")

    def est_valide(self):
        """Vérifie si l'invitation est toujours valide"""
        from django.utils import timezone
        return (
            self.statut == self.Statut.EN_ATTENTE and
            self.date_expiration > timezone.now()
        )

    def marquer_expiree(self):
        """Marque l'invitation comme expirée"""
        if self.statut == self.Statut.EN_ATTENTE:
            self.statut = self.Statut.EXPIREE
            self.save(update_fields=['statut', 'updated_at'])

    def annuler(self):
        """Annule l'invitation"""
        if self.statut == self.Statut.EN_ATTENTE:
            self.statut = self.Statut.ANNULEE
            self.save(update_fields=['statut', 'updated_at'])

    def accepter(self, utilisateur):
        """Marque l'invitation comme acceptée"""
        from django.utils import timezone
        self.statut = self.Statut.ACCEPTEE
        self.utilisateur_cree = utilisateur
        self.date_acceptation = timezone.now()
        self.save(update_fields=['statut', 'utilisateur_cree', 'date_acceptation', 'updated_at'])

    def get_absolute_url(self):
        """Retourne l'URL d'acceptation de l'invitation"""
        from django.urls import reverse
        return reverse('core:invitation-accept', kwargs={'token': self.token})


class ModeleDocumentPDF(BaseModel):
    """
    Template de style PDF configurable par type de document et par mandat.
    Permet la personnalisation visuelle (couleurs, polices, marges, textes, blocs)
    via le Document Studio.
    """

    class TypeDocument(models.TextChoices):
        FACTURE = 'FACTURE', _('Facture')
        AVOIR = 'AVOIR', _('Avoir')
        ACOMPTE = 'ACOMPTE', _("Facture d'acompte")
        FICHE_SALAIRE = 'FICHE_SALAIRE', _('Fiche de salaire')
        CERTIFICAT_SALAIRE = 'CERTIFICAT_SALAIRE', _('Certificat de salaire')
        CERTIFICAT_TRAVAIL = 'CERTIFICAT_TRAVAIL', _('Certificat de travail')
        DECLARATION_COTISATIONS = 'DECLARATION_COTISATIONS', _('Déclaration de cotisations')

    class PoliceChoices(models.TextChoices):
        HELVETICA = 'Helvetica', 'Helvetica'
        TIMES = 'Times-Roman', 'Times Roman'
        COURIER = 'Courier', 'Courier'

    nom = models.CharField(max_length=200, verbose_name=_('Nom du modèle'))
    type_document = models.CharField(
        max_length=30,
        choices=TypeDocument.choices,
        db_index=True,
        verbose_name=_('Type de document')
    )
    mandat = models.ForeignKey(
        'Mandat',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='modeles_pdf',
        verbose_name=_('Mandat'),
        help_text=_('Laisser vide pour un modèle système par défaut')
    )

    # Identité visuelle
    logo = models.FileField(
        upload_to='modeles_pdf/logos/',
        null=True,
        blank=True,
        verbose_name=_('Logo personnalisé')
    )
    utiliser_logo_defaut = models.BooleanField(
        default=True,
        verbose_name=_('Utiliser le logo par défaut')
    )

    # Couleurs
    couleur_primaire = models.CharField(
        max_length=7, default='#088178',
        verbose_name=_('Couleur primaire')
    )
    couleur_accent = models.CharField(
        max_length=7, default='#2c3e50',
        verbose_name=_('Couleur accent')
    )
    couleur_texte = models.CharField(
        max_length=7, default='#333333',
        verbose_name=_('Couleur du texte')
    )

    # Police
    police = models.CharField(
        max_length=50,
        choices=PoliceChoices.choices,
        default=PoliceChoices.HELVETICA,
        verbose_name=_('Police')
    )

    # Marges (en mm)
    marge_haut = models.PositiveIntegerField(default=20, verbose_name=_('Marge haute (mm)'))
    marge_bas = models.PositiveIntegerField(default=25, verbose_name=_('Marge basse (mm)'))
    marge_gauche = models.PositiveIntegerField(default=20, verbose_name=_('Marge gauche (mm)'))
    marge_droite = models.PositiveIntegerField(default=15, verbose_name=_('Marge droite (mm)'))

    # Textes personnalisables
    textes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Textes'),
        help_text=_('Clés: entete, pied_page, introduction, conclusion, conditions, mentions_legales')
    )

    # Blocs visibles (toggles)
    blocs_visibles = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Blocs visibles'),
        help_text=_('Clés: logo, qr_bill, conditions, introduction, conclusion, etc.')
    )

    # Config avancée spécifique au type
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Configuration avancée')
    )

    est_defaut = models.BooleanField(
        default=False,
        verbose_name=_('Modèle par défaut'),
        help_text=_('Un seul modèle par défaut par type et par mandat')
    )

    class Meta:
        db_table = 'modeles_document_pdf'
        verbose_name = _('Modèle de document PDF')
        verbose_name_plural = _('Modèles de document PDF')
        ordering = ['type_document', 'nom']
        constraints = [
            models.UniqueConstraint(
                fields=['type_document', 'mandat'],
                condition=models.Q(est_defaut=True),
                name='unique_defaut_par_type_mandat'
            )
        ]

    def __str__(self):
        mandat_label = self.mandat.nom if self.mandat else _('Système')
        return f"{self.nom} ({self.get_type_document_display()}) - {mandat_label}"

    @classmethod
    def get_effectif(cls, type_document, mandat=None):
        """
        Retourne le modèle effectif pour un type de document et un mandat.
        Priorité : modèle du mandat > modèle système (mandat=None).
        """
        if mandat:
            modele = cls.objects.filter(
                type_document=type_document,
                mandat=mandat,
                est_defaut=True,
                is_active=True
            ).first()
            if modele:
                return modele
        return cls.objects.filter(
            type_document=type_document,
            mandat__isnull=True,
            est_defaut=True,
            is_active=True
        ).first()

    def to_style_config(self):
        """Convertit le modèle en dictionnaire de configuration pour les services PDF."""
        from reportlab.lib.colors import HexColor
        from reportlab.lib.units import mm

        return {
            'couleur_primaire': HexColor(self.couleur_primaire),
            'couleur_accent': HexColor(self.couleur_accent),
            'couleur_texte': HexColor(self.couleur_texte),
            'police': self.police,
            'marge_haut': self.marge_haut * mm,
            'marge_bas': self.marge_bas * mm,
            'marge_gauche': self.marge_gauche * mm,
            'marge_droite': self.marge_droite * mm,
            'textes': self.textes or {},
            'blocs_visibles': self.blocs_visibles or {},
            'config': self.config or {},
            'utiliser_logo_defaut': self.utiliser_logo_defaut,
            'logo': self.logo if self.logo and not self.utiliser_logo_defaut else None,
        }


# =============================================================================
# PARAMETRES METIER (Choix configurables par l'utilisateur)
# =============================================================================

class ParametreMetier(BaseModel):
    """
    Stocke les types/choix métier configurables par l'utilisateur.
    Remplace les CHOICES hardcodées en permettant aux clients de les modifier.

    Chaque entrée représente une valeur possible dans une liste de choix.
    Groupée par module + categorie. Le champ 'code' est la valeur technique
    stockée dans les modèles existants (compatible avec les CharField choices).
    """

    MODULE_CHOICES = [
        ('core', _('Général')),
        ('salaires', _('Salaires')),
        ('facturation', _('Facturation')),
        ('comptabilite', _('Comptabilité')),
        ('fiscalite', _('Fiscalité')),
        ('tva', _('TVA')),
        ('projets', _('Projets')),
        ('documents', _('Documents')),
        ('analytics', _('Analytics')),
    ]

    module = models.CharField(
        max_length=30,
        choices=MODULE_CHOICES,
        db_index=True,
        verbose_name=_('Module'),
        help_text=_('Module auquel appartient ce paramètre')
    )
    categorie = models.CharField(
        max_length=60,
        db_index=True,
        verbose_name=_('Catégorie'),
        help_text=_('Ex: type_contrat, type_facture, mode_paiement, type_journal...')
    )
    code = models.CharField(
        max_length=50,
        verbose_name=_('Code technique'),
        help_text=_('Valeur technique (ex: CDI, VIREMENT, SA). Ne pas modifier après création.')
    )
    libelle = models.CharField(
        max_length=200,
        verbose_name=_('Libellé'),
        help_text=_('Texte affiché à l\'utilisateur')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description ou aide contextuelle')
    )
    ordre = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Ordre d\'affichage')
    )
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parametres_metier',
        verbose_name=_('Régime fiscal'),
        help_text=_('Si renseigné, ce choix n\'apparaît que pour ce régime fiscal')
    )
    systeme = models.BooleanField(
        default=False,
        verbose_name=_('Paramètre système'),
        help_text=_('Si vrai, ne peut pas être supprimé par l\'utilisateur')
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Métadonnées'),
        help_text=_('Données supplémentaires (couleur, icône, config spécifique...)')
    )

    class Meta:
        db_table = 'parametres_metier'
        verbose_name = _('Paramètre métier')
        verbose_name_plural = _('Paramètres métier')
        unique_together = ['module', 'categorie', 'code']
        ordering = ['module', 'categorie', 'ordre', 'libelle']
        indexes = [
            models.Index(fields=['module', 'categorie']),
            models.Index(fields=['module', 'categorie', 'is_active']),
        ]

    def __str__(self):
        return f"{self.libelle} ({self.code})"

    @classmethod
    def get_choices(cls, module, categorie, regime_fiscal=None, include_inactive=False):
        """
        Retourne les choix pour un module/catégorie, compatibles avec Django choices.
        Filtre optionnellement par régime fiscal.
        Falls back sur une liste vide si rien en DB.
        """
        qs = cls.objects.filter(module=module, categorie=categorie)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        if regime_fiscal:
            qs = qs.filter(
                models.Q(regime_fiscal=regime_fiscal) |
                models.Q(regime_fiscal__isnull=True)
            )
        return [(p.code, p.libelle) for p in qs]

    @classmethod
    def get_choices_with_default(cls, module, categorie, default_choices,
                                  regime_fiscal=None):
        """
        Retourne les choix DB si disponibles, sinon les choix par défaut hardcodés.
        Permet une migration progressive sans casser l'existant.
        """
        db_choices = cls.get_choices(module, categorie, regime_fiscal)
        return db_choices if db_choices else default_choices


# =============================================================================
# FICHIER JOINT (Pièce jointe générique réutilisable partout)
# =============================================================================

def fichier_joint_upload_path(instance, filename):
    """
    Chemin d'upload pour les fichiers joints génériques.
    Format: fichiers_joints/{content_type}/{object_id}/{uuid}/{filename}
    """
    ct = instance.content_type
    app_model = f"{ct.app_label}_{ct.model}" if ct else "unknown"
    return f"fichiers_joints/{app_model}/{instance.object_id}/{uuid.uuid4()}/{filename}"


class FichierJoint(BaseModel):
    """
    Pièce jointe générique réutilisable dans tout le projet.

    Utilise GenericForeignKey pour pouvoir être rattachée à n'importe quel
    modèle (TimeTracking, Tache, etc.) sans créer de table intermédiaire
    spécifique à chaque modèle.

    Usage dans un modèle cible :
        from django.contrib.contenttypes.fields import GenericRelation
        from core.models import FichierJoint

        class MonModele(BaseModel):
            fichiers_joints = GenericRelation(FichierJoint)

    Usage dans une vue :
        for f in request.FILES.getlist('fichiers'):
            FichierJoint.objects.create(
                content_object=mon_instance,
                fichier=f,
                nom_original=f.name,
                created_by=request.user,
            )
    """

    # Lien générique vers n'importe quel modèle
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        verbose_name=_('Type de contenu'),
        help_text=_('Modèle auquel ce fichier est rattaché')
    )
    object_id = models.UUIDField(
        verbose_name=_('ID objet'),
        help_text=_('Identifiant de l\'objet parent')
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    # Fichier
    fichier = models.FileField(
        upload_to=fichier_joint_upload_path,
        verbose_name=_('Fichier'),
        help_text=_('Fichier joint')
    )
    nom_original = models.CharField(
        max_length=255,
        verbose_name=_('Nom original'),
        help_text=_('Nom du fichier lors de l\'upload')
    )
    extension = models.CharField(
        max_length=20, blank=True,
        verbose_name=_('Extension'),
        help_text=_('Extension du fichier (pdf, jpg, etc.)')
    )
    mime_type = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Type MIME'),
        help_text=_('Type MIME du fichier')
    )
    taille = models.BigIntegerField(
        default=0,
        verbose_name=_('Taille'),
        help_text=_('Taille du fichier en octets')
    )
    hash_fichier = models.CharField(
        max_length=64, blank=True, db_index=True,
        verbose_name=_('Hash SHA-256'),
        help_text=_('Empreinte SHA-256 du fichier')
    )

    # Description optionnelle
    description = models.CharField(
        max_length=500, blank=True,
        verbose_name=_('Description'),
        help_text=_('Description ou commentaire sur ce fichier')
    )

    # Ordre d'affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name=_('Ordre'),
        help_text=_('Position d\'affichage dans la liste')
    )

    class Meta:
        db_table = 'fichiers_joints'
        verbose_name = _('Fichier joint')
        verbose_name_plural = _('Fichiers joints')
        ordering = ['ordre', 'created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id'], name='fj_ct_oid_idx'),
        ]

    def __str__(self):
        return self.nom_original

    def save(self, *args, **kwargs):
        if self.fichier and not self.nom_original:
            self.nom_original = os.path.basename(self.fichier.name)

        if self.nom_original and not self.extension:
            self.extension = os.path.splitext(self.nom_original)[1].lower().lstrip('.')

        if self.fichier and not self.taille:
            try:
                self.taille = self.fichier.size
            except (OSError, AttributeError):
                pass

        if self.fichier and not self.hash_fichier:
            try:
                hasher = hashlib.sha256()
                for chunk in self.fichier.chunks():
                    hasher.update(chunk)
                self.hash_fichier = hasher.hexdigest()
                self.fichier.seek(0)
            except (OSError, AttributeError):
                pass

        super().save(*args, **kwargs)


# =============================================================================
# MODEL EMBEDDING (vectorisation générique via pgvector)
# =============================================================================

class ModelEmbedding(models.Model):
    """
    Embedding vectoriel générique pour n'importe quel modèle.

    Utilise GenericForeignKey (même pattern que AuditLog, FichierJoint).
    Stocke un vecteur 768D dans pgvector pour la recherche sémantique.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Lien générique vers le modèle source
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        verbose_name=_('Type de contenu'),
    )
    object_id = models.UUIDField(verbose_name=_('ID objet'))
    content_object = GenericForeignKey('content_type', 'object_id')

    # Vecteur 768D (pgvector)
    from pgvector.django import VectorField
    embedding = VectorField(dimensions=768, verbose_name=_('Embedding'))

    # Métadonnées
    text_hash = models.CharField(
        max_length=64,
        verbose_name=_('Hash du texte'),
        help_text=_('SHA-256 du texte source, pour détecter les changements'),
    )
    text_preview = models.CharField(
        max_length=200, blank=True,
        verbose_name=_('Aperçu du texte'),
    )
    model_used = models.CharField(
        max_length=100, default='paraphrase-multilingual-mpnet-base-v2',
        verbose_name=_('Modèle utilisé'),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Créé le'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Modifié le'))

    class Meta:
        db_table = 'model_embeddings'
        verbose_name = _('Embedding de modèle')
        verbose_name_plural = _('Embeddings de modèles')
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id'],
                name='unique_model_embedding',
            ),
        ]
        indexes = [
            models.Index(fields=['content_type', 'object_id'], name='me_ct_oid_idx'),
            models.Index(fields=['content_type'], name='me_ct_idx'),
        ]

    def __str__(self):
        return f"Embedding {self.content_type} #{self.object_id}"

    @classmethod
    def search_similar(cls, embedding, content_type=None, limit=20, threshold=0.5, metric='cosine'):
        """
        Recherche les objets les plus similaires.

        La métrique de distance est configurable (cosine par défaut).
        Voir core.ai.distances pour les métriques disponibles :
        'cosine', 'l2', 'l1', 'jaccard', 'hamming'.

        Args:
            embedding: Vecteur de requête (list[float] 768D)
            content_type: Filtrer par ContentType (optionnel)
            limit: Nombre max de résultats
            threshold: Seuil de similarité (0-1, 1=identique)
            metric: Mesure de distance ('cosine', 'l2', 'l1', 'jaccard', 'hamming')

        Returns:
            QuerySet annoté avec 'distance' (plus petit = plus similaire)
        """
        from core.ai.distances import get_distance_function, threshold_for_metric

        distance_fn = get_distance_function(metric)
        max_distance = threshold_for_metric(metric, threshold)

        qs = cls.objects.annotate(
            distance=distance_fn('embedding', embedding)
        ).filter(
            distance__lt=max_distance
        )

        if content_type:
            qs = qs.filter(content_type=content_type)

        return qs.order_by('distance')[:limit]


# ══════════════════════════════════════════════════════════════
# CONTRATS
# ══════════════════════════════════════════════════════════════

class ModeleContrat(BaseModel):
    """
    Modèle/template de contrat (standard suisse ou personnalisé).

    Le fichier source est un Document existant dans la GED (S3/MinIO),
    éditable via OnlyOffice/NextCloud.
    """

    SOURCE_CHOICES = [
        ('CONFEDERATION', _('Standard Confédération')),
        ('FIDUCIAIRE', _('Standard fiduciaire')),
        ('PERSONNALISE', _('Personnalisé')),
    ]

    nom = models.CharField(max_length=255, verbose_name=_('Nom'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    categorie = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Catégorie'),
        help_text=_('Code ParametreMetier (module=contrats, categorie=type_contrat)')
    )
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default='FIDUCIAIRE',
        verbose_name=_('Source')
    )
    langue = models.CharField(
        max_length=5, default='fr',
        verbose_name=_('Langue')
    )
    document = models.ForeignKey(
        'documents.Document', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='modeles_contrat',
        verbose_name=_('Document template'),
        help_text=_('Fichier template dans la GED (DOCX, éditable via OnlyOffice)')
    )
    ordre = models.IntegerField(default=0, verbose_name=_('Ordre'))

    class Meta:
        db_table = 'modeles_contrat'
        verbose_name = _('Modèle de contrat')
        verbose_name_plural = _('Modèles de contrat')
        ordering = ['ordre', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.get_source_display()})"

    def texte_pour_embedding(self):
        parts = [
            f"Modèle contrat: {self.nom}",
            self.description,
            f"Source: {self.get_source_display()}",
            f"Catégorie: {self.categorie}" if self.categorie else '',
        ]
        return ' '.join(filter(None, parts))


class Contrat(BaseModel):
    """
    Contrat lié à un client/mandat.

    Le fichier du contrat est un Document dans la GED — stocké en S3,
    éditable via OnlyOffice, versionné, OCR-isé et vectorisé.
    """

    SENS_CHOICES = [
        ('EMIS', _('Émis')),
        ('RECU', _('Reçu')),
    ]

    STATUT_CHOICES = [
        ('BROUILLON', _('Brouillon')),
        ('ENVOYE', _('Envoyé')),
        ('SIGNE', _('Signé')),
        ('ACTIF', _('Actif')),
        ('EXPIRE', _('Expiré')),
        ('RESILIE', _('Résilié')),
        ('ANNULE', _('Annulé')),
    ]

    # Rattachement
    client = models.ForeignKey(
        'core.Client', on_delete=models.CASCADE,
        related_name='contrats', verbose_name=_('Client')
    )
    mandat = models.ForeignKey(
        'core.Mandat', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contrats',
        verbose_name=_('Mandat')
    )

    # Document GED (le fichier contrat lui-même)
    document = models.ForeignKey(
        'documents.Document', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contrats',
        verbose_name=_('Document'),
        help_text=_('Fichier du contrat dans la GED')
    )
    modele_source = models.ForeignKey(
        ModeleContrat, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contrats_generes',
        verbose_name=_('Modèle source')
    )

    # Identification
    numero = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Numéro'),
        help_text=_('Référence unique du contrat')
    )
    titre = models.CharField(max_length=255, verbose_name=_('Titre'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    categorie = models.CharField(
        max_length=50, blank=True,
        verbose_name=_('Catégorie'),
        help_text=_('Code ParametreMetier (module=contrats, categorie=type_contrat)')
    )
    sens = models.CharField(
        max_length=10, choices=SENS_CHOICES, default='EMIS',
        verbose_name=_('Sens'),
        help_text=_('Émis = envoyé au client, Reçu = reçu du client')
    )

    # Dates
    date_emission = models.DateField(
        null=True, blank=True, verbose_name=_("Date d'émission")
    )
    date_signature = models.DateField(
        null=True, blank=True, verbose_name=_('Date de signature')
    )
    date_debut = models.DateField(
        null=True, blank=True, verbose_name=_('Date de début')
    )
    date_fin = models.DateField(
        null=True, blank=True, verbose_name=_('Date de fin'),
        help_text=_('Vide = durée indéterminée')
    )

    # Renouvellement
    tacite_reconduction = models.BooleanField(
        default=False, verbose_name=_('Tacite reconduction')
    )
    delai_resiliation_jours = models.IntegerField(
        null=True, blank=True,
        verbose_name=_('Délai de résiliation (jours)')
    )
    date_prochaine_echeance = models.DateField(
        null=True, blank=True,
        verbose_name=_('Prochaine échéance')
    )

    # Financier
    montant = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name=_('Montant')
    )
    devise = models.ForeignKey(
        'core.Devise', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
        verbose_name=_('Devise')
    )

    # Signataires
    signataire_interne = models.CharField(
        max_length=255, blank=True,
        verbose_name=_('Signataire interne')
    )
    signataire_externe = models.CharField(
        max_length=255, blank=True,
        verbose_name=_('Signataire externe')
    )

    # Statut
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='BROUILLON',
        db_index=True, verbose_name=_('Statut')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        db_table = 'contrats'
        verbose_name = _('Contrat')
        verbose_name_plural = _('Contrats')
        ordering = ['-date_emission', '-created_at']
        indexes = [
            models.Index(fields=['client', 'statut']),
            models.Index(fields=['mandat', 'statut']),
        ]

    def __str__(self):
        return f"{self.numero or self.titre} - {self.client}"

    def texte_pour_embedding(self):
        parts = [
            f"Contrat: {self.titre}",
            f"N° {self.numero}" if self.numero else '',
            f"Client: {self.client.raison_sociale}" if self.client_id else '',
            f"Catégorie: {self.categorie}" if self.categorie else '',
            f"Sens: {self.get_sens_display()}",
            f"Statut: {self.get_statut_display()}",
            f"Du {self.date_debut}" if self.date_debut else '',
            f"Au {self.date_fin}" if self.date_fin else 'Durée indéterminée',
            f"Montant: {self.montant} {self.devise}" if self.montant else '',
            self.description,
            self.notes,
        ]
        return ' '.join(filter(None, parts))