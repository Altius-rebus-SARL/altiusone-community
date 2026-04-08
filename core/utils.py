# core/utils.py
"""
Utilitaires partagés par tous les modules.

Centralise le formatage des montants pour éviter les fonctions
hardcodées (format_suisse, _fmt_chf, format_montant_chf…).
"""
from decimal import Decimal, InvalidOperation


def format_montant(montant, devise=None, avec_code=False):
    """
    Formate un montant selon la devise (séparateurs dynamiques).

    Args:
        montant: Decimal, float ou str — le montant à formater
        devise: objet Devise (core.models.Devise) ou None (fallback suisse)
        avec_code: si True, ajoute le code devise (ex: "1'234.56 CHF")

    Returns:
        str — montant formaté

    Exemples:
        format_montant(1234.5)                    → "1'234.50"       (fallback suisse)
        format_montant(1234.5, devise_eur)        → "1 234,50"       (format français)
        format_montant(1234.5, devise_chf, True)  → "1'234.50 CHF"
    """
    if montant is None:
        return '0.00'
    try:
        val = Decimal(str(montant))
    except (InvalidOperation, TypeError, ValueError):
        return str(montant)

    # Résoudre les paramètres de la devise
    if devise:
        sep_milliers = devise.separateur_milliers
        sep_decimal = devise.separateur_decimal
        decimales = devise.decimales
        code = devise.code
    else:
        sep_milliers = "'"
        sep_decimal = '.'
        decimales = 2
        code = 'CHF'

    is_negative = val < 0
    val = abs(val)
    fmt_str = f"{{:.{decimales}f}}"
    parts = fmt_str.format(val).split('.')
    entier = parts[0]
    partie_dec = parts[1] if len(parts) > 1 else '00'

    result = ''
    for i, digit in enumerate(reversed(entier)):
        if i > 0 and i % 3 == 0:
            result = sep_milliers + result
        result = digit + result

    formatted = f"{result}{sep_decimal}{partie_dec}"
    if is_negative:
        formatted = f"-{formatted}"
    if avec_code:
        formatted = f"{formatted} {code}"
    return formatted


def get_devise_for_mandat(mandat):
    """Résout la devise d'un mandat (objet Devise)."""
    if mandat and hasattr(mandat, 'devise') and mandat.devise_id:
        return mandat.devise
    try:
        from core.models import Devise
        return Devise.objects.filter(est_devise_base=True).first()
    except Exception:
        return None
