# facturation/serializers.py
from rest_framework import serializers
from .models import Prestation, TimeTracking, Facture, LigneFacture, Paiement, Relance
from core.serializers import MandatListSerializer, UserSerializer, ClientListSerializer


class PrestationSerializer(serializers.ModelSerializer):
    type_prestation_display = serializers.CharField(
        source="get_type_prestation_display", read_only=True
    )

    class Meta:
        model = Prestation
        fields = "__all__"


class TimeTrackingSerializer(serializers.ModelSerializer):
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    utilisateur_name = serializers.CharField(
        source="utilisateur.get_full_name", read_only=True
    )
    prestation_libelle = serializers.CharField(
        source="prestation.libelle", read_only=True
    )
    duree_heures = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )

    class Meta:
        model = TimeTracking
        fields = "__all__"


class FactureListSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    client_name = serializers.CharField(source="client.raison_sociale", read_only=True)
    devise_code = serializers.CharField(source="devise_id", read_only=True)
    regime_fiscal_code = serializers.CharField(
        source="regime_fiscal.code", read_only=True, default=None
    )

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
        ]


class FactureDetailSerializer(serializers.ModelSerializer):
    client = ClientListSerializer(read_only=True)
    mandat = MandatListSerializer(read_only=True)

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
