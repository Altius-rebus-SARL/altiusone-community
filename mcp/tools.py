# mcp/tools.py
"""MCP Tools pour le graphe relationnel AltiusOne."""
import json
import logging

logger = logging.getLogger(__name__)


def get_tools():
    """Retourne la liste des outils MCP disponibles."""
    return [
        {
            'name': 'graph_search',
            'description': 'Recherche des entités dans le graphe relationnel par nom ou description.',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Terme de recherche',
                    },
                    'type_nom': {
                        'type': 'string',
                        'description': 'Filtrer par type (ex: Personne, Entreprise)',
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Nombre max de résultats',
                        'default': 10,
                    },
                },
                'required': ['query'],
            },
        },
        {
            'name': 'graph_explore',
            'description': 'Explore le graphe à partir d\'une entité, retourne les nœuds et liens voisins.',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'entite_id': {
                        'type': 'string',
                        'description': 'UUID de l\'entité de départ',
                    },
                    'profondeur': {
                        'type': 'integer',
                        'description': 'Profondeur d\'exploration (1-5)',
                        'default': 2,
                    },
                },
                'required': ['entite_id'],
            },
        },
        {
            'name': 'graph_semantic_search',
            'description': 'Recherche sémantique via embeddings vectoriels pgvector.',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Description en langage naturel',
                    },
                    'limit': {
                        'type': 'integer',
                        'default': 10,
                    },
                },
                'required': ['query'],
            },
        },
        {
            'name': 'graph_stats',
            'description': 'Retourne les statistiques du graphe relationnel.',
            'inputSchema': {
                'type': 'object',
                'properties': {},
            },
        },
        {
            'name': 'graph_anomalies',
            'description': 'Liste les anomalies ouvertes dans le graphe.',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string',
                        'description': 'Type d\'anomalie (doublon, orphelin, incoherence)',
                    },
                    'limit': {
                        'type': 'integer',
                        'default': 20,
                    },
                },
            },
        },
    ]


def execute_tool(name, arguments):
    """Exécute un outil MCP et retourne le résultat."""
    try:
        if name == 'graph_search':
            return _tool_search(arguments)
        elif name == 'graph_explore':
            return _tool_explore(arguments)
        elif name == 'graph_semantic_search':
            return _tool_semantic_search(arguments)
        elif name == 'graph_stats':
            return _tool_stats(arguments)
        elif name == 'graph_anomalies':
            return _tool_anomalies(arguments)
        else:
            return {'error': f'Outil inconnu: {name}'}
    except Exception as e:
        logger.error(f'MCP tool error ({name}): {e}')
        return {'error': str(e)}


def _tool_search(args):
    from graph.models import Entite
    from django.db.models import Q

    query = args.get('query', '')
    limit = args.get('limit', 10)
    type_nom = args.get('type_nom')

    qs = Entite.objects.filter(
        Q(nom__icontains=query) | Q(description__icontains=query),
        is_active=True,
    ).select_related('type')

    if type_nom:
        qs = qs.filter(type__nom__icontains=type_nom)

    results = []
    for e in qs[:limit]:
        results.append({
            'id': str(e.pk),
            'nom': e.nom,
            'type': e.type.nom,
            'description': (e.description or '')[:200],
            'confiance': e.confiance,
        })
    return {'results': results, 'count': len(results)}


def _tool_explore(args):
    from graph.services.exploration import explorer_graphe

    entite_id = args.get('entite_id')
    profondeur = args.get('profondeur', 2)
    return explorer_graphe(entite_id, profondeur=profondeur)


def _tool_semantic_search(args):
    from graph.models import Entite
    from documents.embeddings import embedding_service
    from pgvector.django import CosineDistance

    query = args.get('query', '')
    limit = args.get('limit', 10)

    embedding = embedding_service.generate_embedding(query)
    if not embedding:
        return {'error': 'Impossible de générer l\'embedding', 'results': []}

    qs = (
        Entite.objects.filter(is_active=True, embedding__isnull=False)
        .annotate(distance=CosineDistance('embedding', embedding))
        .order_by('distance')[:limit]
    )

    results = []
    for e in qs.select_related('type'):
        results.append({
            'id': str(e.pk),
            'nom': e.nom,
            'type': e.type.nom,
            'similarite': round(1 - e.distance, 4),
        })
    return {'results': results}


def _tool_stats(args):
    from graph.models import OntologieType, Entite, Relation, Anomalie
    from django.db.models import Count

    return {
        'entites': Entite.objects.filter(is_active=True).count(),
        'relations': Relation.objects.filter(is_active=True).count(),
        'types': OntologieType.objects.filter(is_active=True).count(),
        'anomalies_ouvertes': Anomalie.objects.filter(
            statut__in=['nouveau', 'en_cours'], is_active=True,
        ).count(),
        'entites_par_type': list(
            Entite.objects.filter(is_active=True)
            .values('type__nom')
            .annotate(count=Count('id'))
            .order_by('-count')
        ),
    }


def _tool_anomalies(args):
    from graph.models import Anomalie

    qs = Anomalie.objects.filter(
        statut__in=['nouveau', 'en_cours'], is_active=True,
    ).select_related('entite', 'entite_liee')

    anom_type = args.get('type')
    if anom_type:
        qs = qs.filter(type=anom_type)

    limit = args.get('limit', 20)
    results = []
    for a in qs[:limit]:
        results.append({
            'id': str(a.pk),
            'type': a.type,
            'titre': a.titre,
            'score': a.score,
            'entite': a.entite.nom,
            'entite_liee': a.entite_liee.nom if a.entite_liee else None,
            'statut': a.statut,
        })
    return {'anomalies': results, 'count': len(results)}
