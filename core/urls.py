# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "core"

urlpatterns = [
    # ============================================================================
    # AUTHENTIFICATION
    # ============================================================================
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    # Password reset URLs
    path(
        "password-reset/",
        views.CustomPasswordResetView.as_view(),
        name="password-reset",
    ),
    path(
        "password-reset/done/",
        views.CustomPasswordResetDoneView.as_view(),
        name="password-reset-done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        views.CustomPasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "password-reset-complete/",
        views.CustomPasswordResetCompleteView.as_view(),
        name="password-reset-complete",
    ),
    # ============================================================================
    # DASHBOARD
    # ============================================================================
    path("", views.DashboardView.as_view(), name="dashboard"),
    # ============================================================================
    # CLIENTS
    # ============================================================================
    path("clients/", views.ClientListView.as_view(), name="client-list"),
    path("clients/nouveau/", views.ClientCreateView.as_view(), name="client-create"),
    path("clients/<uuid:pk>/", views.ClientDetailView.as_view(), name="client-detail"),
    path(
        "clients/<uuid:pk>/modifier/",
        views.ClientUpdateView.as_view(),
        name="client-update",
    ),
    # ============================================================================
    # MANDATS
    # ============================================================================
    path("mandats/", views.MandatListView.as_view(), name="mandat-list"),
    path("mandats/nouveau/", views.MandatCreateView.as_view(), name="mandat-create"),
    path("mandats/<uuid:pk>/", views.MandatDetailView.as_view(), name="mandat-detail"),
    path(
        "mandats/<uuid:pk>/modifier/",
        views.MandatUpdateView.as_view(),
        name="mandat-update",
    ),
    # ============================================================================
    # EXERCICES COMPTABLES
    # ============================================================================
    path("exercices/", views.ExerciceListView.as_view(), name="exercice-list"),
    path(
        "exercices/nouveau/", views.ExerciceCreateView.as_view(), name="exercice-create"
    ),
    path(
        "exercices/<uuid:pk>/",
        views.ExerciceDetailView.as_view(),
        name="exercice-detail",
    ),
    path(
        "exercices/<uuid:pk>/modifier/",
        views.ExerciceUpdateView.as_view(),
        name="exercice-update",
    ),
    path(
        "exercices/<uuid:pk>/cloturer/",
        views.exercice_cloturer,
        name="exercice-cloturer",
    ),
    # ============================================================================
    # TÂCHES
    # ============================================================================
    path("taches/", views.TacheListView.as_view(), name="tache-list"),
    path("taches/nouvelle/", views.TacheCreateView.as_view(), name="tache-create"),
    path("taches/<uuid:pk>/", views.TacheDetailView.as_view(), name="tache-detail"),
    path(
        "taches/<uuid:pk>/modifier/",
        views.TacheUpdateView.as_view(),
        name="tache-update",
    ),
    # ============================================================================
    # RECHERCHE GLOBALE
    # ============================================================================
    path("search/", views.GlobalSearchView.as_view(), name="global-search"),
    # ============================================================================
    # NOTIFICATIONS
    # ============================================================================
    path(
        "notifications/",
        views.NotificationListView.as_view(),
        name="notifications-list",
    ),
    path(
        "notifications/mark-all-read/",
        views.mark_all_notifications_read,
        name="notifications-mark-all-read",
    ),
    path(
        "notifications/<uuid:pk>/mark-read/",
        views.notification_mark_read,
        name="notification-mark-read",
    ),
    # ============================================================================
    # PROFIL UTILISATEUR
    # ============================================================================
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="profile-update"),
    # ============================================================================
    # PARAMÈTRES
    # ============================================================================
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path(
        "settings/update-preferences/",
        views.update_user_preferences,
        name="update-preferences",
    ),
    # ============================================================================
    # PAGES STATIQUES
    # ============================================================================
    path("about/", views.AboutView.as_view(), name="about"),
    path("support/", views.SupportView.as_view(), name="support"),
    path(
        "support/submit/", views.submit_support_request, name="submit-support-request"
    ),
    # ============================================================================
    # LANGUE
    # ============================================================================
    path("set-language/", views.set_language, name="set-language"),
    # ============================================================================
    # API AJAX
    # ============================================================================
    path(
        "api/taches/<uuid:pk>/statut/",
        views.tache_changer_statut,
        name="tache-changer-statut",
    ),
    path(
        "api/notifications/<uuid:pk>/lire/",
        views.notification_marquer_lue,
        name="notification-marquer-lue",
    ),
    path("api/stats-dashboard/", views.get_stats_dashboard, name="stats-dashboard"),
    path("api/dashboard-stats/", views.get_dashboard_stats, name="dashboard-stats"),
]
