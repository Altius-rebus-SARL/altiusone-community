# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory
from .models import (
    Client, Entreprise, Mandat, Contact, Tache, Adresse, ExerciceComptable, User,
    TypeMandat, TypeFacturation, Periodicite, Role, AccesMandat, Invitation,
    CollaborateurFiduciaire, TypeCollaborateur, CompteBancaire
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


class EntrepriseForm(forms.ModelForm):
    """Formulaire de création/modification d'une entreprise"""

    class Meta:
        model = Entreprise
        fields = [
            "raison_sociale",
            "nom_commercial",
            "forme_juridique",
            "ide_number",
            "ch_id",
            "ofrc_id",
            "tva_number",
            "siege",
            "canton_rc",
            "email",
            "telephone",
            "site_web",
            "but",
            "date_creation",
            "date_inscription_rc",
            "statut",
            "logo",
            "est_defaut",
        ]
        widgets = {
            "raison_sociale": forms.TextInput(attrs={"class": "form-control"}),
            "nom_commercial": forms.TextInput(attrs={"class": "form-control"}),
            "forme_juridique": forms.Select(attrs={"class": "form-control"}),
            "ide_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "CHE-XXX.XXX.XXX"}
            ),
            "ch_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "CH-XXX-XXXXXXX-X"}
            ),
            "ofrc_id": forms.TextInput(attrs={"class": "form-control"}),
            "tva_number": forms.TextInput(attrs={"class": "form-control"}),
            "siege": forms.TextInput(attrs={"class": "form-control"}),
            "canton_rc": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "site_web": forms.URLInput(attrs={"class": "form-control"}),
            "but": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "date_creation": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_inscription_rc": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "statut": forms.Select(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "est_defaut": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CompteBancaireForm(forms.ModelForm):
    """Formulaire pour un compte bancaire d'entreprise"""

    # Override le champ IBAN pour accepter les espaces en saisie (max 42 chars avec espaces)
    iban = forms.CharField(
        max_length=42,
        label=_('IBAN'),
        help_text=_('International Bank Account Number'),
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "CH93 0076 2011 6238 5295 7"}),
    )

    class Meta:
        model = CompteBancaire
        fields = [
            "libelle",
            "type_compte",
            "iban",
            "bic_swift",
            "nom_banque",
            "adresse_banque",
            "clearing",
            "titulaire_nom",
            "devise",
            "est_compte_principal",
            "est_qr_iban",
            "qr_reference_type",
            "actif",
            "notes",
        ]
        widgets = {
            "libelle": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Ex: Compte principal, Compte salaires")}),
            "type_compte": forms.Select(attrs={"class": "form-control"}),
            "bic_swift": forms.TextInput(attrs={"class": "form-control", "placeholder": "POFICHBEXXX"}),
            "nom_banque": forms.TextInput(attrs={"class": "form-control"}),
            "adresse_banque": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "clearing": forms.TextInput(attrs={"class": "form-control"}),
            "titulaire_nom": forms.TextInput(attrs={"class": "form-control"}),
            "devise": forms.Select(attrs={"class": "form-control"}),
            "est_compte_principal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "est_qr_iban": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "qr_reference_type": forms.Select(attrs={"class": "form-control"}),
            "actif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def clean_iban(self):
        """Nettoie l'IBAN : supprime les espaces, met en majuscules, valide le format."""
        import re
        iban = self.cleaned_data.get('iban', '')
        iban = iban.replace(' ', '').upper()
        if iban and not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$', iban):
            raise forms.ValidationError(_('Format IBAN invalide. Ex: CH93 0076 2011 6238 5295 7'))
        return iban


CompteBancaireFormSet = inlineformset_factory(
    Entreprise,
    CompteBancaire,
    form=CompteBancaireForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


class ContactPrincipalForm(forms.ModelForm):
    """Formulaire simplifié pour le contact principal lors de la création d'un client"""

    class Meta:
        model = Contact
        fields = ["civilite", "nom", "prenom", "fonction", "email", "telephone"]
        widgets = {
            "civilite": forms.Select(attrs={"class": "form-control"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "prenom": forms.TextInput(attrs={"class": "form-control"}),
            "fonction": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Seuls nom et prénom sont obligatoires dans ce contexte
        self.fields['civilite'].required = False
        self.fields['fonction'].required = False
        self.fields['email'].required = False
        self.fields['telephone'].required = False
        # Choix vide par défaut
        self.fields['civilite'].choices = [('', '---------')] + list(self.fields['civilite'].choices)
        self.fields['fonction'].choices = [('', '---------')] + list(self.fields['fonction'].choices)


class ClientForm(forms.ModelForm):
    """Formulaire de création/modification d'un client"""

    class Meta:
        model = Client
        fields = [
            "raison_sociale",
            "nom_commercial",
            "forme_juridique",
            "entreprise",
            "ide_number",
            "ch_id",
            "ofrc_id",
            "tva_number",
            "email",
            "telephone",
            "site_web",
            "logo",
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
            "entreprise": forms.Select(attrs={"class": "form-control"}),
            "ide_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "CHE-XXX.XXX.XXX"}
            ),
            "ch_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "CH-XXX-XXXXXXX-X"}
            ),
            "ofrc_id": forms.TextInput(attrs={"class": "form-control"}),
            "tva_number": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "site_web": forms.URLInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
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

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        self.fields['entreprise'].queryset = Entreprise.objects.filter(statut='ACTIVE')
        default = Entreprise.get_default()
        if default and self.instance._state.adding:
            self.fields['entreprise'].initial = default.pk
        # IDE optionnel (clients sans registre du commerce, personnes physiques, etc.)
        self.fields['ide_number'].required = False
        # Date de création optionnelle (pas toujours connue)
        self.fields['date_creation'].required = False
        # Responsable : collaborateurs internes uniquement, optionnel, pré-rempli
        self.fields['responsable'].queryset = User.objects.filter(
            is_active=True, type_utilisateur='STAFF'
        ).order_by('first_name', 'last_name')
        self.fields['responsable'].required = False
        if self.current_user and self.instance._state.adding:
            self.fields['responsable'].initial = self.current_user.pk


class MandatForm(forms.ModelForm):
    """Formulaire pour un mandat"""

    PLAN_COMPTABLE_CHOICES = [
        ('', '---------'),
        ('PME', _('PME')),
        ('GRAND', _('Grand plan comptable')),
    ]

    METHODE_TVA_CHOICES = [
        ('', '---------'),
        ('EFFECTIVE', _('Effective')),
        ('FORFAIT', _('Forfait')),
        ('TDFN', _('Taux de la dette fiscale nette')),
    ]

    PERIODICITE_TVA_CHOICES = [
        ('', '---------'),
        ('MENSUEL', _('Mensuel')),
        ('TRIMESTRIEL', _('Trimestriel')),
        ('SEMESTRIEL', _('Semestriel')),
        ('ANNUEL', _('Annuel')),
    ]

    CLOTURE_MOIS_CHOICES = [('', '---------')] + [
        (i, _(m)) for i, m in [
            (1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
            (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
            (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre'),
        ]
    ]

    MODULES_CHOICES = [
        ('compta', _('Comptabilité')),
        ('tva', _('TVA')),
        ('salaires', _('Salaires')),
        ('revision', _('Révision')),
    ]

    # Champs de configuration comptable (extraits du JSONField)
    plan_comptable = forms.ChoiceField(
        choices=PLAN_COMPTABLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        label=_('Plan comptable'),
    )
    methode_tva = forms.ChoiceField(
        choices=METHODE_TVA_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        label=_('Méthode TVA'),
    )
    periodicite_tva = forms.ChoiceField(
        choices=PERIODICITE_TVA_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        label=_('Périodicité TVA'),
    )
    cloture_mois = forms.TypedChoiceField(
        choices=CLOTURE_MOIS_CHOICES,
        coerce=int,
        empty_value='',
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        label=_('Mois de clôture'),
    )
    modules_actifs = forms.MultipleChoiceField(
        choices=MODULES_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label=_('Modules actifs'),
    )

    class Meta:
        model = Mandat
        fields = [
            "client",
            "type_mandat_ref",
            "regime_fiscal",
            "devise",
            "statut",
            "date_debut",
            "date_fin",
            "periodicite_ref",
            "type_facturation_ref",
            "budget_prevu",
            "taux_horaire",
            "responsable",
            "equipe",
            "description",
            "conditions_particulieres",
        ]
        widgets = {
            "client": forms.Select(attrs={"class": "form-control select2"}),
            "type_mandat_ref": forms.Select(attrs={"class": "form-control"}),
            "regime_fiscal": forms.Select(attrs={"class": "form-control"}),
            "devise": forms.Select(attrs={"class": "form-control"}),
            "statut": forms.Select(attrs={"class": "form-control"}),
            "date_debut": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "periodicite_ref": forms.Select(attrs={"class": "form-control"}),
            "type_facturation_ref": forms.Select(attrs={"class": "form-control"}),
            "budget_prevu": forms.NumberInput(attrs={"class": "form-control"}),
            "taux_horaire": forms.NumberInput(attrs={"class": "form-control"}),
            "responsable": forms.Select(attrs={"class": "form-control select2"}),
            "equipe": forms.SelectMultiple(attrs={"class": "form-control select2"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "conditions_particulieres": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        # Limiter les choix aux éléments actifs
        self.fields['type_mandat_ref'].queryset = TypeMandat.objects.filter(is_active=True)
        self.fields['type_mandat_ref'].label = _('Type de mandat')
        self.fields['periodicite_ref'].queryset = Periodicite.objects.filter(is_active=True)
        self.fields['periodicite_ref'].label = _('Périodicité')
        self.fields['type_facturation_ref'].queryset = TypeFacturation.objects.filter(is_active=True)
        self.fields['type_facturation_ref'].label = _('Type de facturation')
        # Responsable et équipe : collaborateurs internes uniquement
        staff_qs = User.objects.filter(
            is_active=True, type_utilisateur=User.TypeUtilisateur.STAFF
        ).order_by('first_name', 'last_name')
        self.fields['responsable'].queryset = staff_qs
        self.fields['equipe'].queryset = staff_qs
        # Pré-remplir le responsable avec l'utilisateur connecté (création)
        if self.current_user and self.instance._state.adding:
            self.fields['responsable'].initial = self.current_user.pk

        # Pré-remplir les champs de configuration depuis le JSONField
        if self.instance and self.instance.pk:
            config = self.instance.configuration or {}
            self.fields['plan_comptable'].initial = config.get('plan_comptable', '')
            self.fields['methode_tva'].initial = config.get('methode_tva', '')
            self.fields['periodicite_tva'].initial = config.get('periodicite_tva', '')
            self.fields['cloture_mois'].initial = config.get('cloture_mois', '')
            self.fields['modules_actifs'].initial = config.get('modules_actifs', [])

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Sérialiser les champs de configuration dans le JSONField
        config = instance.configuration or {}
        for key in ('plan_comptable', 'methode_tva', 'periodicite_tva'):
            val = self.cleaned_data.get(key)
            if val:
                config[key] = val
            else:
                config.pop(key, None)

        cloture = self.cleaned_data.get('cloture_mois')
        if cloture != '' and cloture is not None:
            config['cloture_mois'] = int(cloture)
        else:
            config.pop('cloture_mois', None)

        modules = self.cleaned_data.get('modules_actifs')
        if modules:
            config['modules_actifs'] = modules
        else:
            config.pop('modules_actifs', None)

        instance.configuration = config

        if commit:
            instance.save()
            self.save_m2m()
        return instance


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
            "assignes",
            "mandat",
            "prestation",
            "priorite",
            "date_echeance",
            "temps_estime_heures",
            "tags",
        ]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "assignes": forms.SelectMultiple(attrs={"class": "form-control select2", "multiple": "multiple"}),
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "prestation": forms.Select(attrs={"class": "form-control select2"}),
            "priorite": forms.Select(attrs={"class": "form-control"}),
            "date_echeance": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "temps_estime_heures": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        mandat_id = kwargs.pop('mandat_id', None)
        super().__init__(*args, **kwargs)

        from facturation.models import Prestation

        # Build assignes queryset: active staff + (if mandat) external users
        users_qs = User.objects.filter(is_active=True, type_utilisateur='STAFF')

        if mandat_id:
            from core.models import AccesMandat, CollaborateurFiduciaire
            acces_users = AccesMandat.objects.filter(
                mandat_id=mandat_id, is_active=True
            ).values_list('utilisateur_id', flat=True)
            collab_users = CollaborateurFiduciaire.objects.filter(
                mandat_id=mandat_id, is_active=True
            ).values_list('utilisateur_id', flat=True)
            external_ids = set(acces_users) | set(collab_users)
            if external_ids:
                users_qs = User.objects.filter(
                    Q(is_active=True, type_utilisateur='STAFF') | Q(pk__in=external_ids)
                ).distinct()

        self.fields['assignes'].queryset = users_qs
        self.fields['prestation'].queryset = Prestation.objects.filter(actif=True)
        self.fields['prestation'].required = False




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
# FORMULAIRE PROFIL UTILISATEUR
# =============================================================================


class ProfileForm(forms.ModelForm):
    """Formulaire de modification du profil par l'utilisateur lui-même."""

    supprimer_avatar = forms.BooleanField(required=False, label=_("Supprimer la photo"))

    class Meta:
        model = User
        fields = [
            'avatar',
            'first_name',
            'last_name',
            'email',
            'phone',
            'mobile',
        ]
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('supprimer_avatar'):
            user.avatar = None
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
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
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


class InvitationCodeForm(forms.Form):
    """Formulaire pour saisir un code d'invitation court"""

    code = forms.CharField(
        max_length=8,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': 'AB3K7X',
            'style': 'letter-spacing: 0.3em; font-weight: bold; text-transform: uppercase;',
            'autocomplete': 'off',
            'maxlength': '8',
        }),
        label=_('Code d\'invitation'),
        help_text=_('Saisissez le code à 6 caractères reçu de votre contact')
    )

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code.isalnum():
            raise forms.ValidationError(_("Le code ne doit contenir que des lettres et chiffres."))
        return code


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
            'permissions': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
            'limite_invitations': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 50}),
            'date_debut_acces': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin_acces': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Tous les utilisateurs actifs (pas seulement CLIENT)
        self.fields['utilisateur'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name')
        self.fields['utilisateur'].label_from_instance = lambda u: (
            f"{u.get_full_name() or u.username} ({u.get_type_utilisateur_display()})"
        )

        # Limiter les permissions aux apps pertinentes
        self.fields['permissions'].queryset = Permission.objects.filter(
            content_type__app_label__in=['documents', 'comptabilite', 'facturation', 'tva']
        ).select_related('content_type').order_by('content_type__app_label', 'codename')

        # Mandats actifs uniquement
        self.fields['mandat'].queryset = Mandat.objects.filter(statut='ACTIF')


class CollaborateurFiduciaireForm(forms.ModelForm):
    """Formulaire pour gérer l'affectation d'un prestataire à un mandat"""

    class Meta:
        model = CollaborateurFiduciaire
        fields = [
            'utilisateur',
            'mandat',
            'role_sur_mandat',
            'date_debut',
            'date_fin',
            'taux_horaire',
            'is_active',
            'notes',
        ]
        widgets = {
            'utilisateur': forms.Select(attrs={'class': 'form-control select2'}),
            'mandat': forms.Select(attrs={'class': 'form-control select2'}),
            'role_sur_mandat': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Ex: Comptable externe, Réviseur, Conseiller fiscal')
            }),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'taux_horaire': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': _('CHF/heure')
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limiter aux utilisateurs STAFF + PRESTATAIRE
        self.fields['utilisateur'].queryset = User.objects.filter(
            type_utilisateur=User.TypeUtilisateur.STAFF,
            type_collaborateur=TypeCollaborateur.PRESTATAIRE,
            is_active=True
        )

        # Mandats actifs uniquement
        self.fields['mandat'].queryset = Mandat.objects.filter(statut='ACTIF')