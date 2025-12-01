# facturation/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Facture, TimeTracking, Paiement, Prestation
from core.models import Mandat, Client, User


class FactureFilter(django_filters.FilterSet):
    """Filtres pour les factures"""

    numero_facture = django_filters.CharFilter(
        lookup_expr="icontains", label=_("Numéro")
    )

    client = django_filters.ModelChoiceFilter(
        queryset=Client.objects.filter(statut="ACTIF"), label=_("Client")
    )

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    type_facture = django_filters.ChoiceFilter(
        choices=Facture.TYPE_CHOICES, label=_("Type")
    )

    statut = django_filters.ChoiceFilter(
        choices=Facture.STATUT_CHOICES, label=_("Statut")
    )

    date_emission = django_filters.DateFromToRangeFilter(label=_("Date émission"))

    date_echeance = django_filters.DateFromToRangeFilter(label=_("Date échéance"))

    montant_min = django_filters.NumberFilter(
        field_name="montant_ttc", lookup_expr="gte", label=_("Montant minimum")
    )

    montant_max = django_filters.NumberFilter(
        field_name="montant_ttc", lookup_expr="lte", label=_("Montant maximum")
    )

    en_retard = django_filters.BooleanFilter(
        method="filter_en_retard", label=_("En retard"), widget=forms.CheckboxInput()
    )

    class Meta:
        model = Facture
        fields = [
            "numero_facture",
            "client",
            "mandat",
            "type_facture",
            "statut",
            "date_emission",
            "date_echeance",
        ]

    def filter_en_retard(self, queryset, name, value):
        from datetime import date

        if value:
            return queryset.filter(
                date_echeance__lt=date.today(),
                statut__in=["EMISE", "ENVOYEE", "RELANCEE", "EN_RETARD"],
            )
        return queryset


class TimeTrackingFilter(django_filters.FilterSet):
    """Filtres pour le time tracking"""

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    utilisateur = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(is_active=True), label=_("Utilisateur")
    )

    prestation = django_filters.ModelChoiceFilter(
        queryset=Prestation.objects.filter(actif=True), label=_("Prestation")
    )

    date_travail = django_filters.DateFromToRangeFilter(label=_("Date"))

    facturable = django_filters.BooleanFilter(
        label=_("Facturable"), widget=forms.CheckboxInput()
    )

    facture = django_filters.BooleanFilter(
        method="filter_facture", label=_("Facturé"), widget=forms.CheckboxInput()
    )

    valide = django_filters.BooleanFilter(
        label=_("Validé"), widget=forms.CheckboxInput()
    )

    class Meta:
        model = TimeTracking
        fields = [
            "mandat",
            "utilisateur",
            "prestation",
            "date_travail",
            "facturable",
            "valide",
        ]

    def filter_facture(self, queryset, name, value):
        if value:
            return queryset.filter(facture__isnull=False)
        else:
            return queryset.filter(facture__isnull=True)


class PaiementFilter(django_filters.FilterSet):
    """Filtres pour les paiements"""

    facture__numero_facture = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Numéro facture"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    facture__client = django_filters.ModelChoiceFilter(
        queryset=Client.objects.filter(statut="ACTIF"),
        label=_("Client"),
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )

    mode_paiement = django_filters.ChoiceFilter(
        choices=Paiement.MODE_PAIEMENT_CHOICES,
        label=_("Mode de paiement"),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Remplacer DateFromToRangeFilter par deux champs séparés
    date_paiement__gte = django_filters.DateFilter(
        field_name="date_paiement",
        lookup_expr="gte",
        label=_("Date début"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    date_paiement__lte = django_filters.DateFilter(
        field_name="date_paiement",
        lookup_expr="lte",
        label=_("Date fin"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    valide = django_filters.BooleanFilter(
        label=_("Validé"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    montant__gte = django_filters.NumberFilter(
        field_name="montant",
        lookup_expr="gte",
        label=_("Montant minimum"),
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    montant__lte = django_filters.NumberFilter(
        field_name="montant",
        lookup_expr="lte",
        label=_("Montant maximum"),
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    class Meta:
        model = Paiement
        fields = [
            "facture__numero_facture",
            "facture__client",
            "mode_paiement",
            "valide",
        ]
