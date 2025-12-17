# salaires/views.py
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
    Employe,
    TauxCotisation,
    FicheSalaire,
    CertificatSalaire,
    CertificatTravail,
    DeclarationCotisations,
)
from .forms import EmployeForm, FicheSalaireForm, CertificatSalaireForm, CertificatTravailForm
from .filters import EmployeFilter, FicheSalaireFilter
from core.models import Mandat


# ============ EMPLOYÉS ============


class EmployeListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des employés"""

    model = Employe
    business_permission = 'salaires.view_employes'
    template_name = "salaires/employe_list.html"
    context_object_name = "employes"
    paginate_by = 50

    def get_queryset(self):
        queryset = (
            Employe.objects.select_related("mandat__client", "adresse")
            .annotate(nb_fiches=Count("fiches_salaire"))
            .filter(is_active=True)
        )
        
        print(f"🔵 Queryset initial: {queryset.count()} employés")
        print(f"🔵 GET params: {self.request.GET}")
        
        user = self.request.user
        if not user.is_manager():
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()
            print(f"🔵 Après filtre role: {queryset.count()} employés")

        if self.request.GET:
            self.filterset = EmployeFilter(self.request.GET, queryset=queryset)
            if self.filterset.is_valid():
                print(f"🔵 Après filtre: {self.filterset.qs.count()} employés")
                return self.filterset.qs.order_by("nom", "prenom")
        
        self.filterset = EmployeFilter(queryset=queryset)
        print(f"🔵 Final queryset: {queryset.count()} employés")
        return queryset.order_by("nom", "prenom")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # ✅ Statistiques sur le queryset PAGINÉ
        # Obtenir le queryset COMPLET (avant pagination)
        full_queryset = self.get_queryset()

        context["stats"] = {
            "total": full_queryset.count(),
            "actifs": full_queryset.filter(statut="ACTIF").count(),
            "cdi": full_queryset.filter(type_contrat="CDI").count(),
            "masse_salariale": full_queryset.filter(statut="ACTIF").aggregate(
                Sum("salaire_brut_mensuel")
            )["salaire_brut_mensuel__sum"]
            or 0,
        }

        return context


class EmployeDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un employé"""

    model = Employe
    business_permission = 'salaires.view_employes'
    template_name = "salaires/employe_detail.html"
    context_object_name = "employe"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("mandat__client", "adresse")
            .prefetch_related("fiches_salaire", "certificats_salaire")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employe = self.object

        # Fiches de salaire
        context["fiches_recentes"] = employe.fiches_salaire.order_by("-periode")[:12]

        # Certificats de salaire
        context["certificats"] = employe.certificats_salaire.order_by("-annee")

        # Statistiques annuelles
        annee_courante = datetime.now().year
        fiches_annee = employe.fiches_salaire.filter(
            annee=annee_courante, statut__in=["VALIDE", "PAYE", "COMPTABILISE"]
        )

        context["stats_annee"] = {
            "salaire_brut_total": fiches_annee.aggregate(Sum("salaire_brut_total"))[
                "salaire_brut_total__sum"
            ]
            or 0,
            "salaire_net_total": fiches_annee.aggregate(Sum("salaire_net"))[
                "salaire_net__sum"
            ]
            or 0,
            "cotisations_employe": fiches_annee.aggregate(
                Sum("total_cotisations_employe")
            )["total_cotisations_employe__sum"]
            or 0,
            "charges_patronales": fiches_annee.aggregate(
                Sum("total_charges_patronales")
            )["total_charges_patronales__sum"]
            or 0,
        }

        # Évolution salaire brut
        evolution = []
        for fiche in context["fiches_recentes"]:
            evolution.append(
                {
                    "periode": fiche.periode.strftime("%Y-%m"),
                    "salaire_brut": float(fiche.salaire_brut_total),
                    "salaire_net": float(fiche.salaire_net),
                }
            )
        context["evolution_salaire"] = json.dumps(list(reversed(evolution)))

        return context


class EmployeCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un employé"""

    model = Employe
    form_class = EmployeForm
    template_name = "salaires/employe_form.html"
    business_permission = 'salaires.view_employes'

    def get_success_url(self):
        return reverse_lazy("salaires:employe-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Employé créé avec succès"))
        return super().form_valid(form)


class EmployeUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un employé"""

    model = Employe
    form_class = EmployeForm
    template_name = "salaires/employe_form.html"
    business_permission = 'salaires.view_employes'

    def get_success_url(self):
        return reverse_lazy("salaires:employe-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Employé modifié avec succès"))
        return super().form_valid(form)


# ============ FICHES DE SALAIRE ============


class FicheSalaireListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des fiches de salaire"""

    model = FicheSalaire
    business_permission = 'salaires.view_fiches_salaire'
    template_name = "salaires/fiche_list.html"
    context_object_name = "fiches"
    paginate_by = 50

    def get_queryset(self):
        # Base queryset
        queryset = FicheSalaire.objects.select_related(
            "employe__mandat__client", "employe", "valide_par"
        ).filter(is_active=True)

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager():
            queryset = queryset.filter(
                Q(employe__mandat__responsable=user) | Q(employe__mandat__equipe=user)
            ).distinct()

        # ✅ CORRECTION : Appliquer les filtres SEULEMENT s'il y a des paramètres
        if self.request.GET:
            self.filterset = FicheSalaireFilter(self.request.GET, queryset=queryset)
            if self.filterset.is_valid():
                return self.filterset.qs.order_by("-periode", "employe__nom")

        # Si pas de paramètres, créer un filterset vide
        self.filterset = FicheSalaireFilter(queryset=queryset)
        return queryset.order_by("-periode", "employe__nom")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques sur le queryset complet
        full_queryset = self.get_queryset()

        context["stats"] = {
            "total": full_queryset.count(),
            "brouillon": full_queryset.filter(statut="BROUILLON").count(),
            "valide": full_queryset.filter(statut="VALIDE").count(),
            "paye": full_queryset.filter(statut="PAYE").count(),
            "masse_salariale_mois": full_queryset.filter(
                periode__year=datetime.now().year,
                periode__month=datetime.now().month,
                statut__in=["VALIDE", "PAYE", "COMPTABILISE"],
            ).aggregate(Sum("salaire_brut_total"))["salaire_brut_total__sum"]
            or 0,
        }

        return context


class FicheSalaireDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une fiche de salaire"""

    model = FicheSalaire
    business_permission = 'salaires.view_fiches_salaire'
    template_name = "salaires/fiche_detail.html"
    context_object_name = "fiche"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "employe__mandat__client",
                "employe__adresse",
                "valide_par",
                "ecriture_comptable",
            )
        )


class FicheSalaireCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'une fiche de salaire"""

    model = FicheSalaire
    form_class = FicheSalaireForm
    template_name = "salaires/fiche_form.html"
    business_permission = 'salaires.add_fiche_salaire'

    def get_initial(self):
        initial = super().get_initial()

        # Préremplir avec l'employé si fourni
        employe_id = self.request.GET.get("employe")
        if employe_id:
            employe = get_object_or_404(Employe, pk=employe_id)
            initial["employe"] = employe
            initial["salaire_base"] = employe.salaire_brut_mensuel

        # Période par défaut: mois précédent
        today = datetime.now().date()
        if today.month == 1:
            initial["periode"] = today.replace(year=today.year - 1, month=12, day=1)
        else:
            initial["periode"] = today.replace(month=today.month - 1, day=1)

        return initial

    def get_success_url(self):
        return reverse_lazy("salaires:fiche-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        fiche = form.instance
        fiche.calculer()
        messages.success(self.request, _("Fiche de salaire créée avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def fiche_valider(request, pk):
    """Valide une fiche de salaire"""
    fiche = get_object_or_404(FicheSalaire, pk=pk, statut="BROUILLON")

    fiche.calculer()
    fiche.statut = "VALIDE"
    fiche.valide_par = request.user
    fiche.date_validation = datetime.now()
    fiche.save()

    messages.success(request, _("Fiche de salaire validée avec succès"))
    return redirect("salaires:fiche-detail", pk=pk)


@login_required
def fiche_generer_pdf(request, pk):
    """Génère le PDF d'une fiche de salaire"""
    from django.http import FileResponse

    fiche = get_object_or_404(FicheSalaire, pk=pk)

    try:
        # Générer le PDF
        fichier = fiche.generer_pdf()

        # Retourner le fichier PDF
        if fichier:
            response = FileResponse(
                fichier.open("rb"),
                content_type="application/pdf"
            )
            response["Content-Disposition"] = f'attachment; filename="fiche_salaire_{fiche.numero_fiche}.pdf"'
            return response

        messages.error(request, _("Erreur lors de la génération du PDF"))
        return redirect("salaires:fiche-detail", pk=pk)

    except Exception as e:
        messages.error(request, _("Erreur lors de la génération du PDF: %(error)s") % {'error': str(e)})
        return redirect("salaires:fiche-detail", pk=pk)


@login_required
def certificat_generer_pdf(request, pk):
    """Génère le PDF d'un certificat de salaire annuel"""
    from django.http import FileResponse

    certificat = get_object_or_404(CertificatSalaire, pk=pk)

    try:
        # Générer le PDF
        fichier = certificat.generer_pdf()

        # Retourner le fichier PDF
        if fichier:
            response = FileResponse(
                fichier.open("rb"),
                content_type="application/pdf"
            )
            response["Content-Disposition"] = f'attachment; filename="certificat_salaire_{certificat.employe.matricule}_{certificat.annee}.pdf"'
            return response

        messages.error(request, _("Erreur lors de la génération du PDF"))
        return redirect("salaires:certificat-detail", pk=pk)

    except Exception as e:
        messages.error(request, _("Erreur lors de la génération du PDF: %(error)s") % {'error': str(e)})
        return redirect("salaires:certificat-detail", pk=pk)


@login_required
def generer_fiches_masse(request):
    """Génère les fiches de salaire pour tous les employés actifs d'un mandat"""

    if request.method == "POST":
        mandat_id = request.POST.get("mandat")
        periode_str = request.POST.get("periode")

        mandat = get_object_or_404(Mandat, pk=mandat_id)
        periode = datetime.strptime(periode_str, "%Y-%m-%d").date()

        employes = Employe.objects.filter(mandat=mandat, statut="ACTIF")

        fiches_creees = 0
        for employe in employes:
            if not FicheSalaire.objects.filter(
                employe=employe, periode=periode
            ).exists():
                # Créer la fiche SANS sauvegarder
                fiche = FicheSalaire(
                    employe=employe,
                    periode=periode,
                    salaire_base=employe.salaire_brut_mensuel,
                    created_by=request.user,
                )

                # CALCULER D'ABORD (sans save)
                fiche.annee = periode.year
                fiche.mois = periode.month
                fiche.numero_fiche = (
                    f"SAL-{periode.strftime('%Y%m')}-{employe.matricule}"
                )

                # Calculer salaire brut total
                fiche.salaire_brut_total = (
                    fiche.salaire_base
                    + fiche.heures_supp_montant
                    + fiche.primes
                    + fiche.indemnites
                    + fiche.treizieme_mois
                )

                # Cotisations employé
                fiche.avs_employe = fiche._calculer_cotisation("AVS", "employe")
                fiche.ac_employe = fiche._calculer_cotisation("AC", "employe")
                fiche.lpp_employe = fiche._calculer_cotisation("LPP", "employe")

                fiche.total_cotisations_employe = (
                    fiche.avs_employe
                    + fiche.ac_employe
                    + fiche.ac_supp_employe
                    + fiche.lpp_employe
                    + fiche.laa_employe
                    + fiche.laac_employe
                    + fiche.ijm_employe
                )

                # Déductions totales
                fiche.total_deductions = (
                    fiche.total_cotisations_employe
                    + fiche.impot_source
                    + fiche.avance_salaire
                    + fiche.saisie_salaire
                    + fiche.autres_deductions
                )

                # Salaire net
                fiche.salaire_net = (
                    fiche.salaire_brut_total
                    - fiche.total_deductions
                    + fiche.allocations_familiales
                    + fiche.autres_allocations
                )

                # Charges patronales
                fiche.avs_employeur = fiche._calculer_cotisation("AVS", "employeur")
                fiche.ac_employeur = fiche._calculer_cotisation("AC", "employeur")
                fiche.lpp_employeur = fiche._calculer_cotisation("LPP", "employeur")

                fiche.total_charges_patronales = (
                    fiche.avs_employeur
                    + fiche.ac_employeur
                    + fiche.lpp_employeur
                    + fiche.laa_employeur
                    + fiche.af_employeur
                )

                # Coût total
                fiche.cout_total_employeur = (
                    fiche.salaire_brut_total + fiche.total_charges_patronales
                )

                # MAINTENANT on peut sauvegarder
                fiche.save()
                fiches_creees += 1

        messages.success(
            request,
            _("%(count)d fiches de salaire créées avec succès")
            % {"count": fiches_creees},
        )
        return redirect("salaires:fiche-list")

    mandats = Mandat.objects.filter(
        statut="ACTIF", type_mandat__in=["SALAIRES", "GLOBAL"]
    )

    return render(request, "salaires/generer_fiches_masse.html", {"mandats": mandats})


# ============ CERTIFICATS DE SALAIRE ============


class CertificatSalaireListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des certificats de salaire"""

    model = CertificatSalaire
    business_permission = 'salaires.view_fiches_salaire'
    template_name = "salaires/certificat_list.html"
    context_object_name = "certificats"
    paginate_by = 50

    def get_queryset(self):
        return CertificatSalaire.objects.select_related(
            "employe__mandat", "genere_par"
        ).order_by("-annee", "employe__nom")


class CertificatSalaireDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un certificat de salaire"""

    model = CertificatSalaire
    business_permission = 'salaires.view_fiches_salaire'
    template_name = "salaires/certificat_detail.html"
    context_object_name = "certificat"


@login_required
def generer_certificat(request, employe_pk):
    """Génère le certificat de salaire annuel pour un employé"""
    employe = get_object_or_404(Employe, pk=employe_pk)

    if request.method == "POST":
        annee = int(request.POST.get("annee"))

        # Récupérer les fiches validées
        fiches = FicheSalaire.objects.filter(
            employe=employe,
            periode__year=annee,
            statut__in=["VALIDE", "PAYE", "COMPTABILISE"],
        )

        # Calculer les totaux
        totaux = fiches.aggregate(
            salaire_brut_annuel=Sum("salaire_brut_total"),
            treizieme_salaire_annuel=Sum("treizieme_mois"),
            primes_annuelles=Sum("primes"),
            avs_annuel=Sum("avs_employe"),
            ac_annuel=Sum("ac_employe"),
            lpp_annuel=Sum("lpp_employe"),
            allocations_familiales_annuel=Sum("allocations_familiales"),
            impot_source_annuel=Sum("impot_source"),
        )

        # Créer ou récupérer le certificat
        certificat, created = CertificatSalaire.objects.get_or_create(
            employe=employe,
            annee=annee,
            defaults={
                "date_debut": datetime(annee, 1, 1).date(),
                "date_fin": datetime(annee, 12, 31).date(),
                "genere_par": request.user,
                "salaire_brut_annuel": totaux["salaire_brut_annuel"] or Decimal("0.00"),
                "treizieme_salaire_annuel": totaux["treizieme_salaire_annuel"]
                or Decimal("0.00"),
                "primes_annuelles": totaux["primes_annuelles"] or Decimal("0.00"),
                "avs_annuel": totaux["avs_annuel"] or Decimal("0.00"),
                "ac_annuel": totaux["ac_annuel"] or Decimal("0.00"),
                "lpp_annuel": totaux["lpp_annuel"] or Decimal("0.00"),
                "allocations_familiales_annuel": totaux["allocations_familiales_annuel"]
                or Decimal("0.00"),
                "impot_source_annuel": totaux["impot_source_annuel"] or Decimal("0.00"),
            },
        )

        if created:
            messages.success(request, _("Certificat de salaire généré avec succès"))
        else:
            # Mettre à jour le certificat existant
            certificat.salaire_brut_annuel = totaux["salaire_brut_annuel"] or Decimal(
                "0.00"
            )
            certificat.treizieme_salaire_annuel = totaux[
                "treizieme_salaire_annuel"
            ] or Decimal("0.00")
            certificat.primes_annuelles = totaux["primes_annuelles"] or Decimal("0.00")
            certificat.avs_annuel = totaux["avs_annuel"] or Decimal("0.00")
            certificat.ac_annuel = totaux["ac_annuel"] or Decimal("0.00")
            certificat.lpp_annuel = totaux["lpp_annuel"] or Decimal("0.00")
            certificat.allocations_familiales_annuel = totaux[
                "allocations_familiales_annuel"
            ] or Decimal("0.00")
            certificat.impot_source_annuel = totaux["impot_source_annuel"] or Decimal(
                "0.00"
            )
            certificat.save()
            messages.info(request, _("Le certificat a été mis à jour"))

        return redirect("salaires:certificat-detail", pk=certificat.pk)

    return render(
        request,
        "salaires/generer_certificat.html",
        {"employe": employe, "current_year": datetime.now().year},
    )


# ============ CERTIFICATS DE TRAVAIL ============


class CertificatTravailListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des certificats de travail"""

    model = CertificatTravail
    business_permission = 'salaires.view_employes'
    template_name = "salaires/certificat_travail_list.html"
    context_object_name = "certificats"
    paginate_by = 50

    def get_queryset(self):
        return CertificatTravail.objects.select_related(
            "employe__mandat__client", "emis_par"
        ).order_by("-date_emission")


class CertificatTravailDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un certificat de travail"""

    model = CertificatTravail
    business_permission = 'salaires.view_employes'
    template_name = "salaires/certificat_travail_detail.html"
    context_object_name = "certificat"


class CertificatTravailCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un certificat de travail"""

    model = CertificatTravail
    form_class = CertificatTravailForm
    business_permission = 'salaires.manage_employes'
    template_name = "salaires/certificat_travail_form.html"

    def get_initial(self):
        initial = super().get_initial()
        employe_pk = self.kwargs.get('employe_pk')
        if employe_pk:
            employe = get_object_or_404(Employe, pk=employe_pk)
            initial['employe'] = employe
            initial['date_debut_emploi'] = employe.date_entree
            initial['date_fin_emploi'] = employe.date_sortie
            initial['fonction_principale'] = employe.fonction
            initial['departement'] = employe.departement
            initial['taux_occupation'] = employe.taux_occupation
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employe_pk = self.kwargs.get('employe_pk')
        if employe_pk:
            context['employe'] = get_object_or_404(Employe, pk=employe_pk)
        return context

    def form_valid(self, form):
        form.instance.emis_par = self.request.user
        messages.success(self.request, _("Certificat de travail créé avec succès."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("salaires:certificat-travail-detail", kwargs={"pk": self.object.pk})


class CertificatTravailUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un certificat de travail"""

    model = CertificatTravail
    form_class = CertificatTravailForm
    business_permission = 'salaires.manage_employes'
    template_name = "salaires/certificat_travail_form.html"

    def form_valid(self, form):
        messages.success(self.request, _("Certificat de travail mis à jour."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("salaires:certificat-travail-detail", kwargs={"pk": self.object.pk})


@login_required
def certificat_travail_generer_pdf(request, pk):
    """Génère le PDF d'un certificat de travail"""
    from django.http import FileResponse

    certificat = get_object_or_404(CertificatTravail, pk=pk)

    try:
        # Générer le PDF
        fichier = certificat.generer_pdf()

        # Retourner le fichier PDF
        if fichier:
            response = FileResponse(
                fichier.open("rb"),
                content_type="application/pdf"
            )
            type_suffix = certificat.type_certificat.lower()
            response["Content-Disposition"] = f'attachment; filename="certificat_travail_{certificat.employe.matricule}_{type_suffix}.pdf"'
            return response

        messages.error(request, _("Erreur lors de la génération du PDF"))
        return redirect("salaires:certificat-travail-detail", pk=pk)

    except Exception as e:
        messages.error(request, _("Erreur lors de la génération du PDF: %(error)s") % {'error': str(e)})
        return redirect("salaires:certificat-travail-detail", pk=pk)


# ============ DÉCLARATIONS COTISATIONS ============


class DeclarationCotisationsListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des déclarations de cotisations"""

    model = DeclarationCotisations
    business_permission = 'salaires.view_cotisations'
    template_name = "salaires/declaration_cotisations_list.html"
    context_object_name = "declarations"

    def get_queryset(self):
        return DeclarationCotisations.objects.select_related("mandat").order_by(
            "-periode_fin"
        )
