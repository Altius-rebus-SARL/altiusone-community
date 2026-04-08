# tva/utils.py
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


def get_taux_tva_defaut(mandat=None):
    """
    Retourne le taux normal du régime fiscal du mandat.

    Résolution :
      1. mandat.regime_fiscal.taux_normal (FK directe)
      2. mandat.config_tva.regime.taux_normal (via ConfigurationTVA)
      3. Decimal('0') + warning log (aucun fallback hardcodé)
    """
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
    logger.warning(
        "Aucun régime fiscal trouvé pour le mandat %s — taux TVA défaut = 0%%",
        getattr(mandat, 'numero', '?'),
    )
    return Decimal("0")
