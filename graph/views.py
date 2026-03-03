# graph/views.py
"""Vues CBV pour le graphe relationnel."""
import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DetailView,
)

from core.permissions import BusinessPermissionMixin
from .models import OntologieType, Entite, Relation, Anomalie, RequeteSauvegardee
from .forms import (
    OntologieTypeForm, EntiteForm, RelationForm,
    AnomalieTraiterForm, ImportCSVForm, RequeteSauvegardeeForm,
)
from .filters import EntiteFilter, RelationFilter, AnomalieFilter


# ========================================================================
# Explorateur de graphe (page principale)
# ========================================================================

class ExplorerView(LoginRequiredMixin, BusinessPermissionMixin, TemplateView):
    """Page principale de l'explorateur de graphe D3.js."""

    template_name = 'graph/explorer.html'
    business_permission = 'graph.view_graph'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types_entites'] = OntologieType.objects.filter(
            categorie='entity', is_active=True,
        ).values('id', 'nom', 'icone', 'couleur')
        context['types_relations'] = OntologieType.objects.filter(
            categorie='relation', is_active=True,
        ).values('id', 'nom', 'verbe')
        # Nœud de départ = le plus connecté (pour un graphe riche dès l'ouverture)
        best_node = (
            Entite.objects.filter(is_active=True)
            .annotate(nb_rels=Count('relations_sortantes') + Count('relations_entrantes'))
            .order_by('-nb_rels')
            .values('id', 'nom', 'type__nom')
            .first()
        )
        all_entites = list(
            Entite.objects.filter(is_active=True)
            .values('id', 'nom', 'type__nom')[:100]
        )
        if best_node and all_entites:
            all_entites = [e for e in all_entites if str(e['id']) != str(best_node['id'])]
            all_entites.insert(0, best_node)
        context['entites_json'] = json.dumps(all_entites, default=str)

        # Précharger le graphe initial côté serveur (pas d'appel API JS nécessaire)
        initial_graph = {'nodes': [], 'links': []}
        entite_param = self.request.GET.get('entite')
        start_id = entite_param or (str(best_node['id']) if best_node else None)
        if start_id:
            try:
                from .services.exploration import explorer_graphe
                initial_graph = explorer_graphe(
                    entite_id=start_id,
                    profondeur=int(self.request.GET.get('profondeur', 3)),
                )
            except Exception:
                pass
        context['initial_graph_json'] = json.dumps(initial_graph, default=str)
        context['stats'] = {
            'entites': Entite.objects.filter(is_active=True).count(),
            'relations': Relation.objects.filter(is_active=True).count(),
            'anomalies': Anomalie.objects.filter(
                statut__in=['nouveau', 'en_cours'], is_active=True,
            ).count(),
        }
        return context


# ========================================================================
# Ontologie CRUD
# ========================================================================

class OntologieListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des types d'ontologie."""

    model = OntologieType
    template_name = 'graph/ontologie_list.html'
    context_object_name = 'types'
    business_permission = 'graph.view_graph'

    def get_queryset(self):
        return OntologieType.objects.filter(is_active=True).annotate(
            nb_entites=Count(
                'entites', filter=Q(entites__is_active=True),
            ),
            nb_relations=Count(
                'relations', filter=Q(relations__is_active=True),
            ),
        ).order_by('ordre_affichage', 'nom')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types_entity'] = [t for t in context['types'] if t.categorie == 'entity']
        context['types_relation'] = [t for t in context['types'] if t.categorie == 'relation']
        return context


class OntologieCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un type d'ontologie."""

    model = OntologieType
    form_class = OntologieTypeForm
    template_name = 'graph/ontologie_form.html'
    business_permission = 'graph.view_graph'

    def get_success_url(self):
        return reverse_lazy('graph:ontologie-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Type d'ontologie créé avec succès"))
        return super().form_valid(form)


class OntologieUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un type d'ontologie."""

    model = OntologieType
    form_class = OntologieTypeForm
    template_name = 'graph/ontologie_form.html'
    business_permission = 'graph.view_graph'

    def get_success_url(self):
        return reverse_lazy('graph:ontologie-list')

    def form_valid(self, form):
        messages.success(self.request, _("Type d'ontologie modifié avec succès"))
        return super().form_valid(form)


# ========================================================================
# Entités CRUD
# ========================================================================

class EntiteListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des entités avec filtres."""

    model = Entite
    template_name = 'graph/entite_list.html'
    context_object_name = 'entites'
    paginate_by = 50
    business_permission = 'graph.view_graph'

    def get_queryset(self):
        queryset = Entite.objects.filter(is_active=True).select_related('type')
        self.filterset = EntiteFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        context['total'] = self.filterset.qs.count()
        return context


class EntiteCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'une entité."""

    model = Entite
    form_class = EntiteForm
    template_name = 'graph/entite_form.html'
    business_permission = 'graph.view_graph'

    def get_success_url(self):
        return reverse_lazy('graph:entite-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Entité créée avec succès"))
        return super().form_valid(form)


class EntiteUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'une entité."""

    model = Entite
    form_class = EntiteForm
    template_name = 'graph/entite_form.html'
    business_permission = 'graph.view_graph'

    def get_success_url(self):
        return reverse_lazy('graph:entite-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Entité modifiée avec succès"))
        return super().form_valid(form)


class EntiteDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une entité."""

    model = Entite
    template_name = 'graph/entite_detail.html'
    context_object_name = 'entite'
    business_permission = 'graph.view_graph'

    def get_queryset(self):
        return Entite.objects.filter(is_active=True).select_related('type')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        context['relations_sortantes'] = Relation.objects.filter(
            source=obj, is_active=True,
        ).select_related('type', 'cible__type')[:20]
        context['relations_entrantes'] = Relation.objects.filter(
            cible=obj, is_active=True,
        ).select_related('type', 'source__type')[:20]
        context['anomalies'] = Anomalie.objects.filter(
            Q(entite=obj) | Q(entite_liee=obj),
            statut__in=['nouveau', 'en_cours'],
            is_active=True,
        )[:10]
        return context


# ========================================================================
# Relations
# ========================================================================

class RelationCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'une relation."""

    model = Relation
    form_class = RelationForm
    template_name = 'graph/relation_form.html'
    business_permission = 'graph.view_graph'

    def get_initial(self):
        initial = super().get_initial()
        source_id = self.request.GET.get('source')
        if source_id:
            initial['source'] = source_id
        return initial

    def get_success_url(self):
        return reverse_lazy('graph:entite-detail', kwargs={'pk': self.object.source_id})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Relation créée avec succès"))
        return super().form_valid(form)


# ========================================================================
# Anomalies
# ========================================================================

class AnomalieListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des anomalies."""

    model = Anomalie
    template_name = 'graph/anomalie_list.html'
    context_object_name = 'anomalies'
    paginate_by = 50
    business_permission = 'graph.view_graph'

    def get_queryset(self):
        queryset = Anomalie.objects.filter(is_active=True).select_related(
            'entite__type', 'entite_liee__type',
        )
        self.filterset = AnomalieFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        context['stats'] = {
            'nouveau': self.filterset.qs.filter(statut='nouveau').count(),
            'en_cours': self.filterset.qs.filter(statut='en_cours').count(),
            'total': self.filterset.qs.count(),
        }
        return context


class AnomalieDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une anomalie avec formulaire de traitement."""

    model = Anomalie
    template_name = 'graph/anomalie_detail.html'
    context_object_name = 'anomalie'
    business_permission = 'graph.view_graph'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AnomalieTraiterForm(initial={
            'statut': self.object.statut,
        })
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = AnomalieTraiterForm(request.POST)
        if form.is_valid():
            self.object.statut = form.cleaned_data['statut']
            self.object.commentaire_resolution = form.cleaned_data.get('commentaire', '')
            self.object.traite_par = request.user
            self.object.traite_at = timezone.now()
            self.object.save(update_fields=[
                'statut', 'commentaire_resolution', 'traite_par', 'traite_at',
            ])
            messages.success(request, _("Anomalie mise à jour"))
            return self.render_to_response(self.get_context_data(form=form))
        return self.render_to_response(self.get_context_data(form=form))


# ========================================================================
# Import
# ========================================================================

class ImportView(LoginRequiredMixin, BusinessPermissionMixin, TemplateView):
    """Page d'import CSV."""

    template_name = 'graph/import.html'
    business_permission = 'graph.view_graph'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ImportCSVForm()
        return context

    def post(self, request, *args, **kwargs):
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            from .services.import_data import importer_csv
            result = importer_csv(
                file=form.cleaned_data['file'],
                type_id=form.cleaned_data['type_id'].pk,
                mapping=form.cleaned_data['mapping_json'],
                created_by=request.user,
            )
            if result['created'] > 0:
                messages.success(
                    request,
                    _("%(count)d entités importées avec succès") % {'count': result['created']},
                )
            if result['errors']:
                for err in result['errors'][:5]:
                    messages.warning(request, err)
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


# ========================================================================
# Recherche
# ========================================================================

class RechercheView(LoginRequiredMixin, BusinessPermissionMixin, TemplateView):
    """Page de recherche sémantique."""

    template_name = 'graph/recherche.html'
    business_permission = 'graph.view_graph'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types_entites'] = OntologieType.objects.filter(
            categorie='entity', is_active=True,
        )
        return context
