# analytics/forms.py - VERSION COMPLÈTE CORRIGÉE
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    TableauBord,
    Indicateur,
    Rapport,
    PlanificationRapport,
    ComparaisonPeriode,
    ExportDonnees,
)
from core.models import Mandat


class TableauBordForm(forms.ModelForm):
    """Formulaire pour un tableau de bord"""

    class Meta:
        model = TableauBord
        fields = [
            "nom",
            "description",
            "visibilite",
            "utilisateurs_partage",
            "configuration",
            "filtres_defaut",
            "auto_refresh",
            "refresh_interval",
            "favori",
            "ordre",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "visibilite": forms.Select(attrs={"class": "form-control"}),
            "utilisateurs_partage": forms.SelectMultiple(
                attrs={"class": "form-control"}
            ),
            "configuration": forms.Textarea(
                attrs={"class": "form-control", "rows": 10}
            ),
            "filtres_defaut": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
            "auto_refresh": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "refresh_interval": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
            "favori": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ordre": forms.NumberInput(attrs={"class": "form-control"}),
        }


class IndicateurForm(forms.ModelForm):
    """Formulaire pour un indicateur"""

    class Meta:
        model = Indicateur
        fields = [
            "code",
            "nom",
            "description",
            "categorie",
            "type_calcul",
            "formule",
            "source_table",
            "source_champ",
            "periodicite",
            "objectif_min",
            "objectif_cible",
            "objectif_max",
            "unite",
            "decimales",
            "seuil_alerte_bas",
            "seuil_alerte_haut",
            "actif",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "categorie": forms.Select(attrs={"class": "form-control"}),
            "type_calcul": forms.Select(attrs={"class": "form-control"}),
            "formule": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "source_table": forms.TextInput(attrs={"class": "form-control"}),
            "source_champ": forms.TextInput(attrs={"class": "form-control"}),
            "periodicite": forms.Select(attrs={"class": "form-control"}),
            "objectif_min": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "objectif_cible": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "objectif_max": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "unite": forms.TextInput(attrs={"class": "form-control"}),
            "decimales": forms.NumberInput(attrs={"class": "form-control"}),
            "seuil_alerte_bas": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "seuil_alerte_haut": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "actif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class RapportForm(forms.ModelForm):
    """Formulaire pour générer un rapport"""

    class Meta:
        model = Rapport
        fields = [
            "mandat",
            "nom",
            "type_rapport",
            "date_debut",
            "date_fin",
            "format_fichier",
            "parametres",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "type_rapport": forms.Select(attrs={"class": "form-control"}),
            "date_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "format_fichier": forms.Select(attrs={"class": "form-control"}),
            "parametres": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }


class PlanificationRapportForm(forms.ModelForm):
    """Formulaire pour une planification de rapport"""

    class Meta:
        model = PlanificationRapport
        fields = [
            "mandat",
            "nom",
            "type_rapport",
            "frequence",
            "jour_mois",
            "jour_semaine",
            "heure_generation",
            "format_fichier",
            "destinataires",
            "parametres",
            "actif",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "type_rapport": forms.Select(attrs={"class": "form-control"}),
            "frequence": forms.Select(attrs={"class": "form-control"}),
            "jour_mois": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "max": "31"}
            ),
            "jour_semaine": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "max": "6"}
            ),
            "heure_generation": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "format_fichier": forms.Select(attrs={"class": "form-control"}),
            "destinataires": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "parametres": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "actif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ComparaisonPeriodeForm(forms.ModelForm):
    """Formulaire pour une comparaison de périodes"""

    class Meta:
        model = ComparaisonPeriode
        fields = [
            "mandat",
            "type_comparaison",
            "nom",
            "periode1_debut",
            "periode1_fin",
            "libelle_periode1",
            "periode2_debut",
            "periode2_fin",
            "libelle_periode2",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control"}),
            "type_comparaison": forms.Select(attrs={"class": "form-control"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "periode1_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "periode1_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "libelle_periode1": forms.TextInput(attrs={"class": "form-control"}),
            "periode2_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "periode2_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "libelle_periode2": forms.TextInput(attrs={"class": "form-control"}),
        }


class ExportDonneesForm(forms.ModelForm):
    """Formulaire pour un export de données"""

    class Meta:
        model = ExportDonnees
        fields = [
            "mandat",
            "nom",
            "type_export",
            "date_debut",
            "date_fin",
            "format_export",
            "filtres",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "type_export": forms.Select(attrs={"class": "form-control"}),
            "date_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "format_export": forms.Select(attrs={"class": "form-control"}),
            "filtres": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }
