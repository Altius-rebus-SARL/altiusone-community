# salaires/serializers.py
from rest_framework import serializers
from .models import (
    Employe,
    TauxCotisation,
    FicheSalaire,
    CertificatSalaire,
    DeclarationCotisations,
)
from core.serializers import MandatListSerializer, UserSerializer, AdresseSerializer


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
            "annee",
            "date_debut",
            "date_fin",
            "type_occupation",
            "taux_occupation",
            "transport_public_disponible",
            "transport_gratuit_fourni",
            "auto_calculer",
            # Optionnel: valeurs manuelles si pas de calcul auto
            "chiffre_1_salaire",
            "chiffre_2_1_repas",
            "chiffre_2_2_voiture",
            "chiffre_2_3_autres",
            "chiffre_3_irregulier",
            "chiffre_9_cotisations",
            "chiffre_10_1_lpp_ordinaire",
            "remarques",
        ]
        extra_kwargs = {
            "date_debut": {"required": False},
            "date_fin": {"required": False},
            "chiffre_1_salaire": {"required": False},
            "chiffre_2_1_repas": {"required": False},
            "chiffre_2_2_voiture": {"required": False},
            "chiffre_2_3_autres": {"required": False},
            "chiffre_3_irregulier": {"required": False},
            "chiffre_9_cotisations": {"required": False},
            "chiffre_10_1_lpp_ordinaire": {"required": False},
        }

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


class DeclarationCotisationsSerializer(serializers.ModelSerializer):
    """Serializer pour les déclarations de cotisations"""

    organisme_display = serializers.CharField(
        source="get_organisme_display", read_only=True
    )
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)

    class Meta:
        model = DeclarationCotisations
        fields = "__all__"
