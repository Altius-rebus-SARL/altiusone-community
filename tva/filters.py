# tva/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import DeclarationTVA, OperationTVA, CodeTVA
from core.models import Mandat


class DeclarationTVAFilter(django_filters.FilterSet):
    """Filtres pour les déclarations TVA"""

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    annee = django_filters.NumberFilter(label=_("Année"))

    trimestre = django_filters.NumberFilter(label=_("Trimestre"))

    semestre = django_filters.NumberFilter(label=_("Semestre"))

    statut = django_filters.ChoiceFilter(
        choices=DeclarationTVA.STATUT_CHOICES, label=_("Statut")
    )

    type_decompte = django_filters.ChoiceFilter(
        choices=DeclarationTVA.TYPE_DECOMPTE_CHOICES, label=_("Type de décompte")
    )

    methode = django_filters.CharFilter(lookup_expr="icontains", label=_("Méthode"))

    class Meta:
        model = DeclarationTVA
        fields = [
            "mandat",
            "annee",
            "trimestre",
            "semestre",
            "statut",
            "type_decompte",
            "methode",
        ]


class OperationTVAFilter(django_filters.FilterSet):
    """Filtres pour les opérations TVA"""

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    type_operation = django_filters.ChoiceFilter(
        choices=OperationTVA.TYPE_OPERATION_CHOICES, label=_("Type d'opération")
    )

    date_operation = django_filters.DateFromToRangeFilter(label=_("Date opération"))

    code_tva = django_filters.ModelChoiceFilter(
        queryset=CodeTVA.objects.filter(actif=True), label=_("Code TVA")
    )

    integre_declaration = django_filters.BooleanFilter(
        label=_("Intégré dans déclaration"), widget=forms.CheckboxInput()
    )

    declaration_tva = django_filters.ModelChoiceFilter(
        queryset=DeclarationTVA.objects.all(), label=_("Déclaration TVA")
    )

    tiers = django_filters.CharFilter(lookup_expr="icontains", label=_("Tiers"))

    montant_min = django_filters.NumberFilter(
        field_name="montant_ttc", lookup_expr="gte", label=_("Montant TTC minimum")
    )

    montant_max = django_filters.NumberFilter(
        field_name="montant_ttc", lookup_expr="lte", label=_("Montant TTC maximum")
    )

    class Meta:
        model = OperationTVA
        fields = [
            "mandat",
            "type_operation",
            "date_operation",
            "code_tva",
            "integre_declaration",
            "declaration_tva",
            "tiers",
        ]
