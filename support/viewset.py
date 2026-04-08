from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import CategorieSupport, ArticleSupport, VideoTutoriel, Nouveaute
from .serializers import (
    CategorieSupportSerializer,
    ArticleSupportSerializer,
    VideoTutorielSerializer,
    NouveauteSerializer,
)


class CategorieSupportViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les catégories de support (lecture seule)."""
    serializer_class = CategorieSupportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'description']
    ordering = ['ordre', 'nom']

    def get_queryset(self):
        return CategorieSupport.objects.filter(is_active=True)


class ArticleSupportViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les articles de support (lecture seule)."""
    serializer_class = ArticleSupportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categorie', 'module', 'publie']
    search_fields = ['titre', 'resume', 'contenu']
    ordering = ['categorie', 'ordre', 'titre']

    def get_queryset(self):
        return ArticleSupport.objects.filter(
            is_active=True, publie=True
        ).select_related('categorie')


class VideoTutorielViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les tutoriels vidéo (lecture seule)."""
    serializer_class = VideoTutorielSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categorie', 'module', 'publie']
    search_fields = ['titre', 'description']
    ordering = ['categorie', 'ordre']

    def get_queryset(self):
        return VideoTutoriel.objects.filter(
            is_active=True, publie=True
        ).select_related('categorie')


class NouveauteViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les nouveautés / changelog (lecture seule)."""
    serializer_class = NouveauteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_changement', 'module', 'version']
    search_fields = ['titre', 'contenu']
    ordering = ['-date_publication', '-version']

    def get_queryset(self):
        return Nouveaute.objects.filter(is_active=True)
