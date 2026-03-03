# documents/embeddings.py
"""
Service d'embeddings pour la recherche semantique avec PGVector.

Utilise le SDK AltiusOne AI pour generer des embeddings 768D.
Ce module est un wrapper autour de ai_service.py pour maintenir
la compatibilite avec le code existant.
"""
import logging
from typing import List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service pour generer des embeddings vectoriels.

    Utilise le SDK AltiusOne AI (768 dimensions).
    Maintient la compatibilite avec l'ancienne interface.
    """

    # Dimensions du modele AltiusOne AI
    MODEL_DIMENSIONS = {
        'altiusone-768': 768,
        # Legacy models (pour compatibilite)
        'text-embedding-3-small': 1536,
        'text-embedding-3-large': 3072,
        'paraphrase-multilingual-MiniLM-L12-v2': 384,
        'paraphrase-multilingual-mpnet-base-v2': 768,
    }

    def __init__(self):
        self.backend = 'altiusone'
        self._ai_service = None

    @property
    def ai_service(self):
        """Acces au service AI (lazy loading)."""
        if self._ai_service is None:
            from documents.ai_service import ai_service
            self._ai_service = ai_service
        return self._ai_service

    @property
    def dimensions(self) -> int:
        """Retourne le nombre de dimensions du modele (768)."""
        return 768

    @property
    def model_name(self) -> str:
        """Retourne le nom du modele utilise."""
        return 'altiusone-768'

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Genere un embedding pour un texte.

        Args:
            text: Texte a vectoriser

        Returns:
            Liste de floats representant le vecteur (768D), ou None si erreur
        """
        if not text or not text.strip():
            return None

        try:
            return self.ai_service.embed(text)
        except Exception as e:
            logger.error(f"Erreur generation embedding: {e}")
            return None

    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Genere des embeddings pour plusieurs textes.

        Args:
            texts: Liste de textes

        Returns:
            Liste d'embeddings (ou None pour les textes vides/erreurs)
        """
        if not texts:
            return []

        try:
            return self.ai_service.embed_batch(texts)
        except Exception as e:
            logger.error(f"Erreur generation embeddings batch: {e}")
            return [None] * len(texts)

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calcule la similarite cosinus entre deux embeddings.

        Returns:
            Score entre 0 et 1 (1 = identique)
        """
        return self.ai_service.compute_similarity(embedding1, embedding2)

    def is_available(self) -> bool:
        """Verifie si le service d'embeddings est disponible."""
        return self.ai_service.enabled


# Instance singleton
embedding_service = EmbeddingService()
