# apps/modelforms/templatetags/modelforms_tags.py
"""
Template tags et filtres pour l'app modelforms.
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Permet d'accéder à un élément d'un dictionnaire avec une clé variable.

    Usage: {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def default_if_none_or_empty(value, default):
    """
    Retourne la valeur par défaut si la valeur est None ou vide.

    Usage: {{ value|default_if_none_or_empty:"default" }}
    """
    if value is None or value == '':
        return default
    return value
