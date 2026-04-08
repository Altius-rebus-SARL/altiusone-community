# salaires/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from datetime import datetime

from .models import Employe, FicheSalaire, CertificatSalaire, CertificatTravail
from core.models import Mandat, Adresse, ParametreMetier


class AdresseInlineForm(forms.ModelForm):
    """Formulaire inline pour une adresse"""

    class Meta:
        model = Adresse
        fields = ["rue", "numero", "complement", "code_postal", "localite", "region", "canton", "pays"]
        widgets = {
            "rue": forms.TextInput(attrs={"class": "form-control"}),
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "complement": forms.TextInput(attrs={"class": "form-control"}),
            "code_postal": forms.TextInput(attrs={"class": "form-control", "placeholder": "NPA / Code postal"}),
            "localite": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.TextInput(attrs={"class": "form-control", "placeholder": "Région (optionnel)"}),
            "canton": forms.Select(attrs={"class": "form-control"}),
            "pays": forms.Select(attrs={"class": "form-control"}),
        }


class EmployeForm(forms.ModelForm):
    """Formulaire pour un employé"""

    class Meta:
        model = Employe
        fields = [
            "mandat",
            "matricule",
            "nom",
            "prenom",
            "nom_naissance",
            "date_naissance",
            "lieu_naissance",
            "nationalite",
            "sexe",
            "avs_number",
            "numero_permis",
            "type_permis",
            "email",
            "telephone",
            "mobile",
            "etat_civil",
            "nombre_enfants",
            "type_contrat",
            "date_entree",
            "date_sortie",
            "date_fin_periode_essai",
            "fonction",
            "departement",
            "taux_occupation",
            "salaire_brut_mensuel",
            "salaire_horaire",
            "nombre_heures_semaine",
            "jours_vacances_annuel",
            "treizieme_salaire",
            "montant_13eme",
            "devise_salaire",
            "iban",
            "banque",
            "statut",
            "regime_fiscal",
            "soumis_is",
            "barreme_is",
            "taux_is",
            "canton_imposition",
            "eglise_is",
            "nombre_enfants_is",
            "numero_securite_sociale",
            "config_cotisations",
            "remarques",
        ]
        widgets = {
            "mandat": forms.Select(attrs={"class": "form-control select2"}),
            "matricule": forms.TextInput(attrs={"class": "form-control"}),
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "prenom": forms.TextInput(attrs={"class": "form-control"}),
            "nom_naissance": forms.TextInput(attrs={"class": "form-control"}),
            "date_naissance": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "lieu_naissance": forms.TextInput(attrs={"class": "form-control"}),
            "nationalite": forms.Select(attrs={"class": "form-control select2"}),
            "sexe": forms.Select(attrs={"class": "form-control"}),
            "avs_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "756.1234.5678.90"}
            ),
            "numero_permis": forms.TextInput(attrs={"class": "form-control"}),
            "type_permis": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
            "etat_civil": forms.Select(attrs={"class": "form-control"}),
            "nombre_enfants": forms.NumberInput(attrs={"class": "form-control"}),
            "type_contrat": forms.Select(attrs={"class": "form-control"}),
            "date_entree": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_sortie": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin_periode_essai": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "fonction": forms.TextInput(attrs={"class": "form-control"}),
            "departement": forms.TextInput(attrs={"class": "form-control"}),
            "taux_occupation": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "salaire_brut_mensuel": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "salaire_horaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "nombre_heures_semaine": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "jours_vacances_annuel": forms.NumberInput(attrs={"class": "form-control"}),
            "treizieme_salaire": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "montant_13eme": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "devise_salaire": forms.Select(attrs={"class": "form-control select2"}),
            "iban": forms.TextInput(attrs={"class": "form-control"}),
            "banque": forms.TextInput(attrs={"class": "form-control"}),
            "statut": forms.Select(attrs={"class": "form-control"}),
            "soumis_is": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "barreme_is": forms.TextInput(attrs={"class": "form-control"}),
            "taux_is": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "canton_imposition": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "2", "placeholder": "GE"}
            ),
            "eglise_is": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "nombre_enfants_is": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "numero_securite_sociale": forms.TextInput(attrs={"class": "form-control"}),
            "config_cotisations": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "remarques": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    _numeric_optional = [
        "nombre_enfants", "salaire_horaire", "montant_13eme", "taux_is",
        "jours_vacances_annuel", "nombre_enfants_is",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Charger les choix depuis ParametreMetier (DB) avec fallback sur les CHOICES du modèle
        self.fields['type_contrat'].choices = ParametreMetier.get_choices_with_default(
            'salaires', 'type_contrat', Employe.TYPE_CONTRAT_CHOICES
        )
        for field_name in self._numeric_optional:
            if field_name in self.fields:
                self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()

        # Convertir les champs numériques vides en valeur par défaut
        for field_name in self._numeric_optional:
            if field_name in cleaned_data and cleaned_data[field_name] is None:
                cleaned_data[field_name] = Decimal('0')

        # Si 13ème salaire activé, vérifier le montant
        if cleaned_data.get("treizieme_salaire"):
            if not cleaned_data.get("montant_13eme"):
                # Par défaut = salaire mensuel
                cleaned_data["montant_13eme"] = cleaned_data.get("salaire_brut_mensuel")

        return cleaned_data


class FicheSalaireForm(forms.ModelForm):
    """Formulaire pour une fiche de salaire"""

    # Champs numériques avec default=0 sur le modèle
    _numeric_optional = [
        "jours_travailles", "heures_travaillees", "heures_supplementaires",
        "jours_absence", "jours_vacances", "jours_maladie",
        "salaire_base", "heures_supp_montant", "primes", "indemnites",
        "treizieme_mois", "allocations_familiales", "autres_allocations",
        "avance_salaire", "saisie_salaire", "autres_deductions",
    ]

    class Meta:
        model = FicheSalaire
        fields = [
            "employe",
            "devise",
            "periode",
            "jours_travailles",
            "heures_travaillees",
            "heures_supplementaires",
            "jours_absence",
            "jours_vacances",
            "jours_maladie",
            "salaire_base",
            "heures_supp_montant",
            "primes",
            "indemnites",
            "treizieme_mois",
            "allocations_familiales",
            "autres_allocations",
            "avance_salaire",
            "saisie_salaire",
            "autres_deductions",
            "remarques",
        ]
        widgets = {
            "employe": forms.Select(attrs={"class": "form-control select2"}),
            "devise": forms.Select(attrs={"class": "form-control", "disabled": "disabled"}),
            "periode": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "jours_travailles": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "heures_travaillees": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "heures_supplementaires": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "jours_absence": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "jours_vacances": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "jours_maladie": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "salaire_base": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "heures_supp_montant": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "primes": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "indemnites": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "treizieme_mois": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "allocations_familiales": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "autres_allocations": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "avance_salaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "saisie_salaire": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "autres_deductions": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "remarques": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self._numeric_optional:
            if field_name in self.fields:
                self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        for field_name in self._numeric_optional:
            if field_name in cleaned_data and cleaned_data[field_name] is None:
                cleaned_data[field_name] = Decimal('0')
        return cleaned_data


class CertificatSalaireForm(forms.ModelForm):
    """Formulaire pour un certificat de salaire - Formulaire 11 suisse

    Organisé par sections conformes au formulaire officiel:
    - Identification et période
    - Occupation et transport (F-G)
    - Revenus (chiffres 1-7)
    - Déductions (chiffres 9-10)
    - Frais professionnels (chiffres 12-15)
    - Remarques et signature
    """

    # Champ optionnel pour calcul automatique
    auto_calculer = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Calculer automatiquement"),
        help_text=_("Remplir automatiquement depuis les fiches de salaire validées"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    class Meta:
        model = CertificatSalaire
        fields = [
            # === Identification et période ===
            "employe",
            "regime_fiscal",
            "devise",
            "annee",
            "date_debut",
            "date_fin",
            # === Section F-G: Occupation et transport ===
            "type_occupation",
            "taux_occupation",
            "transport_public_disponible",
            "transport_gratuit_fourni",
            # === Chiffre 1: Salaire ===
            "chiffre_1_salaire",
            # === Chiffre 2: Prestations en nature ===
            "chiffre_2_1_repas",
            "repas_midi_gratuit",
            "repas_soir_gratuit",
            "chiffre_2_2_voiture",
            "voiture_disponible",
            "voiture_prix_achat",
            "chiffre_2_3_autres",
            "autres_prestations_nature_detail",
            # === Chiffre 3: Prestations irrégulières ===
            "chiffre_3_irregulier",
            # === Chiffre 4: Prestations en capital ===
            "chiffre_4_capital",
            # === Chiffre 5: Participations ===
            "chiffre_5_participations",
            "participations_detail",
            # === Chiffre 6: Conseil d'administration ===
            "chiffre_6_ca",
            # === Chiffre 7: Autres prestations ===
            "chiffre_7_autres",
            "autres_prestations_detail",
            # === Chiffre 9: Cotisations ===
            "chiffre_9_cotisations",
            # === Chiffre 10: Prévoyance professionnelle ===
            "chiffre_10_1_lpp_ordinaire",
            "chiffre_10_2_lpp_rachat",
            # === Chiffre 12: Frais de transport ===
            "chiffre_12_transport",
            # === Chiffre 13: Frais de repas et nuitées ===
            "chiffre_13_1_1_repas_effectif",
            "chiffre_13_1_2_repas_forfait",
            "chiffre_13_2_nuitees",
            "chiffre_13_3_repas_externes",
            # === Chiffre 14: Autres frais ===
            "chiffre_14_autres_frais",
            "autres_frais_detail",
            # === Chiffre 15: Jours de transport ===
            "chiffre_15_jours_transport",
            # === Remarques ===
            "remarques",
            # === Signature ===
            "lieu_signature",
            "nom_signataire",
            "telephone_signataire",
            # === Info (legacy) ===
            "impot_source_annuel",
        ]
        widgets = {
            # Identification
            "employe": forms.Select(attrs={"class": "form-control select2"}),
            "regime_fiscal": forms.Select(attrs={"class": "form-control"}),
            "devise": forms.Select(attrs={"class": "form-control", "disabled": "disabled"}),
            "annee": forms.NumberInput(attrs={"class": "form-control", "min": "2000", "max": "2099"}),
            "date_debut": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "date_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            # Occupation et transport
            "type_occupation": forms.Select(attrs={"class": "form-control"}),
            "taux_occupation": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100"}),
            "transport_public_disponible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "transport_gratuit_fourni": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            # Chiffre 1
            "chiffre_1_salaire": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            # Chiffre 2
            "chiffre_2_1_repas": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "repas_midi_gratuit": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "repas_soir_gratuit": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "chiffre_2_2_voiture": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "voiture_disponible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "voiture_prix_achat": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "chiffre_2_3_autres": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "autres_prestations_nature_detail": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            # Chiffre 3
            "chiffre_3_irregulier": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            # Chiffre 4
            "chiffre_4_capital": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            # Chiffre 5
            "chiffre_5_participations": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "participations_detail": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            # Chiffre 6
            "chiffre_6_ca": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            # Chiffre 7
            "chiffre_7_autres": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "autres_prestations_detail": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            # Chiffre 9
            "chiffre_9_cotisations": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            # Chiffre 10
            "chiffre_10_1_lpp_ordinaire": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "chiffre_10_2_lpp_rachat": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            # Chiffre 12
            "chiffre_12_transport": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            # Chiffre 13
            "chiffre_13_1_1_repas_effectif": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "chiffre_13_1_2_repas_forfait": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "chiffre_13_2_nuitees": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "chiffre_13_3_repas_externes": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            # Chiffre 14
            "chiffre_14_autres_frais": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
            "autres_frais_detail": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            # Chiffre 15
            "chiffre_15_jours_transport": forms.NumberInput(attrs={"class": "form-control", "min": "0", "max": "366"}),
            # Remarques
            "remarques": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            # Signature
            "lieu_signature": forms.TextInput(attrs={"class": "form-control"}),
            "nom_signataire": forms.TextInput(attrs={"class": "form-control"}),
            "telephone_signataire": forms.TextInput(attrs={"class": "form-control"}),
            # Info
            "impot_source_annuel": forms.NumberInput(attrs={"class": "form-control montant", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Marquer les champs non-requis
        optional_fields = [
            "regime_fiscal", "devise",
            "chiffre_2_1_repas", "chiffre_2_2_voiture", "chiffre_2_3_autres",
            "chiffre_3_irregulier", "chiffre_4_capital", "chiffre_5_participations",
            "chiffre_6_ca", "chiffre_7_autres", "chiffre_10_2_lpp_rachat",
            "chiffre_12_transport", "chiffre_13_1_1_repas_effectif",
            "chiffre_13_1_2_repas_forfait", "chiffre_13_2_nuitees",
            "chiffre_13_3_repas_externes", "chiffre_14_autres_frais",
            "voiture_prix_achat", "participations_detail", "autres_prestations_detail",
            "autres_prestations_nature_detail", "autres_frais_detail",
            "lieu_signature", "nom_signataire", "telephone_signataire",
            "impot_source_annuel",
        ]
        for field_name in optional_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()

        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        annee = cleaned_data.get("annee")

        # Vérifier que les dates sont dans l'année
        if date_debut and annee:
            if date_debut.year != annee:
                self.add_error("date_debut", _("La date de début doit être dans l'année du certificat"))

        if date_fin and annee:
            if date_fin.year != annee:
                self.add_error("date_fin", _("La date de fin doit être dans l'année du certificat"))

        # Vérifier que date_debut < date_fin
        if date_debut and date_fin:
            if date_debut > date_fin:
                self.add_error("date_fin", _("La date de fin doit être après la date de début"))

        # Calcul automatique de la valeur voiture si prix d'achat renseigné
        voiture_prix = cleaned_data.get("voiture_prix_achat")
        voiture_valeur = cleaned_data.get("chiffre_2_2_voiture")

        if voiture_prix and not voiture_valeur:
            # 0.9% par mois * nombre de mois
            if date_debut and date_fin:
                from decimal import Decimal
                mois = ((date_fin.year - date_debut.year) * 12 +
                        date_fin.month - date_debut.month + 1)
                cleaned_data["chiffre_2_2_voiture"] = voiture_prix * Decimal("0.009") * mois

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Si calcul automatique demandé
        if self.cleaned_data.get("auto_calculer"):
            if commit:
                instance.save()
                try:
                    instance.calculer_depuis_fiches(save=True)
                except ValueError:
                    pass  # Pas de fiches disponibles
            return instance

        if commit:
            instance.save()

        return instance


class CertificatTravailForm(forms.ModelForm):
    """Formulaire pour un certificat de travail (Arbeitszeugnis)"""

    class Meta:
        model = CertificatTravail
        fields = [
            "employe",
            "regime_fiscal",
            "type_certificat",
            "date_debut_emploi",
            "date_fin_emploi",
            "fonction_principale",
            "departement",
            "taux_occupation",
            "description_taches",
            "evaluation_qualite_travail",
            "evaluation_quantite_travail",
            "evaluation_competences",
            "evaluation_comportement",
            "evaluation_relations",
            "evaluation_autonomie",
            "texte_evaluation",
            "motif_depart",
            "formule_fin",
            "formations_suivies",
            "projets_speciaux",
            "date_demande",
        ]
        widgets = {
            "employe": forms.Select(attrs={"class": "form-control select2"}),
            "regime_fiscal": forms.Select(attrs={"class": "form-control"}),
            "type_certificat": forms.Select(attrs={"class": "form-control"}),
            "date_debut_emploi": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "date_fin_emploi": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "fonction_principale": forms.TextInput(attrs={"class": "form-control"}),
            "departement": forms.TextInput(attrs={"class": "form-control"}),
            "taux_occupation": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100"}
            ),
            "description_taches": forms.Textarea(
                attrs={"class": "form-control", "rows": 5, "placeholder": _("Décrivez les principales responsabilités et tâches...")}
            ),
            "evaluation_qualite_travail": forms.Select(attrs={"class": "form-control"}),
            "evaluation_quantite_travail": forms.Select(attrs={"class": "form-control"}),
            "evaluation_competences": forms.Select(attrs={"class": "form-control"}),
            "evaluation_comportement": forms.Select(attrs={"class": "form-control"}),
            "evaluation_relations": forms.Select(attrs={"class": "form-control"}),
            "evaluation_autonomie": forms.Select(attrs={"class": "form-control"}),
            "texte_evaluation": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": _("Laissez vide pour générer automatiquement selon les notes...")}
            ),
            "motif_depart": forms.Select(attrs={"class": "form-control"}),
            "formule_fin": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": _("Laissez vide pour générer une formule standard...")}
            ),
            "formations_suivies": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": _("Formations suivies pendant l'emploi...")}
            ),
            "projets_speciaux": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": _("Projets ou missions spéciales...")}
            ),
            "date_demande": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Charger les choix depuis ParametreMetier
        self.fields['type_certificat'].choices = ParametreMetier.get_choices_with_default(
            'salaires', 'type_certificat_travail', CertificatTravail.TYPE_CERTIFICAT_CHOICES
        )
        self.fields['motif_depart'].choices = [('', '---------')] + ParametreMetier.get_choices_with_default(
            'salaires', 'motif_depart', CertificatTravail.MOTIF_DEPART_CHOICES
        )
        # Ajouter des choices vides pour les évaluations
        for field_name in [
            'evaluation_qualite_travail',
            'evaluation_quantite_travail',
            'evaluation_competences',
            'evaluation_comportement',
            'evaluation_relations',
            'evaluation_autonomie',
        ]:
            self.fields[field_name].required = False
            self.fields[field_name].choices = [('', '---------')] + list(self.fields[field_name].choices)

    def clean(self):
        cleaned_data = super().clean()
        type_certificat = cleaned_data.get('type_certificat')
        date_fin = cleaned_data.get('date_fin_emploi')
        motif_depart = cleaned_data.get('motif_depart')

        # Pour un certificat final (pas intermédiaire), la date de fin est requise
        if type_certificat != 'INTERMEDIAIRE' and not date_fin:
            # C'est acceptable pour un employé toujours en poste
            pass

        # Si date de fin, le motif de départ devrait être renseigné
        if date_fin and not motif_depart:
            self.add_error(
                'motif_depart',
                _("Veuillez indiquer le motif de départ pour un certificat de fin d'emploi.")
            )

        return cleaned_data
