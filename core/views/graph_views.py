# core/views/graph_views.py
"""
Visualiseur de graphe relationnel pour AltiusOne.
Approche network-centric: part des clients et suit les vraies relations.
"""

import json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, NoReverseMatch
from django.http import JsonResponse
from django.views import View


# Configuration visuelle
NODE_STYLES = {
    'Client': {
        'color': '#3B82F6',
        'borderColor': '#1D4ED8',
        'size': 25,
        'icon': 'building',
    },
    'Mandat': {
        'color': '#10B981',
        'borderColor': '#059669',
        'size': 20,
        'icon': 'briefcase',
    },
    'User': {
        'color': '#8B5CF6',
        'borderColor': '#7C3AED',
        'size': 15,
        'icon': 'user',
    },
    'ExerciceComptable': {
        'color': '#F59E0B',
        'borderColor': '#D97706',
        'size': 12,
        'icon': 'calendar',
    },
    'Dossier': {
        'color': '#F97316',
        'borderColor': '#EA580C',
        'size': 14,
        'icon': 'folder',
    },
    'Document': {
        'color': '#A855F7',
        'borderColor': '#9333EA',
        'size': 10,
        'icon': 'file',
    },
    'Facture': {
        'color': '#EF4444',
        'borderColor': '#DC2626',
        'size': 14,
        'icon': 'file-text',
    },
    'Employe': {
        'color': '#14B8A6',
        'borderColor': '#0D9488',
        'size': 14,
        'icon': 'users',
    },
    'Tache': {
        'color': '#EC4899',
        'borderColor': '#DB2777',
        'size': 10,
        'icon': 'check-square',
    },
    'default': {
        'color': '#6B7280',
        'borderColor': '#4B5563',
        'size': 10,
        'icon': 'circle',
    }
}

EDGE_STYLES = {
    'client': {'color': '#3B82F6', 'size': 3},  # Relations vers client
    'mandat': {'color': '#10B981', 'size': 2},  # Relations vers mandat
    'user': {'color': '#8B5CF6', 'size': 1.5},  # Relations vers user
    'default': {'color': '#94A3B8', 'size': 1},
}


def get_node_style(model_name):
    return NODE_STYLES.get(model_name, NODE_STYLES['default'])


def get_edge_style(relation_type):
    return EDGE_STYLES.get(relation_type, EDGE_STYLES['default'])


def get_detail_url(app_label, model_name, pk):
    """Tente de générer l'URL de détail."""
    patterns = [
        f'{app_label}:{model_name.lower()}-detail',
        f'core:{model_name.lower()}-detail',
    ]
    for pattern in patterns:
        try:
            return reverse(pattern, kwargs={'pk': pk})
        except NoReverseMatch:
            continue
    return None


class GraphDataMixin:
    """Génère les données du graphe en suivant les vraies relations."""

    def get_graph_data(self, center_type=None, center_pk=None):
        """
        Génère un graphe centré sur les relations réelles.
        Approche: Client → Mandats → (Documents, Exercices, Factures, Tâches, etc.)
        """
        from core.models import Client, Mandat, User, ExerciceComptable, Tache
        from documents.models import Dossier, Document

        nodes = {}
        edges = []
        edge_ids = set()
        stats = {}

        def add_node(model_name, instance, label):
            """Ajoute un node s'il n'existe pas."""
            node_id = f"{model_name}:{instance.pk}"
            if node_id not in nodes:
                style = get_node_style(model_name)
                nodes[node_id] = {
                    'id': node_id,
                    'label': str(label)[:50],
                    'nodeType': model_name,
                    'color': style['color'],
                    'borderColor': style['borderColor'],
                    'size': style['size'],
                    'icon': style['icon'],
                    'pk': str(instance.pk),
                    'url': get_detail_url('core', model_name, instance.pk),
                }
            return node_id

        def add_edge(source_id, target_id, relation_name, edge_type='default'):
            """Ajoute un edge s'il n'existe pas."""
            edge_id = f"{source_id}--{target_id}"
            reverse_id = f"{target_id}--{source_id}"
            if edge_id not in edge_ids and reverse_id not in edge_ids:
                edge_ids.add(edge_id)
                style = get_edge_style(edge_type)
                edges.append({
                    'id': edge_id,
                    'source': source_id,
                    'target': target_id,
                    'label': relation_name,
                    'color': style['color'],
                    'size': style['size'],
                })

        # ============================================
        # 1. CLIENTS (racine du graphe)
        # ============================================
        clients = Client.objects.filter(is_active=True)[:10]
        stats['Client'] = {'count': Client.objects.count(), 'displayed': len(clients), 'color': NODE_STYLES['Client']['color']}

        for client in clients:
            client_node = add_node('Client', client, client.raison_sociale or client.nom_commercial)

            # ============================================
            # 2. MANDATS du client
            # ============================================
            mandats = Mandat.objects.filter(client=client, statut='ACTIF')[:5]
            for mandat in mandats:
                mandat_node = add_node('Mandat', mandat, f"{mandat.numero}")
                add_edge(client_node, mandat_node, 'mandat', 'client')

                # Responsable du mandat
                if mandat.responsable:
                    user_node = add_node('User', mandat.responsable, mandat.responsable.get_full_name() or mandat.responsable.email)
                    add_edge(mandat_node, user_node, 'responsable', 'user')

                # Équipe du mandat
                for member in mandat.equipe.all()[:3]:
                    user_node = add_node('User', member, member.get_full_name() or member.email)
                    add_edge(mandat_node, user_node, 'équipe', 'user')

                # Exercices comptables
                exercices = ExerciceComptable.objects.filter(mandat=mandat)[:3]
                for exercice in exercices:
                    ex_node = add_node('ExerciceComptable', exercice, f"{exercice.annee}")
                    add_edge(mandat_node, ex_node, 'exercice', 'mandat')

                # Tâches du mandat
                taches = Tache.objects.filter(mandat=mandat)[:3]
                for tache in taches:
                    tache_node = add_node('Tache', tache, tache.titre[:30])
                    add_edge(mandat_node, tache_node, 'tâche', 'mandat')
                    if tache.assigne_a:
                        user_node = add_node('User', tache.assigne_a, tache.assigne_a.get_full_name() or tache.assigne_a.email)
                        add_edge(tache_node, user_node, 'assigné', 'user')

            # ============================================
            # 3. DOSSIERS et DOCUMENTS du client
            # ============================================
            dossiers = Dossier.objects.filter(client=client)[:5]
            for dossier in dossiers:
                dossier_node = add_node('Dossier', dossier, dossier.nom)
                add_edge(client_node, dossier_node, 'dossier', 'client')

                # Documents dans le dossier
                documents = Document.objects.filter(dossier=dossier)[:3]
                for doc in documents:
                    doc_node = add_node('Document', doc, doc.nom_fichier[:30])
                    add_edge(dossier_node, doc_node, 'contient', 'default')

        # Calculer les stats finales
        node_types = {}
        for node in nodes.values():
            t = node['nodeType']
            node_types[t] = node_types.get(t, 0) + 1

        for t, count in node_types.items():
            if t not in stats:
                stats[t] = {'count': count, 'displayed': count, 'color': get_node_style(t)['color']}

        return {
            'nodes': list(nodes.values()),
            'edges': edges,
            'stats': stats,
            'meta': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
            }
        }


class GraphView(LoginRequiredMixin, GraphDataMixin, TemplateView):
    """Vue principale du graphe relationnel."""
    template_name = 'core/graph.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        center_type = self.kwargs.get('type')
        center_pk = self.kwargs.get('pk')
        graph_data = self.get_graph_data(center_type, center_pk)

        context['graph_data'] = json.dumps(graph_data)
        context['graph_stats'] = graph_data['stats']
        context['graph_meta'] = graph_data['meta']
        context['center_type'] = center_type
        context['center_pk'] = center_pk
        return context


class GraphAPIView(LoginRequiredMixin, GraphDataMixin, View):
    """API pour récupérer les données du graphe."""

    def get(self, request, type=None, pk=None):
        graph_data = self.get_graph_data(type, pk)
        return JsonResponse(graph_data)


class GraphStatsAPIView(LoginRequiredMixin, View):
    """API pour les statistiques du graphe."""

    def get(self, request):
        from core.models import Client, Mandat, User
        from documents.models import Document, Dossier

        stats = {
            'Client': {'count': Client.objects.count(), 'color': NODE_STYLES['Client']['color']},
            'Mandat': {'count': Mandat.objects.count(), 'color': NODE_STYLES['Mandat']['color']},
            'User': {'count': User.objects.count(), 'color': NODE_STYLES['User']['color']},
            'Document': {'count': Document.objects.count(), 'color': NODE_STYLES['Document']['color']},
            'Dossier': {'count': Dossier.objects.count(), 'color': NODE_STYLES['Dossier']['color']},
        }
        return JsonResponse({'stats': stats})
