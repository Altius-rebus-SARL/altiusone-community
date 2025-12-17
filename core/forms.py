# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Client, Mandat, Contact, Tache, Adresse, ExerciceComptable, User


class AdresseForm(forms.ModelForm):
    """Formulaire pour une adresse avec support international"""

    class Meta:
        model = Adresse
        fields = ["rue", "numero", "complement", "code_postal", "localite", "region", "canton", "pays"]
        widgets = {
            "rue": forms.TextInput(attrs={"class": "form-control"}),
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "complement": forms.TextInput(attrs={"class": "form-control"}),
            "code_postal": forms.TextInput(attrs={"class": "form-control", "placeholder": "NPA / Code postal"}),
            "localite": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.TextInput(attrs={"class": "form-control", "placeholder": "Région / État (optionnel)"}),
            "canton": forms.Select(attrs={"class": "form-control select2"}),
            "pays": forms.Select(attrs={"class": "form-control select2"}),
        }


class ClientForm(forms.ModelForm):
    """Formulaire de création/modification d'un client"""

    class Meta:
        model = Client
        fields = [
            "raison_sociale",
            "nom_commercial",
            "forme_juridique",
            "ide_number",
            "tva_number",
            "rc_number",
            "email",
            "telephone",
            "site_web",
            "date_creation",
            "date_inscription_rc",
            "date_debut_exercice",
            "date_fin_exercice",
            "statut",
            "responsable",
            "notes",
        ]
        widgets = {
            "raison_sociale": forms.TextInput(attrs={"class": "form-control"}),
            "nom_commercial": forms.TextInput(attrs={"class": "form-control"}),
            "forme_juridique": forms.Select(attrs={"class": "form-control"}),
            "ide_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "CHE-XXX.XXX.XXX"}
            ),
            "tva_number": forms.TextInput(attrs={"class": "form-control"}),
            "rc_number": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "site_web": forms.URLInput(attrs={"class": "form-control"}),
            "date_creation": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_inscription_rc": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_debut_exercice": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin_exercice": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "statut": forms.Select(attrs={"class": "form-control"}),
            "responsable": forms.Select(attrs={"class": "form-control select2"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class MandatForm(forms.ModelForm):
    """Formulaire pour un mandat"""

    class Meta:
        model = Mandat
        fields = [
            "client",
            "type_mandat",
            "date_debut",
            "date_fin",
            "periodicite",
            "type_facturation",
            "montant_forfait",
            "taux_horaire",
            "responsable",
            "description",
            "conditions_particulieres",
        ]
        widgets = {
            "client": forms.Select(attrs={"class": "form-control select2"}),
            "type_mandat": forms.Select(attrs={"class": "form-control"}),
            "date_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "periodicite": forms.Select(attrs={"class": "form-control"}),
            "type_facturation": forms.Select(attrs={"class": "form-control"}),
            "montant_forfait": forms.NumberInput(attrs={"class": "form-control"}),
            "taux_horaire": forms.NumberInput(attrs={"class": "form-control"}),
            "responsable": forms.Select(attrs={"class": "form-control select2"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "conditions_particulieres": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }


class ContactForm(forms.ModelForm):
    """Formulaire pour un contact"""

    class Meta:
        model = Contact
        fields = [
            "client",
            "civilite",
            "nom",
            "prenom",
            "fonction",
            "email",
            "telephone",
            "mobile",
            "principal",
        ]
        widgets = {
            "client": forms.Select(attrs={"class": "form-control"}),
            "civilite": forms.Select(attrs={"class": "form-control"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "prenom": forms.TextInput(attrs={"class": "form-control"}),
            "fonction": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
            "principal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TacheForm(forms.ModelForm):
    """Formulaire pour une tâche"""

    class Meta:
        model = Tache
        fields = [
            "titre",
            "description",
            "assigne_a",
            "mandat",
            "priorite",
            "date_echeance",
            "temps_estime_heures",
            "tags",
        ]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "assigne_a": forms.Select(attrs={"class": "form-control"}),
            "mandat": forms.Select(attrs={"class": "form-control"}),
            "priorite": forms.Select(attrs={"class": "form-control"}),
            "date_echeance": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "temps_estime_heures": forms.NumberInput(attrs={"class": "form-control"}),
        }




class ExerciceComptableForm(forms.ModelForm):
    """Formulaire pour les exercices comptables"""

    class Meta:
        model = ExerciceComptable
        fields = [
            "mandat",
            "annee",
            "date_debut",
            "date_fin",
            "statut",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "annee": forms.NumberInput(
                attrs={"class": "form-control", "min": 2000, "max": 2100}
            ),
            "date_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "statut": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mandat"].queryset = Mandat.objects.filter(statut="ACTIF")





class SignUpForm(UserCreationForm):
    """Formulaire d'inscription personnalisé"""

    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": _("Entrez votre email")}
        ),
        help_text=_("Requis. Entrez une adresse email valide."),
    )

    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Prénom")}
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Nom")}
        ),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        )
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Nom d'utilisateur")}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Personnaliser les widgets des champs de mot de passe
        self.fields["password1"].widget = forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Mot de passe")}
        )
        self.fields["password2"].widget = forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Confirmer le mot de passe"),
            }
        )

        # Personnaliser les messages d'aide
        self.fields["username"].help_text = _(
            "Requis. 150 caractères ou moins. Lettres, chiffres et @/./+/-/_ uniquement."
        )
        self.fields["password1"].help_text = _(
            "Votre mot de passe doit contenir au moins 12 caractères."
        )

    def clean_email(self):
        """Vérifier que l'email n'existe pas déjà"""
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email

    def save(self, commit=True):
        """Sauvegarder l'utilisateur avec l'email"""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")

        if commit:
            user.save()
        return user