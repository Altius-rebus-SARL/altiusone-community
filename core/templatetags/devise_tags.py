from decimal import Decimal, InvalidOperation

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def devise(value, taux):
    """Convertit un montant par le taux de change de la devise sélectionnée."""
    try:
        return Decimal(str(value)) * Decimal(str(taux))
    except (ValueError, TypeError, InvalidOperation):
        return value


@register.filter
def devise_format(value, devise_obj):
    """Formate un montant selon les paramètres d'une Devise.

    Usage: {{ montant|devise_format:DEVISE_OBJ }}
    Utilise Devise.formater() pour respecter décimales, séparateurs et symbole.
    """
    if devise_obj is None or value is None or value == '':
        return value
    try:
        return devise_obj.formater(value)
    except (ValueError, TypeError, InvalidOperation):
        return value
