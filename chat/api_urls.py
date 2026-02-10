from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, chat_ask_ai

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('', include(router.urls)),
    path('ask/', chat_ask_ai, name='chat-ask-ai'),
]
