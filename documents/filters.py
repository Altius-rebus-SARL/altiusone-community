# documents/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Document, Dossier, TypeDocument, CategorieDocument
from core.models import Mandat, Client


class DocumentFilter(django_filters.FilterSet):
    """Filtres pour les documents"""

    nom_fichier = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Nom fichier"),
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Rechercher...")})
    )

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"),
        label=_("Mandat"),
        empty_label=_("Tous les mandats"),
        widget=forms.Select(attrs={"class": "form-select select2"})
    )

    dossier = django_filters.ModelChoiceFilter(
        queryset=Dossier.objects.all(),
        label=_("Dossier"),
        empty_label=_("Tous les dossiers"),
        widget=forms.Select(attrs={"class": "form-select select2"})
    )

    type_document = django_filters.ModelChoiceFilter(
        queryset=TypeDocument.objects.all(),
        label=_("Type de document"),
        empty_label=_("Tous les types"),
        widget=forms.Select(attrs={"class": "form-select select2"})
    )

    categorie = django_filters.ModelChoiceFilter(
        queryset=CategorieDocument.objects.all(),
        label=_("Catégorie"),
        empty_label=_("Toutes les catégories"),
        widget=forms.Select(attrs={"class": "form-select select2"})
    )

    date_upload = django_filters.DateFromToRangeFilter(
        label=_("Date upload"),
        widget=django_filters.widgets.RangeWidget(attrs={"class": "form-control", "type": "date"})
    )

    date_document = django_filters.DateFromToRangeFilter(
        label=_("Date document"),
        widget=django_filters.widgets.RangeWidget(attrs={"class": "form-control", "type": "date"})
    )

    extension = django_filters.CharFilter(
        lookup_expr="iexact",
        label=_("Extension"),
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": ".pdf"})
    )

    statut_traitement = django_filters.ChoiceFilter(
        choices=Document.STATUT_TRAITEMENT_CHOICES,
        label=_("Statut traitement"),
        empty_label=_("Tous"),
        widget=forms.Select(attrs={"class": "form-select"})
    )

    statut_validation = django_filters.ChoiceFilter(
        choices=Document.STATUT_VALIDATION_CHOICES,
        label=_("Statut validation"),
        empty_label=_("Tous"),
        widget=forms.Select(attrs={"class": "form-select"})
    )

    confidentiel = django_filters.ChoiceFilter(
        label=_("Confidentiel"),
        choices=[
            ('', _('Tous')),
            ('true', _('Confidentiel')),
            ('false', _('Non confidentiel')),
        ],
        method='filter_confidentiel',
        widget=forms.Select(attrs={"class": "form-select"})
    )

    taille_min = django_filters.NumberFilter(
        field_name="taille",
        lookup_expr="gte",
        label=_("Taille min (octets)"),
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "0"})
    )

    taille_max = django_filters.NumberFilter(
        field_name="taille",
        lookup_expr="lte",
        label=_("Taille max (octets)"),
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "0"})
    )

    def filter_confidentiel(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(confidentiel=True)
        elif value == 'false':
            return queryset.filter(confidentiel=False)
        return queryset

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

    nom = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Nom"),
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Rechercher...")})
    )

    type_dossier = django_filters.ChoiceFilter(
        choices=Dossier.TYPE_CHOICES,
        label=_("Type"),
        empty_label=_("Tous les types"),
        widget=forms.Select(attrs={"class": "form-select"})
    )

    client = django_filters.ModelChoiceFilter(
        queryset=Client.objects.filter(statut="ACTIF"),
        label=_("Client"),
        empty_label=_("Tous les clients"),
        widget=forms.Select(attrs={"class": "form-select select2"})
    )

    mandat = django_filters.ModelChoiceFilter(
        queryset=Mandat.objects.filter(statut="ACTIF"),
        label=_("Mandat"),
        empty_label=_("Tous les mandats"),
        widget=forms.Select(attrs={"class": "form-select select2"})
    )

    parent = django_filters.ModelChoiceFilter(
        queryset=Dossier.objects.all(),
        label=_("Dossier parent"),
        empty_label=_("Tous"),
        widget=forms.Select(attrs={"class": "form-select select2"})
    )

    acces_restreint = django_filters.ChoiceFilter(
        label=_("Accès restreint"),
        choices=[
            ('', _('Tous')),
            ('true', _('Restreint')),
            ('false', _('Non restreint')),
        ],
        method='filter_acces_restreint',
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def filter_acces_restreint(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(acces_restreint=True)
        elif value == 'false':
            return queryset.filter(acces_restreint=False)
        return queryset

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
