# graph/services/embedding.py
"""Service d'embeddings pour les entités du graphe."""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def generer_embedding_entite(entite):
    """
    Génère un embedding vectoriel pour une entité.

    Concatène type.nom + nom + description + attributs, puis
    appelle le service d'embedding partagé de documents/.

    Returns:
        list[float] | None: Vecteur 768D ou None si erreur
    """
    from documents.embeddings import embedding_service

    texte = entite.texte_pour_embedding()
    if not texte or not texte.strip():
        return None

    try:
        embedding = embedding_service.generate_embedding(texte)
        return embedding
    except Exception as e:
        logger.error(f"Erreur embedding entité {entite.pk}: {e}")
        return None


def mettre_a_jour_embedding(entite_id):
    """
    Charge une entité, génère son embedding et le sauvegarde.

    Args:
        entite_id: UUID de l'entité

    Returns:
        bool: True si mis à jour, False sinon
    """
    from graph.models import Entite

    try:
        entite = Entite.objects.select_related('type').get(pk=entite_id)
    except Entite.DoesNotExist:
        logger.error(f"Entité introuvable: {entite_id}")
        return False

    embedding = generer_embedding_entite(entite)
    if embedding is not None:
        entite.embedding = embedding
        entite.embedding_updated_at = timezone.now()
        entite.save(update_fields=['embedding', 'embedding_updated_at'])
        logger.info(f"Embedding mis à jour pour entité {entite.nom} ({entite_id})")
        return True

    return False
