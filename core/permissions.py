# core/permissions.py
"""
Système de permissions métier pour AltiusOne.

Ce module définit les permissions métier claires et structurées pour l'application.
Le superadmin a tous les droits. Les autres rôles ont des permissions adaptées
aux fonctionnalités métier.
"""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import BasePermission, SAFE_METHODS
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _


# ============================================================================
# DÉFINITION DES PERMISSIONS MÉTIER
# ============================================================================

# Structure: {app_label: {codename: description}}
PERMISSIONS_METIER = {
    # ============ MODULE COMPTABILITÉ ============
    'comptabilite': {
        # Lecture
        'view_plan_comptable': _('Consulter le plan comptable'),
        'view_ecritures': _('Consulter les écritures comptables'),
        'view_journaux': _('Consulter les journaux'),
        'view_balance': _('Consulter la balance'),
        'view_grand_livre': _('Consulter le grand livre'),

        # Écriture
        'add_ecriture': _('Créer des écritures comptables'),
        'change_ecriture_brouillon': _('Modifier les écritures en brouillon'),
        'validate_ecriture': _('Valider les écritures comptables'),
        'delete_ecriture_brouillon': _('Supprimer les écritures en brouillon'),

        # Actions avancées
        'lettrage': _('Effectuer des lettrages'),
        'cloture_periode': _('Clôturer une période comptable'),
        'cloture_exercice': _('Clôturer un exercice'),
        'extourne': _('Créer des extournes'),
        'import_ecritures': _('Importer des écritures'),
        'export_comptabilite': _('Exporter les données comptables'),
    },

    # ============ MODULE FACTURATION ============
    'facturation': {
        # Lecture
        'view_factures': _('Consulter les factures'),
        'view_all_factures': _('Consulter toutes les factures (tous mandats)'),
        'view_prestations': _('Consulter les prestations'),
        'view_timetracking': _('Consulter le suivi du temps'),
        'view_all_timetracking': _('Consulter tout le suivi du temps'),
        'view_paiements': _('Consulter les paiements'),

        # Écriture
        'add_facture': _('Créer des factures'),
        'change_facture_brouillon': _('Modifier les factures en brouillon'),
        'validate_facture': _('Valider les factures'),
        'delete_facture_brouillon': _('Supprimer les factures en brouillon'),

        # Time tracking
        'add_timetracking': _('Saisir du temps'),
        'add_timetracking_autre': _('Saisir du temps pour un autre utilisateur'),
        'validate_timetracking': _('Valider les saisies de temps'),

        # Paiements
        'add_paiement': _('Enregistrer des paiements'),
        'validate_paiement': _('Valider des paiements'),

        # Actions avancées
        'create_avoir': _('Créer des avoirs'),
        'create_relance': _('Créer des relances'),
        'annuler_facture': _('Annuler des factures'),
        'export_factures': _('Exporter les factures'),
        'generate_qrbill': _('Générer les QR-Bill'),
    },

    # ============ MODULE TVA ============
    'tva': {
        # Lecture
        'view_declarations': _('Consulter les déclarations TVA'),
        'view_all_declarations': _('Consulter toutes les déclarations TVA'),
        'view_operations': _('Consulter les opérations TVA'),
        'view_all_operations': _('Consulter toutes les opérations TVA'),

        # Écriture
        'add_declaration': _('Créer des déclarations TVA'),
        'change_declaration_brouillon': _('Modifier les déclarations en brouillon'),
        'validate_declaration': _('Valider les déclarations TVA'),
        'delete_declaration_brouillon': _('Supprimer les déclarations en brouillon'),

        # Actions avancées
        'calcul_automatique': _('Calculer automatiquement la TVA'),
        'soumettre_afc': _('Soumettre à l\'AFC'),
        'add_correction': _('Ajouter des corrections TVA'),
        'export_tva': _('Exporter les données TVA'),
        'config_tva': _('Configurer la TVA d\'un mandat'),
    },

    # ============ MODULE SALAIRES ============
    'salaires': {
        # Lecture
        'view_fiches_salaire': _('Consulter les fiches de salaire'),
        'view_all_fiches': _('Consulter toutes les fiches de salaire'),
        'view_employes': _('Consulter les employés'),
        'view_cotisations': _('Consulter les cotisations'),

        # Écriture
        'add_fiche_salaire': _('Créer des fiches de salaire'),
        'change_fiche_brouillon': _('Modifier les fiches en brouillon'),
        'validate_fiche': _('Valider les fiches de salaire'),
        'delete_fiche_brouillon': _('Supprimer les fiches en brouillon'),

        # Actions avancées
        'calcul_salaires': _('Calculer les salaires'),
        'generate_certificat': _('Générer les certificats de salaire'),
        'declaration_avs': _('Déclarer à l\'AVS'),
        'declaration_lpp': _('Déclarer à la LPP'),
        'export_salaires': _('Exporter les données salaires'),
    },

    # ============ MODULE FISCALITÉ ============
    'fiscalite': {
        # Lecture
        'view_declarations_fiscales': _('Consulter les déclarations fiscales'),
        'view_all_declarations_fiscales': _('Consulter toutes les déclarations fiscales'),

        # Écriture
        'add_declaration_fiscale': _('Créer des déclarations fiscales'),
        'change_declaration_fiscale': _('Modifier les déclarations fiscales'),
        'validate_declaration_fiscale': _('Valider les déclarations fiscales'),

        # Actions avancées
        'optimisation_fiscale': _('Proposer des optimisations fiscales'),
        'export_fiscalite': _('Exporter les données fiscales'),
    },

    # ============ MODULE DOCUMENTS ============
    'documents': {
        # Lecture
        'view_documents': _('Consulter les documents'),
        'view_all_documents': _('Consulter tous les documents'),
        'download_document': _('Télécharger les documents'),

        # Écriture
        'add_document': _('Ajouter des documents'),
        'change_document': _('Modifier les métadonnées des documents'),
        'delete_document': _('Supprimer des documents'),

        # Actions avancées
        'ocr_document': _('Lancer l\'OCR sur un document'),
        'classify_document': _('Classifier les documents'),
        'share_document': _('Partager des documents'),
    },

    # ============ MODULE ANALYTICS ============
    'analytics': {
        # Lecture
        'view_tableaux_bord': _('Consulter les tableaux de bord'),
        'view_indicateurs': _('Consulter les indicateurs'),
        'view_rapports': _('Consulter les rapports'),
        'view_alertes': _('Consulter les alertes'),

        # Écriture
        'add_tableau_bord': _('Créer des tableaux de bord'),
        'change_tableau_bord': _('Modifier les tableaux de bord'),
        'delete_tableau_bord': _('Supprimer des tableaux de bord'),

        # Rapports
        'generate_rapport': _('Générer des rapports'),
        'schedule_rapport': _('Planifier des rapports'),

        # Exports
        'export_donnees': _('Exporter des données'),

        # Alertes
        'acquitter_alerte': _('Acquitter des alertes'),
        'config_alertes': _('Configurer les alertes'),
    },

    # ============ MODULE CORE ============
    'core': {
        # Clients
        'view_clients': _('Consulter les clients'),
        'view_all_clients': _('Consulter tous les clients'),
        'add_client': _('Créer des clients'),
        'change_client': _('Modifier les clients'),
        'delete_client': _('Supprimer des clients'),

        # Mandats
        'view_mandats': _('Consulter les mandats'),
        'view_all_mandats': _('Consulter tous les mandats'),
        'add_mandat': _('Créer des mandats'),
        'change_mandat': _('Modifier les mandats'),
        'delete_mandat': _('Supprimer des mandats'),

        # Contrats
        'view_contrat': _('Consulter les contrats'),
        'add_contrat': _('Créer des contrats'),
        'change_contrat': _('Modifier les contrats'),
        'delete_contrat': _('Supprimer des contrats'),

        # Utilisateurs
        'view_users': _('Consulter les utilisateurs'),
        'add_user': _('Créer des utilisateurs'),
        'change_user': _('Modifier les utilisateurs'),
        'delete_user': _('Supprimer des utilisateurs'),
        'assign_role': _('Assigner des rôles'),

        # Audit
        'view_audit_log': _('Consulter les logs d\'audit'),

        # Administration
        'admin_settings': _('Accéder aux paramètres d\'administration'),
        'backup_restore': _('Sauvegarder et restaurer'),
    },

    # ============ MODULE MODELFORMS ============
    'modelforms': {
        # Configurations
        'view_configurations': _('Consulter les configurations de formulaires'),
        'add_configuration': _('Créer des configurations de formulaires'),
        'change_configuration': _('Modifier les configurations de formulaires'),
        'delete_configuration': _('Supprimer des configurations de formulaires'),

        # Soumissions
        'view_submissions': _('Consulter les soumissions'),
        'view_all_submissions': _('Consulter toutes les soumissions'),
        'add_submission': _('Soumettre des formulaires'),
        'validate_submission': _('Valider les soumissions'),
        'reject_submission': _('Rejeter les soumissions'),

        # Templates
        'view_templates': _('Consulter les templates'),
        'add_template': _('Créer des templates'),
        'change_template': _('Modifier les templates'),
        'delete_template': _('Supprimer des templates'),

        # Introspection
        'introspect_models': _('Utiliser l\'introspection des modèles'),
    },

    # ============ MODULE GRAPHE RELATIONNEL ============
    'graph': {
        'view_graph': _('Consulter le graphe relationnel'),
        'add_entite': _('Créer des entités'),
        'change_entite': _('Modifier des entités'),
        'delete_entite': _('Supprimer des entités'),
        'add_relation': _('Créer des relations'),
        'manage_ontologie': _('Gérer l\'ontologie'),
        'manage_anomalies': _('Traiter les anomalies'),
        'import_data': _('Importer des données'),
    },
}


# ============================================================================
# MAPPING RÔLES -> PERMISSIONS
# ============================================================================

# Permissions par rôle (le superadmin a toutes les permissions automatiquement)
ROLE_PERMISSIONS = {
    'ADMIN': [
        # Toutes les permissions
        '*'
    ],

    'MANAGER': [
        # Comptabilité
        'comptabilite.view_plan_comptable',
        'comptabilite.view_ecritures',
        'comptabilite.view_journaux',
        'comptabilite.view_balance',
        'comptabilite.view_grand_livre',
        'comptabilite.add_ecriture',
        'comptabilite.change_ecriture_brouillon',
        'comptabilite.validate_ecriture',
        'comptabilite.delete_ecriture_brouillon',
        'comptabilite.lettrage',
        'comptabilite.cloture_periode',
        'comptabilite.import_ecritures',
        'comptabilite.export_comptabilite',

        # Facturation
        'facturation.view_factures',
        'facturation.view_all_factures',
        'facturation.view_prestations',
        'facturation.view_timetracking',
        'facturation.view_all_timetracking',
        'facturation.view_paiements',
        'facturation.add_facture',
        'facturation.change_facture_brouillon',
        'facturation.validate_facture',
        'facturation.delete_facture_brouillon',
        'facturation.add_timetracking',
        'facturation.add_timetracking_autre',
        'facturation.validate_timetracking',
        'facturation.add_paiement',
        'facturation.validate_paiement',
        'facturation.create_avoir',
        'facturation.create_relance',
        'facturation.annuler_facture',
        'facturation.export_factures',
        'facturation.generate_qrbill',

        # TVA
        'tva.view_declarations',
        'tva.view_all_declarations',
        'tva.view_operations',
        'tva.view_all_operations',
        'tva.add_declaration',
        'tva.change_declaration_brouillon',
        'tva.validate_declaration',
        'tva.delete_declaration_brouillon',
        'tva.calcul_automatique',
        'tva.soumettre_afc',
        'tva.add_correction',
        'tva.export_tva',
        'tva.config_tva',

        # Salaires
        'salaires.view_fiches_salaire',
        'salaires.view_all_fiches',
        'salaires.view_employes',
        'salaires.view_cotisations',
        'salaires.add_fiche_salaire',
        'salaires.change_fiche_brouillon',
        'salaires.validate_fiche',
        'salaires.delete_fiche_brouillon',
        'salaires.calcul_salaires',
        'salaires.generate_certificat',
        'salaires.declaration_avs',
        'salaires.declaration_lpp',
        'salaires.export_salaires',

        # Fiscalité
        'fiscalite.view_declarations_fiscales',
        'fiscalite.view_all_declarations_fiscales',
        'fiscalite.add_declaration_fiscale',
        'fiscalite.change_declaration_fiscale',
        'fiscalite.validate_declaration_fiscale',
        'fiscalite.export_fiscalite',

        # Documents
        'documents.view_documents',
        'documents.view_all_documents',
        'documents.download_document',
        'documents.add_document',
        'documents.change_document',
        'documents.delete_document',
        'documents.ocr_document',
        'documents.classify_document',
        'documents.share_document',

        # Analytics
        'analytics.view_tableaux_bord',
        'analytics.view_indicateurs',
        'analytics.view_rapports',
        'analytics.view_alertes',
        'analytics.add_tableau_bord',
        'analytics.change_tableau_bord',
        'analytics.delete_tableau_bord',
        'analytics.generate_rapport',
        'analytics.schedule_rapport',
        'analytics.export_donnees',
        'analytics.acquitter_alerte',
        'analytics.config_alertes',

        # Core
        'core.view_clients',
        'core.view_all_clients',
        'core.add_client',
        'core.change_client',
        'core.view_mandats',
        'core.view_all_mandats',
        'core.add_mandat',
        'core.change_mandat',
        'core.view_contrat',
        'core.add_contrat',
        'core.change_contrat',
        'core.delete_contrat',
        'core.view_users',
        'core.view_audit_log',

        # Modelforms (complet)
        'modelforms.view_configurations',
        'modelforms.add_configuration',
        'modelforms.change_configuration',
        'modelforms.delete_configuration',
        'modelforms.view_submissions',
        'modelforms.view_all_submissions',
        'modelforms.add_submission',
        'modelforms.validate_submission',
        'modelforms.reject_submission',
        'modelforms.view_templates',
        'modelforms.add_template',
        'modelforms.change_template',
        'modelforms.introspect_models',

        # Graphe relationnel
        'graph.view_graph',
        'graph.add_entite',
        'graph.change_entite',
        'graph.delete_entite',
        'graph.add_relation',
        'graph.manage_ontologie',
        'graph.manage_anomalies',
        'graph.import_data',
    ],

    'COMPTABLE': [
        # Comptabilité (complète)
        'comptabilite.view_plan_comptable',
        'comptabilite.view_ecritures',
        'comptabilite.view_journaux',
        'comptabilite.view_balance',
        'comptabilite.view_grand_livre',
        'comptabilite.add_ecriture',
        'comptabilite.change_ecriture_brouillon',
        'comptabilite.validate_ecriture',
        'comptabilite.delete_ecriture_brouillon',
        'comptabilite.lettrage',
        'comptabilite.import_ecritures',
        'comptabilite.export_comptabilite',

        # Facturation (lecture + création)
        'facturation.view_factures',
        'facturation.view_prestations',
        'facturation.view_timetracking',
        'facturation.view_paiements',
        'facturation.add_facture',
        'facturation.change_facture_brouillon',
        'facturation.delete_facture_brouillon',
        'facturation.add_timetracking',
        'facturation.add_paiement',
        'facturation.export_factures',
        'facturation.generate_qrbill',

        # TVA (complète)
        'tva.view_declarations',
        'tva.view_operations',
        'tva.add_declaration',
        'tva.change_declaration_brouillon',
        'tva.validate_declaration',
        'tva.delete_declaration_brouillon',
        'tva.calcul_automatique',
        'tva.add_correction',
        'tva.export_tva',

        # Salaires (lecture + création)
        'salaires.view_fiches_salaire',
        'salaires.view_employes',
        'salaires.view_cotisations',
        'salaires.add_fiche_salaire',
        'salaires.change_fiche_brouillon',
        'salaires.calcul_salaires',
        'salaires.export_salaires',

        # Fiscalité (lecture)
        'fiscalite.view_declarations_fiscales',

        # Documents
        'documents.view_documents',
        'documents.download_document',
        'documents.add_document',
        'documents.change_document',
        'documents.ocr_document',

        # Analytics (lecture)
        'analytics.view_tableaux_bord',
        'analytics.view_indicateurs',
        'analytics.view_rapports',
        'analytics.view_alertes',
        'analytics.generate_rapport',
        'analytics.export_donnees',

        # Core
        'core.view_clients',
        'core.view_mandats',
        'core.view_contrat',
        'core.add_contrat',
        'core.change_contrat',

        # Modelforms (soumission)
        'modelforms.view_configurations',
        'modelforms.view_submissions',
        'modelforms.add_submission',
        'modelforms.view_templates',

        # Graphe relationnel (lecture)
        'graph.view_graph',
    ],

    'ASSISTANT': [
        # Comptabilité (lecture + saisie)
        'comptabilite.view_plan_comptable',
        'comptabilite.view_ecritures',
        'comptabilite.view_journaux',
        'comptabilite.view_balance',
        'comptabilite.add_ecriture',
        'comptabilite.change_ecriture_brouillon',

        # Facturation (saisie temps + lecture)
        'facturation.view_factures',
        'facturation.view_prestations',
        'facturation.view_timetracking',
        'facturation.add_timetracking',
        'facturation.add_facture',
        'facturation.change_facture_brouillon',
        'facturation.generate_qrbill',

        # TVA (lecture)
        'tva.view_declarations',
        'tva.view_operations',

        # Salaires (lecture limitée)
        'salaires.view_fiches_salaire',
        'salaires.view_employes',

        # Documents
        'documents.view_documents',
        'documents.download_document',
        'documents.add_document',

        # Analytics (lecture limitée)
        'analytics.view_tableaux_bord',
        'analytics.view_rapports',

        # Core
        'core.view_clients',
        'core.view_mandats',
    ],

    'CLIENT': [
        # Facturation (ses propres factures)
        'facturation.view_factures',

        # Documents (ses propres documents)
        'documents.view_documents',
        'documents.download_document',
        'documents.add_document',

        # Analytics (tableaux de bord partagés)
        'analytics.view_tableaux_bord',
        'analytics.view_rapports',
    ],
}


# ============================================================================
# CLASSES DE PERMISSION REST FRAMEWORK
# ============================================================================

class IsSuperAdmin(BasePermission):
    """
    Vérifie si l'utilisateur est superadmin (is_superuser=True).
    Le superadmin a TOUS les droits.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsAdminRole(BasePermission):
    """Vérifie si l'utilisateur a le rôle ADMIN (niveau 100)."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_admin()
        )


class IsManagerOrAbove(BasePermission):
    """Vérifie si l'utilisateur est MANAGER ou supérieur (niveau >= 80)."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_manager()
        )


class IsComptableOrAbove(BasePermission):
    """Vérifie si l'utilisateur est COMPTABLE ou supérieur (niveau >= 60)."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_comptable()
        )


class IsStaffOrAbove(BasePermission):
    """Vérifie si l'utilisateur est un membre du staff (pas CLIENT, niveau > 10)."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or not request.user.is_client())
        )


class HasBusinessPermission(BasePermission):
    """
    Permission générique basée sur les permissions métier.

    Usage:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [HasBusinessPermission]
            required_permission = 'facturation.add_facture'
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Superadmin a tous les droits
        if request.user.is_superuser:
            return True

        # Vérifier la permission requise
        required_perm = getattr(view, 'required_permission', None)
        if not required_perm:
            return True

        return has_business_permission(request.user, required_perm)


class CanViewOrEdit(BasePermission):
    """
    Permission différenciée lecture/écriture.
    Lecture (GET, HEAD, OPTIONS) = permission view
    Écriture = permission edit correspondante
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if request.method in SAFE_METHODS:
            perm = getattr(view, 'view_permission', None)
        else:
            perm = getattr(view, 'edit_permission', None)

        if not perm:
            return True

        return has_business_permission(request.user, perm)


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def has_business_permission(user, permission_code):
    """
    Vérifie si un utilisateur a une permission métier.

    Args:
        user: Instance User
        permission_code: Code de permission (ex: 'facturation.add_facture')

    Returns:
        bool: True si l'utilisateur a la permission
    """
    if not user or not user.is_authenticated:
        return False

    # Superadmin a tous les droits
    if user.is_superuser:
        return True

    # Récupérer les permissions du rôle
    role_code = user.role.code if user.role else None
    role_perms = ROLE_PERMISSIONS.get(role_code, [])

    # ADMIN a toutes les permissions
    if '*' in role_perms:
        return True

    # Vérifier si la permission est dans la liste du rôle
    if permission_code in role_perms:
        return True

    # Vérifier aussi les permissions Django standard
    return user.has_perm(permission_code)


def get_user_permissions(user):
    """
    Retourne toutes les permissions d'un utilisateur.

    Args:
        user: Instance User

    Returns:
        set: Ensemble des codes de permission
    """
    if not user or not user.is_authenticated:
        return set()

    # Superadmin a toutes les permissions
    if user.is_superuser:
        all_perms = set()
        for app_perms in PERMISSIONS_METIER.values():
            for perm in app_perms.keys():
                all_perms.add(perm)
        return all_perms

    # Récupérer les permissions du rôle
    role_code = user.role.code if user.role else None
    role_perms = ROLE_PERMISSIONS.get(role_code, [])

    if '*' in role_perms:
        # ADMIN a toutes les permissions
        all_perms = set()
        for app, perms in PERMISSIONS_METIER.items():
            for perm in perms.keys():
                all_perms.add(f"{app}.{perm}")
        return all_perms

    return set(role_perms)


def get_permissions_for_role(role):
    """
    Retourne les permissions pour un rôle donné.

    Args:
        role: Code du rôle (ADMIN, MANAGER, etc.)

    Returns:
        list: Liste des permissions
    """
    return ROLE_PERMISSIONS.get(role, [])


# ============================================================================
# DÉCORATEURS POUR LES VUES
# ============================================================================

def permission_required_business(permission_code, redirect_url=None, raise_exception=True):
    """
    Décorateur pour exiger une permission métier sur une vue fonction.

    Usage:
        @permission_required_business('facturation.add_facture')
        def ma_vue(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if has_business_permission(request.user, permission_code):
                return view_func(request, *args, **kwargs)

            if raise_exception:
                raise PermissionDenied(
                    f"Permission requise: {permission_code}"
                )

            if redirect_url:
                messages.error(
                    request,
                    _("Vous n'avez pas les droits nécessaires pour cette action.")
                )
                return redirect(redirect_url)

            raise PermissionDenied()

        return _wrapped_view
    return decorator


def superadmin_required(view_func):
    """
    Décorateur qui exige que l'utilisateur soit superadmin.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied(_("Accès réservé aux super-administrateurs."))
    return _wrapped_view


def role_required(*roles):
    """
    Décorateur qui exige un ou plusieurs rôles.

    Usage:
        @role_required('ADMIN', 'MANAGER')
        def ma_vue(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            role_code = request.user.role.code if request.user.role else None
            if role_code in roles:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied(
                _("Accès réservé aux rôles: %(roles)s") % {'roles': ', '.join(roles)}
            )
        return _wrapped_view
    return decorator


# ============================================================================
# MIXINS POUR LES VUES CLASS-BASED
# ============================================================================

class BusinessPermissionMixin:
    """
    Mixin pour vérifier les permissions métier dans les CBV.

    Usage:
        class MaVue(BusinessPermissionMixin, TemplateView):
            business_permission = 'facturation.add_facture'
    """
    business_permission = None

    def dispatch(self, request, *args, **kwargs):
        if self.business_permission:
            if not has_business_permission(request.user, self.business_permission):
                raise PermissionDenied(
                    _("Permission requise: %(perm)s") % {'perm': self.business_permission}
                )
        return super().dispatch(request, *args, **kwargs)


class SuperAdminRequiredMixin:
    """Mixin qui exige que l'utilisateur soit superadmin."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied(_("Accès réservé aux super-administrateurs."))
        return super().dispatch(request, *args, **kwargs)


class RoleRequiredMixin:
    """
    Mixin qui exige un ou plusieurs rôles.

    Usage:
        class MaVue(RoleRequiredMixin, TemplateView):
            required_roles = ['ADMIN', 'MANAGER']
    """
    required_roles = []

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        role_code = request.user.role.code if request.user.role else None
        if role_code in self.required_roles:
            return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied(
            _("Accès réservé aux rôles: %(roles)s") % {'roles': ', '.join(self.required_roles)}
        )


# ============================================================================
# CONTEXT PROCESSOR POUR LES TEMPLATES
# ============================================================================

def permissions_context(request):
    """
    Context processor pour ajouter les permissions au contexte des templates.

    Usage dans settings.py:
        TEMPLATES = [{
            'OPTIONS': {
                'context_processors': [
                    ...
                    'core.permissions.permissions_context',
                ],
            },
        }]

    Usage dans les templates:
        {% if user_permissions.facturation.add_facture %}
            <a href="...">Créer facture</a>
        {% endif %}
    """
    import os
    from django.conf import settings

    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'user_permissions': {}, 'user_role': None, 'is_superadmin': False}

    user = request.user
    permissions = get_user_permissions(user)

    # Organiser par app
    perms_by_app = {}
    for perm in permissions:
        if '.' in perm:
            app, code = perm.split('.', 1)
            if app not in perms_by_app:
                perms_by_app[app] = {}
            perms_by_app[app][code] = True

    # URLs des services externes (Nextcloud, MinIO) — cloud edition only
    domain = os.environ.get('DOMAIN', 'localhost')
    community_mode = getattr(settings, 'COMMUNITY_MODE', False)
    nextcloud_enabled = (
        not community_mode
        and os.environ.get('NEXTCLOUD_ENABLED', 'False').lower() in ('true', '1', 'yes')
    )
    nextcloud_url = f"https://nextcloud.{domain}" if nextcloud_enabled else None
    minio_url = f"https://minio.{domain}" if nextcloud_enabled else None

    return {
        'user_permissions': perms_by_app,
        'user_role': user.role.code if user.role else None,
        'is_superadmin': user.is_superuser,
        'nextcloud_enabled': nextcloud_enabled,
        'nextcloud_url': nextcloud_url,
        'minio_url': minio_url,
    }


# ============================================================================
# COMMANDE DE CRÉATION DES PERMISSIONS
# ============================================================================

def create_business_permissions():
    """
    Crée les permissions métier dans la base de données.
    À appeler via une commande management ou un signal post_migrate.
    """
    for app_label, permissions in PERMISSIONS_METIER.items():
        # Trouver un ContentType pour l'app (utiliser le premier modèle disponible)
        try:
            content_type = ContentType.objects.filter(app_label=app_label).first()
            if not content_type:
                print(f"Pas de ContentType pour {app_label}, skip.")
                continue

            for codename, name in permissions.items():
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type,
                    defaults={'name': str(name)}
                )

        except Exception as e:
            print(f"Erreur création permissions {app_label}: {e}")

    print("Permissions métier créées avec succès.")
