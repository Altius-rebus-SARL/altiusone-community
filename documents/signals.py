# documents/signals.py
"""
Signals pour le traitement automatique des documents
et la mise à jour des statistiques dénormalisées.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Document
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Document)
def traiter_document_apres_upload(sender, instance, created, **kwargs):
    """
    Lance le traitement automatique d'un document après upload.

    Le signal est le SEUL point d'entrée pour le lancement OCR.
    Les vues ne doivent PAS lancer traiter_document_ocr directement
    lors de la création (seulement pour un re-traitement manuel).
    """
    if created and instance.statut_traitement == 'UPLOAD':
        if getattr(settings, 'OCR_SERVICE_ENABLED', True):
            from documents.tasks import traiter_document_ocr

            logger.info(f"Déclenchement automatique traitement AI pour document {instance.id}")
            traiter_document_ocr.delay(str(instance.id))


@receiver(post_save, sender=Document)
def maj_stats_dossier_apres_save(sender, instance, **kwargs):
    """Met à jour les stats dénormalisées du dossier parent après save."""
    if instance.dossier_id:
        instance.dossier.mettre_a_jour_stats()


@receiver(post_delete, sender=Document)
def maj_stats_dossier_apres_delete(sender, instance, **kwargs):
    """Met à jour les stats dénormalisées du dossier parent après suppression."""
    if instance.dossier_id:
        try:
            instance.dossier.mettre_a_jour_stats()
        except Exception:
            # Le dossier peut avoir été supprimé aussi (cascade)
            pass


@receiver(post_delete, sender=Document)
def cleanup_fichier_minio(sender, instance, **kwargs):
    """
    Supprime le fichier physique dans MinIO/S3 quand un Document est supprimé.
    Empêche les fichiers orphelins après suppression en cascade.
    """
    if instance.fichier:
        try:
            # storage.delete() gère S3 et local
            instance.fichier.delete(save=False)
            logger.info(f"Fichier supprimé du stockage: {instance.fichier.name}")
        except Exception as e:
            logger.warning(f"Impossible de supprimer le fichier {instance.fichier.name}: {e}")
