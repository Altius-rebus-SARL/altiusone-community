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
    TauxImposition,
)
from core.models import Mandat, ExerciceComptable, ParametreMetier


class DeclarationFiscaleForm(forms.ModelForm):
    """Formulaire pour une déclaration fiscale"""

    class Meta:
        model = DeclarationFiscale
        fields = [
            "mandat",
            "regime_fiscal",
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
            "devise",
            "remarques",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "regime_fiscal": forms.Select(attrs={"class": "form-control"}),
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
            "devise": forms.Select(attrs={"class": "form-control"}),
            "remarques": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    _numeric_optional = [
        'benefice_avant_impots', 'benefice_imposable',
        'capital_propre', 'capital_imposable',
        'impot_federal', 'impot_cantonal', 'impot_communal',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_declaration'].choices = ParametreMetier.get_choices_with_default(
            'fiscalite', 'type_declaration', DeclarationFiscale.TYPE_DECLARATION_CHOICES
        )
        self.fields['type_impot'].choices = ParametreMetier.get_choices_with_default(
            'fiscalite', 'type_impot', DeclarationFiscale.TYPE_IMPOT_CHOICES
        )
        for field_name in self._numeric_optional:
            if field_name in self.fields:
                self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        for field_name in self._numeric_optional:
            if field_name in cleaned_data and cleaned_data[field_name] is None:
                cleaned_data[field_name] = Decimal('0')
        return cleaned_data


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_annexe'].choices = ParametreMetier.get_choices_with_default(
            'fiscalite', 'type_annexe', AnnexeFiscale.TYPE_ANNEXE_CHOICES
        )


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_correction'].choices = ParametreMetier.get_choices_with_default(
            'fiscalite', 'type_correction', CorrectionFiscale.TYPE_CORRECTION_CHOICES
        )
        self.fields['montant_comptable'].required = False

    def clean_montant_comptable(self):
        val = self.cleaned_data.get('montant_comptable')
        return val if val is not None else Decimal('0')


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categorie'].choices = ParametreMetier.get_choices_with_default(
            'fiscalite', 'categorie_optimisation', OptimisationFiscale.CATEGORIE_CHOICES
        )


class TauxImpositionForm(forms.ModelForm):
    """Formulaire pour un taux d'imposition"""

    class Meta:
        model = TauxImposition
        fields = [
            "regime_fiscal",
            "type_impot",
            "annee",
            "canton",
            "commune",
            "subdivision",
            "taux_fixe",
            "bareme",
            "multiplicateur_cantonal",
            "multiplicateur_communal",
            "actif",
        ]
        widgets = {
            "regime_fiscal": forms.Select(attrs={"class": "form-control"}),
            "type_impot": forms.Select(attrs={"class": "form-control"}),
            "annee": forms.NumberInput(attrs={"class": "form-control"}),
            "canton": forms.Select(attrs={"class": "form-control select2"}),
            "commune": forms.TextInput(attrs={"class": "form-control"}),
            "subdivision": forms.TextInput(attrs={"class": "form-control"}),
            "taux_fixe": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "bareme": forms.Textarea(
                attrs={"class": "form-control font-monospace", "rows": 6,
                       "placeholder": '{"tranches": [{"min": 0, "max": 50000, "taux": 10}, ...]}'}
            ),
            "multiplicateur_cantonal": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "multiplicateur_communal": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "actif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
