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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import RegimeFiscal
        regimes_methodes = {
            r.pk.hex: r.methodes_disponibles
            for r in RegimeFiscal.objects.all()
        }
        context['regimes_methodes_json'] = json.dumps(regimes_methodes)
        return context

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

        # Formulaires pour ajout inline (brouillon uniquement)
        if declaration.statut == 'BROUILLON':
            context["ligne_form"] = LigneTVAForm()
            context["correction_form"] = CorrectionTVAForm()

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
    from django.http import FileResponse

    declaration = get_object_or_404(DeclarationTVA, pk=pk)

    try:
        fichier = declaration.generer_xml()

        response = FileResponse(fichier.open("rb"), content_type="application/xml")
        filename = fichier.name.split('/')[-1]
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        messages.error(request, _("Erreur lors de la génération XML: %(error)s") % {'error': str(e)})
        return redirect("tva:declaration-detail", pk=pk)


@login_required
def declaration_exporter_pdf(request, pk):
    """Génère et télécharge le PDF de la déclaration TVA."""
    from core.pdf import serve_pdf

    declaration = get_object_or_404(DeclarationTVA, pk=pk)
    return serve_pdf(
        request, declaration, 'fichier_pdf',
        f"declaration_tva_{declaration.numero_declaration}.pdf",
        ("tva:declaration-detail", pk),
        generate=True,
    )


@login_required
def declaration_preview_pdf(request, pk):
    """Aperçu inline du PDF de la déclaration TVA."""
    from core.pdf import serve_pdf

    declaration = get_object_or_404(DeclarationTVA, pk=pk)
    return serve_pdf(
        request, declaration, 'fichier_pdf',
        f"declaration_tva_{declaration.numero_declaration}.pdf",
        ("tva:declaration-detail", pk),
        generate=True, inline=True,
    )
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


# ============ DÉCLARATION — ÉDITION / SUPPRESSION / ACTIONS ============


class DeclarationTVAUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'une déclaration TVA (brouillon uniquement)"""

    model = DeclarationTVA
    form_class = DeclarationTVAForm
    template_name = "tva/declaration_form.html"
    business_permission = 'tva.add_declaration'

    def get_queryset(self):
        return super().get_queryset().filter(statut='BROUILLON')

    def get_success_url(self):
        return reverse_lazy("tva:declaration-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Déclaration TVA modifiée avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def declaration_supprimer(request, pk):
    """Supprime une déclaration TVA (brouillon uniquement)"""
    declaration = get_object_or_404(DeclarationTVA, pk=pk, statut="BROUILLON")

    # Délier les opérations intégrées
    declaration.operations.update(integre_declaration=False, declaration_tva=None, date_integration=None)

    declaration.delete()
    messages.success(request, _("Déclaration TVA supprimée"))
    return redirect("tva:declaration-list")


@login_required
@require_http_methods(["POST"])
def declaration_rouvrir(request, pk):
    """Rouvre une déclaration validée → brouillon"""
    declaration = get_object_or_404(DeclarationTVA, pk=pk, statut="VALIDE")

    try:
        declaration.rouvrir()
        messages.success(request, _("Déclaration rouverte en brouillon"))
    except ValueError as e:
        messages.error(request, str(e))

    return redirect("tva:declaration-detail", pk=pk)


@login_required
@require_http_methods(["POST"])
def declaration_soumettre(request, pk):
    """Soumet une déclaration validée à l'AFC"""
    declaration = get_object_or_404(DeclarationTVA, pk=pk, statut="VALIDE")

    try:
        numero_reference = request.POST.get('numero_reference', '').strip()
        declaration.soumettre_afc(request.user, numero_reference=numero_reference or None)
        messages.success(request, _("Déclaration soumise à l'AFC"))
    except ValueError as e:
        messages.error(request, str(e))

    return redirect("tva:declaration-detail", pk=pk)


# ============ LIGNES TVA — CRUD ============


@login_required
def ligne_tva_create(request, declaration_pk):
    """Ajouter une ligne TVA à une déclaration"""
    declaration = get_object_or_404(DeclarationTVA, pk=declaration_pk, statut="BROUILLON")

    if request.method == "POST":
        form = LigneTVAForm(request.POST)
        if form.is_valid():
            ligne = form.save(commit=False)
            ligne.declaration = declaration
            ligne.save()
            declaration.recalculer_totaux()
            messages.success(request, _("Ligne TVA ajoutée"))
            return redirect("tva:declaration-detail", pk=declaration.pk)
    else:
        form = LigneTVAForm()

    return render(request, "tva/ligne_tva_form.html", {
        "form": form,
        "declaration": declaration,
    })


@login_required
def ligne_tva_update(request, pk):
    """Modifier une ligne TVA"""
    ligne = get_object_or_404(LigneTVA, pk=pk, declaration__statut="BROUILLON")
    declaration = ligne.declaration

    if request.method == "POST":
        form = LigneTVAForm(request.POST, instance=ligne)
        if form.is_valid():
            form.save()
            declaration.recalculer_totaux()
            messages.success(request, _("Ligne TVA modifiée"))
            return redirect("tva:declaration-detail", pk=declaration.pk)
    else:
        form = LigneTVAForm(instance=ligne)

    return render(request, "tva/ligne_tva_form.html", {
        "form": form,
        "declaration": declaration,
        "ligne": ligne,
    })


@login_required
@require_http_methods(["POST"])
def ligne_tva_delete(request, pk):
    """Supprimer une ligne TVA"""
    ligne = get_object_or_404(LigneTVA, pk=pk, declaration__statut="BROUILLON")
    declaration = ligne.declaration
    ligne.delete()
    declaration.recalculer_totaux()
    messages.success(request, _("Ligne TVA supprimée"))
    return redirect("tva:declaration-detail", pk=declaration.pk)


# ============ CORRECTIONS TVA — CRUD ============


@login_required
def correction_tva_create(request, declaration_pk):
    """Ajouter une correction TVA"""
    declaration = get_object_or_404(DeclarationTVA, pk=declaration_pk, statut="BROUILLON")

    if request.method == "POST":
        form = CorrectionTVAForm(request.POST)
        if form.is_valid():
            correction = form.save(commit=False)
            correction.declaration = declaration
            correction.save()
            declaration.recalculer_totaux()
            messages.success(request, _("Correction TVA ajoutée"))
            return redirect("tva:declaration-detail", pk=declaration.pk)
    else:
        form = CorrectionTVAForm()

    return render(request, "tva/correction_form.html", {
        "form": form,
        "declaration": declaration,
    })


@login_required
@require_http_methods(["POST"])
def correction_tva_delete(request, pk):
    """Supprimer une correction TVA"""
    correction = get_object_or_404(CorrectionTVA, pk=pk, declaration__statut="BROUILLON")
    declaration = correction.declaration
    correction.delete()
    declaration.recalculer_totaux()
    messages.success(request, _("Correction TVA supprimée"))
    return redirect("tva:declaration-detail", pk=declaration.pk)


# ============ OPÉRATIONS TVA — ÉDITION / SUPPRESSION ============


class OperationTVAUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'une opération TVA (non intégrée uniquement)"""

    model = OperationTVA
    form_class = OperationTVAForm
    template_name = "tva/operation_form.html"
    business_permission = 'tva.view_operations'

    def get_queryset(self):
        return super().get_queryset().filter(integre_declaration=False)

    def get_success_url(self):
        return reverse_lazy("tva:operation-list")

    def form_valid(self, form):
        messages.success(self.request, _("Opération TVA modifiée avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def operation_tva_delete(request, pk):
    """Supprimer une opération TVA (non intégrée uniquement)"""
    operation = get_object_or_404(OperationTVA, pk=pk, integre_declaration=False)
    operation.delete()
    messages.success(request, _("Opération TVA supprimée"))
    return redirect("tva:operation-list")
