# documents/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from .models import Dossier, CategorieDocument, TypeDocument, Document
from core.models import Mandat, Client


class DossierForm(forms.ModelForm):
    """Formulaire pour un dossier"""

    class Meta:
        model = Dossier
        fields = [
            "parent",
            "client",
            "mandat",
            "nom",
            "type_dossier",
            "description",
            "tags",
            "acces_restreint",
            "utilisateurs_autorises",
        ]
        widgets = {
            "parent": forms.Select(attrs={"class": "form-control select2", "id": "id_parent"}),
            "client": forms.Select(attrs={"class": "form-control select2"}),
            "mandat": forms.Select(attrs={"class": "form-control select2", "id": "id_mandat"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "type_dossier": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tags": forms.TextInput(attrs={"class": "form-control"}),
            "acces_restreint": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "utilisateurs_autorises": forms.SelectMultiple(
                attrs={"class": "form-control select2"}
            ),
        }

    def __init__(self, *args, **kwargs):
        mandat_initial = kwargs.pop('mandat', None)
        super().__init__(*args, **kwargs)

        # Déterminer le mandat sélectionné
        mandat_selectionne = None
        if self.instance and self.instance.pk and self.instance.mandat_id:
            mandat_selectionne = self.instance.mandat
        elif mandat_initial:
            mandat_selectionne = mandat_initial
        elif self.data.get('mandat'):
            try:
                mandat_selectionne = Mandat.objects.get(pk=self.data.get('mandat'))
            except Mandat.DoesNotExist:
                pass

        # Filtrer les dossiers parents selon le mandat
        if mandat_selectionne:
            # Dossiers du même mandat ou du client
            self.fields['parent'].queryset = Dossier.objects.filter(
                Q(mandat=mandat_selectionne) | Q(client=mandat_selectionne.client),
                is_active=True
            ).exclude(pk=self.instance.pk if self.instance.pk else None).order_by('chemin_complet')
            self.fields['parent'].empty_label = _("Aucun (dossier racine)")
        else:
            # Afficher tous les dossiers avec indication du mandat
            self.fields['parent'].queryset = Dossier.objects.filter(
                is_active=True
            ).exclude(pk=self.instance.pk if self.instance.pk else None).select_related('mandat').order_by('chemin_complet')
            self.fields['parent'].empty_label = _("Sélectionnez d'abord un mandat")

        # Mandats actifs
        self.fields['mandat'].queryset = Mandat.objects.filter(
            statut='ACTIF',
            is_active=True
        ).select_related('client').order_by('numero') 


class CategorieDocumentForm(forms.ModelForm):
    """Formulaire pour une catégorie de document"""

    class Meta:
        model = CategorieDocument
        fields = [
            "nom",
            "description",
            "mots_cles",
            "patterns_regex",
            "icone",
            "couleur",
            "ordre",
            "parent",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "mots_cles": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "patterns_regex": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "icone": forms.TextInput(attrs={"class": "form-control"}),
            "couleur": forms.TextInput(
                attrs={"class": "form-control", "type": "color"}
            ),
            "ordre": forms.NumberInput(attrs={"class": "form-control"}),
            "parent": forms.Select(attrs={"class": "form-control select2"}),
        }


class TypeDocumentForm(forms.ModelForm):
    """Formulaire pour un type de document"""

    class Meta:
        model = TypeDocument
        fields = [
            "code",
            "libelle",
            "type_document",
            "categorie",
            "champs_extraire",
            "template_extraction",
            "validation_requise",
            "validateurs",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "libelle": forms.TextInput(attrs={"class": "form-control"}),
            "type_document": forms.Select(attrs={"class": "form-control"}),
            "categorie": forms.Select(attrs={"class": "form-control select2"}),
            "champs_extraire": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "template_extraction": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "validation_requise": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "validateurs": forms.SelectMultiple(attrs={"class": "form-control select2"}),
        }


class DocumentForm(forms.ModelForm):
    """Formulaire pour éditer un document"""

    class Meta:
        model = Document
        fields = [
            "mandat",
            "dossier",
            "type_document",
            "categorie",
            "date_document",
            "description",
            "notes",
            "tags",
            "confidentiel",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2", "id": "id_mandat"}),
            "dossier": forms.Select(attrs={"class": "form-control select2", "id": "id_dossier"}),
            "type_document": forms.Select(attrs={"class": "form-control"}),
            "categorie": forms.Select(attrs={"class": "form-control select2"}),
            "date_document": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "tags": forms.TextInput(attrs={"class": "form-control"}),
            "confidentiel": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        mandat_initial = kwargs.pop('mandat', None)
        super().__init__(*args, **kwargs)

        # Mandats actifs
        self.fields['mandat'].queryset = Mandat.objects.filter(
            statut='ACTIF',
            is_active=True
        ).select_related('client').order_by('numero')

        # Déterminer le mandat sélectionné
        mandat_selectionne = None
        if self.instance and self.instance.pk and self.instance.mandat_id:
            mandat_selectionne = self.instance.mandat
        elif mandat_initial:
            mandat_selectionne = mandat_initial
        elif self.data.get('mandat'):
            try:
                mandat_selectionne = Mandat.objects.get(pk=self.data.get('mandat'))
            except Mandat.DoesNotExist:
                pass

        # Filtrer les dossiers selon le mandat
        if mandat_selectionne:
            self.fields['dossier'].queryset = Dossier.objects.filter(
                Q(mandat=mandat_selectionne) | Q(client=mandat_selectionne.client),
                is_active=True
            ).select_related('parent').order_by('chemin_complet')
            self.fields['dossier'].empty_label = _("Sélectionner un dossier (optionnel)")
        else:
            self.fields['dossier'].queryset = Dossier.objects.none()
            self.fields['dossier'].empty_label = _("Sélectionnez d'abord un mandat")

        self.fields['dossier'].required = False


class DocumentUploadForm(forms.ModelForm):
    """Formulaire pour uploader un document"""

    fichier = forms.FileField(
        label=_("Fichier"), widget=forms.FileInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = Document
        fields = ["mandat", "dossier", "description", "tags"]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2", "id": "id_mandat"}),
            "dossier": forms.Select(attrs={"class": "form-control select2", "id": "id_dossier"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "tags": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        mandat_initial = kwargs.pop('mandat', None)
        super().__init__(*args, **kwargs)

        # Mandats actifs
        self.fields['mandat'].queryset = Mandat.objects.filter(
            statut='ACTIF',
            is_active=True
        ).select_related('client').order_by('numero')

        # Déterminer le mandat sélectionné
        mandat_selectionne = None
        if mandat_initial:
            mandat_selectionne = mandat_initial
        elif self.data.get('mandat'):
            try:
                mandat_selectionne = Mandat.objects.get(pk=self.data.get('mandat'))
            except Mandat.DoesNotExist:
                pass

        # Filtrer les dossiers selon le mandat
        if mandat_selectionne:
            self.fields['dossier'].queryset = Dossier.objects.filter(
                Q(mandat=mandat_selectionne) | Q(client=mandat_selectionne.client),
                is_active=True
            ).select_related('parent').order_by('chemin_complet')
            self.fields['dossier'].empty_label = _("Sélectionner un dossier (optionnel)")
        else:
            self.fields['dossier'].queryset = Dossier.objects.none()
            self.fields['dossier'].empty_label = _("Sélectionnez d'abord un mandat")

        self.fields['dossier'].required = False
