# core/ai/embeddings.py
"""
Service d'embeddings local avec sentence-transformers.

Modèle: paraphrase-multilingual-mpnet-base-v2
- 768 dimensions (compatible pgvector existant)
- Multilingue: FR, DE, EN, IT (parfait pour la Suisse)
- ~400MB RAM, ~50ms/embedding sur CPU
- Chargé lazily au premier appel (pas d'impact au démarrage)
"""
import logging
from typing import List, Optional

import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)


class LocalEmbeddingService:
    """
    Service d'embeddings local utilisant sentence-transformers.

    Le modèle est chargé lazily au premier appel et gardé en mémoire.
    Thread-safe (sentence-transformers gère le locking interne).
    """

    def __init__(self):
        self._model = None
        self._model_name = getattr(
            settings,
            'EMBEDDING_MODEL',
            'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
        )
        self._dimensions = getattr(settings, 'EMBEDDING_DIMENSIONS', 768)

    @property
    def model(self):
        """Charge le modèle sentence-transformers lazily."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Chargement du modèle d'embedding: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            logger.info(f"Modèle chargé ({self._dimensions}D)")
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_available(self) -> bool:
        """Le service local est toujours disponible."""
        try:
            _ = self.model
            return True
        except Exception as e:
            logger.error(f"Modèle d'embedding non disponible: {e}")
            return False

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Génère un embedding 768D pour un texte.

        Args:
            text: Texte à vectoriser (tronqué à 8192 tokens par le modèle)

        Returns:
            Liste de 768 floats, ou None si texte vide/erreur
        """
        if not text or not text.strip():
            return None

        try:
            embedding = self.model.encode(
                text,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Erreur génération embedding: {e}")
            return None

    def generate_embeddings_batch(
        self, texts: List[str], batch_size: int = 32
    ) -> List[Optional[List[float]]]:
        """
        Génère des embeddings pour plusieurs textes en batch.

        Args:
            texts: Liste de textes
            batch_size: Taille des batches (défaut 32)

        Returns:
            Liste d'embeddings (None pour les textes vides)
        """
        if not texts:
            return []

        # Séparer les textes valides et leurs indices
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_indices.append(i)
                valid_texts.append(text)

        if not valid_texts:
            return [None] * len(texts)

        try:
            embeddings = self.model.encode(
                valid_texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=batch_size,
            )

            # Reconstruire la liste avec None aux bons endroits
            results: List[Optional[List[float]]] = [None] * len(texts)
            for idx, emb in zip(valid_indices, embeddings):
                results[idx] = emb.tolist()

            return results

        except Exception as e:
            logger.error(f"Erreur génération embeddings batch: {e}")
            return [None] * len(texts)

    def compute_similarity(
        self, embedding1: List[float], embedding2: List[float],
        metric: str = 'cosine'
    ) -> float:
        """
        Calcule la similarité entre deux embeddings.

        Args:
            embedding1: Premier vecteur
            embedding2: Second vecteur
            metric: 'cosine' (défaut), 'l2', 'l1'

        Returns:
            Score de similarité (plus haut = plus similaire)
            - cosine: -1 à 1 (1 = identique)
            - l2: 0 à +inf converti en similarité (1 / (1 + distance))
            - l1: 0 à +inf converti en similarité (1 / (1 + distance))
        """
        a = np.array(embedding1)
        b = np.array(embedding2)

        if metric == 'cosine':
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))

        elif metric == 'l2':
            dist = float(np.linalg.norm(a - b))
            return 1.0 / (1.0 + dist)

        elif metric == 'l1':
            dist = float(np.sum(np.abs(a - b)))
            return 1.0 / (1.0 + dist)

        else:
            raise ValueError(f"Métrique inconnue: '{metric}'. Utiliser 'cosine', 'l2' ou 'l1'.")


# Singleton — importé partout via `from core.ai.embeddings import embedding_service`
embedding_service = LocalEmbeddingService()
