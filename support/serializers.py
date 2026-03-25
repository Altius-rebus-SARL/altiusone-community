from rest_framework import serializers
from .models import CategorieSupport, ArticleSupport, VideoTutoriel, Nouveaute


class CategorieSupportSerializer(serializers.ModelSerializer):
    nb_articles = serializers.IntegerField(source='articles.count', read_only=True)
    nb_videos = serializers.IntegerField(source='videos.count', read_only=True)

    class Meta:
        model = CategorieSupport
        fields = ['id', 'code', 'nom', 'description', 'icone', 'couleur', 'ordre', 'nb_articles', 'nb_videos']


class ArticleSupportSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)

    class Meta:
        model = ArticleSupport
        fields = ['id', 'categorie', 'categorie_nom', 'titre', 'slug', 'resume', 'contenu', 'module', 'ordre', 'publie', 'created_at']


class VideoTutorielSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)

    class Meta:
        model = VideoTutoriel
        fields = ['id', 'categorie', 'categorie_nom', 'titre', 'description', 'youtube_id', 'duree_secondes', 'module', 'ordre', 'publie', 'created_at']


class NouveauteSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_changement_display', read_only=True)

    class Meta:
        model = Nouveaute
        fields = ['id', 'version', 'date_publication', 'titre', 'contenu', 'type_changement', 'type_display', 'module', 'created_at']
