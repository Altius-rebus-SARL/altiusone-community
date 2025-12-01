# documents/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Document, Dossier, TypeDocument, CategorieDocument
from core.models import Mandat, Client


class DocumentFilter(django_filters.FilterSet):
    """Filtres pour les documents"""

    nom_fichier = django_filters.CharFilter(
        lookup_expr="icontains", label=_("Nom fichier")
    )

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    dossier = django_filters.ModelChoiceFilter(
        queryset=Dossier.objects.all(), label=_("Dossier")
    )

    type_document = django_filters.ModelChoiceFilter(
        queryset=TypeDocument.objects.all(), label=_("Type de document")
    )

    categorie = django_filters.ModelChoiceFilter(
        queryset=CategorieDocument.objects.all(), label=_("Catégorie")
    )

    date_upload = django_filters.DateFromToRangeFilter(label=_("Date upload"))

    date_document = django_filters.DateFromToRangeFilter(label=_("Date document"))

    extension = django_filters.CharFilter(lookup_expr="iexact", label=_("Extension"))

    statut_traitement = django_filters.ChoiceFilter(
        choices=Document.STATUT_TRAITEMENT_CHOICES, label=_("Statut traitement")
    )

    statut_validation = django_filters.ChoiceFilter(
        choices=Document.STATUT_VALIDATION_CHOICES, label=_("Statut validation")
    )

    confidentiel = django_filters.BooleanFilter(
        label=_("Confidentiel"), widget=forms.CheckboxInput()
    )

    taille_min = django_filters.NumberFilter(
        field_name="taille", lookup_expr="gte", label=_("Taille minimum (octets)")
    )

    taille_max = django_filters.NumberFilter(
        field_name="taille", lookup_expr="lte", label=_("Taille maximum (octets)")
    )

    class Meta:
        model = Document
        fields = [
            "nom_fichier",
            "mandat",
            "dossier",
            "type_document",
            "categorie",
            "date_upload",
            "date_document",
            "extension",
            "statut_traitement",
            "statut_validation",
            "confidentiel",
        ]


class DossierFilter(django_filters.FilterSet):
    """Filtres pour les dossiers"""

    nom = django_filters.CharFilter(lookup_expr="icontains", label=_("Nom"))

    type_dossier = django_filters.ChoiceFilter(
        choices=Dossier.TYPE_CHOICES, label=_("Type")
    )

    client = django_filters.ModelChoiceFilter(
        queryset=Client.objects.filter(statut="ACTIF"), label=_("Client")
    )

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"), label=_("Mandat")
    )

    parent = django_filters.ModelChoiceFilter(
        queryset=Dossier.objects.all(), label=_("Dossier parent")
    )

    acces_restreint = django_filters.BooleanFilter(
        label=_("Accès restreint"), widget=forms.CheckboxInput()
    )

    class Meta:
        model = Dossier
        fields = [
            "nom",
            "type_dossier",
            "client",
            "mandat",
            "parent",
            "acces_restreint",
        ]
