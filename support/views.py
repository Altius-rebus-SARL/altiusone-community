# support/views.py
"""Vues CBV pour le centre d'aide et support."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.views.generic import TemplateView, ListView, DetailView

from .models import CategorieSupport, ArticleSupport, VideoTutoriel, Nouveaute


# ========================================================================
# Hub principal
# ========================================================================

class SupportHubView(LoginRequiredMixin, TemplateView):
    """Page principale du centre d'aide -- 3 sections : Articles, Videos, Nouveautes."""

    template_name = 'support/hub.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = (
            CategorieSupport.objects
            .filter(is_active=True)
            .prefetch_related('articles', 'videos')
            .annotate(
                nb_articles=Count('articles', filter=Q(articles__publie=True, articles__is_active=True)),
                nb_videos=Count('videos', filter=Q(videos__publie=True, videos__is_active=True)),
            )
        )
        ctx['articles_recents'] = (
            ArticleSupport.objects
            .filter(publie=True, is_active=True)
            .select_related('categorie')
            .order_by('-created_at')[:5]
        )
        ctx['videos_recentes'] = (
            VideoTutoriel.objects
            .filter(publie=True, is_active=True)
            .select_related('categorie')
            .order_by('-created_at')[:4]
        )
        ctx['nouveautes'] = (
            Nouveaute.objects
            .filter(is_active=True)
            .order_by('-date_publication')[:10]
        )
        return ctx


# ========================================================================
# Articles
# ========================================================================

class ArticleListView(LoginRequiredMixin, ListView):
    """Liste des articles, filtrable par categorie ou module."""

    model = ArticleSupport
    template_name = 'support/article_list.html'
    context_object_name = 'articles'
    paginate_by = 20

    def get_queryset(self):
        qs = (
            ArticleSupport.objects
            .filter(publie=True, is_active=True)
            .select_related('categorie')
            .order_by('categorie__ordre', 'ordre', 'titre')
        )
        categorie = self.request.GET.get('categorie')
        if categorie:
            qs = qs.filter(categorie__code=categorie)
        module = self.request.GET.get('module')
        if module:
            qs = qs.filter(module=module)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(titre__icontains=q) | Q(resume__icontains=q) | Q(contenu__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = CategorieSupport.objects.filter(is_active=True)
        ctx['current_categorie'] = self.request.GET.get('categorie', '')
        ctx['current_module'] = self.request.GET.get('module', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ArticleDetailView(LoginRequiredMixin, DetailView):
    """Detail d'un article (contenu Markdown/HTML rendu)."""

    model = ArticleSupport
    template_name = 'support/article_detail.html'
    slug_field = 'slug'
    context_object_name = 'article'

    def get_queryset(self):
        return (
            ArticleSupport.objects
            .filter(publie=True, is_active=True)
            .select_related('categorie')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['related_articles'] = (
            ArticleSupport.objects
            .filter(
                publie=True,
                is_active=True,
                categorie=self.object.categorie,
            )
            .exclude(pk=self.object.pk)
            .order_by('ordre', 'titre')[:5]
        )
        return ctx


# ========================================================================
# Videos
# ========================================================================

class VideoListView(LoginRequiredMixin, ListView):
    """Liste des tutoriels video."""

    model = VideoTutoriel
    template_name = 'support/video_list.html'
    context_object_name = 'videos'
    paginate_by = 12

    def get_queryset(self):
        qs = (
            VideoTutoriel.objects
            .filter(publie=True, is_active=True)
            .select_related('categorie')
            .order_by('categorie__ordre', 'ordre')
        )
        categorie = self.request.GET.get('categorie')
        if categorie:
            qs = qs.filter(categorie__code=categorie)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(titre__icontains=q) | Q(description__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = CategorieSupport.objects.filter(is_active=True)
        ctx['current_categorie'] = self.request.GET.get('categorie', '')
        return ctx


# ========================================================================
# Nouveautes / Changelog
# ========================================================================

class NouveauteListView(LoginRequiredMixin, ListView):
    """Changelog / notes de version."""

    model = Nouveaute
    template_name = 'support/nouveaute_list.html'
    context_object_name = 'nouveautes'
    paginate_by = 30

    def get_queryset(self):
        return (
            Nouveaute.objects
            .filter(is_active=True)
            .order_by('-date_publication', '-version')
        )
