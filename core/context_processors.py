from decimal import Decimal

from django.utils.translation import gettext_lazy as _

from core.models import Devise


CONNEXION_BADGES = {
    ("STAFF", "EMPLOYE"):      {"label": _("Staff interne"),  "color": "success"},
    ("STAFF", "PRESTATAIRE"):  {"label": _("Staff externe"),  "color": "info"},
    ("CLIENT", "EMPLOYE"):     {"label": _("Client interne"), "color": "warning"},
    ("CLIENT", "PRESTATAIRE"): {"label": _("Client externe"), "color": "danger"},
}


def connexion_context(request):
    """Expose le type de connexion utilisateur dans tous les templates.

    Variables exposées :
    - CONNEXION_LABEL : libellé du type de connexion (ex: "Staff interne")
    - CONNEXION_COLOR : couleur Bootstrap du badge (success, info, warning, danger)
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {}

    user = request.user
    key = (
        getattr(user, "type_utilisateur", "STAFF"),
        getattr(user, "type_collaborateur", "EMPLOYE"),
    )
    badge = CONNEXION_BADGES.get(key, CONNEXION_BADGES[("STAFF", "EMPLOYE")])

    return {
        "CONNEXION_LABEL": badge["label"],
        "CONNEXION_COLOR": badge["color"],
    }


def devise_context(request):
    """Fournit les variables de devise à tous les templates.

    Variables exposées :
    - DEVISE_CODE : code ISO de la devise affichée (ex: EUR)
    - DEVISE_TAUX : taux de conversion depuis la devise de base (1 si devise de base)
    - DEVISE_BASE_CODE : code ISO de la devise de base (ex: CHF)
    - DEVISES_ACTIVES : queryset des devises actives pour le sélecteur
    """
    try:
        devise_base = Devise.get_devise_base()
        base_code = devise_base.code
    except Exception:
        return {
            "DEVISE_CODE": "CHF",
            "DEVISE_TAUX": Decimal("1"),
            "DEVISE_BASE_CODE": "CHF",
            "DEVISES_ACTIVES": [],
        }

    devises_actives = Devise.objects.filter(actif=True)

    # Devise choisie par l'utilisateur (persistée dans preferences)
    devise_code = base_code
    devise_taux = Decimal("1")
    devise_obj = devise_base

    if hasattr(request, "user") and request.user.is_authenticated:
        pref_code = request.user.preferences.get("devise_code") if request.user.preferences else None
        if pref_code:
            try:
                devise_choisie = devises_actives.get(code=pref_code)
                devise_code = devise_choisie.code
                devise_taux = devise_choisie.taux_change
                devise_obj = devise_choisie
            except Devise.DoesNotExist:
                pass

    return {
        "DEVISE_CODE": devise_code,
        "DEVISE_TAUX": devise_taux,
        "DEVISE_BASE_CODE": base_code,
        "DEVISE_OBJ": devise_obj,
        "DEVISES_ACTIVES": devises_actives,
    }
