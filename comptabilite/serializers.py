# comptabilite/serializers.py
from rest_framework import serializers
from decimal import Decimal
from .models import (
    PlanComptable,
    Compte,
    Journal,
    EcritureComptable,
    PieceComptable,
    Lettrage,
)
from core.serializers import MandatListSerializer, UserSerializer


class PlanComptableSerializer(serializers.ModelSerializer):
    """Serializer pour les plans comptables"""

    type_plan_display = serializers.CharField(
        source="get_type_plan_display", read_only=True
    )
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    nombre_comptes = serializers.SerializerMethodField()

    class Meta:
        model = PlanComptable
        fields = [
            "id",
            "nom",
            "type_plan",
            "type_plan_display",
            "description",
            "is_template",
            "mandat",
            "mandat_numero",
            "base_sur",
            "nombre_comptes",
            "created_at",
            "updated_at",
        ]

    def get_nombre_comptes(self, obj):
        return obj.comptes.count()


class CompteListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de comptes"""

    type_compte_display = serializers.CharField(
        source="get_type_compte_display", read_only=True
    )
    classe_display = serializers.CharField(source="get_classe_display", read_only=True)
    solde_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Compte
        fields = [
            "id",
            "numero",
            "libelle",
            "libelle_court",
            "type_compte",
            "type_compte_display",
            "classe",
            "classe_display",
            "niveau",
            "est_collectif",
            "imputable",
            "solde_debit",
            "solde_credit",
            "solde_formatted",
        ]

    def get_solde_formatted(self, obj):
        return obj.get_solde_display()


class CompteDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un compte"""

    type_compte_display = serializers.CharField(
        source="get_type_compte_display", read_only=True
    )
    classe_display = serializers.CharField(source="get_classe_display", read_only=True)
    plan_comptable_nom = serializers.CharField(
        source="plan_comptable.nom", read_only=True
    )
    compte_parent_libelle = serializers.CharField(
        source="compte_parent.libelle", read_only=True
    )
    solde_formatted = serializers.SerializerMethodField()
    sous_comptes_count = serializers.SerializerMethodField()

    class Meta:
        model = Compte
        fields = "__all__"

    def get_solde_formatted(self, obj):
        return obj.get_solde_display()

    def get_sous_comptes_count(self, obj):
        return obj.sous_comptes.count()


class JournalSerializer(serializers.ModelSerializer):
    """Serializer pour les journaux"""

    type_journal_display = serializers.CharField(
        source="get_type_journal_display", read_only=True
    )
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    compte_contrepartie = CompteListSerializer(
        source="compte_contrepartie_defaut", read_only=True
    )

    class Meta:
        model = Journal
        fields = [
            "id",
            "mandat",
            "mandat_numero",
            "code",
            "libelle",
            "type_journal",
            "type_journal_display",
            "compte_contrepartie",
            "numerotation_auto",
            "prefixe_piece",
            "dernier_numero",
            "created_at",
            "updated_at",
        ]


class EcritureComptableListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste d'écritures"""

    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    compte_numero = serializers.CharField(source="compte.numero", read_only=True)
    compte_libelle = serializers.CharField(source="compte.libelle", read_only=True)
    journal_code = serializers.CharField(source="journal.code", read_only=True)
    sens = serializers.CharField(read_only=True)
    montant = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = EcritureComptable
        fields = [
            "id",
            "numero_piece",
            "numero_ligne",
            "date_ecriture",
            "journal",
            "journal_code",
            "compte",
            "compte_numero",
            "compte_libelle",
            "libelle",
            "montant_debit",
            "montant_credit",
            "sens",
            "montant",
            "code_lettrage",
            "statut",
            "statut_display",
            "created_at",
        ]


class EcritureComptableDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une écriture"""

    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    mandat = MandatListSerializer(read_only=True)
    journal = JournalSerializer(read_only=True)
    compte = CompteDetailSerializer(read_only=True)
    valide_par_name = serializers.CharField(
        source="valide_par.get_full_name", read_only=True
    )
    sens = serializers.CharField(read_only=True)
    montant = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = EcritureComptable
        fields = "__all__"


class EcritureComptableCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une écriture"""

    class Meta:
        model = EcritureComptable
        fields = [
            "mandat",
            "exercice",
            "journal",
            "piece",
            "numero_piece",
            "numero_ligne",
            "date_ecriture",
            "date_valeur",
            "date_echeance",
            "compte",
            "compte_auxiliaire",
            "libelle",
            "libelle_complement",
            "montant_debit",
            "montant_credit",
            "devise",
            "taux_change",
            "code_tva",
            "tiers",
            "montant_tva",
            "piece_justificative",
        ]

    def validate(self, attrs):
        # Vérifier qu'une écriture a soit débit soit crédit
        if attrs.get("montant_debit", 0) and attrs.get("montant_credit", 0):
            raise serializers.ValidationError(
                "Une écriture ne peut pas avoir à la fois un débit et un crédit"
            )

        if not attrs.get("montant_debit", 0) and not attrs.get("montant_credit", 0):
            raise serializers.ValidationError(
                "Une écriture doit avoir soit un débit soit un crédit"
            )

        return attrs


class TypePieceComptableSerializer(serializers.ModelSerializer):
    """Serializer pour les types de pièces comptables"""

    class Meta:
        from .models import TypePieceComptable
        model = TypePieceComptable
        fields = [
            "id",
            "code",
            "libelle",
            "description",
            "categorie",
            "prefixe_numero",
            "dossier_classement",
            "ordre",
            "is_active",
        ]


class PieceComptableListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de pièces comptables"""

    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    client_nom = serializers.CharField(
        source="mandat.client.raison_sociale", read_only=True
    )
    journal_code = serializers.CharField(source="journal.code", read_only=True)
    type_piece_code = serializers.CharField(source="type_piece.code", read_only=True)
    type_piece_libelle = serializers.CharField(
        source="type_piece.libelle", read_only=True
    )
    dossier_nom = serializers.CharField(source="dossier.nom", read_only=True)
    nombre_documents = serializers.SerializerMethodField()

    class Meta:
        model = PieceComptable
        fields = [
            "id",
            "mandat",
            "mandat_numero",
            "client_nom",
            "journal",
            "journal_code",
            "type_piece",
            "type_piece_code",
            "type_piece_libelle",
            "numero_piece",
            "date_piece",
            "libelle",
            "reference_externe",
            "tiers_nom",
            "montant_ht",
            "montant_tva",
            "montant_ttc",
            "statut",
            "dossier",
            "dossier_nom",
            "nombre_documents",
            "created_at",
        ]

    def get_nombre_documents(self, obj):
        return obj.documents.count() if hasattr(obj, 'documents') else 0


class PieceComptableDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une pièce comptable"""

    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    client_nom = serializers.CharField(
        source="mandat.client.raison_sociale", read_only=True
    )
    journal = JournalSerializer(read_only=True)
    type_piece = TypePieceComptableSerializer(read_only=True)
    dossier_chemin = serializers.CharField(
        source="dossier.chemin_complet", read_only=True
    )
    valide_par_name = serializers.CharField(
        source="valide_par.get_full_name", read_only=True
    )
    ecritures = EcritureComptableListSerializer(many=True, read_only=True)
    documents = serializers.SerializerMethodField()

    class Meta:
        model = PieceComptable
        fields = [
            "id",
            "mandat",
            "mandat_numero",
            "client_nom",
            "journal",
            "type_piece",
            "numero_piece",
            "date_piece",
            "libelle",
            "reference_externe",
            "tiers_nom",
            "tiers_numero_tva",
            "montant_ht",
            "montant_tva",
            "montant_ttc",
            "total_debit",
            "total_credit",
            "equilibree",
            "statut",
            "dossier",
            "dossier_chemin",
            "valide_par",
            "valide_par_name",
            "date_validation",
            "ecritures",
            "documents",
            "created_at",
            "updated_at",
            "created_by",
        ]

    def get_documents(self, obj):
        """Retourne les documents justificatifs associés à cette pièce"""
        from documents.serializers import DocumentListSerializer
        return DocumentListSerializer(obj.documents_justificatifs.all(), many=True).data


class PieceComptableCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer/modifier une pièce comptable"""

    generer_numero = serializers.BooleanField(
        write_only=True, required=False, default=True
    )

    class Meta:
        model = PieceComptable
        fields = [
            "mandat",
            "journal",
            "type_piece",
            "numero_piece",
            "date_piece",
            "libelle",
            "reference_externe",
            "tiers_nom",
            "tiers_numero_tva",
            "montant_ht",
            "montant_tva",
            "montant_ttc",
            "dossier",
            "generer_numero",
        ]

    def validate(self, attrs):
        generer = attrs.pop('generer_numero', True)
        numero = attrs.get('numero_piece')

        if not generer and not numero:
            raise serializers.ValidationError({
                'numero_piece': "Le numéro de pièce est obligatoire si la génération automatique est désactivée"
            })

        # Stocker pour utiliser dans create/update
        self._generer_numero = generer
        return attrs

    def create(self, validated_data):
        instance = PieceComptable(**validated_data)

        if self._generer_numero and not instance.numero_piece:
            if instance.date_piece:
                instance.generer_numero()

        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class EcritureInlinePieceSerializer(serializers.Serializer):
    """Serializer pour une écriture inline lors de la création d'une pièce."""

    compte = serializers.PrimaryKeyRelatedField(queryset=Compte.objects.all())
    libelle = serializers.CharField(max_length=255)
    montant_debit = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0")
    )
    montant_credit = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0")
    )
    code_tva = serializers.CharField(max_length=10, required=False, allow_blank=True, default="")
    tiers = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate_tiers(self, value):
        if value is None:
            return None
        from core.models import Tiers
        try:
            return Tiers.objects.get(pk=value)
        except Tiers.DoesNotExist:
            raise serializers.ValidationError("Tiers non trouvé")

    def validate(self, attrs):
        debit = attrs.get("montant_debit", Decimal("0"))
        credit = attrs.get("montant_credit", Decimal("0"))

        if debit > 0 and credit > 0:
            raise serializers.ValidationError(
                "Une écriture ne peut pas avoir un montant au débit ET au crédit"
            )
        if debit == 0 and credit == 0:
            raise serializers.ValidationError(
                "Une écriture doit avoir un montant (débit ou crédit)"
            )
        return attrs


class PieceComptableCreateWithEcrituresSerializer(serializers.ModelSerializer):
    """Serializer pour créer une pièce comptable avec ses écritures inline."""

    generer_numero = serializers.BooleanField(
        write_only=True, required=False, default=True
    )
    ecritures = EcritureInlinePieceSerializer(many=True, write_only=True, required=False)
    numero_piece = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = PieceComptable
        fields = [
            "mandat",
            "journal",
            "type_piece",
            "numero_piece",
            "date_piece",
            "libelle",
            "reference_externe",
            "tiers_nom",
            "tiers_numero_tva",
            "montant_ht",
            "montant_tva",
            "montant_ttc",
            "dossier",
            "generer_numero",
            "ecritures",
        ]

    def validate(self, attrs):
        generer = attrs.pop('generer_numero', True)
        numero = attrs.get('numero_piece')

        if not generer and not numero:
            raise serializers.ValidationError({
                'numero_piece': "Le numéro de pièce est obligatoire si la génération automatique est désactivée"
            })

        self._generer_numero = generer

        # Valider l'équilibre des écritures
        ecritures_data = attrs.get('ecritures', [])
        if ecritures_data:
            total_debit = sum(e.get('montant_debit', Decimal('0')) for e in ecritures_data)
            total_credit = sum(e.get('montant_credit', Decimal('0')) for e in ecritures_data)
            if total_debit != total_credit:
                raise serializers.ValidationError({
                    'ecritures': f"La pièce n'est pas équilibrée : débit ({total_debit}) ≠ crédit ({total_credit})"
                })

        return attrs

    def create(self, validated_data):
        ecritures_data = validated_data.pop('ecritures', [])

        instance = PieceComptable(**validated_data)
        if self._generer_numero and not instance.numero_piece:
            if instance.date_piece:
                instance.generer_numero()
        instance.save()

        # Créer les écritures inline
        if ecritures_data:
            mandat = instance.mandat
            exercice = mandat.exercices.filter(statut='OUVERT').first()
            user = self.context.get('request', None)
            user = user.user if user else None

            # Le journal est auto-résolu par PieceComptable.save()
            journal = instance.journal

            for i, ecriture_data in enumerate(ecritures_data):
                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice,
                    journal=journal,
                    piece=instance,
                    numero_piece=instance.numero_piece,
                    numero_ligne=i + 1,
                    date_ecriture=instance.date_piece,
                    compte=ecriture_data['compte'],
                    libelle=ecriture_data['libelle'],
                    montant_debit=ecriture_data.get('montant_debit', Decimal('0')),
                    montant_credit=ecriture_data.get('montant_credit', Decimal('0')),
                    code_tva=ecriture_data.get('code_tva', ''),
                    tiers=ecriture_data.get('tiers'),
                    statut='BROUILLON',
                    created_by=user,
                )

            instance.calculer_equilibre()

        # Auto-classement
        if not instance.dossier and instance.type_piece:
            dossier_cible = instance.type_piece.dossier_classement
            if dossier_cible:
                from documents.models import Dossier
                from django.db.models import Q
                _mandat = instance.mandat
                dossier = Dossier.objects.filter(
                    Q(client=_mandat.client) | Q(mandat=_mandat),
                    nom=dossier_cible, is_active=True,
                ).first()
                if dossier:
                    instance.dossier = dossier
                    instance.save(update_fields=['dossier'])

        return instance


class PieceComptableSerializer(serializers.ModelSerializer):
    """Serializer standard pour les pièces comptables (compatibilité)"""

    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    journal = JournalSerializer(read_only=True)
    ecritures = EcritureComptableListSerializer(
        many=True, read_only=True, source="mandat.ecritures"
    )
    nombre_ecritures = serializers.SerializerMethodField()

    class Meta:
        model = PieceComptable
        fields = [
            "id",
            "mandat",
            "mandat_numero",
            "journal",
            "numero_piece",
            "date_piece",
            "libelle",
            "total_debit",
            "total_credit",
            "equilibree",
            "statut",
            "ecritures",
            "nombre_ecritures",
            "created_at",
            "updated_at",
        ]

    def get_nombre_ecritures(self, obj):
        return obj.mandat.ecritures.filter(numero_piece=obj.numero_piece).count()


class LettrageSerializer(serializers.ModelSerializer):
    """Serializer pour les lettrages"""

    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    compte = CompteListSerializer(read_only=True)
    lettre_par_name = serializers.CharField(
        source="lettre_par.get_full_name", read_only=True
    )
    nombre_ecritures = serializers.SerializerMethodField()

    class Meta:
        model = Lettrage
        fields = [
            "id",
            "mandat",
            "mandat_numero",
            "compte",
            "code_lettrage",
            "montant_total",
            "solde",
            "date_lettrage",
            "lettre_par",
            "lettre_par_name",
            "complet",
            "nombre_ecritures",
            "created_at",
        ]

    def get_nombre_ecritures(self, obj):
        return EcritureComptable.objects.filter(code_lettrage=obj.code_lettrage).count()


class BalanceSerializer(serializers.Serializer):
    """Serializer pour la balance comptable"""

    compte = CompteListSerializer()
    solde_debit_initial = serializers.DecimalField(max_digits=15, decimal_places=2)
    solde_credit_initial = serializers.DecimalField(max_digits=15, decimal_places=2)
    mouvements_debit = serializers.DecimalField(max_digits=15, decimal_places=2)
    mouvements_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    solde_debit_final = serializers.DecimalField(max_digits=15, decimal_places=2)
    solde_credit_final = serializers.DecimalField(max_digits=15, decimal_places=2)
    solde = serializers.DecimalField(max_digits=15, decimal_places=2)


class BilanSerializer(serializers.Serializer):
    """Serializer pour le bilan"""

    actif_circulant = serializers.DecimalField(max_digits=15, decimal_places=2)
    actif_immobilise = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_actif = serializers.DecimalField(max_digits=15, decimal_places=2)

    capitaux_tiers_ct = serializers.DecimalField(max_digits=15, decimal_places=2)
    capitaux_tiers_lt = serializers.DecimalField(max_digits=15, decimal_places=2)
    capitaux_propres = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_passif = serializers.DecimalField(max_digits=15, decimal_places=2)

    details = serializers.JSONField()


class CompteResultatsSerializer(serializers.Serializer):
    """Serializer pour le compte de résultats"""

    produits_exploitation = serializers.DecimalField(max_digits=15, decimal_places=2)
    charges_exploitation = serializers.DecimalField(max_digits=15, decimal_places=2)
    resultat_exploitation = serializers.DecimalField(max_digits=15, decimal_places=2)

    produits_financiers = serializers.DecimalField(max_digits=15, decimal_places=2)
    charges_financieres = serializers.DecimalField(max_digits=15, decimal_places=2)
    resultat_financier = serializers.DecimalField(max_digits=15, decimal_places=2)

    resultat_avant_impots = serializers.DecimalField(max_digits=15, decimal_places=2)
    impots = serializers.DecimalField(max_digits=15, decimal_places=2)
    resultat_net = serializers.DecimalField(max_digits=15, decimal_places=2)

    details = serializers.JSONField()
