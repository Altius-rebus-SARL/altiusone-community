# documents/signals.py
"""
Signals pour le traitement automatique des documents.

Déclenche le pipeline AI (OCR, classification, embedding)
automatiquement après l'upload d'un document.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Document
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Document)
def traiter_document_apres_upload(sender, instance, created, **kwargs):
    """
    Lance le traitement automatique d'un document après upload.

    Pipeline déclenché:
    1. OCR (extraction de texte)
    2. Classification automatique
    3. Extraction de métadonnées
    4. Génération d'embedding pour recherche sémantique
    """
    if created and instance.statut_traitement == 'UPLOAD':
        # Lancer tâche asynchrone Celery pour traitement complet
        from documents.tasks import traiter_document_ocr

        logger.info(f"Déclenchement automatique traitement AI pour document {instance.id}")
        traiter_document_ocr.delay(str(instance.id))
