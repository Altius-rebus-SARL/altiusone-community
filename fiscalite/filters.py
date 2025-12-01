# fiscalite/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import DeclarationFiscale, OptimisationFiscale
from core.models import Mandat


class DeclarationFiscaleFilter(django_filters.FilterSet):
    """Filtres pour les déclarations fiscales"""

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    numero_declaration = django_filters.CharFilter(
        lookup_expr="icontains", label=_("Numéro")
    )

    type_declaration = django_filters.ChoiceFilter(
        choices=DeclarationFiscale.TYPE_DECLARATION_CHOICES,
        label=_("Type de déclaration"),
    )

    type_impot = django_filters.ChoiceFilter(
        choices=DeclarationFiscale.TYPE_IMPOT_CHOICES, label=_("Type d'impôt")
    )

    annee_fiscale = django_filters.NumberFilter(label=_("Année fiscale"))

    canton = django_filters.CharFilter(lookup_expr="iexact", label=_("Canton"))

    statut = django_filters.ChoiceFilter(
        choices=DeclarationFiscale.STATUT_CHOICES, label=_("Statut")
    )

    class Meta:
        model = DeclarationFiscale
        fields = [
            "mandat",
            "numero_declaration",
            "type_declaration",
            "type_impot",
            "annee_fiscale",
            "canton",
            "statut",
        ]


class OptimisationFiscaleFilter(django_filters.FilterSet):
    """Filtres pour les optimisations fiscales"""

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    categorie = django_filters.ChoiceFilter(
        choices=OptimisationFiscale.CATEGORIE_CHOICES, label=_("Catégorie")
    )

    statut = django_filters.ChoiceFilter(
        choices=OptimisationFiscale.STATUT_CHOICES, label=_("Statut")
    )

    niveau_risque = django_filters.ChoiceFilter(
        choices=[("FAIBLE", "Faible"), ("MOYEN", "Moyen"), ("ELEVE", "Élevé")],
        label=_("Niveau de risque"),
    )

    annee_application = django_filters.NumberFilter(label=_("Année d'application"))

    economie_min = django_filters.NumberFilter(
        field_name="economie_estimee", lookup_expr="gte", label=_("Économie minimale")
    )

    class Meta:
        model = OptimisationFiscale
        fields = ["mandat", "categorie", "statut", "niveau_risque", "annee_application"]
