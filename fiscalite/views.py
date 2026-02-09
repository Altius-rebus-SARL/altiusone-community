# fiscalite/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from core.permissions import BusinessPermissionMixin, permission_required_business
from django.db.models import Q, Count, Sum, Avg, F, Max
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import (
    DeclarationFiscale,
    AnnexeFiscale,
    CorrectionFiscale,
    ReportPerte,
    UtilisationPerte,
    TauxImposition,
    ReclamationFiscale,
    OptimisationFiscale,
)
from core.pdf import serve_file
from .forms import (
    DeclarationFiscaleForm,
    AnnexeFiscaleForm,
    CorrectionFiscaleForm,
    ReportPerteForm,
    ReclamationFiscaleForm,
    OptimisationFiscaleForm,
)
from .filters import DeclarationFiscaleFilter, OptimisationFiscaleFilter
from core.models import Mandat, ExerciceComptable


# ============ DÉCLARATIONS FISCALES ============


class DeclarationFiscaleListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des déclarations fiscales"""

    model = DeclarationFiscale
    template_name = "fiscalite/declaration_list.html"
    context_object_name = "declarations"
    paginate_by = 50
    business_permission = 'fiscalite.view_declarations_fiscales'

    def get_queryset(self):
        queryset = DeclarationFiscale.objects.select_related(
            "mandat__client", "exercice_comptable", "valide_par"
        ).prefetch_related("annexes", "corrections")

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager():
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = DeclarationFiscaleFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-annee_fiscale", "-date_creation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "brouillon": queryset.filter(statut="BROUILLON").count(),
            "deposees": queryset.filter(statut="DEPOSEE").count(),
            "acceptees": queryset.filter(statut="ACCEPTE").count(),
            "impot_total_annee": queryset.filter(
                annee_fiscale=datetime.now().year
            ).aggregate(Sum("impot_total"))["impot_total__sum"]
            or 0,
        }

        return context


class DeclarationFiscaleDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une déclaration fiscale"""

    model = DeclarationFiscale
    template_name = "fiscalite/declaration_detail.html"
    context_object_name = "declaration"
    business_permission = 'fiscalite.view_declarations_fiscales'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("mandat__client", "exercice_comptable", "valide_par")
            .prefetch_related(
                "annexes", "corrections", "reclamations", "pertes_utilisees"
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        declaration = self.object

        # Annexes par type
        annexes_par_type = {}
        for annexe in declaration.annexes.all():
            type_annexe = annexe.get_type_annexe_display()
            if type_annexe not in annexes_par_type:
                annexes_par_type[type_annexe] = []
            annexes_par_type[type_annexe].append(annexe)

        context["annexes_par_type"] = annexes_par_type

        # Corrections
        context["corrections"] = declaration.corrections.select_related("compte")

        # Réclamations
        context["reclamations"] = declaration.reclamations.all()

        # Pertes utilisées
        context["pertes_utilisees"] = declaration.pertes_utilisees.select_related(
            "report_perte"
        )

        # Répartition de l'impôt (graphique)
        repartition_impot = {
            "federal": float(declaration.impot_federal),
            "cantonal": float(declaration.impot_cantonal),
            "communal": float(declaration.impot_communal),
        }
        context["repartition_impot"] = json.dumps(repartition_impot)

        return context


class DeclarationFiscaleCreateView(
    LoginRequiredMixin, BusinessPermissionMixin, CreateView
):
    """Création d'une déclaration fiscale"""

    model = DeclarationFiscale
    form_class = DeclarationFiscaleForm
    template_name = "fiscalite/declaration_form.html"
    business_permission = 'fiscalite.add_declaration_fiscale'

    def get_initial(self):
        initial = super().get_initial()

        # Mandat
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            mandat = get_object_or_404(Mandat, pk=mandat_id)
            initial["mandat"] = mandat

            # Exercice comptable
            exercice = mandat.exercices.filter(statut="OUVERT").first()
            if exercice:
                initial["exercice_comptable"] = exercice
                initial["annee_fiscale"] = exercice.annee

        return initial

    def get_success_url(self):
        return reverse_lazy(
            "fiscalite:declaration-detail", kwargs={"pk": self.object.pk}
        )

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Déclaration fiscale créée avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def declaration_valider(request, pk):
    """Valide une déclaration fiscale"""
    declaration = get_object_or_404(DeclarationFiscale, pk=pk, statut="BROUILLON")

    declaration.statut = "A_VALIDER"
    declaration.valide_par = request.user
    declaration.date_validation = datetime.now()
    declaration.save()

    messages.success(request, _("Déclaration validée avec succès"))
    return redirect("fiscalite:declaration-detail", pk=pk)


@login_required
@require_http_methods(["POST"])
def declaration_deposer(request, pk):
    """Marque une déclaration comme déposée"""
    declaration = get_object_or_404(DeclarationFiscale, pk=pk)

    date_depot = request.POST.get("date_depot")

    declaration.statut = "DEPOSEE"
    declaration.date_depot = (
        datetime.strptime(date_depot, "%Y-%m-%d").date()
        if date_depot
        else datetime.now().date()
    )
    declaration.save()

    messages.success(request, _("Déclaration marquée comme déposée"))
    return redirect("fiscalite:declaration-detail", pk=pk)


# ============ ANNEXES FISCALES ============


@login_required
def annexe_create(request, declaration_pk):
    """Crée une annexe fiscale"""
    declaration = get_object_or_404(DeclarationFiscale, pk=declaration_pk)

    if request.method == "POST":
        form = AnnexeFiscaleForm(request.POST, request.FILES)
        if form.is_valid():
            annexe = form.save(commit=False)
            annexe.declaration = declaration

            # Ordre
            dernier_ordre = (
                declaration.annexes.aggregate(Max("ordre"))["ordre__max"] or 0
            )
            annexe.ordre = dernier_ordre + 1

            annexe.save()

            messages.success(request, _("Annexe ajoutée avec succès"))
            return redirect("fiscalite:declaration-detail", pk=declaration.pk)
    else:
        form = AnnexeFiscaleForm()

    return render(
        request,
        "fiscalite/annexe_form.html",
        {"form": form, "declaration": declaration},
    )


# ============ CORRECTIONS FISCALES ============


@login_required
def correction_create(request, declaration_pk):
    """Crée une correction fiscale"""
    declaration = get_object_or_404(DeclarationFiscale, pk=declaration_pk)

    if request.method == "POST":
        form = CorrectionFiscaleForm(request.POST)
        if form.is_valid():
            correction = form.save(commit=False)
            correction.declaration = declaration
            correction.save()

            messages.success(request, _("Correction ajoutée avec succès"))
            return redirect("fiscalite:declaration-detail", pk=declaration.pk)
    else:
        form = CorrectionFiscaleForm()

    return render(
        request,
        "fiscalite/correction_form.html",
        {"form": form, "declaration": declaration},
    )


# ============ REPORTS DE PERTES ============


class ReportPerteListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des reports de pertes"""

    model = ReportPerte
    template_name = "fiscalite/report_perte_list.html"
    context_object_name = "reports"
    business_permission = 'fiscalite.view_declarations_fiscales'

    def get_queryset(self):
        queryset = ReportPerte.objects.select_related("mandat__client")

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager():
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        return queryset.order_by("annee_expiration", "annee_origine")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "actifs": queryset.filter(expire=False).count(),
            "expires": queryset.filter(expire=True).count(),
            "montant_disponible": queryset.filter(expire=False).aggregate(
                Sum("montant_restant")
            )["montant_restant__sum"]
            or 0,
        }

        return context


class ReportPerteDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un report de perte"""

    model = ReportPerte
    template_name = "fiscalite/report_perte_detail.html"
    context_object_name = "report"
    business_permission = 'fiscalite.view_declarations_fiscales'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Utilisations
        context["utilisations"] = self.object.utilisations.select_related(
            "declaration_fiscale"
        ).order_by("-declaration_fiscale__annee_fiscale")

        return context


# ============ RÉCLAMATIONS FISCALES ============


class ReclamationFiscaleListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des réclamations fiscales"""

    model = ReclamationFiscale
    template_name = "fiscalite/reclamation_list.html"
    context_object_name = "reclamations"
    business_permission = 'fiscalite.view_declarations_fiscales'

    def get_queryset(self):
        return ReclamationFiscale.objects.select_related(
            "declaration__mandat__client"
        ).order_by("-date_reclamation")


@login_required
def reclamation_create(request, declaration_pk):
    """Crée une réclamation fiscale"""
    declaration = get_object_or_404(DeclarationFiscale, pk=declaration_pk)

    if request.method == "POST":
        form = ReclamationFiscaleForm(request.POST, request.FILES)
        if form.is_valid():
            reclamation = form.save(commit=False)
            reclamation.declaration = declaration
            reclamation.save()

            messages.success(request, _("Réclamation créée avec succès"))
            return redirect("fiscalite:declaration-detail", pk=declaration.pk)
    else:
        form = ReclamationFiscaleForm()

    return render(
        request,
        "fiscalite/reclamation_form.html",
        {"form": form, "declaration": declaration},
    )


# ============ OPTIMISATIONS FISCALES ============


class OptimisationFiscaleListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des optimisations fiscales"""

    model = OptimisationFiscale
    template_name = "fiscalite/optimisation_list.html"
    context_object_name = "optimisations"
    paginate_by = 50
    business_permission = 'fiscalite.view_declarations_fiscales'

    def get_queryset(self):
        queryset = OptimisationFiscale.objects.select_related("mandat__client")

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager():
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = OptimisationFiscaleFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-economie_estimee")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "identifiees": queryset.filter(statut="IDENTIFIEE").count(),
            "en_cours": queryset.filter(statut="EN_COURS").count(),
            "realisees": queryset.filter(statut="REALISEE").count(),
            "economie_potentielle": queryset.filter(
                statut__in=["IDENTIFIEE", "EN_ANALYSE", "VALIDEE", "EN_COURS"]
            ).aggregate(Sum("economie_estimee"))["economie_estimee__sum"]
            or 0,
            "economie_realisee": queryset.filter(statut="REALISEE").aggregate(
                Sum("economie_reelle")
            )["economie_reelle__sum"]
            or 0,
        }

        return context


class OptimisationFiscaleDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une optimisation fiscale"""

    model = OptimisationFiscale
    template_name = "fiscalite/optimisation_detail.html"
    context_object_name = "optimisation"
    business_permission = 'fiscalite.view_declarations_fiscales'


class OptimisationFiscaleCreateView(
    LoginRequiredMixin, BusinessPermissionMixin, CreateView
):
    """Création d'une opportunité d'optimisation fiscale"""

    model = OptimisationFiscale
    form_class = OptimisationFiscaleForm
    template_name = "fiscalite/optimisation_form.html"
    business_permission = 'fiscalite.optimisation_fiscale'
    success_url = reverse_lazy("fiscalite:optimisation-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Optimisation fiscale créée avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def optimisation_changer_statut(request, pk):
    """Change le statut d'une optimisation fiscale"""
    optimisation = get_object_or_404(OptimisationFiscale, pk=pk)

    nouveau_statut = request.POST.get("statut")

    if nouveau_statut in dict(OptimisationFiscale.STATUT_CHOICES):
        optimisation.statut = nouveau_statut

        if nouveau_statut == "REALISEE":
            optimisation.date_realisation = datetime.now().date()

            # Demander l'économie réelle
            economie_reelle = request.POST.get("economie_reelle")
            if economie_reelle:
                optimisation.economie_reelle = Decimal(economie_reelle)

        optimisation.save()

        messages.success(request, _("Statut mis à jour"))

    return redirect("fiscalite:optimisation-detail", pk=pk)


# ============ TAUX D'IMPOSITION ============


class TauxImpositionListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des taux d'imposition"""

    model = TauxImposition
    template_name = "fiscalite/taux_imposition_list.html"
    context_object_name = "taux"
    business_permission = 'fiscalite.view_declarations_fiscales'

    def get_queryset(self):
        return TauxImposition.objects.filter(actif=True).order_by(
            "canton", "commune", "-annee"
        )


# ============ RAPPORTS FISCAUX ============


@login_required
def rapport_fiscal_annuel(request, mandat_pk):
    """Génère un rapport fiscal annuel pour un mandat"""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)

    annee = request.GET.get("annee", datetime.now().year)

    # Déclarations de l'année
    declarations = DeclarationFiscale.objects.filter(mandat=mandat, annee_fiscale=annee)

    # Optimisations
    optimisations = OptimisationFiscale.objects.filter(
        mandat=mandat, annee_application=annee
    )

    # Reports de pertes disponibles
    reports_pertes = ReportPerte.objects.filter(mandat=mandat, expire=False)

    context = {
        "mandat": mandat,
        "annee": annee,
        "declarations": declarations,
        "optimisations": optimisations,
        "reports_pertes": reports_pertes,
    }

    return render(request, "fiscalite/rapport_annuel.html", context)


# ============ TÉLÉCHARGEMENT FICHIERS ============


@login_required
def declaration_telecharger_fichier(request, pk):
    """Télécharge le fichier de déclaration fiscale."""
    declaration = get_object_or_404(DeclarationFiscale, pk=pk)
    filename = f"declaration_fiscale_{declaration.annee_fiscale}.pdf"
    return serve_file(
        request, declaration, 'fichier_declaration', filename,
        ("fiscalite:declaration-detail", pk),
    )


@login_required
def declaration_telecharger_taxation(request, pk):
    """Télécharge le fichier de taxation."""
    declaration = get_object_or_404(DeclarationFiscale, pk=pk)
    filename = f"taxation_{declaration.annee_fiscale}.pdf"
    return serve_file(
        request, declaration, 'fichier_taxation', filename,
        ("fiscalite:declaration-detail", pk),
    )


@login_required
def declaration_preview_fichier(request, pk):
    """Aperçu inline du fichier de déclaration fiscale."""
    from core.pdf import serve_pdf

    declaration = get_object_or_404(DeclarationFiscale, pk=pk)
    filename = f"declaration_fiscale_{declaration.annee_fiscale}.pdf"
    return serve_pdf(
        request, declaration, 'fichier_declaration', filename,
        ("fiscalite:declaration-detail", pk),
        generate=False, inline=True,
    )


@login_required
def annexe_telecharger(request, pk):
    """Télécharge le fichier d'une annexe fiscale."""
    annexe = get_object_or_404(AnnexeFiscale, pk=pk)
    ext = annexe.fichier.name.rsplit('.', 1)[-1] if annexe.fichier else 'pdf'
    filename = f"annexe_{annexe.type_annexe}_{annexe.pk}.{ext}"
    return serve_file(
        request, annexe, 'fichier', filename,
        ("fiscalite:declaration-detail", annexe.declaration_id),
    )
