# graph/tasks.py
"""Tâches Celery pour le graphe relationnel."""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generer_embedding_entite_task(self, entite_id):
    """
    Génère l'embedding vectoriel d'une entité.

    Args:
        entite_id: UUID de l'entité (str)
    """
    from graph.services.embedding import mettre_a_jour_embedding

    try:
        result = mettre_a_jour_embedding(entite_id)
        return {'status': 'ok' if result else 'skipped', 'entite_id': str(entite_id)}
    except Exception as e:
        logger.error(f"Erreur embedding entité {entite_id}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=1, default_retry_delay=300)
def detecter_anomalies_task(self):
    """Lance la détection complète d'anomalies sur le graphe."""
    from graph.services.anomalies import detecter_tout

    try:
        resultats = detecter_tout()
        return {'status': 'ok', 'resultats': resultats}
    except Exception as e:
        logger.error(f"Erreur détection anomalies: {e}")
        raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=1, default_retry_delay=300)
def reindexer_tous_embeddings_task(self, batch_size=100):
    """
    Réindexe les embeddings de toutes les entités actives.

    Args:
        batch_size: Nombre d'entités par batch
    """
    from graph.models import Entite
    from graph.services.embedding import mettre_a_jour_embedding

    entites = Entite.objects.filter(is_active=True).values_list('pk', flat=True)
    total = entites.count()
    updated = 0
    errors = 0

    logger.info(f"Reindexation embeddings: {total} entités")

    for pk in entites.iterator(chunk_size=batch_size):
        try:
            if mettre_a_jour_embedding(pk):
                updated += 1
        except Exception as e:
            logger.error(f"Erreur reindex entité {pk}: {e}")
            errors += 1

    logger.info(f"Reindexation terminée: {updated}/{total} mis à jour, {errors} erreurs")
    return {'status': 'ok', 'total': total, 'updated': updated, 'errors': errors}
