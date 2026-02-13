# graph/signals.py
"""Signals pour le graphe relationnel."""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='graph.Entite')
def entite_post_save(sender, instance, created, **kwargs):
    """Lance la génération d'embedding après sauvegarde d'une entité."""
    # Éviter les boucles : ne pas relancer si seul l'embedding a changé
    update_fields = kwargs.get('update_fields')
    if update_fields and set(update_fields) <= {'embedding', 'embedding_updated_at'}:
        return

    from graph.tasks import generer_embedding_entite_task

    try:
        generer_embedding_entite_task.delay(str(instance.pk))
    except Exception as e:
        logger.warning(f"Impossible de lancer le task embedding pour {instance.pk}: {e}")
