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
    """Formate un montant selon la devise du contexte (fallback format suisse)."""
    from core.utils import format_montant
    return format_montant(value)
