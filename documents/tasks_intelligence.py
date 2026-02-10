# documents/tasks_intelligence.py
"""
Taches Celery pour le moteur d'intelligence AI.

- decouvrir_relations_document: Apres chaque indexation
- analyser_mandat_complet: Analyse complete d'un mandat
- analyser_mandats_actifs: Analyse quotidienne
- generer_digests_hebdomadaires: Digests lundi matin
- generer_digests_mensuels: Digests 1er du mois
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def decouvrir_relations_document(self, document_id: str):
    """
    Detecte les relations d'un nouveau document avec les existants.

    Appelée automatiquement après l'indexation embedding d'un document.
    """
    from documents.models import Document
    from documents.services.relation_service import RelationService

    try:
        document = Document.objects.select_related('mandat').get(id=document_id)
        service = RelationService()
        relations = service.decouvrir_relations(document)

        return {
            'status': 'success',
            'document_id': str(document_id),
            'relations_creees': len(relations),
        }

    except Document.DoesNotExist:
        logger.error(f"Document {document_id} non trouvé")
        return {'status': 'error', 'reason': 'Document not found'}

    except Exception as e:
        logger.error(f"Erreur découverte relations document {document_id}: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=1, default_retry_delay=300)
def analyser_mandat_complet(self, mandat_id: str):
    """
    Analyse complete d'un mandat: relations, anomalies, coherence, tendances.

    Peut etre declenchée manuellement ou periodiquement.
    """
    from documents.services.relation_service import RelationService
    from documents.services.insight_service import InsightService
    from documents.services.temporal_service import TemporalAnalysisService

    try:
        logger.info(f"Début analyse complète mandat {mandat_id}")

        # 1. Detection doublons
        relation_service = RelationService()
        doublons = relation_service.detecter_doublons_mandat(mandat_id)

        # 2. Insights (anomalies, documents manquants, coherence)
        insight_service = InsightService()
        insights = insight_service.analyser_mandat(mandat_id)

        # 3. Anomalies temporelles
        temporal_service = TemporalAnalysisService()
        temporal_insights = temporal_service.detecter_anomalies_temporelles(mandat_id)

        return {
            'status': 'success',
            'mandat_id': mandat_id,
            'doublons': len(doublons),
            'insights': len(insights),
            'anomalies_temporelles': len(temporal_insights),
        }

    except Exception as e:
        logger.error(f"Erreur analyse mandat {mandat_id}: {e}")
        raise self.retry(exc=e)


@shared_task
def analyser_mandats_actifs():
    """
    Analyse quotidienne de tous les mandats actifs.

    Planifiée via Celery Beat: chaque nuit à 02h00.
    """
    from core.models import Mandat

    mandats = Mandat.objects.filter(statut='ACTIF')
    count = 0

    for mandat in mandats:
        try:
            analyser_mandat_complet.delay(str(mandat.id))
            count += 1
        except Exception as e:
            logger.error(f"Erreur lancement analyse mandat {mandat.numero}: {e}")

    logger.info(f"Analyse quotidienne: {count} mandats lancés")
    return {'mandats_lances': count}


@shared_task
def generer_digests_hebdomadaires():
    """
    Genere les digests hebdomadaires pour tous les mandats actifs.

    Planifiée via Celery Beat: lundi à 06h00.
    """
    from documents.services.digest_service import DigestService

    try:
        service = DigestService()
        count = service.generer_digests_hebdomadaires()
        return {'status': 'success', 'digests_generes': count}
    except Exception as e:
        logger.error(f"Erreur génération digests hebdomadaires: {e}")
        return {'status': 'error', 'reason': str(e)}


@shared_task
def generer_digests_mensuels():
    """
    Genere les digests mensuels pour tous les mandats actifs.

    Planifiée via Celery Beat: 1er du mois à 06h00.
    """
    from documents.services.digest_service import DigestService

    try:
        service = DigestService()
        count = service.generer_digests_mensuels()
        return {'status': 'success', 'digests_generes': count}
    except Exception as e:
        logger.error(f"Erreur génération digests mensuels: {e}")
        return {'status': 'error', 'reason': str(e)}
