# graph/services/exploration.py
"""Service d'exploration du graphe via CTE récursive PostgreSQL."""
import logging
from django.db import connection

logger = logging.getLogger(__name__)


def explorer_graphe(
    entite_id,
    profondeur=2,
    types_entites=None,
    types_relations=None,
    date_min=None,
    date_max=None,
    confiance_min=0.0,
):
    """
    Explore le graphe à partir d'une entité avec BFS récursif.

    Utilise une CTE récursive PostgreSQL pour traverser les relations
    et retourne les données au format D3.js (nodes/links).

    Args:
        entite_id: UUID de l'entité de départ
        profondeur: Nombre de sauts maximum (1-10)
        types_entites: Liste d'UUIDs de types d'entités à inclure (None = tous)
        types_relations: Liste d'UUIDs de types de relations à inclure (None = tous)
        date_min: Date minimum pour les relations
        date_max: Date maximum pour les relations
        confiance_min: Score de confiance minimum

    Returns:
        dict: {nodes: [...], links: [...], meta: {...}}
    """
    profondeur = max(1, min(profondeur, 10))

    # Construction des clauses WHERE dynamiques
    filters_relation = ["r.is_active = true"]
    params = [str(entite_id), profondeur]

    if types_relations:
        placeholders = ', '.join(['%s'] * len(types_relations))
        filters_relation.append(f"r.type_id IN ({placeholders})")
        params.extend([str(t) for t in types_relations])

    if date_min:
        filters_relation.append("(r.date_fin IS NULL OR r.date_fin >= %s)")
        params.append(date_min)

    if date_max:
        filters_relation.append("(r.date_debut IS NULL OR r.date_debut <= %s)")
        params.append(date_max)

    if confiance_min > 0:
        filters_relation.append("r.confiance >= %s")
        params.append(confiance_min)

    where_relation = " AND ".join(filters_relation)

    # Filtre sur les types d'entités
    where_entite = "e.is_active = true"
    if types_entites:
        placeholders = ', '.join(['%s'] * len(types_entites))
        where_entite += f" AND e.type_id IN ({placeholders})"
        params.extend([str(t) for t in types_entites])

    sql = f"""
    WITH RECURSIVE graphe_bfs AS (
        -- Nœud de départ
        SELECT
            e.id AS entite_id,
            0 AS depth,
            ARRAY[e.id] AS path
        FROM graph_entite e
        WHERE e.id = %s AND e.is_active = true

        UNION ALL

        -- Expansion BFS via relations (bidirectionnel)
        SELECT
            CASE
                WHEN r.source_id = g.entite_id THEN r.cible_id
                ELSE r.source_id
            END AS entite_id,
            g.depth + 1 AS depth,
            g.path || CASE
                WHEN r.source_id = g.entite_id THEN r.cible_id
                ELSE r.source_id
            END AS path
        FROM graphe_bfs g
        JOIN graph_relation r ON (
            r.source_id = g.entite_id OR r.cible_id = g.entite_id
        )
        WHERE
            g.depth < %s
            AND {where_relation}
            AND NOT (
                CASE
                    WHEN r.source_id = g.entite_id THEN r.cible_id
                    ELSE r.source_id
                END = ANY(g.path)
            )
    )
    SELECT DISTINCT ON (entite_id)
        entite_id, depth
    FROM graphe_bfs
    ORDER BY entite_id, depth;
    """

    nodes = []
    node_ids = set()
    links = []

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        for row in rows:
            node_ids.add(row[0])

    if not node_ids:
        return {'nodes': [], 'links': [], 'meta': {'total_nodes': 0, 'total_links': 0}}

    # Charger les entités
    from graph.models import Entite, Relation

    entites = Entite.objects.select_related('type').filter(
        pk__in=node_ids, is_active=True,
    )

    if types_entites:
        entites = entites.filter(type_id__in=types_entites)

    entite_map = {}
    for e in entites:
        node = {
            'id': str(e.pk),
            'nom': e.nom,
            'type': str(e.type_id),
            'type_nom': e.type.nom,
            'couleur': e.type.couleur,
            'icone': e.type.icone,
            'confiance': e.confiance,
            'has_anomalies': False,
        }
        if e.geom:
            node['lat'] = e.geom.y
            node['lng'] = e.geom.x
        nodes.append(node)
        entite_map[e.pk] = node

    # Vérifier les anomalies
    from graph.models import Anomalie
    anomalie_ids = set(
        Anomalie.objects.filter(
            entite_id__in=entite_map.keys(),
            statut__in=['nouveau', 'en_cours'],
        ).values_list('entite_id', flat=True)
    )
    for aid in anomalie_ids:
        if aid in entite_map:
            entite_map[aid]['has_anomalies'] = True

    # Charger les relations entre les nœuds trouvés
    valid_ids = set(entite_map.keys())
    relations_qs = Relation.objects.select_related('type').filter(
        source_id__in=valid_ids,
        cible_id__in=valid_ids,
        is_active=True,
    )

    if types_relations:
        relations_qs = relations_qs.filter(type_id__in=types_relations)

    if date_min:
        relations_qs = relations_qs.filter(
            models.Q(date_fin__isnull=True) | models.Q(date_fin__gte=date_min)
        )

    if date_max:
        relations_qs = relations_qs.filter(
            models.Q(date_debut__isnull=True) | models.Q(date_debut__lte=date_max)
        )

    if confiance_min > 0:
        relations_qs = relations_qs.filter(confiance__gte=confiance_min)

    for rel in relations_qs:
        links.append({
            'id': str(rel.pk),
            'source': str(rel.source_id),
            'target': str(rel.cible_id),
            'type': str(rel.type_id),
            'type_nom': rel.type.nom,
            'verbe': rel.type.verbe or rel.type.nom,
            'poids': rel.poids,
            'en_cours': rel.en_cours,
        })

    return {
        'nodes': nodes,
        'links': links,
        'meta': {
            'total_nodes': len(nodes),
            'total_links': len(links),
            'entite_depart': str(entite_id),
            'profondeur': profondeur,
        },
    }
