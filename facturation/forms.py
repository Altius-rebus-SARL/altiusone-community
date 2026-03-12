# facturation/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from datetime import datetime, timedelta, date
from django.forms import inlineformset_factory

from .models import (
    Prestation, TimeTracking, Facture, LigneFacture, Paiement, Relance,
    ZoneGeographique, TarifMandat,
)
from django.db.models import Q
from core.models import Mandat, Client, User, ParametreMetier
from projets.forms import CoordonneesMixin


class PrestationForm(forms.ModelForm):
    """Formulaire pour une prestation"""

    class Meta:
        model = Prestation
        fields = [
            "code",
            "libelle",
            "description",
            "type_prestation",
            "types_mandats",
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
            "type_prestation": forms.Select(attrs={"class": "form-control select2"}),
            "types_mandats": forms.SelectMultiple(attrs={"class": "form-control select2", "multiple": "multiple"}),
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


class MultipleFileInput(forms.ClearableFileInput):
    """Widget pour upload de plusieurs fichiers."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Champ de formulaire acceptant plusieurs fichiers."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png,.gif,.tiff,.doc,.docx,.xls,.xlsx,.csv,.txt,.zip',
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class TimeTrackingForm(CoordonneesMixin, forms.ModelForm):
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

    # Géolocalisation (hidden, rempli par JS)
    coordonnees = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_coordonnees"}),
    )

    # Pièces jointes (preuves du travail effectué)
    fichiers = MultipleFileField(
        required=False,
        label=_("Pièces jointes"),
        help_text=_("Joindre des fichiers comme preuve du travail effectué (captures, documents, etc.)"),
    )

    class Meta:
        model = TimeTracking
        fields = [
            "mandat",
            "utilisateur",
            "prestation",
            "tache",
            "position",
            "operation",
            "date_travail",
            "duree_minutes",
            "description",
            "notes_internes",
            "facturable",
            "taux_horaire",
            "zone_geographique",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "utilisateur": forms.Select(attrs={"class": "form-control select2"}),
            "prestation": forms.Select(attrs={"class": "form-control select2"}),
            "tache": forms.Select(attrs={"class": "form-control select2"}),
            "position": forms.Select(attrs={"class": "form-control select2"}),
            "operation": forms.Select(attrs={"class": "form-control select2"}),
            "date_travail": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "duree_minutes": forms.NumberInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "notes_internes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "facturable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "taux_horaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "readonly": "readonly"}
            ),
            "zone_geographique": forms.Select(attrs={"class": "form-control select2"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Tache: filtrer par utilisateur pour les non-managers
        from core.models import Tache
        if self.user and not self.user.is_manager():
            self.fields['tache'].queryset = Tache.objects.filter(
                assignes=self.user,
                statut__in=['A_FAIRE', 'EN_COURS'],
            ).distinct()
        else:
            self.fields['tache'].queryset = Tache.objects.filter(
                statut__in=['A_FAIRE', 'EN_COURS', 'EN_ATTENTE'],
            )
        self.fields['tache'].required = False

        # Initialiser les coordonnées depuis l'instance existante
        self._init_coordonnees()

        # Position et opération : querysets vides par défaut (remplis par JS)
        from projets.models import Position, Operation
        if self.instance and self.instance.pk:
            # En édition : remplir le queryset depuis l'instance
            if self.instance.position_id:
                self.fields["position"].queryset = Position.objects.filter(
                    mandat=self.instance.mandat, is_active=True
                )
            else:
                self.fields["position"].queryset = Position.objects.none()
            if self.instance.operation_id:
                self.fields["operation"].queryset = Operation.objects.filter(
                    position=self.instance.position, is_active=True
                )
            else:
                self.fields["operation"].queryset = Operation.objects.none()
        else:
            self.fields["position"].queryset = Position.objects.none()
            self.fields["operation"].queryset = Operation.objects.none()

        # En POST, accepter les valeurs envoyées par le JS
        if self.data:
            position_id = self.data.get("position")
            operation_id = self.data.get("operation")
            if position_id:
                self.fields["position"].queryset = Position.objects.filter(is_active=True)
            if operation_id:
                self.fields["operation"].queryset = Operation.objects.filter(is_active=True)

        # Si on a des heures début/fin, calculer la durée
        if self.instance and self.instance.heure_debut and self.instance.heure_fin:
            self.fields["heure_debut_time"].initial = self.instance.heure_debut
            self.fields["heure_fin_time"].initial = self.instance.heure_fin

        # Restrictions pour les non-managers
        if self.user and not self.user.is_manager():
            self.fields["utilisateur"].widget = forms.HiddenInput()
            self.fields["utilisateur"].initial = self.user
            # Filtrer les mandats accessibles
            self.fields["mandat"].queryset = Mandat.objects.filter(
                Q(responsable=self.user) | Q(equipe=self.user),
                statut='ACTIF',
            ).distinct()

    def clean(self):
        cleaned_data = super().clean()

        # Calculer la durée depuis les heures si fournies
        heure_debut = cleaned_data.get("heure_debut_time")
        heure_fin = cleaned_data.get("heure_fin_time")
        duree_minutes = cleaned_data.get("duree_minutes")

        if heure_debut and heure_fin:
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

        # Validation cohérence position/opération
        position = cleaned_data.get("position")
        operation = cleaned_data.get("operation")
        mandat = cleaned_data.get("mandat")

        if position and mandat and position.mandat_id != mandat.id:
            self.add_error("position", _("Cette position n'appartient pas au mandat sélectionné"))

        if operation and position and operation.position_id != position.id:
            self.add_error("operation", _("Cette opération n'appartient pas à la position sélectionnée"))

        # Résolution cascade du taux horaire : TarifMandat → Prestation → Mandat
        if not cleaned_data.get("taux_horaire"):
            mandat = cleaned_data.get("mandat")
            prestation = cleaned_data.get("prestation")
            taux = None

            # 1. TarifMandat spécifique
            if mandat and prestation:
                tarif = TarifMandat.objects.filter(
                    mandat=mandat, prestation=prestation, is_active=True,
                ).first()
                if tarif and tarif.est_valide(cleaned_data.get("date_travail") or date.today()):
                    taux = tarif.taux_horaire

            # 2. Taux de la prestation
            if not taux and prestation and prestation.taux_horaire:
                taux = prestation.taux_horaire

            # 3. Taux du mandat
            if not taux and mandat and mandat.taux_horaire:
                taux = mandat.taux_horaire

            if taux:
                cleaned_data["taux_horaire"] = taux
            else:
                raise forms.ValidationError(_("Un taux horaire doit être défini"))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Sauvegarder les heures si calculées
        if hasattr(self, "cleaned_data"):
            instance.heure_debut = self.cleaned_data.get("heure_debut")
            instance.heure_fin = self.cleaned_data.get("heure_fin")

        # Forcer l'utilisateur pour les non-managers
        if self.user and not self.user.is_manager():
            instance.utilisateur = self.user

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
            "regime_fiscal",
            "exercice",
            "devise",
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
            "regime_fiscal": forms.Select(attrs={"class": "form-control select2"}),
            "exercice": forms.Select(attrs={"class": "form-control select2"}),
            "devise": forms.Select(attrs={"class": "form-control"}),
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
        self.mandat = kwargs.pop('mandat', None)
        super().__init__(*args, **kwargs)
        # Charger les types de facture depuis ParametreMetier
        self.fields['type_facture'].choices = ParametreMetier.get_choices_with_default(
            'facturation', 'type_facture', Facture.TYPE_CHOICES
        )
        # Forcer le format de date
        self.fields["date_emission"].input_formats = ["%Y-%m-%d"]
        self.fields["date_service_debut"].input_formats = ["%Y-%m-%d"]
        self.fields["date_service_fin"].input_formats = ["%Y-%m-%d"]

        # Pré-peupler la devise et le régime fiscal depuis le mandat
        if not self.instance.pk and self.mandat:
            if hasattr(self.mandat, 'devise_id') and self.mandat.devise_id:
                self.fields["devise"].initial = self.mandat.devise_id
            if hasattr(self.mandat, 'regime_fiscal_id') and self.mandat.regime_fiscal_id:
                self.fields["regime_fiscal"].initial = self.mandat.regime_fiscal_id


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
    extra=0,
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
            "devise": forms.Select(attrs={"class": "form-control"}),
            "date_paiement": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "mode_paiement": forms.Select(attrs={"class": "form-control"}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mode_paiement'].choices = ParametreMetier.get_choices_with_default(
            'facturation', 'mode_paiement', Paiement.MODE_PAIEMENT_CHOICES
        )


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


class TarifMandatForm(forms.ModelForm):
    """Formulaire pour un tarif mandat/prestation"""

    class Meta:
        model = TarifMandat
        fields = [
            "mandat",
            "prestation",
            "taux_horaire",
            "prix_forfaitaire",
            "devise",
            "date_debut",
            "date_fin",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "prestation": forms.Select(attrs={"class": "form-control select2"}),
            "taux_horaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "prix_forfaitaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "devise": forms.Select(attrs={"class": "form-control"}),
            "date_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }


class ZoneGeographiqueForm(forms.ModelForm):
    """Formulaire pour une zone géographique"""

    class Meta:
        model = ZoneGeographique
        fields = ["nom", "description", "couleur"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "couleur": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
        }
