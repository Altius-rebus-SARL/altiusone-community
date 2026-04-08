# comptabilite/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.forms import inlineformset_factory
from decimal import Decimal
from .models import (
    PlanComptable,
    Compte,
    Journal,
    EcritureComptable,
    PieceComptable,
    Lettrage,
    TypePieceComptable,
    AxeAnalytique,
    SectionAnalytique,
    Immobilisation,
)
from core.models import Mandat, ExerciceComptable, ParametreMetier


class PlanComptableForm(forms.ModelForm):
    """Formulaire pour un plan comptable"""

    class Meta:
        model = PlanComptable
        fields = [
            "nom_fr",
            "nom_de",
            "nom_it",
            "nom_en",
            "type_plan",
            "description_fr",
            "description_de",
            "description_it",
            "description_en",
            "is_template",
            "mandat",
            "devise",
            "base_sur",
            "is_active",
        ]
        widgets = {
            "nom_fr": forms.TextInput(attrs={"class": "form-control"}),
            "nom_de": forms.TextInput(attrs={"class": "form-control"}),
            "nom_it": forms.TextInput(attrs={"class": "form-control"}),
            "nom_en": forms.TextInput(attrs={"class": "form-control"}),
            "type_plan": forms.Select(attrs={"class": "form-control select-basic"}),
            "description_fr": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "description_de": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "description_it": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "description_en": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "is_template": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "devise": forms.Select(attrs={"class": "form-control select2"}),
            "base_sur": forms.Select(attrs={"class": "form-control select2"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si c'est un template, pas de mandat
        if self.instance and self.instance.is_template:
            self.fields["mandat"].required = False

        # Limiter les plans de base aux templates
        self.fields["base_sur"].queryset = PlanComptable.objects.filter(
            is_template=True
        )


class CompteForm(forms.ModelForm):
    """Formulaire pour un compte"""

    class Meta:
        model = Compte
        fields = [
            "plan_comptable",
            "numero",
            "libelle_fr",
            "libelle_de",
            "libelle_it",
            "libelle_en",
            "libelle_court_fr",
            "libelle_court_de",
            "libelle_court_it",
            "libelle_court_en",
            "type_compte",
            "classe",
            "niveau",
            "compte_parent",
            "est_collectif",
            "imputable",
            "lettrable",
            "obligatoire_tiers",
            "soumis_tva",
            "code_tva_defaut",
            "code_tva_defaut_ref",
        ]
        widgets = {
            "plan_comptable": forms.Select(attrs={"class": "form-control select2"}),
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "libelle_fr": forms.TextInput(attrs={"class": "form-control"}),
            "libelle_de": forms.TextInput(attrs={"class": "form-control"}),
            "libelle_it": forms.TextInput(attrs={"class": "form-control"}),
            "libelle_en": forms.TextInput(attrs={"class": "form-control"}),
            "libelle_court_fr": forms.TextInput(attrs={"class": "form-control"}),
            "libelle_court_de": forms.TextInput(attrs={"class": "form-control"}),
            "libelle_court_it": forms.TextInput(attrs={"class": "form-control"}),
            "libelle_court_en": forms.TextInput(attrs={"class": "form-control"}),
            "type_compte": forms.Select(attrs={"class": "form-control select-basic"}),
            "classe": forms.Select(attrs={"class": "form-control select-basic"}),
            "niveau": forms.NumberInput(attrs={"class": "form-control"}),
            "compte_parent": forms.Select(attrs={"class": "form-control select2"}),
            "est_collectif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "imputable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "lettrable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "obligatoire_tiers": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "soumis_tva": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "code_tva_defaut": forms.TextInput(attrs={"class": "form-control"}),
            "code_tva_defaut_ref": forms.Select(attrs={"class": "form-control select2"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limiter les comptes parents au même plan
        if self.instance and self.instance.plan_comptable_id:
            self.fields["compte_parent"].queryset = Compte.objects.filter(
                plan_comptable=self.instance.plan_comptable
            ).exclude(pk=self.instance.pk)

    def clean(self):
        cleaned_data = super().clean()
        # Validation du numéro de compte selon la classe
        numero = cleaned_data.get("numero")
        classe = cleaned_data.get("classe")

        if numero and classe:
            if not numero.startswith(str(classe)):
                raise forms.ValidationError(
                    _("Le numéro de compte doit commencer par le chiffre de la classe")
                )

        # Un compte collectif ne peut pas être imputable
        if cleaned_data.get("est_collectif") and cleaned_data.get("imputable"):
            raise forms.ValidationError(
                _("Un compte collectif ne peut pas être imputable")
            )

        return cleaned_data


class JournalForm(forms.ModelForm):
    """Formulaire pour un journal"""

    class Meta:
        model = Journal
        fields = [
            "mandat",
            "code",
            "libelle",
            "type_journal",
            "compte_contrepartie_defaut",
            "devise",
            "numerotation_auto",
            "prefixe_piece",
            "dernier_numero",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "devise": forms.Select(attrs={"class": "form-control select2"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "libelle": forms.TextInput(attrs={"class": "form-control"}),
            "type_journal": forms.Select(attrs={"class": "form-control select-basic"}),
            "compte_contrepartie_defaut": forms.Select(
                attrs={"class": "form-control select2"}
            ),
            "numerotation_auto": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "prefixe_piece": forms.TextInput(attrs={"class": "form-control"}),
            "dernier_numero": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Charger les types de journal depuis ParametreMetier
        self.fields['type_journal'].choices = ParametreMetier.get_choices_with_default(
            'comptabilite', 'type_journal', Journal.TYPE_CHOICES
        )
        # Limiter les comptes au plan du mandat
        if self.instance and self.instance.mandat:
            plan = self.instance.mandat.plan_comptable
            if plan:
                self.fields[
                    "compte_contrepartie_defaut"
                ].queryset = Compte.objects.filter(plan_comptable=plan)


class EcritureComptableForm(forms.ModelForm):
    """Formulaire pour une écriture comptable"""

    class Meta:
        model = EcritureComptable
        fields = [
            "mandat",
            "exercice",
            "journal",
            "numero_piece",
            "numero_ligne",
            "date_ecriture",
            "date_valeur",
            "date_echeance",
            "compte",
            "compte_auxiliaire",
            "libelle",
            "libelle_complement",
            "montant_debit",
            "montant_credit",
            "devise",
            "taux_change",
            "code_tva",
            "montant_tva",
            "piece_justificative",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "exercice": forms.Select(attrs={"class": "form-control select2"}),
            "journal": forms.Select(attrs={"class": "form-control select2"}),
            "numero_piece": forms.TextInput(attrs={"class": "form-control"}),
            "numero_ligne": forms.NumberInput(attrs={"class": "form-control"}),
            "date_ecriture": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_valeur": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_echeance": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "compte": forms.Select(attrs={"class": "form-control select2"}),
            "compte_auxiliaire": forms.TextInput(attrs={"class": "form-control"}),
            "libelle": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "libelle_complement": forms.TextInput(attrs={"class": "form-control"}),
            "montant_debit": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "montant_credit": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "devise": forms.Select(attrs={"class": "form-control"}),
            "taux_change": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.000001"}
            ),
            "code_tva": forms.TextInput(attrs={"class": "form-control"}),
            "montant_tva": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "piece_justificative": forms.Select(
                attrs={"class": "form-control select2"}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.mandat_obj = kwargs.pop('mandat', None)
        super().__init__(*args, **kwargs)

        # Champs numériques avec default sur le modèle : accepter vide
        for field_name in ('montant_debit', 'montant_credit', 'taux_change', 'montant_tva'):
            if field_name in self.fields:
                self.fields[field_name].required = False

        # Devise: auto-remplie depuis le mandat, pas besoin de la montrer
        self.fields['devise'].required = False
        self.fields['devise'].widget = forms.HiddenInput()

        # Déterminer le mandat (édition ou création)
        mandat = None
        if not self.instance._state.adding and self.instance.mandat_id:
            mandat = self.instance.mandat
        elif self.mandat_obj:
            mandat = self.mandat_obj

        if mandat:
            try:
                # Exercices du mandat
                self.fields["exercice"].queryset = ExerciceComptable.objects.filter(
                    mandat=mandat
                )

                # Journaux du mandat
                self.fields["journal"].queryset = Journal.objects.filter(mandat=mandat)

                # Comptes du plan
                plan = mandat.plan_comptable
                if plan:
                    self.fields["compte"].queryset = Compte.objects.filter(
                        plan_comptable=plan, imputable=True
                    ).order_by("numero")

                # Documents du mandat
                from documents.models import Document
                self.fields["piece_justificative"].queryset = Document.objects.filter(
                    mandat=mandat
                )

                # Pré-remplir devise et exercice en création
                if self.instance._state.adding:
                    if hasattr(mandat, 'devise_id') and mandat.devise_id:
                        self.initial["devise"] = mandat.devise_id
                    exercice_ouvert = mandat.exercices.filter(statut="OUVERT").first()
                    if exercice_ouvert:
                        self.initial["exercice"] = exercice_ouvert.pk
            except Exception:
                pass

    def clean_montant_debit(self):
        val = self.cleaned_data.get('montant_debit')
        return val if val is not None else Decimal('0')

    def clean_montant_credit(self):
        val = self.cleaned_data.get('montant_credit')
        return val if val is not None else Decimal('0')

    def clean_taux_change(self):
        val = self.cleaned_data.get('taux_change')
        return val if val is not None else Decimal('1')

    def clean_montant_tva(self):
        val = self.cleaned_data.get('montant_tva')
        return val if val is not None else Decimal('0')

    def clean(self):
        cleaned_data = super().clean()

        # Auto-remplir devise depuis le mandat si non fournie
        if not cleaned_data.get('devise'):
            mandat = cleaned_data.get('mandat')
            if mandat and hasattr(mandat, 'devise') and mandat.devise:
                cleaned_data['devise'] = mandat.devise
            else:
                from core.models import Devise
                cleaned_data['devise'] = Devise.get_devise_base()

        # Validation: soit débit, soit crédit (pas les deux)
        debit = cleaned_data.get("montant_debit", Decimal("0"))
        credit = cleaned_data.get("montant_credit", Decimal("0"))

        if debit > 0 and credit > 0:
            raise forms.ValidationError(
                _("Une écriture ne peut pas avoir un montant au débit ET au crédit")
            )

        if debit == 0 and credit == 0:
            raise forms.ValidationError(
                _("Une écriture doit avoir un montant (débit ou crédit)")
            )

        # Vérifier que la date est dans l'exercice
        date_ecriture = cleaned_data.get("date_ecriture")
        exercice = cleaned_data.get("exercice")

        if date_ecriture and exercice:
            if not (exercice.date_debut <= date_ecriture <= exercice.date_fin):
                raise forms.ValidationError(
                    _(
                        "La date de l'écriture doit être comprise dans l'exercice comptable"
                    )
                )

        # Validation compte auxiliaire si obligatoire
        compte = cleaned_data.get("compte")
        compte_auxiliaire = cleaned_data.get("compte_auxiliaire")

        if compte and compte.obligatoire_tiers and not compte_auxiliaire:
            raise forms.ValidationError(
                _("Un compte auxiliaire est obligatoire pour ce compte")
            )

        return cleaned_data


class MultipleFileInput(forms.FileInput):
    """Widget pour upload de fichiers multiples"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Champ pour upload de fichiers multiples"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png,.tiff,.gif'
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class PieceComptableForm(forms.ModelForm):
    """Formulaire enrichi pour une pièce comptable avec upload de documents"""

    # Champ pour upload de fichiers multiples
    fichiers = MultipleFileField(
        required=False,
        label=_("Documents justificatifs"),
        help_text=_("Uploadez les factures, reçus ou autres justificatifs (PDF, images)")
    )

    # Checkbox pour générer le numéro automatiquement
    generer_numero = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Générer le numéro automatiquement"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = PieceComptable
        fields = [
            "mandat", "journal", "type_piece", "numero_piece", "date_piece",
            "libelle", "reference_externe", "tiers_nom", "tiers_numero_tva",
            "montant_ht", "montant_tva", "montant_ttc", "dossier"
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2", "id": "id_mandat"}),
            "journal": forms.Select(attrs={"class": "form-control select2", "id": "id_journal"}),
            "type_piece": forms.Select(attrs={"class": "form-control"}),
            "numero_piece": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Généré automatiquement si vide")
            }),
            "date_piece": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format='%Y-%m-%d'
            ),
            "libelle": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "reference_externe": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Ex: Facture n° 2024-001")
            }),
            "tiers_nom": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Nom du fournisseur/client")
            }),
            "tiers_numero_tva": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("CHE-123.456.789 TVA")
            }),
            "montant_ht": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "0.00"
            }),
            "montant_tva": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "0.00"
            }),
            "montant_ttc": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "0.00"
            }),
            "dossier": forms.Select(attrs={"class": "form-control select2", "id": "id_dossier"}),
        }
        labels = {
            "mandat": _("Mandat"),
            "journal": _("Journal"),
            "type_piece": _("Type de pièce"),
            "numero_piece": _("Numéro de pièce"),
            "date_piece": _("Date"),
            "libelle": _("Libellé"),
            "reference_externe": _("Référence externe"),
            "tiers_nom": _("Tiers (fournisseur/client)"),
            "tiers_numero_tva": _("N° TVA du tiers"),
            "montant_ht": _("Montant HT"),
            "montant_tva": _("Montant TVA"),
            "montant_ttc": _("Montant TTC"),
            "dossier": _("Dossier de classement"),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        mandat_initial = kwargs.pop('mandat', None)
        super().__init__(*args, **kwargs)

        # Types de pièces actifs, ordonnés
        self.fields['type_piece'].queryset = TypePieceComptable.objects.filter(
            is_active=True
        ).order_by('ordre', 'code')

        # Afficher tous les mandats actifs (le filtrage par permission est géré par la vue)
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

        # Filtrer les journaux et dossiers selon le mandat
        from documents.models import Dossier

        if mandat_selectionne:
            # Journaux du mandat (peut être vide si le mandat n'a pas de journaux)
            journaux_qs = Journal.objects.filter(
                mandat=mandat_selectionne,
                is_active=True
            ).order_by('code')
            self.fields['journal'].queryset = journaux_qs

            # Si le mandat n'a pas de journaux, afficher un message approprié
            if not journaux_qs.exists():
                self.fields['journal'].empty_label = _("Aucun journal (optionnel)")
            else:
                self.fields['journal'].empty_label = _("Sélectionner un journal (optionnel)")

            # Dossiers du mandat OU du client - affichage avec chemin complet
            # Un dossier peut être rattaché au mandat OU au client du mandat
            dossiers_qs = Dossier.objects.filter(
                Q(mandat=mandat_selectionne) | Q(client=mandat_selectionne.client),
                is_active=True
            ).select_related('parent').order_by('nom')
            self.fields['dossier'].queryset = dossiers_qs

            # Message approprié pour les dossiers
            if not dossiers_qs.exists():
                self.fields['dossier'].empty_label = _("Aucun dossier disponible")
            else:
                self.fields['dossier'].empty_label = _("Sélectionner un dossier (optionnel)")
        else:
            # Pas de mandat sélectionné: listes vides avec message
            self.fields['journal'].queryset = Journal.objects.none()
            self.fields['journal'].empty_label = _("Sélectionnez d'abord un mandat")

            self.fields['dossier'].queryset = Dossier.objects.none()
            self.fields['dossier'].empty_label = _("Sélectionnez d'abord un mandat")

        # Le journal est optionnel (certains mandats n'en ont pas)
        self.fields['journal'].required = False
        # Option vide par défaut pour le dossier
        self.fields['dossier'].required = False
        # Le numéro de pièce est optionnel si la génération automatique est activée
        # La validation se fait dans clean()
        self.fields['numero_piece'].required = False

        # Si édition (instance déjà sauvegardée en base), ne pas permettre de changer le numéro généré
        # Note: on utilise _state.adding pour vérifier si c'est une nouvelle instance
        is_editing = self.instance.pk and not self.instance._state.adding
        if is_editing:
            self.fields['generer_numero'].initial = False
            self.fields['generer_numero'].widget = forms.HiddenInput()
            # Ne pas permettre de changer le mandat en édition
            self.fields['mandat'].widget.attrs['disabled'] = True

    def clean(self):
        cleaned_data = super().clean()
        generer_numero = cleaned_data.get('generer_numero')
        numero_piece = cleaned_data.get('numero_piece')

        # Si on ne génère pas automatiquement, le numéro est obligatoire
        if not generer_numero and not numero_piece:
            raise forms.ValidationError(
                _("Le numéro de pièce est obligatoire si la génération automatique est désactivée")
            )

        # Calculer montant_ttc si non fourni
        montant_ht = cleaned_data.get('montant_ht')
        montant_tva = cleaned_data.get('montant_tva')
        montant_ttc = cleaned_data.get('montant_ttc')

        if montant_ht and montant_tva and not montant_ttc:
            cleaned_data['montant_ttc'] = montant_ht + montant_tva

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Générer le numéro si demandé
        # Note: le journal n'est plus obligatoire, on peut générer un numéro
        # avec juste le type de pièce ou un préfixe par défaut
        if self.cleaned_data.get('generer_numero') and not instance.numero_piece:
            if instance.date_piece:
                instance.generer_numero()

        if commit:
            instance.save()
            self._save_m2m()

        return instance


class PieceComptableQuickForm(forms.ModelForm):
    """Formulaire simplifié pour création rapide de pièce comptable"""

    class Meta:
        model = PieceComptable
        fields = ["mandat", "journal", "type_piece", "date_piece", "libelle"]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "journal": forms.Select(attrs={"class": "form-control select2"}),
            "type_piece": forms.Select(attrs={"class": "form-control"}),
            "date_piece": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "libelle": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class LettrageForm(forms.ModelForm):
    """Formulaire pour un lettrage"""

    class Meta:
        model = Lettrage
        fields = ["mandat", "compte", "code_lettrage", "montant_total", "date_lettrage"]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "compte": forms.Select(attrs={"class": "form-control select2"}),
            "code_lettrage": forms.TextInput(attrs={"class": "form-control"}),
            "montant_total": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "date_lettrage": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }


class SaisieRapideForm(forms.Form):
    """Formulaire de saisie rapide d'écritures (OD)"""

    mandat = forms.ModelChoiceField(
        queryset=Mandat.objects.filter(statut="ACTIF"),
        label=_("Mandat"),
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )

    date_ecriture = forms.DateField(
        label=_("Date"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    libelle = forms.CharField(
        label=_("Libellé"), widget=forms.TextInput(attrs={"class": "form-control"})
    )

    # Ligne 1 (débit)
    compte_debit = forms.ModelChoiceField(
        queryset=Compte.objects.none(),
        label=_("Compte au débit"),
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )
    montant_debit = forms.DecimalField(
        label=_("Montant débit"),
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    # Ligne 2 (crédit)
    compte_credit = forms.ModelChoiceField(
        queryset=Compte.objects.none(),
        label=_("Compte au crédit"),
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )
    montant_credit = forms.DecimalField(
        label=_("Montant crédit"),
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Limiter les mandats selon l'utilisateur
        if user and not user.is_manager():
            self.fields["mandat"].queryset = Mandat.objects.filter(
                Q(responsable=user) | Q(equipe=user), statut="ACTIF"
            ).distinct()

    def clean(self):
        cleaned_data = super().clean()

        # Vérifier l'équilibre
        debit = cleaned_data.get("montant_debit", Decimal("0"))
        credit = cleaned_data.get("montant_credit", Decimal("0"))

        if debit != credit:
            raise forms.ValidationError(
                _("Les montants doivent être équilibrés (débit = crédit)")
            )

        return cleaned_data


class ImportEcrituresForm(forms.Form):
    """Formulaire d'import d'écritures depuis un fichier"""

    SEPARATEUR_CHOICES = [
        (",", _("Virgule")),
        (";", _("Point-virgule")),
        ("\t", _("Tabulation")),
    ]

    mandat = forms.ModelChoiceField(
        queryset=Mandat.objects.filter(statut="ACTIF"),
        label=_("Mandat"),
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )

    fichier = forms.FileField(
        label=_("Fichier CSV"),
        help_text=_("Format attendu: date;journal;compte;libelle;debit;credit"),
        widget=forms.FileInput(attrs={"class": "form-control"}),
    )

    separateur = forms.ChoiceField(
        choices=SEPARATEUR_CHOICES,
        initial=";",
        label=_("Séparateur"),
        widget=forms.Select(attrs={"class": "form-control select-basic"}),
    )

    premiere_ligne_entete = forms.BooleanField(
        required=False,
        initial=True,
        label=_("La première ligne contient les en-têtes"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


# =============================================================================
# ÉCRITURES INLINE DANS PIÈCE COMPTABLE
# =============================================================================

class EcritureInlinePieceForm(forms.ModelForm):
    """Formulaire inline pour une écriture dans une pièce comptable."""

    class Meta:
        model = EcritureComptable
        fields = [
            'compte', 'libelle', 'montant_debit', 'montant_credit',
            'code_tva', 'tiers',
        ]
        widgets = {
            'compte': forms.Select(attrs={
                'class': 'form-control select2 ecriture-compte',
            }),
            'libelle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Libellé'),
            }),
            'montant_debit': forms.NumberInput(attrs={
                'class': 'form-control text-end ecriture-debit',
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'montant_credit': forms.NumberInput(attrs={
                'class': 'form-control text-end ecriture-credit',
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'code_tva': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Code TVA'),
            }),
            'tiers': forms.Select(attrs={
                'class': 'form-control select2',
            }),
        }

    def __init__(self, *args, mandat=None, **kwargs):
        self.mandat_obj = mandat
        super().__init__(*args, **kwargs)

        # Champs numériques optionnels avec default
        for field_name in ('montant_debit', 'montant_credit'):
            self.fields[field_name].required = False
        self.fields['code_tva'].required = False
        self.fields['tiers'].required = False

        # Filtrer comptes par plan du mandat
        if mandat:
            plan = mandat.plan_comptable
            if plan:
                self.fields['compte'].queryset = Compte.objects.filter(
                    plan_comptable=plan, imputable=True
                ).order_by('numero')

    def clean_montant_debit(self):
        val = self.cleaned_data.get('montant_debit')
        return val if val is not None else Decimal('0')

    def clean_montant_credit(self):
        val = self.cleaned_data.get('montant_credit')
        return val if val is not None else Decimal('0')

    def clean(self):
        cleaned_data = super().clean()
        # Ignorer les lignes vides (pas de compte sélectionné)
        if not cleaned_data.get('compte'):
            return cleaned_data

        debit = cleaned_data.get('montant_debit', Decimal('0'))
        credit = cleaned_data.get('montant_credit', Decimal('0'))

        if debit > 0 and credit > 0:
            raise forms.ValidationError(
                _("Une écriture ne peut pas avoir un montant au débit ET au crédit")
            )
        if debit == 0 and credit == 0:
            raise forms.ValidationError(
                _("Une écriture doit avoir un montant (débit ou crédit)")
            )
        return cleaned_data


class BaseEcritureInlineFormSet(forms.BaseInlineFormSet):
    """Formset de base avec validation d'équilibre."""

    def __init__(self, *args, mandat=None, **kwargs):
        self.mandat_obj = mandat
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['mandat'] = self.mandat_obj
        return kwargs

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        total_debit = Decimal('0')
        total_credit = Decimal('0')
        has_data = False

        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if not form.cleaned_data or not form.cleaned_data.get('compte'):
                continue
            has_data = True
            total_debit += form.cleaned_data.get('montant_debit', Decimal('0'))
            total_credit += form.cleaned_data.get('montant_credit', Decimal('0'))

        if has_data and total_debit != total_credit:
            raise forms.ValidationError(
                _("La pièce n'est pas équilibrée : débit (%(debit)s) ≠ crédit (%(credit)s)") % {
                    'debit': total_debit,
                    'credit': total_credit,
                }
            )


EcritureInlineFormSet = inlineformset_factory(
    PieceComptable,
    EcritureComptable,
    form=EcritureInlinePieceForm,
    formset=BaseEcritureInlineFormSet,
    fk_name='piece',
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=True,
)


# =============================================================================
# COMPTABILITÉ ANALYTIQUE
# =============================================================================

class AxeAnalytiqueForm(forms.ModelForm):
    """Formulaire pour un axe analytique"""

    class Meta:
        model = AxeAnalytique
        fields = ['code', 'libelle', 'description', 'obligatoire']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'libelle': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'obligatoire': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SectionAnalytiqueForm(forms.ModelForm):
    """Formulaire pour une section analytique"""

    class Meta:
        model = SectionAnalytique
        fields = ['code', 'libelle', 'description', 'budget_annuel', 'parent']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'libelle': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'budget_annuel': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'parent': forms.Select(attrs={'class': 'form-control select2'}),
        }

    def __init__(self, *args, **kwargs):
        axe = kwargs.pop('axe', None)
        super().__init__(*args, **kwargs)
        if axe:
            self.fields['parent'].queryset = SectionAnalytique.objects.filter(
                axe=axe
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
        elif self.instance and self.instance.axe_id:
            self.fields['parent'].queryset = SectionAnalytique.objects.filter(
                axe=self.instance.axe
            ).exclude(pk=self.instance.pk)
        else:
            self.fields['parent'].queryset = SectionAnalytique.objects.none()


# =============================================================================
# IMMOBILISATIONS
# =============================================================================

class ImmobilisationForm(forms.ModelForm):
    """Formulaire pour une immobilisation"""

    class Meta:
        model = Immobilisation
        fields = [
            'mandat', 'numero', 'designation', 'description', 'categorie',
            'date_acquisition', 'date_mise_en_service', 'valeur_acquisition',
            'fournisseur', 'numero_facture',
            'compte_immobilisation', 'compte_amortissement', 'compte_amort_cumule',
            'methode_amortissement', 'duree_amortissement_mois',
            'taux_amortissement', 'valeur_residuelle',
            'statut', 'devise', 'notes',
        ]
        widgets = {
            'mandat': forms.Select(attrs={'class': 'form-control select2'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'categorie': forms.TextInput(attrs={'class': 'form-control'}),
            'date_acquisition': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'date_mise_en_service': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'valeur_acquisition': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fournisseur': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_facture': forms.TextInput(attrs={'class': 'form-control'}),
            'compte_immobilisation': forms.Select(attrs={'class': 'form-control select2'}),
            'compte_amortissement': forms.Select(attrs={'class': 'form-control select2'}),
            'compte_amort_cumule': forms.Select(attrs={'class': 'form-control select2'}),
            'methode_amortissement': forms.Select(attrs={'class': 'form-control select-basic'}),
            'duree_amortissement_mois': forms.NumberInput(attrs={'class': 'form-control'}),
            'taux_amortissement': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valeur_residuelle': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'statut': forms.Select(attrs={'class': 'form-control select-basic'}),
            'devise': forms.Select(attrs={'class': 'form-control select2'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les comptes par le plan du mandat
        mandat = None
        if self.instance and self.instance.mandat_id:
            mandat = self.instance.mandat
        elif self.data.get('mandat'):
            try:
                from core.models import Mandat as MandatModel
                mandat = MandatModel.objects.get(pk=self.data.get('mandat'))
            except Exception:
                pass

        if mandat and hasattr(mandat, 'plan_comptable') and mandat.plan_comptable:
            comptes_qs = Compte.objects.filter(
                plan_comptable=mandat.plan_comptable
            ).order_by('numero')
            self.fields['compte_immobilisation'].queryset = comptes_qs
            self.fields['compte_amortissement'].queryset = comptes_qs
            self.fields['compte_amort_cumule'].queryset = comptes_qs

        # Catégories depuis ParametreMetier
        categories = ParametreMetier.get_choices_with_default(
            'comptabilite', 'type_immobilisation', []
        )
        if categories:
            self.fields['categorie'].widget = forms.Select(
                attrs={'class': 'form-control select-basic'},
                choices=[('', '---------')] + list(categories),
            )
