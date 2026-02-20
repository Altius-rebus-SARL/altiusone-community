# tva/utils.py
from decimal import Decimal


def get_taux_tva_defaut(mandat=None):
    """Retourne le taux normal du regime fiscal du mandat. Fallback: 8.1"""
    if mandat:
        try:
            return mandat.config_tva.regime.taux_normal
        except (AttributeError, Exception):
            pass
    return Decimal("8.1")
