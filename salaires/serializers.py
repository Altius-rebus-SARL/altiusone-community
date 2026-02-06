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


class CertificatSalaireSerializer(serializers.ModelSerializer):
    """Serializer pour les certificats de salaire"""

    employe = EmployeListSerializer(read_only=True)
    genere_par = UserSerializer(read_only=True)

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
