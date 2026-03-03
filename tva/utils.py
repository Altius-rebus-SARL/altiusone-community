# tva/utils.py
from decimal import Decimal


def get_taux_tva_defaut(mandat=None):
    """Retourne le taux normal du regime fiscal du mandat. Fallback: 8.1"""
    if mandat:
        try:
            # Priorité 1: mandat.regime_fiscal (FK directe)
            if hasattr(mandat, 'regime_fiscal') and mandat.regime_fiscal_id:
                return mandat.regime_fiscal.taux_normal
        except (AttributeError, Exception):
            pass
        try:
            # Priorité 2: config_tva.regime
            return mandat.config_tva.regime.taux_normal
        except (AttributeError, Exception):
            pass
    return Decimal("8.1")
