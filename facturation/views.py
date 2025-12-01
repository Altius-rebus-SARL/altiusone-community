# facturation/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count, Sum, Avg, F, Max, Min, Prefetch
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.forms import inlineformset_factory
from .models import Prestation, TimeTracking, Facture, LigneFacture, Paiement, Relance
from .forms import (
    PrestationForm,
    TimeTrackingForm,
    FactureForm,
    LigneFactureForm,
    PaiementForm,
    LigneFactureFormSet,
    RelanceForm,
)
from .filters import FactureFilter, TimeTrackingFilter, PaiementFilter
from core.models import Mandat, Client


# ============ PRESTATIONS ============


class PrestationListView(LoginRequiredMixin, ListView):
    """Liste des prestations"""

    model = Prestation
    template_name = "facturation/prestation_list.html"
    context_object_name = "prestations"
    paginate_by = 50

    def get_queryset(self):
        queryset = Prestation.objects.annotate(nb_lignes_facture=Count("lignefacture"))

        # Filtrer par type
        type_prestation = self.request.GET.get("type")
        if type_prestation:
            queryset = queryset.filter(type_prestation=type_prestation)

        # Filtrer par actif
        actif = self.request.GET.get("actif")
        if actif:
            queryset = queryset.filter(actif=actif == "true")

        return queryset.order_by("code")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["stats"] = {
            "total": self.get_queryset().count(),
            "actives": self.get_queryset().filter(actif=True).count(),
            "par_type": self.get_queryset()
            .values("type_prestation")
            .annotate(count=Count("id")),
        }

        return context


class PrestationDetailView(LoginRequiredMixin, DetailView):
    """Détail d'une prestation"""

    model = Prestation
    template_name = "facturation/prestation_detail.html"
    context_object_name = "prestation"


class PrestationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Création d'une prestation"""

    model = Prestation
    form_class = PrestationForm
    template_name = "facturation/prestation_form.html"
    permission_required = "facturation.add_prestation"
    success_url = reverse_lazy("facturation:prestation-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Prestation créée avec succès"))
        return super().form_valid(form)

class PrestationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Modification d'une prestation"""

    model = Prestation
    form_class = PrestationForm
    template_name = "facturation/prestation_form.html"
    permission_required = "facturation.change_prestation"
    success_url = reverse_lazy("facturation:prestation-list")

    def form_valid(self, form):
        messages.success(self.request, _("Prestation modifiée avec succès"))
        return super().form_valid(form)

# ============ TIME TRACKING ============


class TimeTrackingListView(LoginRequiredMixin, ListView):
    """Liste du suivi du temps"""

    model = TimeTracking
    template_name = "facturation/timetracking_list.html"
    context_object_name = "temps"
    paginate_by = 50

    def get_queryset(self):
        queryset = TimeTracking.objects.select_related(
            "mandat__client", "utilisateur", "prestation", "facture"
        )

        # Filtrer selon le rôle
        user = self.request.user
        if user.role not in ["ADMIN", "MANAGER"] and user.has_perm("facturation.view_all_timetracking"):
            queryset = queryset.filter(
                Q(utilisateur=user)
                | Q(mandat__responsable=user)
                | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = TimeTrackingFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-date_travail")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        user = self.request.user
        queryset = self.get_queryset()

        context["stats"] = {
            "total_heures": queryset.aggregate(total=Sum("duree_minutes"))["total"]
            or 0,
            "total_heures_display": (
                queryset.aggregate(total=Sum("duree_minutes"))["total"] or 0
            )
            / 60,
            "non_facture": queryset.filter(
                facturable=True, facture__isnull=True
            ).count(),
            "montant_non_facture": queryset.filter(
                facturable=True, facture__isnull=True
            ).aggregate(Sum("montant_ht"))["montant_ht__sum"]
            or 0,
        }

        # Temps par utilisateur (si admin/manager)
        if user.role in ["ADMIN", "MANAGER"]:
            context["temps_par_utilisateur"] = (
                queryset.values(
                    "utilisateur__username",
                    "utilisateur__first_name",
                    "utilisateur__last_name",
                )
                .annotate(
                    total_minutes=Sum("duree_minutes"), total_montant=Sum("montant_ht")
                )
                .order_by("-total_minutes")
            )

        return context


class TimeTrackingCreateView(LoginRequiredMixin, CreateView):
    """Saisie de temps"""

    model = TimeTracking
    form_class = TimeTrackingForm
    template_name = "facturation/timetracking_form.html"
    success_url = reverse_lazy("facturation:timetracking-list")

    def get_initial(self):
        initial = super().get_initial()
        initial["utilisateur"] = self.request.user
        initial["date_travail"] = datetime.now().date()
        initial["facturable"] = True
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        # Calcul automatique du montant si taux horaire défini
        if form.instance.taux_horaire and form.instance.duree_minutes:
            heures = Decimal(form.instance.duree_minutes) / Decimal("60")
            form.instance.montant_ht = (heures * form.instance.taux_horaire).quantize(
                Decimal("0.01")
            )

        messages.success(self.request, _("Temps enregistré avec succès"))
        return super().form_valid(form)


# ============ FACTURES ============


class FactureListView(LoginRequiredMixin, ListView):
    """Liste des factures"""

    model = Facture
    template_name = "facturation/facture_list.html"
    context_object_name = "factures"
    paginate_by = 50

    def get_queryset(self):
        queryset = Facture.objects.select_related(
            "mandat__client", "client", "creee_par"
        ).prefetch_related("lignes")

        # Filtrer selon le rôle
        user = self.request.user
        if user.role not in ["ADMIN", "MANAGER"] and not user.has_perm("facturation.view_all_factures"):
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = FactureFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-date_emission")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.get_queryset()

        context["stats"] = {
            "total": queryset.count(),
            "brouillon": queryset.filter(statut="BROUILLON").count(),
            "emises": queryset.filter(statut="EMISE").count(),
            "en_retard": queryset.filter(statut="EN_RETARD").count(),
            "payees": queryset.filter(statut="PAYEE").count(),
            "ca_total": queryset.aggregate(Sum("montant_ttc"))["montant_ttc__sum"] or 0,
            "ca_annee": queryset.filter(
                date_emission__year=datetime.now().year
            ).aggregate(Sum("montant_ttc"))["montant_ttc__sum"]
            or 0,
            "impaye_total": queryset.exclude(statut="PAYEE").aggregate(
                Sum("montant_restant")
            )["montant_restant__sum"]
            or 0,
        }

        # Évolution CA par mois (6 derniers mois)
        evolution_ca = []
        for i in range(5, -1, -1):
            date = datetime.now() - timedelta(days=30 * i)
            ca_mois = (
                queryset.filter(
                    date_emission__year=date.year, date_emission__month=date.month
                ).aggregate(Sum("montant_ttc"))["montant_ttc__sum"]
                or 0
            )

            evolution_ca.append({"mois": date.strftime("%Y-%m"), "ca": float(ca_mois)})

        context["evolution_ca"] = json.dumps(evolution_ca)

        return context


class FactureDetailView(LoginRequiredMixin, DetailView):
    """Détail d'une facture"""

    model = Facture
    template_name = "facturation/facture_detail.html"
    context_object_name = "facture"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "mandat__client",
                "client",
                "creee_par",
                "validee_par",
                "facture_origine",
            )
            .prefetch_related(
                "lignes__prestation", "lignes__temps_factures", "paiements", "relances"
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facture = self.object

        # Paiements
        context["paiements"] = facture.paiements.all().order_by("-date_paiement")

        # Relances
        context["relances"] = facture.relances.all().order_by("-date_relance")

        # Temps facturés
        temps_factures = TimeTracking.objects.none()
        for ligne in facture.lignes.all():
            temps_factures = temps_factures | ligne.temps_factures.all()
        context["temps_factures"] = temps_factures

        # Avoirs liés
        context["avoirs"] = Facture.objects.filter(
            facture_origine=facture, type_facture="AVOIR"
        )

        return context


class FactureCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Création d'une facture avec lignes"""

    model = Facture
    form_class = FactureForm
    template_name = "facturation/facture_form.html"
    permission_required = "facturation.add_facture"

    def get_initial(self):
        initial = super().get_initial()

        # Préremplir avec le mandat si fourni
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            mandat = get_object_or_404(Mandat, pk=mandat_id)
            initial["mandat"] = mandat
            initial["client"] = mandat.client

        initial["date_emission"] = datetime.now().date()
        initial["delai_paiement_jours"] = 30

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["formset"] = LigneFactureFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["formset"] = LigneFactureFormSet(instance=self.object)

        # Prestations pour l'autocomplete
        context["prestations"] = Prestation.objects.filter(actif=True).values(
            "id", "libelle", "prix_unitaire_ht", "unite", "taux_tva_defaut"
        )

        return context

    def get_success_url(self):
        return reverse_lazy("facturation:facture-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            form.instance.creee_par = self.request.user
            self.object = form.save()

            formset.instance = self.object
            formset.save()

            # Recalculer les totaux
            self.object.calculer_totaux()

            messages.success(self.request, _("Facture créée avec succès"))
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class FactureUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Modification d'une facture"""

    model = Facture
    form_class = FactureForm
    template_name = "facturation/facture_form.html"
    permission_required = "facturation.change_facture"

    def get_queryset(self):
        # Ne peut modifier que les factures en brouillon
        return super().get_queryset().filter(statut="BROUILLON")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["formset"] = LigneFactureFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["formset"] = LigneFactureFormSet(instance=self.object)

        # Prestations pour l'autocomplete
        context["prestations"] = Prestation.objects.filter(actif=True).values(
            "id", "libelle", "prix_unitaire_ht", "unite", "taux_tva_defaut"
        )

        return context

    def get_success_url(self):
        return reverse_lazy("facturation:facture-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()

            # Recalculer les totaux
            self.object.calculer_totaux()

            messages.success(self.request, _("Facture modifiée avec succès"))
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


# facturation/views.py - Ajouter ces vues


@login_required
def ligne_facture_form_row(request):
    """Retourne une nouvelle ligne de formulaire vide"""
    index = int(request.GET.get("index", 0))

    # Créer un formset vide avec un seul formulaire
    
    FormSet = inlineformset_factory(
        Facture, LigneFacture, form=LigneFactureForm, extra=1, can_delete=True
    )
    formset = FormSet()
    form = formset.forms[0]

    # Remplacer le prefix
    form.prefix = form.prefix.replace("0", str(index))

    prestations = Prestation.objects.filter(actif=True).values(
        "id", "libelle", "prix_unitaire_ht", "unite", "taux_tva_defaut"
    )

    return render(
        request,
        "facturation/partials/ligne_facture_row.html",
        {
            "ligne_form": form,
            "index": index,
            "prestations": prestations,
        },
    )


@login_required
@require_http_methods(["DELETE"])
def ligne_facture_delete_row(request, index):
    """Marque une ligne pour suppression"""
    return HttpResponse(status=200)


@login_required
@require_http_methods(["POST"])
def facture_valider(request, pk):
    """Valide une facture"""
    facture = get_object_or_404(Facture, pk=pk, statut="BROUILLON")

    try:
        facture.valider(request.user)
        messages.success(request, _("Facture validée avec succès"))
    except ValueError as e:
        messages.error(request, str(e))

    return redirect("facturation:facture-detail", pk=pk)


@login_required
def facture_generer_pdf(request, pk):
    """Génère le PDF d'une facture"""
    facture = get_object_or_404(Facture, pk=pk)

    try:
        fichier = facture.generer_pdf()

        with fichier.open("rb") as f:
            response = HttpResponse(f.read(), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{fichier.name}"'

        messages.success(request, _("PDF généré avec succès"))
        return response

    except Exception as e:
        messages.error(request, f"Erreur lors de la génération: {str(e)}")
        return redirect("facturation:facture-detail", pk=pk)


@login_required
def facture_envoyer_email(request, pk):
    """Envoie la facture par email au client"""
    facture = get_object_or_404(Facture, pk=pk)

    # TODO: Envoyer l'email avec le PDF

    facture.statut = "ENVOYEE"
    facture.save()

    messages.success(request, _("Facture envoyée par email"))
    return redirect("facturation:facture-detail", pk=pk)


# ============ LIGNES DE FACTURE ============


@login_required
def ligne_facture_create(request, facture_pk):
    """Ajoute une ligne à une facture"""
    facture = get_object_or_404(Facture, pk=facture_pk, statut="BROUILLON")

    if request.method == "POST":
        form = LigneFactureForm(request.POST)
        if form.is_valid():
            ligne = form.save(commit=False)
            ligne.facture = facture

            # Ordre
            dernier_ordre = facture.lignes.aggregate(Max("ordre"))["ordre__max"] or 0
            ligne.ordre = dernier_ordre + 1

            ligne.save()

            # Recalculer la facture
            facture.calculer_totaux()

            messages.success(request, _("Ligne ajoutée avec succès"))
            return redirect("facturation:facture-detail", pk=facture.pk)
    else:
        form = LigneFactureForm()

    return render(
        request, "facturation/ligne_form.html", {"form": form, "facture": facture}
    )


@login_required
def ligne_facture_delete(request, pk):
    """Supprime une ligne de facture"""
    ligne = get_object_or_404(LigneFacture, pk=pk)
    facture = ligne.facture

    if facture.statut != "BROUILLON":
        messages.error(
            request, _("Impossible de supprimer une ligne d'une facture validée")
        )
        return redirect("facturation:facture-detail", pk=facture.pk)

    ligne.delete()
    facture.calculer_totaux()

    messages.success(request, _("Ligne supprimée avec succès"))
    return redirect("facturation:facture-detail", pk=facture.pk)


# ============ PAIEMENTS ============


# facturation/views.py


class PaiementListView(LoginRequiredMixin, ListView):
    """Liste des paiements"""

    model = Paiement
    template_name = "facturation/paiement_list.html"
    context_object_name = "paiements"
    paginate_by = 50

    def get_queryset(self):
        # Queryset de base
        queryset = Paiement.objects.select_related(
            "facture__client", "facture__mandat", "valide_par"
        ).filter(is_active=True)

        # Appliquer les filtres SEULEMENT s'il y a des paramètres
        if self.request.GET:
            self.filterset = PaiementFilter(self.request.GET, queryset=queryset)
            return self.filterset.qs.order_by("-date_paiement")
        else:
            # Pas de filtres = tout afficher
            self.filterset = PaiementFilter(queryset=queryset)  # Filterset vide
            return queryset.order_by("-date_paiement")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.object_list  # Utiliser object_list au lieu de get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "valides": queryset.filter(valide=True).count(),
            "montant_total": queryset.filter(valide=True).aggregate(Sum("montant"))[
                "montant__sum"
            ]
            or 0,
            "montant_mois": queryset.filter(
                valide=True,
                date_paiement__year=datetime.now().year,
                date_paiement__month=datetime.now().month,
            ).aggregate(Sum("montant"))["montant__sum"]
            or 0,
        }

        return context


@login_required
def paiement_create(request, facture_pk):
    """Enregistre un paiement pour une facture"""
    facture = get_object_or_404(Facture, pk=facture_pk)

    if request.method == "POST":
        form = PaiementForm(request.POST)
        if form.is_valid():
            try:
                paiement = facture.enregistrer_paiement(
                    montant=form.cleaned_data["montant"],
                    date_paiement=form.cleaned_data["date_paiement"],
                    mode_paiement=form.cleaned_data["mode_paiement"],
                    reference=form.cleaned_data.get("reference", ""),
                    user=request.user,
                )
                messages.success(request, _("Paiement enregistré avec succès"))
                return redirect("facturation:facture-detail", pk=facture.pk)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = PaiementForm(
            initial={
                "montant": facture.montant_restant,
                "date_paiement": datetime.now().date(),
            }
        )

    return render(
        request, "facturation/paiement_form.html", {"form": form, "facture": facture}
    )


@login_required
@require_http_methods(["POST"])
def paiement_valider(request, pk):
    """Valide un paiement"""
    paiement = get_object_or_404(Paiement, pk=pk, valide=False)

    paiement.valide = True
    paiement.valide_par = request.user
    paiement.date_validation = datetime.now()
    paiement.save()

    messages.success(request, _("Paiement validé avec succès"))
    return redirect("facturation:facture-detail", pk=paiement.facture.pk)


# ============ RELANCES ============


@login_required
def relance_create(request, facture_pk):
    """Crée une relance pour une facture"""
    facture = get_object_or_404(Facture, pk=facture_pk)

    try:
        relance = facture.creer_relance(user=request.user)
        messages.success(request, _("Relance créée avec succès"))
        return redirect("facturation:facture-detail", pk=facture.pk)
    except Exception as e:
        messages.error(request, str(e))
        return redirect("facturation:facture-detail", pk=facture.pk)
