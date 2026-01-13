"""
Formulaires pour l'application Éditeur Collaboratif.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from .models import (
    DocumentCollaboratif,
    PartageDocument,
    LienPartagePublic,
    ModeleDocument
)

User = get_user_model()


class DocumentCollaboratifForm(forms.ModelForm):
    """Formulaire de création/modification d'un document collaboratif."""

    class Meta:
        model = DocumentCollaboratif
        fields = [
            'titre',
            'description',
            'type_document',
            'mandat',
            'client',
            'dossier',
            'langue',
            'est_public',
        ]
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _("Titre du document"),
                'autofocus': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _("Description optionnelle")
            }),
            'type_document': forms.Select(attrs={
                'class': 'form-select'
            }),
            'mandat': forms.Select(attrs={
                'class': 'form-select'
            }),
            'client': forms.Select(attrs={
                'class': 'form-select'
            }),
            'dossier': forms.Select(attrs={
                'class': 'form-select'
            }),
            'langue': forms.Select(attrs={
                'class': 'form-select'
            }),
            'est_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user:
            # Filtrer les mandats accessibles
            from core.models import Mandat
            mandats = Mandat.objects.filter(
                id__in=user.mandats_accessibles.values_list('id', flat=True)
            )
            self.fields['mandat'].queryset = mandats
            self.fields['mandat'].required = False

            # Filtrer les clients
            from core.models import Client
            clients = Client.objects.filter(mandats__in=mandats).distinct()
            self.fields['client'].queryset = clients
            self.fields['client'].required = False

            # Filtrer les dossiers
            from documents.models import Dossier
            dossiers = Dossier.objects.filter(mandat__in=mandats)
            self.fields['dossier'].queryset = dossiers
            self.fields['dossier'].required = False


class PartageDocumentForm(forms.ModelForm):
    """Formulaire de partage d'un document."""

    email_utilisateur = forms.EmailField(
        label=_("Email de l'utilisateur"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _("email@example.com")
        }),
        required=False
    )

    class Meta:
        model = PartageDocument
        fields = [
            'utilisateur',
            'niveau_acces',
            'date_expiration',
            'notifier_modifications',
        ]
        widgets = {
            'utilisateur': forms.Select(attrs={
                'class': 'form-select'
            }),
            'niveau_acces': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date_expiration': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'notifier_modifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, document=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.document = document

        if document:
            # Exclure les utilisateurs déjà partagés et le créateur
            partages_existants = document.partages.values_list('utilisateur_id', flat=True)
            exclusions = list(partages_existants) + [document.createur_id]

            self.fields['utilisateur'].queryset = User.objects.exclude(
                id__in=exclusions
            ).filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()

        # Si email fourni au lieu de sélection
        email = cleaned_data.get('email_utilisateur')
        utilisateur = cleaned_data.get('utilisateur')

        if email and not utilisateur:
            try:
                utilisateur = User.objects.get(email=email, is_active=True)
                cleaned_data['utilisateur'] = utilisateur
            except User.DoesNotExist:
                raise forms.ValidationError(
                    _("Aucun utilisateur avec cet email n'a été trouvé.")
                )

        if not cleaned_data.get('utilisateur'):
            raise forms.ValidationError(
                _("Veuillez sélectionner un utilisateur ou saisir un email.")
            )

        return cleaned_data


class LienPartagePublicForm(forms.ModelForm):
    """Formulaire de création d'un lien de partage public."""

    mot_de_passe = forms.CharField(
        label=_("Mot de passe (optionnel)"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _("Laisser vide pour un accès sans mot de passe")
        }),
        required=False
    )

    class Meta:
        model = LienPartagePublic
        fields = [
            'permet_edition',
            'permet_commentaire',
            'permet_telechargement',
            'date_expiration',
            'nombre_acces_max',
        ]
        widgets = {
            'permet_edition': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'permet_commentaire': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'permet_telechargement': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'date_expiration': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'nombre_acces_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': _("Illimité si vide")
            }),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)

        mot_de_passe = self.cleaned_data.get('mot_de_passe')
        if mot_de_passe:
            from django.contrib.auth.hashers import make_password
            instance.mot_de_passe_hash = make_password(mot_de_passe)

        if commit:
            instance.save()

        return instance


class ModeleDocumentForm(forms.ModelForm):
    """Formulaire de création/modification d'un modèle."""

    class Meta:
        model = ModeleDocument
        fields = [
            'nom',
            'description',
            'categorie',
            'type_document',
            'langue',
            'est_public',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _("Nom du modèle")
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'categorie': forms.Select(attrs={
                'class': 'form-select'
            }),
            'type_document': forms.Select(attrs={
                'class': 'form-select'
            }),
            'langue': forms.Select(attrs={
                'class': 'form-select'
            }),
            'est_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class RechercheDocumentForm(forms.Form):
    """Formulaire de recherche de documents collaboratifs."""

    q = forms.CharField(
        label=_("Recherche"),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _("Rechercher...")
        })
    )

    statut = forms.ChoiceField(
        label=_("Statut"),
        required=False,
        choices=[('', _("Tous"))] + list(DocumentCollaboratif.Statut.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    type_document = forms.ChoiceField(
        label=_("Type"),
        required=False,
        choices=[('', _("Tous"))] + list(DocumentCollaboratif.TypeDocument.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_debut = forms.DateField(
        label=_("Date début"),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    date_fin = forms.DateField(
        label=_("Date fin"),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
