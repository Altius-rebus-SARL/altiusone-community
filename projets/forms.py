from decimal import Decimal

from django import forms
from django.contrib.gis.geos import Point
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Contact, User

from .models import Operation, OperationNote, Position


class CoordonneesMixin:
    """Mixin to handle coordonnees PointField as a hidden lat,lng text field."""

    def _init_coordonnees(self):
        """Populate the coordonnees field with lat,lng string from the instance."""
        if self.instance and self.instance.pk and self.instance.coordonnees:
            pt = self.instance.coordonnees
            self.initial["coordonnees"] = f"{pt.y},{pt.x}"

    def clean_coordonnees(self):
        value = self.cleaned_data.get("coordonnees", "").strip()
        if not value:
            return None
        try:
            parts = value.split(",")
            lat = float(parts[0])
            lng = float(parts[1])
            return Point(lng, lat, srid=4326)
        except (ValueError, IndexError):
            raise forms.ValidationError(_("Format de coordonnées invalide (lat,lng attendu)."))


class PositionForm(CoordonneesMixin, forms.ModelForm):
    coordonnees = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Position
        fields = [
            "titre",
            "description",
            "budget_prevu",
            "devise",
            "date_debut",
            "date_fin",
            "responsable",
            "statut",
            "adresse",
            "coordonnees",
            "prestataire_nom",
            "prestataire_contact",
            "est_sous_traite",
        ]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Titre de la position")}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "budget_prevu": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "devise": forms.Select(attrs={"class": "form-control select2"}),
            "date_debut": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "date_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "responsable": forms.Select(attrs={"class": "form-control select2"}),
            "statut": forms.Select(attrs={"class": "form-control"}),
            "adresse": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Adresse")}),
            "prestataire_nom": forms.TextInput(attrs={"class": "form-control"}),
            "prestataire_contact": forms.TextInput(attrs={"class": "form-control"}),
            "est_sous_traite": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.mandat = kwargs.pop("mandat", None)
        super().__init__(*args, **kwargs)
        self.fields["responsable"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        self._init_coordonnees()

    def clean_budget_prevu(self):
        budget = self.cleaned_data.get("budget_prevu") or Decimal("0")
        mandat = self.mandat
        if not mandat:
            return budget
        # If mandat has no budget, positions cannot have one
        if not mandat.budget_prevu or mandat.budget_prevu <= 0:
            if budget > 0:
                raise forms.ValidationError(
                    _("Le mandat n'a pas de budget défini. Veuillez d'abord définir le budget du mandat.")
                )
            return budget
        # Sum of other active positions' budgets (exclude self if editing)
        other_positions = mandat.positions.filter(is_active=True)
        if self.instance and self.instance.pk:
            other_positions = other_positions.exclude(pk=self.instance.pk)
        total_autres = other_positions.aggregate(
            total=models.Sum("budget_prevu")
        )["total"] or Decimal("0")
        total = total_autres + budget
        if total > mandat.budget_prevu:
            raise forms.ValidationError(
                _("Le budget total des positions (%(total)s CHF) dépasse le budget du mandat (%(mandat_budget)s CHF)."),
                params={"total": total, "mandat_budget": mandat.budget_prevu},
            )
        return budget


class OperationForm(CoordonneesMixin, forms.ModelForm):
    coordonnees = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Operation
        fields = [
            "titre",
            "description",
            "budget_prevu",
            "cout_reel",
            "date_debut",
            "date_fin",
            "duree_estimee_heures",
            "assigne_a",
            "contacts_assignes",
            "statut",
            "priorite",
            "adresse",
            "coordonnees",
        ]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Titre de l'opération")}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "budget_prevu": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "cout_reel": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "date_debut": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "date_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "duree_estimee_heures": forms.NumberInput(attrs={"class": "form-control", "step": "0.5"}),
            "assigne_a": forms.SelectMultiple(attrs={"class": "form-control select2"}),
            "contacts_assignes": forms.SelectMultiple(attrs={"class": "form-control select2"}),
            "statut": forms.Select(attrs={"class": "form-control"}),
            "priorite": forms.Select(attrs={"class": "form-control"}),
            "adresse": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Adresse")}),
        }

    def __init__(self, *args, **kwargs):
        self.position = kwargs.pop("position", None)
        super().__init__(*args, **kwargs)
        self.fields["assigne_a"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        self.fields["contacts_assignes"].queryset = Contact.objects.filter(is_active=True).order_by("nom", "prenom")
        self._init_coordonnees()

    def clean_budget_prevu(self):
        budget = self.cleaned_data.get("budget_prevu") or Decimal("0")
        position = self.position
        if not position:
            return budget
        # If position has no budget, operations cannot have one
        if not position.budget_prevu or position.budget_prevu <= 0:
            if budget > 0:
                raise forms.ValidationError(
                    _("La position n'a pas de budget défini. Veuillez d'abord définir le budget de la position.")
                )
            return budget
        # Sum of other active operations' budgets (exclude self if editing)
        other_operations = position.operations.filter(is_active=True)
        if self.instance and self.instance.pk:
            other_operations = other_operations.exclude(pk=self.instance.pk)
        total_autres = other_operations.aggregate(
            total=models.Sum("budget_prevu")
        )["total"] or Decimal("0")
        total = total_autres + budget
        if total > position.budget_prevu:
            raise forms.ValidationError(
                _("Le budget total des opérations (%(total)s CHF) dépasse le budget de la position (%(position_budget)s CHF)."),
                params={"total": total, "position_budget": position.budget_prevu},
            )
        return budget


class OperationNoteForm(forms.ModelForm):
    class Meta:
        model = OperationNote
        fields = ["contenu"]
        widgets = {
            "contenu": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": _("Ajouter une note...")}),
        }
