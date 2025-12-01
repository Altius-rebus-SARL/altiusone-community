# tva/serializers.py
from rest_framework import serializers
from .models import (
    ConfigurationTVA,
    TauxTVA,
    CodeTVA,
    DeclarationTVA,
    LigneTVA,
    OperationTVA,
    CorrectionTVA,
)
from core.serializers import MandatListSerializer, UserSerializer


class ConfigurationTVASerializer(serializers.ModelSerializer):
    """Serializer pour la configuration TVA"""

    methode_calcul_display = serializers.CharField(
        source="get_methode_calcul_display", read_only=True
    )
    periodicite_display = serializers.CharField(
        source="get_periodicite_display", read_only=True
    )
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)

    class Meta:
        model = ConfigurationTVA
        fields = "__all__"


class TauxTVASerializer(serializers.ModelSerializer):
    """Serializer pour les taux de TVA"""

    type_taux_display = serializers.CharField(
        source="get_type_taux_display", read_only=True
    )
    actif = serializers.SerializerMethodField()

    class Meta:
        model = TauxTVA
        fields = [
            "id",
            "type_taux",
            "type_taux_display",
            "taux",
            "date_debut",
            "date_fin",
            "description",
            "actif",
            "created_at",
        ]

    def get_actif(self, obj):
        from datetime import date

        today = date.today()
        if obj.date_fin:
            return obj.date_debut <= today <= obj.date_fin
        return obj.date_debut <= today


class CodeTVASerializer(serializers.ModelSerializer):
    """Serializer pour les codes TVA"""

    categorie_display = serializers.CharField(
        source="get_categorie_display", read_only=True
    )
    taux_applicable_detail = TauxTVASerializer(source="taux_applicable", read_only=True)

    class Meta:
        model = CodeTVA
        fields = [
            "id",
            "code",
            "libelle",
            "categorie",
            "categorie_display",
            "ordre_affichage",
            "taux_applicable",
            "taux_applicable_detail",
            "formule",
            "actif",
            "description",
        ]


class DeclarationTVAListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de déclarations TVA"""

    type_decompte_display = serializers.CharField(
        source="get_type_decompte_display", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    periode = serializers.SerializerMethodField()

    class Meta:
        model = DeclarationTVA
        fields = [
            "id",
            "numero_declaration",
            "mandat",
            "mandat_numero",
            "annee",
            "trimestre",
            "semestre",
            "periode",
            "type_decompte",
            "type_decompte_display",
            "statut",
            "statut_display",
            "solde_tva",
            "date_echeance_paiement",
            "created_at",
        ]

    def get_periode(self, obj):
        if obj.trimestre:
            return f"{obj.annee} T{obj.trimestre}"
        return f"{obj.annee} S{obj.semestre}"


class DeclarationTVADetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une déclaration TVA"""

    type_decompte_display = serializers.CharField(
        source="get_type_decompte_display", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    mandat = MandatListSerializer(read_only=True)
    valide_par = UserSerializer(read_only=True)
    soumis_par = UserSerializer(read_only=True)

    class Meta:
        model = DeclarationTVA
        fields = "__all__"


class LigneTVASerializer(serializers.ModelSerializer):
    """Serializer pour les lignes TVA"""

    code_tva_detail = CodeTVASerializer(source="code_tva", read_only=True)

    class Meta:
        model = LigneTVA
        fields = [
            "id",
            "declaration",
            "code_tva",
            "code_tva_detail",
            "base_imposable",
            "taux_tva",
            "montant_tva",
            "libelle",
            "description",
            "calcul_automatique",
            "ordre",
        ]


class OperationTVASerializer(serializers.ModelSerializer):
    """Serializer pour les opérations TVA"""

    type_operation_display = serializers.CharField(
        source="get_type_operation_display", read_only=True
    )
    code_tva_detail = CodeTVASerializer(source="code_tva", read_only=True)
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)

    class Meta:
        model = OperationTVA
        fields = [
            "id",
            "mandat",
            "mandat_numero",
            "declaration_tva",
            "ecriture_comptable",
            "date_operation",
            "type_operation",
            "type_operation_display",
            "montant_ht",
            "code_tva",
            "code_tva_detail",
            "taux_tva",
            "montant_tva",
            "montant_ttc",
            "tiers",
            "numero_tva_tiers",
            "numero_facture",
            "libelle",
            "integre_declaration",
            "date_integration",
            "created_at",
        ]


class CorrectionTVASerializer(serializers.ModelSerializer):
    """Serializer pour les corrections TVA"""

    type_correction_display = serializers.CharField(
        source="get_type_correction_display", read_only=True
    )
    code_tva_detail = CodeTVASerializer(source="code_tva", read_only=True)

    class Meta:
        model = CorrectionTVA
        fields = [
            "id",
            "declaration",
            "type_correction",
            "type_correction_display",
            "code_tva",
            "code_tva_detail",
            "base_calcul",
            "taux",
            "montant_correction",
            "description",
            "justification",
        ]
