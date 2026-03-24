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
    # ENTREPRISES
    # ============================================================================
    path("entreprises/", views.EntrepriseListView.as_view(), name="entreprise-list"),
    path("entreprises/nouvelle/", views.EntrepriseCreateView.as_view(), name="entreprise-create"),
    path("entreprises/<uuid:pk>/", views.EntrepriseDetailView.as_view(), name="entreprise-detail"),
    path("entreprises/<uuid:pk>/modifier/", views.EntrepriseUpdateView.as_view(), name="entreprise-update"),
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
    path("taches/calendrier/", views.TacheCalendarView.as_view(), name="tache-calendar"),
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
    path("settings/2fa/setup/", views.TwoFactorSetupWebView.as_view(), name="2fa-setup"),
    path("settings/2fa/enable/", views.TwoFactorEnableWebView.as_view(), name="2fa-enable"),
    path("settings/2fa/disable/", views.TwoFactorDisableWebView.as_view(), name="2fa-disable"),
    # ============================================================================
    # DEVISES & TAUX DE CHANGE
    # ============================================================================
    path("devises/", views.DeviseListView.as_view(), name="devise-list"),
    # ============================================================================
    # PAGES STATIQUES
    # ============================================================================
    path("about/", views.AboutView.as_view(), name="about"),
    path("support/", views.SupportView.as_view(), name="support"),
    path(
        "support/submit/", views.submit_support_request, name="submit-support-request"
    ),
    # ============================================================================
    # LANGUE & DEVISE
    # ============================================================================
    path("set-language/", views.set_language, name="set-language"),
    path("set-devise/", views.set_devise, name="set-devise"),
    # ============================================================================
    # DOCUMENT STUDIO
    # ============================================================================
    path("api/modele-pdf/save/", views.modele_pdf_save, name="modele-pdf-save"),
    # ============================================================================
    # API AJAX
    # ============================================================================
    path(
        "api/taches/<uuid:pk>/statut/",
        views.tache_changer_statut,
        name="tache-changer-statut",
    ),
    path("api/taches/calendrier-events/", views.tache_calendar_events, name="tache-calendar-events"),
    path("api/taches/assignable-users/", views.api_get_assignable_users, name="tache-assignable-users"),
    path(
        "api/notifications/<uuid:pk>/lire/",
        views.notification_marquer_lue,
        name="notification-marquer-lue",
    ),
    path("api/stats-dashboard/", views.get_stats_dashboard, name="stats-dashboard"),
    path("api/dashboard-stats/", views.get_dashboard_stats, name="dashboard-stats"),
    path("api/omnibar-search/", views.omnibar_search, name="omnibar-search"),
    # ============================================================================
    # ADMINISTRATION - UTILISATEURS
    # ============================================================================
    path("admin/", views.AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin/utilisateurs/", views.UserListView.as_view(), name="admin-user-list"),
    path("admin/utilisateurs/nouveau/", views.UserCreateView.as_view(), name="admin-user-create"),
    path("admin/utilisateurs/<uuid:pk>/", views.UserDetailView.as_view(), name="admin-user-detail"),
    path("admin/utilisateurs/<uuid:pk>/modifier/", views.UserUpdateView.as_view(), name="admin-user-update"),
    path("admin/utilisateurs/<uuid:pk>/toggle-active/", views.user_toggle_active, name="admin-user-toggle-active"),
    path("admin/utilisateurs/<uuid:pk>/reset-password/", views.user_reset_password, name="admin-user-reset-password"),
    # ============================================================================
    # ADMINISTRATION - ROLES
    # ============================================================================
    path("admin/roles/", views.RoleListView.as_view(), name="admin-role-list"),
    path("admin/roles/nouveau/", views.RoleCreateView.as_view(), name="admin-role-create"),
    path("admin/roles/<uuid:pk>/", views.RoleDetailView.as_view(), name="admin-role-detail"),
    path("admin/roles/<uuid:pk>/modifier/", views.RoleUpdateView.as_view(), name="admin-role-update"),
    # ============================================================================
    # ADMINISTRATION - INVITATIONS
    # ============================================================================
    path("admin/invitations/", views.InvitationListView.as_view(), name="admin-invitation-list"),
    path("admin/invitations/staff/", views.InvitationStaffCreateView.as_view(), name="admin-invitation-staff-create"),
    path("admin/invitations/client/", views.InvitationClientCreateView.as_view(), name="admin-invitation-client-create"),
    path("admin/invitations/<uuid:pk>/", views.InvitationDetailView.as_view(), name="admin-invitation-detail"),
    path("admin/invitations/<uuid:pk>/resend/", views.invitation_resend, name="admin-invitation-resend"),
    path("admin/invitations/<uuid:pk>/cancel/", views.invitation_cancel, name="admin-invitation-cancel"),
    # ============================================================================
    # ADMINISTRATION - ACCES MANDATS
    # ============================================================================
    path("admin/acces-mandats/", views.AccesMandatListView.as_view(), name="admin-acces-mandat-list"),
    path("admin/acces-mandats/nouveau/", views.AccesMandatCreateView.as_view(), name="admin-acces-mandat-create"),
    path("admin/acces-mandats/<uuid:pk>/modifier/", views.AccesMandatUpdateView.as_view(), name="admin-acces-mandat-update"),
    path("admin/acces-mandats/<uuid:pk>/toggle/", views.acces_mandat_toggle, name="admin-acces-mandat-toggle"),
    # ============================================================================
    # ADMINISTRATION - COLLABORATEURS FIDUCIAIRE (PRESTATAIRES)
    # ============================================================================
    path("admin/collaborateurs/", views.CollaborateurFiduciaireListView.as_view(), name="admin-collaborateur-list"),
    path("admin/collaborateurs/nouveau/", views.CollaborateurFiduciaireCreateView.as_view(), name="admin-collaborateur-create"),
    path("admin/collaborateurs/<uuid:pk>/modifier/", views.CollaborateurFiduciaireUpdateView.as_view(), name="admin-collaborateur-update"),
    path("admin/collaborateurs/<uuid:pk>/toggle/", views.collaborateur_fiduciaire_toggle, name="admin-collaborateur-toggle"),
    # ============================================================================
    # INTÉGRATION IA (MCP)
    # ============================================================================
    path("configuration/mcp/", views.mcp_setup_view, name="mcp-setup"),
    path("configuration/mcp/generate-token/", views.mcp_generate_token, name="mcp-generate-token"),
    path("configuration/mcp/revoke-token/", views.mcp_revoke_token, name="mcp-revoke-token"),
    # ============================================================================
    # CONFIGURATION METIER (Paramètres configurables)
    # ============================================================================
    path("configuration/", views.configuration_index, name="configuration"),
    path(
        "configuration/<str:module>/<str:categorie>/",
        views.configuration_list_partial,
        name="configuration-list",
    ),
    path(
        "configuration/<str:module>/<str:categorie>/nouveau/",
        views.configuration_create,
        name="configuration-create",
    ),
    path(
        "configuration/<str:module>/<str:categorie>/reorder/",
        views.configuration_reorder,
        name="configuration-reorder",
    ),
    path(
        "configuration/param/<uuid:pk>/modifier/",
        views.configuration_update,
        name="configuration-update",
    ),
    path(
        "configuration/param/<uuid:pk>/supprimer/",
        views.configuration_delete,
        name="configuration-delete",
    ),
    path(
        "configuration/param/<uuid:pk>/toggle/",
        views.configuration_toggle,
        name="configuration-toggle",
    ),
    path(
        "api/quick-create/<str:model_type>/",
        views.quick_create_reference,
        name="quick-create-reference",
    ),
    # ============================================================================
    # INVITATIONS CLIENT (accessible par les clients responsables)
    # ============================================================================
    path("mes-invitations/", views.MesInvitationsView.as_view(), name="mes-invitations"),
    path("mes-invitations/<uuid:mandat_pk>/inviter/", views.ClientInvitationCreateView.as_view(), name="client-invitation-create"),
    path("mes-invitations/<uuid:pk>/annuler/", views.client_invitation_cancel, name="client-invitation-cancel"),
    # ============================================================================
    # ACCEPTATION INVITATION (PUBLIQUE)
    # ============================================================================
    path("invitation/code/", views.AcceptInvitationByCodeView.as_view(), name="invitation-accept-code"),
    path("invitation/<str:token>/", views.AcceptInvitationView.as_view(), name="invitation-accept"),
    # ============================================================================
    # CHANGEMENT MOT DE PASSE OBLIGATOIRE
    # ============================================================================
    path("force-password-change/", views.ForcePasswordChangeView.as_view(), name="force-password-change"),
    # ============================================================================
    # CONTRATS
    # ============================================================================
    path("contrats/", views.ContratListView.as_view(), name="contrat-list"),
    path("contrats/nouveau/", views.ContratCreateView.as_view(), name="contrat-create"),
    path("contrats/<uuid:pk>/", views.ContratDetailView.as_view(), name="contrat-detail"),
    path("contrats/<uuid:pk>/modifier/", views.ContratUpdateView.as_view(), name="contrat-update"),
    path("modeles-contrat/", views.ModeleContratListView.as_view(), name="modele-contrat-list"),
    # ============================================================================
    # GRAPHE RELATIONNEL
    # ============================================================================
    path("graphe/", views.GraphView.as_view(), name="graph"),
    path("graphe/<str:type>/<uuid:pk>/", views.GraphView.as_view(), name="graph-centered"),
    path("api/graphe/", views.GraphAPIView.as_view(), name="graph-api"),
    path("api/graphe/<str:type>/<uuid:pk>/", views.GraphAPIView.as_view(), name="graph-api-centered"),
    path("api/graphe/stats/", views.GraphStatsAPIView.as_view(), name="graph-stats-api"),
]
