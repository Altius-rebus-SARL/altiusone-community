# core/views/__init__.py
"""
Vues du module core.
"""
from .export_views import (
    facture_export_pdf,
    facture_generate_qrbill,
    factures_export_csv,
    factures_export_excel,
    declaration_tva_export_xml,
    declaration_tva_export_pdf,
    declarations_tva_export_csv,
    balance_export,
    grand_livre_export_csv,
    fiches_salaire_export_csv,
    rapport_telecharger,
    export_telecharger,
)

from .main_views import (
    # Error handlers
    error_400,
    error_403,
    error_404,
    error_500,
    # Dashboard
    DashboardView,
    # Clients
    ClientListView,
    ClientDetailView,
    ClientCreateView,
    ClientUpdateView,
    # Mandats
    MandatListView,
    MandatDetailView,
    MandatCreateView,
    MandatUpdateView,
    # Tâches
    TacheListView,
    TacheDetailView,
    TacheCreateView,
    TacheUpdateView,
    tache_changer_statut,
    # Notifications
    NotificationListView,
    notification_marquer_lue,
    mark_all_notifications_read,
    notification_mark_read,
    # Recherche
    GlobalSearchView,
    omnibar_search,
    # Profil
    ProfileView,
    ProfileUpdateView,
    # Authentication
    CustomLoginView,
    SignUpView,
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView,
    logout_view,
    # Paramètres
    SettingsView,
    update_user_preferences,
    # Pages statiques
    AboutView,
    SupportView,
    submit_support_request,
    # Langue
    set_language,
    # API Dashboard
    get_stats_dashboard,
    get_dashboard_stats,
    # Exercices comptables
    ExerciceListView,
    ExerciceDetailView,
    ExerciceCreateView,
    ExerciceUpdateView,
    exercice_cloturer,
    # Devises
    DeviseListView,
)

from .graph_views import (
    GraphView,
    GraphAPIView,
    GraphStatsAPIView,
)

from .admin_views import (
    # Administration Dashboard
    AdminDashboardView,
    # Utilisateurs
    UserListView,
    UserDetailView,
    UserCreateView,
    UserUpdateView,
    user_toggle_active,
    user_reset_password,
    # Rôles
    RoleListView,
    RoleDetailView,
    RoleCreateView,
    RoleUpdateView,
    # Invitations
    InvitationListView,
    InvitationDetailView,
    InvitationStaffCreateView,
    InvitationClientCreateView,
    invitation_resend,
    invitation_cancel,
    AcceptInvitationView,
    # Accès Mandats
    AccesMandatListView,
    AccesMandatCreateView,
    AccesMandatUpdateView,
    acces_mandat_toggle,
    # Collaborateurs Fiduciaire (Prestataires)
    CollaborateurFiduciaireListView,
    CollaborateurFiduciaireCreateView,
    CollaborateurFiduciaireUpdateView,
    collaborateur_fiduciaire_toggle,
    # Changement mot de passe
    ForcePasswordChangeView,
)

__all__ = [
    # Error handlers
    'error_400',
    'error_403',
    'error_404',
    'error_500',
    # Export views
    'facture_export_pdf',
    'facture_generate_qrbill',
    'factures_export_csv',
    'factures_export_excel',
    'declaration_tva_export_xml',
    'declaration_tva_export_pdf',
    'declarations_tva_export_csv',
    'balance_export',
    'grand_livre_export_csv',
    'fiches_salaire_export_csv',
    'rapport_telecharger',
    'export_telecharger',
    # Dashboard
    'DashboardView',
    # Clients
    'ClientListView',
    'ClientDetailView',
    'ClientCreateView',
    'ClientUpdateView',
    # Mandats
    'MandatListView',
    'MandatDetailView',
    'MandatCreateView',
    'MandatUpdateView',
    # Tâches
    'TacheListView',
    'TacheDetailView',
    'TacheCreateView',
    'TacheUpdateView',
    'tache_changer_statut',
    # Notifications
    'NotificationListView',
    'notification_marquer_lue',
    'mark_all_notifications_read',
    'notification_mark_read',
    # Recherche
    'GlobalSearchView',
    'omnibar_search',
    # Profil
    'ProfileView',
    'ProfileUpdateView',
    # Authentication
    'CustomLoginView',
    'SignUpView',
    'CustomPasswordResetView',
    'CustomPasswordResetDoneView',
    'CustomPasswordResetConfirmView',
    'CustomPasswordResetCompleteView',
    'logout_view',
    # Paramètres
    'SettingsView',
    'update_user_preferences',
    # Pages statiques
    'AboutView',
    'SupportView',
    'submit_support_request',
    # Langue
    'set_language',
    # API Dashboard
    'get_stats_dashboard',
    'get_dashboard_stats',
    # Exercices comptables
    'ExerciceListView',
    'ExerciceDetailView',
    'ExerciceCreateView',
    'ExerciceUpdateView',
    'exercice_cloturer',
    # Devises
    'DeviseListView',
    # Administration
    'AdminDashboardView',
    'UserListView',
    'UserDetailView',
    'UserCreateView',
    'UserUpdateView',
    'user_toggle_active',
    'user_reset_password',
    'RoleListView',
    'RoleDetailView',
    'RoleCreateView',
    'RoleUpdateView',
    'InvitationListView',
    'InvitationDetailView',
    'InvitationStaffCreateView',
    'InvitationClientCreateView',
    'invitation_resend',
    'invitation_cancel',
    'AcceptInvitationView',
    'AccesMandatListView',
    'AccesMandatCreateView',
    'AccesMandatUpdateView',
    'acces_mandat_toggle',
    'CollaborateurFiduciaireListView',
    'CollaborateurFiduciaireCreateView',
    'CollaborateurFiduciaireUpdateView',
    'collaborateur_fiduciaire_toggle',
    'ForcePasswordChangeView',
    # Graphe
    'GraphView',
    'GraphAPIView',
    'GraphStatsAPIView',
]