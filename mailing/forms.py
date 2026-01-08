# mailing/forms.py
"""
Formulaires pour le module mailing.
"""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ConfigurationEmail, TemplateEmail


class ConfigurationEmailForm(forms.ModelForm):
    """Formulaire pour les configurations email"""

    # Types de sécurité pour SMTP
    SMTP_SECURITY_CHOICES = [
        ('NONE', _('Aucune')),
        ('TLS', _('STARTTLS')),
        ('SSL', _('SSL/TLS')),
    ]

    # Types de sécurité pour IMAP
    IMAP_SECURITY_CHOICES = [
        ('NONE', _('Aucune')),
        ('SSL', _('SSL/TLS')),
    ]

    # Champ mot de passe séparé (pour ne pas afficher le mot de passe existant)
    password_new = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Laisser vide pour ne pas modifier'),
            'autocomplete': 'new-password'
        }),
        label=_('Mot de passe'),
        help_text=_('Mot de passe ou mot de passe d\'application')
    )

    # Champs de sécurité simplifiés
    smtp_security = forms.ChoiceField(
        choices=SMTP_SECURITY_CHOICES,
        initial='TLS',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Sécurité SMTP'),
        required=False
    )

    imap_security = forms.ChoiceField(
        choices=IMAP_SECURITY_CHOICES,
        initial='SSL',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Sécurité IMAP'),
        required=False
    )

    class Meta:
        model = ConfigurationEmail
        fields = [
            'nom',
            'usage',
            'email_address',
            'from_name',
            'reply_to',
            'username',
            # SMTP
            'smtp_host',
            'smtp_port',
            # IMAP
            'imap_host',
            'imap_port',
            'imap_dossier',
            # Options
            'analyse_ai_activee',
            'extraire_pieces_jointes',
            'est_defaut',
            'actif',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Ex: Email Principal')}),
            'usage': forms.Select(attrs={'class': 'form-select'}),
            'email_address': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('votre@email.com')}),
            'from_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Ex: AltiusOne Support')}),
            'reply_to': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('reponse@email.com')}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Identique à l\'email si vide')}),
            # SMTP - pas de valeur par défaut pour le port
            'smtp_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('smtp.votreserveur.com')}),
            'smtp_port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('587, 465, 25...')}),
            # IMAP
            'imap_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('imap.votreserveur.com')}),
            'imap_port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('993, 143...')}),
            'imap_dossier': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'INBOX'}),
            # Options
            'analyse_ai_activee': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extraire_pieces_jointes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'est_defaut': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Rendre les ports non requis (on ne veut pas de valeur par défaut)
        self.fields['smtp_port'].required = False
        self.fields['imap_port'].required = False

        # Si édition, charger les valeurs de sécurité existantes
        if self.instance and self.instance.pk:
            self.fields['password_new'].help_text = _('Mot de passe actuel enregistré. Laisser vide pour ne pas modifier.')

            # Déterminer le type de sécurité SMTP
            if self.instance.smtp_use_ssl:
                self.initial['smtp_security'] = 'SSL'
            elif self.instance.smtp_use_tls:
                self.initial['smtp_security'] = 'TLS'
            else:
                self.initial['smtp_security'] = 'NONE'

            # Déterminer le type de sécurité IMAP
            if self.instance.imap_use_ssl:
                self.initial['imap_security'] = 'SSL'
            else:
                self.initial['imap_security'] = 'NONE'

    def clean(self):
        cleaned_data = super().clean()

        smtp_host = cleaned_data.get('smtp_host')
        imap_host = cleaned_data.get('imap_host')

        # Au moins un serveur doit être configuré
        if not smtp_host and not imap_host:
            raise forms.ValidationError(
                _('Vous devez configurer au moins un serveur (SMTP ou IMAP).')
            )

        # Si SMTP configuré, le port est requis
        if smtp_host and not cleaned_data.get('smtp_port'):
            self.add_error('smtp_port', _('Le port SMTP est requis.'))

        # Si IMAP configuré, le port est requis
        if imap_host and not cleaned_data.get('imap_port'):
            self.add_error('imap_port', _('Le port IMAP est requis.'))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Mettre à jour le mot de passe uniquement s'il est fourni
        password_new = self.cleaned_data.get('password_new')
        if password_new:
            instance.password = password_new

        # Convertir les choix de sécurité en champs booléens
        smtp_security = self.cleaned_data.get('smtp_security', 'TLS')
        instance.smtp_use_tls = (smtp_security == 'TLS')
        instance.smtp_use_ssl = (smtp_security == 'SSL')

        imap_security = self.cleaned_data.get('imap_security', 'SSL')
        instance.imap_use_ssl = (imap_security == 'SSL')

        # Déterminer le type de configuration automatiquement
        has_smtp = bool(self.cleaned_data.get('smtp_host'))
        has_imap = bool(self.cleaned_data.get('imap_host'))

        if has_smtp and not has_imap:
            instance.type_config = 'SMTP'
        elif has_imap and not has_smtp:
            instance.type_config = 'IMAP'
        else:
            instance.type_config = 'SMTP'  # Par défaut si les deux

        if commit:
            instance.save()
        return instance


class TemplateEmailForm(forms.ModelForm):
    """Formulaire pour les templates email"""

    class Meta:
        model = TemplateEmail
        fields = [
            'code',
            'nom',
            'type_template',
            'configuration',
            'sujet',
            'corps_html',
            'corps_texte',
            'variables_disponibles',
            'actif',
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Ex: INVITATION_STAFF')}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'type_template': forms.Select(attrs={'class': 'form-select'}),
            'configuration': forms.Select(attrs={'class': 'form-select'}),
            'sujet': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Ex: Invitation à rejoindre {{nom_entreprise}}')}),
            'corps_html': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
            'corps_texte': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limiter aux configurations SMTP actives
        self.fields['configuration'].queryset = ConfigurationEmail.objects.filter(
            actif=True
        ).exclude(smtp_host='')
        self.fields['configuration'].required = False

        # Le champ variables_disponibles est un JSONField
        self.fields['variables_disponibles'].widget = forms.HiddenInput()
        self.fields['variables_disponibles'].required = False


class ComposeEmailForm(forms.Form):
    """Formulaire pour composer un email - Django 6 moderne"""

    destinataire = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('destinataire@email.com')
        }),
        label=_('Destinataire')
    )
    cc = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('email1@ex.com, email2@ex.com')
        }),
        label=_('CC'),
        help_text=_('Séparez les adresses par des virgules')
    )
    sujet = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Sujet du message')
        }),
        label=_('Sujet')
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': _('Votre message...')
        }),
        label=_('Message')
    )
    configuration = forms.ModelChoiceField(
        queryset=ConfigurationEmail.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Envoyer depuis'),
        help_text=_('Configuration email à utiliser')
    )
    # Champ fichier simple - les fichiers multiples sont gérés côté vue avec request.FILES.getlist()
    pieces_jointes = forms.FileField(
        required=False,
        label=_('Pièces jointes')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Définir le queryset dynamiquement pour éviter les problèmes de chargement
        self.fields['configuration'].queryset = ConfigurationEmail.objects.filter(
            actif=True
        ).exclude(smtp_host='')

    def clean_cc(self):
        """Valide et nettoie les adresses CC"""
        cc = self.cleaned_data.get('cc', '')
        if not cc:
            return []

        emails = [e.strip() for e in cc.split(',') if e.strip()]
        for email in emails:
            try:
                forms.EmailField().clean(email)
            except forms.ValidationError:
                raise forms.ValidationError(
                    _('Adresse email invalide: %(email)s'),
                    params={'email': email}
                )
        return emails
