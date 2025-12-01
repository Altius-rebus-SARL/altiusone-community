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
            "npa",
            "localite",
            "canton",
            "canton_display",
            "pays",
            "adresse_complete",
        ]

    def get_adresse_complete(self, obj):
        return str(obj)


class UserSerializer(serializers.ModelSerializer):
    """Serializer pour les utilisateurs"""

    role_display = serializers.CharField(source="get_role_display", read_only=True)
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


class MandatListSerializer(serializers.ModelSerializer):
    """Serializer léger pour liste de mandats"""

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

    type_mandat_display = serializers.CharField(
        source="get_type_mandat_display", read_only=True
    )
    periodicite_display = serializers.CharField(
        source="get_periodicite_display", read_only=True
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
        source="cloture_par.get_full_name", read_only=True
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
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)

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
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True)

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
