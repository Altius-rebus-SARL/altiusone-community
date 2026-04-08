# support/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import CategorieSupport, ArticleSupport, VideoTutoriel, Nouveaute


@register(CategorieSupport)
class CategorieSupportTranslationOptions(TranslationOptions):
    fields = ('nom', 'description')


@register(ArticleSupport)
class ArticleSupportTranslationOptions(TranslationOptions):
    fields = ('titre', 'resume', 'contenu')


@register(VideoTutoriel)
class VideoTutorielTranslationOptions(TranslationOptions):
    fields = ('titre', 'description')


@register(Nouveaute)
class NouveauteTranslationOptions(TranslationOptions):
    fields = ('titre', 'contenu')
