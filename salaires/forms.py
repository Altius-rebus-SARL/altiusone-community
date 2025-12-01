# salaires/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from datetime import datetime

from .models import Employe, FicheSalaire, CertificatSalaire
from core.models import Mandat, Adresse


class AdresseInlineForm(forms.ModelForm):
    """Formulaire inline pour une adresse"""

    class Meta:
        model = Adresse
        fields = ["rue", "numero", "complement", "npa", "localite", "canton", "pays"]
        widgets = {
            "rue": forms.TextInput(attrs={"class": "form-control"}),
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "complement": forms.TextInput(attrs={"class": "form-control"}),
            "npa": forms.TextInput(attrs={"class": "form-control"}),
            "localite": forms.TextInput(attrs={"class": "form-control"}),
            "canton": forms.Select(attrs={"class": "form-control"}),
            "pays": forms.TextInput(attrs={"class": "form-control", "value": "CH"}),
        }


class EmployeForm(forms.ModelForm):
    """Formulaire pour un employé"""

    class Meta:
        model = Employe
        fields = [
            "mandat",
            "matricule",
            "nom",
            "prenom",
            "nom_naissance",
            "date_naissance",
            "lieu_naissance",
            "nationalite",
            "sexe",
            "avs_number",
            "numero_permis",
            "type_permis",
            "email",
            "telephone",
            "mobile",
            "etat_civil",
            "nombre_enfants",
            "type_contrat",
            "date_entree",
            "date_sortie",
            "date_fin_periode_essai",
            "fonction",
            "departement",
            "taux_occupation",
            "salaire_brut_mensuel",
            "salaire_horaire",
            "nombre_heures_semaine",
            "jours_vacances_annuel",
            "treizieme_salaire",
            "montant_13eme",
            "iban",
            "banque",
            "statut",
            "soumis_is",
            "barreme_is",
            "taux_is",
            "config_cotisations",
            "remarques",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "matricule": forms.TextInput(attrs={"class": "form-control"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "prenom": forms.TextInput(attrs={"class": "form-control"}),
            "nom_naissance": forms.TextInput(attrs={"class": "form-control"}),
            "date_naissance": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "lieu_naissance": forms.TextInput(attrs={"class": "form-control"}),
            "nationalite": forms.TextInput(attrs={"class": "form-control select2"}),
            "sexe": forms.Select(attrs={"class": "form-control"}),
            "avs_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "756.1234.5678.90"}
            ),
            "numero_permis": forms.TextInput(attrs={"class": "form-control"}),
            "type_permis": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
            "etat_civil": forms.Select(attrs={"class": "form-control"}),
            "nombre_enfants": forms.NumberInput(attrs={"class": "form-control"}),
            "type_contrat": forms.Select(attrs={"class": "form-control"}),
            "date_entree": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_sortie": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin_periode_essai": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "fonction": forms.TextInput(attrs={"class": "form-control"}),
            "departement": forms.TextInput(attrs={"class": "form-control"}),
            "taux_occupation": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "salaire_brut_mensuel": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "salaire_horaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "nombre_heures_semaine": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "jours_vacances_annuel": forms.NumberInput(attrs={"class": "form-control"}),
            "treizieme_salaire": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "montant_13eme": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "iban": forms.TextInput(attrs={"class": "form-control"}),
            "banque": forms.TextInput(attrs={"class": "form-control"}),
            "statut": forms.Select(attrs={"class": "form-control"}),
            "soumis_is": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "barreme_is": forms.TextInput(attrs={"class": "form-control"}),
            "taux_is": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "config_cotisations": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "remarques": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Si 13ème salaire activé, vérifier le montant
        if cleaned_data.get("treizieme_salaire"):
            if not cleaned_data.get("montant_13eme"):
                # Par défaut = salaire mensuel
                cleaned_data["montant_13eme"] = cleaned_data.get("salaire_brut_mensuel")

        return cleaned_data


class FicheSalaireForm(forms.ModelForm):
    """Formulaire pour une fiche de salaire"""

    class Meta:
        model = FicheSalaire
        fields = [
            "employe",
            "periode",
            "jours_travailles",
            "heures_travaillees",
            "heures_supplementaires",
            "jours_absence",
            "jours_vacances",
            "jours_maladie",
            "salaire_base",
            "heures_supp_montant",
            "primes",
            "indemnites",
            "treizieme_mois",
            "allocations_familiales",
            "autres_allocations",
            "avance_salaire",
            "saisie_salaire",
            "autres_deductions",
            "remarques",
        ]
        widgets = {
            "employe": forms.Select(attrs={"class": "form-control select2"}),
            "periode": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "jours_travailles": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "heures_travaillees": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "heures_supplementaires": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "jours_absence": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "jours_vacances": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "jours_maladie": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "salaire_base": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "heures_supp_montant": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "primes": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "indemnites": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "treizieme_mois": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "allocations_familiales": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "autres_allocations": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "avance_salaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "saisie_salaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "autres_deductions": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "remarques": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class CertificatSalaireForm(forms.ModelForm):
    """Formulaire pour un certificat de salaire"""

    class Meta:
        model = CertificatSalaire
        fields = [
            "employe",
            "annee",
            "date_debut",
            "date_fin",
            "salaire_brut_annuel",
            "treizieme_salaire_annuel",
            "primes_annuelles",
            "avs_annuel",
            "ac_annuel",
            "lpp_annuel",
            "allocations_familiales_annuel",
            "frais_deplacement",
            "frais_repas",
            "impot_source_annuel",
        ]
        widgets = {
            "employe": forms.Select(attrs={"class": "form-control select2"}),
            "annee": forms.NumberInput(attrs={"class": "form-control"}),
            "date_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "salaire_brut_annuel": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "treizieme_salaire_annuel": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "primes_annuelles": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "avs_annuel": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "ac_annuel": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "lpp_annuel": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "allocations_familiales_annuel": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "frais_deplacement": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "frais_repas": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "impot_source_annuel": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }
