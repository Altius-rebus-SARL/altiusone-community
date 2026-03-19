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
    FichierJoint,
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
        source="responsable.get_full_name", read_only=True, default=""
    )
    nombre_mandats = serializers.SerializerMethodField()

    adresse_siege = AdresseSerializer(read_only=True)

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
            "adresse_siege",
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
    responsable_detail = UserSerializer(source="responsable", read_only=True)
    responsable = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True, type_utilisateur='STAFF'),
        required=False, allow_null=True,
    )
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

        # Default responsable to current user if not provided
        if "responsable" not in validated_data or validated_data["responsable"] is None:
            request = self.context.get("request")
            if request and request.user.type_utilisateur == 'STAFF':
                validated_data["responsable"] = request.user

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
        source="responsable.get_full_name", read_only=True, default=""
    )

    plan_comptable_id = serializers.UUIDField(
        source="plan_comptable_actif_id", read_only=True
    )
    plan_comptable_nom = serializers.CharField(
        source="plan_comptable.nom", read_only=True, default=None
    )

    class Meta:
        model = Mandat
        fields = [
            "id",
            "numero",
            "client",
            "client_name",
            # Plan comptable actif
            "plan_comptable_actif",
            "plan_comptable_id",
            "plan_comptable_nom",
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
    # Plan comptable actif (via property)
    plan_comptable_nom = serializers.CharField(
        source="plan_comptable.nom", read_only=True, default=None
    )
    plan_comptable_type = serializers.CharField(
        source="plan_comptable.type_plan.code", read_only=True, default=None
    )

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
    assignes = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )
    assignes_details = serializers.SerializerMethodField()
    cree_par_name = serializers.CharField(
        source="cree_par.get_full_name", read_only=True
    )
    mandat_numero = serializers.CharField(source="mandat.numero", read_only=True, allow_null=True, default=None)
    prestation_libelle = serializers.CharField(source="prestation.libelle", read_only=True, allow_null=True, default=None)

    class Meta:
        model = Tache
        fields = [
            "id",
            "titre",
            "description",
            "assignes",
            "assignes_details",
            "cree_par",
            "cree_par_name",
            "mandat",
            "mandat_numero",
            "prestation",
            "prestation_libelle",
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

    def get_assignes_details(self, obj):
        return [
            {"id": u.pk, "name": u.get_full_name() or u.username}
            for u in obj.assignes.all()
        ]


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


# =============================================================================
# SERIALIZERS POUR FICHIERS JOINTS (pièces jointes génériques)
# =============================================================================

class FichierJointListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des fichiers joints"""

    content_type_name = serializers.CharField(
        source="content_type.model", read_only=True
    )
    taille_formatee = serializers.SerializerMethodField()

    class Meta:
        model = FichierJoint
        fields = [
            "id",
            "content_type",
            "content_type_name",
            "object_id",
            "nom_original",
            "extension",
            "mime_type",
            "taille",
            "taille_formatee",
            "description",
            "ordre",
            "created_at",
        ]

    def get_taille_formatee(self, obj):
        if obj.taille < 1024:
            return f"{obj.taille} o"
        elif obj.taille < 1024 * 1024:
            return f"{obj.taille / 1024:.1f} Ko"
        return f"{obj.taille / (1024 * 1024):.1f} Mo"


class FichierJointDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un fichier joint"""

    content_type_name = serializers.CharField(
        source="content_type.model", read_only=True
    )
    url = serializers.SerializerMethodField()

    class Meta:
        model = FichierJoint
        fields = [
            "id",
            "content_type",
            "content_type_name",
            "object_id",
            "fichier",
            "url",
            "nom_original",
            "extension",
            "mime_type",
            "taille",
            "hash_fichier",
            "description",
            "ordre",
            "created_at",
            "updated_at",
        ]

    def get_url(self, obj):
        if obj.fichier:
            try:
                return obj.fichier.url
            except Exception:
                return None
        return None


class FichierJointUploadSerializer(serializers.ModelSerializer):
    """Serializer pour l'upload de fichiers joints"""

    fichier_base64 = serializers.CharField(write_only=True, required=False)
    fichier_nom = serializers.CharField(write_only=True, required=False)
    fichier_type = serializers.CharField(
        write_only=True, required=False, default="application/octet-stream"
    )

    class Meta:
        model = FichierJoint
        fields = [
            "id",
            "content_type",
            "object_id",
            "fichier",
            "fichier_base64",
            "fichier_nom",
            "fichier_type",
            "description",
            "ordre",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "fichier": {"required": False},
            "description": {"required": False},
            "ordre": {"required": False},
        }

    def validate(self, attrs):
        fichier = attrs.get("fichier")
        fichier_base64 = attrs.get("fichier_base64")
        fichier_nom = attrs.get("fichier_nom")

        if not fichier and not fichier_base64:
            raise serializers.ValidationError(
                {"fichier": "Un fichier est requis (fichier ou fichier_base64)"}
            )
        if fichier_base64 and not fichier_nom:
            raise serializers.ValidationError(
                {"fichier_nom": "Le nom du fichier est requis avec fichier_base64"}
            )
        return attrs

    def create(self, validated_data):
        import base64
        from django.core.files.base import ContentFile

        fichier_base64 = validated_data.pop("fichier_base64", None)
        fichier_nom = validated_data.pop("fichier_nom", None)
        fichier_type = validated_data.pop("fichier_type", "application/octet-stream")

        if fichier_base64:
            if ";base64," in fichier_base64:
                fichier_base64 = fichier_base64.split(";base64,")[1]
            file_content = base64.b64decode(fichier_base64)
            validated_data["fichier"] = ContentFile(file_content, name=fichier_nom)
            validated_data["nom_original"] = fichier_nom
            validated_data["mime_type"] = fichier_type

        return super().create(validated_data)

    def to_representation(self, instance):
        return FichierJointDetailSerializer(instance).data
