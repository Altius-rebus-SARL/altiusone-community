from rest_framework.routers import DefaultRouter
from .viewset import (
    CategorieSupportViewSet,
    ArticleSupportViewSet,
    VideoTutorielViewSet,
    NouveauteViewSet,
)

router = DefaultRouter()
router.register(r"categories", CategorieSupportViewSet, basename="support-categorie")
router.register(r"articles", ArticleSupportViewSet, basename="support-article")
router.register(r"videos", VideoTutorielViewSet, basename="support-video")
router.register(r"nouveautes", NouveauteViewSet, basename="support-nouveaute")

urlpatterns = router.urls
