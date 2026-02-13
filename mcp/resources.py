# mcp/resources.py
"""MCP Resources pour le graphe relationnel AltiusOne."""
import logging

logger = logging.getLogger(__name__)


def get_resources():
    """Retourne la liste des ressources MCP disponibles."""
    return [
        {
            'uri': 'graph://ontologie',
            'name': 'Types d\'ontologie',
            'description': 'Liste complète des types d\'entités et relations dans l\'ontologie',
            'mimeType': 'application/json',
        },
        {
            'uri': 'graph://stats',
            'name': 'Statistiques du graphe',
            'description': 'Statistiques globales du graphe relationnel',
            'mimeType': 'application/json',
        },
    ]


def read_resource(uri):
    """Lit une ressource MCP."""
    try:
        if uri == 'graph://ontologie':
            return _resource_ontologie()
        elif uri == 'graph://stats':
            return _resource_stats()
        else:
            return {'error': f'Ressource inconnue: {uri}'}
    except Exception as e:
        logger.error(f'MCP resource error ({uri}): {e}')
        return {'error': str(e)}


def _resource_ontologie():
    from graph.models import OntologieType

    types = OntologieType.objects.filter(is_active=True).order_by('categorie', 'ordre_affichage')
    result = {'entity_types': [], 'relation_types': []}

    for t in types:
        data = {
            'id': str(t.pk),
            'nom': t.nom,
            'description': t.description,
            'icone': t.icone,
            'couleur': t.couleur,
            'schema_attributs': t.schema_attributs,
        }
        if t.categorie == 'entity':
            result['entity_types'].append(data)
        else:
            data['verbe'] = t.verbe
            data['verbe_inverse'] = t.verbe_inverse
            data['bidirectionnel'] = t.bidirectionnel
            result['relation_types'].append(data)

    return result


def _resource_stats():
    from mcp.tools import _tool_stats
    return _tool_stats({})
