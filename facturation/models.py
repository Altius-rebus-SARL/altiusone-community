# apps/facturation/models.py
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation
from core.models import BaseModel, Devise, Mandat, Client, User, FichierJoint
from core.storage import InvoiceStorage
from decimal import Decimal
from datetime import datetime, date, timedelta
from tva.utils import get_taux_tva_defaut
import uuid


class TypePrestation(models.Model):
    """Type/catégorie de prestation (table de référence)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True, verbose_name=_('Code'))
    libelle = models.CharField(max_length=100, verbose_name=_('Libellé'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    icone = models.CharField(max_length=50, blank=True, default='ph-package', verbose_name=_('Icône'))
    couleur = models.CharField(max_length=20, blank=True, default='primary', verbose_name=_('Couleur'))
    ordre = models.PositiveSmallIntegerField(default=0, verbose_name=_('Ordre'))
    is_active = models.BooleanField(default=True, verbose_name=_('Actif'))

    class Meta:
        db_table = 'types_prestations'
        ordering = ['ordre', 'libelle']
        verbose_name = _('Type de prestation')
        verbose_name_plural = _('Types de prestations')

    def __str__(self):
        return self.libelle


class Prestation(BaseModel):
    """Prestation/Service fourni"""

    # Identification
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Code unique de la prestation")
    )
    libelle = models.CharField(
        max_length=255,
        verbose_name=_("Libellé"),
        help_text=_("Libellé de la prestation")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description détaillée de la prestation")
    )

    type_prestation = models.ForeignKey(
        TypePrestation,
        on_delete=models.PROTECT,
        related_name='prestations',
        verbose_name=_("Type de prestation"),
        help_text=_("Catégorie de la prestation")
    )

    # Tarification par défaut
    prix_unitaire_ht = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Prix unitaire HT"),
        help_text=_("Prix unitaire hors taxes par défaut")
    )
    unite = models.CharField(
        max_length=50,
        default='heure',
        verbose_name=_("Unité"),
        help_text=_("Unité de facturation (heure, jour, forfait, unité)")
    )

    taux_horaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Taux horaire"),
        help_text=_("Taux horaire de facturation")
    )

    # TVA
    soumis_tva = models.BooleanField(
        default=True,
        verbose_name=_("Soumis à TVA"),
        help_text=_("Indique si la prestation est soumise à TVA")
    )
    taux_tva_defaut = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("Taux TVA par défaut"),
        help_text=_("Taux de TVA appliqué par défaut (résolu depuis le régime fiscal si 0)")
    )
    taux_tva_ref = models.ForeignKey(
        'tva.TauxTVA',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prestations',
        verbose_name=_("Taux TVA (référence)"),
        help_text=_("Référence vers le taux TVA du régime fiscal")
    )

    # Compte comptable
    compte_produit = models.ForeignKey(
        'comptabilite.Compte',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Compte de produit"),
        help_text=_("Compte comptable de produit associé")
    )

    # Lien avec les types de mandats
    types_mandats = models.ManyToManyField(
        'core.TypeMandat',
        blank=True,
        related_name='prestations',
        verbose_name=_("Types de mandats"),
        help_text=_("Types de mandats auxquels cette prestation est associée")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Actif"),
        help_text=_("Indique si la prestation est active")
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            f"{self.code} {self.libelle}",
            self.description,
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'prestations'
        verbose_name = _('Prestation')
        verbose_name_plural = _('Prestations')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class ZoneGeographique(BaseModel):
    """Zone géographique pour le suivi du temps"""

    nom = models.CharField(
        max_length=255,
        verbose_name=_("Nom"),
        help_text=_("Nom de la zone géographique")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description de la zone")
    )
    geometrie = gis_models.PolygonField(
        srid=4326,
        verbose_name=_("Géométrie"),
        help_text=_("Polygone délimitant la zone")
    )
    couleur = models.CharField(
        max_length=7,
        default='#3388ff',
        verbose_name=_("Couleur"),
        help_text=_("Couleur d'affichage (hex)")
    )

    class Meta:
        db_table = 'zones_geographiques'
        verbose_name = _('Zone géographique')
        verbose_name_plural = _('Zones géographiques')
        ordering = ['nom']

    def __str__(self):
        return self.nom


class TarifMandat(BaseModel):
    """Tarification spécifique par mandat et prestation"""

    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='tarifs',
        verbose_name=_("Mandat"),
        help_text=_("Mandat concerné")
    )
    prestation = models.ForeignKey(
        'Prestation',
        on_delete=models.CASCADE,
        related_name='tarifs_mandat',
        verbose_name=_("Prestation"),
        help_text=_("Prestation concernée")
    )
    taux_horaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Taux horaire"),
        help_text=_("Taux horaire spécifique pour ce mandat/prestation")
    )
    prix_forfaitaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Prix forfaitaire"),
        help_text=_("Prix forfaitaire optionnel")
    )
    devise = models.ForeignKey(
        Devise,
        on_delete=models.PROTECT,
        db_column='devise',
        verbose_name=_("Devise"),
        help_text=_("Devise du tarif")
    )
    date_debut = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de début"),
        help_text=_("Début de validité du tarif")
    )
    date_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de fin"),
        help_text=_("Fin de validité du tarif")
    )

    class Meta:
        db_table = 'tarifs_mandat'
        verbose_name = _('Tarif mandat')
        verbose_name_plural = _('Tarifs mandat')
        unique_together = [('mandat', 'prestation')]
        ordering = ['mandat', 'prestation']

    def __str__(self):
        return f"{self.mandat} - {self.prestation} : {self.taux_horaire} {self.devise_id}/h"

    def save(self, *args, **kwargs):
        # Auto-populate devise from mandat if not set
        if not self.devise_id and self.mandat_id:
            self.devise_id = self.mandat.devise_id
        super().save(*args, **kwargs)

    def est_valide(self, date_ref=None):
        """Vérifie si le tarif est valide à une date donnée"""
        if date_ref is None:
            date_ref = date.today()
        if self.date_debut and date_ref < self.date_debut:
            return False
        if self.date_fin and date_ref > self.date_fin:
            return False
        return True


class CategorieTemps(models.Model):
    """Catégorie pour le temps interne et les absences.

    Permet de classifier le temps non lié à un mandat client :
    - INTERNE : formation, réunion, admin, prospection...
    - ABSENCE : vacances, maladie, congé personnel, service militaire...
    """

    TYPE_CHOICES = [
        ('INTERNE', _('Temps interne')),
        ('ABSENCE', _('Absence')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=30, unique=True,
        verbose_name=_('Code'),
        help_text=_('Code technique unique (ex: FORMATION, VACANCES)')
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_('Libellé'),
        help_text=_('Nom affiché (ex: Formation, Vacances)')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
    )
    type_categorie = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name=_('Type'),
        help_text=_('Interne = temps de travail non facturable, Absence = jour non travaillé')
    )
    icone = models.CharField(
        max_length=50, blank=True, default='ph-clock',
        verbose_name=_('Icône'),
    )
    couleur = models.CharField(
        max_length=20, blank=True, default='secondary',
        verbose_name=_('Couleur'),
    )
    # Pour les absences : impacte-t-il le solde vacances ?
    decompte_vacances = models.BooleanField(
        default=False,
        verbose_name=_('Décompte vacances'),
        help_text=_('Si coché, cette catégorie décompte du solde de jours de vacances')
    )
    # Pour les absences : impacte-t-il le compteur maladie ?
    decompte_maladie = models.BooleanField(
        default=False,
        verbose_name=_('Décompte maladie'),
        help_text=_('Si coché, cette catégorie incrémente le compteur jours maladie')
    )
    ordre = models.IntegerField(default=0, verbose_name=_('Ordre'))
    is_active = models.BooleanField(default=True, verbose_name=_('Actif'))

    class Meta:
        db_table = 'categories_temps'
        verbose_name = _('Catégorie de temps')
        verbose_name_plural = _('Catégories de temps')
        ordering = ['type_categorie', 'ordre', 'libelle']

    def __str__(self):
        return f"[{self.get_type_categorie_display()}] {self.libelle}"

    @property
    def est_interne(self):
        return self.type_categorie == 'INTERNE'

    @property
    def est_absence(self):
        return self.type_categorie == 'ABSENCE'


class TimeTracking(BaseModel):
    """Suivi du temps de travail sur les prestations, temps interne et absences"""

    TYPE_ENTREE_CHOICES = [
        ('CLIENT', _('Temps client (mandat)')),
        ('INTERNE', _('Temps interne')),
        ('ABSENCE', _('Absence')),
    ]

    # Type d'entrée
    type_entree = models.CharField(
        max_length=10,
        choices=TYPE_ENTREE_CHOICES,
        default='CLIENT',
        db_index=True,
        verbose_name=_("Type d'entrée"),
        help_text=_("CLIENT=mandat, INTERNE=formation/admin, ABSENCE=vacances/maladie")
    )

    # Catégorie interne/absence (obligatoire si type_entree != CLIENT)
    categorie = models.ForeignKey(
        CategorieTemps,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='temps',
        verbose_name=_("Catégorie"),
        help_text=_("Catégorie de temps interne ou type d'absence")
    )

    # Rattachement (mandat/prestation optionnels si INTERNE ou ABSENCE)
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='temps_travail',
        verbose_name=_("Mandat"),
        help_text=_("Mandat concerné (obligatoire pour type CLIENT)")
    )
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='temps_travail',
        verbose_name=_("Utilisateur"),
        help_text=_("Collaborateur ayant effectué le travail")
    )
    prestation = models.ForeignKey(
        Prestation,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='temps_travail',
        verbose_name=_("Prestation"),
        help_text=_("Type de prestation (obligatoire pour type CLIENT)")
    )

    # Temps
    date_travail = models.DateField(
        db_index=True,
        verbose_name=_("Date du travail"),
        help_text=_("Date à laquelle le travail a été effectué")
    )
    heure_debut = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Heure de début"),
        help_text=_("Heure de début du travail")
    )
    heure_fin = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Heure de fin"),
        help_text=_("Heure de fin du travail")
    )
    duree_minutes = models.IntegerField(
        verbose_name=_("Durée (minutes)"),
        help_text=_("Durée du travail en minutes")
    )

    # Description
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Description du travail effectué")
    )
    notes_internes = models.TextField(
        blank=True,
        verbose_name=_("Notes internes"),
        help_text=_("Notes internes non visibles sur la facture")
    )

    # Facturation
    facturable = models.BooleanField(
        default=True,
        verbose_name=_("Facturable"),
        help_text=_("Indique si ce temps est facturable au client")
    )
    taux_horaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Taux horaire"),
        help_text=_("Taux horaire appliqué pour ce travail")
    )
    montant_ht = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant HT"),
        help_text=_("Montant hors taxes calculé")
    )
    devise = models.ForeignKey(
        'core.Devise',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='temps_travail',
        verbose_name=_("Devise"),
        help_text=_("Devise du taux horaire et du montant")
    )

    facture = models.ForeignKey(
        'Facture',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='temps_factures',
        verbose_name=_("Facture"),
        help_text=_("Facture associée si ce temps a été facturé")
    )
    date_facturation = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de facturation"),
        help_text=_("Date à laquelle ce temps a été facturé")
    )

    # Lien avec une tâche
    tache = models.ForeignKey(
        'core.Tache', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='temps_travail',
        verbose_name=_('Tâche')
    )

    # Lien avec le module projets
    position = models.ForeignKey(
        "projets.Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="temps_passes",
        verbose_name=_("Position"),
        help_text=_("Position/lot lié dans le module projets"),
    )
    operation = models.ForeignKey(
        "projets.Operation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="temps_passes",
        verbose_name=_("Opération"),
        help_text=_("Opération liée dans le module projets"),
    )

    # Géolocalisation
    coordonnees = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        geography=True,
        verbose_name=_("Coordonnées"),
        help_text=_("Position GPS lors de la saisie"),
    )
    zone_geographique = models.ForeignKey(
        ZoneGeographique,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='temps_travail',
        verbose_name=_("Zone géographique"),
        help_text=_("Zone géographique associée"),
    )

    # Validation
    valide = models.BooleanField(
        default=False,
        verbose_name=_("Validé"),
        help_text=_("Indique si ce temps a été validé")
    )
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Validé par"),
        help_text=_("Utilisateur ayant validé ce temps")
    )

    # Pièces jointes (preuves du travail effectué)
    fichiers_joints = GenericRelation(
        FichierJoint,
        verbose_name=_("Fichiers joints"),
        help_text=_("Pièces jointes : preuves du travail effectué (captures, documents, etc.)")
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            self.description,
            self.notes_internes,
            self.prestation.libelle if self.prestation else '',
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'time_tracking'
        verbose_name = _('Suivi du temps')
        verbose_name_plural = _('Suivis du temps')
        ordering = ['-date_travail', 'utilisateur']
        indexes = [
            models.Index(fields=['mandat', 'date_travail']),
            models.Index(fields=['utilisateur', 'date_travail']),
            models.Index(fields=['facturable', 'facture']),
            models.Index(fields=['type_entree', 'utilisateur', 'date_travail']),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.type_entree == 'CLIENT':
            if not self.mandat_id:
                errors['mandat'] = _('Le mandat est obligatoire pour une entrée de type client.')
            if not self.prestation_id:
                errors['prestation'] = _('La prestation est obligatoire pour une entrée de type client.')
        else:
            if not self.categorie_id:
                errors['categorie'] = _('La catégorie est obligatoire pour le temps interne ou les absences.')
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        prefix = self.get_type_entree_display() if self.type_entree != 'CLIENT' else ''
        base = f"{self.date_travail} - {self.utilisateur.username} - {self.duree_minutes}min"
        return f"[{prefix}] {base}" if prefix else base

    @property
    def duree_heures(self):
        """Retourne la durée en heures décimales"""
        return Decimal(self.duree_minutes) / Decimal('60')

    def calculer_montant(self):
        """Calcule le montant HT basé sur durée et taux"""
        heures = Decimal(self.duree_minutes) / Decimal("60")
        self.montant_ht = (heures * self.taux_horaire).quantize(Decimal("0.01"))
        self.save(update_fields=["montant_ht"])
        return self.montant_ht

    def ajouter_a_facture(self, facture):
        """Ajoute ce temps à une facture existante"""
        # Trouver ou créer la ligne correspondante
        ligne = facture.lignes.filter(prestation=self.prestation).first()

        if ligne:
            # Ajouter au temps existant
            ligne.quantite += self.duree_heures
            ligne.save()
        else:
            # Créer nouvelle ligne
            ordre = facture.lignes.aggregate(models.Max("ordre"))["ordre__max"] or 0
            ligne = LigneFacture.objects.create(
                facture=facture,
                ordre=ordre + 1,
                prestation=self.prestation,
                description=self.description,
                quantite=self.duree_heures,
                unite="heure",
                prix_unitaire_ht=self.taux_horaire,
                taux_tva=self.prestation.taux_tva_defaut
                if self.prestation
                else get_taux_tva_defaut(facture.mandat),
            )

        # Lier le temps à la ligne
        ligne.temps_factures.add(self)

        # Marquer comme facturé
        self.facture = facture
        self.date_facturation = date.today()
        self.save()

        # Recalculer la facture
        facture.calculer_totaux()

        return ligne


class Facture(BaseModel):
    """Facture client"""

    STATUT_CHOICES = [
        ('BROUILLON', _('Brouillon')),
        ('PROFORMA', _('Pro forma')),
        ('EMISE', _('Émise')),
        ('ENVOYEE', _('Envoyée')),
        ('RELANCEE', _('Relancée')),
        ('PARTIELLEMENT_PAYEE', _('Partiellement payée')),
        ('PAYEE', _('Payée')),
        ('EN_RETARD', _('En retard')),
        ('ANNULEE', _('Annulée')),
        ('AVOIR', _('Avoir')),
    ]

    TYPE_CHOICES = [
        ('FACTURE', _('Facture')),
        ('DEVIS', _('Devis')),
        ('AVOIR', _('Avoir')),
        ('ACOMPTE', _("Facture d'acompte")),
    ]

    # Identification
    numero_facture = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Numéro de facture"),
        help_text=_("Numéro unique de la facture")
    )
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='factures',
        verbose_name=_("Mandat"),
        help_text=_("Mandat concerné par cette facture")
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='factures',
        verbose_name=_("Client"),
        help_text=_("Client facturé")
    )
    position = models.ForeignKey(
        'projets.Position',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='factures',
        verbose_name=_("Position"),
        help_text=_("Position/lot du projet concerné")
    )

    type_facture = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='FACTURE',
        verbose_name=_("Type de facture"),
        help_text=_("Type de document (Facture, Avoir, Acompte)")
    )

    # Dates
    date_emission = models.DateField(
        db_index=True,
        verbose_name=_("Date d'émission"),
        help_text=_("Date d'émission de la facture")
    )
    date_echeance = models.DateField(
        db_index=True,
        verbose_name=_("Date d'échéance"),
        help_text=_("Date limite de paiement")
    )
    date_service_debut = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Début de période"),
        help_text=_("Date de début de la période facturée")
    )
    date_service_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Fin de période"),
        help_text=_("Date de fin de la période facturée")
    )

    # Montants
    montant_ht = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant HT"),
        help_text=_("Montant total hors taxes")
    )
    montant_tva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant TVA"),
        help_text=_("Montant total de la TVA")
    )
    montant_ttc = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant TTC"),
        help_text=_("Montant total toutes taxes comprises")
    )

    # Remises
    remise_pourcent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("Remise (%)"),
        help_text=_("Pourcentage de remise globale")
    )
    remise_montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant remise"),
        help_text=_("Montant de la remise calculée")
    )

    # Paiement
    delai_paiement_jours = models.IntegerField(
        default=30,
        verbose_name=_("Délai de paiement (jours)"),
        help_text=_("Nombre de jours accordés pour le paiement")
    )
    conditions_paiement = models.TextField(
        blank=True,
        verbose_name=_("Conditions de paiement"),
        help_text=_("Conditions de paiement spécifiques")
    )

    # QR-Bill Suisse
    qr_reference = models.CharField(
        max_length=27,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_("Référence QR"),
        help_text=_("Référence QR structurée pour le paiement suisse")
    )
    qr_iban = models.CharField(
        max_length=34,
        blank=True,
        verbose_name=_("IBAN QR"),
        help_text=_("IBAN pour le QR-Bill")
    )
    qr_code_image = models.ImageField(
        upload_to='factures/qr/',
        storage=InvoiceStorage(),
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("Image QR code"),
        help_text=_("Image du QR code généré")
    )

    # Statut
    statut = models.CharField(
        max_length=30,
        choices=STATUT_CHOICES,
        default='BROUILLON',
        db_index=True,
        verbose_name=_("Statut"),
        help_text=_("Statut actuel de la facture")
    )

    # Paiements
    montant_paye = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant payé"),
        help_text=_("Montant total déjà payé")
    )
    montant_restant = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant restant"),
        help_text=_("Montant restant à payer")
    )

    date_paiement_complet = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de paiement complet"),
        help_text=_("Date à laquelle la facture a été entièrement payée")
    )

    # Relances
    nombre_relances = models.IntegerField(
        default=0,
        verbose_name=_("Nombre de relances"),
        help_text=_("Nombre de relances envoyées")
    )
    date_derniere_relance = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date dernière relance"),
        help_text=_("Date de la dernière relance envoyée")
    )

    # Avoir / Annulation
    facture_origine = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='avoirs',
        verbose_name=_("Facture d'origine"),
        help_text=_("Facture d'origine pour un avoir")
    )
    motif_annulation = models.TextField(
        blank=True,
        verbose_name=_("Motif d'annulation"),
        help_text=_("Raison de l'annulation ou de l'avoir")
    )

    # Fichiers
    fichier_pdf = models.FileField(
        upload_to='factures/pdf/',
        storage=InvoiceStorage(),
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("Fichier PDF"),
        help_text=_("Fichier PDF de la facture")
    )

    # Comptabilité
    ecriture_comptable = models.ForeignKey(
        'comptabilite.PieceComptable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='factures',
        verbose_name=_("Pièce comptable"),
        help_text=_("Pièce comptable associée")
    )

    # Régime fiscal (support international)
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='factures',
        verbose_name=_("Régime fiscal"),
        help_text=_("Régime fiscal applicable à cette facture")
    )
    TYPE_OPERATION_TVA_CHOICES = [
        ('NATIONALE', _('Vente nationale')),
        ('EXPORT', _('Exportation')),
        ('INTRACOM', _('Intracommunautaire')),
        ('AUTOLIQUIDATION', _('Autoliquidation')),
    ]
    type_operation_tva = models.CharField(
        max_length=20,
        choices=TYPE_OPERATION_TVA_CHOICES,
        default='NATIONALE',
        verbose_name=_("Type d'opération TVA"),
        help_text=_("Détermine le traitement TVA : nationale, export (0%), intracommunautaire, autoliquidation")
    )
    mentions_legales_generees = models.TextField(
        blank=True,
        verbose_name=_("Mentions légales"),
        help_text=_("Mentions légales générées automatiquement selon le régime fiscal")
    )
    # Exercice comptable
    exercice = models.ForeignKey(
        'core.ExerciceComptable',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='factures',
        verbose_name=_("Exercice comptable"),
        help_text=_("Exercice comptable de rattachement")
    )
    # Devise (support international)
    devise = models.ForeignKey(
        'core.Devise',
        on_delete=models.PROTECT,
        related_name='factures',
        verbose_name=_("Devise"),
        help_text=_("Devise de facturation")
    )

    # Textes
    introduction = models.TextField(
        blank=True,
        verbose_name=_("Introduction"),
        help_text=_("Texte d'introduction de la facture")
    )
    conclusion = models.TextField(
        blank=True,
        verbose_name=_("Conclusion"),
        help_text=_("Texte de conclusion/remerciements")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes internes"),
        help_text=_("Notes internes non visibles sur la facture")
    )

    # Création/validation
    creee_par = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='factures_creees',
        verbose_name=_("Créée par"),
        help_text=_("Utilisateur ayant créé la facture")
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de validation"),
        help_text=_("Date et heure de validation")
    )
    validee_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='factures_validees',
        verbose_name=_("Validée par"),
        help_text=_("Utilisateur ayant validé la facture")
    )

    def texte_pour_embedding(self):
        """Texte pour vectorisation sémantique."""
        parts = [
            f"Facture {self.numero_facture}",
            self.client.raison_sociale if self.client else '',
            self.introduction,
            self.conclusion,
            self.notes,
        ]
        return ' '.join(filter(None, parts))

    class Meta:
        db_table = 'factures'
        verbose_name = _('Facture')
        verbose_name_plural = _('Factures')
        ordering = ['-date_emission', 'numero_facture']
        indexes = [
            models.Index(fields=['client', 'statut']),
            models.Index(fields=['date_emission']),
            models.Index(fields=['date_echeance', 'statut']),
            models.Index(fields=['numero_facture']),
        ]

    def __str__(self):
        devise_code = self.devise_id or self.mandat.devise_id
        return f"{self.numero_facture} - {self.client.raison_sociale} - {self.montant_ttc} {devise_code}"

    @property
    def est_simplifiee(self):
        """Facture simplifiée (Art. 26 MWSTG) : montant TTC < CHF 400."""
        from decimal import Decimal
        return self.montant_ttc < Decimal('400')

    def save(self, *args, **kwargs):
        # Auto-populate regime_fiscal from mandat if not set
        if not self.regime_fiscal_id and self.mandat_id:
            self.regime_fiscal = getattr(self.mandat, 'regime_fiscal', None)

        # Auto-calculer date_echeance si absente
        if not self.date_echeance and self.date_emission:
            from datetime import timedelta
            jours = self.delai_paiement_jours or 30
            self.date_echeance = self.date_emission + timedelta(days=jours)

        # Génération numéro facture/devis
        if not self.numero_facture:
            year = self.date_emission.year
            if self.type_facture == 'DEVIS':
                prefix = 'DEV'
            else:
                prefix = 'FAC'
            last = Facture.objects.filter(
                numero_facture__startswith=f'{prefix}-{year}'
            ).order_by('numero_facture').last()

            if last:
                last_num = int(last.numero_facture.split('-')[-1])
                self.numero_facture = f'{prefix}-{year}-{last_num + 1:04d}'
            else:
                self.numero_facture = f'{prefix}-{year}-0001'

        # Calcul montant restant
        self.montant_restant = self.montant_ttc - self.montant_paye

        # Mise à jour statut basé sur paiement
        # (seulement si montant_ttc > 0 pour éviter 0 >= 0 = PAYEE sur création)
        if self.montant_ttc > 0 and self.montant_paye >= self.montant_ttc and self.statut not in ('PAYEE', 'ANNULEE', 'AVOIR'):
            self.statut = 'PAYEE'
            if not self.date_paiement_complet:
                from django.utils import timezone
                self.date_paiement_complet = timezone.now()
        elif self.montant_paye > 0 and self.montant_paye < self.montant_ttc and self.statut in ('EMISE', 'ENVOYEE', 'RELANCEE', 'EN_RETARD'):
            self.statut = 'PARTIELLEMENT_PAYEE'

        super().save(*args, **kwargs)

    def convertir_en_facture(self):
        """Convertit un devis en facture. Crée une nouvelle facture depuis ce devis."""
        if self.type_facture != 'DEVIS':
            raise ValueError("Seul un devis peut être converti en facture.")

        facture = Facture(
            mandat=self.mandat,
            client=self.client,
            type_facture='FACTURE',
            regime_fiscal=self.regime_fiscal,
            exercice=self.exercice,
            devise=self.devise,
            date_emission=date.today(),
            delai_paiement_jours=self.delai_paiement_jours,
            conditions_paiement=self.conditions_paiement,
            remise_pourcent=self.remise_pourcent,
            introduction=self.introduction,
            conclusion=self.conclusion,
            notes=f"Converti depuis devis {self.numero_facture}",
            date_service_debut=self.date_service_debut,
            date_service_fin=self.date_service_fin,
            statut='BROUILLON',
        )
        facture.save()

        # Copier les lignes
        for ligne in self.lignes.all():
            LigneFacture.objects.create(
                facture=facture,
                prestation=ligne.prestation,
                description=ligne.description,
                quantite=ligne.quantite,
                unite=ligne.unite,
                prix_unitaire_ht=ligne.prix_unitaire_ht,
                taux_tva=ligne.taux_tva,
                remise_ligne_pourcent=ligne.remise_ligne_pourcent,
            )

        facture.calculer_totaux()

        # Marquer le devis comme converti
        self.statut = 'EMISE'
        self.notes = (self.notes or '') + f"\nConverti en facture {facture.numero_facture}"
        self.save(update_fields=['statut', 'notes'])

        return facture

    def generer_qr_reference(self):
        """Génère la référence QR structurée selon norme suisse"""
        # Référence QR : 27 chiffres avec checksum
        # Format: [ID Créancier 6 digits][ID Facture 20 digits][Checksum 1 digit]

        # Convertir UUID en nombre (utiliser les chiffres du hash)
        # Pour l'ID créancier: convertir UUID hex en int et prendre 6 chiffres
        mandat_hash = int(str(self.mandat.id).replace('-', '')[:12], 16)
        id_creancier = str(mandat_hash)[-6:].zfill(6)

        # Pour l'ID facture: convertir UUID hex en int et prendre 20 chiffres
        facture_hash = int(str(self.id).replace('-', ''), 16)
        id_facture = str(facture_hash)[-20:].zfill(20)

        # Référence de base (26 digits)
        ref_base = id_creancier + id_facture

        # Calcul checksum modulo 10 récursif
        checksum = self._calcul_checksum_modulo10(ref_base)

        # Référence complète (27 digits)
        self.qr_reference = ref_base + str(checksum)
        self.save(update_fields=["qr_reference"])

        return self.qr_reference

    def _calcul_checksum_modulo10(self, reference):
        """Calcul checksum modulo 10 récursif (norme suisse)"""
        table = [0, 9, 4, 6, 8, 2, 7, 1, 3, 5]
        carry = 0
        for char in reference:
            carry = table[(carry + int(char)) % 10]
        return (10 - carry) % 10

    def _resolve_iban_and_creditor(self):
        """
        Résout l'IBAN et l'entreprise créancière pour le QR-Bill.

        Chaîne de résolution :
        1. qr_iban sur la facture (override manuel)
        2. Compte lié au mandat
        3. Compte principal de l'entreprise du client (Client → Entreprise → Compte)
        4. Compte principal de l'entreprise par défaut
        5. N'importe quel compte actif de l'entreprise par défaut
        6. N'importe quel compte actif dans le système
        """
        from core.models import CompteBancaire, Entreprise

        iban = None
        entreprise_creancier = None
        compte = None

        if self.qr_iban:
            iban = self.qr_iban
        else:
            # 1. Compte directement lié au mandat
            compte = CompteBancaire.objects.filter(
                mandat=self.mandat, actif=True
            ).order_by('-est_compte_principal').first()

            # 2. Via le client → son entreprise → compte de l'entreprise
            if not compte and self.client and self.client.entreprise_id:
                entreprise_creancier = self.client.entreprise
                compte = CompteBancaire.objects.filter(
                    entreprise=entreprise_creancier, actif=True
                ).order_by('-est_compte_principal').first()

            # 3. Entreprise par défaut → compte principal
            if not compte:
                entreprise_creancier = Entreprise.objects.filter(est_defaut=True).first()
                if entreprise_creancier:
                    compte = CompteBancaire.objects.filter(
                        entreprise=entreprise_creancier, actif=True
                    ).order_by('-est_compte_principal').first()

            # 4. N'importe quel compte actif
            if not compte:
                compte = CompteBancaire.objects.filter(
                    actif=True
                ).order_by('-est_compte_principal').first()

            if compte:
                iban = compte.iban
                if not entreprise_creancier and compte.entreprise:
                    entreprise_creancier = compte.entreprise

        if not entreprise_creancier:
            entreprise_creancier = Entreprise.objects.filter(est_defaut=True).first()

        if not iban:
            raise ValueError(
                "Aucun IBAN configuré. Ajoutez un compte bancaire actif "
                "à votre entreprise dans Configuration > Entreprise."
            )

        return iban.replace(" ", "").upper(), entreprise_creancier

    def generer_qr_bill(self):
        """
        Génère le QR-Bill suisse complet (SVG) avec la librairie qrbill.

        Le SVG contient le récépissé, la section paiement et le QR code
        selon la norme Swiss Payment Standards (ISO 20022).
        """
        from qrbill import QRBill
        from django.core.files.base import ContentFile
        import io

        if not self.qr_reference:
            self.generer_qr_reference()

        iban, entreprise_creancier = self._resolve_iban_and_creditor()

        # Adresse du créancier = l'entreprise (fiduciaire)
        adresse_creancier = getattr(entreprise_creancier, 'adresse', None)
        if adresse_creancier:
            creditor = {
                'name': (entreprise_creancier.raison_sociale if entreprise_creancier else "")[:70],
                'pcode': adresse_creancier.npa or "0000",
                'city': (adresse_creancier.localite or "Suisse")[:35],
                'country': 'CH',
            }
            if adresse_creancier.rue:
                creditor['street'] = adresse_creancier.rue[:70]
            if adresse_creancier.numero:
                creditor['house_num'] = adresse_creancier.numero[:16]
        else:
            # Fallback: parser le champ siege "Rue Num, NPA Ville"
            creditor = {
                'name': (entreprise_creancier.raison_sociale if entreprise_creancier else "")[:70],
                'pcode': '0000',
                'city': 'Suisse',
                'country': 'CH',
            }
            siege = getattr(entreprise_creancier, 'siege', '') or ''
            if siege:
                import re
                # Format suisse: "Rue ..., NPA Ville" ou juste "Ville"
                match = re.match(r'^(.+?),\s*(\d{4})\s+(.+)$', siege)
                if match:
                    creditor['street'] = match.group(1).strip()[:70]
                    creditor['pcode'] = match.group(2)
                    creditor['city'] = match.group(3).strip()[:35]
                else:
                    creditor['city'] = siege[:35]

        # Adresse du débiteur = le client facturé
        adresse_debiteur = self.client.adresse_correspondance or self.client.adresse_siege
        debtor = {
            'name': self.client.raison_sociale[:70],
            'pcode': (adresse_debiteur.npa if adresse_debiteur else "") or "0000",
            'city': ((adresse_debiteur.localite if adresse_debiteur else "") or "Suisse")[:35],
            'country': 'CH',
        }
        if adresse_debiteur and adresse_debiteur.rue:
            debtor['street'] = adresse_debiteur.rue[:70]
        if adresse_debiteur and adresse_debiteur.numero:
            debtor['house_num'] = adresse_debiteur.numero[:16]

        # Déterminer si c'est un QR-IBAN (IID 30000-31999)
        is_qr_iban = False
        if iban.startswith('CH') and len(iban) >= 9:
            try:
                iid = int(iban[4:9])
                is_qr_iban = 30000 <= iid <= 31999
            except ValueError:
                pass

        devise = self.devise_id if self.devise_id in ('CHF', 'EUR') else 'CHF'

        qr_kwargs = {
            'account': iban,
            'creditor': creditor,
            'debtor': debtor,
            'amount': str(self.montant_ttc),
            'currency': devise,
            'additional_information': f"Facture {self.numero_facture}",
            'language': 'fr',
            'top_line': True,
            'payment_line': True,
        }

        # QRR reference seulement avec QR-IBAN
        if is_qr_iban and self.qr_reference:
            qr_kwargs['reference_number'] = self.qr_reference

        bill = QRBill(**qr_kwargs)

        # Générer le SVG
        svg_buf = io.StringIO()
        bill.as_svg(svg_buf)
        svg_content = svg_buf.getvalue()

        # Sauvegarder le SVG comme fichier Django
        self.qr_code_image.save(
            f"qr_bill_{self.numero_facture}.svg",
            ContentFile(svg_content.encode('utf-8')),
            save=True,
        )

        return self.qr_code_image

    def generer_pdf(self, avec_qr_bill=False, style_config=None):
        """
        Génère le PDF complet de la facture.

        Args:
            avec_qr_bill: Si True, ajoute le QR-Bill suisse en bas de page.
            style_config: Dict optionnel de personnalisation (couleurs, polices, marges, textes, blocs).
        """
        from facturation.services.pdf_facture import FacturePDF
        from core.pdf import save_pdf_overwrite

        service = FacturePDF(self, style_config=style_config, avec_qr_bill=avec_qr_bill)
        pdf_bytes = service.generer()

        suffix = "_qr" if avec_qr_bill else ""
        filename = f"facture_{self.numero_facture}{suffix}.pdf"
        return save_pdf_overwrite(self, 'fichier_pdf', pdf_bytes, filename)

    def _wrap_text(self, text, max_chars):
        """Découpe un texte en lignes de max_chars caractères"""
        if not text:
            return []
        words = text.replace('\n', ' ').split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def _ajouter_qr_bill(self, canvas, page_width, page_height):
        """Ajoute le QR-Bill suisse en bas de la facture via le SVG qrbill."""
        from reportlab.lib.units import mm
        from reportlab.graphics import renderPDF
        import logging

        logger = logging.getLogger(__name__)

        # Générer le SVG si pas encore fait
        if not self.qr_code_image or not self.qr_code_image.name:
            try:
                self.generer_qr_bill()
                self.refresh_from_db(fields=['qr_code_image'])
            except Exception as e:
                logger.warning(f"Impossible de générer le QR-Bill: {e}")
                self._draw_qr_bill_fallback(canvas, page_width, str(e))
                return

        # Lire le SVG et le convertir en drawing ReportLab
        try:
            from svglib.svglib import svg2rlg
            import tempfile, os

            svg_content = self.qr_code_image.read().decode('utf-8')
            self.qr_code_image.seek(0)

            with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as f:
                f.write(svg_content)
                tmp_path = f.name

            drawing = svg2rlg(tmp_path)
            os.unlink(tmp_path)

            if not drawing:
                raise ValueError("Impossible de parser le SVG")

            # Dimensionner pour occuper le bas de la page A4 (210mm x 105mm)
            qr_bill_height = 105 * mm
            scale_x = page_width / drawing.width
            scale_y = qr_bill_height / drawing.height
            scale = min(scale_x, scale_y)

            drawing.width *= scale
            drawing.height *= scale
            drawing.scale(scale, scale)

            # Dessiner en bas de page
            renderPDF.draw(drawing, canvas, 0, 0)

        except Exception as e:
            logger.warning(f"Erreur rendu QR-Bill SVG: {e}")
            self._draw_qr_bill_fallback(canvas, page_width, str(e))

    def _draw_qr_bill_fallback(self, canvas, page_width, error_msg=""):
        """Fallback si le SVG QR-Bill n'est pas disponible."""
        from reportlab.lib.units import mm
        from reportlab.lib import colors

        qr_height = 105 * mm
        canvas.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
        canvas.setDash(3, 3)
        canvas.line(0, qr_height, page_width, qr_height)
        canvas.setDash()

        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(5 * mm, qr_height - 10 * mm, "QR-Bill non disponible")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.Color(0.5, 0.5, 0.5))
        if error_msg:
            canvas.drawString(5 * mm, qr_height - 20 * mm, error_msg[:100])

    def calculer_totaux(self):
        """Recalcule tous les totaux à partir des lignes"""
        from django.db.models import Sum

        lignes = self.lignes.all()

        # Total HT
        self.montant_ht = lignes.aggregate(Sum("montant_ht"))[
            "montant_ht__sum"
        ] or Decimal("0")

        # Application remise globale
        if self.remise_pourcent:
            self.remise_montant = (
                self.montant_ht * self.remise_pourcent / 100
            ).quantize(Decimal("0.01"))

        montant_ht_net = self.montant_ht - self.remise_montant

        # TVA
        self.montant_tva = lignes.aggregate(Sum("montant_tva"))[
            "montant_tva__sum"
        ] or Decimal("0")

        # TTC
        self.montant_ttc = montant_ht_net + self.montant_tva

        # Montant restant
        self.montant_restant = self.montant_ttc - self.montant_paye

        self.save(
            update_fields=[
                "montant_ht",
                "montant_tva",
                "montant_ttc",
                "remise_montant",
                "montant_restant",
                "statut",
            ]
        )

        return self

    def valider(self, user):
        """Valide la facture"""
        if not self.lignes.exists():
            raise ValueError(_("La facture doit avoir au moins une ligne"))

        # Recalculer les totaux
        self.calculer_totaux()

        # Générer QR-Bill
        if not self.qr_reference:
            self.generer_qr_reference()

        # Changer le statut
        self.statut = "EMISE"
        self.validee_par = user
        self.date_validation = datetime.now()
        self.save()

        return self

    def enregistrer_paiement(
        self, montant, date_paiement, mode_paiement, reference="", user=None
    ):
        """Enregistre un paiement pour cette facture"""
        paiement = Paiement.objects.create(
            facture=self,
            montant=montant,
            date_paiement=date_paiement,
            mode_paiement=mode_paiement,
            reference=reference,
            valide=True,
            valide_par=user,
            date_validation=datetime.now() if user else None,
        )

        return paiement

    def creer_avoir(self, montant=None, motif="", user=None):
        """Crée un avoir pour cette facture"""
        montant_avoir = montant or self.montant_ttc

        avoir = Facture.objects.create(
            mandat=self.mandat,
            client=self.client,
            type_facture="AVOIR",
            facture_origine=self,
            date_emission=date.today(),
            date_echeance=date.today() + timedelta(days=30),
            montant_ht=-abs(montant_avoir),
            montant_ttc=-abs(montant_avoir),
            statut="EMISE",
            motif_annulation=motif,
            creee_par=user or self.creee_par,
        )

        # Copier les lignes (en négatif)
        for ligne in self.lignes.all():
            LigneFacture.objects.create(
                facture=avoir,
                ordre=ligne.ordre,
                prestation=ligne.prestation,
                description=ligne.description,
                quantite=-ligne.quantite,
                unite=ligne.unite,
                prix_unitaire_ht=ligne.prix_unitaire_ht,
                taux_tva=ligne.taux_tva,
            )

        return avoir

    def creer_relance(self, niveau=None, user=None):
        """
        Crée une relance pour cette facture.

        Les frais et délais sont lus depuis NiveauRelance (DB) pour le régime
        fiscal de la facture. Fallback sur des valeurs par défaut si non configuré.
        """
        niveau_relance = niveau or (self.nombre_relances + 1)
        params = self.niveau_relance_suivant()

        relance = Relance.objects.create(
            facture=self,
            niveau=niveau_relance,
            date_echeance=date.today() + timedelta(days=params['delai_jours']),
            montant_frais=params['frais'],
        )

        # Mettre à jour la facture
        self.nombre_relances += 1
        self.date_derniere_relance = date.today()
        if self.statut not in ["EN_RETARD", "ANNULEE"]:
            self.statut = "RELANCEE"
        self.save()

        return relance

    # =========================================================================
    # Règles métier
    # =========================================================================

    def peut_emettre(self):
        """Vérifie si la facture peut être émise/validée."""
        if self.statut != 'BROUILLON':
            return False, _("Seule une facture en brouillon peut être émise.")
        if not self.lignes.exists():
            return False, _("La facture doit avoir au moins une ligne.")
        if self.montant_ttc <= 0 and self.type_facture != 'AVOIR':
            return False, _("Le montant TTC doit être positif.")
        if not self.client_id:
            return False, _("Un client doit être renseigné.")
        return True, ""

    def peut_supprimer(self):
        """
        Vérifie si la facture peut être supprimée.

        Par défaut (et conformément aux législations FR, CH, OHADA),
        seules les factures en brouillon sont supprimables.
        Le régime fiscal peut autoriser la suppression de factures émises
        sans paiement via `suppression_facture_emise`.
        """
        if self.statut == 'BROUILLON':
            return True, ""
        if self.paiements.filter(valide=True).exists():
            return False, _("Impossible de supprimer une facture avec des paiements validés. Créez un avoir.")
        if self.statut in ['PAYEE', 'PARTIELLEMENT_PAYEE']:
            return False, _("Impossible de supprimer une facture payée. Créez un avoir.")
        # Vérifier si le régime autorise la suppression après émission
        if self.statut == 'EMISE' and self.regime_fiscal and self.regime_fiscal.suppression_facture_emise:
            return True, ""
        if self.statut != 'BROUILLON':
            return False, _("Une facture émise ne peut pas être supprimée. Créez un avoir.")
        return False, _("Cette facture ne peut pas être supprimée dans son statut actuel.")

    def peut_relancer(self):
        """Vérifie si la facture peut faire l'objet d'une relance."""
        if self.type_facture in ['DEVIS', 'AVOIR']:
            return False, _("Seules les factures peuvent être relancées.")
        if self.statut in ['BROUILLON', 'PAYEE', 'ANNULEE']:
            return False, _("Cette facture ne peut pas être relancée.")
        if self.montant_restant <= 0:
            return False, _("Aucun solde restant à relancer.")
        if self.nombre_relances >= 4:
            return False, _("Nombre maximum de relances atteint (mise en demeure déjà envoyée).")
        return True, ""

    def peut_annuler(self):
        """Vérifie si la facture peut être annulée."""
        if self.statut in ['ANNULEE', 'AVOIR']:
            return False, _("Cette facture est déjà annulée.")
        if self.paiements.filter(valide=True).exists():
            return False, _("Créez un avoir plutôt qu'annuler une facture avec des paiements.")
        return True, ""

    def est_en_retard(self):
        """Vérifie si la facture est en retard."""
        return (
            self.date_echeance
            and self.date_echeance < date.today()
            and self.montant_restant > 0
            and self.statut not in ["PAYEE", "ANNULEE", "AVOIR"]
        )

    def jours_retard(self):
        """Retourne le nombre de jours de retard."""
        if self.est_en_retard():
            return (date.today() - self.date_echeance).days
        return 0

    def niveau_relance_suivant(self):
        """
        Retourne le prochain niveau de relance et ses paramètres.

        Cherche d'abord dans NiveauRelance (DB) pour le régime fiscal,
        puis fallback sur la configuration suisse par défaut.
        """
        niveau = self.nombre_relances + 1

        # Chercher en DB pour le régime fiscal de la facture
        if self.regime_fiscal_id:
            from facturation.models import NiveauRelance
            config = NiveauRelance.objects.filter(
                regime_fiscal=self.regime_fiscal,
                niveau=niveau,
                is_active=True,
            ).first()
            if config:
                return {
                    'label': config.libelle,
                    'delai_jours': config.delai_jours,
                    'frais': config.frais,
                    'interets': config.interets,
                    'taux_interet': config.taux_interet,
                }
            # Si pas de config pour ce niveau, prendre le dernier niveau configuré
            dernier = NiveauRelance.objects.filter(
                regime_fiscal=self.regime_fiscal,
                is_active=True,
            ).order_by('-niveau').first()
            if dernier:
                return {
                    'label': dernier.libelle,
                    'delai_jours': dernier.delai_jours,
                    'frais': dernier.frais,
                    'interets': dernier.interets,
                    'taux_interet': dernier.taux_interet,
                }

        # Fallback : configuration suisse par défaut
        NIVEAUX_DEFAUT = {
            1: {'label': _('1ère relance'), 'delai_jours': 15, 'frais': Decimal('0'), 'interets': False, 'taux_interet': Decimal('0')},
            2: {'label': _('2ème relance'), 'delai_jours': 10, 'frais': Decimal('20.00'), 'interets': False, 'taux_interet': Decimal('0')},
            3: {'label': _('3ème relance'), 'delai_jours': 10, 'frais': Decimal('40.00'), 'interets': True, 'taux_interet': Decimal('5')},
            4: {'label': _('Mise en demeure'), 'delai_jours': 10, 'frais': Decimal('50.00'), 'interets': True, 'taux_interet': Decimal('5')},
        }
        return NIVEAUX_DEFAUT.get(niveau, NIVEAUX_DEFAUT[4])


class LigneFacture(BaseModel):
    """Ligne de facture"""

    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_("Facture"),
        help_text=_("Facture à laquelle appartient cette ligne")
    )

    # Ordre d'affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name=_("Ordre"),
        help_text=_("Ordre d'affichage de la ligne")
    )

    # Prestation/Produit
    prestation = models.ForeignKey(
        Prestation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Prestation"),
        help_text=_("Prestation associée à cette ligne")
    )

    # Compte de produit override (prioritaire sur prestation.compte_produit)
    compte_produit = models.ForeignKey(
        'comptabilite.Compte',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lignes_facture',
        verbose_name=_("Compte de produit"),
        help_text=_("Compte comptable de produit (override la prestation)")
    )

    # Description
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Description de la ligne")
    )
    description_detaillee = models.TextField(
        blank=True,
        verbose_name=_("Description détaillée"),
        help_text=_("Description détaillée additionnelle")
    )

    # Quantité et prix
    quantite = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        verbose_name=_("Quantité"),
        help_text=_("Quantité facturée")
    )
    unite = models.CharField(
        max_length=50,
        default='heure',
        verbose_name=_("Unité"),
        help_text=_("Unité de mesure")
    )
    prix_unitaire_ht = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Prix unitaire HT"),
        help_text=_("Prix unitaire hors taxes")
    )

    # Montants
    montant_ht = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("Montant HT"),
        help_text=_("Montant hors taxes de la ligne")
    )

    # TVA
    taux_tva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("Taux TVA"),
        help_text=_("Taux de TVA appliqué (résolu depuis le régime fiscal du mandat)")
    )
    taux_tva_ref = models.ForeignKey(
        'tva.TauxTVA',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lignes_facture',
        verbose_name=_("Taux TVA (référence)"),
        help_text=_("Référence vers le taux TVA du régime fiscal")
    )
    code_tva = models.ForeignKey(
        'tva.CodeTVA',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lignes_facture',
        verbose_name=_("Code TVA"),
        help_text=_("Code TVA applicable")
    )
    montant_tva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("Montant TVA"),
        help_text=_("Montant de TVA calculé")
    )
    montant_ttc = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("Montant TTC"),
        help_text=_("Montant toutes taxes comprises")
    )

    # Remise spécifique ligne
    remise_pourcent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("Remise (%)"),
        help_text=_("Pourcentage de remise sur cette ligne")
    )

    # Lien time tracking
    temps_factures = models.ManyToManyField(
        TimeTracking,
        blank=True,
        related_name='lignes_facture',
        verbose_name=_("Temps facturés"),
        help_text=_("Temps de travail associés à cette ligne")
    )

    class Meta:
        db_table = 'lignes_facture'
        verbose_name = _('Ligne de facture')
        verbose_name_plural = _('Lignes de facture')
        ordering = ['facture', 'ordre']

    def __str__(self):
        return f"{self.facture.numero_facture} - {self.description[:50]}"

    def save(self, *args, **kwargs):
        # Resolve taux_tva from mandat regime if not explicitly set
        if not self.taux_tva and self.facture_id:
            self.taux_tva = get_taux_tva_defaut(self.facture.mandat)

        # Calcul automatique des montants
        montant_brut = self.quantite * self.prix_unitaire_ht

        # Application remise ligne
        if self.remise_pourcent:
            montant_brut = montant_brut * (1 - self.remise_pourcent / 100)

        self.montant_ht = montant_brut.quantize(Decimal('0.01'))
        self.montant_tva = (self.montant_ht * self.taux_tva / 100).quantize(Decimal('0.01'))
        self.montant_ttc = self.montant_ht + self.montant_tva

        super().save(*args, **kwargs)


class Paiement(BaseModel):
    """Paiement d'une facture"""

    MODE_PAIEMENT_CHOICES = [
        ('VIREMENT', _('Virement bancaire')),
        ('QR_BILL', _('QR-Bill')),
        ('CARTE', _('Carte bancaire')),
        ('ESPECES', _('Espèces')),
        ('CHEQUE', _('Chèque')),
        ('COMPENSATION', _('Compensation')),
        ('AUTRE', _('Autre')),
    ]

    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name=_("Facture"),
        help_text=_("Facture concernée par ce paiement")
    )

    # Montant
    montant = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("Montant"),
        help_text=_("Montant du paiement")
    )
    devise = models.ForeignKey(
        'core.Devise',
        on_delete=models.PROTECT,
        db_column='devise',
        verbose_name=_("Devise"),
        help_text=_("Devise du paiement")
    )

    # Date et mode
    date_paiement = models.DateField(
        db_index=True,
        verbose_name=_("Date de paiement"),
        help_text=_("Date du paiement")
    )
    mode_paiement = models.CharField(
        max_length=20,
        choices=MODE_PAIEMENT_CHOICES,
        verbose_name=_("Mode de paiement"),
        help_text=_("Mode de paiement utilisé")
    )

    # Référence
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Référence"),
        help_text=_("Référence bancaire ou numéro de transaction")
    )

    # Validation
    valide = models.BooleanField(
        default=False,
        verbose_name=_("Validé"),
        help_text=_("Indique si le paiement est validé")
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de validation"),
        help_text=_("Date et heure de validation")
    )
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Validé par"),
        help_text=_("Utilisateur ayant validé le paiement")
    )

    # Comptabilisation
    ecriture_comptable = models.ForeignKey(
        'comptabilite.EcritureComptable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements',
        verbose_name=_("Écriture comptable"),
        help_text=_("Écriture comptable associée")
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Notes concernant ce paiement")
    )

    class Meta:
        db_table = 'paiements'
        verbose_name = _('Paiement')
        verbose_name_plural = _('Paiements')
        ordering = ['-date_paiement']
        indexes = [
            models.Index(fields=['facture', 'date_paiement']),
            models.Index(fields=['date_paiement']),
        ]

    def __str__(self):
        return f"Paiement {self.montant} {self.devise_id} - {self.facture.numero_facture}"

    def save(self, *args, **kwargs):
        # Auto-populate devise from facture if not set
        if not self.devise_id and self.facture_id:
            self.devise_id = self.facture.devise_id
        super().save(*args, **kwargs)

        # Mise à jour du montant payé sur la facture
        self.facture.montant_paye = self.facture.paiements.filter(
            valide=True
        ).aggregate(
            total=models.Sum('montant')
        )['total'] or Decimal('0')

        self.facture.save(update_fields=['montant_paye', 'montant_restant', 'statut'])


class Relance(BaseModel):
    """Relance de paiement"""

    NIVEAU_CHOICES = [
        (1, _('1ère relance')),
        (2, _('2ème relance')),
        (3, _('3ème relance')),
        (4, _('Mise en demeure')),
    ]

    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name='relances',
        verbose_name=_("Facture"),
        help_text=_("Facture concernée par cette relance")
    )

    niveau = models.IntegerField(
        choices=NIVEAU_CHOICES,
        verbose_name=_("Niveau"),
        help_text=_("Niveau de la relance (1ère, 2ème, etc.)")
    )
    date_relance = models.DateField(
        auto_now_add=True,
        verbose_name=_("Date de relance"),
        help_text=_("Date de création de la relance")
    )
    date_echeance = models.DateField(
        verbose_name=_("Date d'échéance"),
        help_text=_("Nouvelle date limite de paiement")
    )

    montant_frais = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Frais de relance"),
        help_text=_("Montant des frais de relance")
    )
    montant_interets = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Intérêts de retard"),
        help_text=_("Montant des intérêts de retard")
    )

    envoyee = models.BooleanField(
        default=False,
        verbose_name=_("Envoyée"),
        help_text=_("Indique si la relance a été envoyée")
    )
    date_envoi = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date d'envoi"),
        help_text=_("Date d'envoi de la relance")
    )

    fichier_pdf = models.FileField(
        upload_to='factures/relances/',
        storage=InvoiceStorage(),
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("Fichier PDF"),
        help_text=_("Fichier PDF de la relance")
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Notes concernant cette relance")
    )

    class Meta:
        db_table = 'relances'
        verbose_name = _('Relance')
        verbose_name_plural = _('Relances')
        ordering = ['-date_relance']

    def __str__(self):
        return f"Relance niv.{self.niveau} - {self.facture.numero_facture}"


class NiveauRelance(BaseModel):
    """
    Configuration des niveaux de relance par régime fiscal.

    Remplace les frais et délais hardcodés (système suisse 0/20/40/50 CHF)
    par une configuration en base, adaptable par pays/régime.
    """
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal',
        on_delete=models.CASCADE,
        related_name='niveaux_relance',
        verbose_name=_("Régime fiscal"),
    )
    niveau = models.PositiveIntegerField(
        verbose_name=_("Niveau"),
        help_text=_("Numéro du niveau de relance (1, 2, 3, 4…)")
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_("Libellé"),
        help_text=_("Ex: 1ère relance, Mise en demeure, Sommation")
    )
    delai_jours = models.PositiveIntegerField(
        verbose_name=_("Délai accordé (jours)"),
        help_text=_("Nouveau délai de paiement accordé en jours")
    )
    frais = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_("Frais de relance"),
        help_text=_("Montant des frais facturés pour cette relance")
    )
    interets = models.BooleanField(
        default=False,
        verbose_name=_("Intérêts moratoires"),
        help_text=_("Appliquer des intérêts de retard à ce niveau")
    )
    taux_interet = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_("Taux d'intérêt annuel (%)"),
        help_text=_("Taux annuel des intérêts moratoires (ex: 5% en Suisse)")
    )

    class Meta:
        db_table = 'niveaux_relance'
        verbose_name = _("Niveau de relance")
        verbose_name_plural = _("Niveaux de relance")
        ordering = ['regime_fiscal', 'niveau']
        unique_together = ['regime_fiscal', 'niveau']

    def __str__(self):
        return f"{self.regime_fiscal.code} — Niv.{self.niveau}: {self.libelle}"


class MentionLegale(BaseModel):
    """
    Mention légale obligatoire ou optionnelle par régime fiscal.

    Chaque régime définit ses mentions : N° TVA, SIRET, RCCM,
    conditions de pénalités, mentions d'exonération, etc.
    Le texte supporte des variables : {tva_number}, {ide_number}, {raison_sociale}…
    """
    regime_fiscal = models.ForeignKey(
        'tva.RegimeFiscal',
        on_delete=models.CASCADE,
        related_name='mentions_legales',
        verbose_name=_("Régime fiscal"),
    )
    code = models.CharField(
        max_length=50,
        verbose_name=_("Code"),
        help_text=_("Code technique (ex: TVA_NUMBER, PENALITES_RETARD, EXONERATION)")
    )
    libelle = models.CharField(
        max_length=200,
        verbose_name=_("Libellé"),
    )
    texte = models.TextField(
        verbose_name=_("Texte de la mention"),
        help_text=_("Supporte les variables : {tva_number}, {ide_number}, {raison_sociale}, {siret}, {rccm}")
    )
    TYPE_DOCUMENT_CHOICES = [
        ('TOUS', _('Tous les documents')),
        ('FACTURE', _('Factures uniquement')),
        ('DEVIS', _('Devis uniquement')),
        ('AVOIR', _('Avoirs uniquement')),
    ]
    type_document = models.CharField(
        max_length=20,
        choices=TYPE_DOCUMENT_CHOICES,
        default='TOUS',
        verbose_name=_("Type de document"),
    )
    obligatoire = models.BooleanField(
        default=True,
        verbose_name=_("Obligatoire"),
        help_text=_("Si True, la mention est ajoutée automatiquement au document")
    )
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'mentions_legales'
        verbose_name = _("Mention légale")
        verbose_name_plural = _("Mentions légales")
        ordering = ['regime_fiscal', 'ordre']
        unique_together = ['regime_fiscal', 'code']

    def __str__(self):
        return f"{self.regime_fiscal.code} — {self.code}: {self.libelle}"
