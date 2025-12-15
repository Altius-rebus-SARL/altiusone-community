# apps/core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
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


class User(AbstractUser):
    """Utilisateur étendu"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ROLE_CHOICES = [
        ('ADMIN', _('Administrateur')),
        ('MANAGER', _('Chef de bureau')),
        ('COMPTABLE', _('Comptable')),
        ('ASSISTANT', _('Assistant')),
        ('CLIENT', _('Client')),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ASSISTANT', verbose_name=_('Rôle'))
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
        if self.is_superuser and self.role != 'ADMIN':
            self.role = 'ADMIN'
        super().save(*args, **kwargs)


class Adresse(models.Model):

    """Adresse réutilisable"""
    rue = models.CharField(max_length=255, verbose_name=_('Rue'))
    numero = models.CharField(max_length=10, blank=True, verbose_name=_('Numéro'))
    complement = models.CharField(max_length=100, blank=True, verbose_name=_('Complément'))
    npa = models.CharField(max_length=10, validators=[
        RegexValidator(r'^\d{4}$', 'NPA invalide (4 chiffres)')
    ], verbose_name=_('NPA'))
    localite = models.CharField(max_length=100, verbose_name=_('Localité'))
    canton = models.CharField(max_length=2, choices=SwissCantons.choices, verbose_name=_('Canton'))
    pays = models.CharField(max_length=2, default='CH', verbose_name=_('Pays'))

    class Meta:
        db_table = 'adresses'
        verbose_name = _('Adresse')
        verbose_name_plural = _('Adresses')

    def __str__(self):
        return f"{self.rue} {self.numero}, {self.npa} {self.localite}"


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