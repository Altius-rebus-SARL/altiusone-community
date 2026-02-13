from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def devise(value, taux):
    """Convertit un montant par le taux de change de la devise sélectionnée."""
    try:
        return Decimal(str(value)) * Decimal(str(taux))
    except (ValueError, TypeError, InvalidOperation):
        return value
