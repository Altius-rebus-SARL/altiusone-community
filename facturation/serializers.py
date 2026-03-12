# facturation/serializers.py
from rest_framework import serializers
from .models import (
    Prestation,
    TimeTracking,
    Facture,
    LigneFacture,
    Paiement,
    Relance,
    TypePrestation,
    ZoneGeographique,
    TarifMandat,
    CategorieTemps,
)
from core.serializers import MandatListSerializer, UserSerializer, ClientListSerializer


class TypeMandatSimpleSerializer(serializers.Serializer):
    """Serializer léger pour les types de mandats dans le contexte prestation"""
    id = serializers.UUIDField()
    code = serializers.CharField()
    libelle = serializers.CharField()


class PrestationSerializer(serializers.ModelSerializer):
    type_prestation_display = serializers.CharField(
        source="type_prestation.libelle", read_only=True
    )
    type_prestation_code = serializers.CharField(
        source="type_prestation.code", read_only=True
    )
    types_mandats_detail = TypeMandatSimpleSerializer(
        source="types_mandats", many=True, read_only=True
    )

    class Meta:
        model = Prestation
        fields = "__all__"


# =============================================================================
# CATÉGORIES DE TEMPS (interne & absences)
# =============================================================================

class CategorieTempsSerializer(serializers.ModelSerializer):
    """Serializer pour les catégories de temps (interne et absences)"""

    type_categorie_display = serializers.CharField(
        source="get_type_categorie_display", read_only=True
    )

    class Meta:
        model = CategorieTemps
        fields = [
            "id",
            "code",
            "libelle",
            "description",
            "type_categorie",
            "type_categorie_display",
            "icone",
            "couleur",
            "decompte_vacances",
            "decompte_maladie",
            "ordre",
            "is_active",
        ]


# =============================================================================
# TIME TRACKING
# =============================================================================

class TimeTrackingListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des entrées de temps"""

    type_entree_display = serializers.CharField(
        source="get_type_entree_display", read_only=True
    )
    mandat_numero = serializers.CharField(
        source="mandat.numero", read_only=True, allow_null=True, default=None
    )
    utilisateur_name = serializers.CharField(
        source="utilisateur.get_full_name", read_only=True
    )
    prestation_libelle = serializers.CharField(
        source="prestation.libelle", read_only=True, allow_null=True, default=None
    )
    categorie_libelle = serializers.CharField(
        source="categorie.libelle", read_only=True, allow_null=True, default=None
    )
    categorie_icone = serializers.CharField(
        source="categorie.icone", read_only=True, allow_null=True, default=None
    )
    categorie_couleur = serializers.CharField(
        source="categorie.couleur", read_only=True, allow_null=True, default=None
    )
    duree_heures = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )

    class Meta:
        model = TimeTracking
        fields = [
            "id",
            "type_entree",
            "type_entree_display",
            "date_travail",
            "utilisateur",
            "utilisateur_name",
            "mandat",
            "mandat_numero",
            "prestation",
            "prestation_libelle",
            "categorie",
            "categorie_libelle",
            "categorie_icone",
            "categorie_couleur",
            "heure_debut",
            "heure_fin",
            "duree_minutes",
            "duree_heures",
            "description",
            "facturable",
            "montant_ht",
            "valide",
            "created_at",
        ]


class TimeTrackingSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour le CRUD des entrées de temps"""

    type_entree_display = serializers.CharField(
        source="get_type_entree_display", read_only=True
    )
    mandat_numero = serializers.CharField(
        source="mandat.numero", read_only=True, allow_null=True, default=None
    )
    utilisateur_name = serializers.CharField(
        source="utilisateur.get_full_name", read_only=True
    )
    prestation_libelle = serializers.CharField(
        source="prestation.libelle", read_only=True, allow_null=True, default=None
    )
    categorie_detail = CategorieTempsSerializer(
        source="categorie", read_only=True
    )
    duree_heures = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )

    class Meta:
        model = TimeTracking
        fields = "__all__"

    def validate(self, attrs):
        type_entree = attrs.get("type_entree", "CLIENT")
        if type_entree == "CLIENT":
            if not attrs.get("mandat"):
                raise serializers.ValidationError(
                    {"mandat": "Le mandat est obligatoire pour une entrée client."}
                )
            if not attrs.get("prestation"):
                raise serializers.ValidationError(
                    {"prestation": "La prestation est obligatoire pour une entrée client."}
                )
            # Les entrées client sont facturables par défaut
        else:
            if not attrs.get("categorie"):
                raise serializers.ValidationError(
                    {"categorie": "La catégorie est obligatoire pour le temps interne ou les absences."}
                )
            # Les entrées internes/absences ne sont jamais facturables
            attrs["facturable"] = False
        return attrs


class FactureListSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    client_name = serializers.CharField(source="client.raison_sociale", read_only=True)
    devise_code = serializers.CharField(source="devise_id", read_only=True)
    regime_fiscal_code = serializers.CharField(
        source="regime_fiscal.code", read_only=True, default=None
    )
    est_simplifiee = serializers.BooleanField(read_only=True)

    class Meta:
        model = Facture
        fields = [
            "id",
            "numero_facture",
            "client_name",
            "date_emission",
            "date_echeance",
            "montant_ttc",
            "montant_restant",
            "statut",
            "statut_display",
            "devise_code",
            "regime_fiscal_code",
            "est_simplifiee",
        ]


class FactureDetailSerializer(serializers.ModelSerializer):
    client = ClientListSerializer(read_only=True)
    mandat = MandatListSerializer(read_only=True)
    est_simplifiee = serializers.BooleanField(read_only=True)

    class Meta:
        model = Facture
        fields = "__all__"


class LigneFactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneFacture
        fields = "__all__"


class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = "__all__"


class RelanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Relance
        fields = "__all__"


class TypePrestationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypePrestation
        fields = [
            "id",
            "code",
            "libelle",
            "description",
            "icone",
            "couleur",
            "ordre",
            "is_active",
        ]


class ZoneGeographiqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneGeographique
        fields = ["id", "nom", "description", "couleur"]


class TarifMandatSerializer(serializers.ModelSerializer):
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    prestation_libelle = serializers.CharField(
        source="prestation.libelle", read_only=True
    )

    class Meta:
        model = TarifMandat
        fields = "__all__"
