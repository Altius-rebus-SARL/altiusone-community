# comptabilite/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Compte, EcritureComptable, PieceComptable, Journal, PlanComptable, TypePlanComptable
from core.models import Mandat


class PlanComptableFilter(django_filters.FilterSet):
    """Filtres pour les plans comptables"""

    nom = django_filters.CharFilter(
        field_name="nom", lookup_expr="icontains", label=_("Rechercher")
    )

    type_plan = django_filters.ModelChoiceFilter(
        queryset=TypePlanComptable.objects.filter(is_active=True).order_by('ordre', 'code'),
        label=_("Type de plan"),
        empty_label=_("Tous les types"),
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
        choices=[
            ('', _('Toutes les classes')),
            (1, _('1 - Actifs')),
            (2, _('2 - Passifs')),
            (3, _('3 - Charges d\'exploitation')),
            (4, _('4 - Produits d\'exploitation')),
            (5, _('5 - Charges financières')),
            (6, _('6 - Produits financiers')),
            (7, _('7 - Charges hors exploitation')),
            (8, _('8 - Produits hors exploitation')),
            (9, _('9 - Clôture')),
        ],
        label=_("Classe"),
        empty_label=None,
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

    equilibree = django_filters.ChoiceFilter(
        label=_("Équilibrée"),
        choices=[
            ('', _('Toutes')),
            ('true', _('Équilibrées')),
            ('false', _('Non équilibrées')),
        ],
        method='filter_equilibree',
    )

    def filter_equilibree(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(equilibree=True)
        elif value == 'false':
            return queryset.filter(equilibree=False)
        return queryset

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
