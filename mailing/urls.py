# mailing/urls.py
from django.urls import path
from . import views

app_name = "mailing"

urlpatterns = [
    # ============================================================================
    # CONFIGURATIONS EMAIL
    # ============================================================================
    path("configurations/", views.ConfigurationListView.as_view(), name="configuration-list"),
    path("configurations/nouveau/", views.ConfigurationCreateView.as_view(), name="configuration-create"),
    path("configurations/<uuid:pk>/", views.ConfigurationDetailView.as_view(), name="configuration-detail"),
    path("configurations/<uuid:pk>/modifier/", views.ConfigurationUpdateView.as_view(), name="configuration-update"),
    path("configurations/<uuid:pk>/test/", views.configuration_test, name="configuration-test"),

    # ============================================================================
    # TEMPLATES EMAIL
    # ============================================================================
    path("templates/", views.TemplateListView.as_view(), name="template-list"),
    path("templates/nouveau/", views.TemplateCreateView.as_view(), name="template-create"),
    path("templates/<uuid:pk>/", views.TemplateDetailView.as_view(), name="template-detail"),
    path("templates/<uuid:pk>/modifier/", views.TemplateUpdateView.as_view(), name="template-update"),
    path("templates/<uuid:pk>/preview/", views.template_preview, name="template-preview"),

    # ============================================================================
    # EMAILS ENVOYES
    # ============================================================================
    path("envoyes/", views.EmailEnvoyeListView.as_view(), name="email-envoye-list"),
    path("envoyes/<uuid:pk>/", views.EmailEnvoyeDetailView.as_view(), name="email-envoye-detail"),
    path("envoyes/<uuid:pk>/renvoyer/", views.email_renvoyer, name="email-renvoyer"),

    # ============================================================================
    # EMAILS RECUS
    # ============================================================================
    path("recus/", views.EmailRecuListView.as_view(), name="email-recu-list"),
    path("recus/<uuid:pk>/", views.EmailRecuDetailView.as_view(), name="email-recu-detail"),
    path("recus/<uuid:pk>/analyser/", views.email_analyser, name="email-analyser"),
    path("recus/fetch/", views.emails_fetch, name="emails-fetch"),

    # ============================================================================
    # COMPOSER EMAIL
    # ============================================================================
    path("composer/", views.email_compose, name="email-compose"),
]
