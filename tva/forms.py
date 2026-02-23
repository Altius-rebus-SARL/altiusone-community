# tva/forms.py
import re

from django import forms
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from .models import (
    ConfigurationTVA,
    RegimeFiscal,
    DeclarationTVA,
    LigneTVA,
    OperationTVA,
    CorrectionTVA,
    CodeTVA,
)
from core.models import Mandat, Periodicite


class ConfigurationTVAForm(forms.ModelForm):
    """Formulaire pour la configuration TVA"""

    class Meta:
        model = ConfigurationTVA
        fields = [
            "mandat",
            "regime",
            "assujetti_tva",
            "numero_tva",
            "date_debut_assujettissement",
            "date_fin_assujettissement",
            "methode_calcul",
            "periodicite_ref",
            "taux_forfaitaire_ventes",
            "taux_forfaitaire_achats",
            "option_imposition_prestations",
            "option_reduction_deduction",
            "compte_tva_due",
            "compte_tva_prealable",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "regime": forms.Select(attrs={"class": "form-control select2"}),
            "assujetti_tva": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "numero_tva": forms.TextInput(attrs={"class": "form-control"}),
            "date_debut_assujettissement": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin_assujettissement": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "methode_calcul": forms.Select(attrs={"class": "form-control"}),
            "periodicite_ref": forms.Select(attrs={"class": "form-control"}),
            "taux_forfaitaire_ventes": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "taux_forfaitaire_achats": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "option_imposition_prestations": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "option_reduction_deduction": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "compte_tva_due": forms.Select(attrs={"class": "form-control"}),
            "compte_tva_prealable": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer sur les périodicités applicables à la TVA (trimestriel et semestriel)
        self.fields['periodicite_ref'].queryset = Periodicite.objects.filter(
            is_active=True,
            code__in=['TRIMESTRIEL', 'SEMESTRIEL']
        )
        self.fields['periodicite_ref'].label = _('Périodicité')
        self.fields['regime'].queryset = RegimeFiscal.objects.all()
        self.fields['regime'].label = _('Régime fiscal')
        self.fields['regime'].required = False

    def clean_numero_tva(self):
        """Valide le format du numéro TVA selon le regex du régime fiscal"""
        numero = self.cleaned_data.get('numero_tva', '').strip()
        if not numero:
            return numero

        regime = self.cleaned_data.get('regime')
        if not regime and self.instance and self.instance.pk:
            regime = self.instance.regime

        if regime and regime.format_numero_tva:
            if not re.match(regime.format_numero_tva, numero):
                raise forms.ValidationError(
                    _('Format invalide. Pour le régime %(regime)s, '
                      'le format attendu est : %(format)s') % {
                        'regime': regime.code,
                        'format': 'CHE-xxx.xxx.xxx TVA' if regime.code == 'CH' else regime.format_numero_tva,
                    }
                )
        return numero


class DeclarationTVAForm(forms.ModelForm):
    """Formulaire pour une déclaration TVA"""

    class Meta:
        model = DeclarationTVA
        fields = [
            "mandat",
            "regime_fiscal",
            "devise",
            "annee",
            "trimestre",
            "semestre",
            "type_decompte",
            "methode",
            "remarques_internes",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "regime_fiscal": forms.Select(attrs={"class": "form-control select2"}),
            "devise": forms.Select(attrs={"class": "form-control select2"}),
            "annee": forms.NumberInput(attrs={"class": "form-control"}),
            "trimestre": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "max": "4"}
            ),
            "semestre": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "max": "2"}
            ),
            "type_decompte": forms.Select(attrs={"class": "form-control"}),
            "methode": forms.TextInput(attrs={"class": "form-control"}),
            "remarques_internes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Rendre trimestre ou semestre obligatoire selon la périodicité
        # Seulement si on modifie une instance existante ET qu'elle a un mandat
        if self.instance and self.instance.pk and hasattr(self.instance, "mandat"):
            try:
                config = self.instance.mandat.config_tva
                # Utiliser le nouveau champ de référence ou l'ancien pour compatibilité
                periodicite_code = config.periodicite_ref.code if config.periodicite_ref else config.periodicite
                if periodicite_code == "TRIMESTRIEL":
                    self.fields["trimestre"].required = True
                    self.fields["semestre"].required = False
                else:
                    self.fields["trimestre"].required = False
                    self.fields["semestre"].required = True
            except:
                pass

    def clean(self):
        cleaned_data = super().clean()

        trimestre = cleaned_data.get("trimestre")
        semestre = cleaned_data.get("semestre")
        annee = cleaned_data.get("annee")

        # Au moins trimestre ou semestre doit être rempli
        if not trimestre and not semestre:
            raise forms.ValidationError(
                _("Vous devez indiquer soit le trimestre, soit le semestre")
            )

        # Calculer les dates de début et fin de période
        if trimestre:
            mois_debut = (trimestre - 1) * 3 + 1
            mois_fin = trimestre * 3
            from datetime import date

            cleaned_data["periode_debut"] = date(annee, mois_debut, 1)

            # Dernier jour du mois
            if mois_fin == 12:
                cleaned_data["periode_fin"] = date(annee, 12, 31)
            else:
                from calendar import monthrange

                jour_fin = monthrange(annee, mois_fin)[1]
                cleaned_data["periode_fin"] = date(annee, mois_fin, jour_fin)

        elif semestre:
            from datetime import date

            if semestre == 1:
                cleaned_data["periode_debut"] = date(annee, 1, 1)
                cleaned_data["periode_fin"] = date(annee, 6, 30)
            else:
                cleaned_data["periode_debut"] = date(annee, 7, 1)
                cleaned_data["periode_fin"] = date(annee, 12, 31)

        return cleaned_data


class LigneTVAForm(forms.ModelForm):
    """Formulaire pour une ligne de déclaration TVA"""

    class Meta:
        model = LigneTVA
        fields = [
            "code_tva",
            "base_imposable",
            "taux_tva",
            "montant_tva",
            "libelle",
            "description",
            "calcul_automatique",
        ]
        widgets = {
            "code_tva": forms.Select(attrs={"class": "form-control"}),
            "base_imposable": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "taux_tva": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "montant_tva": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "libelle": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "calcul_automatique": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Si calcul automatique, calculer le montant TVA
        if cleaned_data.get("calcul_automatique"):
            base = cleaned_data.get("base_imposable", Decimal("0"))
            taux = cleaned_data.get("taux_tva", Decimal("0"))

            cleaned_data["montant_tva"] = (base * taux / 100).quantize(Decimal("0.01"))

        return cleaned_data


class OperationTVAForm(forms.ModelForm):
    """Formulaire pour une opération TVA"""

    class Meta:
        model = OperationTVA
        fields = [
            "mandat",
            "date_operation",
            "type_operation",
            "montant_ht",
            "code_tva",
            "taux_tva",
            "montant_tva",
            "tiers",
            "tiers_ref",
            "numero_tva_tiers",
            "numero_facture",
            "facture",
            "libelle",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "date_operation": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "type_operation": forms.Select(attrs={"class": "form-control"}),
            "tiers_ref": forms.Select(attrs={"class": "form-control select2"}),
            "facture": forms.Select(attrs={"class": "form-control select2"}),
            "montant_ht": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "code_tva": forms.Select(attrs={"class": "form-control"}),
            "taux_tva": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "montant_tva": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "tiers": forms.TextInput(attrs={"class": "form-control"}),
            "numero_tva_tiers": forms.TextInput(attrs={"class": "form-control"}),
            "numero_facture": forms.TextInput(attrs={"class": "form-control"}),
            "libelle": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Calculer le montant TVA
        montant_ht = cleaned_data.get("montant_ht", Decimal("0"))
        taux_tva = cleaned_data.get("taux_tva", Decimal("0"))

        cleaned_data["montant_tva"] = (montant_ht * taux_tva / 100).quantize(
            Decimal("0.01")
        )
        cleaned_data["montant_ttc"] = montant_ht + cleaned_data["montant_tva"]

        return cleaned_data


class CorrectionTVAForm(forms.ModelForm):
    """Formulaire pour une correction TVA"""

    class Meta:
        model = CorrectionTVA
        fields = [
            "type_correction",
            "code_tva",
            "base_calcul",
            "taux",
            "montant_correction",
            "description",
            "justification",
        ]
        widgets = {
            "type_correction": forms.Select(attrs={"class": "form-control"}),
            "code_tva": forms.Select(attrs={"class": "form-control"}),
            "base_calcul": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "taux": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "montant_correction": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "justification": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
