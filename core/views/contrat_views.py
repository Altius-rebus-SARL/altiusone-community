# core/views/contrat_views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count, Sum
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from datetime import date

from core.permissions import BusinessPermissionMixin
from core.mixins import SearchMixin
from core.models import Contrat, ModeleContrat
from core.forms import ContratForm


# ============================================================================
# CONTRATS
# ============================================================================


class ContratListView(SearchMixin, LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des contrats"""

    model = Contrat
    business_permission = 'core.view_contrat'
    template_name = "core/contrat_list.html"
    context_object_name = "contrats"
    paginate_by = 50
    search_fields = ['numero', 'titre', 'client__raison_sociale', 'description', 'notes']

    def get_queryset(self):
        queryset = Contrat.objects.select_related(
            "client", "mandat", "devise", "created_by"
        )

        # Filtre par statut
        statut = self.request.GET.get("statut")
        if statut:
            queryset = queryset.filter(statut=statut)

        # Filtre par sens
        sens = self.request.GET.get("sens")
        if sens:
            queryset = queryset.filter(sens=sens)

        # Filtre par client
        client = self.request.GET.get("client")
        if client:
            queryset = queryset.filter(client_id=client)

        return self.apply_search(queryset.order_by("-date_emission", "-created_at"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Statistiques
        queryset = self.get_queryset()
        today = date.today()

        context["stats"] = {
            "total": queryset.count(),
            "actifs": queryset.filter(statut="ACTIF").count(),
            "en_retard": queryset.filter(
                statut="ACTIF",
                date_fin__lt=today,
            ).count(),
            "montant_total": queryset.filter(
                statut__in=["ACTIF", "SIGNE"]
            ).aggregate(Sum("montant"))["montant__sum"] or 0,
        }

        return context


class ContratDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Detail d'un contrat"""

    model = Contrat
    business_permission = 'core.view_contrat'
    template_name = "core/contrat_detail.html"
    context_object_name = "contrat"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "client",
                "mandat",
                "devise",
                "document",
                "modele_source",
                "created_by",
            )
        )


class ContratCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Creation d'un contrat"""

    model = Contrat
    form_class = ContratForm
    template_name = "core/contrat_form.html"
    business_permission = 'core.add_contrat'

    def get_success_url(self):
        return reverse_lazy("core:contrat-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Contrat cree avec succes"))
        return super().form_valid(form)


class ContratUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un contrat"""

    model = Contrat
    form_class = ContratForm
    template_name = "core/contrat_form.html"
    business_permission = 'core.add_contrat'

    def get_success_url(self):
        return reverse_lazy("core:contrat-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Contrat modifie avec succes"))
        return super().form_valid(form)


# ============================================================================
# MODELES DE CONTRAT
# ============================================================================


class ModeleContratListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des modeles de contrat"""

    model = ModeleContrat
    business_permission = 'core.view_contrat'
    template_name = "core/modele_contrat_list.html"
    context_object_name = "modeles"
    paginate_by = 50

    def get_queryset(self):
        return ModeleContrat.objects.filter(is_active=True).select_related(
            "document"
        ).order_by("ordre", "nom")
