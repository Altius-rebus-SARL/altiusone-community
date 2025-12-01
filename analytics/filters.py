# analytics/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Rapport, AlerteMetrique
from core.models import Mandat


class RapportFilter(django_filters.FilterSet):
    """Filtres pour les rapports"""

    nom = django_filters.CharFilter(lookup_expr="icontains", label=_("Nom"))

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    type_rapport = django_filters.ChoiceFilter(
        choices=Rapport.TYPE_RAPPORT_CHOICES, label=_("Type de rapport")
    )

    format_fichier = django_filters.ChoiceFilter(
        choices=[("PDF", "PDF"), ("EXCEL", "Excel"), ("CSV", "CSV")], label=_("Format")
    )

    date_generation = django_filters.DateFromToRangeFilter(
        label=_("Date de génération")
    )

    statut = django_filters.ChoiceFilter(
        choices=[
            ("EN_COURS", "En cours"),
            ("TERMINE", "Terminé"),
            ("ERREUR", "Erreur"),
        ],
        label=_("Statut"),
    )

    class Meta:
        model = Rapport
        fields = [
            "nom",
            "mandat",
            "type_rapport",
            "format_fichier",
            "date_generation",
            "statut",
        ]


class AlerteMetriqueFilter(django_filters.FilterSet):
    """Filtres pour les alertes"""

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    niveau = django_filters.ChoiceFilter(
        choices=[
            ("INFO", "Info"),
            ("ATTENTION", "Attention"),
            ("CRITIQUE", "Critique"),
        ],
        label=_("Niveau"),
    )

    statut = django_filters.ChoiceFilter(
        choices=[
            ("ACTIVE", "Active"),
            ("ACQUITTEE", "Acquittée"),
            ("RESOLUE", "Résolue"),
        ],
        label=_("Statut"),
    )

    date_detection = django_filters.DateFromToRangeFilter(label=_("Date de détection"))

    class Meta:
        model = AlerteMetrique
        fields = ["mandat", "niveau", "statut", "date_detection"]
