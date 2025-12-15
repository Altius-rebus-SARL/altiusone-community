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
from django.urls import reverse_lazy
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


# ============ PLANS COMPTABLES ============


from .filters import PlanComptableFilter



# comptabilite/views.py


class PlanComptableListView(LoginRequiredMixin, BusinessPermissionMixin, FilterView):
    """Liste des plans comptables"""

    model = PlanComptable
    template_name = "comptabilite/plan_list.html"
    context_object_name = "plans"
    paginate_by = 25
    filterset_class = PlanComptableFilter
    business_permission = 'comptabilite.view_plan_comptable'

    def get_queryset(self):
        queryset = PlanComptable.objects.select_related("mandat").annotate(
            nb_comptes=Count("comptes")
        )

        # SUPPRIMEZ CE BLOC QUI FILTRE TOUT
        # user = self.request.user
        # if user.role not in ["ADMIN", "MANAGER"]:
        #     queryset = queryset.filter(
        #         Q(mandat__responsable=user) | Q(mandat__equipe=user)
        #     ).distinct()

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
        if user.role in ["ADMIN", "MANAGER"]:
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
        if user.role not in ["ADMIN", "MANAGER"] and user.is_superuser == False:
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

    def get_initial(self):
        initial = super().get_initial()

        # Préremplir avec le mandat si fourni
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            mandat = get_object_or_404(Mandat, pk=mandat_id)
            initial["mandat"] = mandat
            initial["exercice"] = mandat.exercices.filter(statut="OUVERT").first()

        # Préremplir la date
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
        if user.role not in ["ADMIN", "MANAGER"]:
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

        return context


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