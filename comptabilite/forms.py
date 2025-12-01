# comptabilite/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from decimal import Decimal
from .models import (
    PlanComptable,
    Compte,
    Journal,
    EcritureComptable,
    PieceComptable,
    Lettrage,
)
from core.models import Mandat, ExerciceComptable


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
            "base_sur",
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
            "base_sur": forms.Select(attrs={"class": "form-control select2"}),
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limiter les comptes parents au même plan
        if self.instance and self.instance.plan_comptable:
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
            "numerotation_auto",
            "prefixe_piece",
            "dernier_numero",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
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
        # Limiter les comptes au plan du mandat
        if self.instance and self.instance.mandat:
            plan = self.instance.mandat.plans_comptables.first()
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
            "devise": forms.TextInput(attrs={"class": "form-control"}),
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
        super().__init__(*args, **kwargs)

        # Limiter les choix selon le mandat - SEULEMENT si l'instance a un PK (modification)
        if self.instance.pk:
            try:
                mandat = self.instance.mandat

                # Exercices du mandat
                self.fields["exercice"].queryset = ExerciceComptable.objects.filter(
                    mandat=mandat
                )

                # Journaux du mandat
                self.fields["journal"].queryset = Journal.objects.filter(mandat=mandat)

                # Comptes du plan
                plan = mandat.plans_comptables.first()
                if plan:
                    self.fields["compte"].queryset = Compte.objects.filter(
                        plan_comptable=plan, imputable=True
                    ).order_by("numero")

                # Documents du mandat
                from documents.models import Document

                self.fields["piece_justificative"].queryset = Document.objects.filter(
                    mandat=mandat
                )
            except:
                # Si pas de mandat, laisser les querysets par défaut
                pass

    def clean(self):
        cleaned_data = super().clean()

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


class PieceComptableForm(forms.ModelForm):
    """Formulaire pour une pièce comptable"""

    class Meta:
        model = PieceComptable
        fields = ["mandat", "journal", "numero_piece", "date_piece", "libelle"]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "journal": forms.Select(attrs={"class": "form-control select2"}),
            "numero_piece": forms.TextInput(attrs={"class": "form-control"}),
            "date_piece": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "libelle": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
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
        if user and user.role not in ["ADMIN", "MANAGER"]:
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
