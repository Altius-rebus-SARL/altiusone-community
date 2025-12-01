# fiscalite/serializers.py
from rest_framework import serializers
from .models import (
    DeclarationFiscale,
    AnnexeFiscale,
    CorrectionFiscale,
    ReportPerte,
    TauxImposition,
    OptimisationFiscale,
)
from core.serializers import MandatListSerializer


class DeclarationFiscaleListSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    type_impot_display = serializers.CharField(
        source="get_type_impot_display", read_only=True
    )

    class Meta:
        model = DeclarationFiscale
        fields = [
            "id",
            "numero_declaration",
            "annee_fiscale",
            "type_impot",
            "type_impot_display",
            "statut",
            "statut_display",
            "impot_total",
        ]


class DeclarationFiscaleDetailSerializer(serializers.ModelSerializer):
    mandat = MandatListSerializer(read_only=True)

    class Meta:
        model = DeclarationFiscale
        fields = "__all__"


class AnnexeFiscaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnexeFiscale
        fields = "__all__"


class CorrectionFiscaleSerializer(serializers.ModelSerializer):
    type_correction_display = serializers.CharField(
        source="get_type_correction_display", read_only=True
    )

    class Meta:
        model = CorrectionFiscale
        fields = "__all__"


class ReportPerteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportPerte
        fields = "__all__"


class TauxImpositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TauxImposition
        fields = "__all__"


class OptimisationFiscaleSerializer(serializers.ModelSerializer):
    categorie_display = serializers.CharField(
        source="get_categorie_display", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = OptimisationFiscale
        fields = "__all__"
