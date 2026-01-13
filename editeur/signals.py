"""
Signaux Django pour l'application Éditeur Collaboratif.

Gère la synchronisation automatique entre AltiusOne et Docs.
"""

import logging
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.conf import settings

from .models import DocumentCollaboratif, PartageDocument
from .docs_service import docs_service, DocsServiceError

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DocumentCollaboratif)
def sync_document_title(sender, instance, created, **kwargs):
    """
    Synchronise le titre du document avec Docs lors des modifications.
    """
    if created:
        # La création est gérée dans la vue
        return

    # Éviter les boucles infinies avec un flag
    if getattr(instance, '_skip_sync', False):
        return

    # Si le titre a changé, mettre à jour dans Docs
    if instance.tracker.has_changed('titre') if hasattr(instance, 'tracker') else False:
        try:
            docs_service.update_document(
                instance.docs_id,
                title=instance.titre
            )
            logger.info(f"Titre synchronisé avec Docs: {instance.docs_id}")
        except DocsServiceError as e:
            logger.warning(f"Erreur sync titre Docs: {e}")


@receiver(pre_delete, sender=DocumentCollaboratif)
def delete_docs_document(sender, instance, **kwargs):
    """
    Supprime le document de Docs lors de la suppression locale.
    """
    if instance.docs_id:
        try:
            docs_service.delete_document(instance.docs_id)
            logger.info(f"Document supprimé de Docs: {instance.docs_id}")
        except DocsServiceError as e:
            logger.warning(f"Erreur suppression Docs (continuer quand même): {e}")


@receiver(post_save, sender=PartageDocument)
def sync_collaborator_added(sender, instance, created, **kwargs):
    """
    Synchronise l'ajout d'un collaborateur avec Docs.
    """
    if not created:
        return

    # Éviter les boucles si déjà synchro via la vue
    if getattr(instance, '_synced_to_docs', False):
        return

    permission_map = {
        'LECTURE': 'view',
        'COMMENTAIRE': 'comment',
        'EDITION': 'edit',
        'ADMIN': 'admin'
    }

    try:
        docs_service.add_collaborator(
            instance.document.docs_id,
            instance.utilisateur,
            permission_map.get(instance.niveau_acces, 'view')
        )
        logger.info(
            f"Collaborateur ajouté à Docs: {instance.utilisateur.email} "
            f"sur {instance.document.docs_id}"
        )
    except DocsServiceError as e:
        logger.warning(f"Erreur ajout collaborateur Docs: {e}")


@receiver(post_delete, sender=PartageDocument)
def sync_collaborator_removed(sender, instance, **kwargs):
    """
    Synchronise le retrait d'un collaborateur avec Docs.
    """
    # Éviter les boucles si déjà synchro via la vue
    if getattr(instance, '_synced_to_docs', False):
        return

    try:
        docs_service.remove_collaborator(
            instance.document.docs_id,
            instance.utilisateur
        )
        logger.info(
            f"Collaborateur retiré de Docs: {instance.utilisateur.email} "
            f"de {instance.document.docs_id}"
        )
    except DocsServiceError as e:
        logger.warning(f"Erreur retrait collaborateur Docs: {e}")


# =============================================================================
# Signal pour la création automatique de dossiers éditeur par mandat
# =============================================================================

def create_editeur_defaults_for_mandat(sender, instance, created, **kwargs):
    """
    Crée les ressources par défaut de l'éditeur pour un nouveau mandat.

    Appelé depuis core.signals lors de la création d'un mandat.
    """
    if not created:
        return

    # Cette fonction peut être appelée depuis core.signals
    # pour créer des modèles par défaut spécifiques au mandat
    pass
