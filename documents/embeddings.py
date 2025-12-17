# documents/embeddings.py
"""
Service d'embeddings pour la recherche sémantique avec PGVector.

Supporte plusieurs backends:
- OpenAI (text-embedding-3-small, text-embedding-3-large)
- Local avec sentence-transformers (multilingual)
"""
import logging
from typing import List, Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service pour générer des embeddings vectoriels.

    Utilise OpenAI par défaut, avec fallback sur sentence-transformers local.
    """

    # Dimensions selon le modèle
    MODEL_DIMENSIONS = {
        'text-embedding-3-small': 1536,
        'text-embedding-3-large': 3072,
        'text-embedding-ada-002': 1536,
        'paraphrase-multilingual-MiniLM-L12-v2': 384,
        'paraphrase-multilingual-mpnet-base-v2': 768,
        'all-MiniLM-L6-v2': 384,
    }

    def __init__(self):
        self.backend = getattr(settings, 'EMBEDDING_BACKEND', 'openai')
        self.openai_model = getattr(settings, 'OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
        self.local_model = getattr(settings, 'LOCAL_EMBEDDING_MODEL', 'paraphrase-multilingual-MiniLM-L12-v2')
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', '')

        self._openai_client = None
        self._local_model = None

    @property
    def dimensions(self) -> int:
        """Retourne le nombre de dimensions du modèle actuel."""
        if self.backend == 'openai':
            return self.MODEL_DIMENSIONS.get(self.openai_model, 1536)
        else:
            return self.MODEL_DIMENSIONS.get(self.local_model, 384)

    def _get_openai_client(self):
        """Initialise le client OpenAI à la demande."""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_api_key)
            except ImportError:
                logger.error("Package openai non installé")
                raise
        return self._openai_client

    def _get_local_model(self):
        """Initialise le modèle local à la demande."""
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer(self.local_model)
                logger.info(f"Modèle local chargé: {self.local_model}")
            except ImportError:
                logger.error("Package sentence-transformers non installé")
                raise
        return self._local_model

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Génère un embedding pour un texte.

        Args:
            text: Texte à vectoriser

        Returns:
            Liste de floats représentant le vecteur, ou None si erreur
        """
        if not text or not text.strip():
            return None

        # Tronquer le texte si trop long (limite OpenAI: ~8000 tokens)
        text = text[:30000]

        try:
            if self.backend == 'openai' and self.openai_api_key:
                return self._generate_openai_embedding(text)
            else:
                return self._generate_local_embedding(text)
        except Exception as e:
            logger.error(f"Erreur génération embedding: {e}")
            # Fallback sur local si OpenAI échoue
            if self.backend == 'openai':
                try:
                    return self._generate_local_embedding(text)
                except Exception:
                    pass
            return None

    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Génère un embedding via OpenAI."""
        client = self._get_openai_client()

        response = client.embeddings.create(
            model=self.openai_model,
            input=text,
            encoding_format="float"
        )

        return response.data[0].embedding

    def _generate_local_embedding(self, text: str) -> List[float]:
        """Génère un embedding via sentence-transformers local."""
        model = self._get_local_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Génère des embeddings pour plusieurs textes.
        Plus efficace que d'appeler generate_embedding en boucle.

        Args:
            texts: Liste de textes

        Returns:
            Liste d'embeddings (ou None pour les textes vides)
        """
        if not texts:
            return []

        # Filtrer les textes vides
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        valid_texts = [texts[i][:30000] for i in valid_indices]

        if not valid_texts:
            return [None] * len(texts)

        try:
            if self.backend == 'openai' and self.openai_api_key:
                embeddings = self._generate_openai_embeddings_batch(valid_texts)
            else:
                embeddings = self._generate_local_embeddings_batch(valid_texts)

            # Reconstruire la liste avec None pour les textes vides
            result = [None] * len(texts)
            for idx, emb in zip(valid_indices, embeddings):
                result[idx] = emb

            return result

        except Exception as e:
            logger.error(f"Erreur génération embeddings batch: {e}")
            return [None] * len(texts)

    def _generate_openai_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Génère des embeddings en batch via OpenAI."""
        client = self._get_openai_client()

        response = client.embeddings.create(
            model=self.openai_model,
            input=texts,
            encoding_format="float"
        )

        # Trier par index pour garantir l'ordre
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [d.embedding for d in sorted_data]

    def _generate_local_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Génère des embeddings en batch via sentence-transformers."""
        model = self._get_local_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calcule la similarité cosinus entre deux embeddings.

        Returns:
            Score entre 0 et 1 (1 = identique)
        """
        import numpy as np

        a = np.array(embedding1)
        b = np.array(embedding2)

        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Instance singleton
embedding_service = EmbeddingService()
