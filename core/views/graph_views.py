# core/views/graph_views.py
"""
Visualiseur de graphe relationnel pour AltiusOne.
Affiche tous les modèles et leurs relations de manière interactive.
Inspiré de Retina (OuestWare).
"""

import json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.apps import apps
from django.db.models import ForeignKey, ManyToManyField, OneToOneField, Count
from django.urls import reverse, NoReverseMatch
from django.http import JsonResponse
from django.views import View

# Configuration des modèles à inclure dans le graphe
GRAPH_CONFIG = {
    # Modèles principaux et leurs configurations
    'models': {
        # Core
        'core.Client': {
            'color': '#3B82F6',  # Bleu
            'size': 20,
            'label_field': 'raison_sociale',
            'icon': 'building',
            'priority': 1,  # Plus haut = plus important
        },
        'core.Mandat': {
            'color': '#10B981',  # Vert
            'size': 16,
            'label_field': 'numero',
            'icon': 'briefcase',
            'priority': 2,
        },
        'core.User': {
            'color': '#8B5CF6',  # Violet
            'size': 12,
            'label_field': 'get_full_name',
            'icon': 'user',
            'priority': 3,
        },
        'core.ExerciceComptable': {
            'color': '#F59E0B',  # Orange
            'size': 10,
            'label_field': '__str__',
            'icon': 'calendar',
            'priority': 4,
        },
        'core.Tache': {
            'color': '#EC4899',  # Rose
            'size': 8,
            'label_field': 'titre',
            'icon': 'check-square',
            'priority': 5,
        },
        # Comptabilité
        'comptabilite.PlanComptable': {
            'color': '#6366F1',  # Indigo
            'size': 14,
            'label_field': 'nom',
            'icon': 'book',
            'priority': 3,
        },
        'comptabilite.Compte': {
            'color': '#06B6D4',  # Cyan
            'size': 8,
            'label_field': 'numero',
            'icon': 'hash',
            'priority': 6,
        },
        'comptabilite.Ecriture': {
            'color': '#84CC16',  # Lime
            'size': 6,
            'label_field': 'libelle',
            'icon': 'edit-3',
            'priority': 7,
        },
        # Facturation
        'facturation.Facture': {
            'color': '#EF4444',  # Rouge
            'size': 10,
            'label_field': 'numero',
            'icon': 'file-text',
            'priority': 4,
        },
        'facturation.Paiement': {
            'color': '#22C55E',  # Vert clair
            'size': 8,
            'label_field': '__str__',
            'icon': 'credit-card',
            'priority': 6,
        },
        # Documents
        'documents.Dossier': {
            'color': '#F97316',  # Orange vif
            'size': 10,
            'label_field': 'nom',
            'icon': 'folder',
            'priority': 4,
        },
        'documents.Document': {
            'color': '#A855F7',  # Violet clair
            'size': 6,
            'label_field': 'nom_fichier',
            'icon': 'file',
            'priority': 7,
        },
        # Salaires
        'salaires.Employe': {
            'color': '#14B8A6',  # Teal
            'size': 12,
            'label_field': '__str__',
            'icon': 'users',
            'priority': 4,
        },
        'salaires.FicheSalaire': {
            'color': '#0EA5E9',  # Sky
            'size': 6,
            'label_field': '__str__',
            'icon': 'file-text',
            'priority': 7,
        },
        # TVA
        'tva.DeclarationTVA': {
            'color': '#DC2626',  # Rouge foncé
            'size': 10,
            'label_field': '__str__',
            'icon': 'percent',
            'priority': 5,
        },
        # Fiscalité
        'fiscalite.DeclarationFiscale': {
            'color': '#7C3AED',  # Violet foncé
            'size': 10,
            'label_field': '__str__',
            'icon': 'file-minus',
            'priority': 5,
        },
    },
    # Types de relations
    'relations': {
        'ForeignKey': {'color': '#6B7280', 'width': 1, 'style': 'solid'},
        'OneToOneField': {'color': '#3B82F6', 'width': 2, 'style': 'solid'},
        'ManyToManyField': {'color': '#10B981', 'width': 1, 'style': 'dashed'},
    },
    # Limites
    'max_nodes': 500,
    'max_edges': 2000,
}


def get_model_config(model_label):
    """Récupère la configuration d'un modèle ou retourne une config par défaut."""
    default = {
        'color': '#9CA3AF',
        'size': 8,
        'label_field': '__str__',
        'icon': 'circle',
        'priority': 10,
    }
    return GRAPH_CONFIG['models'].get(model_label, default)


def get_detail_url(model, instance):
    """Tente de générer l'URL de détail pour une instance."""
    app_label = model._meta.app_label
    model_name = model._meta.model_name

    # Patterns d'URL courants
    url_patterns = [
        f'{app_label}:{model_name}-detail',
        f'core:{model_name}-detail',
        f'{model_name}-detail',
    ]

    for pattern in url_patterns:
        try:
            return reverse(pattern, kwargs={'pk': instance.pk})
        except NoReverseMatch:
            continue
    return None


def get_list_url(model):
    """Tente de générer l'URL de liste pour un modèle."""
    app_label = model._meta.app_label
    model_name = model._meta.model_name

    url_patterns = [
        f'{app_label}:{model_name}-list',
        f'core:{model_name}-list',
        f'{model_name}-list',
    ]

    for pattern in url_patterns:
        try:
            return reverse(pattern)
        except NoReverseMatch:
            continue
    return None


def get_instance_label(instance, label_field):
    """Récupère le label d'une instance."""
    if label_field == '__str__':
        return str(instance)

    value = getattr(instance, label_field, None)
    if callable(value):
        return value()
    return str(value) if value else str(instance)


class GraphDataMixin:
    """Mixin pour générer les données du graphe."""

    def get_graph_data(self, center_type=None, center_pk=None, depth=2):
        """
        Génère les données du graphe (nodes et edges).

        Args:
            center_type: Type de modèle pour centrer la vue (ex: 'client')
            center_pk: PK de l'instance centrale
            depth: Profondeur de traversée depuis le centre
        """
        nodes = []
        edges = []
        node_ids = set()
        edge_ids = set()

        # Statistiques par type
        stats = {}

        # Collecter tous les modèles configurés
        for model_label, config in GRAPH_CONFIG['models'].items():
            try:
                app_label, model_name = model_label.split('.')
                model = apps.get_model(app_label, model_name)
            except (LookupError, ValueError):
                continue

            # Récupérer les instances (avec limite)
            queryset = model.objects.all()

            # Filtrer si on a un centre
            if center_type and center_pk:
                # TODO: Filtrer par proximité au centre
                pass

            # Appliquer la limite
            instances = queryset[:GRAPH_CONFIG['max_nodes'] // len(GRAPH_CONFIG['models'])]

            # Stats
            stats[model_label] = {
                'count': queryset.count(),
                'displayed': len(instances),
                'color': config['color'],
                'label': str(model._meta.verbose_name_plural),
                'list_url': get_list_url(model),
            }

            # Créer les nodes
            for instance in instances:
                node_id = f"{model_label}:{instance.pk}"
                if node_id in node_ids:
                    continue
                node_ids.add(node_id)

                nodes.append({
                    'id': node_id,
                    'label': get_instance_label(instance, config['label_field']),
                    'type': model_label,
                    'type_label': str(model._meta.verbose_name),
                    'color': config['color'],
                    'size': config['size'],
                    'icon': config['icon'],
                    'url': get_detail_url(model, instance),
                    'pk': str(instance.pk),
                    # Données supplémentaires pour le panneau de détails
                    'data': self._get_instance_data(instance),
                })

            # Créer les edges (relations)
            for field in model._meta.get_fields():
                if isinstance(field, (ForeignKey, OneToOneField)):
                    rel_type = 'OneToOneField' if isinstance(field, OneToOneField) else 'ForeignKey'
                    rel_config = GRAPH_CONFIG['relations'][rel_type]

                    related_model = field.related_model
                    related_label = f"{related_model._meta.app_label}.{related_model._meta.model_name}"

                    # Seulement si le modèle cible est dans notre config
                    if related_label not in GRAPH_CONFIG['models']:
                        continue

                    for instance in instances:
                        related_instance = getattr(instance, field.name, None)
                        if related_instance:
                            source_id = f"{model_label}:{instance.pk}"
                            target_id = f"{related_label}:{related_instance.pk}"
                            edge_id = f"{source_id}->{target_id}"

                            if edge_id not in edge_ids and len(edges) < GRAPH_CONFIG['max_edges']:
                                edge_ids.add(edge_id)
                                edges.append({
                                    'id': edge_id,
                                    'source': source_id,
                                    'target': target_id,
                                    'type': rel_type,
                                    'label': field.name,
                                    'color': rel_config['color'],
                                    'size': rel_config['width'],
                                })

                elif isinstance(field, ManyToManyField):
                    rel_config = GRAPH_CONFIG['relations']['ManyToManyField']
                    related_model = field.related_model
                    related_label = f"{related_model._meta.app_label}.{related_model._meta.model_name}"

                    if related_label not in GRAPH_CONFIG['models']:
                        continue

                    for instance in instances:
                        related_instances = getattr(instance, field.name).all()[:10]  # Limite M2M
                        for related_instance in related_instances:
                            source_id = f"{model_label}:{instance.pk}"
                            target_id = f"{related_label}:{related_instance.pk}"
                            edge_id = f"{source_id}<->{target_id}"

                            if edge_id not in edge_ids and len(edges) < GRAPH_CONFIG['max_edges']:
                                edge_ids.add(edge_id)
                                edges.append({
                                    'id': edge_id,
                                    'source': source_id,
                                    'target': target_id,
                                    'type': 'ManyToManyField',
                                    'label': field.name,
                                    'color': rel_config['color'],
                                    'size': rel_config['width'],
                                })

        return {
            'nodes': nodes,
            'edges': edges,
            'stats': stats,
            'meta': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'max_nodes': GRAPH_CONFIG['max_nodes'],
                'max_edges': GRAPH_CONFIG['max_edges'],
            }
        }

    def _get_instance_data(self, instance):
        """Extrait les données clés d'une instance pour le panneau de détails."""
        data = {}
        model = instance._meta.model

        # Champs à exclure
        exclude = {'id', 'pk', 'password', 'created_at', 'updated_at', 'is_active'}

        for field in model._meta.get_fields():
            if field.name in exclude:
                continue
            if hasattr(field, 'get_internal_type'):
                field_type = field.get_internal_type()
                if field_type in ('CharField', 'TextField', 'DateField', 'DateTimeField',
                                  'DecimalField', 'IntegerField', 'BooleanField', 'EmailField'):
                    value = getattr(instance, field.name, None)
                    if value is not None:
                        key = str(field.verbose_name) if field.verbose_name else field.name
                        data[key] = str(value)[:100]

        return dict(list(data.items())[:8])  # Limite à 8 champs


class GraphView(LoginRequiredMixin, GraphDataMixin, TemplateView):
    """Vue principale du graphe relationnel."""
    template_name = 'core/graph.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Paramètres de centrage optionnels
        center_type = self.kwargs.get('type')
        center_pk = self.kwargs.get('pk')

        # Générer les données du graphe
        graph_data = self.get_graph_data(center_type, center_pk)

        context['graph_data'] = json.dumps(graph_data)
        context['graph_stats'] = graph_data['stats']
        context['graph_meta'] = graph_data['meta']
        context['center_type'] = center_type
        context['center_pk'] = center_pk

        return context


class GraphAPIView(LoginRequiredMixin, GraphDataMixin, View):
    """API pour récupérer les données du graphe (AJAX)."""

    def get(self, request, type=None, pk=None):
        graph_data = self.get_graph_data(type, pk)
        return JsonResponse(graph_data)


class GraphStatsAPIView(LoginRequiredMixin, View):
    """API pour les statistiques du graphe."""

    def get(self, request):
        stats = {}

        for model_label, config in GRAPH_CONFIG['models'].items():
            try:
                app_label, model_name = model_label.split('.')
                model = apps.get_model(app_label, model_name)
                stats[model_label] = {
                    'count': model.objects.count(),
                    'color': config['color'],
                    'label': str(model._meta.verbose_name_plural),
                    'list_url': get_list_url(model),
                }
            except (LookupError, ValueError):
                continue

        return JsonResponse({'stats': stats})
