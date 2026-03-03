from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def sub(value, arg):
    """Soustrait arg de value. Usage: {{ value|sub:arg }}"""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (InvalidOperation, TypeError, ValueError):
        return ""
