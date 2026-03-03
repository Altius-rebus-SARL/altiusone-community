# core/tasks.py
"""Taches Celery pour le module core."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    name='core.tasks.update_snb_exchange_rates',
)
def update_snb_exchange_rates(self):
    """Met a jour les taux de change depuis la BNS (SNB)."""
    try:
        from core.services import SNBExchangeRateService
        result = SNBExchangeRateService.update_devise_rates()
        logger.info("Taux SNB mis a jour: %s", result)
        return result
    except Exception as exc:
        logger.error("Erreur mise a jour taux SNB: %s", exc)
        raise self.retry(exc=exc)
