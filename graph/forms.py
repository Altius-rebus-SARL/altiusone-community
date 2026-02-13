# graph/forms.py
import json
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import OntologieType, Entite, Relation, Anomalie, RequeteSauvegardee


class OntologieTypeForm(forms.ModelForm):
    """Formulaire pour les types d'ontologie."""

    schema_attributs = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 8,
            'placeholder': '{"champ1": {"type": "text", "label": "Champ 1", "required": true}}',
        }),
        required=False,
        help_text=_('Schéma JSON des attributs dynamiques'),
    )

    class Meta:
        model = OntologieType
        fields = [
            'categorie', 'nom', 'nom_pluriel', 'description',
            'icone', 'couleur', 'schema_attributs',
            'source_types_autorises', 'cible_types_autorises',
            'verbe', 'verbe_inverse', 'bidirectionnel',
            'ordre_affichage',
        ]
        widgets = {
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'nom_pluriel': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ph-user',
            }),
            'couleur': forms.TextInput(attrs={
                'class': 'form-control', 'type': 'color',
            }),
            'source_types_autorises': forms.SelectMultiple(attrs={
                'class': 'form-select select2',
            }),
            'cible_types_autorises': forms.SelectMultiple(attrs={
                'class': 'form-select select2',
            }),
            'verbe': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': _('emploie'),
            }),
            'verbe_inverse': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': _('est employé par'),
            }),
            'bidirectionnel': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'ordre_affichage': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convertir le JSON en texte pour l'édition
        if self.instance and self.instance.pk:
            val = self.instance.schema_attributs
            if val:
                self.initial['schema_attributs'] = json.dumps(val, indent=2, ensure_ascii=False)

        # Filtrer les M2M : seuls les types entity pour source/cible
        entity_qs = OntologieType.objects.filter(categorie='entity', is_active=True)
        self.fields['source_types_autorises'].queryset = entity_qs
        self.fields['cible_types_autorises'].queryset = entity_qs

    def clean_schema_attributs(self):
        val = self.cleaned_data.get('schema_attributs', '')
        if not val or not val.strip():
            return {}
        try:
            return json.loads(val)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(
                _('JSON invalide: %(error)s'), params={'error': str(e)},
            )


class EntiteForm(forms.ModelForm):
    """Formulaire pour les entités (champs dynamiques selon le type)."""

    latitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': 'any', 'placeholder': '46.2044',
        }),
    )
    longitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': 'any', 'placeholder': '6.1432',
        }),
    )
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': _('tag1, tag2, tag3'),
        }),
        help_text=_('Tags séparés par des virgules'),
    )

    class Meta:
        model = Entite
        fields = [
            'type', 'nom', 'description',
            'source', 'confiance',
        ]
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select', 'id': 'id_type'}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'confiance': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '1',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].queryset = OntologieType.objects.filter(
            categorie='entity', is_active=True,
        )

        # Pré-remplir lat/lng et tags depuis l'instance
        if self.instance and self.instance.pk:
            if self.instance.geom:
                self.initial['latitude'] = self.instance.geom.y
                self.initial['longitude'] = self.instance.geom.x
            if self.instance.tags:
                self.initial['tags_input'] = ', '.join(str(t) for t in self.instance.tags)

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Géolocalisation
        lat = self.cleaned_data.get('latitude')
        lng = self.cleaned_data.get('longitude')
        if lat is not None and lng is not None:
            from django.contrib.gis.geos import Point
            instance.geom = Point(lng, lat, srid=4326)
        elif lat is None and lng is None:
            instance.geom = None

        # Tags
        tags_raw = self.cleaned_data.get('tags_input', '')
        instance.tags = [t.strip() for t in tags_raw.split(',') if t.strip()]

        if commit:
            instance.save()
        return instance


class RelationForm(forms.ModelForm):
    """Formulaire pour les relations."""

    class Meta:
        model = Relation
        fields = [
            'type', 'source', 'cible',
            'poids', 'date_debut', 'date_fin', 'en_cours',
            'document_preuve', 'confiance',
        ]
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.Select(attrs={'class': 'form-select select2'}),
            'cible': forms.Select(attrs={'class': 'form-select select2'}),
            'poids': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.1', 'min': '0',
            }),
            'date_debut': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'date_fin': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'en_cours': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'document_preuve': forms.Select(attrs={'class': 'form-select select2'}),
            'confiance': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '1',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].queryset = OntologieType.objects.filter(
            categorie='relation', is_active=True,
        )
        self.fields['source'].queryset = Entite.objects.filter(is_active=True)
        self.fields['cible'].queryset = Entite.objects.filter(is_active=True)


class AnomalieTraiterForm(forms.Form):
    """Formulaire pour traiter une anomalie."""

    statut = forms.ChoiceField(
        choices=[
            ('en_cours', _('En cours d\'analyse')),
            ('confirme', _('Confirmé')),
            ('rejete', _('Rejeté')),
            ('resolu', _('Résolu')),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    commentaire = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': _('Commentaire de résolution...'),
        }),
    )


class ImportCSVForm(forms.Form):
    """Formulaire pour l'import CSV d'entités."""

    file = forms.FileField(
        label=_('Fichier CSV'),
        widget=forms.FileInput(attrs={
            'class': 'form-control', 'accept': '.csv',
        }),
    )
    type_id = forms.ModelChoiceField(
        queryset=OntologieType.objects.filter(categorie='entity', is_active=True),
        label=_('Type d\'entité'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    mapping_json = forms.CharField(
        label=_('Mapping colonnes'),
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace', 'rows': 5,
            'placeholder': '{"Colonne CSV": "nom", "Adresse": "attributs.adresse"}',
        }),
        help_text=_('JSON mapping: {colonne_csv: champ_entite}'),
    )

    def clean_mapping_json(self):
        val = self.cleaned_data.get('mapping_json', '')
        try:
            mapping = json.loads(val)
            if not isinstance(mapping, dict):
                raise forms.ValidationError(_('Le mapping doit être un objet JSON'))
            return mapping
        except json.JSONDecodeError as e:
            raise forms.ValidationError(
                _('JSON invalide: %(error)s'), params={'error': str(e)},
            )


class RequeteSauvegardeeForm(forms.ModelForm):
    """Formulaire pour sauvegarder une requête."""

    class Meta:
        model = RequeteSauvegardee
        fields = [
            'nom', 'description',
            'entite_depart', 'profondeur',
            'date_min', 'date_max',
            'partage',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'entite_depart': forms.Select(attrs={'class': 'form-select select2'}),
            'profondeur': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'max': 10,
            }),
            'date_min': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_max': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'partage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
