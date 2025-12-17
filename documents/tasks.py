# documents/tasks.py
"""
Tâches Celery pour le traitement asynchrone des documents.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def traiter_document_ocr(self, document_id: str):
    """
    Tâche Celery pour traiter un document via le service OCR externe.

    Args:
        document_id: UUID du document à traiter

    Retries:
        3 tentatives avec délai de 60 secondes entre chaque
    """
    from documents.models import Document, TraitementDocument
    from documents.storage import storage_service
    from documents.ocr_client import ocr_client, OCRServiceError
    from django.utils import timezone

    try:
        document = Document.objects.get(id=document_id)
        logger.info(f"Début traitement OCR document {document_id}: {document.nom_fichier}")

        # Vérifier si le service OCR est disponible
        if not ocr_client.enabled:
            logger.warning(f"Service OCR désactivé, document {document_id} mis en attente")
            return {'status': 'skipped', 'reason': 'OCR service disabled'}

        # Créer un enregistrement de traitement
        traitement = TraitementDocument.objects.create(
            document=document,
            type_traitement='OCR',
            statut='EN_COURS',
            moteur='Service OCR externe'
        )

        # Mettre à jour le statut du document
        document.statut_traitement = 'OCR_EN_COURS'
        document.save(update_fields=['statut_traitement'])

        # Télécharger le fichier depuis le stockage
        content = storage_service.telecharger_fichier(document.path_storage)
        if content is None:
            raise Exception(f"Impossible de télécharger le fichier: {document.path_storage}")

        # Traitement complet via service OCR
        result = ocr_client.traiter_document_complet(
            file_content=content,
            filename=document.nom_fichier,
            mime_type=document.mime_type,
            mandat_id=str(document.mandat_id)
        )

        # Mettre à jour le document avec les résultats
        document.ocr_text = result['ocr']['text']
        document.ocr_confidence = result['ocr']['confidence']
        document.prediction_type = result['classification']['type_document']
        document.prediction_confidence = result['classification']['confidence']
        document.tags_auto = result['classification']['tags']
        document.metadata_extraite = result['metadata']
        document.statut_traitement = 'OCR_TERMINE'
        document.save()

        # Mettre à jour le traitement
        traitement.statut = 'TERMINE'
        traitement.date_fin = timezone.now()
        traitement.resultat = result
        traitement.duree_secondes = int(result.get('processing_time', 0))
        traitement.save()

        logger.info(f"Document {document_id} traité avec succès en {traitement.duree_secondes}s")

        return {
            'status': 'success',
            'document_id': str(document_id),
            'type_document': result['classification']['type_document'],
            'confidence': result['classification']['confidence'],
            'processing_time': result.get('processing_time', 0)
        }

    except Document.DoesNotExist:
        logger.error(f"Document {document_id} non trouvé")
        return {'status': 'error', 'reason': 'Document not found'}

    except OCRServiceError as e:
        logger.error(f"Erreur OCR pour document {document_id}: {e}")

        # Mettre à jour le traitement si créé
        try:
            traitement.statut = 'ERREUR'
            traitement.erreur = str(e)
            traitement.date_fin = timezone.now()
            traitement.save()

            document.statut_traitement = 'ERREUR'
            document.save(update_fields=['statut_traitement'])
        except Exception:
            pass

        # Retry si possible
        raise self.retry(exc=e)

    except Exception as e:
        logger.error(f"Erreur inattendue traitement document {document_id}: {e}")
        raise self.retry(exc=e)


@shared_task
def traiter_documents_en_attente():
    """
    Tâche périodique pour traiter les documents en attente d'OCR.
    À planifier via Celery Beat (ex: toutes les 5 minutes).
    """
    from documents.models import Document

    documents = Document.objects.filter(
        statut_traitement='UPLOAD'
    ).order_by('date_upload')[:10]  # Traiter max 10 à la fois

    for doc in documents:
        traiter_document_ocr.delay(str(doc.id))

    logger.info(f"Lancé traitement OCR pour {len(documents)} documents")
    return {'documents_queued': len(documents)}


@shared_task
def classifier_document(document_id: str):
    """
    Tâche pour classifier un document (si déjà OCR effectué).
    """
    from documents.models import Document, TraitementDocument
    from documents.ocr_client import ocr_client, OCRServiceError
    from django.utils import timezone

    try:
        document = Document.objects.get(id=document_id)

        if not document.ocr_text:
            logger.warning(f"Document {document_id} n'a pas de texte OCR")
            return {'status': 'skipped', 'reason': 'No OCR text'}

        traitement = TraitementDocument.objects.create(
            document=document,
            type_traitement='CLASSIFICATION',
            statut='EN_COURS',
            moteur='Service OCR externe - Classification'
        )

        document.statut_traitement = 'CLASSIFICATION_EN_COURS'
        document.save(update_fields=['statut_traitement'])

        result = ocr_client.classifier_document(
            text=document.ocr_text,
            filename=document.nom_fichier
        )

        document.prediction_type = result['type_document']
        document.prediction_confidence = result['confidence']
        document.tags_auto = result.get('tags', [])
        document.statut_traitement = 'CLASSIFICATION_TERMINEE'
        document.save()

        traitement.statut = 'TERMINE'
        traitement.date_fin = timezone.now()
        traitement.resultat = result
        traitement.save()

        return {
            'status': 'success',
            'type_document': result['type_document'],
            'confidence': result['confidence']
        }

    except Document.DoesNotExist:
        return {'status': 'error', 'reason': 'Document not found'}
    except OCRServiceError as e:
        logger.error(f"Erreur classification document {document_id}: {e}")
        return {'status': 'error', 'reason': str(e)}


@shared_task
def extraire_metadonnees(document_id: str):
    """
    Tâche pour extraire les métadonnées d'un document classifié.
    """
    from documents.models import Document, TraitementDocument
    from documents.ocr_client import ocr_client, OCRServiceError
    from django.utils import timezone

    try:
        document = Document.objects.get(id=document_id)

        if not document.ocr_text or not document.prediction_type:
            return {'status': 'skipped', 'reason': 'Missing OCR text or classification'}

        traitement = TraitementDocument.objects.create(
            document=document,
            type_traitement='EXTRACTION',
            statut='EN_COURS',
            moteur='Service OCR externe - Extraction'
        )

        document.statut_traitement = 'EXTRACTION_EN_COURS'
        document.save(update_fields=['statut_traitement'])

        # Récupérer le template d'extraction si défini
        template = None
        if document.type_document and document.type_document.template_extraction:
            template = document.type_document.template_extraction

        result = ocr_client.extraire_metadonnees(
            text=document.ocr_text,
            type_document=document.prediction_type,
            template=template
        )

        document.metadata_extraite = result
        document.statut_traitement = 'EXTRACTION_TERMINEE'
        document.save()

        traitement.statut = 'TERMINE'
        traitement.date_fin = timezone.now()
        traitement.resultat = result
        traitement.save()

        return {
            'status': 'success',
            'metadata': result
        }

    except Document.DoesNotExist:
        return {'status': 'error', 'reason': 'Document not found'}
    except OCRServiceError as e:
        logger.error(f"Erreur extraction métadonnées document {document_id}: {e}")
        return {'status': 'error', 'reason': str(e)}


# ============================================================================
# TÂCHES D'INDEXATION VECTORIELLE (PGVector)
# ============================================================================

@shared_task
def indexer_document_embedding(document_id: str):
    """
    Génère et stocke l'embedding d'un document pour la recherche sémantique.

    Utilise le texte OCR ou la description du document.
    """
    from documents.models import Document
    from documents.search import search_service

    try:
        document = Document.objects.get(id=document_id)

        # Vérifier qu'il y a du texte à indexer
        text = document.ocr_text or document.description
        if not text:
            logger.warning(f"Document {document_id} n'a pas de texte à indexer")
            return {'status': 'skipped', 'reason': 'No text to index'}

        # Indexer le document
        success = search_service.index_document(document)

        if success:
            return {'status': 'success', 'document_id': str(document_id)}
        else:
            return {'status': 'error', 'reason': 'Indexation failed'}

    except Document.DoesNotExist:
        return {'status': 'error', 'reason': 'Document not found'}
    except Exception as e:
        logger.error(f"Erreur indexation document {document_id}: {e}")
        return {'status': 'error', 'reason': str(e)}


@shared_task
def indexer_document_chunks(document_id: str, chunk_size: int = 1000):
    """
    Indexe un document en le découpant en chunks (pour documents longs).
    """
    from documents.models import Document
    from documents.search import search_service

    try:
        document = Document.objects.get(id=document_id)

        text = document.ocr_text or document.description
        if not text:
            return {'status': 'skipped', 'reason': 'No text to index'}

        # Indexer en chunks si document long
        if len(text) > chunk_size * 2:
            chunks_count = search_service.index_document_with_chunks(
                document,
                chunk_size=chunk_size,
                overlap=200
            )
            return {
                'status': 'success',
                'document_id': str(document_id),
                'chunks_indexed': chunks_count
            }
        else:
            # Document court: indexation simple
            success = search_service.index_document(document)
            return {
                'status': 'success' if success else 'error',
                'document_id': str(document_id)
            }

    except Document.DoesNotExist:
        return {'status': 'error', 'reason': 'Document not found'}
    except Exception as e:
        logger.error(f"Erreur indexation chunks document {document_id}: {e}")
        return {'status': 'error', 'reason': str(e)}


@shared_task
def reindexer_tous_documents(mandat_id: str = None, batch_size: int = 50):
    """
    Réindexe tous les documents d'un mandat ou de toute la base.
    Tâche à lancer manuellement ou périodiquement.
    """
    from documents.search import search_service

    try:
        indexed, errors = search_service.reindex_all_documents(
            mandat_id=mandat_id,
            batch_size=batch_size
        )

        return {
            'status': 'success',
            'indexed_count': indexed,
            'error_count': errors,
            'mandat_id': mandat_id
        }

    except Exception as e:
        logger.error(f"Erreur réindexation documents: {e}")
        return {'status': 'error', 'reason': str(e)}


@shared_task
def indexer_documents_sans_embedding():
    """
    Tâche périodique pour indexer les documents sans embedding.
    À planifier via Celery Beat (ex: toutes les heures).
    """
    from documents.models import Document, DocumentEmbedding
    from documents.search import search_service

    # Trouver les documents avec texte mais sans embedding
    documents_avec_embedding = DocumentEmbedding.objects.values_list('document_id', flat=True)

    documents_a_indexer = Document.objects.filter(
        is_active=True
    ).exclude(
        id__in=documents_avec_embedding
    ).exclude(
        ocr_text=''
    ).exclude(
        ocr_text__isnull=True
    ).order_by('-created_at')[:100]  # Limiter à 100 par exécution

    indexed_count = 0
    for doc in documents_a_indexer:
        if search_service.index_document(doc):
            indexed_count += 1

    logger.info(f"Indexation automatique: {indexed_count} documents indexés")
    return {'indexed_count': indexed_count}
