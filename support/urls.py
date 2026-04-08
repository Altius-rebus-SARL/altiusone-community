# support/urls.py
from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    path('', views.SupportHubView.as_view(), name='hub'),
    path('articles/', views.ArticleListView.as_view(), name='article-list'),
    path('articles/<slug:slug>/', views.ArticleDetailView.as_view(), name='article-detail'),
    path('videos/', views.VideoListView.as_view(), name='video-list'),
    path('nouveautes/', views.NouveauteListView.as_view(), name='nouveaute-list'),
]
