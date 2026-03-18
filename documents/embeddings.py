# documents/embeddings.py
"""
Service d'embeddings pour la recherche sémantique documentaire.

Wrapper rétro-compatible qui délègue vers core.ai.embeddings.
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Wrapper rétro-compatible vers le service d'embeddings local.

    Tout le code existant qui importe depuis `documents.embeddings`
    continue de fonctionner sans modification.
    """

    def __init__(self):
        self._core_service = None

    @property
    def _service(self):
        if self._core_service is None:
            from core.ai.embeddings import embedding_service
            self._core_service = embedding_service
        return self._core_service

    @property
    def dimensions(self) -> int:
        return self._service.dimensions

    @property
    def model_name(self) -> str:
        return self._service.model_name

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        return self._service.generate_embedding(text)

    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        return self._service.generate_embeddings_batch(texts)

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        return self._service.compute_similarity(embedding1, embedding2)

    def is_available(self) -> bool:
        return self._service.is_available()


# Instance singleton (rétro-compatibilité)
embedding_service = EmbeddingService()
