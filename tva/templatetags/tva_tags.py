# tva/templatetags/tva_tags.py
from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


STATUT_BADGE_MAP = {
    'BROUILLON': 'bg-secondary-subtle text-secondary',
    'EN_COURS': 'bg-info-subtle text-info',
    'A_VALIDER': 'bg-warning-subtle text-warning',
    'VALIDE': 'bg-info-subtle text-info',
    'SOUMIS': 'bg-primary-subtle text-primary',
    'ACCEPTE': 'bg-success-subtle text-success',
    'PAYE': 'bg-success',
    'CLOTURE': 'bg-dark-subtle text-dark',
}


@register.filter(name='statut_badge_class')
def statut_badge_class(statut):
    """Retourne la classe CSS Bootstrap pour un statut TVA donné."""
    return STATUT_BADGE_MAP.get(statut, 'bg-secondary')


@register.filter(name='format_suisse')
def format_suisse(value):
    """Formate un montant selon la convention suisse : 1'234.56"""
    if value is None:
        return '0.00'
    try:
        val = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)

    # Séparer partie entière et décimale
    is_negative = val < 0
    val = abs(val)
    parts = f"{val:.2f}".split('.')
    entier = parts[0]
    decimale = parts[1]

    # Ajouter les apostrophes comme séparateur de milliers
    result = ''
    for i, digit in enumerate(reversed(entier)):
        if i > 0 and i % 3 == 0:
            result = "'" + result
        result = digit + result

    formatted = f"{result}.{decimale}"
    if is_negative:
        formatted = f"-{formatted}"
    return formatted
