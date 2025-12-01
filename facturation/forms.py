# facturation/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from datetime import datetime, timedelta
from django.forms import inlineformset_factory

from .models import Prestation, TimeTracking, Facture, LigneFacture, Paiement, Relance
from core.models import Mandat, Client, User


class PrestationForm(forms.ModelForm):
    """Formulaire pour une prestation"""

    class Meta:
        model = Prestation
        fields = [
            "code",
            "libelle",
            "description",
            "type_prestation",
            "prix_unitaire_ht",
            "unite",
            "taux_horaire",
            "soumis_tva",
            "taux_tva_defaut",
            "compte_produit",
            "actif",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "libelle": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "type_prestation": forms.Select(attrs={"class": "form-control"}),
            "prix_unitaire_ht": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "unite": forms.TextInput(attrs={"class": "form-control"}),
            "taux_horaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "soumis_tva": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "taux_tva_defaut": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "compte_produit": forms.Select(attrs={"class": "form-control select2"}),
            "actif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TimeTrackingForm(forms.ModelForm):
    """Formulaire pour le suivi du temps"""

    # Champs calculés
    heure_debut_time = forms.TimeField(
        required=False,
        label=_("Heure début"),
        widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
    )

    heure_fin_time = forms.TimeField(
        required=False,
        label=_("Heure fin"),
        widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
    )

    class Meta:
        model = TimeTracking
        fields = [
            "mandat",
            "utilisateur",
            "prestation",
            "date_travail",
            "duree_minutes",
            "description",
            "notes_internes",
            "facturable",
            "taux_horaire",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "utilisateur": forms.Select(attrs={"class": "form-control select2"}),
            "prestation": forms.Select(attrs={"class": "form-control select2"}),
            "date_travail": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "duree_minutes": forms.NumberInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "notes_internes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "facturable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "taux_horaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si on a des heures début/fin, calculer la durée
        if self.instance and self.instance.heure_debut and self.instance.heure_fin:
            self.fields["heure_debut_time"].initial = self.instance.heure_debut
            self.fields["heure_fin_time"].initial = self.instance.heure_fin

    def clean(self):
        cleaned_data = super().clean()

        # Calculer la durée depuis les heures si fournies
        heure_debut = cleaned_data.get("heure_debut_time")
        heure_fin = cleaned_data.get("heure_fin_time")
        duree_minutes = cleaned_data.get("duree_minutes")

        if heure_debut and heure_fin:
            # Calculer la durée
            from datetime import datetime, timedelta

            debut = datetime.combine(datetime.today(), heure_debut)
            fin = datetime.combine(datetime.today(), heure_fin)

            if fin < debut:
                raise forms.ValidationError(
                    _("L'heure de fin doit être après l'heure de début")
                )

            duree = fin - debut
            cleaned_data["duree_minutes"] = int(duree.total_seconds() / 60)

            # Sauvegarder les heures
            cleaned_data["heure_debut"] = heure_debut
            cleaned_data["heure_fin"] = heure_fin

        elif not duree_minutes:
            raise forms.ValidationError(
                _("Veuillez fournir soit la durée, soit les heures de début et fin")
            )

        # Vérifier que le taux horaire est défini
        if not cleaned_data.get("taux_horaire"):
            # Prendre le taux de la prestation
            prestation = cleaned_data.get("prestation")
            if prestation and prestation.taux_horaire:
                cleaned_data["taux_horaire"] = prestation.taux_horaire
            else:
                raise forms.ValidationError(_("Un taux horaire doit être défini"))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Sauvegarder les heures si calculées
        if hasattr(self, "cleaned_data"):
            instance.heure_debut = self.cleaned_data.get("heure_debut")
            instance.heure_fin = self.cleaned_data.get("heure_fin")

        if commit:
            instance.save()

        return instance


class FactureForm(forms.ModelForm):
    """Formulaire pour une facture"""

    class Meta:
        model = Facture
        fields = [
            "mandat",
            "client",
            "type_facture",
            "date_emission",
            "date_service_debut",
            "date_service_fin",
            "delai_paiement_jours",
            "conditions_paiement",
            "remise_pourcent",
            "introduction",
            "conclusion",
            "notes",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "client": forms.Select(attrs={"class": "form-control select2"}),
            "type_facture": forms.Select(attrs={"class": "form-control"}),
            "date_emission": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "date_service_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "date_service_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "delai_paiement_jours": forms.NumberInput(attrs={"class": "form-control"}),
            "conditions_paiement": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "remise_pourcent": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "introduction": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "conclusion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Forcer le format de date
        self.fields["date_emission"].input_formats = ["%Y-%m-%d"]
        self.fields["date_service_debut"].input_formats = ["%Y-%m-%d"]
        self.fields["date_service_fin"].input_formats = ["%Y-%m-%d"]


class LigneFactureForm(forms.ModelForm):
    """Formulaire pour une ligne de facture"""

    class Meta:
        model = LigneFacture
        fields = [
            "prestation",
            "description",
            "description_detaillee",
            "quantite",
            "unite",
            "prix_unitaire_ht",
            "taux_tva",
            "remise_pourcent",
        ]
        widgets = {
            "prestation": forms.Select(
                attrs={"class": "form-control select2 prestation-select"}
            ),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "description_detaillee": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "quantite": forms.NumberInput(
                attrs={"class": "form-control quantite-input", "step": "0.01"}
            ),
            "unite": forms.TextInput(attrs={"class": "form-control"}),
            "prix_unitaire_ht": forms.NumberInput(
                attrs={"class": "form-control prix-input", "step": "0.01"}
            ),
            "taux_tva": forms.NumberInput(
                attrs={"class": "form-control tva-input", "step": "0.01"}
            ),
            "remise_pourcent": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }


# Formset pour les lignes de facture
LigneFactureFormSet = inlineformset_factory(
    Facture,
    LigneFacture,
    form=LigneFactureForm,
    extra=1,  # 1 ligne vide par défaut
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class PaiementForm(forms.ModelForm):
    """Formulaire pour un paiement"""

    class Meta:
        model = Paiement
        fields = [
            "montant",
            "devise",
            "date_paiement",
            "mode_paiement",
            "reference",
            "notes",
        ]
        widgets = {
            "montant": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "devise": forms.TextInput(attrs={"class": "form-control"}),
            "date_paiement": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "mode_paiement": forms.Select(attrs={"class": "form-control"}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class RelanceForm(forms.ModelForm):
    """Formulaire pour une relance"""

    class Meta:
        model = Relance
        fields = ["date_echeance", "montant_frais", "montant_interets", "notes"]
        widgets = {
            "date_echeance": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "montant_frais": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "montant_interets": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class FacturationGroupeeForm(forms.Form):
    """Formulaire pour facturer du temps en groupe"""

    mandat = forms.ModelChoiceField(
        queryset=Mandat.objects.filter(statut="ACTIF"),
        label=_("Mandat"),
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )

    periode_debut = forms.DateField(
        label=_("Période début"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    periode_fin = forms.DateField(
        label=_("Période fin"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    grouper_par = forms.ChoiceField(
        choices=[
            ("prestation", _("Par prestation")),
            ("utilisateur", _("Par utilisateur")),
            ("jour", _("Par jour")),
        ],
        label=_("Grouper par"),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    inclure_detail = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Inclure le détail dans la description"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
