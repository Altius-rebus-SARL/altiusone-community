from django import forms
from django.utils.translation import gettext_lazy as _

from core.models import Contact, User

from .models import Operation, OperationNote, Position


class PositionForm(forms.ModelForm):
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
            "prestataire_nom",
            "prestataire_contact",
            "est_sous_traite",
            "ordre",
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
            "ordre": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsable"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name")


class OperationForm(forms.ModelForm):
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
            "ordre",
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
            "ordre": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigne_a"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        self.fields["contacts_assignes"].queryset = Contact.objects.filter(is_active=True).order_by("nom", "prenom")


class OperationNoteForm(forms.ModelForm):
    class Meta:
        model = OperationNote
        fields = ["contenu"]
        widgets = {
            "contenu": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": _("Ajouter une note...")}),
        }
