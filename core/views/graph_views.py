# core/views/graph_views.py
"""
Visualiseur de graphe relationnel pour AltiusOne.
Layout circulaire par type inspiré de l'Epstein Visualizer.

Structure:
- Centre: AltiusOne (la fiduciaire)
- 1er cercle: Clients
- 2e cercle: Mandats, Contacts, Users (staff)
- 3e cercle: Factures, Documents, Tâches, Exercices
"""

import json
import math
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, NoReverseMatch
from django.http import JsonResponse
from django.views import View


# =============================================================================
# CONFIGURATION DES TYPES
# =============================================================================

NODE_TYPES = {
    'Fiduciaire': {
        'color': '#818cf8',  # Indigo (centre)
        'icon': 'fa-building-columns',
        'size': 30,
        'level': 0,
    },
    'Client': {
        'color': '#6366f1',  # Indigo
        'icon': 'fa-building',
        'size': 16,
        'level': 1,
    },
    'User': {
        'color': '#06b6d4',  # Cyan
        'icon': 'fa-user-tie',
        'size': 14,
        'level': 2,
    },
    'Mandat': {
        'color': '#10b981',  # Emerald
        'icon': 'fa-file-contract',
        'size': 12,
        'level': 2,
    },
    'Contact': {
        'color': '#8b5cf6',  # Violet
        'icon': 'fa-address-book',
        'size': 10,
        'level': 2,
    },
    'Facture': {
        'color': '#f59e0b',  # Amber
        'icon': 'fa-file-invoice-dollar',
        'size': 9,
        'level': 3,
    },
    'Document': {
        'color': '#64748b',  # Slate
        'icon': 'fa-file-alt',
        'size': 8,
        'level': 3,
    },
    'Tache': {
        'color': '#14b8a6',  # Teal
        'icon': 'fa-tasks',
        'size': 8,
        'level': 3,
    },
    'ExerciceComptable': {
        'color': '#f97316',  # Orange
        'icon': 'fa-calendar-check',
        'size': 9,
        'level': 3,
    },
    'Dossier': {
        'color': '#eab308',  # Yellow
        'icon': 'fa-folder',
        'size': 8,
        'level': 3,
    },
    'Ecriture': {
        'color': '#ec4899',  # Pink
        'icon': 'fa-pen-fancy',
        'size': 7,
        'level': 4,
    },
    'Paiement': {
        'color': '#22c55e',  # Green
        'icon': 'fa-money-bill-wave',
        'size': 8,
        'level': 3,
    },
}

EDGE_TYPES = {
    'gere': {'color': 'rgba(99, 102, 241, 0.4)', 'label': 'Gère'},
    'client_de': {'color': 'rgba(99, 102, 241, 0.3)', 'label': 'Client de'},
    'mandat_de': {'color': 'rgba(16, 185, 129, 0.3)', 'label': 'Mandat'},
    'responsable': {'color': 'rgba(6, 182, 212, 0.4)', 'label': 'Responsable'},
    'equipe': {'color': 'rgba(6, 182, 212, 0.2)', 'label': 'Équipe'},
    'contact_de': {'color': 'rgba(139, 92, 246, 0.3)', 'label': 'Contact'},
    'facture_de': {'color': 'rgba(245, 158, 11, 0.3)', 'label': 'Facture'},
    'document_de': {'color': 'rgba(100, 116, 139, 0.3)', 'label': 'Document'},
    'tache_de': {'color': 'rgba(20, 184, 166, 0.3)', 'label': 'Tâche'},
    'exercice_de': {'color': 'rgba(249, 115, 22, 0.3)', 'label': 'Exercice'},
    'dossier_de': {'color': 'rgba(234, 179, 8, 0.3)', 'label': 'Dossier'},
    'paiement_de': {'color': 'rgba(34, 197, 94, 0.3)', 'label': 'Paiement'},
    'ecriture_de': {'color': 'rgba(236, 72, 153, 0.2)', 'label': 'Écriture'},
    'assigne_a': {'color': 'rgba(6, 182, 212, 0.3)', 'label': 'Assigné à'},
}


def get_detail_url(model_name, pk):
    """Génère l'URL de détail si possible."""
    patterns = [
        f'core:{model_name.lower()}-detail',
        f'{model_name.lower()}:detail',
    ]
    for pattern in patterns:
        try:
            return reverse(pattern, kwargs={'pk': pk})
        except NoReverseMatch:
            continue
    return None


# =============================================================================
# LAYOUT CIRCULAIRE PAR TYPE
# =============================================================================

def circular_layout(nodes_by_type, center_x=0, center_y=0):
    """
    Place les nœuds en cercles concentriques par niveau.
    Chaque type occupe un secteur du cercle de son niveau.
    """
    positions = {}

    # Regrouper par niveau
    levels = {}
    for node_type, nodes in nodes_by_type.items():
        config = NODE_TYPES.get(node_type, {'level': 3})
        level = config.get('level', 3)
        if level not in levels:
            levels[level] = []
        levels[level].append((node_type, nodes))

    # Rayon de base par niveau
    level_radii = {
        0: 0,      # Centre (Fiduciaire)
        1: 200,    # Clients
        2: 450,    # Mandats, Users, Contacts
        3: 750,    # Factures, Documents, etc.
        4: 1000,   # Écritures (plus éloigné)
    }

    for level, type_list in levels.items():
        radius = level_radii.get(level, 500 + level * 200)

        if level == 0:
            # Le centre (Fiduciaire)
            for node_type, nodes in type_list:
                for node_id in nodes:
                    positions[node_id] = (center_x, center_y)
        else:
            # Calculer l'angle total et le diviser entre les types
            total_nodes = sum(len(nodes) for _, nodes in type_list)
            if total_nodes == 0:
                continue

            # Angle de départ pour chaque type
            current_angle = 0

            for node_type, nodes in type_list:
                if not nodes:
                    continue

                # L'angle occupé par ce type est proportionnel au nombre de nœuds
                angle_span = (len(nodes) / total_nodes) * 2 * math.pi
                angle_step = angle_span / len(nodes) if len(nodes) > 1 else 0

                for i, node_id in enumerate(nodes):
                    # Position sur l'arc de cercle + légère variation pour éviter les superpositions
                    angle = current_angle + (i + 0.5) * angle_step
                    # Légère variation de rayon pour aérer
                    r = radius + (i % 3 - 1) * 30

                    x = center_x + r * math.cos(angle)
                    y = center_y + r * math.sin(angle)
                    positions[node_id] = (x, y)

                current_angle += angle_span

    return positions


# =============================================================================
# GÉNÉRATION DES DONNÉES DU GRAPHE
# =============================================================================

class GraphDataMixin:
    """Génère les données complètes du graphe avec layout circulaire."""

    def get_graph_data(self, limit_per_type=None):
        """
        Génère le graphe complet avec:
        - AltiusOne au centre
        - Clients autour
        - Mandats, Users, Contacts
        - Factures, Documents, Tâches...
        """
        from core.models import Client, Mandat, User, ExerciceComptable, Tache, Contact
        from documents.models import Dossier, Document
        from facturation.models import Facture, Paiement

        nodes = {}  # id -> node data
        edges = []
        edge_set = set()
        nodes_by_type = {}  # type -> list of node_ids
        connection_count = {}

        def add_node(node_type, node_id, label, data=None):
            """Ajoute un nœud au graphe."""
            full_id = f"{node_type}:{node_id}"
            if full_id not in nodes:
                config = NODE_TYPES.get(node_type, {
                    'color': '#6b7280', 'size': 10, 'level': 3
                })
                nodes[full_id] = {
                    'id': full_id,
                    'label': str(label)[:40] if label else f'{node_type} {node_id}',
                    'nodeType': node_type,
                    'color': config['color'],
                    'size': config['size'],
                    'level': config['level'],
                    'pk': str(node_id),
                    'data': data or {},
                }
                connection_count[full_id] = 0

                if node_type not in nodes_by_type:
                    nodes_by_type[node_type] = []
                nodes_by_type[node_type].append(full_id)

            return full_id

        def add_edge(source_id, target_id, edge_type='default'):
            """Ajoute une arête si elle n'existe pas."""
            if source_id == target_id:
                return
            edge_key = tuple(sorted([source_id, target_id]))
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                edge_config = EDGE_TYPES.get(edge_type, {
                    'color': 'rgba(100, 116, 139, 0.2)',
                    'label': edge_type
                })
                edges.append({
                    'source': source_id,
                    'target': target_id,
                    'edgeType': edge_type,
                    'color': edge_config['color'],
                    'label': edge_config['label'],
                })
                connection_count[source_id] = connection_count.get(source_id, 0) + 1
                connection_count[target_id] = connection_count.get(target_id, 0) + 1

        # ==============================================
        # 1. NŒUD CENTRAL: Entreprise (la fiduciaire)
        # ==============================================
        from core.models import Entreprise
        entreprise = Entreprise.get_instance()
        if entreprise:
            fiduciaire_id = add_node('Fiduciaire', entreprise.pk, entreprise.raison_sociale, {
                'description': entreprise.but[:100] if entreprise.but else '',
                'ide': entreprise.ide_number,
                'forme_juridique': entreprise.get_forme_juridique_display(),
                'siege': entreprise.siege,
            })
        else:
            # Fallback si pas d'entreprise configurée
            fiduciaire_id = add_node('Fiduciaire', 'main', 'AltiusOne', {
                'description': 'Fiduciaire principale'
            })

        # ==============================================
        # 2. UTILISATEURS STAFF (collaborateurs)
        # ==============================================
        users = User.objects.filter(
            is_active=True,
            type_utilisateur='STAFF'
        ).select_related('role')[:limit_per_type or 50]

        for user in users:
            user_id = add_node('User', user.pk, user.get_full_name() or user.username, {
                'email': user.email,
                'role': user.role.nom if user.role else 'N/A',
            })
            # Tous les users staff sont liés à la fiduciaire
            add_edge(fiduciaire_id, user_id, 'gere')

        # ==============================================
        # 3. CLIENTS
        # ==============================================
        clients = Client.objects.filter(
            is_active=True
        ).select_related('responsable', 'adresse_siege')[:limit_per_type or 100]

        for client in clients:
            client_id = add_node('Client', client.pk,
                                 client.raison_sociale or client.nom_commercial, {
                'forme_juridique': client.get_forme_juridique_display(),
                'statut': client.get_statut_display(),
                'ide': client.ide_number,
            })
            # Client lié à la fiduciaire
            add_edge(fiduciaire_id, client_id, 'client_de')

            # Lien avec le responsable
            if client.responsable_id:
                resp_id = f"User:{client.responsable_id}"
                if resp_id in nodes:
                    add_edge(client_id, resp_id, 'responsable')

        # ==============================================
        # 4. CONTACTS
        # ==============================================
        contacts = Contact.objects.filter(
            is_active=True
        ).select_related('client')[:limit_per_type or 200]

        for contact in contacts:
            contact_id = add_node('Contact', contact.pk,
                                  f"{contact.prenom} {contact.nom}", {
                'fonction': contact.get_fonction_display(),
                'email': contact.email,
            })
            # Lien avec le client
            if contact.client_id:
                client_node_id = f"Client:{contact.client_id}"
                if client_node_id in nodes:
                    add_edge(client_node_id, contact_id, 'contact_de')

        # ==============================================
        # 5. MANDATS
        # ==============================================
        mandats = Mandat.objects.filter(
            statut='ACTIF'
        ).select_related('client', 'responsable')[:limit_per_type or 150]

        for mandat in mandats:
            mandat_id = add_node('Mandat', mandat.pk, mandat.numero, {
                'type': mandat.get_type_mandat_display(),
                'statut': mandat.get_statut_display(),
            })

            # Lien Client -> Mandat
            if mandat.client_id:
                client_node_id = f"Client:{mandat.client_id}"
                if client_node_id in nodes:
                    add_edge(client_node_id, mandat_id, 'mandat_de')

            # Lien Mandat -> Responsable
            if mandat.responsable_id:
                user_node_id = f"User:{mandat.responsable_id}"
                if user_node_id in nodes:
                    add_edge(mandat_id, user_node_id, 'responsable')

        # Équipes des mandats
        for mandat in mandats:
            mandat_node_id = f"Mandat:{mandat.pk}"
            if mandat_node_id in nodes:
                for member in mandat.equipe.all()[:5]:  # Limiter
                    user_node_id = f"User:{member.pk}"
                    if user_node_id in nodes:
                        add_edge(mandat_node_id, user_node_id, 'equipe')

        # ==============================================
        # 6. EXERCICES COMPTABLES
        # ==============================================
        exercices = ExerciceComptable.objects.select_related(
            'mandat'
        )[:limit_per_type or 100]

        for ex in exercices:
            if ex.mandat_id:
                mandat_node_id = f"Mandat:{ex.mandat_id}"
                if mandat_node_id in nodes:
                    ex_id = add_node('ExerciceComptable', ex.pk, f"Exercice {ex.annee}", {
                        'annee': ex.annee,
                        'statut': ex.get_statut_display(),
                    })
                    add_edge(mandat_node_id, ex_id, 'exercice_de')

        # ==============================================
        # 7. TÂCHES
        # ==============================================
        taches = Tache.objects.filter(
            statut__in=['A_FAIRE', 'EN_COURS']
        ).select_related('mandat', 'assigne_a')[:limit_per_type or 100]

        for tache in taches:
            tache_id = add_node('Tache', tache.pk, tache.titre[:30], {
                'priorite': tache.get_priorite_display(),
                'statut': tache.get_statut_display(),
            })

            if tache.mandat_id:
                mandat_node_id = f"Mandat:{tache.mandat_id}"
                if mandat_node_id in nodes:
                    add_edge(mandat_node_id, tache_id, 'tache_de')

            if tache.assigne_a_id:
                user_node_id = f"User:{tache.assigne_a_id}"
                if user_node_id in nodes:
                    add_edge(tache_id, user_node_id, 'assigne_a')

        # ==============================================
        # 8. DOSSIERS
        # ==============================================
        dossiers = Dossier.objects.filter(
            is_active=True
        ).select_related('client', 'mandat')[:limit_per_type or 100]

        for dossier in dossiers:
            dossier_id = add_node('Dossier', dossier.pk, dossier.nom, {
                'type': dossier.get_type_dossier_display(),
            })

            if dossier.mandat_id:
                mandat_node_id = f"Mandat:{dossier.mandat_id}"
                if mandat_node_id in nodes:
                    add_edge(mandat_node_id, dossier_id, 'dossier_de')
            elif dossier.client_id:
                client_node_id = f"Client:{dossier.client_id}"
                if client_node_id in nodes:
                    add_edge(client_node_id, dossier_id, 'dossier_de')

        # ==============================================
        # 9. DOCUMENTS (limité)
        # ==============================================
        documents = Document.objects.filter(
            is_active=True
        ).select_related('mandat', 'dossier')[:limit_per_type or 50]

        for doc in documents:
            doc_id = add_node('Document', doc.pk, doc.nom_fichier[:25], {
                'extension': doc.extension,
                'statut': doc.get_statut_traitement_display(),
            })

            if doc.dossier_id:
                dossier_node_id = f"Dossier:{doc.dossier_id}"
                if dossier_node_id in nodes:
                    add_edge(dossier_node_id, doc_id, 'document_de')
            elif doc.mandat_id:
                mandat_node_id = f"Mandat:{doc.mandat_id}"
                if mandat_node_id in nodes:
                    add_edge(mandat_node_id, doc_id, 'document_de')

        # ==============================================
        # 10. FACTURES
        # ==============================================
        factures = Facture.objects.filter(
            statut__in=['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']
        ).select_related('mandat', 'client')[:limit_per_type or 80]

        for facture in factures:
            facture_id = add_node('Facture', facture.pk, facture.numero_facture, {
                'montant': str(facture.montant_ttc),
                'statut': facture.get_statut_display(),
            })

            if facture.mandat_id:
                mandat_node_id = f"Mandat:{facture.mandat_id}"
                if mandat_node_id in nodes:
                    add_edge(mandat_node_id, facture_id, 'facture_de')

        # ==============================================
        # 11. PAIEMENTS
        # ==============================================
        paiements = Paiement.objects.filter(
            valide=True
        ).select_related('facture')[:limit_per_type or 50]

        for paiement in paiements:
            if paiement.facture_id:
                facture_node_id = f"Facture:{paiement.facture_id}"
                if facture_node_id in nodes:
                    paiement_id = add_node('Paiement', paiement.pk,
                                           f"PAY-{str(paiement.pk)[:8]}", {
                        'montant': str(paiement.montant),
                        'mode': paiement.get_mode_paiement_display(),
                    })
                    add_edge(facture_node_id, paiement_id, 'paiement_de')

        # ==============================================
        # APPLIQUER LE LAYOUT CIRCULAIRE
        # ==============================================
        positions = circular_layout(nodes_by_type)

        for node_id, (x, y) in positions.items():
            if node_id in nodes:
                nodes[node_id]['x'] = x
                nodes[node_id]['y'] = y

        # Ajouter le nombre de connexions
        for node_id, node in nodes.items():
            node['connections'] = connection_count.get(node_id, 0)
            # Ajuster la taille en fonction des connexions
            base_size = node['size']
            conn = node['connections']
            node['size'] = min(base_size + conn * 0.5, base_size * 2.5)

        # Stats par type
        stats = {}
        for node in nodes.values():
            t = node['nodeType']
            if t not in stats:
                stats[t] = {
                    'count': 0,
                    'color': NODE_TYPES.get(t, {}).get('color', '#6b7280'),
                    'icon': NODE_TYPES.get(t, {}).get('icon', 'fa-circle'),
                }
            stats[t]['count'] += 1

        # Stats des relations
        edge_stats = {}
        for edge in edges:
            et = edge['edgeType']
            if et not in edge_stats:
                edge_stats[et] = {
                    'count': 0,
                    'color': EDGE_TYPES.get(et, {}).get('color', 'rgba(100,100,100,0.3)'),
                    'label': EDGE_TYPES.get(et, {}).get('label', et),
                }
            edge_stats[et]['count'] += 1

        return {
            'nodes': list(nodes.values()),
            'edges': edges,
            'stats': stats,
            'edgeStats': edge_stats,
            'meta': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'types_count': len(stats),
            }
        }


# =============================================================================
# VUES
# =============================================================================

class GraphView(LoginRequiredMixin, GraphDataMixin, TemplateView):
    """Vue principale du graphe relationnel."""
    template_name = 'core/graph.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        graph_data = self.get_graph_data()

        context['graph_data'] = json.dumps(graph_data)
        context['graph_stats'] = graph_data['stats']
        context['graph_meta'] = graph_data['meta']
        context['node_types'] = NODE_TYPES
        context['edge_types'] = EDGE_TYPES
        return context


class GraphAPIView(LoginRequiredMixin, GraphDataMixin, View):
    """API pour récupérer les données du graphe."""

    def get(self, request, type=None, pk=None):
        limit = request.GET.get('limit', None)
        limit = int(limit) if limit else None
        graph_data = self.get_graph_data(limit_per_type=limit)
        return JsonResponse(graph_data)


class GraphStatsAPIView(LoginRequiredMixin, View):
    """API pour les statistiques du graphe."""

    def get(self, request):
        from core.models import Client, Mandat, User
        from documents.models import Document, Dossier
        from facturation.models import Facture

        stats = {}
        for node_type, config in NODE_TYPES.items():
            stats[node_type] = {
                'color': config['color'],
                'icon': config.get('icon', ''),
            }

        stats['Client']['count'] = Client.objects.filter(is_active=True).count()
        stats['Mandat']['count'] = Mandat.objects.filter(statut='ACTIF').count()
        stats['User']['count'] = User.objects.filter(is_active=True, type_utilisateur='STAFF').count()
        stats['Document']['count'] = Document.objects.filter(is_active=True).count()
        stats['Dossier']['count'] = Dossier.objects.filter(is_active=True).count()
        stats['Facture']['count'] = Facture.objects.exclude(statut__in=['BROUILLON', 'ANNULEE']).count()
        stats['Fiduciaire']['count'] = 1

        return JsonResponse({'stats': stats})
