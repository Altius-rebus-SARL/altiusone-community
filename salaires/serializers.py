# salaires/serializers.py
from rest_framework import serializers
from .models import (
    Employe,
    TauxCotisation,
    FicheSalaire,
    CertificatSalaire,
    DeclarationCotisations,
    DeclarationCotisationsLigne,
    CertificatTravail,
    LigneCotisationFiche,
)
from core.serializers import MandatListSerializer, UserSerializer, AdresseSerializer


class LigneCotisationFicheSerializer(serializers.ModelSerializer):
    type_cotisation_libelle = serializers.CharField(source='taux_cotisation.libelle', read_only=True)
    type_cotisation_code = serializers.CharField(source='taux_cotisation.type_cotisation', read_only=True)

    class Meta:
        model = LigneCotisationFiche
        fields = ['id', 'taux_cotisation', 'type_cotisation_libelle', 'type_cotisation_code',
                  'libelle', 'base_calcul', 'taux_employe', 'taux_employeur',
                  'montant_employe', 'montant_employeur', 'ordre']


class EmployeListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste d'employés"""

    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    type_contrat_display = serializers.CharField(
        source="get_type_contrat_display", read_only=True
    )
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    age = serializers.IntegerField(read_only=True)
    utilisateur_email = serializers.CharField(
        source="utilisateur.email", read_only=True
    )
    a_compte_utilisateur = serializers.SerializerMethodField()

    class Meta:
        model = Employe
        fields = [
            "id",
            "matricule",
            "nom",
            "prenom",
            "fonction",
            "date_naissance",
            "age",
            "statut",
            "statut_display",
            "type_contrat",
            "type_contrat_display",
            "salaire_brut_mensuel",
            "mandat",
            "mandat_numero",
            "utilisateur",
            "utilisateur_email",
            "a_compte_utilisateur",
            "canton_imposition",
            "eglise_is",
            "nombre_enfants_is",
            "numero_securite_sociale",
            "created_at",
        ]

    def get_a_compte_utilisateur(self, obj):
        return obj.utilisateur is not None


class EmployeDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un employé"""

    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    type_contrat_display = serializers.CharField(
        source="get_type_contrat_display", read_only=True
    )
    sexe_display = serializers.CharField(source="get_sexe_display", read_only=True)
    mandat = MandatListSerializer(read_only=True)
    adresse = AdresseSerializer(read_only=True)
    utilisateur = UserSerializer(read_only=True)
    age = serializers.IntegerField(read_only=True)
    salaire_annuel_brut = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Employe
        fields = "__all__"


class TauxCotisationSerializer(serializers.ModelSerializer):
    """Serializer pour les taux de cotisations"""

    type_cotisation_display = serializers.CharField(
        source="get_type_cotisation_display", read_only=True
    )
    repartition_display = serializers.CharField(
        source="get_repartition_display", read_only=True
    )

    class Meta:
        model = TauxCotisation
        fields = "__all__"


class FicheSalaireListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de fiches de salaire"""

    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    employe_nom = serializers.CharField(source="employe.__str__", read_only=True)
    periode_formatted = serializers.SerializerMethodField()

    class Meta:
        model = FicheSalaire
        fields = [
            "id",
            "numero_fiche",
            "employe",
            "employe_nom",
            "periode",
            "periode_formatted",
            "annee",
            "mois",
            "salaire_brut_total",
            "salaire_net",
            "statut",
            "statut_display",
            "date_paiement",
            "created_at",
        ]

    def get_periode_formatted(self, obj):
        return obj.periode.strftime("%m/%Y")


class FicheSalaireDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une fiche de salaire"""

    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    employe = EmployeListSerializer(read_only=True)
    valide_par = UserSerializer(read_only=True)
    lignes_cotisations = LigneCotisationFicheSerializer(many=True, read_only=True)

    class Meta:
        model = FicheSalaire
        fields = "__all__"


class CertificatSalaireListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de certificats de salaire"""

    employe_nom = serializers.CharField(source="employe.__str__", read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    type_occupation_display = serializers.CharField(
        source="get_type_occupation_display", read_only=True
    )
    regime_fiscal_code = serializers.CharField(
        source="regime_fiscal.code", read_only=True, default=None
    )
    devise_code = serializers.CharField(
        source="devise.code", read_only=True, default=None
    )
    periode_formatted = serializers.SerializerMethodField()

    class Meta:
        model = CertificatSalaire
        fields = [
            "id",
            "employe",
            "employe_nom",
            "annee",
            "date_debut",
            "date_fin",
            "periode_formatted",
            "regime_fiscal",
            "regime_fiscal_code",
            "devise",
            "devise_code",
            "statut",
            "statut_display",
            "type_occupation",
            "type_occupation_display",
            "taux_occupation",
            "chiffre_8_total_brut",
            "chiffre_11_net",
            "est_signe",
            "fichier_pdf",
            "created_at",
        ]

    def get_periode_formatted(self, obj):
        if obj.date_debut and obj.date_fin:
            return f"{obj.date_debut.strftime('%d.%m.%Y')} - {obj.date_fin.strftime('%d.%m.%Y')}"
        return ""


class CertificatSalaireDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un certificat de salaire - Formulaire 11"""

    employe = EmployeListSerializer(read_only=True)
    genere_par = UserSerializer(read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    type_occupation_display = serializers.CharField(
        source="get_type_occupation_display", read_only=True
    )

    # Informations employeur (via l'employé)
    employeur_raison_sociale = serializers.CharField(
        source="employe.mandat.client.raison_sociale", read_only=True
    )
    employeur_ide = serializers.CharField(
        source="employe.mandat.client.ide_number", read_only=True
    )

    # Champs calculés
    total_prestations_nature = serializers.SerializerMethodField()
    total_deductions = serializers.SerializerMethodField()
    total_frais = serializers.SerializerMethodField()

    class Meta:
        model = CertificatSalaire
        fields = "__all__"

    def get_total_prestations_nature(self, obj):
        """Total des chiffres 2.1 + 2.2 + 2.3"""
        from decimal import Decimal
        return (
            (obj.chiffre_2_1_repas or Decimal('0')) +
            (obj.chiffre_2_2_voiture or Decimal('0')) +
            (obj.chiffre_2_3_autres or Decimal('0'))
        )

    def get_total_deductions(self, obj):
        """Total des déductions (chiffres 9 + 10)"""
        from decimal import Decimal
        return (
            (obj.chiffre_9_cotisations or Decimal('0')) +
            (obj.chiffre_10_1_lpp_ordinaire or Decimal('0')) +
            (obj.chiffre_10_2_lpp_rachat or Decimal('0'))
        )

    def get_total_frais(self, obj):
        """Total des frais professionnels (chiffres 12-14)"""
        from decimal import Decimal
        return (
            (obj.chiffre_12_transport or Decimal('0')) +
            (obj.chiffre_13_1_1_repas_effectif or Decimal('0')) +
            (obj.chiffre_13_1_2_repas_forfait or Decimal('0')) +
            (obj.chiffre_13_2_nuitees or Decimal('0')) +
            (obj.chiffre_13_3_repas_externes or Decimal('0')) +
            (obj.chiffre_14_autres_frais or Decimal('0'))
        )


class CertificatSalaireCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un certificat de salaire avec option de calcul automatique"""

    auto_calculer = serializers.BooleanField(
        write_only=True, default=False,
        help_text="Si True, calcule automatiquement les montants depuis les fiches de salaire"
    )

    class Meta:
        model = CertificatSalaire
        fields = [
            "employe",
            "regime_fiscal",
            "devise",
            "annee",
            "date_debut",
            "date_fin",
            "type_occupation",
            "taux_occupation",
            "transport_public_disponible",
            "transport_gratuit_fourni",
            "repas_midi_gratuit",
            "repas_soir_gratuit",
            "auto_calculer",
            # Revenus
            "chiffre_1_salaire",
            "chiffre_2_1_repas",
            "chiffre_2_2_voiture",
            "voiture_disponible",
            "voiture_prix_achat",
            "chiffre_2_3_autres",
            "autres_prestations_nature_detail",
            "chiffre_3_irregulier",
            "chiffre_4_capital",
            "chiffre_5_participations",
            "participations_detail",
            "chiffre_6_ca",
            "chiffre_7_autres",
            "autres_prestations_detail",
            # Déductions
            "chiffre_9_cotisations",
            "chiffre_10_1_lpp_ordinaire",
            "chiffre_10_2_lpp_rachat",
            # Frais
            "chiffre_12_transport",
            "chiffre_13_1_1_repas_effectif",
            "chiffre_13_1_2_repas_forfait",
            "chiffre_13_2_nuitees",
            "chiffre_13_3_repas_externes",
            "chiffre_14_autres_frais",
            "autres_frais_detail",
            "chiffre_15_jours_transport",
            # Signature
            "lieu_signature",
            "nom_signataire",
            "telephone_signataire",
            "impot_source_annuel",
            "remarques",
        ]
        extra_kwargs = {f: {"required": False} for f in [
            "regime_fiscal", "devise", "date_debut", "date_fin",
            "chiffre_1_salaire", "chiffre_2_1_repas", "chiffre_2_2_voiture",
            "chiffre_2_3_autres", "chiffre_3_irregulier", "chiffre_4_capital",
            "chiffre_5_participations", "chiffre_6_ca", "chiffre_7_autres",
            "chiffre_9_cotisations", "chiffre_10_1_lpp_ordinaire",
            "chiffre_10_2_lpp_rachat", "chiffre_12_transport",
            "chiffre_13_1_1_repas_effectif", "chiffre_13_1_2_repas_forfait",
            "chiffre_13_2_nuitees", "chiffre_13_3_repas_externes",
            "chiffre_14_autres_frais", "voiture_prix_achat",
            "autres_prestations_nature_detail", "participations_detail",
            "autres_prestations_detail", "autres_frais_detail",
            "lieu_signature", "nom_signataire", "telephone_signataire",
            "impot_source_annuel",
        ]}

    def create(self, validated_data):
        auto_calculer = validated_data.pop("auto_calculer", False)

        # Si calcul auto, on a besoin seulement de employe et annee
        if auto_calculer:
            employe = validated_data["employe"]
            annee = validated_data["annee"]

            # Créer avec valeurs par défaut
            from datetime import date
            certificat = CertificatSalaire(
                employe=employe,
                annee=annee,
                date_debut=validated_data.get("date_debut") or date(annee, 1, 1),
                date_fin=validated_data.get("date_fin") or date(annee, 12, 31),
                type_occupation=validated_data.get("type_occupation", "PLEIN_TEMPS"),
                taux_occupation=validated_data.get("taux_occupation", 100),
                transport_public_disponible=validated_data.get("transport_public_disponible", True),
                transport_gratuit_fourni=validated_data.get("transport_gratuit_fourni", False),
                remarques=validated_data.get("remarques", ""),
            )
            certificat.save()

            # Calculer depuis les fiches
            try:
                certificat.calculer_depuis_fiches(save=True)
            except ValueError as e:
                # Si pas de fiches, garder le certificat en brouillon
                certificat.remarques = f"Calcul auto impossible: {str(e)}"
                certificat.save()

            return certificat
        else:
            # Création manuelle standard
            return super().create(validated_data)


class CertificatSalaireSerializer(serializers.ModelSerializer):
    """Serializer par défaut pour les certificats de salaire (compatibilité)"""

    employe = EmployeListSerializer(read_only=True)
    genere_par = UserSerializer(read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = CertificatSalaire
        fields = "__all__"


class DeclarationCotisationsLigneSerializer(serializers.ModelSerializer):
    """Serializer pour les lignes de déclaration par employé"""

    employe_nom = serializers.CharField(source='employe.nom', read_only=True)
    employe_prenom = serializers.CharField(source='employe.prenom', read_only=True)
    employe_avs = serializers.CharField(source='employe.avs_number', read_only=True)

    class Meta:
        model = DeclarationCotisationsLigne
        fields = [
            'id', 'employe', 'employe_nom', 'employe_prenom', 'employe_avs',
            'salaire_brut', 'salaire_soumis',
            'cotisation_employe', 'cotisation_employeur', 'cotisation_totale'
        ]


class DeclarationCotisationsListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des déclarations"""

    organisme_display = serializers.CharField(source="get_organisme_display", read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    periode_display = serializers.CharField(source="get_periode_display", read_only=True)
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    client_nom = serializers.CharField(source="mandat.client.raison_sociale", read_only=True)
    regime_fiscal_code = serializers.CharField(
        source="regime_fiscal.code", read_only=True, default=None
    )
    devise_code = serializers.CharField(
        source="devise.code", read_only=True, default=None
    )

    class Meta:
        model = DeclarationCotisations
        fields = [
            'id', 'mandat', 'mandat_numero', 'client_nom',
            'regime_fiscal', 'regime_fiscal_code',
            'devise', 'devise_code',
            'organisme', 'organisme_display',
            'periode_type', 'annee', 'mois', 'trimestre', 'periode_display',
            'periode_debut', 'periode_fin',
            'nombre_employes', 'masse_salariale_brute', 'montant_cotisations',
            'statut', 'statut_display',
            'date_echeance', 'date_paiement',
        ]


class DeclarationCotisationsDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail des déclarations"""

    organisme_display = serializers.CharField(source="get_organisme_display", read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    periode_display = serializers.CharField(source="get_periode_display", read_only=True)
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    client_nom = serializers.CharField(source="mandat.client.raison_sociale", read_only=True)
    regime_fiscal_code = serializers.CharField(
        source="regime_fiscal.code", read_only=True, default=None
    )
    devise_code = serializers.CharField(
        source="devise.code", read_only=True, default=None
    )
    lignes = DeclarationCotisationsLigneSerializer(many=True, read_only=True)

    class Meta:
        model = DeclarationCotisations
        fields = [
            'id', 'mandat', 'mandat_numero', 'client_nom',
            'regime_fiscal', 'regime_fiscal_code',
            'devise', 'devise_code',
            'organisme', 'organisme_display',
            'nom_caisse', 'numero_affilie', 'numero_contrat',
            'periode_type', 'annee', 'mois', 'trimestre', 'periode_display',
            'periode_debut', 'periode_fin',
            'nombre_employes', 'masse_salariale_brute', 'masse_salariale_soumise',
            # Cotisations AVS
            'cotisation_avs', 'cotisation_ai', 'cotisation_apg',
            'cotisation_ac', 'cotisation_ac_supp', 'frais_administration',
            # Cotisations LPP
            'cotisation_lpp_employe', 'cotisation_lpp_employeur',
            # Cotisations LAA
            'cotisation_laa_pro', 'cotisation_laa_non_pro', 'cotisation_laac',
            # Cotisations AF/IJM
            'cotisation_af', 'cotisation_ijm',
            # Totaux
            'total_cotisations_employe', 'total_cotisations_employeur', 'montant_cotisations',
            # Statut et dates
            'statut', 'statut_display',
            'date_declaration', 'date_echeance', 'date_transmission', 'date_paiement',
            # Paiement
            'numero_reference', 'numero_bvr', 'iban_caisse',
            # Documents
            'fichier_declaration', 'remarques',
            # Lignes
            'lignes',
            # Timestamps
            'created_at', 'updated_at',
        ]


class DeclarationCotisationsCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de déclarations"""

    auto_calculer = serializers.BooleanField(write_only=True, default=True)

    class Meta:
        model = DeclarationCotisations
        fields = [
            'mandat', 'organisme', 'regime_fiscal', 'devise',
            'periode_type', 'annee', 'mois', 'trimestre',
            'nom_caisse', 'numero_affilie', 'numero_contrat',
            'auto_calculer',
        ]
        extra_kwargs = {
            'regime_fiscal': {'required': False},
            'devise': {'required': False},
            'mois': {'required': False},
            'trimestre': {'required': False},
            'nom_caisse': {'required': False},
            'numero_affilie': {'required': False},
            'numero_contrat': {'required': False},
        }

    def create(self, validated_data):
        from calendar import monthrange
        from datetime import date

        auto_calculer = validated_data.pop('auto_calculer', True)
        annee = validated_data.get('annee')
        mois = validated_data.get('mois')
        trimestre = validated_data.get('trimestre')
        periode_type = validated_data.get('periode_type', 'MENSUEL')

        # Calculer les dates de période
        if periode_type == 'MENSUEL' and mois:
            validated_data['periode_debut'] = date(annee, mois, 1)
            last_day = monthrange(annee, mois)[1]
            validated_data['periode_fin'] = date(annee, mois, last_day)
        elif periode_type == 'TRIMESTRIEL' and trimestre:
            mois_debut = (trimestre - 1) * 3 + 1
            mois_fin = trimestre * 3
            validated_data['periode_debut'] = date(annee, mois_debut, 1)
            last_day = monthrange(annee, mois_fin)[1]
            validated_data['periode_fin'] = date(annee, mois_fin, last_day)
        else:
            validated_data['periode_debut'] = date(annee, 1, 1)
            validated_data['periode_fin'] = date(annee, 12, 31)

        validated_data['date_declaration'] = date.today()

        declaration = super().create(validated_data)

        if auto_calculer:
            declaration.calculer_depuis_fiches()
            declaration.calculer_echeance()

        return declaration


class DeclarationCotisationsSerializer(serializers.ModelSerializer):
    """Serializer par défaut pour les déclarations de cotisations"""

    organisme_display = serializers.CharField(source="get_organisme_display", read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)

    class Meta:
        model = DeclarationCotisations
        fields = "__all__"


class CertificatTravailListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de certificats de travail"""

    employe_nom = serializers.CharField(source="employe.__str__", read_only=True)
    type_certificat_display = serializers.CharField(
        source="get_type_certificat_display", read_only=True
    )

    class Meta:
        model = CertificatTravail
        fields = [
            "id",
            "employe",
            "employe_nom",
            "type_certificat",
            "type_certificat_display",
            "date_emission",
            "date_debut_emploi",
            "date_fin_emploi",
            "fonction_principale",
            "fichier_pdf",
        ]


class CertificatTravailDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un certificat de travail"""

    employe = EmployeListSerializer(read_only=True)
    emis_par = UserSerializer(read_only=True)
    type_certificat_display = serializers.CharField(
        source="get_type_certificat_display", read_only=True
    )

    class Meta:
        model = CertificatTravail
        fields = "__all__"
