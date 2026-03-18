# core/ai/distances.py
"""
Mesures de distance vectorielle pour pgvector.

Registre extensible — ajouter de nouvelles mesures sans modifier le code existant.
Chaque mesure est une fonction pgvector Django ORM (CosineDistance, L2Distance, etc.)

Usage:
    from core.ai.distances import get_distance_function, COSINE, L2

    # Dans une query pgvector
    qs = ModelEmbedding.objects.annotate(
        distance=get_distance_function('cosine')('embedding', query_vector)
    )
"""
from enum import Enum
from typing import Callable


class DistanceMetric(str, Enum):
    """Mesures de distance disponibles."""
    COSINE = 'cosine'       # 1 - cosinus similarity (0 = identique)
    L2 = 'l2'               # Distance euclidienne
    L1 = 'l1'               # Distance Manhattan
    JACCARD = 'jaccard'     # Distance Jaccard (pour vecteurs binaires/sparse)
    HAMMING = 'hamming'     # Distance Hamming (pour vecteurs binaires)


# Aliases pour import direct
COSINE = DistanceMetric.COSINE
L2 = DistanceMetric.L2
L1 = DistanceMetric.L1
JACCARD = DistanceMetric.JACCARD
HAMMING = DistanceMetric.HAMMING


def get_distance_function(metric: str | DistanceMetric) -> Callable:
    """
    Retourne la fonction de distance pgvector pour une métrique donnée.

    Args:
        metric: 'cosine', 'l2', 'l1', 'jaccard', 'hamming' ou DistanceMetric enum

    Returns:
        Classe pgvector.django (CosineDistance, L2Distance, etc.)

    Raises:
        ValueError: si la métrique n'est pas reconnue
    """
    from pgvector.django import (
        CosineDistance,
        L2Distance,
        L1Distance,
        JaccardDistance,
        HammingDistance,
    )

    if isinstance(metric, DistanceMetric):
        metric = metric.value

    registry = {
        'cosine': CosineDistance,
        'l2': L2Distance,
        'l1': L1Distance,
        'jaccard': JaccardDistance,
        'hamming': HammingDistance,
    }

    func = registry.get(metric)
    if func is None:
        available = ', '.join(registry.keys())
        raise ValueError(f"Métrique inconnue: '{metric}'. Disponibles: {available}")

    return func


def threshold_for_metric(metric: str | DistanceMetric, similarity_threshold: float) -> float:
    """
    Convertit un seuil de similarité (0-1, 1=identique) en seuil de distance
    adapté à la métrique choisie.

    Pour cosinus: distance = 1 - similarity
    Pour L2: pas de conversion directe (le seuil est une distance brute)
    Pour les autres: retourne tel quel

    Args:
        metric: La métrique utilisée
        similarity_threshold: Seuil de similarité (0-1)

    Returns:
        Seuil de distance max à utiliser dans un filter
    """
    if isinstance(metric, DistanceMetric):
        metric = metric.value

    if metric == 'cosine':
        # cosine distance = 1 - similarity
        return 1.0 - similarity_threshold
    elif metric == 'l2':
        # L2: pas de mapping direct. On utilise un heuristique :
        # pour des embeddings normalisés (norme ~1), L2 ≈ sqrt(2 * (1 - cosine_sim))
        import math
        return math.sqrt(2.0 * (1.0 - similarity_threshold))
    else:
        # Pour jaccard, hamming, l1 : le seuil est déjà une distance
        return 1.0 - similarity_threshold
