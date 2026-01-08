# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _
from .models import (
    Client, Mandat, Contact, Tache, Adresse, ExerciceComptable, User,
    TypeMandat, TypeFacturation, Periodicite, Role, AccesMandat, Invitation
)


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
            "type_mandat_ref",
            "date_debut",
            "date_fin",
            "periodicite_ref",
            "type_facturation_ref",
            "montant_forfait",
            "taux_horaire",
            "responsable",
            "description",
            "conditions_particulieres",
        ]
        widgets = {
            "client": forms.Select(attrs={"class": "form-control select2"}),
            "type_mandat_ref": forms.Select(attrs={"class": "form-control"}),
            "date_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "periodicite_ref": forms.Select(attrs={"class": "form-control"}),
            "type_facturation_ref": forms.Select(attrs={"class": "form-control"}),
            "montant_forfait": forms.NumberInput(attrs={"class": "form-control"}),
            "taux_horaire": forms.NumberInput(attrs={"class": "form-control"}),
            "responsable": forms.Select(attrs={"class": "form-control select2"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "conditions_particulieres": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limiter les choix aux éléments actifs
        self.fields['type_mandat_ref'].queryset = TypeMandat.objects.filter(is_active=True)
        self.fields['type_mandat_ref'].label = _('Type de mandat')
        self.fields['periodicite_ref'].queryset = Periodicite.objects.filter(is_active=True)
        self.fields['periodicite_ref'].label = _('Périodicité')
        self.fields['type_facturation_ref'].queryset = TypeFacturation.objects.filter(is_active=True)
        self.fields['type_facturation_ref'].label = _('Type de facturation')


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


# =============================================================================
# FORMULAIRES GESTION UTILISATEURS
# =============================================================================

class UserForm(forms.ModelForm):
    """Formulaire de création/modification d'un utilisateur"""

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'type_utilisateur',
            'phone',
            'mobile',
            'is_active',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'type_utilisateur': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Limiter les rôles assignables selon l'utilisateur courant
        if self.current_user:
            if self.current_user.is_superuser:
                self.fields['role'].queryset = Role.objects.filter(actif=True)
            elif self.current_user.role:
                # Ne peut assigner que des rôles de niveau inférieur
                self.fields['role'].queryset = Role.objects.filter(
                    actif=True,
                    niveau__lt=self.current_user.role.niveau
                )
            else:
                self.fields['role'].queryset = Role.objects.none()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email


class UserCreateForm(UserCreationForm):
    """Formulaire de création d'un utilisateur avec mot de passe"""

    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(actif=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Rôle')
    )
    type_utilisateur = forms.ChoiceField(
        choices=User.TypeUtilisateur.choices,
        initial=User.TypeUtilisateur.STAFF,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Type d\'utilisateur')
    )
    doit_changer_mot_de_passe = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Forcer le changement de mot de passe'),
        help_text=_('L\'utilisateur devra changer son mot de passe à la première connexion')
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'type_utilisateur',
            'phone',
            'mobile',
            'password1',
            'password2',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Personnaliser les widgets des mots de passe
        self.fields['password1'].widget = forms.PasswordInput(
            attrs={'class': 'form-control'}
        )
        self.fields['password2'].widget = forms.PasswordInput(
            attrs={'class': 'form-control'}
        )

        # Limiter les rôles selon l'utilisateur courant
        if self.current_user:
            if self.current_user.is_superuser:
                self.fields['role'].queryset = Role.objects.filter(actif=True)
            elif self.current_user.role:
                self.fields['role'].queryset = Role.objects.filter(
                    actif=True,
                    niveau__lt=self.current_user.role.niveau
                )
            else:
                self.fields['role'].queryset = Role.objects.none()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.type_utilisateur = self.cleaned_data.get('type_utilisateur', User.TypeUtilisateur.STAFF)
        user.doit_changer_mot_de_passe = self.cleaned_data.get('doit_changer_mot_de_passe', True)
        user.role = self.cleaned_data.get('role')

        if commit:
            user.save()
        return user


class ForcePasswordChangeForm(SetPasswordForm):
    """Formulaire pour forcer le changement de mot de passe"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget = forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': _('Nouveau mot de passe')}
        )
        self.fields['new_password2'].widget = forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': _('Confirmer le mot de passe')}
        )


# =============================================================================
# FORMULAIRES ROLES
# =============================================================================

class RoleForm(forms.ModelForm):
    """Formulaire de création/modification d'un rôle"""

    class Meta:
        model = Role
        fields = [
            'code',
            'nom',
            'description',
            'niveau',
            'permissions',
            'permissions_custom',
            'peut_etre_assigne',
            'est_role_defaut',
            'actif',
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: COMPTABLE'}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'niveau': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'permissions': forms.SelectMultiple(attrs={'class': 'form-control select2', 'size': 10}),
            'peut_etre_assigne': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'est_role_defaut': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Grouper les permissions par app
        self.fields['permissions'].queryset = Permission.objects.select_related(
            'content_type'
        ).order_by('content_type__app_label', 'codename')

        # Le champ permissions_custom est un JSONField - le cacher ou le traiter spécialement
        self.fields['permissions_custom'].widget = forms.HiddenInput()
        self.fields['permissions_custom'].required = False


# =============================================================================
# FORMULAIRES INVITATIONS
# =============================================================================

class InvitationStaffForm(forms.Form):
    """Formulaire pour inviter un collaborateur staff"""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
        label=_('Email')
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(actif=True, peut_etre_assigne=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Rôle'),
        help_text=_('Rôle attribué après acceptation')
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Message personnalisé (optionnel)')}),
        label=_('Message')
    )
    forcer_changement_mdp = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Forcer le changement de mot de passe')
    )

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Limiter les rôles selon l'utilisateur courant
        if self.current_user:
            if self.current_user.is_superuser:
                self.fields['role'].queryset = Role.objects.filter(
                    actif=True, peut_etre_assigne=True
                )
            elif self.current_user.role:
                self.fields['role'].queryset = Role.objects.filter(
                    actif=True,
                    peut_etre_assigne=True,
                    niveau__lt=self.current_user.role.niveau
                )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Un utilisateur avec cet email existe déjà."))
        if Invitation.objects.filter(email=email, statut=Invitation.Statut.EN_ATTENTE).exists():
            raise forms.ValidationError(_("Une invitation en attente existe déjà pour cet email."))
        return email


class InvitationClientForm(forms.Form):
    """Formulaire pour inviter un client externe"""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
        label=_('Email')
    )
    mandat = forms.ModelChoiceField(
        queryset=Mandat.objects.filter(statut='ACTIF'),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label=_('Mandat')
    )
    est_responsable = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Responsable du mandat'),
        help_text=_('Le responsable peut inviter d\'autres utilisateurs')
    )
    limite_invitations = forms.IntegerField(
        min_value=0,
        max_value=50,
        initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 100px'}),
        label=_('Limite d\'invitations'),
        help_text=_('Nombre d\'utilisateurs que ce responsable pourra inviter')
    )
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(
            content_type__app_label__in=['documents', 'comptabilite', 'facturation']
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label=_('Permissions sur le mandat')
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label=_('Message personnalisé')
    )
    forcer_changement_mdp = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Forcer le changement de mot de passe')
    )

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Limiter les mandats selon l'utilisateur
        if self.current_user:
            if self.current_user.is_client_user():
                # Client: uniquement les mandats où il est responsable
                self.fields['mandat'].queryset = Mandat.objects.filter(
                    acces_utilisateurs__utilisateur=self.current_user,
                    acces_utilisateurs__est_responsable=True,
                    acces_utilisateurs__is_active=True,
                    statut='ACTIF'
                )
                # Cacher les champs que le client ne peut pas modifier
                self.fields['est_responsable'].initial = False
                self.fields['est_responsable'].widget = forms.HiddenInput()
                self.fields['limite_invitations'].widget = forms.HiddenInput()
            elif not self.current_user.is_superuser:
                # Staff: mandats accessibles
                self.fields['mandat'].queryset = self.current_user.get_accessible_mandats()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        mandat = cleaned_data.get('mandat')

        if email and mandat:
            if Invitation.objects.filter(
                email=email,
                mandat=mandat,
                statut=Invitation.Statut.EN_ATTENTE
            ).exists():
                raise forms.ValidationError(
                    _("Une invitation en attente existe déjà pour cet email sur ce mandat.")
                )

        return cleaned_data


class AcceptInvitationForm(forms.Form):
    """Formulaire d'acceptation d'une invitation"""

    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Prénom')}),
        label=_('Prénom')
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nom')}),
        label=_('Nom')
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Téléphone')}),
        label=_('Téléphone')
    )
    password = forms.CharField(
        min_length=12,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Mot de passe (min. 12 caractères)')}),
        label=_('Mot de passe'),
        help_text=_('Minimum 12 caractères')
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Confirmer le mot de passe')}),
        label=_('Confirmation')
    )
    accept_terms = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('J\'accepte les conditions d\'utilisation')
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError(_("Les mots de passe ne correspondent pas."))

        return cleaned_data


# =============================================================================
# FORMULAIRES ACCES MANDAT
# =============================================================================

class AccesMandatForm(forms.ModelForm):
    """Formulaire pour gérer l'accès d'un utilisateur à un mandat"""

    class Meta:
        model = AccesMandat
        fields = [
            'utilisateur',
            'mandat',
            'est_responsable',
            'permissions',
            'limite_invitations',
            'date_debut_acces',
            'date_fin_acces',
            'is_active',
            'notes',
        ]
        widgets = {
            'utilisateur': forms.Select(attrs={'class': 'form-control select2'}),
            'mandat': forms.Select(attrs={'class': 'form-control select2'}),
            'est_responsable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'permissions': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'limite_invitations': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 50}),
            'date_debut_acces': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin_acces': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limiter aux utilisateurs CLIENT
        self.fields['utilisateur'].queryset = User.objects.filter(
            type_utilisateur=User.TypeUtilisateur.CLIENT,
            is_active=True
        )

        # Limiter les permissions aux apps pertinentes
        self.fields['permissions'].queryset = Permission.objects.filter(
            content_type__app_label__in=['documents', 'comptabilite', 'facturation', 'tva']
        ).select_related('content_type').order_by('content_type__app_label', 'codename')

        # Mandats actifs uniquement
        self.fields['mandat'].queryset = Mandat.objects.filter(statut='ACTIF')