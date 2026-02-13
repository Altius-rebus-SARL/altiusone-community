# graph/serializers.py
from rest_framework import serializers
from .models import OntologieType, Entite, Relation, Anomalie, RequeteSauvegardee


class OntologieTypeSerializer(serializers.ModelSerializer):
    categorie_display = serializers.CharField(
        source='get_categorie_display', read_only=True,
    )

    class Meta:
        model = OntologieType
        fields = [
            'id', 'categorie', 'categorie_display',
            'nom', 'nom_pluriel', 'description',
            'icone', 'couleur',
            'schema_attributs',
            'source_types_autorises', 'cible_types_autorises',
            'verbe', 'verbe_inverse', 'bidirectionnel',
            'ordre_affichage',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EntiteListSerializer(serializers.ModelSerializer):
    type_nom = serializers.CharField(source='type.nom', read_only=True)
    couleur = serializers.CharField(source='type.couleur', read_only=True)
    icone = serializers.CharField(source='type.icone', read_only=True)
    source_display = serializers.CharField(
        source='get_source_display', read_only=True,
    )
    nb_relations = serializers.SerializerMethodField()

    class Meta:
        model = Entite
        fields = [
            'id', 'nom', 'type', 'type_nom',
            'couleur', 'icone',
            'source', 'source_display',
            'confiance', 'verifie',
            'nb_relations',
            'created_at',
        ]

    def get_nb_relations(self, obj):
        return (
            obj.relations_sortantes.filter(is_active=True).count()
            + obj.relations_entrantes.filter(is_active=True).count()
        )


class EntiteDetailSerializer(serializers.ModelSerializer):
    type_nom = serializers.CharField(source='type.nom', read_only=True)
    type_schema = serializers.JSONField(
        source='type.schema_attributs', read_only=True,
    )
    couleur = serializers.CharField(source='type.couleur', read_only=True)
    icone = serializers.CharField(source='type.icone', read_only=True)
    source_display = serializers.CharField(
        source='get_source_display', read_only=True,
    )
    relations_sortantes = serializers.SerializerMethodField()
    relations_entrantes = serializers.SerializerMethodField()
    anomalies = serializers.SerializerMethodField()
    geom_coords = serializers.SerializerMethodField()

    class Meta:
        model = Entite
        fields = [
            'id', 'nom', 'description',
            'type', 'type_nom', 'type_schema',
            'couleur', 'icone',
            'attributs', 'tags',
            'source', 'source_display',
            'confiance', 'verifie', 'verifie_par', 'verifie_at',
            'geom_coords',
            'content_type', 'object_id',
            'relations_sortantes', 'relations_entrantes',
            'anomalies',
            'is_active', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_relations_sortantes(self, obj):
        rels = obj.relations_sortantes.filter(is_active=True).select_related(
            'type', 'cible__type',
        )[:20]
        return RelationSerializer(rels, many=True).data

    def get_relations_entrantes(self, obj):
        rels = obj.relations_entrantes.filter(is_active=True).select_related(
            'type', 'source__type',
        )[:20]
        return RelationSerializer(rels, many=True).data

    def get_anomalies(self, obj):
        anomalies = obj.anomalies.filter(
            statut__in=['nouveau', 'en_cours'],
        )[:10]
        return AnomalieSerializer(anomalies, many=True).data

    def get_geom_coords(self, obj):
        if obj.geom:
            return {'lat': obj.geom.y, 'lng': obj.geom.x}
        return None


class RelationSerializer(serializers.ModelSerializer):
    type_nom = serializers.CharField(source='type.nom', read_only=True)
    verbe = serializers.CharField(source='type.verbe', read_only=True)
    source_nom = serializers.CharField(source='source.nom', read_only=True)
    cible_nom = serializers.CharField(source='cible.nom', read_only=True)
    source_type_nom = serializers.CharField(
        source='source.type.nom', read_only=True,
    )
    cible_type_nom = serializers.CharField(
        source='cible.type.nom', read_only=True,
    )

    class Meta:
        model = Relation
        fields = [
            'id', 'type', 'type_nom', 'verbe',
            'source', 'source_nom', 'source_type_nom',
            'cible', 'cible_nom', 'cible_type_nom',
            'attributs', 'poids',
            'date_debut', 'date_fin', 'en_cours',
            'document_preuve', 'confiance',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnomalieSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(
        source='get_type_display', read_only=True,
    )
    statut_display = serializers.CharField(
        source='get_statut_display', read_only=True,
    )
    entite_nom = serializers.CharField(source='entite.nom', read_only=True)
    entite_liee_nom = serializers.CharField(
        source='entite_liee.nom', read_only=True, default=None,
    )

    class Meta:
        model = Anomalie
        fields = [
            'id', 'type', 'type_display',
            'entite', 'entite_nom',
            'entite_liee', 'entite_liee_nom',
            'titre', 'description', 'score', 'details',
            'statut', 'statut_display',
            'traite_par', 'traite_at', 'commentaire_resolution',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnomalieTraiterSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=[
        ('en_cours', 'En cours'),
        ('confirme', 'Confirmé'),
        ('rejete', 'Rejeté'),
        ('resolu', 'Résolu'),
    ])
    commentaire = serializers.CharField(required=False, allow_blank=True)


class RequeteSauvegardeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequeteSauvegardee
        fields = [
            'id', 'nom', 'description',
            'entite_depart',
            'types_entites', 'types_relations',
            'profondeur',
            'date_min', 'date_max',
            'parametres_vue', 'partage',
            'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class GrapheExploreSerializer(serializers.Serializer):
    """Sérialiseur pour les paramètres d'exploration du graphe."""
    entite_id = serializers.UUIDField()
    profondeur = serializers.IntegerField(default=2, min_value=1, max_value=10)
    types_entites = serializers.ListField(
        child=serializers.UUIDField(), required=False,
    )
    types_relations = serializers.ListField(
        child=serializers.UUIDField(), required=False,
    )
    date_min = serializers.DateField(required=False)
    date_max = serializers.DateField(required=False)
    confiance_min = serializers.FloatField(default=0.0, min_value=0.0, max_value=1.0)


class RechercheSemantiquSerializer(serializers.Serializer):
    """Sérialiseur pour la recherche sémantique."""
    query = serializers.CharField(max_length=500)
    types = serializers.ListField(
        child=serializers.UUIDField(), required=False,
    )
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)
