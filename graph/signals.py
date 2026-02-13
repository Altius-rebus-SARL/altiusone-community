# graph/signals.py
"""Signals pour le graphe relationnel."""
import logging
from django.db.models.signals import post_save, post_delete
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


# --- Sync signals pour auto-population du graphe ---

# Flag pour éviter la récursion (sync_instance sauvegarde Entite → signal Entite)
_sync_in_progress = set()


def graph_post_save(sender, instance, **kwargs):
    """Synchronise une instance Django vers le graphe après sauvegarde."""
    key = (sender, instance.pk)
    if key in _sync_in_progress:
        return
    _sync_in_progress.add(key)
    try:
        from graph.services.sync import sync_instance, sync_relations
        entite = sync_instance(instance)
        if entite:
            sync_relations(instance)
    except Exception as e:
        logger.warning(f"Erreur sync graphe pour {sender.__name__} #{instance.pk}: {e}")
    finally:
        _sync_in_progress.discard(key)


def graph_post_delete(sender, instance, **kwargs):
    """Désactive l'entité du graphe quand l'instance Django est supprimée."""
    try:
        from graph.services.sync import delete_instance
        delete_instance(instance)
    except Exception as e:
        logger.warning(f"Erreur delete graphe pour {sender.__name__} #{instance.pk}: {e}")


def register_sync_signals():
    """Enregistre les signals post_save/post_delete pour tous les modèles mappés."""
    from django.apps import apps as django_apps
    from graph.sync_config import MODEL_GRAPH_CONFIG

    for model_key in MODEL_GRAPH_CONFIG:
        app_label, model_name = model_key.split('.')
        try:
            model = django_apps.get_model(app_label, model_name)
            post_save.connect(graph_post_save, sender=model, dispatch_uid=f'graph_sync_save_{model_key}')
            post_delete.connect(graph_post_delete, sender=model, dispatch_uid=f'graph_sync_delete_{model_key}')
        except LookupError:
            logger.warning(f"Modèle introuvable pour sync graphe: {model_key}")
