# graph/filters.py
import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import OntologieType, Entite, Relation, Anomalie


class EntiteFilter(django_filters.FilterSet):
    """Filtres pour les entités du graphe."""

    nom = django_filters.CharFilter(
        lookup_expr='icontains',
        label=_('Nom'),
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': _('Rechercher...'),
        }),
    )

    type = django_filters.ModelChoiceFilter(
        queryset=OntologieType.objects.filter(categorie='entity', is_active=True),
        label=_('Type'),
        empty_label=_('Tous les types'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    source = django_filters.ChoiceFilter(
        choices=Entite.Source.choices,
        label=_('Source'),
        empty_label=_('Toutes'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    confiance_min = django_filters.NumberFilter(
        field_name='confiance',
        lookup_expr='gte',
        label=_('Confiance min'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '1',
        }),
    )

    verifie = django_filters.ChoiceFilter(
        label=_('Vérifié'),
        choices=[('', _('Tous')), ('true', _('Oui')), ('false', _('Non'))],
        method='filter_verifie',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    created_at = django_filters.DateFromToRangeFilter(
        label=_('Date de création'),
        widget=django_filters.widgets.RangeWidget(attrs={
            'class': 'form-control', 'type': 'date',
        }),
    )

    has_anomalies = django_filters.ChoiceFilter(
        label=_('Anomalies'),
        choices=[('', _('Tous')), ('true', _('Avec anomalies')), ('false', _('Sans anomalies'))],
        method='filter_has_anomalies',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def filter_verifie(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(verifie=True)
        elif value == 'false':
            return queryset.filter(verifie=False)
        return queryset

    def filter_has_anomalies(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(
                anomalies__statut__in=['nouveau', 'en_cours'],
            ).distinct()
        elif value == 'false':
            return queryset.exclude(
                anomalies__statut__in=['nouveau', 'en_cours'],
            )
        return queryset

    class Meta:
        model = Entite
        fields = ['nom', 'type', 'source', 'confiance_min', 'verifie', 'created_at']


class RelationFilter(django_filters.FilterSet):
    """Filtres pour les relations du graphe."""

    type = django_filters.ModelChoiceFilter(
        queryset=OntologieType.objects.filter(categorie='relation', is_active=True),
        label=_('Type'),
        empty_label=_('Tous les types'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    en_cours = django_filters.ChoiceFilter(
        label=_('En cours'),
        choices=[('', _('Tous')), ('true', _('Oui')), ('false', _('Non'))],
        method='filter_en_cours',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    date_debut = django_filters.DateFromToRangeFilter(
        label=_('Date de début'),
        widget=django_filters.widgets.RangeWidget(attrs={
            'class': 'form-control', 'type': 'date',
        }),
    )

    def filter_en_cours(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(en_cours=True)
        elif value == 'false':
            return queryset.filter(en_cours=False)
        return queryset

    class Meta:
        model = Relation
        fields = ['type', 'en_cours', 'date_debut']


class AnomalieFilter(django_filters.FilterSet):
    """Filtres pour les anomalies."""

    type = django_filters.ChoiceFilter(
        choices=Anomalie.TypeAnomalie.choices,
        label=_('Type'),
        empty_label=_('Tous les types'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    statut = django_filters.ChoiceFilter(
        choices=Anomalie.Statut.choices,
        label=_('Statut'),
        empty_label=_('Tous'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    score_min = django_filters.NumberFilter(
        field_name='score',
        lookup_expr='gte',
        label=_('Score min'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '1',
        }),
    )

    class Meta:
        model = Anomalie
        fields = ['type', 'statut', 'score_min']
