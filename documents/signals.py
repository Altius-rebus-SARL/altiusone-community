# documents/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Document


@receiver(post_save, sender=Document)
def traiter_document(sender, instance, created, **kwargs):
    """Lance le traitement automatique d'un document"""
    if created:
        # Lancer tâche asynchrone Celery pour OCR et classification
        from documents.tasks import traiter_document_async
        traiter_document_async.delay(instance.id)
