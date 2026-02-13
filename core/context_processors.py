from decimal import Decimal

from core.models import Devise


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

    if hasattr(request, "user") and request.user.is_authenticated:
        pref_code = request.user.preferences.get("devise_code") if request.user.preferences else None
        if pref_code:
            try:
                devise_choisie = devises_actives.get(code=pref_code)
                devise_code = devise_choisie.code
                devise_taux = devise_choisie.taux_change
            except Devise.DoesNotExist:
                pass

    return {
        "DEVISE_CODE": devise_code,
        "DEVISE_TAUX": devise_taux,
        "DEVISE_BASE_CODE": base_code,
        "DEVISES_ACTIVES": devises_actives,
    }
