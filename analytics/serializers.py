# analytics/serializers.py
from rest_framework import serializers
from .models import (
    TableauBord,
    Indicateur,
    ValeurIndicateur,
    Rapport,
    PlanificationRapport,
    ComparaisonPeriode,
    AlerteMetrique,
    ExportDonnees,
)
from core.serializers import MandatListSerializer, UserSerializer


class TableauBordSerializer(serializers.ModelSerializer):
    visibilite_display = serializers.CharField(
        source="get_visibilite_display", read_only=True
    )
    proprietaire = UserSerializer(read_only=True)

    class Meta:
        model = TableauBord
        fields = "__all__"


class IndicateurSerializer(serializers.ModelSerializer):
    categorie_display = serializers.CharField(
        source="get_categorie_display", read_only=True
    )
    type_calcul_display = serializers.CharField(
        source="get_type_calcul_display", read_only=True
    )
    periodicite_display = serializers.CharField(
        source="get_periodicite_display", read_only=True
    )

    class Meta:
        model = Indicateur
        fields = "__all__"


class ValeurIndicateurSerializer(serializers.ModelSerializer):
    indicateur_nom = serializers.CharField(source="indicateur.nom", read_only=True)

    class Meta:
        model = ValeurIndicateur
        fields = "__all__"


class RapportListSerializer(serializers.ModelSerializer):
    type_rapport_display = serializers.CharField(
        source="get_type_rapport_display", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = Rapport
        fields = [
            "id",
            "nom",
            "type_rapport",
            "type_rapport_display",
            "date_generation",
            "statut",
            "statut_display",
            "format_fichier",
            "fichier",
        ]


class RapportDetailSerializer(serializers.ModelSerializer):
    mandat = MandatListSerializer(read_only=True)
    genere_par = UserSerializer(read_only=True)

    class Meta:
        model = Rapport
        fields = "__all__"


class PlanificationRapportSerializer(serializers.ModelSerializer):
    frequence_display = serializers.CharField(
        source="get_frequence_display", read_only=True
    )

    class Meta:
        model = PlanificationRapport
        fields = "__all__"


class ComparaisonPeriodeSerializer(serializers.ModelSerializer):
    type_comparaison_display = serializers.CharField(
        source="get_type_comparaison_display", read_only=True
    )

    class Meta:
        model = ComparaisonPeriode
        fields = "__all__"


class AlerteMetriqueSerializer(serializers.ModelSerializer):
    niveau_display = serializers.CharField(source="get_niveau_display", read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    indicateur_nom = serializers.CharField(source="indicateur.nom", read_only=True)

    class Meta:
        model = AlerteMetrique
        fields = "__all__"


class ExportDonneesSerializer(serializers.ModelSerializer):
    type_export_display = serializers.CharField(
        source="get_type_export_display", read_only=True
    )

    class Meta:
        model = ExportDonnees
        fields = "__all__"


