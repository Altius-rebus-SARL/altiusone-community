# analytics/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count, Sum, Avg, F, Max, Min
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.http import FileResponse

from core.permissions import BusinessPermissionMixin, permission_required_business

from .models import (
    TableauBord,
    Indicateur,
    ValeurIndicateur,
    Rapport,
    PlanificationRapport,
    ComparaisonPeriode,
    AlerteMetrique,
    ExportDonnees,
)
from .forms import (
    TableauBordForm,
    IndicateurForm,
    RapportForm,
    PlanificationRapportForm,
    ComparaisonPeriodeForm,
    ExportDonneesForm,
)
from core.models import Mandat


# ============ TABLEAUX DE BORD ============


class TableauBordListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des tableaux de bord"""

    model = TableauBord
    template_name = "analytics/tableau_bord_list.html"
    context_object_name = "tableaux"
    business_permission = 'analytics.view_tableaux_bord'

    def get_queryset(self):
        user = self.request.user

        return (
            TableauBord.objects.filter(
                Q(proprietaire=user)
                | Q(visibilite="TOUS")
                | (
                    Q(visibilite="EQUIPE")
                    & Q(proprietaire__in=user.mandats_equipe.values("responsable"))
                )
                | Q(utilisateurs_partage=user)
            )
            .distinct()
            .order_by("ordre", "nom")
        )


class TableauBordDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Affichage d'un tableau de bord"""

    model = TableauBord
    template_name = "analytics/tableau_bord_detail.html"
    context_object_name = "tableau"
    business_permission = 'analytics.view_tableaux_bord'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tableau = self.object

        # Configuration du tableau en JSON pour le frontend
        context["configuration"] = json.dumps(tableau.configuration)

        # Calculer les valeurs des indicateurs selon la configuration
        from .services import KPICalculator
        from .models import Indicateur

        calculator = KPICalculator()
        kpi_values = {}

        # Si la configuration contient des widgets, calculer leurs métriques
        if tableau.configuration and 'widgets' in tableau.configuration:
            for widget in tableau.configuration['widgets']:
                metric_code = widget.get('metric')
                if metric_code:
                    try:
                        indicateur = Indicateur.objects.get(code=metric_code)
                        resultat = calculator.calculer_kpi(indicateur)
                        kpi_values[metric_code] = {
                            'valeur': float(resultat['valeur']),
                            'indicateur': {
                                'nom': indicateur.nom,
                                'unite': indicateur.unite,
                                'decimales': indicateur.decimales,
                                'objectif_cible': float(indicateur.objectif_cible) if indicateur.objectif_cible else None,
                            },
                            'details': resultat.get('details', {}),
                        }
                    except Indicateur.DoesNotExist:
                        kpi_values[metric_code] = {
                            'valeur': 0,
                            'erreur': 'Indicateur non trouvé'
                        }

        context["kpi_values"] = json.dumps(kpi_values)

        return context


class TableauBordCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un tableau de bord"""

    model = TableauBord
    form_class = TableauBordForm
    template_name = "analytics/tableau_bord_form.html"
    success_url = reverse_lazy("analytics:tableau-bord-list")
    business_permission = 'analytics.view_tableaux_bord'

    def form_valid(self, form):
        form.instance.proprietaire = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Tableau de bord créé avec succès"))
        return super().form_valid(form)


# ============ INDICATEURS ============


class IndicateurListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des indicateurs"""

    model = Indicateur
    template_name = "analytics/indicateur_list.html"
    context_object_name = "indicateurs"
    business_permission = 'analytics.view_indicateurs'

    def get_queryset(self):
        queryset = Indicateur.objects.filter(actif=True).annotate(
            nb_valeurs=Count("valeurs")
        )

        # Filtrer par catégorie
        categorie = self.request.GET.get("categorie")
        if categorie:
            queryset = queryset.filter(categorie=categorie)

        return queryset.order_by("categorie", "nom")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Catégories
        context["categories"] = (
            Indicateur.objects.values("categorie")
            .annotate(count=Count("id"))
            .order_by("categorie")
        )

        return context


class IndicateurDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un indicateur avec historique"""

    model = Indicateur
    template_name = "analytics/indicateur_detail.html"
    context_object_name = "indicateur"
    business_permission = 'analytics.view_indicateurs'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        indicateur = self.object

        # Valeurs récentes
        valeurs = indicateur.valeurs.order_by("-date_mesure")[:50]
        context["valeurs"] = valeurs

        # Évolution pour graphique
        evolution = []
        for valeur in reversed(list(valeurs)):
            evolution.append(
                {
                    "date": valeur.date_mesure.strftime("%Y-%m-%d"),
                    "valeur": float(valeur.valeur),
                    "objectif": float(indicateur.objectif_cible)
                    if indicateur.objectif_cible
                    else None,
                }
            )

        context["evolution"] = json.dumps(evolution)

        # Statistiques
        context["stats"] = {
            "derniere_valeur": valeurs.first().valeur if valeurs.exists() else None,
            "moyenne": valeurs.aggregate(Avg("valeur"))["valeur__avg"],
            "min": valeurs.aggregate(Min("valeur"))["valeur__min"],
            "max": valeurs.aggregate(Max("valeur"))["valeur__max"],
        }

        return context


# ============ RAPPORTS ============


class RapportListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des rapports générés"""

    model = Rapport
    template_name = "analytics/rapport_list.html"
    context_object_name = "rapports"
    paginate_by = 50
    business_permission = 'analytics.view_rapports'

    def get_queryset(self):
        queryset = Rapport.objects.select_related(
            "mandat__client", "genere_par", "planification"
        )

        # Filtrer par type
        type_rapport = self.request.GET.get("type")
        if type_rapport:
            queryset = queryset.filter(type_rapport=type_rapport)

        # Filtrer par mandat
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            queryset = queryset.filter(mandat_id=mandat_id)

        return queryset.order_by("-date_generation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Types de rapports
        context["types_rapport"] = (
            Rapport.objects.values("type_rapport")
            .annotate(count=Count("id"))
            .order_by("type_rapport")
        )

        return context


class RapportDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un rapport"""

    model = Rapport
    template_name = "analytics/rapport_detail.html"
    context_object_name = "rapport"
    business_permission = 'analytics.view_rapports'


@login_required
def rapport_telecharger(request, pk):
    """Télécharge un rapport"""
    rapport = get_object_or_404(Rapport, pk=pk)

    if rapport.fichier:
        response = FileResponse(rapport.fichier.open("rb"))
        response["Content-Disposition"] = (
            f'attachment; filename="{rapport.nom}.{rapport.format_fichier.lower()}"'
        )
        return response

    messages.error(request, _("Fichier non trouvé"))
    return redirect("analytics:rapport-detail", pk=pk)


@login_required
def rapport_generer(request):
    """Génère un nouveau rapport"""

    if request.method == "POST":
        form = RapportForm(request.POST)
        if form.is_valid():
            rapport = form.save(commit=False)
            rapport.genere_par = request.user
            rapport.statut = "EN_COURS"
            rapport.save()

            # TODO: Lancer génération asynchrone
            # from analytics.tasks import generer_rapport_async
            # generer_rapport_async.delay(rapport.id)

            messages.success(request, _("Génération du rapport lancée"))
            return redirect("analytics:rapport-detail", pk=rapport.pk)
    else:
        form = RapportForm()

    return render(request, "analytics/rapport_generer.html", {"form": form})


# ============ PLANIFICATIONS DE RAPPORTS ============


class PlanificationRapportListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des planifications de rapports"""

    model = PlanificationRapport
    template_name = "analytics/planification_list.html"
    context_object_name = "planifications"
    business_permission = 'analytics.schedule_rapport'

    def get_queryset(self):
        return PlanificationRapport.objects.select_related("mandat").order_by("nom")


class PlanificationRapportCreateView(
    LoginRequiredMixin, BusinessPermissionMixin, CreateView
):
    """Création d'une planification de rapport"""

    model = PlanificationRapport
    form_class = PlanificationRapportForm
    template_name = "analytics/planification_form.html"
    business_permission = 'analytics.schedule_rapport'
    success_url = reverse_lazy("analytics:planification-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Planification créée avec succès"))
        return super().form_valid(form)


# ============ COMPARAISONS DE PÉRIODES ============


@login_required
def comparaison_periodes(request):
    """Crée une comparaison entre deux périodes"""

    if request.method == "POST":
        form = ComparaisonPeriodeForm(request.POST)
        if form.is_valid():
            comparaison = form.save(commit=False)
            comparaison.created_by = request.user

            # TODO: Calculer les résultats de comparaison
            # comparaison.resultats = calculer_comparaison(...)

            comparaison.save()

            messages.success(request, _("Comparaison créée avec succès"))
            return redirect("analytics:comparaison-detail", pk=comparaison.pk)
    else:
        form = ComparaisonPeriodeForm()

    return render(request, "analytics/comparaison_form.html", {"form": form})


class ComparaisonPeriodeDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une comparaison de périodes"""

    model = ComparaisonPeriode
    template_name = "analytics/comparaison_detail.html"
    context_object_name = "comparaison"
    business_permission = 'analytics.view_rapports'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Résultats en JSON pour graphiques
        if self.object.resultats:
            context["resultats"] = json.dumps(self.object.resultats)

        return context


# ============ ALERTES ============


class AlerteMetriqueListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des alertes"""

    model = AlerteMetrique
    template_name = "analytics/alerte_list.html"
    context_object_name = "alertes"
    paginate_by = 50
    business_permission = 'analytics.view_alertes'

    def get_queryset(self):
        user = self.request.user

        queryset = AlerteMetrique.objects.select_related(
            "indicateur", "valeur_indicateur", "mandat", "acquittee_par"
        )

        # Filtrer selon le rôle
        if not user.is_manager():
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Par défaut: alertes actives
        statut = self.request.GET.get("statut", "ACTIVE")
        if statut:
            queryset = queryset.filter(statut=statut)

        return queryset.order_by("-date_detection")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = AlerteMetrique.objects.all()
        context["stats"] = {
            "actives": queryset.filter(statut="ACTIVE").count(),
            "critiques": queryset.filter(niveau="CRITIQUE", statut="ACTIVE").count(),
        }

        return context


@login_required
@require_http_methods(["POST"])
def alerte_acquitter(request, pk):
    """Acquitte une alerte"""
    alerte = get_object_or_404(AlerteMetrique, pk=pk)

    commentaire = request.POST.get("commentaire", "")

    alerte.statut = "ACQUITTEE"
    alerte.acquittee_par = request.user
    alerte.date_acquittement = datetime.now()
    alerte.commentaire = commentaire
    alerte.save()

    messages.success(request, _("Alerte acquittée"))
    return redirect("analytics:alerte-list")


# ============ EXPORTS DE DONNÉES ============


@login_required
def export_donnees(request):
    """Exporte des données pour analyse externe"""

    if request.method == "POST":
        form = ExportDonneesForm(request.POST)
        if form.is_valid():
            export = form.save(commit=False)
            export.demande_par = request.user
            export.save()

            # TODO: Générer l'export asynchrone
            # from analytics.tasks import generer_export_async
            # generer_export_async.delay(export.id)

            messages.success(request, _("Export lancé"))
            return redirect("analytics:export-list")
    else:
        form = ExportDonneesForm()

    return render(request, "analytics/export_form.html", {"form": form})


class ExportDonneesListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des exports de données"""

    model = ExportDonnees
    template_name = "analytics/export_list.html"
    context_object_name = "exports"
    business_permission = 'analytics.view_rapports'

    def get_queryset(self):
        return ExportDonnees.objects.select_related("mandat", "demande_par").order_by(
            "-date_demande"
        )


@login_required
def export_telecharger(request, pk):
    """Télécharge un export"""
    export = get_object_or_404(ExportDonnees, pk=pk)

    if export.fichier:
        response = FileResponse(export.fichier.open("rb"))
        response["Content-Disposition"] = (
            f'attachment; filename="{export.nom}.{export.format_export.lower()}"'
        )
        return response

    messages.error(request, _("Fichier non trouvé"))
    return redirect("analytics:export-list")
