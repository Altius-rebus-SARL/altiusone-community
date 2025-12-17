# tva/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from core.permissions import BusinessPermissionMixin, permission_required_business
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count, Sum, F, Max
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from decimal import Decimal
import json
import csv
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import io


from .models import (
    ConfigurationTVA,
    TauxTVA,
    CodeTVA,
    DeclarationTVA,
    LigneTVA,
    OperationTVA,
    CorrectionTVA,
)
from .forms import (
    ConfigurationTVAForm,
    DeclarationTVAForm,
    LigneTVAForm,
    OperationTVAForm,
    CorrectionTVAForm,
)
from .filters import DeclarationTVAFilter, OperationTVAFilter
from core.models import Mandat


# ============ CONFIGURATION TVA ============


class ConfigurationTVAListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des configurations TVA"""

    model = ConfigurationTVA
    template_name = "tva/configuration_list.html"
    context_object_name = "configurations"
    business_permission = 'tva.config_tva'

    def get_queryset(self):
        return ConfigurationTVA.objects.select_related("mandat__client")


class ConfigurationTVADetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une configuration TVA"""

    model = ConfigurationTVA
    template_name = "tva/configuration_detail.html"
    context_object_name = "configuration"
    business_permission = 'tva.config_tva'


class ConfigurationTVAUpdateView(
    LoginRequiredMixin, BusinessPermissionMixin, UpdateView
):
    """Modification d'une configuration TVA"""

    model = ConfigurationTVA
    form_class = ConfigurationTVAForm
    template_name = "tva/configuration_form.html"
    business_permission = 'tva.config_tva'

    def get_success_url(self):
        return reverse_lazy("tva:configuration-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Configuration TVA modifiée avec succès"))
        return super().form_valid(form)


# ============ DÉCLARATIONS TVA ============


class DeclarationTVAListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des déclarations TVA"""

    model = DeclarationTVA
    template_name = "tva/declaration_list.html"
    context_object_name = "declarations"
    paginate_by = 50
    business_permission = 'tva.view_declarations'

    def get_queryset(self):
        queryset = DeclarationTVA.objects.select_related(
            "mandat__client"
        ).prefetch_related("lignes")

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager() and not user.has_perm("tva.view_all_declarationtva"):
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = DeclarationTVAFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-annee", "-trimestre", "-semestre")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "brouillon": queryset.filter(statut="BROUILLON").count(),
            "soumis": queryset.filter(statut="SOUMIS").count(),
            "accepte": queryset.filter(statut="ACCEPTE").count(),
            "paye": queryset.filter(statut="PAYE").count(),
            "tva_due_annee": queryset.filter(annee=datetime.now().year).aggregate(
                Sum("solde_tva")
            )["solde_tva__sum"]
            or 0,
        }
        
        # Années disponibles
        context["annees"] = range(2020, datetime.now().year + 2)

        return context

class DeclarationTVADetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une déclaration TVA"""

    model = DeclarationTVA
    template_name = "tva/declaration_detail.html"
    context_object_name = "declaration"
    business_permission = 'tva.view_declarations'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("mandat__client", "valide_par", "soumis_par")
            .prefetch_related("lignes__code_tva", "operations", "corrections")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        declaration = self.object

        # Lignes groupées par catégorie
        lignes_par_categorie = {}
        for ligne in declaration.lignes.all():
            categorie = ligne.code_tva.categorie
            if categorie not in lignes_par_categorie:
                lignes_par_categorie[categorie] = []
            lignes_par_categorie[categorie].append(ligne)

        context["lignes_par_categorie"] = lignes_par_categorie

        # Opérations TVA de la période
        context["operations"] = declaration.operations.select_related(
            "code_tva", "ecriture_comptable"
        ).order_by("date_operation")

        # Corrections
        context["corrections"] = declaration.corrections.select_related("code_tva")

        return context


class DeclarationTVACreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'une déclaration TVA"""

    model = DeclarationTVA
    form_class = DeclarationTVAForm
    template_name = "tva/declaration_form.html"
    business_permission = 'tva.add_declaration'

    def get_initial(self):
        initial = super().get_initial()

        # Préremplir avec le mandat si fourni
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            mandat = get_object_or_404(Mandat, pk=mandat_id)
            initial["mandat"] = mandat

            # Configuration TVA
            config = mandat.config_tva
            initial["methode"] = config.methode_calcul

        # Période par défaut: trimestre en cours
        today = datetime.now().date()
        initial["annee"] = today.year
        initial["trimestre"] = (today.month - 1) // 3 + 1

        return initial

    def get_success_url(self):
        return reverse_lazy("tva:declaration-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Déclaration TVA créée avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def declaration_calculer(request, pk):
    """Calcule automatiquement les montants de la déclaration"""
    declaration = get_object_or_404(DeclarationTVA, pk=pk, statut="BROUILLON")

    try:
        declaration.calculer_automatiquement()
        messages.success(request, _("Déclaration calculée avec succès"))
    except Exception as e:
        messages.error(request, f"Erreur lors du calcul: {str(e)}")

    return redirect("tva:declaration-detail", pk=pk)


@login_required
@require_http_methods(["POST"])
def declaration_valider(request, pk):
    """Valide une déclaration TVA"""
    declaration = get_object_or_404(DeclarationTVA, pk=pk, statut="BROUILLON")

    try:
        declaration.valider(request.user)
        messages.success(request, _("Déclaration validée avec succès"))
    except ValueError as e:
        messages.error(request, str(e))

    return redirect("tva:declaration-detail", pk=pk)



@login_required
def declaration_exporter_xml(request, pk):
    """Exporte la déclaration au format XML AFC"""
    declaration = get_object_or_404(DeclarationTVA, pk=pk)

    try:
        # Générer le XML via la méthode du modèle
        fichier = declaration.generer_xml()

        # Retourner le fichier
        with fichier.open("rb") as f:
            response = HttpResponse(f.read(), content_type="application/xml")
            response["Content-Disposition"] = f'attachment; filename="{fichier.name}"'

        messages.success(request, _("Export XML généré avec succès"))
        return response

    except Exception as e:
        messages.error(request, f"Erreur lors de la génération XML: {str(e)}")
        return redirect("tva:declaration-detail", pk=pk)


@login_required
def declaration_exporter_pdf(request, pk):
    """Génère un PDF de la déclaration"""
    declaration = get_object_or_404(DeclarationTVA, pk=pk)

    try:
        # Générer le PDF via la méthode du modèle
        fichier = declaration.generer_pdf()

        # Retourner le fichier
        with fichier.open("rb") as f:
            response = HttpResponse(f.read(), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{fichier.name}"'

        messages.success(request, _("Export PDF généré avec succès"))
        return response

    except Exception as e:
        messages.error(request, f"Erreur lors de la génération PDF: {str(e)}")
        return redirect("tva:declaration-detail", pk=pk)
# ============ OPÉRATIONS TVA ============


class OperationTVAListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des opérations TVA"""

    model = OperationTVA
    template_name = "tva/operation_list.html"
    context_object_name = "operations"
    paginate_by = 100
    business_permission = 'tva.view_operations'

    def get_queryset(self):
        queryset = OperationTVA.objects.select_related(
            "mandat", "declaration_tva", "code_tva", "ecriture_comptable"
        )

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager() and not user.has_perm("tva.view_all_operationtva"):
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = OperationTVAFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-date_operation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "non_integrees": queryset.filter(integre_declaration=False).count(),
            "tva_due": queryset.filter(type_operation="VENTE").aggregate(
                Sum("montant_tva")
            )["montant_tva__sum"]
            or 0,
            "tva_prealable": queryset.filter(type_operation="ACHAT").aggregate(
                Sum("montant_tva")
            )["montant_tva__sum"]
            or 0,
        }

        return context


class OperationTVACreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création manuelle d'une opération TVA"""

    model = OperationTVA
    form_class = OperationTVAForm
    template_name = "tva/operation_form.html"
    business_permission = 'tva.view_operations'
    success_url = reverse_lazy("tva:operation-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Opération TVA créée avec succès"))
        return super().form_valid(form)
