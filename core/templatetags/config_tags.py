from django import template

register = template.Library()


@register.filter(name='getattr')
def getattr_filter(obj, attr):
    """Accès dynamique à un attribut d'un objet. Usage: {{ item|getattr:"field_name" }}"""
    try:
        val = getattr(obj, attr, None)
        if callable(val):
            val = val()
        return val
    except Exception:
        return None
