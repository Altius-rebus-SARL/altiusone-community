# documents/tasks.py
"""
Taches Celery pour le traitement asynchrone des documents.

Utilise le SDK AltiusOne AI pour:
- OCR (extraction de texte)
- Classification automatique
- Extraction de metadonnees
- Generation d'embeddings
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def traiter_document_ocr(self, document_id: str):
    """
    Tache Celery pour traiter un document via le SDK AltiusOne AI.

    Pipeline complet:
    1. OCR (extraction texte)
    2. Classification automatique
    3. Extraction metadonnees
    4. Generation embedding

    Args:
        document_id: UUID du document a traiter

    Retries:
        3 tentatives avec delai de 60 secondes entre chaque
    """
    from documents.models import Document, TraitementDocument
    from documents.storage import storage_service
    from documents.ai_service import ai_service, AIServiceError
    from django.utils import timezone

    try:
        document = Document.objects.get(id=document_id)
        logger.info(f"Debut traitement AI document {document_id}: {document.nom_fichier}")

        # Verifier si le service AI est disponible
        if not ai_service.enabled:
            logger.warning(f"Service AI non configure, document {document_id} mis en attente")
            return {'status': 'skipped', 'reason': 'AI service not configured'}

        # Creer un enregistrement de traitement
        traitement = TraitementDocument.objects.create(
            document=document,
            type_traitement='OCR',
            statut='EN_COURS',
            moteur='AltiusOne AI SDK'
        )

        # Mettre a jour le statut du document
        document.statut_traitement = 'OCR_EN_COURS'
        document.save(update_fields=['statut_traitement'])

        # Lire le fichier depuis le stockage (S3/MinIO)
        if not document.fichier:
            raise Exception(f"Fichier non disponible pour le document: {document.id}")

        document.fichier.open('rb')
        content = document.fichier.read()
        document.fichier.close()

        if content is None:
            raise Exception(f"Impossible de lire le fichier: {document.nom_fichier}")

        # Traitement complet via SDK AltiusOne AI
        result = ai_service.process_document(
            file_content=content,
            filename=document.nom_fichier,
            mime_type=document.mime_type,
            generate_embedding=True
        )

        if not result['success'] and result['ocr'] is None:
            raise AIServiceError(f"Echec OCR: {result['errors']}")

        # Mettre a jour le document avec les resultats OCR
        if result['ocr']:
            document.ocr_text = result['ocr']['text']
            document.ocr_confidence = result['ocr']['confidence']

        # Classification
        if result['classification']:
            document.prediction_type = result['classification']['type_document']
            document.prediction_confidence = result['classification']['confidence']
            document.tags_auto = result['classification']['tags']

        # Metadonnees
        if result['metadata']:
            document.metadata_extraite = result['metadata']

        document.statut_traitement = 'OCR_TERMINE'
        document.save()

        # Sauvegarder l'embedding
        if result['embedding']:
            from documents.models import DocumentEmbedding
            import hashlib

            text = document.ocr_text or document.description or document.nom_fichier
            text_hash = hashlib.sha256(text.encode()).hexdigest()

            DocumentEmbedding.objects.update_or_create(
                document=document,
                defaults={
                    'embedding': result['embedding'],
                    'model_used': 'altiusone-768',
                    'dimensions': 768,
                    'text_hash': text_hash,
                    'text_length': len(text)
                }
            )

        # Mettre a jour le traitement
        traitement.statut = 'TERMINE'
        traitement.date_fin = timezone.now()
        traitement.resultat = {
            'ocr_success': result['ocr'] is not None,
            'classification': result['classification'],
            'metadata_count': len(result['metadata']) if result['metadata'] else 0,
            'embedding_generated': result['embedding'] is not None,
            'errors': result['errors']
        }
        traitement.save()

        logger.info(f"Document {document_id} traite avec succes")

        # Declencher la decouverte de relations si embedding genere
        if result['embedding']:
            try:
                from documents.tasks_intelligence import decouvrir_relations_document
                decouvrir_relations_document.delay(str(document_id))
            except Exception as e:
                logger.warning(f"Impossible de lancer decouverte relations: {e}")

        return {
            'status': 'success',
            'document_id': str(document_id),
            'type_document': result['classification']['type_document'] if result['classification'] else None,
            'confidence': result['classification']['confidence'] if result['classification'] else 0,
            'embedding_generated': result['embedding'] is not None
        }

    except Document.DoesNotExist:
        logger.error(f"Document {document_id} non trouve")
        return {'status': 'error', 'reason': 'Document not found'}

    except AIServiceError as e:
        logger.error(f"Erreur AI pour document {document_id}: {e}")

        # Mettre a jour le traitement si cree
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
    Tache periodique pour traiter les documents en attente d'OCR et relancer ceux en erreur.
    A planifier via Celery Beat (ex: toutes les 5 minutes).

    Gere aussi les documents bloques (EN_COURS depuis plus de 5 minutes).
    """
    from documents.models import Document
    from documents.ai_service import ai_service
    from django.db.models import Q
    from django.utils import timezone
    from datetime import timedelta

    if not ai_service.enabled:
        logger.warning("Service AI non configure, traitement en attente ignore")
        return {'documents_queued': 0, 'errors_retried': 0, 'stuck_reset': 0, 'reason': 'AI service not configured'}

    # 1. Reset des documents BLOQUES (EN_COURS depuis plus de 5 minutes)
    seuil_blocage = timezone.now() - timedelta(minutes=5)
    documents_bloques = Document.objects.filter(
        statut_traitement__in=['OCR_EN_COURS', 'CLASSIFICATION_EN_COURS', 'EXTRACTION_EN_COURS'],
        updated_at__lt=seuil_blocage
    )
    stuck_count = documents_bloques.count()
    if stuck_count > 0:
        logger.warning(f"Reset de {stuck_count} documents bloques depuis plus de 5 minutes")
        documents_bloques.update(statut_traitement='UPLOAD')

    # 2. Documents en attente (nouveaux uploads) - traiter par batch
    documents_upload = Document.objects.filter(
        statut_traitement='UPLOAD'
    ).order_by('date_upload')[:10]

    # 3. Documents en erreur a relancer (max 5 par cycle pour ne pas surcharger)
    documents_erreur = Document.objects.filter(
        statut_traitement='ERREUR'
    ).order_by('updated_at')[:5]

    # Relancer les documents en attente
    for doc in documents_upload:
        traiter_document_ocr.delay(str(doc.id))

    # Relancer les documents en erreur (reset du statut)
    for doc in documents_erreur:
        doc.statut_traitement = 'UPLOAD'
        doc.save(update_fields=['statut_traitement'])
        traiter_document_ocr.delay(str(doc.id))

    total_upload = len(documents_upload)
    total_erreur = len(documents_erreur)

    if total_upload > 0 or total_erreur > 0 or stuck_count > 0:
        logger.info(f"Traitement AI: {total_upload} nouveaux, {total_erreur} erreurs, {stuck_count} bloques resets")

    return {
        'documents_queued': total_upload,
        'errors_retried': total_erreur,
        'stuck_reset': stuck_count
    }


@shared_task
def classifier_document(document_id: str):
    """
    Tache pour classifier un document (si deja OCR effectue).
    """
    from documents.models import Document, TraitementDocument
    from documents.ai_service import ai_service, AIServiceError
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
            moteur='AltiusOne AI SDK'
        )

        document.statut_traitement = 'CLASSIFICATION_EN_COURS'
        document.save(update_fields=['statut_traitement'])

        result = ai_service.classify_document(
            text=document.ocr_text,
            filename=document.nom_fichier
        )

        document.prediction_type = result.type_document
        document.prediction_confidence = result.confidence
        document.tags_auto = result.tags
        document.statut_traitement = 'CLASSIFICATION_TERMINEE'
        document.save()

        traitement.statut = 'TERMINE'
        traitement.date_fin = timezone.now()
        traitement.resultat = {
            'type_document': result.type_document,
            'confidence': result.confidence,
            'tags': result.tags
        }
        traitement.save()

        return {
            'status': 'success',
            'type_document': result.type_document,
            'confidence': result.confidence
        }

    except Document.DoesNotExist:
        return {'status': 'error', 'reason': 'Document not found'}
    except AIServiceError as e:
        logger.error(f"Erreur classification document {document_id}: {e}")
        return {'status': 'error', 'reason': str(e)}


@shared_task
def extraire_metadonnees(document_id: str):
    """
    Tache pour extraire les metadonnees d'un document classifie.
    """
    from documents.models import Document, TraitementDocument
    from documents.ai_service import ai_service, AIServiceError
    from django.utils import timezone

    try:
        document = Document.objects.get(id=document_id)

        if not document.ocr_text or not document.prediction_type:
            return {'status': 'skipped', 'reason': 'Missing OCR text or classification'}

        traitement = TraitementDocument.objects.create(
            document=document,
            type_traitement='EXTRACTION',
            statut='EN_COURS',
            moteur='AltiusOne AI SDK'
        )

        document.statut_traitement = 'EXTRACTION_EN_COURS'
        document.save(update_fields=['statut_traitement'])

        # Recuperer le template d'extraction si defini
        custom_schema = None
        if document.type_document and document.type_document.template_extraction:
            custom_schema = document.type_document.template_extraction

        result = ai_service.extract_metadata(
            text=document.ocr_text,
            type_document=document.prediction_type,
            custom_schema=custom_schema
        )

        document.metadata_extraite = result.data
        document.statut_traitement = 'EXTRACTION_TERMINEE'
        document.save()

        traitement.statut = 'TERMINE'
        traitement.date_fin = timezone.now()
        traitement.resultat = result.data
        traitement.save()

        return {
            'status': 'success',
            'metadata': result.data
        }

    except Document.DoesNotExist:
        return {'status': 'error', 'reason': 'Document not found'}
    except AIServiceError as e:
        logger.error(f"Erreur extraction metadonnees document {document_id}: {e}")
        return {'status': 'error', 'reason': str(e)}


# ============================================================================
# TACHES D'INDEXATION VECTORIELLE (PGVector)
# ============================================================================

@shared_task
def indexer_document_embedding(document_id: str):
    """
    Genere et stocke l'embedding d'un document pour la recherche semantique.

    Utilise le SDK AltiusOne AI (768 dimensions).
    """
    from documents.models import Document
    from documents.search import search_service

    try:
        document = Document.objects.get(id=document_id)

        # Verifier qu'il y a du texte a indexer
        text = document.ocr_text or document.description
        if not text:
            logger.warning(f"Document {document_id} n'a pas de texte a indexer")
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
    Indexe un document en le decoupant en chunks (pour documents longs).
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
    Reindexe tous les documents d'un mandat ou de toute la base.
    Tache a lancer manuellement ou periodiquement.

    IMPORTANT: A executer apres la migration vers 768D.
    """
    from documents.search import search_service
    from documents.ai_service import ai_service

    if not ai_service.enabled:
        logger.error("Service AI non configure, reindexation impossible")
        return {'status': 'error', 'reason': 'AI service not configured'}

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
        logger.error(f"Erreur reindexation documents: {e}")
        return {'status': 'error', 'reason': str(e)}


@shared_task
def indexer_documents_sans_embedding():
    """
    Tache periodique pour indexer les documents sans embedding.
    A planifier via Celery Beat (ex: toutes les heures).
    """
    from documents.models import Document, DocumentEmbedding
    from documents.search import search_service
    from documents.ai_service import ai_service

    if not ai_service.enabled:
        logger.warning("Service AI non configure, indexation automatique ignoree")
        return {'indexed_count': 0, 'reason': 'AI service not configured'}

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
    ).order_by('-created_at')[:100]  # Limiter a 100 par execution

    indexed_count = 0
    for doc in documents_a_indexer:
        if search_service.index_document(doc):
            indexed_count += 1

    logger.info(f"Indexation automatique: {indexed_count} documents indexes")
    return {'indexed_count': indexed_count}


# ============================================================================
# TACHES UTILITAIRES
# ============================================================================

@shared_task
def verifier_service_ai():
    """
    Tache pour verifier l'etat du service AI.
    Utile pour le monitoring.
    """
    from documents.ai_service import ai_service

    status = ai_service.health_check()
    logger.info(f"Verification service AI: {status}")
    return status
