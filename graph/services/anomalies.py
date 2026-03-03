# graph/services/anomalies.py
"""Service de détection d'anomalies dans le graphe."""
import logging
from django.db.models import Q, Count, F
from pgvector.django import CosineDistance

logger = logging.getLogger(__name__)


def detecter_doublons(seuil=0.85):
    """
    Détecte les entités potentiellement dupliquées via similarité cosinus pgvector.

    Args:
        seuil: Seuil de similarité (0.85 = 85% similaires)

    Returns:
        int: Nombre de doublons détectés
    """
    from graph.models import Entite, Anomalie

    entites = Entite.objects.filter(
        is_active=True,
        embedding__isnull=False,
    ).select_related('type')

    count = 0
    processed_pairs = set()

    for entite in entites:
        if entite.embedding is None:
            continue

        # Chercher les voisins proches du même type
        similaires = (
            Entite.objects.filter(
                is_active=True,
                type=entite.type,
                embedding__isnull=False,
            )
            .exclude(pk=entite.pk)
            .annotate(distance=CosineDistance('embedding', entite.embedding))
            .filter(distance__lt=(1 - seuil))
            .order_by('distance')[:5]
        )

        for sim in similaires:
            pair_key = tuple(sorted([str(entite.pk), str(sim.pk)]))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)

            # Vérifier qu'une anomalie n'existe pas déjà
            exists = Anomalie.objects.filter(
                type='doublon',
                entite=entite,
                entite_liee=sim,
                statut__in=['nouveau', 'en_cours'],
            ).exists()

            if not exists:
                similarity = 1 - sim.distance
                Anomalie.objects.create(
                    type='doublon',
                    entite=entite,
                    entite_liee=sim,
                    titre=f"Doublon potentiel: {entite.nom} ↔ {sim.nom}",
                    description=(
                        f"Les entités '{entite.nom}' et '{sim.nom}' "
                        f"(type: {entite.type.nom}) ont une similarité de "
                        f"{similarity:.0%}."
                    ),
                    score=similarity,
                    details={
                        'similarite': round(similarity, 4),
                        'entite_nom': entite.nom,
                        'entite_liee_nom': sim.nom,
                    },
                )
                count += 1

    logger.info(f"Détection doublons: {count} nouveaux trouvés")
    return count


def detecter_orphelins():
    """
    Détecte les entités sans aucune relation (orphelines).

    Returns:
        int: Nombre d'orphelins détectés
    """
    from graph.models import Entite, Anomalie

    orphelins = (
        Entite.objects.filter(is_active=True)
        .annotate(
            nb_relations=Count('relations_sortantes') + Count('relations_entrantes'),
        )
        .filter(nb_relations=0)
    )

    count = 0
    for entite in orphelins:
        exists = Anomalie.objects.filter(
            type='orphelin',
            entite=entite,
            statut__in=['nouveau', 'en_cours'],
        ).exists()

        if not exists:
            Anomalie.objects.create(
                type='orphelin',
                entite=entite,
                titre=f"Entité orpheline: {entite.nom}",
                description=(
                    f"L'entité '{entite.nom}' (type: {entite.type.nom}) "
                    f"n'a aucune relation dans le graphe."
                ),
                score=0.5,
            )
            count += 1

    logger.info(f"Détection orphelins: {count} nouveaux trouvés")
    return count


def detecter_incoherences_temporelles():
    """
    Détecte les relations dont date_fin < date_debut.

    Returns:
        int: Nombre d'incohérences détectées
    """
    from graph.models import Relation, Anomalie

    incoherentes = Relation.objects.filter(
        is_active=True,
        date_debut__isnull=False,
        date_fin__isnull=False,
        date_fin__lt=F('date_debut'),
    ).select_related('source', 'cible', 'type')

    count = 0
    for rel in incoherentes:
        exists = Anomalie.objects.filter(
            type='incoherence',
            entite=rel.source,
            entite_liee=rel.cible,
            statut__in=['nouveau', 'en_cours'],
            details__relation_id=str(rel.pk),
        ).exists()

        if not exists:
            Anomalie.objects.create(
                type='incoherence',
                entite=rel.source,
                entite_liee=rel.cible,
                titre=f"Incohérence temporelle: {rel}",
                description=(
                    f"La relation '{rel.type.nom}' entre '{rel.source.nom}' "
                    f"et '{rel.cible.nom}' a une date de fin ({rel.date_fin}) "
                    f"antérieure à la date de début ({rel.date_debut})."
                ),
                score=0.9,
                details={
                    'relation_id': str(rel.pk),
                    'date_debut': str(rel.date_debut),
                    'date_fin': str(rel.date_fin),
                },
            )
            count += 1

    logger.info(f"Détection incohérences: {count} nouvelles trouvées")
    return count


def detecter_tout():
    """Lance toutes les détections d'anomalies.

    Returns:
        dict: Résultats par type
    """
    resultats = {
        'doublons': detecter_doublons(),
        'orphelins': detecter_orphelins(),
        'incoherences': detecter_incoherences_temporelles(),
    }
    logger.info(f"Détection anomalies complète: {resultats}")
    return resultats
