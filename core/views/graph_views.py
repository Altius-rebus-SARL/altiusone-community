# core/views/graph_views.py
"""
Visualiseur de graphe relationnel pour AltiusOne.
Inspiré par Epstein Visualizer - approche network-centric avec taille basée sur les connexions.
"""

import json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, NoReverseMatch
from django.http import JsonResponse
from django.views import View


# Configuration visuelle par type
NODE_COLORS = {
    'Client': '#3B82F6',       # Bleu
    'Mandat': '#10B981',       # Vert
    'User': '#8B5CF6',         # Violet
    'ExerciceComptable': '#F59E0B',  # Orange
    'Dossier': '#F97316',      # Orange vif
    'Document': '#EC4899',     # Rose
    'Facture': '#EF4444',      # Rouge
    'Employe': '#14B8A6',      # Teal
    'Tache': '#06B6D4',        # Cyan
    'Contact': '#84CC16',      # Lime
    'default': '#6B7280',      # Gris
}

EDGE_COLORS = {
    'owns': '#3B82F6',         # Client owns
    'works_on': '#10B981',     # Mandat relations
    'assigned': '#8B5CF6',     # User assignments
    'contains': '#F97316',     # Folder contains
    'default': '#94A3B8',      # Gris slate
}


def get_node_color(node_type):
    return NODE_COLORS.get(node_type, NODE_COLORS['default'])


def get_detail_url(app_label, model_name, pk):
    """Génère l'URL de détail si possible."""
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
    """Génère les données complètes du graphe sans limites artificielles."""

    def get_graph_data(self, center_type=None, center_pk=None, max_hops=None):
        """
        Génère le graphe complet en suivant toutes les relations.
        Taille des nodes basée sur le nombre de connexions.
        """
        from core.models import Client, Mandat, User, ExerciceComptable, Tache, Contact
        from documents.models import Dossier, Document

        nodes = {}  # id -> node data
        edges = []
        edge_set = set()  # Pour éviter les doublons
        connection_count = {}  # node_id -> count

        def add_node(node_type, instance, label):
            """Ajoute un node au graphe."""
            node_id = f"{node_type}:{instance.pk}"
            if node_id not in nodes:
                nodes[node_id] = {
                    'id': node_id,
                    'label': str(label)[:40] if label else str(instance),
                    'nodeType': node_type,
                    'color': get_node_color(node_type),
                    'pk': str(instance.pk),
                    'url': get_detail_url('core', node_type, instance.pk),
                }
                connection_count[node_id] = 0
            return node_id

        def add_edge(source_id, target_id, relation, edge_type='default'):
            """Ajoute une arête si elle n'existe pas."""
            if source_id == target_id:
                return
            edge_key = tuple(sorted([source_id, target_id]))
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                edges.append({
                    'source': source_id,
                    'target': target_id,
                    'label': relation,
                    'color': EDGE_COLORS.get(edge_type, EDGE_COLORS['default']),
                })
                # Incrémenter le compteur de connexions
                connection_count[source_id] = connection_count.get(source_id, 0) + 1
                connection_count[target_id] = connection_count.get(target_id, 0) + 1

        # ============================================
        # CHARGER TOUTES LES DONNÉES
        # ============================================

        # 1. CLIENTS
        clients = Client.objects.filter(is_active=True).select_related()
        for client in clients:
            client_id = add_node('Client', client, client.raison_sociale or client.nom_commercial or f"Client {client.pk}")

        # 2. MANDATS avec leurs relations
        mandats = Mandat.objects.filter(statut='ACTIF').select_related('client', 'responsable')
        for mandat in mandats:
            mandat_id = add_node('Mandat', mandat, mandat.numero or f"Mandat {mandat.pk}")

            # Lien Client -> Mandat
            if mandat.client_id:
                client_id = f"Client:{mandat.client_id}"
                if client_id in nodes:
                    add_edge(client_id, mandat_id, 'mandat', 'owns')

            # Lien Mandat -> Responsable
            if mandat.responsable_id:
                user_id = add_node('User', mandat.responsable,
                                   mandat.responsable.get_full_name() or mandat.responsable.email)
                add_edge(mandat_id, user_id, 'responsable', 'assigned')

        # 3. ÉQUIPES DES MANDATS
        for mandat in mandats:
            mandat_id = f"Mandat:{mandat.pk}"
            if mandat_id in nodes:
                for member in mandat.equipe.all():
                    user_id = add_node('User', member, member.get_full_name() or member.email)
                    add_edge(mandat_id, user_id, 'équipe', 'assigned')

        # 4. EXERCICES COMPTABLES
        exercices = ExerciceComptable.objects.select_related('mandat')
        for ex in exercices:
            if ex.mandat_id:
                mandat_id = f"Mandat:{ex.mandat_id}"
                if mandat_id in nodes:
                    ex_id = add_node('ExerciceComptable', ex, f"{ex.annee}")
                    add_edge(mandat_id, ex_id, 'exercice', 'works_on')

        # 5. TÂCHES
        taches = Tache.objects.select_related('mandat', 'assigne_a', 'cree_par')
        for tache in taches:
            tache_id = add_node('Tache', tache, tache.titre[:30] if tache.titre else f"Tâche {tache.pk}")

            if tache.mandat_id:
                mandat_id = f"Mandat:{tache.mandat_id}"
                if mandat_id in nodes:
                    add_edge(mandat_id, tache_id, 'tâche', 'works_on')

            if tache.assigne_a_id:
                user_id = add_node('User', tache.assigne_a,
                                   tache.assigne_a.get_full_name() or tache.assigne_a.email)
                add_edge(tache_id, user_id, 'assigné', 'assigned')

        # 6. DOSSIERS
        dossiers = Dossier.objects.select_related('client', 'mandat')
        for dossier in dossiers:
            dossier_id = add_node('Dossier', dossier, dossier.nom)

            if dossier.client_id:
                client_id = f"Client:{dossier.client_id}"
                if client_id in nodes:
                    add_edge(client_id, dossier_id, 'dossier', 'owns')

            if dossier.mandat_id:
                mandat_id = f"Mandat:{dossier.mandat_id}"
                if mandat_id in nodes:
                    add_edge(mandat_id, dossier_id, 'dossier', 'works_on')

        # 7. DOCUMENTS
        documents = Document.objects.select_related('dossier', 'mandat', 'uploaded_by')
        for doc in documents:
            doc_id = add_node('Document', doc, doc.nom_fichier[:25] if doc.nom_fichier else f"Doc {doc.pk}")

            if doc.dossier_id:
                dossier_id = f"Dossier:{doc.dossier_id}"
                if dossier_id in nodes:
                    add_edge(dossier_id, doc_id, 'contient', 'contains')

            if doc.mandat_id:
                mandat_id = f"Mandat:{doc.mandat_id}"
                if mandat_id in nodes:
                    add_edge(mandat_id, doc_id, 'document', 'works_on')

        # 8. CONTACTS
        try:
            contacts = Contact.objects.select_related('client')
            for contact in contacts:
                contact_id = add_node('Contact', contact,
                                      f"{contact.prenom} {contact.nom}" if hasattr(contact, 'prenom') else str(contact))
                if contact.client_id:
                    client_id = f"Client:{contact.client_id}"
                    if client_id in nodes:
                        add_edge(client_id, contact_id, 'contact', 'owns')
        except Exception:
            pass  # Model might not exist

        # ============================================
        # CALCULER LA TAILLE DES NODES
        # Formule: base_size + (connections * factor)
        # ============================================
        BASE_SIZE = 8
        SIZE_FACTOR = 3
        MAX_SIZE = 50

        for node_id, node in nodes.items():
            connections = connection_count.get(node_id, 0)
            size = min(BASE_SIZE + (connections * SIZE_FACTOR), MAX_SIZE)
            node['size'] = size
            node['connections'] = connections

        # Stats par type
        stats = {}
        for node in nodes.values():
            t = node['nodeType']
            if t not in stats:
                stats[t] = {'count': 0, 'color': node['color']}
            stats[t]['count'] += 1

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
        graph_data = self.get_graph_data()

        context['graph_data'] = json.dumps(graph_data)
        context['graph_stats'] = graph_data['stats']
        context['graph_meta'] = graph_data['meta']
        return context


class GraphAPIView(LoginRequiredMixin, GraphDataMixin, View):
    """API pour récupérer les données du graphe."""

    def get(self, request, type=None, pk=None):
        graph_data = self.get_graph_data()
        return JsonResponse(graph_data)


class GraphStatsAPIView(LoginRequiredMixin, View):
    """API pour les statistiques du graphe."""

    def get(self, request):
        from core.models import Client, Mandat, User
        from documents.models import Document, Dossier

        stats = {
            'Client': {'count': Client.objects.filter(is_active=True).count(), 'color': NODE_COLORS['Client']},
            'Mandat': {'count': Mandat.objects.filter(statut='ACTIF').count(), 'color': NODE_COLORS['Mandat']},
            'User': {'count': User.objects.filter(is_active=True).count(), 'color': NODE_COLORS['User']},
            'Document': {'count': Document.objects.count(), 'color': NODE_COLORS['Document']},
            'Dossier': {'count': Dossier.objects.count(), 'color': NODE_COLORS['Dossier']},
        }
        return JsonResponse({'stats': stats})
