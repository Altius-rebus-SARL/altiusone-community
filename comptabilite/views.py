# comptabilite/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from core.permissions import BusinessPermissionMixin, permission_required_business
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django_filters.views import FilterView
from django.db.models import Q, Count, Sum, Avg, F, Max, Min, Prefetch
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.paginator import Paginator
import json
import csv
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from .models import (
    TypePlanComptable,
    ClasseComptable,
    PlanComptable,
    Compte,
    Journal,
    EcritureComptable,
    PieceComptable,
    Lettrage,
)
from .forms import (
    PlanComptableForm,
    CompteForm,
    JournalForm,
    EcritureComptableForm,
    PieceComptableForm,
    LettrageForm,
)
from .filters import (
    CompteFilter,
    EcritureComptableFilter,
    PieceComptableFilter,
    PlanComptableFilter,
)
from core.models import Mandat, ExerciceComptable


# ============================================================================
# TYPES DE PLANS COMPTABLES (PME, OHADA, Swiss GAAP, etc.)
# ============================================================================


class TypePlanComptableListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """
    Liste des types de plans comptables disponibles.

    Page principale qui affiche les différents standards comptables:
    - PME Suisse
    - OHADA (Afrique)
    - Swiss GAAP RPC
    - etc.
    """

    model = TypePlanComptable
    template_name = "comptabilite/type_plan_list.html"
    context_object_name = "types_plans"
    business_permission = 'comptabilite.view_plan_comptable'

    def get_queryset(self):
        return TypePlanComptable.objects.filter(is_active=True).annotate(
            nb_classes=Count('classes'),
            nb_plans=Count('plans'),
            nb_plans_templates=Count('plans', filter=Q(plans__is_template=True)),
        ).order_by('ordre', 'code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'total_types': TypePlanComptable.objects.filter(is_active=True).count(),
            'total_plans': PlanComptable.objects.count(),
            'total_templates': PlanComptable.objects.filter(is_template=True).count(),
        }
        return context


class TypePlanComptableDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """
    Détail d'un type de plan comptable.

    Affiche:
    - Les classes comptables du standard
    - Les plans comptables utilisant ce type
    - Les templates disponibles
    """

    model = TypePlanComptable
    template_name = "comptabilite/type_plan_detail.html"
    context_object_name = "type_plan"
    business_permission = 'comptabilite.view_plan_comptable'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        type_plan = self.object

        # Classes comptables de ce type
        context['classes'] = type_plan.classes.order_by('numero')

        # Plans utilisant ce type
        context['plans'] = type_plan.plans.select_related('mandat').annotate(
            nb_comptes=Count('comptes')
        ).order_by('-is_template', '-created_at')

        # Templates disponibles
        context['templates'] = type_plan.plans.filter(is_template=True).annotate(
            nb_comptes=Count('comptes')
        )

        # Stats
        context['stats'] = {
            'nb_classes': type_plan.classes.count(),
            'nb_plans': type_plan.plans.count(),
            'nb_templates': type_plan.plans.filter(is_template=True).count(),
            'nb_mandats': type_plan.plans.filter(is_template=False).count(),
        }

        return context


class ClasseComptableListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """
    Liste des classes comptables pour un type de plan.
    """

    model = ClasseComptable
    template_name = "comptabilite/classe_list.html"
    context_object_name = "classes"
    business_permission = 'comptabilite.view_plan_comptable'

    def get_queryset(self):
        type_pk = self.kwargs.get('pk')
        return ClasseComptable.objects.filter(
            type_plan_id=type_pk,
            is_active=True
        ).annotate(
            nb_comptes=Count('comptes')
        ).order_by('numero')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        type_pk = self.kwargs.get('pk')
        context['type_plan'] = get_object_or_404(TypePlanComptable, pk=type_pk)
        return context


# ============================================================================
# PLANS COMPTABLES (instances pour mandats)
# ============================================================================


from .filters import PlanComptableFilter


class PlanComptableListView(LoginRequiredMixin, BusinessPermissionMixin, FilterView):
    """Liste des plans comptables"""

    model = PlanComptable
    template_name = "comptabilite/plan_list.html"
    context_object_name = "plans"
    paginate_by = 25
    filterset_class = PlanComptableFilter
    business_permission = 'comptabilite.view_plan_comptable'

    def get_queryset(self):
        queryset = PlanComptable.objects.select_related("mandat", "type_plan").annotate(
            nb_comptes=Count("comptes")
        )

        # Filtrer par type si spécifié dans l'URL
        type_pk = self.kwargs.get('type_pk')
        if type_pk:
            queryset = queryset.filter(type_plan_id=type_pk)

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_qs = (
            self.filterset.qs if hasattr(self, "filterset") else self.get_queryset()
        )

        context["stats"] = {
            "total": filtered_qs.count(),
            "templates": filtered_qs.filter(is_template=True).count(),
            "instances": filtered_qs.filter(is_template=False).count(),
        }

        # Ajouter le type de plan si filtré
        type_pk = self.kwargs.get('type_pk')
        if type_pk:
            context['type_plan'] = get_object_or_404(TypePlanComptable, pk=type_pk)

        # Liste des types pour le filtre
        context['types_plans'] = TypePlanComptable.objects.filter(
            is_active=True
        ).order_by('ordre')

        return context
    



class PlanComptableDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un plan comptable avec tous ses comptes"""

    model = PlanComptable
    template_name = "comptabilite/plan_detail.html"
    context_object_name = "plan"
    paginate_by = 50
    business_permission = 'comptabilite.view_plan_comptable'

    def get_queryset(self):
        return super().get_queryset().select_related("mandat")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.object

        # Récupérer tous les comptes du plan
        comptes_qs = plan.comptes.select_related("compte_parent").order_by("numero")

        # Recherche
        search = self.request.GET.get("q")
        if search:
            comptes_qs = comptes_qs.filter(
                Q(numero__icontains=search) | Q(libelle__icontains=search)
            )

        # Filtrer par classe si spécifié
        classe = self.request.GET.get("classe")
        if classe:
            comptes_qs = comptes_qs.filter(classe=classe)

        paginator = Paginator(comptes_qs, self.paginate_by)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        context["comptes"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["page_obj"] = page_obj

        # Classes disponibles pour le filtre
        context["classes_disponibles"] = (
            plan.comptes.values_list("classe", flat=True).distinct().order_by("classe")
        )

        # Statistiques
        context["stats"] = {
            "total_comptes": plan.comptes.count(),
            "comptes_imputables": plan.comptes.filter(imputable=True).count(),
            "comptes_collectifs": plan.comptes.filter(est_collectif=True).count(),
            "comptes_lettrables": plan.comptes.filter(lettrable=True).count(),
        }

        return context

    

class PlanComptableCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un nouveau plan comptable"""

    model = PlanComptable
    form_class = PlanComptableForm
    template_name = "comptabilite/plan_form.html"
    business_permission = 'comptabilite.view_plan_comptable'

    def get_success_url(self):
        return reverse_lazy("comptabilite:plan-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Plan comptable créé avec succès"))
        return super().form_valid(form)



class PlanComptableUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un plan comptable"""

    model = PlanComptable
    form_class = PlanComptableForm
    template_name = "comptabilite/plan_form.html"
    business_permission = 'comptabilite.view_plan_comptable'

    def get_success_url(self):
        return reverse_lazy("comptabilite:plan-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Plan comptable modifié avec succès"))
        return super().form_valid(form)
    
# ============ COMPTES ============


class CompteListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des comptes avec filtres avancés"""

    model = Compte
    template_name = "comptabilite/compte_list.html"
    context_object_name = "comptes"
    paginate_by = 50
    business_permission = 'comptabilite.view_plan_comptable'

    def get_queryset(self):
        # Récupérer le plan comptable depuis l'URL ou les paramètres
        plan_id = self.kwargs.get("plan_pk") or self.request.GET.get("plan")

        queryset = Compte.objects.select_related(
            "plan_comptable", "compte_parent"
        ).annotate(nb_ecritures=Count("ecritures"))

        if plan_id:
            queryset = queryset.filter(plan_comptable_id=plan_id)

        # Appliquer les filtres
        self.filterset = CompteFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("numero")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Plans comptables disponibles
        context["plans"] = PlanComptable.objects.filter(is_template=False)

        # Statistiques
        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "imputables": queryset.filter(imputable=True).count(),
            "lettrables": queryset.filter(lettrable=True).count(),
            "solde_total_debit": queryset.aggregate(Sum("solde_debit"))[
                "solde_debit__sum"
            ]
            or 0,
            "solde_total_credit": queryset.aggregate(Sum("solde_credit"))[
                "solde_credit__sum"
            ]
            or 0,
        }

        # URLs d'export
        context["compte_export_csv_url"] = reverse_lazy("comptabilite:compte-export-csv")
        context["compte_export_excel_url"] = reverse_lazy("comptabilite:compte-export-excel")

        return context


class CompteDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un compte avec historique des écritures"""

    model = Compte
    template_name = "comptabilite/compte_detail.html"
    context_object_name = "compte"
    business_permission = 'comptabilite.view_plan_comptable'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("plan_comptable__mandat", "compte_parent")
            .prefetch_related("sous_comptes")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        compte = self.object

        # Période à afficher (par défaut: exercice en cours)
        exercice_id = self.request.GET.get("exercice")
        exercice = None
        
        if exercice_id:
            exercice = get_object_or_404(ExerciceComptable, pk=exercice_id)
        else:
            # Vérifier si le plan a un mandat
            if compte.plan_comptable.mandat:
                exercice = compte.plan_comptable.mandat.exercices.filter(
                    statut="OUVERT"
                ).first()

        # Écritures
        ecritures_qs = compte.ecritures.select_related("journal", "exercice").order_by(
            "-date_ecriture", "numero_piece", "numero_ligne"
        )

        if exercice:
            ecritures_qs = ecritures_qs.filter(exercice=exercice)
            context["exercice"] = exercice

        context["ecritures"] = ecritures_qs[:100]

        # Sous-comptes
        context["sous_comptes"] = compte.sous_comptes.all()

        # Statistiques de l'exercice
        if exercice:
            context["stats_exercice"] = {
                "nb_ecritures": ecritures_qs.count(),
                "total_debit": ecritures_qs.aggregate(Sum("montant_debit"))["montant_debit__sum"] or 0,
                "total_credit": ecritures_qs.aggregate(Sum("montant_credit"))["montant_credit__sum"] or 0,
            }

        # Exercices disponibles (seulement si mandat existe)
        if compte.plan_comptable.mandat:
            context["exercices"] = compte.plan_comptable.mandat.exercices.all()

        return context


class CompteCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un nouveau compte"""

    model = Compte
    form_class = CompteForm
    template_name = "comptabilite/compte_form.html"
    business_permission = 'comptabilite.view_plan_comptable'

    def get_initial(self):
        initial = super().get_initial()
        plan_pk = self.kwargs.get("plan_pk")
        if plan_pk:
            initial["plan_comptable"] = get_object_or_404(PlanComptable, pk=plan_pk)
        return initial

    def get_success_url(self):
        return reverse_lazy("comptabilite:compte-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Compte créé avec succès"))
        return super().form_valid(form)


class CompteUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un compte"""

    model = Compte
    form_class = CompteForm
    template_name = "comptabilite/compte_form.html"
    business_permission = 'comptabilite.view_plan_comptable'

    def get_success_url(self):
        return reverse_lazy("comptabilite:compte-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Compte modifié avec succès"))
        return super().form_valid(form)


# ============ JOURNAUX ============


class JournalListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des journaux"""

    model = Journal
    template_name = "comptabilite/journal_list.html"
    context_object_name = "journaux"
    business_permission = 'comptabilite.view_ecritures'

    def get_queryset(self):
        queryset = Journal.objects.select_related("mandat").annotate(
            nb_ecritures=Count("ecriturecomptable")
        )

        # Filtrer selon mandat
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            queryset = queryset.filter(mandat_id=mandat_id)

        return queryset.order_by("code")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mandats disponibles
        user = self.request.user
        if user.is_manager():
            context["mandats"] = Mandat.objects.filter(statut="ACTIF")
        else:
            context["mandats"] = Mandat.objects.filter(
                Q(responsable=user) | Q(equipe=user), statut="ACTIF"
            ).distinct()

        return context


class JournalDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un journal avec ses écritures"""

    model = Journal
    template_name = "comptabilite/journal_detail.html"
    context_object_name = "journal"
    business_permission = 'comptabilite.view_ecritures'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        journal = self.object

        # Période
        date_debut = self.request.GET.get("date_debut")
        date_fin = self.request.GET.get("date_fin")

        ecritures_qs = journal.ecriturecomptable_set.select_related(
            "compte", "exercice"
        ).order_by("-date_ecriture", "numero_piece", "numero_ligne")

        if date_debut:
            ecritures_qs = ecritures_qs.filter(date_ecriture__gte=date_debut)
        if date_fin:
            ecritures_qs = ecritures_qs.filter(date_ecriture__lte=date_fin)

        context["ecritures"] = ecritures_qs[:200]

        # Statistiques
        context["stats"] = {
            "nb_ecritures": ecritures_qs.count(),
            "total_debit": ecritures_qs.aggregate(Sum("montant_debit"))[
                "montant_debit__sum"
            ]
            or 0,
            "total_credit": ecritures_qs.aggregate(Sum("montant_credit"))[
                "montant_credit__sum"
            ]
            or 0,
            "pieces_non_equilibrees": PieceComptable.objects.filter(
                journal=journal, equilibree=False
            ).count(),
        }

        return context


class JournalCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un nouveau journal"""

    model = Journal
    form_class = JournalForm
    template_name = "comptabilite/journal_form.html"
    business_permission = 'comptabilite.add_journal'

    def get_success_url(self):
        return reverse_lazy(
            "comptabilite:journal-detail", kwargs={"pk": self.object.pk}
        )

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Journal créé avec succès"))
        return super().form_valid(form)


class JournalUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un journal"""

    model = Journal
    form_class = JournalForm
    template_name = "comptabilite/journal_form.html"
    business_permission = 'comptabilite.view_ecritures'

    def get_success_url(self):
        return reverse_lazy(
            "comptabilite:journal-detail", kwargs={"pk": self.object.pk}
        )

    def form_valid(self, form):
        messages.success(self.request, _("Journal modifié avec succès"))
        return super().form_valid(form)

# ============ ÉCRITURES COMPTABLES ============


class EcritureComptableListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des écritures comptables"""

    model = EcritureComptable
    template_name = "comptabilite/ecriture_list.html"
    context_object_name = "ecritures"
    paginate_by = 100
    business_permission = 'comptabilite.view_ecritures'

    def get_queryset(self):
        queryset = EcritureComptable.objects.select_related(
            "mandat", "exercice", "journal", "compte"
        )

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager() and not user.is_superuser:
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = EcritureComptableFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by(
            "-date_ecriture", "numero_piece", "numero_ligne"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "total_debit": queryset.aggregate(Sum("montant_debit"))[
                "montant_debit__sum"
            ]
            or 0,
            "total_credit": queryset.aggregate(Sum("montant_credit"))[
                "montant_credit__sum"
            ]
            or 0,
            "brouillon": queryset.filter(statut="BROUILLON").count(),
            "valide": queryset.filter(statut="VALIDE").count(),
        }

        return context


class EcritureComptableDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une écriture comptable"""

    model = EcritureComptable
    template_name = "comptabilite/ecriture_detail.html"
    context_object_name = "ecriture"
    business_permission = 'comptabilite.view_ecritures'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "mandat__client",
                "exercice",
                "journal",
                "compte",
                "piece_justificative",
                "valide_par",
                "created_by",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ecriture = self.object

        # Autres écritures de la même pièce
        context["ecritures_piece"] = (
            EcritureComptable.objects.filter(
                numero_piece=ecriture.numero_piece, journal=ecriture.journal
            )
            .exclude(pk=ecriture.pk)
            .select_related("compte")
        )

        # Vérifier l'équilibre de la pièce
        piece = PieceComptable.objects.filter(
            numero_piece=ecriture.numero_piece
        ).first()
        context["piece"] = piece

        return context


class EcritureComptableCreateView(
    LoginRequiredMixin, BusinessPermissionMixin, CreateView
):
    """Création d'une nouvelle écriture comptable"""

    model = EcritureComptable
    form_class = EcritureComptableForm
    template_name = "comptabilite/ecriture_form.html"
    business_permission = 'comptabilite.add_ecriture'

    def _get_mandat(self):
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            return get_object_or_404(Mandat, pk=mandat_id)
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['mandat'] = self._get_mandat()
        return kwargs

    def get_initial(self):
        initial = super().get_initial()

        mandat = self._get_mandat()
        if mandat:
            initial["mandat"] = mandat
            initial["exercice"] = mandat.exercices.filter(statut="OUVERT").first()

        initial["date_ecriture"] = datetime.now().date()

        return initial

    def get_success_url(self):
        return reverse_lazy(
            "comptabilite:ecriture-detail", kwargs={"pk": self.object.pk}
        )

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Écriture créée avec succès"))
        return super().form_valid(form)


class EcritureComptableUpdateView(
    LoginRequiredMixin, BusinessPermissionMixin, UpdateView
):
    """Modification d'une écriture comptable"""

    model = EcritureComptable
    form_class = EcritureComptableForm
    template_name = "comptabilite/ecriture_form.html"
    business_permission = 'comptabilite.view_ecritures'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['mandat'] = self.object.mandat if self.object else None
        return kwargs

    def get_queryset(self):
        # Ne peut modifier que les écritures en brouillon
        return super().get_queryset().filter(statut="BROUILLON")

    def get_success_url(self):
        return reverse_lazy(
            "comptabilite:ecriture-detail", kwargs={"pk": self.object.pk}
        )

    def form_valid(self, form):
        messages.success(self.request, _("Écriture modifiée avec succès"))
        return super().form_valid(form)


# ============ PIÈCES COMPTABLES ============


class PieceComptableListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des pièces comptables"""

    model = PieceComptable
    template_name = "comptabilite/piece_list.html"
    context_object_name = "pieces"
    paginate_by = 50
    business_permission = 'comptabilite.view_ecritures'

    def get_queryset(self):
        queryset = PieceComptable.objects.select_related("mandat", "journal").annotate(
            nb_ecritures=Count(
                "mandat__ecritures",
                filter=Q(mandat__ecritures__numero_piece=F("numero_piece")),
            )
        )

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager():
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = PieceComptableFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-date_piece", "numero_piece")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "equilibrees": queryset.filter(equilibree=True).count(),
            "non_equilibrees": queryset.filter(equilibree=False).count(),
            "brouillon": queryset.filter(statut="BROUILLON").count(),
        }

        return context


class PieceComptableDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une pièce comptable"""

    model = PieceComptable
    template_name = "comptabilite/piece_detail.html"
    context_object_name = "piece"
    business_permission = 'comptabilite.view_ecritures'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        piece = self.object

        # Toutes les écritures de la pièce
        context["ecritures"] = (
            EcritureComptable.objects.filter(
                numero_piece=piece.numero_piece, mandat=piece.mandat
            )
            .select_related("compte")
            .order_by("numero_ligne")
        )

        # Recalculer l'équilibre
        piece.calculer_equilibre()

        # Documents justificatifs
        context["documents"] = piece.documents_justificatifs.all()

        return context


class PieceComptableCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'une pièce comptable avec upload de documents"""

    model = PieceComptable
    form_class = PieceComptableForm
    template_name = "comptabilite/piece_form.html"
    business_permission = 'comptabilite.add_ecritures'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        # Passer le mandat initial pour le filtrage des journaux/dossiers
        mandat_id = self.request.GET.get('mandat')
        if mandat_id:
            try:
                kwargs['mandat'] = Mandat.objects.get(pk=mandat_id)
            except Mandat.DoesNotExist:
                pass
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        from datetime import date
        initial['date_piece'] = date.today()
        # Pré-sélectionner le mandat si fourni en paramètre
        mandat_id = self.request.GET.get('mandat')
        if mandat_id:
            initial['mandat'] = mandat_id
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Nouvelle pièce comptable")
        context['submit_text'] = _("Créer la pièce")
        return context

    def form_valid(self, form):
        from django.contrib import messages
        from documents.models import Document
        from documents.storage import storage_service

        # Sauvegarder la pièce
        piece = form.save(commit=False)
        piece.created_by = self.request.user
        piece.save()
        form.save_m2m()
        self.object = piece  # Nécessaire pour get_success_url()

        # Traiter les fichiers uploadés
        fichiers = self.request.FILES.getlist('fichiers')
        documents_crees = []

        for fichier in fichiers:
            try:
                import hashlib
                import os

                # Calculer le hash du fichier
                fichier.seek(0)
                file_content = fichier.read()
                file_hash = hashlib.sha256(file_content).hexdigest()
                fichier.seek(0)

                # Extension
                _, ext = os.path.splitext(fichier.name)

                # Créer le document
                document = Document(
                    mandat=piece.mandat,
                    dossier=piece.dossier,
                    nom_fichier=fichier.name,
                    nom_original=fichier.name,
                    extension=ext.lower(),
                    mime_type=fichier.content_type,
                    taille=fichier.size,
                    hash_fichier=file_hash,
                    statut_traitement='UPLOAD',
                    created_by=self.request.user,
                )

                # Sauvegarder le document puis le fichier
                document.save()
                document.fichier.save(fichier.name, fichier, save=True)
                documents_crees.append(document)

                # Lancer le traitement OCR en arrière-plan
                from documents.tasks import traiter_document_ocr
                traiter_document_ocr.delay(str(document.id))

            except Exception as e:
                messages.warning(
                    self.request,
                    _("Erreur lors de l'upload de %(filename)s: %(error)s") % {
                        'filename': fichier.name,
                        'error': str(e)
                    }
                )

        # Associer les documents à la pièce
        if documents_crees:
            piece.documents_justificatifs.add(*documents_crees)
            messages.success(
                self.request,
                _("%(count)d document(s) ajouté(s) à la pièce") % {
                    'count': len(documents_crees)
                }
            )

        messages.success(
            self.request,
            _("Pièce comptable %(numero)s créée avec succès") % {
                'numero': piece.numero_piece
            }
        )

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('comptabilite:piece-detail', kwargs={'pk': self.object.pk})


class PieceComptableUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'une pièce comptable"""

    model = PieceComptable
    form_class = PieceComptableForm
    template_name = "comptabilite/piece_form.html"
    context_object_name = "piece"
    business_permission = 'comptabilite.change_ecritures'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Modifier la pièce %(numero)s") % {
            'numero': self.object.numero_piece
        }
        context['submit_text'] = _("Enregistrer les modifications")
        context['documents'] = self.object.documents_justificatifs.all()
        return context

    def form_valid(self, form):
        from django.contrib import messages
        from documents.models import Document
        from documents.storage import storage_service

        piece = form.save()

        # Traiter les nouveaux fichiers uploadés
        fichiers = self.request.FILES.getlist('fichiers')
        documents_crees = []

        for fichier in fichiers:
            try:
                import hashlib
                import os

                # Calculer le hash du fichier
                fichier.seek(0)
                file_content = fichier.read()
                file_hash = hashlib.sha256(file_content).hexdigest()
                fichier.seek(0)

                # Extension
                _, ext = os.path.splitext(fichier.name)

                document = Document(
                    mandat=piece.mandat,
                    dossier=piece.dossier,
                    nom_fichier=fichier.name,
                    nom_original=fichier.name,
                    extension=ext.lower(),
                    mime_type=fichier.content_type,
                    taille=fichier.size,
                    hash_fichier=file_hash,
                    statut_traitement='UPLOAD',
                    created_by=self.request.user,
                )

                # Sauvegarder le document puis le fichier
                document.save()
                document.fichier.save(fichier.name, fichier, save=True)
                documents_crees.append(document)

                from documents.tasks import traiter_document_ocr
                traiter_document_ocr.delay(str(document.id))

            except Exception as e:
                messages.warning(
                    self.request,
                    _("Erreur lors de l'upload de %(filename)s: %(error)s") % {
                        'filename': fichier.name,
                        'error': str(e)
                    }
                )

        if documents_crees:
            piece.documents_justificatifs.add(*documents_crees)
            messages.success(
                self.request,
                _("%(count)d document(s) ajouté(s)") % {'count': len(documents_crees)}
            )

        messages.success(self.request, _("Pièce comptable mise à jour"))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('comptabilite:piece-detail', kwargs={'pk': self.object.pk})


@login_required
def piece_ajouter_document(request, pk):
    """Ajouter un document justificatif à une pièce existante (AJAX)"""
    from django.http import JsonResponse
    from documents.models import Document
    import hashlib
    import os

    piece = get_object_or_404(PieceComptable, pk=pk)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    fichier = request.FILES.get('fichier')
    if not fichier:
        return JsonResponse({'error': 'No file provided'}, status=400)

    try:
        # Calculer le hash du fichier
        fichier.seek(0)
        file_content = fichier.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        fichier.seek(0)

        # Extension
        _, ext = os.path.splitext(fichier.name)

        document = Document(
            mandat=piece.mandat,
            dossier=piece.dossier,
            nom_fichier=fichier.name,
            nom_original=fichier.name,
            extension=ext.lower(),
            mime_type=fichier.content_type,
            taille=fichier.size,
            hash_fichier=file_hash,
            statut_traitement='UPLOAD',
            created_by=request.user,
        )

        # Sauvegarder le document puis le fichier
        document.save()
        document.fichier.save(fichier.name, fichier, save=True)
        piece.documents_justificatifs.add(document)

        # Lancer OCR
        from documents.tasks import traiter_document_ocr
        traiter_document_ocr.delay(str(document.id))

        return JsonResponse({
            'success': True,
            'document': {
                'id': str(document.id),
                'nom': document.nom_fichier,
                'type': document.mime_type,
                'taille': document.taille,
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def piece_extraire_ocr(request, pk):
    """Extrait les informations OCR et pré-remplit les champs de la pièce"""
    from django.http import JsonResponse

    piece = get_object_or_404(PieceComptable, pk=pk)

    # Récupérer le premier document avec métadonnées OCR
    document = piece.documents_justificatifs.filter(
        metadata_extraite__isnull=False
    ).exclude(metadata_extraite={}).first()

    if not document:
        return JsonResponse({
            'success': False,
            'message': _("Aucun document avec données OCR disponible")
        })

    metadata = document.metadata_extraite or {}

    # Mapper les champs OCR vers les champs de la pièce
    data = {
        'reference_externe': metadata.get('numero_facture', ''),
        'tiers_nom': metadata.get('fournisseur', '') or metadata.get('client', ''),
        'tiers_numero_tva': metadata.get('numero_tva_fournisseur', '') or metadata.get('numero_tva', ''),
        'montant_ht': metadata.get('montant_ht'),
        'montant_tva': metadata.get('montant_tva'),
        'montant_ttc': metadata.get('montant_ttc'),
        'date_piece': metadata.get('date_facture') or metadata.get('date_document'),
        'libelle': metadata.get('description', ''),
    }

    # Déterminer le type de pièce
    doc_type = document.prediction_type or ''
    type_mapping = {
        'FACTURE_ACHAT': 'FACTURE_ACHAT',
        'FACTURE_VENTE': 'FACTURE_VENTE',
        'RELEVE_BANQUE': 'RELEVE_BANQUE',
        'FICHE_SALAIRE': 'SALAIRE',
        'DEVIS': 'AUTRE',
    }
    data['type_piece'] = type_mapping.get(doc_type, 'AUTRE')

    # Mettre à jour la pièce si demandé
    if request.method == 'POST' and request.POST.get('apply') == 'true':
        for field, value in data.items():
            if value and hasattr(piece, field):
                setattr(piece, field, value)
        piece.metadata_ocr = metadata
        piece.save()
        return JsonResponse({'success': True, 'applied': True, 'data': data})

    return JsonResponse({'success': True, 'data': data})


@login_required
def piece_valider(request, pk):
    """Valide une pièce comptable"""
    from django.contrib import messages

    piece = get_object_or_404(PieceComptable, pk=pk)

    if request.method != 'POST':
        return redirect('comptabilite:piece-detail', pk=pk)

    try:
        piece.valider(request.user)
        messages.success(request, _("Pièce validée avec succès"))
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('comptabilite:piece-detail', pk=pk)


# ============ API AJAX POUR FILTRAGE DYNAMIQUE ============


@login_required
def api_journaux_par_mandat(request, mandat_pk):
    """Retourne les journaux d'un mandat (AJAX)"""
    journaux = Journal.objects.filter(
        mandat_id=mandat_pk,
        is_active=True
    ).order_by('code').values('id', 'code', 'libelle', 'type_journal')

    return JsonResponse({
        'journaux': [
            {
                'id': str(j['id']),
                'code': j['code'],
                'libelle': j['libelle'],
                'display': f"{j['code']} - {j['libelle']}"
            }
            for j in journaux
        ]
    })


@login_required
def api_dossiers_par_mandat(request, mandat_pk):
    """Retourne les dossiers d'un mandat (AJAX)

    Retourne TOUS les dossiers accessibles pour ce mandat:
    - Dossiers directement liés au mandat (mandat=mandat_pk)
    - Dossiers liés au client du mandat (client=mandat.client_id)
    """
    from documents.models import Dossier
    from django.db.models import Q

    # Récupérer le mandat pour avoir accès au client
    mandat = get_object_or_404(Mandat, pk=mandat_pk)

    # Dossiers liés au mandat OU au client du mandat
    dossiers = Dossier.objects.filter(
        Q(mandat=mandat) | Q(client=mandat.client),
        is_active=True
    ).select_related('parent', 'mandat', 'mandat__client', 'client').order_by('chemin_complet')

    return JsonResponse({
        'dossiers': [
            {
                'id': str(d.id),
                'nom': d.nom,
                'chemin': d.chemin_complet,
                # Affichage avec contexte pour éviter confusion entre dossiers homonymes
                'display': d.get_path_display(include_context=True)
            }
            for d in dossiers
        ]
    })


@login_required
def api_types_pieces(request):
    """Retourne les types de pièces comptables (AJAX)"""
    from .models import TypePieceComptable

    types = TypePieceComptable.objects.filter(
        is_active=True
    ).order_by('ordre', 'code').values(
        'id', 'code', 'libelle', 'categorie', 'prefixe_numero'
    )

    return JsonResponse({
        'types': [
            {
                'id': str(t['id']),
                'code': t['code'],
                'libelle': t['libelle'],
                'categorie': t['categorie'],
                'prefixe': t['prefixe_numero'],
                'display': f"{t['code']} - {t['libelle']}"
            }
            for t in types
        ]
    })


# ============ LETTRAGE ============


class LettrageListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des lettrages"""

    model = Lettrage
    template_name = "comptabilite/lettrage_list.html"
    context_object_name = "lettrages"
    paginate_by = 50
    business_permission = 'comptabilite.view_ecritures'

    def get_queryset(self):
        return Lettrage.objects.select_related(
            "mandat", "compte", "lettre_par"
        ).order_by("-date_lettrage")


@login_required
def lettrage_compte(request, compte_pk):
    """Interface de lettrage d'un compte"""
    compte = get_object_or_404(Compte, pk=compte_pk, lettrable=True)

    # Écritures non lettrées du compte
    ecritures = EcritureComptable.objects.filter(
        compte=compte, statut="VALIDE", code_lettrage=""
    ).order_by("date_ecriture")

    if request.method == "POST":
        # Traiter le lettrage
        ecriture_ids = request.POST.getlist("ecritures")

        if ecriture_ids:
            ecritures_a_lettrer = EcritureComptable.objects.filter(
                pk__in=ecriture_ids, compte=compte
            )

            # Vérifier l'équilibre
            total_debit = sum(e.montant_debit for e in ecritures_a_lettrer)
            total_credit = sum(e.montant_credit for e in ecritures_a_lettrer)

            if total_debit == total_credit:
                # Générer code de lettrage
                dernier_lettrage = (
                    Lettrage.objects.filter(mandat=compte.plan_comptable.mandat)
                    .order_by("code_lettrage")
                    .last()
                )

                if dernier_lettrage:
                    # Incrémenter
                    last_num = int(dernier_lettrage.code_lettrage[1:])
                    code_lettrage = f"L{last_num + 1:06d}"
                else:
                    code_lettrage = "L000001"

                # Créer le lettrage
                lettrage = Lettrage.objects.create(
                    mandat=compte.plan_comptable.mandat,
                    compte=compte,
                    code_lettrage=code_lettrage,
                    montant_total=total_debit,
                    solde=0,
                    date_lettrage=datetime.now().date(),
                    lettre_par=request.user,
                    complet=True,
                )

                # Appliquer le code aux écritures
                ecritures_a_lettrer.update(
                    code_lettrage=code_lettrage,
                    date_lettrage=datetime.now().date(),
                    statut="LETTRE",
                )

                messages.success(request, _("Lettrage effectué avec succès"))
                return redirect("comptabilite:compte-detail", pk=compte.pk)
            else:
                messages.error(
                    request, _("Les écritures sélectionnées ne sont pas équilibrées")
                )

    context = {
        "compte": compte,
        "ecritures": ecritures,
    }

    return render(request, "comptabilite/lettrage_form.html", context)


# ============ RAPPORTS ============


@login_required
def balance_generale(request, mandat_pk):
    """Balance générale d'un mandat"""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)

    # Exercice
    exercice_id = request.GET.get("exercice")
    if exercice_id:
        exercice = get_object_or_404(ExerciceComptable, pk=exercice_id)
    else:
        exercice = mandat.exercices.filter(statut="OUVERT").first()

    # Plan comptable
    plan = mandat.plans_comptables.first()
    if not plan:
        messages.error(request, _("Aucun plan comptable trouvé pour ce mandat"))
        return redirect("core:mandat-detail", pk=mandat.pk)

    # Récupérer tous les comptes avec leurs soldes
    comptes = Compte.objects.filter(plan_comptable=plan, imputable=True).order_by(
        "numero"
    )

    balance = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for compte in comptes:
        # Soldes de l'exercice
        ecritures = compte.ecritures.filter(
            exercice=exercice, statut__in=["VALIDE", "LETTRE", "CLOTURE"]
        )

        solde_debit = (
            ecritures.aggregate(Sum("montant_debit"))["montant_debit__sum"] or 0
        )
        solde_credit = (
            ecritures.aggregate(Sum("montant_credit"))["montant_credit__sum"] or 0
        )

        if solde_debit != 0 or solde_credit != 0:
            balance.append(
                {
                    "compte": compte,
                    "solde_debit": solde_debit,
                    "solde_credit": solde_credit,
                }
            )

            total_debit += solde_debit
            total_credit += solde_credit

    # Format de sortie
    format_export = request.GET.get("format", "html")

    if format_export == "pdf":
        return generer_balance_pdf(mandat, exercice, balance, total_debit, total_credit)
    elif format_export == "csv":
        return generer_balance_csv(mandat, exercice, balance, total_debit, total_credit)

    context = {
        "mandat": mandat,
        "exercice": exercice,
        "exercices": mandat.exercices.all(),
        "balance": balance,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "equilibre": total_debit == total_credit,
    }

    return render(request, "comptabilite/balance_generale.html", context)


def generer_balance_pdf(mandat, exercice, balance, total_debit, total_credit):
    """Génère un PDF de la balance"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # En-tête
    p.setFont("Helvetica-Bold", 16)
    p.drawString(
        2 * cm, height - 2 * cm, f"Balance générale - {mandat.client.raison_sociale}"
    )

    p.setFont("Helvetica", 12)
    p.drawString(2 * cm, height - 3 * cm, f"Exercice: {exercice.annee}")
    p.drawString(
        2 * cm,
        height - 3.5 * cm,
        f"Période: {exercice.date_debut} au {exercice.date_fin}",
    )

    # Tableau
    y = height - 5 * cm
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2 * cm, y, "Compte")
    p.drawString(8 * cm, y, "Libellé")
    p.drawString(14 * cm, y, "Débit")
    p.drawString(17 * cm, y, "Crédit")

    y -= 0.5 * cm
    p.line(2 * cm, y, 19 * cm, y)
    y -= 0.5 * cm

    p.setFont("Helvetica", 9)
    for item in balance:
        if y < 3 * cm:
            p.showPage()
            y = height - 2 * cm

        p.drawString(2 * cm, y, item["compte"].numero)
        p.drawString(8 * cm, y, item["compte"].libelle[:30])
        p.drawRightString(16 * cm, y, f"{item['solde_debit']:,.2f}")
        p.drawRightString(19 * cm, y, f"{item['solde_credit']:,.2f}")
        y -= 0.5 * cm

    # Totaux
    y -= 0.5 * cm
    p.line(2 * cm, y, 19 * cm, y)
    y -= 0.5 * cm
    p.setFont("Helvetica-Bold", 10)
    p.drawString(8 * cm, y, "TOTAUX")
    p.drawRightString(16 * cm, y, f"{total_debit:,.2f}")
    p.drawRightString(19 * cm, y, f"{total_credit:,.2f}")

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="balance_{mandat.numero}_{exercice.annee}.pdf"'
    )
    return response


def generer_balance_csv(mandat, exercice, balance, total_debit, total_credit):
    """Génère un CSV de la balance"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="balance_{mandat.numero}_{exercice.annee}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(["Compte", "Libellé", "Débit", "Crédit"])

    for item in balance:
        writer.writerow(
            [
                item["compte"].numero,
                item["compte"].libelle,
                f"{item['solde_debit']:.2f}",
                f"{item['solde_credit']:.2f}",
            ]
        )

    writer.writerow(["", "TOTAUX", f"{total_debit:.2f}", f"{total_credit:.2f}"])

    return response


@login_required
def grand_livre(request, compte_pk):
    """Grand livre d'un compte"""
    compte = get_object_or_404(Compte, pk=compte_pk)

    # Période
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    ecritures = (
        compte.ecritures.filter(statut__in=["VALIDE", "LETTRE", "CLOTURE"])
        .select_related("journal")
        .order_by("date_ecriture", "numero_piece")
    )

    if date_debut:
        ecritures = ecritures.filter(date_ecriture__gte=date_debut)
    if date_fin:
        ecritures = ecritures.filter(date_ecriture__lte=date_fin)

    # Calcul des soldes cumulés
    solde_cumule = Decimal("0")
    ecritures_avec_solde = []

    for ecriture in ecritures:
        if compte.type_compte in ["ACTIF", "CHARGE"]:
            solde_cumule += ecriture.montant_debit - ecriture.montant_credit
        else:
            solde_cumule += ecriture.montant_credit - ecriture.montant_debit

        ecritures_avec_solde.append({"ecriture": ecriture, "solde": solde_cumule})

    context = {
        "compte": compte,
        "ecritures_avec_solde": ecritures_avec_solde,
        "date_debut": date_debut,
        "date_fin": date_fin,
    }

    return render(request, "comptabilite/grand_livre.html", context)


# ============ BILAN ============


@login_required
def bilan(request, mandat_pk):
    """Bilan (Actifs vs Passifs) d'un mandat — PME suisse classes 1 et 2"""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)

    exercice_id = request.GET.get("exercice")
    if exercice_id:
        exercice = get_object_or_404(ExerciceComptable, pk=exercice_id)
    else:
        exercice = mandat.exercices.filter(statut="OUVERT").first()

    plan = mandat.plans_comptables.first()
    if not plan:
        messages.error(request, _("Aucun plan comptable trouvé pour ce mandat"))
        return redirect("core:mandat-detail", pk=mandat.pk)

    def _solde_comptes(type_compte):
        comptes = Compte.objects.filter(
            plan_comptable=plan, imputable=True, type_compte=type_compte
        ).order_by("numero")
        items = []
        total = Decimal("0")
        for compte in comptes:
            ecritures = compte.ecritures.filter(
                exercice=exercice, statut__in=["VALIDE", "LETTRE", "CLOTURE"]
            )
            debit = ecritures.aggregate(Sum("montant_debit"))["montant_debit__sum"] or Decimal("0")
            credit = ecritures.aggregate(Sum("montant_credit"))["montant_credit__sum"] or Decimal("0")
            if type_compte == "ACTIF":
                solde = debit - credit
            else:
                solde = credit - debit
            if solde != 0:
                items.append({"compte": compte, "solde": solde})
                total += solde
        return items, total

    actifs, total_actifs = _solde_comptes("ACTIF")
    passifs, total_passifs = _solde_comptes("PASSIF")
    equilibre = total_actifs == total_passifs

    context = {
        "mandat": mandat,
        "exercice": exercice,
        "exercices": mandat.exercices.all(),
        "actifs": actifs,
        "passifs": passifs,
        "total_actifs": total_actifs,
        "total_passifs": total_passifs,
        "equilibre": equilibre,
    }

    return render(request, "comptabilite/bilan.html", context)


# ============ COMPTE DE RÉSULTAT ============


@login_required
def compte_resultat(request, mandat_pk):
    """Compte de résultat (Produits vs Charges) — PME suisse classes 3-8"""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)

    exercice_id = request.GET.get("exercice")
    if exercice_id:
        exercice = get_object_or_404(ExerciceComptable, pk=exercice_id)
    else:
        exercice = mandat.exercices.filter(statut="OUVERT").first()

    plan = mandat.plans_comptables.first()
    if not plan:
        messages.error(request, _("Aucun plan comptable trouvé pour ce mandat"))
        return redirect("core:mandat-detail", pk=mandat.pk)

    def _solde_comptes(type_compte):
        comptes = Compte.objects.filter(
            plan_comptable=plan, imputable=True, type_compte=type_compte
        ).order_by("numero")
        items = []
        total = Decimal("0")
        for compte in comptes:
            ecritures = compte.ecritures.filter(
                exercice=exercice, statut__in=["VALIDE", "LETTRE", "CLOTURE"]
            )
            debit = ecritures.aggregate(Sum("montant_debit"))["montant_debit__sum"] or Decimal("0")
            credit = ecritures.aggregate(Sum("montant_credit"))["montant_credit__sum"] or Decimal("0")
            if type_compte == "CHARGE":
                solde = debit - credit
            else:
                solde = credit - debit
            if solde != 0:
                items.append({"compte": compte, "solde": solde})
                total += solde
        return items, total

    produits, total_produits = _solde_comptes("PRODUIT")
    charges, total_charges = _solde_comptes("CHARGE")
    resultat = total_produits - total_charges

    context = {
        "mandat": mandat,
        "exercice": exercice,
        "exercices": mandat.exercices.all(),
        "produits": produits,
        "charges": charges,
        "total_produits": total_produits,
        "total_charges": total_charges,
        "resultat": resultat,
    }

    return render(request, "comptabilite/compte_resultat.html", context)


# ============ CLÔTURE D'EXERCICE ============


@login_required
def cloture_exercice(request, mandat_pk):
    """Workflow de clôture d'exercice comptable"""
    from django.utils import timezone

    mandat = get_object_or_404(Mandat, pk=mandat_pk)

    exercice_id = request.GET.get("exercice")
    if exercice_id:
        exercice = get_object_or_404(ExerciceComptable, pk=exercice_id)
    else:
        exercice = mandat.exercices.filter(statut="OUVERT").first()

    if not exercice:
        messages.error(request, _("Aucun exercice ouvert trouvé"))
        return redirect("core:mandat-detail", pk=mandat.pk)

    plan = mandat.plans_comptables.first()

    # Vérifications pré-clôture
    ecritures_brouillon = EcritureComptable.objects.filter(
        exercice=exercice, statut="BROUILLON"
    ).count()

    from tva.models import DeclarationTVA
    declarations_non_soumises = DeclarationTVA.objects.filter(
        mandat=mandat,
        periode_debut__gte=exercice.date_debut,
        periode_fin__lte=exercice.date_fin,
    ).exclude(statut="SOUMISE").count()

    pret_a_cloturer = ecritures_brouillon == 0 and declarations_non_soumises == 0

    if request.method == "POST" and request.POST.get("action") == "cloturer":
        if not pret_a_cloturer:
            messages.error(request, _("Impossible de clôturer : vérifiez les conditions préalables"))
            return redirect(request.path + f"?exercice={exercice.pk}")

        # 1. Calculer le résultat (Produits - Charges)
        produits_total = Decimal("0")
        charges_total = Decimal("0")
        comptes_resultat = Compte.objects.filter(
            plan_comptable=plan, imputable=True, type_compte__in=["PRODUIT", "CHARGE"]
        )

        journal_cloture = Journal.objects.filter(plan_comptable=plan).first()
        numero_piece = f"CLO-{exercice.annee}"
        date_cloture = exercice.date_fin

        for compte in comptes_resultat:
            ecritures = compte.ecritures.filter(
                exercice=exercice, statut__in=["VALIDE", "LETTRE", "CLOTURE"]
            )
            debit = ecritures.aggregate(Sum("montant_debit"))["montant_debit__sum"] or Decimal("0")
            credit = ecritures.aggregate(Sum("montant_credit"))["montant_credit__sum"] or Decimal("0")
            solde = debit - credit

            if solde == 0:
                continue

            if compte.type_compte == "PRODUIT":
                produits_total += credit - debit
            else:
                charges_total += debit - credit

            # Écriture de clôture : solder le compte
            EcritureComptable.objects.create(
                mandat=mandat,
                exercice=exercice,
                journal=journal_cloture,
                numero_piece=numero_piece,
                date_ecriture=date_cloture,
                compte=compte,
                libelle=_("Clôture exercice %(annee)s") % {"annee": exercice.annee},
                montant_debit=credit if credit > debit else Decimal("0"),
                montant_credit=debit if debit > credit else Decimal("0"),
                statut="CLOTURE",
            )

        # 2. Écriture de résultat vers compte résultat (2990 ou 2979 PME suisse)
        resultat = produits_total - charges_total
        compte_resultat_obj = Compte.objects.filter(
            plan_comptable=plan, numero__startswith="299", imputable=True
        ).first()

        if compte_resultat_obj and resultat != 0:
            EcritureComptable.objects.create(
                mandat=mandat,
                exercice=exercice,
                journal=journal_cloture,
                numero_piece=numero_piece,
                date_ecriture=date_cloture,
                compte=compte_resultat_obj,
                libelle=_("Résultat exercice %(annee)s") % {"annee": exercice.annee},
                montant_debit=abs(resultat) if resultat < 0 else Decimal("0"),
                montant_credit=resultat if resultat > 0 else Decimal("0"),
                statut="CLOTURE",
            )

        # 3. Verrouiller l'exercice
        exercice.statut = "CLOTURE_DEFINITIVE"
        exercice.date_cloture = timezone.now()
        exercice.cloture_par = request.user
        exercice.resultat_exercice = resultat
        exercice.save()

        # 4. Créer écritures d'ouverture pour l'exercice suivant
        exercice_suivant = mandat.exercices.filter(annee=exercice.annee + 1).first()
        if exercice_suivant:
            comptes_bilan = Compte.objects.filter(
                plan_comptable=plan, imputable=True, type_compte__in=["ACTIF", "PASSIF"]
            )
            journal_ouverture = journal_cloture
            numero_ouverture = f"OUV-{exercice_suivant.annee}"

            for compte in comptes_bilan:
                ecritures = compte.ecritures.filter(
                    exercice=exercice, statut__in=["VALIDE", "LETTRE", "CLOTURE"]
                )
                debit = ecritures.aggregate(Sum("montant_debit"))["montant_debit__sum"] or Decimal("0")
                credit = ecritures.aggregate(Sum("montant_credit"))["montant_credit__sum"] or Decimal("0")
                solde = debit - credit

                if solde == 0:
                    continue

                EcritureComptable.objects.create(
                    mandat=mandat,
                    exercice=exercice_suivant,
                    journal=journal_ouverture,
                    numero_piece=numero_ouverture,
                    date_ecriture=exercice_suivant.date_debut,
                    compte=compte,
                    libelle=_("Report à nouveau exercice %(annee)s") % {"annee": exercice.annee},
                    montant_debit=solde if solde > 0 else Decimal("0"),
                    montant_credit=abs(solde) if solde < 0 else Decimal("0"),
                    statut="VALIDE",
                )

        messages.success(request, _("Exercice %(annee)s clôturé avec succès. Résultat : %(resultat)s") % {
            "annee": exercice.annee,
            "resultat": f"{resultat:,.2f}",
        })
        return redirect("comptabilite:balance-generale", mandat_pk=mandat.pk)

    context = {
        "mandat": mandat,
        "exercice": exercice,
        "exercices": mandat.exercices.all(),
        "ecritures_brouillon": ecritures_brouillon,
        "declarations_non_soumises": declarations_non_soumises,
        "pret_a_cloturer": pret_a_cloturer,
    }

    return render(request, "comptabilite/cloture_exercice.html", context)


# ============ EXPORTS ============


@login_required
@permission_required_business('comptabilite.export_comptabilite')
def export_comptes_csv(request):
    """Export des comptes en CSV"""
    from core.services.export_service import ExportService

    queryset = Compte.objects.select_related('plan_comptable').order_by('numero')

    # Appliquer les mêmes filtres que la liste
    plan_id = request.GET.get('plan')
    if plan_id:
        queryset = queryset.filter(plan_comptable_id=plan_id)

    type_compte = request.GET.get('type_compte')
    if type_compte:
        queryset = queryset.filter(type_compte=type_compte)

    fields = ['numero', 'libelle', 'type_compte', 'classe', 'plan_comptable__nom']
    field_labels = {
        'numero': 'Numéro',
        'libelle': 'Libellé',
        'type_compte': 'Type',
        'classe': 'Classe',
        'plan_comptable__nom': 'Plan comptable',
    }

    return ExportService.generate_csv_from_queryset(
        queryset, fields, field_labels, 'comptes'
    )


@login_required
@permission_required_business('comptabilite.export_comptabilite')
def export_comptes_excel(request):
    """Export des comptes en Excel"""
    from core.services.export_service import ExportService

    queryset = Compte.objects.select_related('plan_comptable').order_by('numero')

    plan_id = request.GET.get('plan')
    if plan_id:
        queryset = queryset.filter(plan_comptable_id=plan_id)

    type_compte = request.GET.get('type_compte')
    if type_compte:
        queryset = queryset.filter(type_compte=type_compte)

    fields = ['numero', 'libelle', 'type_compte', 'classe', 'plan_comptable__nom']
    field_labels = {
        'numero': 'Numéro',
        'libelle': 'Libellé',
        'type_compte': 'Type',
        'classe': 'Classe',
        'plan_comptable__nom': 'Plan comptable',
    }

    return ExportService.generate_excel_streaming(
        queryset, fields, field_labels, 'comptes', 'Comptes'
    )


@login_required
@permission_required_business('comptabilite.export_comptabilite')
def export_ecritures_csv(request):
    """Export des écritures en CSV"""
    from core.services.export_service import ExportService

    queryset = EcritureComptable.objects.select_related(
        'mandat', 'compte', 'journal'
    ).order_by('-date_ecriture')

    # Filtres
    mandat_id = request.GET.get('mandat')
    if mandat_id:
        queryset = queryset.filter(mandat_id=mandat_id)

    statut = request.GET.get('statut')
    if statut:
        queryset = queryset.filter(statut=statut)

    fields = [
        'date_ecriture', 'numero_piece', 'compte__numero', 'compte__libelle',
        'libelle', 'montant_debit', 'montant_credit', 'statut'
    ]
    field_labels = {
        'date_ecriture': 'Date',
        'numero_piece': 'N° Pièce',
        'compte__numero': 'Compte',
        'compte__libelle': 'Libellé compte',
        'libelle': 'Libellé',
        'montant_debit': 'Débit',
        'montant_credit': 'Crédit',
        'statut': 'Statut',
    }

    return ExportService.generate_csv_from_queryset(
        queryset, fields, field_labels, 'ecritures'
    )


@login_required
@permission_required_business('comptabilite.export_comptabilite')
def export_ecritures_excel(request):
    """Export des écritures en Excel"""
    from core.services.export_service import ExportService

    queryset = EcritureComptable.objects.select_related(
        'mandat', 'compte', 'journal'
    ).order_by('-date_ecriture')

    mandat_id = request.GET.get('mandat')
    if mandat_id:
        queryset = queryset.filter(mandat_id=mandat_id)

    statut = request.GET.get('statut')
    if statut:
        queryset = queryset.filter(statut=statut)

    fields = [
        'date_ecriture', 'numero_piece', 'compte__numero', 'compte__libelle',
        'libelle', 'montant_debit', 'montant_credit', 'statut'
    ]
    field_labels = {
        'date_ecriture': 'Date',
        'numero_piece': 'N° Pièce',
        'compte__numero': 'Compte',
        'compte__libelle': 'Libellé compte',
        'libelle': 'Libellé',
        'montant_debit': 'Débit',
        'montant_credit': 'Crédit',
        'statut': 'Statut',
    }

    return ExportService.generate_excel_streaming(
        queryset, fields, field_labels, 'ecritures', 'Écritures'
    )


# =============================================================================
# IMPORT RELEVÉ BANCAIRE (camt.053)
# =============================================================================
class ReleveBancaireImportView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Page d'import de relevés bancaires camt.053."""
    template_name = "comptabilite/releve_bancaire_import.html"
    model = Journal
    context_object_name = "journaux"
    permission_code = "comptabilite.view"

    def get_queryset(self):
        return Journal.objects.filter(
            plan_comptable__mandat__fiduciaire=self.request.user.fiduciaire
        ).select_related("plan_comptable__mandat")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import Mandat, ExerciceComptable
        context["mandats"] = Mandat.objects.filter(
            fiduciaire=self.request.user.fiduciaire, actif=True
        )
        context["exercices"] = ExerciceComptable.objects.filter(
            mandat__fiduciaire=self.request.user.fiduciaire
        ).select_related("mandat")
        context["comptes_banque"] = Compte.objects.filter(
            plan_comptable__mandat__fiduciaire=self.request.user.fiduciaire,
            numero__startswith="10",
        ).select_related("plan_comptable__mandat")
        return context


# =============================================================================
# PAIEMENTS FOURNISSEURS (pain.001)
# =============================================================================
class PaiementListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Page de génération de fichiers pain.001."""
    template_name = "comptabilite/paiement_list.html"
    model = PieceComptable
    context_object_name = "pieces"
    permission_code = "comptabilite.view"

    def get_queryset(self):
        return PieceComptable.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import Mandat, CompteBancaire
        context["mandats"] = Mandat.objects.filter(
            fiduciaire=self.request.user.fiduciaire, actif=True
        )
        context["comptes_bancaires"] = CompteBancaire.objects.filter(
            client__mandats__fiduciaire=self.request.user.fiduciaire, actif=True
        ).distinct()
        return context