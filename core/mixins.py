# core/mixins.py
from django.db.models import Q


class SearchMixin:
    """Mixin ajoutant la recherche ?q= sur toutes les colonnes spécifiées.

    Usage:
        class MandatListView(SearchMixin, LoginRequiredMixin, ListView):
            search_fields = ['numero', 'client__raison_sociale', 'description']

    La recherche "jorat gospel" cherche les objets dont au moins un champ
    contient "jorat" ET au moins un champ contient "gospel" (insensible à la casse).
    """

    search_fields = []
    search_param = 'q'

    def get_search_query(self):
        return self.request.GET.get(self.search_param, '').strip()

    def apply_search(self, queryset):
        query = self.get_search_query()
        if not query or not self.search_fields:
            return queryset
        for term in query.split():
            term_q = Q()
            for field in self.search_fields:
                term_q |= Q(**{f'{field}__icontains': term})
            queryset = queryset.filter(term_q)
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query'] = self.get_search_query()
        return ctx
