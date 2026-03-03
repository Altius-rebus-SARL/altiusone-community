# salaires/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Employe, FicheSalaire
from core.models import Mandat


class EmployeFilter(django_filters.FilterSet):
    """Filtres pour les employés"""

    nom = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Nom"),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nom..."}
        ),
    )

    prenom = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Prénom"),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Prénom..."}
        ),
    )

    matricule = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Matricule"),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Matricule..."}
        ),
    )

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"),
        label=_("Mandat"),
        empty_label="Tous les mandats",  # ⚠️ IMPORTANT
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )

    statut = django_filters.ChoiceFilter(
        choices=Employe.STATUT_CHOICES,
        label=_("Statut"),
        empty_label="Tous les statuts",  # ⚠️ IMPORTANT
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    type_contrat = django_filters.ChoiceFilter(
        choices=Employe.TYPE_CONTRAT_CHOICES,
        label=_("Type de contrat"),
        empty_label="Tous les types",  # ⚠️ IMPORTANT
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    fonction = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Fonction"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    departement = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Département"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    # Remplacer DateFromToRangeFilter par des champs simples
    date_entree__gte = django_filters.DateFilter(
        field_name="date_entree",
        lookup_expr="gte",
        label=_("Date entrée (depuis)"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    date_entree__lte = django_filters.DateFilter(
        field_name="date_entree",
        lookup_expr="lte",
        label=_("Date entrée (jusqu'à)"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    class Meta:
        model = Employe
        fields = []  # ⚠️ VIDE pour ne pas auto-appliquer


class FicheSalaireFilter(django_filters.FilterSet):
    """Filtres pour les fiches de salaire"""

    employe__nom = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Nom employé"),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nom..."}
        ),
    )

    employe__mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"),
        label=_("Mandat"),
        empty_label="Tous les mandats",  # ⚠️ IMPORTANT
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )

    numero_fiche = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Numéro fiche"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    # Remplacer DateFromToRangeFilter par des champs simples
    periode__gte = django_filters.DateFilter(
        field_name="periode",
        lookup_expr="gte",
        label=_("Période (depuis)"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    periode__lte = django_filters.DateFilter(
        field_name="periode",
        lookup_expr="lte",
        label=_("Période (jusqu'à)"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    annee = django_filters.NumberFilter(
        label=_("Année"),
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "2024"}
        ),
    )

    mois = django_filters.NumberFilter(
        label=_("Mois"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "1",
                "max": "12",
                "placeholder": "1-12",
            }
        ),
    )

    statut = django_filters.ChoiceFilter(
        choices=FicheSalaire.STATUT_CHOICES,
        label=_("Statut"),
        empty_label="Tous les statuts",  # ⚠️ IMPORTANT
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = FicheSalaire
        fields = []  # ⚠️ VIDE pour ne pas auto-appliquer
