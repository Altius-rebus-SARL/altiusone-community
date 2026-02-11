from decimal import Decimal

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel, Tache

User = "core.User"


class Position(BaseModel):
    """Poste/lot dans un mandat (ex: 'Terrassement', 'Electricite', 'Comptabilite Q1')"""

    mandat = models.ForeignKey(
        "core.Mandat",
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name=_("Mandat"),
    )
    numero = models.CharField(max_length=20, verbose_name=_("Numéro"))
    titre = models.CharField(max_length=255, verbose_name=_("Titre"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    # Budget
    budget_prevu = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name=_("Budget prévu")
    )
    budget_reel = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name=_("Budget réel")
    )
    devise = models.ForeignKey(
        "core.Devise",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Devise"),
    )

    # Planning
    date_debut = models.DateField(null=True, blank=True, verbose_name=_("Date de début"))
    date_fin = models.DateField(null=True, blank=True, verbose_name=_("Date de fin"))

    # Responsable
    responsable = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="positions_responsable",
        null=True,
        blank=True,
        verbose_name=_("Responsable"),
    )

    # Geolocalisation
    adresse = models.CharField(max_length=500, blank=True, verbose_name=_("Adresse"))
    coordonnees = gis_models.PointField(
        srid=4326, null=True, blank=True, geography=True, verbose_name=_("Coordonnées")
    )

    # Ordre d'affichage
    ordre = models.PositiveIntegerField(default=0, verbose_name=_("Ordre"))

    # Statut
    STATUT_CHOICES = [
        ("PLANIFIE", _("Planifié")),
        ("EN_COURS", _("En cours")),
        ("TERMINE", _("Terminé")),
        ("ANNULE", _("Annulé")),
    ]
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default="PLANIFIE", verbose_name=_("Statut")
    )

    # Prestataire externe
    prestataire_nom = models.CharField(
        max_length=255, blank=True, verbose_name=_("Nom du prestataire")
    )
    prestataire_contact = models.CharField(
        max_length=255, blank=True, verbose_name=_("Contact du prestataire")
    )
    est_sous_traite = models.BooleanField(default=False, verbose_name=_("Sous-traité"))

    class Meta:
        db_table = "positions"
        verbose_name = _("Position")
        verbose_name_plural = _("Positions")
        ordering = ["mandat", "ordre"]
        unique_together = [["mandat", "numero"]]

    def __str__(self):
        return f"{self.numero} - {self.titre}"

    def save(self, *args, **kwargs):
        if not self.numero:
            last = (
                Position.objects.filter(mandat=self.mandat)
                .order_by("numero")
                .last()
            )
            if last and last.numero.startswith("P-"):
                try:
                    last_num = int(last.numero.split("-")[-1])
                    self.numero = f"P-{last_num + 1:03d}"
                except (ValueError, IndexError):
                    self.numero = "P-001"
            else:
                self.numero = "P-001"
        super().save(*args, **kwargs)

    @property
    def budget_consomme_pourcent(self):
        if self.budget_prevu > 0:
            return (self.budget_reel / self.budget_prevu * 100).quantize(Decimal("0.1"))
        return Decimal("0")

    @property
    def nb_operations(self):
        return self.operations.count()

    @property
    def nb_operations_terminees(self):
        return self.operations.filter(statut="TERMINEE").count()

    @property
    def progression_pourcent(self):
        total = self.nb_operations
        if total == 0:
            return Decimal("0")
        return (Decimal(self.nb_operations_terminees) / Decimal(total) * 100).quantize(
            Decimal("0.1")
        )

    def recalculer_budget_reel(self):
        """Recalcule le budget réel à partir des coûts des opérations."""
        total = self.operations.aggregate(total=models.Sum("cout_reel"))["total"] or Decimal("0")
        self.budget_reel = total
        self.save(update_fields=["budget_reel"])


class Operation(BaseModel):
    """Opération/tâche dans une position"""

    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name="operations",
        verbose_name=_("Position"),
    )
    numero = models.CharField(max_length=20, verbose_name=_("Numéro"))
    titre = models.CharField(max_length=255, verbose_name=_("Titre"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    # Budget
    budget_prevu = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name=_("Budget prévu")
    )
    cout_reel = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name=_("Coût réel")
    )

    # Planning
    date_debut = models.DateField(null=True, blank=True, verbose_name=_("Date de début"))
    date_fin = models.DateField(null=True, blank=True, verbose_name=_("Date de fin"))
    duree_estimee_heures = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Durée estimée (heures)"),
    )

    # Assignation
    assigne_a = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="operations_assignees",
        null=True,
        blank=True,
        verbose_name=_("Assigné à"),
    )

    # Statut
    STATUT_CHOICES = [
        ("A_FAIRE", _("À faire")),
        ("EN_COURS", _("En cours")),
        ("EN_ATTENTE", _("En attente")),
        ("TERMINEE", _("Terminée")),
        ("ANNULEE", _("Annulée")),
    ]
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default="A_FAIRE", verbose_name=_("Statut")
    )

    PRIORITE_CHOICES = Tache.PRIORITE_CHOICES
    priorite = models.CharField(
        max_length=20, choices=PRIORITE_CHOICES, default="NORMALE", verbose_name=_("Priorité")
    )

    # Dépendances
    depend_de = models.ManyToManyField(
        "self", symmetrical=False, blank=True, related_name="bloque", verbose_name=_("Dépend de")
    )

    # Géolocalisation
    adresse = models.CharField(max_length=500, blank=True, verbose_name=_("Adresse"))
    coordonnees = gis_models.PointField(
        srid=4326, null=True, blank=True, geography=True, verbose_name=_("Coordonnées")
    )

    # Ordre
    ordre = models.PositiveIntegerField(default=0, verbose_name=_("Ordre"))

    class Meta:
        db_table = "operations"
        verbose_name = _("Opération")
        verbose_name_plural = _("Opérations")
        ordering = ["position", "ordre"]

    def __str__(self):
        return f"{self.numero} - {self.titre}"

    def save(self, *args, **kwargs):
        if not self.numero:
            last = (
                Operation.objects.filter(position=self.position)
                .order_by("numero")
                .last()
            )
            if last and last.numero.startswith("OP-"):
                try:
                    last_num = int(last.numero.split("-")[-1])
                    self.numero = f"OP-{last_num + 1:03d}"
                except (ValueError, IndexError):
                    self.numero = "OP-001"
            else:
                self.numero = "OP-001"
        super().save(*args, **kwargs)


class OperationNote(BaseModel):
    """Note/commentaire sur une opération (journal de chantier)"""

    operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name=_("Opération"),
    )
    auteur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_("Auteur"),
    )
    contenu = models.TextField(verbose_name=_("Contenu"))

    class Meta:
        db_table = "operation_notes"
        verbose_name = _("Note d'opération")
        verbose_name_plural = _("Notes d'opération")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note par {self.auteur} sur {self.operation}"
