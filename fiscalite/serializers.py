# fiscalite/serializers.py
from rest_framework import serializers
from .models import (
    DeclarationFiscale,
    AnnexeFiscale,
    CorrectionFiscale,
    ReportPerte,
    TauxImposition,
    OptimisationFiscale,
    ReclamationFiscale,
    UtilisationPerte,
    AcompteFiscal,
    ImpotAnticipe,
)
from core.serializers import MandatListSerializer


class DeclarationFiscaleListSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    type_impot_display = serializers.CharField(
        source="get_type_impot_display", read_only=True
    )

    regime_fiscal_display = serializers.StringRelatedField(
        source="regime_fiscal", read_only=True
    )

    class Meta:
        model = DeclarationFiscale
        fields = [
            "id",
            "numero_declaration",
            "annee_fiscale",
            "regime_fiscal",
            "regime_fiscal_display",
            "type_impot",
            "type_impot_display",
            "statut",
            "statut_display",
            "impot_total",
            "devise",
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


class ReclamationFiscaleSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    declaration_numero = serializers.CharField(
        source="declaration.numero_declaration", read_only=True
    )

    class Meta:
        model = ReclamationFiscale
        fields = "__all__"


class UtilisationPerteSerializer(serializers.ModelSerializer):
    report_annee_origine = serializers.IntegerField(
        source="report_perte.annee_origine", read_only=True
    )
    declaration_numero = serializers.CharField(
        source="declaration_fiscale.numero_declaration", read_only=True
    )

    class Meta:
        model = UtilisationPerte
        fields = "__all__"


class AcompteFiscalListSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_display = serializers.CharField(source='get_type_acompte_display', read_only=True)

    class Meta:
        model = AcompteFiscal
        fields = ['id', 'mandat', 'type_acompte', 'type_display', 'annee_fiscale',
                  'numero_acompte', 'date_echeance', 'montant', 'montant_paye',
                  'date_paiement', 'statut', 'statut_display']


class AcompteFiscalDetailSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_display = serializers.CharField(source='get_type_acompte_display', read_only=True)

    class Meta:
        model = AcompteFiscal
        fields = '__all__'


class ImpotAnticipeListSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_display = serializers.CharField(source='get_type_revenu_display', read_only=True)

    class Meta:
        model = ImpotAnticipe
        fields = ['id', 'mandat', 'type_revenu', 'type_display', 'annee',
                  'date_revenu', 'montant_brut', 'taux_retenue', 'montant_retenu',
                  'debiteur', 'statut', 'statut_display']


class ImpotAnticipeDetailSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_display = serializers.CharField(source='get_type_revenu_display', read_only=True)

    class Meta:
        model = ImpotAnticipe
        fields = '__all__'
