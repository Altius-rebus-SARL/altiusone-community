# graph/services/suggestions.py
"""Service de suggestions de connexions via pgvector."""
import logging
from pgvector.django import CosineDistance

logger = logging.getLogger(__name__)


def suggerer_connexions(entite_id, limit=10):
    """
    Suggère des entités à connecter via nearest neighbors pgvector.

    Trouve les entités les plus proches sémantiquement qui ne sont
    pas encore liées directement.

    Args:
        entite_id: UUID de l'entité source
        limit: Nombre maximum de suggestions

    Returns:
        list[dict]: Suggestions avec score de similarité
    """
    from graph.models import Entite, Relation

    try:
        entite = Entite.objects.select_related('type').get(
            pk=entite_id, is_active=True,
        )
    except Entite.DoesNotExist:
        return []

    if entite.embedding is None:
        return []

    # IDs des entités déjà liées
    liees_sortantes = set(
        Relation.objects.filter(
            source=entite, is_active=True,
        ).values_list('cible_id', flat=True)
    )
    liees_entrantes = set(
        Relation.objects.filter(
            cible=entite, is_active=True,
        ).values_list('source_id', flat=True)
    )
    deja_liees = liees_sortantes | liees_entrantes | {entite.pk}

    # Nearest neighbors non liés
    candidats = (
        Entite.objects.filter(is_active=True, embedding__isnull=False)
        .exclude(pk__in=deja_liees)
        .annotate(distance=CosineDistance('embedding', entite.embedding))
        .order_by('distance')[:limit]
    )

    suggestions = []
    for c in candidats:
        similarity = 1 - c.distance
        if similarity < 0.3:
            continue
        suggestions.append({
            'id': str(c.pk),
            'nom': c.nom,
            'type_id': str(c.type_id),
            'type_nom': c.type.nom,
            'couleur': c.type.couleur,
            'icone': c.type.icone,
            'similarite': round(similarity, 4),
        })

    return suggestions
