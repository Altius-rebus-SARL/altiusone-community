# apps/modelforms/permissions.py
"""
Helpers de permission pour modelforms.

Centralise la logique de mandat-scoping pour FormConfiguration et FormSubmission.
Ces helpers sont utilises dans les vues HTMX (views.py), les viewsets DRF
(viewset.py) et les serializers (serializers.py) pour garantir que le filtrage
par mandat est coherent partout.

Regles metier:

- **FormConfiguration** peut etre assignee a un ou plusieurs mandats via M2M.
  Si `mandats` est vide, la configuration est consideree comme GLOBALE et
  visible par tous les utilisateurs authentifies. Sinon, seuls les
  utilisateurs ayant acces a au moins un des mandats de la liste peuvent
  la voir. Les managers/superusers voient tout.

- **FormSubmission** a un FK `mandat` (nullable). Un utilisateur voit:
  * Ses propres soumissions (submitted_by=user) — toujours, meme si le
    mandat n'est pas dans ses mandats accessibles (utile pour traquer
    ce qu'on a soumis).
  * Les soumissions des autres utilisateurs UNIQUEMENT si elles sont
    attachees a un de ses mandats accessibles.
  * Les managers/superusers voient tout.
"""
from django.db.models import Q


def _is_manager_or_above(user) -> bool:
    """Retourne True si l'utilisateur est manager ou superuser."""
    if getattr(user, 'is_superuser', False):
        return True
    if hasattr(user, 'is_manager') and user.is_manager():
        return True
    return False


def scope_form_configs_by_user(queryset, user):
    """
    Filtre un queryset de FormConfiguration selon les mandats accessibles.

    Regle:
    - Manager/superuser: tout voit.
    - Autres: configs sans mandat (globales) + configs liees a leurs mandats.

    Args:
        queryset: QuerySet de FormConfiguration a filtrer.
        user: Instance User Django.

    Returns:
        QuerySet filtre.
    """
    if _is_manager_or_above(user):
        return queryset

    if not hasattr(user, 'get_accessible_mandats'):
        # Fallback ultra-prudent : ne montrer que les configs globales
        return queryset.filter(mandats__isnull=True).distinct()

    accessible = user.get_accessible_mandats()
    return queryset.filter(
        Q(mandats__isnull=True) | Q(mandats__in=accessible)
    ).distinct()


def scope_form_submissions_by_user(queryset, user):
    """
    Filtre un queryset de FormSubmission selon les mandats accessibles.

    Regle:
    - Manager/superuser: tout voit.
    - Autres: leurs propres soumissions + celles attachees a leurs mandats.

    Args:
        queryset: QuerySet de FormSubmission a filtrer.
        user: Instance User Django.

    Returns:
        QuerySet filtre.
    """
    if _is_manager_or_above(user):
        return queryset

    if not hasattr(user, 'get_accessible_mandats'):
        # Fallback: seulement ses propres soumissions
        return queryset.filter(submitted_by=user)

    accessible = user.get_accessible_mandats()
    return queryset.filter(
        Q(submitted_by=user) | Q(mandat__in=accessible)
    ).distinct()


def user_can_access_mandat(user, mandat) -> bool:
    """
    Verifie qu'un utilisateur peut acceder a un Mandat donne.

    Utilise pour valider les mandat_id fournis dans les POST de soumission
    afin d'eviter qu'un utilisateur attache une soumission a un mandat
    auquel il n'a pas acces.

    Args:
        user: Instance User Django.
        mandat: Instance Mandat OU identifiant UUID/pk.

    Returns:
        True si l'utilisateur a acces, False sinon.
    """
    if mandat is None:
        # Un mandat null est toujours autorise (soumission sans contexte)
        return True

    if _is_manager_or_above(user):
        return True

    if not hasattr(user, 'get_accessible_mandats'):
        return False

    accessible = user.get_accessible_mandats()
    # Accepter soit une instance Mandat, soit un pk
    if hasattr(mandat, 'pk'):
        return accessible.filter(pk=mandat.pk).exists()
    return accessible.filter(pk=mandat).exists()


def user_can_access_form_config(user, form_config) -> bool:
    """
    Verifie qu'un utilisateur peut acceder a un FormConfiguration donne.

    Regle identique a scope_form_configs_by_user mais pour un objet unique.
    Utile dans les vues detail/submit.

    Args:
        user: Instance User Django.
        form_config: Instance FormConfiguration.

    Returns:
        True si l'utilisateur a acces, False sinon.
    """
    if form_config is None:
        return False

    if _is_manager_or_above(user):
        return True

    # Configuration globale (sans mandat assigne)
    if not form_config.mandats.exists():
        return True

    if not hasattr(user, 'get_accessible_mandats'):
        return False

    accessible = user.get_accessible_mandats()
    return form_config.mandats.filter(pk__in=accessible).exists()
