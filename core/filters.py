# core/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Client, Mandat, Tache, User



class ClientFilter(django_filters.FilterSet):
    """Filtres pour les clients"""

    raison_sociale = django_filters.CharFilter(
        lookup_expr="icontains", label=_("Raison sociale")
    )

    forme_juridique = django_filters.ChoiceFilter(
        choices=Client.FORME_JURIDIQUE_CHOICES, label=_("Forme juridique")
    )

    statut = django_filters.ChoiceFilter(
        choices=Client.STATUT_CHOICES, label=_("Statut")
    )

    canton = django_filters.CharFilter(
        field_name="adresse_siege__canton", label=_("Canton")
    )

    responsable = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(role__in=["ADMIN", "MANAGER", "COMPTABLE"]),
        label=_("Responsable"),
    )

    class Meta:
        model = Client
        fields = [
            "raison_sociale",
            "forme_juridique",
            "statut",
            "canton",
            "responsable",
        ]


class MandatFilter(django_filters.FilterSet):
    """Filtres pour les mandats"""

    numero = django_filters.CharFilter(lookup_expr="icontains", label=_("Numéro"))

    client__raison_sociale = django_filters.CharFilter(
        lookup_expr="icontains", label=_("Client")
    )

    type_mandat = django_filters.ChoiceFilter(
        choices=Mandat.TYPE_CHOICES, label=_("Type")
    )

    statut = django_filters.ChoiceFilter(
        choices=Mandat.STATUT_CHOICES, label=_("Statut")
    )

    responsable = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(), label=_("Responsable")
    )

    date_debut = django_filters.DateFromToRangeFilter(label=_("Date début"))

    class Meta:
        model = Mandat
        fields = [
            "numero",
            "client__raison_sociale",
            "type_mandat",
            "statut",
            "responsable",
        ]


class TacheFilter(django_filters.FilterSet):
    """Filtres pour les tâches"""

    titre = django_filters.CharFilter(lookup_expr="icontains", label=_("Titre"))

    statut = django_filters.ChoiceFilter(
        choices=Tache.STATUT_CHOICES, label=_("Statut")
    )

    priorite = django_filters.ChoiceFilter(
        choices=Tache.PRIORITE_CHOICES, label=_("Priorité")
    )

    assigne_a = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(), label=_("Assigné à")
    )

    date_echeance = django_filters.DateFromToRangeFilter(label=_("Échéance"))

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.all(), label=_("Mandat")
    )

    class Meta:
        model = Tache
        fields = ["titre", "statut", "priorite", "assigne_a", "date_echeance", "mandat"]
