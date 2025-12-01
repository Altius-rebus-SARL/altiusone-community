# comptabilite/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Compte, EcritureComptable, PieceComptable, Journal, PlanComptable
from core.models import Mandat


# comptabilite/filters.py


class PlanComptableFilter(django_filters.FilterSet):
    """Filtres pour les plans comptables"""

    nom = django_filters.CharFilter(
        field_name="nom", lookup_expr="icontains", label=_("Rechercher")
    )

    type_plan = django_filters.ChoiceFilter(
        choices=PlanComptable.TYPE_CHOICES,
        label=_("Type de plan"),
        empty_label=_("Type de plan"),
    )

    is_template = django_filters.ChoiceFilter(
        choices=[
            ("", _("Tous les plans")),
            ("true", _("Templates uniquement")),
            ("false", _("Instances uniquement")),
        ],
        label=_("Filtrer par type"),
        empty_label=None,
        method="filter_is_template",
    )

    class Meta:
        model = PlanComptable
        fields = ["nom", "type_plan", "is_template"]

    def filter_is_template(self, queryset, name, value):
        if value == "true":
            return queryset.filter(is_template=True)
        elif value == "false":
            return queryset.filter(is_template=False)
        return queryset
    

class CompteFilter(django_filters.FilterSet):
    """Filtres pour les comptes"""

    numero = django_filters.CharFilter(lookup_expr="icontains", label=_("Numéro"))

    libelle = django_filters.CharFilter(lookup_expr="icontains", label=_("Libellé"))

    type_compte = django_filters.ChoiceFilter(
        choices=Compte.TYPE_COMPTE_CHOICES, label=_("Type de compte")
    )

    classe = django_filters.ChoiceFilter(
        choices=Compte.CLASSE_CHOICES, label=_("Classe")
    )

    imputable = django_filters.BooleanFilter(
        label=_("Imputable"), widget=forms.CheckboxInput()
    )

    lettrable = django_filters.BooleanFilter(
        label=_("Lettrable"), widget=forms.CheckboxInput()
    )

    est_collectif = django_filters.BooleanFilter(
        label=_("Collectif"), widget=forms.CheckboxInput()
    )

    class Meta:
        model = Compte
        fields = [
            "numero",
            "libelle",
            "type_compte",
            "classe",
            "imputable",
            "lettrable",
            "est_collectif",
        ]


class EcritureComptableFilter(django_filters.FilterSet):
    """Filtres pour les écritures comptables"""

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    journal = django_filters.ModelChoiceFilter(
        queryset=Journal.objects.all(), label=_("Journal")
    )

    compte__numero = django_filters.CharFilter(
        lookup_expr="icontains", label=_("Numéro de compte")
    )

    numero_piece = django_filters.CharFilter(
        lookup_expr="icontains", label=_("Numéro de pièce")
    )

    libelle = django_filters.CharFilter(lookup_expr="icontains", label=_("Libellé"))

    date_ecriture = django_filters.DateFromToRangeFilter(label=_("Date"))

    statut = django_filters.ChoiceFilter(
        choices=EcritureComptable.STATUT_CHOICES, label=_("Statut")
    )

    code_lettrage = django_filters.CharFilter(
        lookup_expr="iexact", label=_("Code lettrage")
    )

    montant_min = django_filters.NumberFilter(
        method="filter_montant_min", label=_("Montant minimum")
    )

    montant_max = django_filters.NumberFilter(
        method="filter_montant_max", label=_("Montant maximum")
    )

    class Meta:
        model = EcritureComptable
        fields = [
            "mandat",
            "journal",
            "compte__numero",
            "numero_piece",
            "libelle",
            "date_ecriture",
            "statut",
            "code_lettrage",
        ]

    def filter_montant_min(self, queryset, name, value):
        from django.db.models import Q

        return queryset.filter(
            Q(montant_debit__gte=value) | Q(montant_credit__gte=value)
        )

    def filter_montant_max(self, queryset, name, value):
        from django.db.models import Q

        return queryset.filter(
            Q(montant_debit__lte=value) | Q(montant_credit__lte=value)
        )


class PieceComptableFilter(django_filters.FilterSet):
    """Filtres pour les pièces comptables"""

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    journal = django_filters.ModelChoiceFilter(
        queryset=Journal.objects.all(), label=_("Journal")
    )

    numero_piece = django_filters.CharFilter(
        lookup_expr="icontains", label=_("Numéro de pièce")
    )

    libelle = django_filters.CharFilter(lookup_expr="icontains", label=_("Libellé"))

    date_piece = django_filters.DateFromToRangeFilter(label=_("Date"))

    equilibree = django_filters.BooleanFilter(
        label=_("Équilibrée"), widget=forms.CheckboxInput()
    )

    statut = django_filters.ChoiceFilter(
        choices=PieceComptable.STATUT_CHOICES, label=_("Statut")
    )

    class Meta:
        model = PieceComptable
        fields = [
            "mandat",
            "journal",
            "numero_piece",
            "libelle",
            "date_piece",
            "equilibree",
            "statut",
        ]
