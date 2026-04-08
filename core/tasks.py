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


# =============================================================================
# EMBEDDING TASKS
# =============================================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name='core.tasks.generer_embedding_task',
)
def generer_embedding_task(self, app_label: str, model_name: str, object_id: str):
    """
    Génère l'embedding pour un objet donné et le stocke dans ModelEmbedding.

    Args:
        app_label: ex 'core'
        model_name: ex 'client'
        object_id: UUID string
    """
    import hashlib
    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType
    from core.models import ModelEmbedding
    from core.ai.embeddings import embedding_service

    try:
        model_class = apps.get_model(app_label, model_name)
        instance = model_class.objects.get(pk=object_id)
    except (LookupError, model_class.DoesNotExist):
        logger.warning(f"Objet introuvable: {app_label}.{model_name} #{object_id}")
        return {'status': 'skipped', 'reason': 'not found'}

    if not hasattr(instance, 'texte_pour_embedding'):
        return {'status': 'skipped', 'reason': 'no texte_pour_embedding method'}

    text = instance.texte_pour_embedding()
    if not text or not text.strip():
        return {'status': 'skipped', 'reason': 'empty text'}

    text_hash = hashlib.sha256(text.encode()).hexdigest()

    # Vérifier si l'embedding existe déjà avec le même hash (pas de changement)
    ct = ContentType.objects.get_for_model(model_class)
    existing = ModelEmbedding.objects.filter(
        content_type=ct, object_id=object_id
    ).first()

    if existing and existing.text_hash == text_hash:
        return {'status': 'skipped', 'reason': 'unchanged'}

    # Générer l'embedding
    embedding = embedding_service.generate_embedding(text)
    if embedding is None:
        logger.warning(f"Embedding None pour {app_label}.{model_name} #{object_id}")
        return {'status': 'error', 'reason': 'embedding generation failed'}

    ModelEmbedding.objects.update_or_create(
        content_type=ct,
        object_id=object_id,
        defaults={
            'embedding': embedding,
            'text_hash': text_hash,
            'text_preview': text[:200],
            'model_used': embedding_service.model_name,
        }
    )

    return {
        'status': 'success',
        'app_model': f'{app_label}.{model_name}',
        'object_id': object_id,
    }


@shared_task(name='core.tasks.reindexer_tous_embeddings_task')
def reindexer_tous_embeddings_task(tier: int = 3, batch_size: int = 50):
    """
    Regénère tous les embeddings pour les modèles jusqu'au tier donné.

    Utilisé par la commande manage.py vectorize_all.
    """
    from core.embedding_config import get_models_for_tier, get_model_class

    configs = get_models_for_tier(tier)
    total = 0
    errors = 0

    for app_model, cfg in configs.items():
        try:
            model_class = get_model_class(app_model)
            qs = model_class.objects.all()
            if hasattr(model_class, 'is_active'):
                qs = qs.filter(is_active=True)

            extra_filter = cfg.get('filter')
            if extra_filter:
                qs = qs.filter(**extra_filter)

            for obj in qs.iterator(chunk_size=batch_size):
                result = generer_embedding_task(
                    app_label=obj._meta.app_label,
                    model_name=obj._meta.model_name,
                    object_id=str(obj.pk),
                )
                if result.get('status') == 'success':
                    total += 1
                elif result.get('status') == 'error':
                    errors += 1
        except Exception as e:
            logger.error(f"Erreur reindexation {app_model}: {e}")
            errors += 1

    logger.info(f"Reindexation terminée: {total} embeddings, {errors} erreurs")
    return {'indexed': total, 'errors': errors}


@shared_task(name='core.tasks.indexer_embeddings_manquants_task')
def indexer_embeddings_manquants_task(tier: int = 2, batch_size: int = 50):
    """
    Indexe les objets qui n'ont pas encore d'embedding.

    Planifié via Celery Beat toutes les 30 minutes.
    """
    from django.contrib.contenttypes.models import ContentType
    from core.models import ModelEmbedding
    from core.embedding_config import get_models_for_tier, get_model_class

    configs = get_models_for_tier(tier)
    total = 0

    for app_model, cfg in configs.items():
        try:
            model_class = get_model_class(app_model)
            ct = ContentType.objects.get_for_model(model_class)

            # IDs déjà indexés
            indexed_ids = set(
                ModelEmbedding.objects.filter(
                    content_type=ct
                ).values_list('object_id', flat=True)
            )

            qs = model_class.objects.all()
            if hasattr(model_class, 'is_active'):
                qs = qs.filter(is_active=True)
            extra_filter = cfg.get('filter')
            if extra_filter:
                qs = qs.filter(**extra_filter)

            # Trouver les objets non indexés (max batch_size par modèle)
            missing = qs.exclude(pk__in=indexed_ids)[:batch_size]

            for obj in missing:
                generer_embedding_task.delay(
                    app_label=obj._meta.app_label,
                    model_name=obj._meta.model_name,
                    object_id=str(obj.pk),
                )
                total += 1

        except Exception as e:
            logger.debug(f"Erreur indexation manquants {app_model}: {e}")

    if total > 0:
        logger.info(f"Embeddings manquants: {total} tâches lancées")
    return {'queued': total}
