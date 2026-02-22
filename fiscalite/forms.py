# fiscalite/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from .models import (
    DeclarationFiscale,
    AnnexeFiscale,
    CorrectionFiscale,
    ReportPerte,
    ReclamationFiscale,
    OptimisationFiscale,
)
from core.models import Mandat, ExerciceComptable


class DeclarationFiscaleForm(forms.ModelForm):
    """Formulaire pour une déclaration fiscale"""

    class Meta:
        model = DeclarationFiscale
        fields = [
            "mandat",
            "type_declaration",
            "type_impot",
            "exercice_comptable",
            "annee_fiscale",
            "periode_debut",
            "periode_fin",
            "canton",
            "commune",
            "subdivision",
            "numero_contribuable",
            "benefice_avant_impots",
            "benefice_imposable",
            "capital_propre",
            "capital_imposable",
            "impot_federal",
            "impot_cantonal",
            "impot_communal",
            "remarques",
        ] 
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "type_declaration": forms.Select(attrs={"class": "form-control"}),
            "type_impot": forms.Select(attrs={"class": "form-control"}),
            "exercice_comptable": forms.Select(attrs={"class": "form-control select2"}),
            "annee_fiscale": forms.NumberInput(attrs={"class": "form-control"}),
            "periode_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "periode_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "canton": forms.Select(attrs={"class": "form-control select2"}),
            "commune": forms.TextInput(attrs={"class": "form-control"}),
            "subdivision": forms.TextInput(attrs={"class": "form-control"}),
            "numero_contribuable": forms.TextInput(attrs={"class": "form-control"}),
            "benefice_avant_impots": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "benefice_imposable": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "capital_propre": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "capital_imposable": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "impot_federal": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "impot_cantonal": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "impot_communal": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "remarques": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class AnnexeFiscaleForm(forms.ModelForm):
    """Formulaire pour une annexe fiscale"""

    class Meta:
        model = AnnexeFiscale
        fields = ["type_annexe", "titre", "donnees", "fichier"]
        widgets = {
            "type_annexe": forms.Select(attrs={"class": "form-control"}),
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "donnees": forms.Textarea(attrs={"class": "form-control", "rows": 10}),
            "fichier": forms.FileInput(attrs={"class": "form-control"}),
        }


class CorrectionFiscaleForm(forms.ModelForm):
    """Formulaire pour une correction fiscale"""

    class Meta:
        model = CorrectionFiscale
        fields = [
            "type_correction",
            "description",
            "montant_comptable",
            "montant_correction",
            "compte",
            "justification",
            "reference_legale",
        ]
        widgets = {
            "type_correction": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "montant_comptable": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "montant_correction": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "compte": forms.Select(attrs={"class": "form-control"}),
            "justification": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "reference_legale": forms.TextInput(attrs={"class": "form-control"}),
        }


class ReportPerteForm(forms.ModelForm):
    """Formulaire pour un report de perte"""

    class Meta:
        model = ReportPerte
        fields = ["mandat", "annee_origine", "montant_perte", "annee_expiration"]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "annee_origine": forms.NumberInput(attrs={"class": "form-control"}),
            "montant_perte": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "annee_expiration": forms.NumberInput(attrs={"class": "form-control"}),
        }


class ReclamationFiscaleForm(forms.ModelForm):
    """Formulaire pour une réclamation fiscale"""

    class Meta:
        model = ReclamationFiscale
        fields = [
            "date_reclamation",
            "motif",
            "montant_conteste",
            "montant_demande",
            "fichier_reclamation",
        ]
        widgets = {
            "date_reclamation": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "motif": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "montant_conteste": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "montant_demande": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "fichier_reclamation": forms.FileInput(attrs={"class": "form-control"}),
        }


class OptimisationFiscaleForm(forms.ModelForm):
    """Formulaire pour une optimisation fiscale"""

    class Meta:
        model = OptimisationFiscale
        fields = [
            "mandat",
            "categorie",
            "titre",
            "description",
            "economie_estimee",
            "annee_application",
            "niveau_risque",
            "reference_legale",
            "notes",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "categorie": forms.Select(attrs={"class": "form-control"}),
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "economie_estimee": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "annee_application": forms.NumberInput(attrs={"class": "form-control"}),
            "niveau_risque": forms.Select(attrs={"class": "form-control"}),
            "reference_legale": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
