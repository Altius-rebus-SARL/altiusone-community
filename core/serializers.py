# core/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    User,
    Adresse,
    Client,
    Contact,
    Mandat,
    ExerciceComptable,
    AuditLog,
    Notification,
    Tache,
    TypeMandat,
    TypeFacturation,
    Periodicite,
    CollaborateurFiduciaire,
)

User = get_user_model()


class AdresseSerializer(serializers.ModelSerializer):
    """Serializer pour les adresses"""

    canton_display = serializers.CharField(source="get_canton_display", read_only=True)
    adresse_complete = serializers.SerializerMethodField()

    class Meta:
        model = Adresse
        fields = [
            "id",
            "rue",
            "numero",
            "complement",
            "code_postal",
            "localite",
            "region",
            "canton",
            "canton_display",
            "pays",
            "adresse_complete",
        ]

    def get_adresse_complete(self, obj):
        return obj.adresse_complete


class UserSerializer(serializers.ModelSerializer):
    """Serializer pour les utilisateurs"""

    role_display = serializers.CharField(source="get_role_display", read_only=True)
    role_code = serializers.SerializerMethodField()
    type_utilisateur_display = serializers.CharField(
        source="get_type_utilisateur_display", read_only=True
    )
    type_collaborateur_display = serializers.CharField(
        source="get_type_collaborateur_display", read_only=True
    )
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "role_display",
            "role_code",
            "type_utilisateur",
            "type_utilisateur_display",
            "type_collaborateur",
            "type_collaborateur_display",
            "phone",
            "mobile",
            "signature",
            "two_factor_enabled",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["date_joined", "last_login"]
        extra_kwargs = {"password": {"write_only": True}}

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_role_code(self, obj):
        return obj.role.code if obj.role else None


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création d'utilisateurs"""

    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
            "role",
            "phone",
            "mobile",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError("Les mots de passe ne correspondent pas")
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class ContactSerializer(serializers.ModelSerializer):
    """Serializer pour les contacts"""

    civilite_display = serializers.CharField(
        source="get_civilite_display", read_only=True
    )
    fonction_display = serializers.CharField(
        source="get_fonction_display", read_only=True
    )
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            "id",
            "client",
            "civilite",
            "civilite_display",
            "nom",
            "prenom",
            "nom_complet",
            "fonction",
            "fonction_display",
            "email",
            "telephone",
            "mobile",
            "principal",
            "created_at",
            "updated_at",
        ]

    def get_nom_complet(self, obj):
        return f"{obj.prenom} {obj.nom}"


class ClientListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de clients"""

    forme_juridique_display = serializers.CharField(
        source="get_forme_juridique_display", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    responsable_name = serializers.CharField(
        source="responsable.get_full_name", read_only=True
    )
    nombre_mandats = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "id",
            "raison_sociale",
            "nom_commercial",
            "forme_juridique",
            "forme_juridique_display",
            "ide_number",
            "ch_id",
            "ofrc_id",
            "siege",
            "canton_rc",
            "npa",
            "localite",
            "statut",
            "statut_display",
            "email",
            "telephone",
            "responsable",
            "responsable_name",
            "nombre_mandats",
            "created_at",
        ]

    def get_nombre_mandats(self, obj):
        return obj.mandats.filter(statut="ACTIF").count()


class ClientDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un client"""

    forme_juridique_display = serializers.CharField(
        source="get_forme_juridique_display", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    adresse_siege = AdresseSerializer()
    adresse_correspondance = AdresseSerializer(allow_null=True)
    contacts = ContactSerializer(many=True, read_only=True)
    responsable = UserSerializer(read_only=True)
    contact_principal = ContactSerializer(read_only=True)

    class Meta:
        model = Client
        fields = "__all__"

    def create(self, validated_data):
        adresse_siege_data = validated_data.pop("adresse_siege")
        adresse_correspondance_data = validated_data.pop("adresse_correspondance", None)

        adresse_siege = Adresse.objects.create(**adresse_siege_data)
        adresse_correspondance = None
        if adresse_correspondance_data:
            adresse_correspondance = Adresse.objects.create(
                **adresse_correspondance_data
            )

        client = Client.objects.create(
            adresse_siege=adresse_siege,
            adresse_correspondance=adresse_correspondance,
            **validated_data,
        )
        return client


# =============================================================================
# SERIALIZERS POUR LES TABLES DE RÉFÉRENCE
# =============================================================================

class PeriodiciteSerializer(serializers.ModelSerializer):
    """Serializer pour les périodicités"""

    class Meta:
        model = Periodicite
        fields = [
            "id",
            "code",
            "libelle",
            "description",
            "nombre_mois",
            "nombre_par_an",
            "ordre",
            "is_active",
        ]


class TypeMandatSerializer(serializers.ModelSerializer):
    """Serializer pour les types de mandats"""

    periodicite_defaut = PeriodiciteSerializer(read_only=True)

    class Meta:
        model = TypeMandat
        fields = [
            "id",
            "code",
            "libelle",
            "description",
            "icone",
            "couleur",
            "periodicite_defaut",
            "modules_actifs",
            "ordre",
            "is_active",
        ]


class TypeFacturationSerializer(serializers.ModelSerializer):
    """Serializer pour les types de facturation"""

    class Meta:
        model = TypeFacturation
        fields = [
            "id",
            "code",
            "libelle",
            "description",
            "necessite_forfait",
            "necessite_taux_horaire",
            "ordre",
            "is_active",
        ]


# =============================================================================
# SERIALIZERS POUR LES MANDATS
# =============================================================================

class MandatListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de mandats"""

    # Nouveaux champs (prioritaires)
    type_mandat_libelle = serializers.CharField(
        source="type_mandat_ref.libelle", read_only=True, allow_null=True, default=None
    )
    periodicite_libelle = serializers.CharField(
        source="periodicite_ref.libelle", read_only=True, allow_null=True, default=None
    )
    type_facturation_libelle = serializers.CharField(
        source="type_facturation_ref.libelle", read_only=True, allow_null=True, default=None
    )
    # Anciens champs (fallback)
    type_mandat_display = serializers.CharField(
        source="get_type_mandat_display", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    client_name = serializers.CharField(source="client.raison_sociale", read_only=True)
    responsable_name = serializers.CharField(
        source="responsable.get_full_name", read_only=True
    )

    class Meta:
        model = Mandat
        fields = [
            "id",
            "numero",
            "client",
            "client_name",
            # Nouveaux champs de référence
            "type_mandat_ref",
            "type_mandat_libelle",
            "periodicite_ref",
            "periodicite_libelle",
            "type_facturation_ref",
            "type_facturation_libelle",
            # Anciens champs (compatibilité)
            "type_mandat",
            "type_mandat_display",
            "date_debut",
            "date_fin",
            "statut",
            "statut_display",
            "responsable",
            "responsable_name",
            "created_at",
        ]


class MandatDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un mandat"""

    # Nouveaux champs avec serializers imbriqués
    type_mandat_ref_detail = TypeMandatSerializer(
        source="type_mandat_ref", read_only=True
    )
    periodicite_ref_detail = PeriodiciteSerializer(
        source="periodicite_ref", read_only=True
    )
    type_facturation_ref_detail = TypeFacturationSerializer(
        source="type_facturation_ref", read_only=True
    )
    # Anciens champs (fallback)
    type_mandat_display = serializers.CharField(
        source="get_type_mandat_display", read_only=True
    )
    periodicite_display = serializers.CharField(
        source="get_periodicite_display", read_only=True
    )
    type_facturation_display = serializers.CharField(
        source="get_type_facturation_display", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    client = ClientListSerializer(read_only=True)
    responsable = UserSerializer(read_only=True)
    equipe = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Mandat
        fields = "__all__"


class ExerciceComptableSerializer(serializers.ModelSerializer):
    """Serializer pour les exercices comptables"""

    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    cloture_par_name = serializers.CharField(
        source="cloture_par.get_full_name", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = ExerciceComptable
        fields = [
            "id",
            "mandat",
            "mandat_numero",
            "annee",
            "date_debut",
            "date_fin",
            "statut",
            "statut_display",
            "date_cloture",
            "cloture_par",
            "cloture_par_name",
            "resultat_exercice",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["date_cloture", "cloture_par"]


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer pour les logs d'audit"""

    utilisateur_name = serializers.CharField(
        source="utilisateur.get_full_name", read_only=True
    )
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "utilisateur",
            "utilisateur_name",
            "action",
            "action_display",
            "table_name",
            "object_id",
            "object_repr",
            "changements",
            "timestamp",
            "ip_address",
            "user_agent",
            "mandat",
            "mandat_numero",
        ]
        read_only_fields = ["timestamp"]


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications"""

    type_notification_display = serializers.CharField(
        source="get_type_notification_display", read_only=True
    )
    destinataire_name = serializers.CharField(
        source="destinataire.get_full_name", read_only=True
    )
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True, allow_null=True, default=None)

    class Meta:
        model = Notification
        fields = [
            "id",
            "destinataire",
            "destinataire_name",
            "type_notification",
            "type_notification_display",
            "titre",
            "message",
            "lien_action",
            "lien_texte",
            "lue",
            "date_lecture",
            "archivee",
            "mandat",
            "mandat_numero",
            "created_at",
        ]
        read_only_fields = ["created_at", "date_lecture"]


class TacheSerializer(serializers.ModelSerializer):
    """Serializer pour les tâches"""

    priorite_display = serializers.CharField(
        source="get_priorite_display", read_only=True
    )
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    assigne_a_name = serializers.CharField(
        source="assigne_a.get_full_name", read_only=True
    )
    cree_par_name = serializers.CharField(
        source="cree_par.get_full_name", read_only=True
    )
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True, allow_null=True, default=None)

    class Meta:
        model = Tache
        fields = [
            "id",
            "titre",
            "description",
            "assigne_a",
            "assigne_a_name",
            "cree_par",
            "cree_par_name",
            "mandat",
            "mandat_numero",
            "priorite",
            "priorite_display",
            "date_echeance",
            "statut",
            "statut_display",
            "date_debut",
            "date_fin",
            "temps_estime_heures",
            "temps_reel_heures",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["cree_par", "created_at"]


# =============================================================================
# SERIALIZERS POUR COLLABORATEURS FIDUCIAIRE
# =============================================================================

class CollaborateurFiduciaireListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste d'affectations prestataires"""

    utilisateur_name = serializers.CharField(
        source="utilisateur.get_full_name", read_only=True
    )
    utilisateur_email = serializers.CharField(
        source="utilisateur.email", read_only=True
    )
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)
    client_name = serializers.CharField(
        source="mandat.client.raison_sociale", read_only=True
    )

    class Meta:
        model = CollaborateurFiduciaire
        fields = [
            "id",
            "utilisateur",
            "utilisateur_name",
            "utilisateur_email",
            "mandat",
            "mandat_numero",
            "client_name",
            "role_sur_mandat",
            "date_debut",
            "date_fin",
            "is_active",
            "created_at",
        ]


class CollaborateurFiduciaireDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une affectation prestataire"""

    utilisateur = UserSerializer(read_only=True)
    mandat = MandatListSerializer(read_only=True)
    utilisateur_id = serializers.UUIDField(write_only=True)
    mandat_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = CollaborateurFiduciaire
        fields = [
            "id",
            "utilisateur",
            "utilisateur_id",
            "mandat",
            "mandat_id",
            "role_sur_mandat",
            "date_debut",
            "date_fin",
            "taux_horaire",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        utilisateur_id = validated_data.pop("utilisateur_id")
        mandat_id = validated_data.pop("mandat_id")
        validated_data["utilisateur_id"] = utilisateur_id
        validated_data["mandat_id"] = mandat_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Ne pas permettre de changer utilisateur/mandat sur update
        validated_data.pop("utilisateur_id", None)
        validated_data.pop("mandat_id", None)
        return super().update(instance, validated_data)
