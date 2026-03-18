# analytics/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count, Sum, Avg, F, Max, Min
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse, FileResponse
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from decimal import Decimal
import json
import time
import logging

logger = logging.getLogger(__name__)

from core.permissions import BusinessPermissionMixin, permission_required_business
from .dashboard_service import DashboardDataService

from .models import (
    TableauBord,
    Indicateur,
    ValeurIndicateur,
    Rapport,
    PlanificationRapport,
    ComparaisonPeriode,
    AlerteMetrique,
    ExportDonnees,
    SectionRapport,
    TypeGraphiqueRapport,
    ModeleRapport,
)
from .services import RapportSectionService, GraphiqueService
from .forms import (
    TableauBordForm,
    IndicateurForm,
    RapportForm,
    PlanificationRapportForm,
    ComparaisonPeriodeForm,
    ExportDonneesForm,
)
from core.models import Mandat


# ============ HUB ANALYTICS ============


def _get_analytics_filters(request):
    """Parse les filtres communs année/mandat depuis la requête."""
    annee = request.GET.get('annee')
    if annee:
        try:
            annee = int(annee)
        except ValueError:
            annee = None

    mandat_id = request.GET.get('mandat')
    mandat = None
    if mandat_id:
        try:
            mandat = Mandat.objects.get(pk=mandat_id)
        except Mandat.DoesNotExist:
            pass

    return annee, mandat


def _get_filters_context(request):
    """Retourne le contexte commun pour les filtres."""
    annee, mandat = _get_analytics_filters(request)
    return {
        'annees': list(range(datetime.now().year, datetime.now().year - 5, -1)),
        'annee_selectionnee': annee or datetime.now().year,
        'mandats': Mandat.objects.filter(
            statut='ACTIF'
        ).select_related('client').order_by('client__raison_sociale'),
        'mandat_selectionne': mandat,
    }


class AnalyticsHubView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """
    Hub Analytics — Point d'entrée unique pour toute l'analyse.

    Onglets chargés en HTMX:
    - Vue d'ensemble (overview) — KPIs + alertes
    - Financier — CA, évolution, répartition, treemap
    - Clients — Top clients, Pareto, aging, DSO
    - Visualisations — D3.js (calendrier, sunburst, sankey, etc.)
    - Rapports — Génération + liste
    - Alertes & Exports
    """
    template_name = "analytics/hub.html"
    business_permission = 'analytics.view_tableaux_bord'

    def get_object(self):
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_filters_context(self.request))

        tab = self.request.GET.get('tab', 'overview')
        context['active_tab'] = tab

        # Charger les données de l'onglet overview inline (pas de HTMX pour le premier)
        if tab == 'overview':
            annee, mandat = _get_analytics_filters(self.request)
            service = DashboardDataService(
                user=self.request.user, mandat=mandat, annee=annee
            )
            kpis = service.get_kpis_principaux()
            context['kpis'] = kpis
            context['alertes'] = service.get_alertes_dashboard()
            # Compteurs pour les badges
            context['nb_alertes_actives'] = AlerteMetrique.objects.filter(statut='ACTIVE').count()
            context['nb_rapports'] = Rapport.objects.count()

        return context


# Ancien alias — redirige vers le hub
class DashboardExecutifView(AnalyticsHubView):
    """Rétro-compatibilité: redirige vers le Hub Analytics."""
    pass


class D3DashboardView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Dashboard des visualisations D3.js avancées (accès direct conservé)."""
    template_name = "analytics/d3_dashboard.html"
    business_permission = 'analytics.view_tableaux_bord'

    def get_object(self):
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_filters_context(self.request))
        return context


# ============ HTMX PARTIALS POUR LE HUB ============


@login_required
def hub_tab_overview(request):
    """Onglet Vue d'ensemble — KPIs + alertes."""
    annee, mandat = _get_analytics_filters(request)
    service = DashboardDataService(user=request.user, mandat=mandat, annee=annee)
    kpis = service.get_kpis_principaux()
    context = _get_filters_context(request)
    context['kpis'] = kpis
    context['alertes'] = service.get_alertes_dashboard()
    context['nb_alertes_actives'] = AlerteMetrique.objects.filter(statut='ACTIVE').count()
    context['nb_rapports'] = Rapport.objects.count()
    return render(request, "analytics/partials/tab_overview.html", context)


@login_required
def hub_tab_financier(request):
    """Onglet Financier — CA, évolution, répartition, treemap."""
    annee, mandat = _get_analytics_filters(request)
    service = DashboardDataService(user=request.user, mandat=mandat, annee=annee)
    context = _get_filters_context(request)
    context['chart_evolution_ca'] = json.dumps(service.get_evolution_ca_mensuel())
    context['chart_repartition'] = json.dumps(service.get_repartition_ca_type_prestation())
    context['chart_treemap'] = json.dumps(service.get_treemap_mandats())
    # KPIs financiers
    kpis = service.get_kpis_principaux()
    context['kpis'] = kpis
    return render(request, "analytics/partials/tab_financier.html", context)


@login_required
def hub_tab_clients(request):
    """Onglet Clients — Top clients, Pareto, aging, DSO."""
    annee, mandat = _get_analytics_filters(request)
    service = DashboardDataService(user=request.user, mandat=mandat, annee=annee)
    context = _get_filters_context(request)
    context['chart_top_clients'] = json.dumps(service.get_top_clients())
    context['chart_pareto'] = json.dumps(service.get_pareto_clients())
    context['chart_aging'] = json.dumps(service.get_aging_analysis())
    kpis = service.get_kpis_principaux()
    context['kpis'] = kpis
    return render(request, "analytics/partials/tab_clients.html", context)


@login_required
def hub_tab_visualisations(request):
    """Onglet Visualisations D3.js."""
    context = _get_filters_context(request)
    return render(request, "analytics/partials/tab_visualisations.html", context)


@login_required
def hub_tab_rapports(request):
    """Onglet Rapports — Liste + lien vers génération."""
    context = _get_filters_context(request)
    context['rapports'] = Rapport.objects.select_related(
        "mandat__client", "genere_par"
    ).order_by("-date_generation")[:20]
    context['planifications'] = PlanificationRapport.objects.select_related(
        "mandat"
    ).filter(actif=True).order_by("nom")[:10]
    context['types_rapport'] = (
        Rapport.objects.values("type_rapport")
        .annotate(count=Count("id"))
        .order_by("type_rapport")
    )
    return render(request, "analytics/partials/tab_rapports.html", context)


@login_required
def hub_tab_alertes(request):
    """Onglet Alertes & Exports."""
    user = request.user
    context = _get_filters_context(request)

    # Alertes
    alertes_qs = AlerteMetrique.objects.select_related(
        "indicateur", "mandat", "acquittee_par"
    )
    if hasattr(user, 'is_manager') and not user.is_manager():
        alertes_qs = alertes_qs.filter(
            Q(mandat__responsable=user) | Q(mandat__equipe=user)
        ).distinct()
    context['alertes_actives'] = alertes_qs.filter(statut='ACTIVE').order_by('-date_detection')[:20]
    context['alertes_stats'] = {
        'actives': alertes_qs.filter(statut='ACTIVE').count(),
        'critiques': alertes_qs.filter(statut='ACTIVE', niveau='CRITIQUE').count(),
    }

    # Exports
    context['exports'] = ExportDonnees.objects.select_related(
        "mandat", "demande_par"
    ).order_by("-date_demande")[:15]

    return render(request, "analytics/partials/tab_alertes.html", context)


@login_required
def dashboard_api_refresh(request):
    """
    API endpoint pour rafraîchir les données du dashboard en AJAX.

    Returns:
        JsonResponse: Données complètes du dashboard
    """
    annee = request.GET.get('annee')
    mandat_id = request.GET.get('mandat')

    try:
        annee = int(annee) if annee else None
    except ValueError:
        annee = None

    mandat = None
    if mandat_id:
        try:
            mandat = Mandat.objects.get(pk=mandat_id)
        except Mandat.DoesNotExist:
            pass

    service = DashboardDataService(
        user=request.user,
        mandat=mandat,
        annee=annee
    )

    data = service.get_full_dashboard_data()

    # Convertir les Decimals en float pour JSON
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decimal_to_float(item) for item in obj]
        return obj

    return JsonResponse(decimal_to_float(data))


@login_required
def rapport_preview_api(request):
    """
    API endpoint pour la preview d'un rapport avant génération.

    Retourne les données et un aperçu graphique selon le type de rapport.
    """
    from django.apps import apps
    from datetime import datetime

    type_rapport = request.GET.get('type_rapport', 'BILAN')
    mandat_id = request.GET.get('mandat_id') or request.GET.get('mandat')  # Support both names
    date_debut_str = request.GET.get('date_debut')
    date_fin_str = request.GET.get('date_fin')

    logger.info(f"Preview API appelée: type={type_rapport}, mandat_id={mandat_id}, debut={date_debut_str}, fin={date_fin_str}")

    # Parser les dates
    try:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date() if date_debut_str else None
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date() if date_fin_str else None
    except ValueError:
        date_debut = None
        date_fin = None

    # Récupérer le mandat si spécifié
    mandat = None
    if mandat_id:
        try:
            mandat = Mandat.objects.get(pk=mandat_id)
            logger.info(f"Mandat trouvé: {mandat.id} - {mandat}")
        except Mandat.DoesNotExist:
            logger.warning(f"Mandat {mandat_id} non trouvé dans la base")
    else:
        logger.info("Aucun mandat sélectionné - données globales")

    # Préparer les données selon le type de rapport
    preview_data = {
        'type': type_rapport,
        'has_data': False,
        'summary': {},
        'chart_data': None,
        'chart_type': 'bar',
        'table_preview': [],
        'warnings': [],
    }

    try:
        if type_rapport == 'BILAN':
            preview_data.update(_get_preview_bilan(mandat, date_debut, date_fin))
        elif type_rapport == 'COMPTE_RESULTATS':
            preview_data.update(_get_preview_compte_resultats(mandat, date_debut, date_fin))
        elif type_rapport == 'BALANCE':
            preview_data.update(_get_preview_balance(mandat, date_debut, date_fin))
        elif type_rapport == 'TRESORERIE':
            preview_data.update(_get_preview_tresorerie(mandat, date_debut, date_fin))
        elif type_rapport == 'TVA':
            preview_data.update(_get_preview_tva(mandat, date_debut, date_fin))
        elif type_rapport == 'EVOLUTION_CA':
            preview_data.update(_get_preview_evolution_ca(mandat, date_debut, date_fin))
        elif type_rapport == 'RENTABILITE':
            preview_data.update(_get_preview_rentabilite(mandat, date_debut, date_fin))
        elif type_rapport == 'SALAIRES':
            preview_data.update(_get_preview_salaires(mandat, date_debut, date_fin))
        elif type_rapport == 'CUSTOM':
            preview_data.update(_get_preview_custom(mandat, date_debut, date_fin))
        else:
            preview_data['warnings'].append("Type de rapport non supporté pour la preview")

        logger.debug(f"Preview data: has_data={preview_data.get('has_data')}, chart_type={preview_data.get('chart_type')}")

    except Exception as e:
        logger.exception(f"Erreur preview rapport: {e}")
        preview_data['warnings'].append(f"Erreur lors de la récupération des données: {str(e)}")

    # Convertir Decimals
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decimal_to_float(item) for item in obj]
        return obj

    return JsonResponse(decimal_to_float(preview_data))


def _get_preview_bilan(mandat, date_debut, date_fin):
    """Preview pour le bilan - avec tableau détaillé comme le PDF."""
    from django.apps import apps
    from django.db.models import Sum

    try:
        EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')
    except LookupError:
        return {'has_data': False, 'warnings': ["Module comptabilité non disponible"]}

    filters = {}
    if date_debut:
        filters['date_ecriture__gte'] = date_debut
    if date_fin:
        filters['date_ecriture__lte'] = date_fin
    if mandat:
        filters['mandat'] = mandat

    # Debug: compter les écritures avec et sans filtre mandat
    total_ecritures = EcritureComptable.objects.count()
    ecritures_filtrees = EcritureComptable.objects.filter(**filters).count()
    logger.info(f"BILAN - Mandat: {mandat}, Filters: {filters}")
    logger.info(f"BILAN - Total écritures en base: {total_ecritures}, Écritures filtrées: {ecritures_filtrees}")

    # Si mandat spécifié, vérifier combien d'écritures existent pour ce mandat
    if mandat:
        ecritures_mandat = EcritureComptable.objects.filter(mandat=mandat).count()
        logger.info(f"BILAN - Écritures pour le mandat {mandat.id}: {ecritures_mandat}")

        # Lister les mandats disponibles avec écritures
        from django.db.models import Count
        mandats_avec_ecritures = EcritureComptable.objects.values('mandat__id', 'mandat__numero').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        logger.info(f"BILAN - Top 5 mandats avec écritures: {list(mandats_avec_ecritures)}")

    # Récupérer les totaux par classe
    ecritures_classe = EcritureComptable.objects.filter(**filters).values(
        'compte__classe'
    ).annotate(
        total_debit=Sum('montant_debit'),
        total_credit=Sum('montant_credit')
    )

    logger.info(f"BILAN - Résultat par classe: {list(ecritures_classe)}")

    actif_total = Decimal('0')
    passif_total = Decimal('0')

    for e in ecritures_classe:
        classe = e['compte__classe']
        logger.debug(f"BILAN - Classe: {classe} (type: {type(classe)})")
        solde = (e['total_debit'] or Decimal('0')) - (e['total_credit'] or Decimal('0'))
        # Note: classe est un IntegerField, donc on compare avec des entiers
        if classe in [1, 2]:
            actif_total += abs(solde)
        elif classe in [3, 4]:
            passif_total += abs(solde)

    # Récupérer les détails par compte (top 5 actif + top 5 passif)
    ecritures_detail = EcritureComptable.objects.filter(**filters).values(
        'compte__numero', 'compte__libelle', 'compte__classe'
    ).annotate(
        total_debit=Sum('montant_debit'),
        total_credit=Sum('montant_credit')
    ).order_by('-total_debit')[:10]

    table_preview = []
    for e in ecritures_detail:
        classe = e['compte__classe'] or ''
        debit = e['total_debit'] or Decimal('0')
        credit = e['total_credit'] or Decimal('0')
        solde = debit - credit
        type_compte = 'Actif' if classe in [1, 2] else 'Passif' if classe in [3, 4] else 'Autre'
        table_preview.append({
            'Compte': e['compte__numero'],
            'Libellé': (e['compte__libelle'] or '-')[:25],
            'Type': type_compte,
            'Solde': float(abs(solde)),
        })

    has_data = actif_total > 0 or passif_total > 0
    ecart = actif_total - passif_total

    return {
        'has_data': has_data,
        'summary': {
            'Total Actif': actif_total,
            'Total Passif': passif_total,
            'Écart': ecart,
        },
        'chart_type': 'donut',
        'chart_data': {
            'labels': ['Actif', 'Passif'],
            'series': [float(actif_total), float(passif_total)],
        },
        'table_preview': table_preview if table_preview else None,
        'warnings': [] if has_data else ["Aucune donnée comptable pour cette période"],
    }


def _get_preview_compte_resultats(mandat, date_debut, date_fin):
    """Preview pour le compte de résultats - avec détails comme le PDF."""
    from django.apps import apps
    from django.db.models import Sum

    try:
        EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')
    except LookupError:
        return {'has_data': False, 'warnings': ["Module comptabilité non disponible"]}

    filters = {}
    if date_debut:
        filters['date_ecriture__gte'] = date_debut
    if date_fin:
        filters['date_ecriture__lte'] = date_fin
    if mandat:
        filters['mandat'] = mandat

    # Totaux par classe
    ecritures = EcritureComptable.objects.filter(**filters).values(
        'compte__classe'
    ).annotate(
        total_debit=Sum('montant_debit'),
        total_credit=Sum('montant_credit')
    )

    produits_total = Decimal('0')
    charges_total = Decimal('0')

    for e in ecritures:
        classe = e['compte__classe'] or ''
        debit = e['total_debit'] or Decimal('0')
        credit = e['total_credit'] or Decimal('0')
        # Classification selon le plan comptable suisse PME:
        # Classe 3 = Produits d'exploitation, Classe 7 = Produits hors exploitation
        # Classes 4, 5, 6, 8 = Charges
        if classe in [3, 7]:  # Produits (exploitation + hors exploitation)
            produits_total += credit - debit
        elif classe in [4, 5, 6, 8]:  # Charges
            charges_total += debit - credit

    resultat = produits_total - charges_total
    has_data = produits_total > 0 or charges_total > 0

    # Top 5 produits et top 5 charges
    table_preview = []

    # Top produits
    top_produits = EcritureComptable.objects.filter(
        **filters,
        compte__classe__in=[3, 7]  # Produits (exploitation + hors exploitation)
    ).values(
        'compte__numero', 'compte__libelle'
    ).annotate(
        total=Sum('montant_credit') - Sum('montant_debit')
    ).order_by('-total')[:5]

    for p in top_produits:
        table_preview.append({
            'Compte': p['compte__numero'],
            'Libellé': (p['compte__libelle'] or '-')[:25],
            'Type': 'Produit',
            'Montant': float(p['total'] or 0),
        })

    # Top charges
    top_charges = EcritureComptable.objects.filter(
        **filters,
        compte__classe__in=[4, 5, 6, 8]  # Charges (toutes les catégories)
    ).values(
        'compte__numero', 'compte__libelle'
    ).annotate(
        total=Sum('montant_debit') - Sum('montant_credit')
    ).order_by('-total')[:5]

    for c in top_charges:
        table_preview.append({
            'Compte': c['compte__numero'],
            'Libellé': (c['compte__libelle'] or '-')[:25],
            'Type': 'Charge',
            'Montant': float(c['total'] or 0),
        })

    # Calcul de la marge
    marge_nette = (resultat / produits_total * 100) if produits_total > 0 else 0

    return {
        'has_data': has_data,
        'summary': {
            'Total Produits': produits_total,
            'Total Charges': charges_total,
            'Résultat': resultat,
            'Marge nette': f"{marge_nette:.1f}%",
        },
        'chart_type': 'bar',
        'chart_data': {
            'categories': ['Produits', 'Charges', 'Résultat'],
            'series': [{
                'name': 'Montant',
                'data': [float(produits_total), float(charges_total), float(resultat)]
            }],
        },
        'table_preview': table_preview if table_preview else None,
        'warnings': [] if has_data else ["Aucune donnée pour cette période"],
    }


def _get_preview_balance(mandat, date_debut, date_fin):
    """Preview pour la balance."""
    from django.apps import apps
    from django.db.models import Sum

    try:
        EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')
    except LookupError:
        return {'has_data': False, 'warnings': ["Module comptabilité non disponible"]}

    filters = {}
    if date_debut:
        filters['date_ecriture__gte'] = date_debut
    if date_fin:
        filters['date_ecriture__lte'] = date_fin
    if mandat:
        filters['mandat'] = mandat

    ecritures = EcritureComptable.objects.filter(**filters).values(
        'compte__numero', 'compte__libelle'
    ).annotate(
        total_debit=Sum('montant_debit'),
        total_credit=Sum('montant_credit')
    ).order_by('compte__numero')[:10]  # Top 10 pour preview

    table_preview = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')

    for e in ecritures:
        debit = e['total_debit'] or Decimal('0')
        credit = e['total_credit'] or Decimal('0')
        total_debit += debit
        total_credit += credit
        table_preview.append({
            'numero': e['compte__numero'],
            'libelle': e['compte__libelle'][:30] if e['compte__libelle'] else '-',
            'debit': debit,
            'credit': credit,
            'solde': debit - credit,
        })

    has_data = len(table_preview) > 0

    return {
        'has_data': has_data,
        'summary': {
            'Nombre de comptes': len(table_preview),
            'Total Débit': total_debit,
            'Total Crédit': total_credit,
        },
        'table_preview': table_preview,
        'chart_type': 'bar',
        'chart_data': {
            'categories': [e['numero'] for e in table_preview[:8]],
            'series': [{
                'name': 'Solde',
                'data': [float(e['solde']) for e in table_preview[:8]]
            }],
        },
        'warnings': [] if has_data else ["Aucune écriture pour cette période"],
    }


def _get_preview_tresorerie(mandat, date_debut, date_fin):
    """Preview pour la trésorerie - avec détails comme le PDF."""
    from django.apps import apps
    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    try:
        Facture = apps.get_model('facturation', 'Facture')
        Paiement = apps.get_model('facturation', 'Paiement')
        EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')
    except LookupError:
        return {'has_data': False, 'warnings': ["Module facturation ou comptabilité non disponible"]}

    # Récupérer les paiements sur la période (table Paiement)
    paiement_filters = {}
    if date_debut:
        paiement_filters['date_paiement__gte'] = date_debut
    if date_fin:
        paiement_filters['date_paiement__lte'] = date_fin
    if mandat:
        paiement_filters['facture__mandat'] = mandat

    paiements = Paiement.objects.filter(**paiement_filters)
    encaissements = paiements.aggregate(
        total=Coalesce(Sum('montant'), Decimal('0'))
    )['total'] or Decimal('0')
    nb_paiements = paiements.count()

    # Calcul du délai moyen de paiement (date_paiement - date_emission de la facture)
    delai_moyen = 0
    paiements_avec_dates = paiements.select_related('facture').filter(
        facture__date_emission__isnull=False
    )[:100]
    if paiements_avec_dates.exists():
        delais = []
        for p in paiements_avec_dates:
            if p.date_paiement and p.facture.date_emission:
                delai = (p.date_paiement - p.facture.date_emission).days
                if delai >= 0:
                    delais.append(delai)
        delai_moyen = int(sum(delais) / len(delais)) if delais else 0

    # Factures payées (pour compter le nombre)
    facture_filters = {'statut__in': ['PAYEE', 'PARTIELLEMENT_PAYEE']}
    if date_debut:
        facture_filters['date_paiement_complet__gte'] = date_debut
    if date_fin:
        facture_filters['date_paiement_complet__lte'] = date_fin
    if mandat:
        facture_filters['mandat'] = mandat
    nb_factures_payees = Facture.objects.filter(**facture_filters).count()

    # Si pas de paiements directs, récupérer via montant_paye des factures
    if encaissements == 0:
        factures_avec_paiement = Facture.objects.filter(
            statut__in=['PAYEE', 'PARTIELLEMENT_PAYEE'],
            montant_paye__gt=0
        )
        if date_debut:
            factures_avec_paiement = factures_avec_paiement.filter(date_emission__gte=date_debut)
        if date_fin:
            factures_avec_paiement = factures_avec_paiement.filter(date_emission__lte=date_fin)
        if mandat:
            factures_avec_paiement = factures_avec_paiement.filter(mandat=mandat)

        encaissements = factures_avec_paiement.aggregate(
            total=Coalesce(Sum('montant_paye'), Decimal('0'))
        )['total'] or Decimal('0')
        nb_factures_payees = factures_avec_paiement.count()

    # Décaissements (charges comptables)
    ecriture_filters = {'compte__classe__in': [4, 5, 6, 8]}  # Charges selon plan comptable suisse PME
    if date_debut:
        ecriture_filters['date_ecriture__gte'] = date_debut
    if date_fin:
        ecriture_filters['date_ecriture__lte'] = date_fin
    if mandat:
        ecriture_filters['mandat'] = mandat

    charges_data = EcritureComptable.objects.filter(**ecriture_filters).aggregate(
        total_debit=Sum('montant_debit'),
        total_credit=Sum('montant_credit')
    )
    decaissements = (charges_data['total_debit'] or Decimal('0')) - (charges_data['total_credit'] or Decimal('0'))
    if decaissements <= 0:
        decaissements = encaissements * Decimal('0.7')  # Fallback estimation

    solde = encaissements - decaissements
    has_data = encaissements > 0 or decaissements > 0

    return {
        'has_data': has_data,
        'summary': {
            'Encaissements': encaissements,
            'Factures payées': nb_factures_payees,
            'Décaissements': decaissements,
            'Solde net': solde,
            'Délai moyen paiement': f"{delai_moyen}j" if delai_moyen > 0 else 'N/A',
        },
        'chart_type': 'bar',
        'chart_data': {
            'categories': ['Encaissements', 'Décaissements', 'Solde net'],
            'series': [{
                'name': 'Trésorerie',
                'data': [float(encaissements), float(decaissements), float(solde)]
            }],
        },
        'table_preview': [
            {'Indicateur': 'Encaissements (paiements reçus)', 'Valeur': float(encaissements)},
            {'Indicateur': 'Nombre de factures payées', 'Valeur': nb_factures_payees},
            {'Indicateur': 'Décaissements (charges)', 'Valeur': float(decaissements)},
            {'Indicateur': 'Solde net de trésorerie', 'Valeur': float(solde)},
            {'Indicateur': 'Délai moyen de paiement', 'Valeur': f"{delai_moyen} jours" if delai_moyen > 0 else 'N/A'},
        ],
        'warnings': [] if has_data else ["Aucune donnée de trésorerie pour cette période"],
    }


def _get_preview_tva(mandat, date_debut, date_fin):
    """Preview pour la TVA - avec détails comme le PDF."""
    from django.apps import apps
    from django.db.models import Sum, Count

    try:
        Facture = apps.get_model('facturation', 'Facture')
    except LookupError:
        return {'has_data': False, 'warnings': ["Module facturation non disponible"]}

    # Essayer de récupérer les opérations TVA si disponibles
    try:
        OperationTVA = apps.get_model('tva', 'OperationTVA')
        has_tva_module = True
    except LookupError:
        has_tva_module = False

    filters = {'statut__in': ['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']}
    if date_debut:
        filters['date_emission__gte'] = date_debut
    if date_fin:
        filters['date_emission__lte'] = date_fin
    if mandat:
        filters['mandat'] = mandat

    factures = Facture.objects.filter(**filters)
    data = factures.aggregate(
        ca_ht=Sum('montant_ht'),
        tva=Sum('montant_tva'),
        count=Count('id')
    )

    ca_ht = data['ca_ht'] or Decimal('0')
    tva_collectee = data['tva'] or Decimal('0')
    nb_factures = data['count'] or 0

    # Si module TVA disponible, récupérer la TVA déductible
    if has_tva_module:
        tva_filters = {}
        if date_debut:
            tva_filters['date_operation__gte'] = date_debut
        if date_fin:
            tva_filters['date_operation__lte'] = date_fin
        if mandat:
            tva_filters['mandat'] = mandat

        try:
            tva_data = OperationTVA.objects.filter(**tva_filters).aggregate(
                deductible=Sum('montant_tva', filter={'type_operation': 'ACHAT'}) if hasattr(OperationTVA, 'type_operation') else None
            )
            tva_deductible = tva_data.get('deductible') or tva_collectee * Decimal('0.6')
        except Exception:
            tva_deductible = tva_collectee * Decimal('0.6')
    else:
        tva_deductible = tva_collectee * Decimal('0.6')  # Estimation

    tva_nette = tva_collectee - tva_deductible
    taux_moyen = float((tva_collectee / ca_ht) * 100) if ca_ht > 0 else 0

    return {
        'has_data': ca_ht > 0,
        'summary': {
            'CA HT': ca_ht,
            'Nombre de factures': nb_factures,
            'TVA collectée': tva_collectee,
            'TVA déductible': tva_deductible,
            'TVA nette à payer': tva_nette,
            'Taux moyen': f"{taux_moyen:.1f}%",
        },
        'chart_type': 'donut',
        'chart_data': {
            'labels': ['TVA collectée', 'TVA déductible'],
            'series': [float(tva_collectee), float(tva_deductible)],
        },
        'table_preview': [
            {'Élément': 'Chiffre d\'affaires HT', 'Montant': float(ca_ht)},
            {'Élément': 'TVA collectée (ventes)', 'Montant': float(tva_collectee)},
            {'Élément': 'TVA déductible (achats)', 'Montant': float(tva_deductible)},
            {'Élément': 'TVA nette à payer', 'Montant': float(tva_nette)},
        ],
        'warnings': [] if ca_ht > 0 else ["Aucune facture pour cette période"],
    }


def _get_preview_evolution_ca(mandat, date_debut, date_fin):
    """Preview pour l'évolution du CA - avec analyse comme le PDF."""
    from django.apps import apps
    from django.db.models import Sum
    from django.db.models.functions import TruncMonth

    try:
        Facture = apps.get_model('facturation', 'Facture')
    except LookupError:
        return {'has_data': False, 'warnings': ["Module facturation non disponible"]}

    filters = {'statut__in': ['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']}
    if date_debut:
        filters['date_emission__gte'] = date_debut
    if date_fin:
        filters['date_emission__lte'] = date_fin
    if mandat:
        filters['mandat'] = mandat

    mois_noms = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']

    factures = Facture.objects.filter(**filters).annotate(
        mois=TruncMonth('date_emission')
    ).values('mois').annotate(
        ca=Sum('montant_ht')
    ).order_by('mois')

    categories = []
    data_series = []
    mois_data = []
    total_ca = Decimal('0')
    prev_ca = None

    for f in factures:
        if f['mois']:
            mois_label = f"{mois_noms[f['mois'].month - 1]} {f['mois'].year}"
            categories.append(mois_label)
            ca = f['ca'] or Decimal('0')
            data_series.append(float(ca))
            total_ca += ca

            # Calcul évolution
            evol = 0
            if prev_ca and prev_ca > 0:
                evol = float((ca - prev_ca) / prev_ca * 100)

            mois_data.append({
                'Mois': mois_label,
                'CA HT': float(ca),
                'Évolution': f"{evol:+.1f}%" if prev_ca else '-',
            })
            prev_ca = ca

    has_data = len(categories) > 0

    # Analyse
    if has_data:
        moyenne = total_ca / len(categories)
        ca_max = max(data_series)
        ca_min = min(data_series)
        mois_max = categories[data_series.index(ca_max)]
        mois_min = categories[data_series.index(ca_min)]

        # Tendance
        if len(data_series) >= 2:
            premiere_moitie = sum(data_series[:len(data_series)//2]) / max(1, len(data_series)//2)
            deuxieme_moitie = sum(data_series[len(data_series)//2:]) / max(1, len(data_series) - len(data_series)//2)
            tendance = ((deuxieme_moitie - premiere_moitie) / premiere_moitie * 100) if premiere_moitie > 0 else 0
        else:
            tendance = 0
    else:
        moyenne = Decimal('0')
        mois_max = '-'
        mois_min = '-'
        ca_max = 0
        ca_min = 0
        tendance = 0

    return {
        'has_data': has_data,
        'summary': {
            'CA Total': total_ca,
            'Moyenne mensuelle': moyenne,
            'Meilleur mois': mois_max,
            'Tendance': f"{tendance:+.1f}%" if tendance != 0 else 'Stable',
        },
        'chart_type': 'area',
        'chart_data': {
            'categories': categories,
            'series': [{
                'name': 'Chiffre d\'affaires',
                'data': data_series
            }],
        },
        'table_preview': mois_data if mois_data else None,
        'warnings': [] if has_data else ["Aucune facture pour cette période"],
    }


def _get_preview_rentabilite(mandat, date_debut, date_fin):
    """Preview pour la rentabilité - utilise les mêmes données que le PDF."""
    from django.apps import apps
    from django.db.models import Sum

    try:
        Facture = apps.get_model('facturation', 'Facture')
        EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')
    except LookupError:
        return {'has_data': False, 'warnings': ["Module facturation ou comptabilité non disponible"]}

    # Filtres pour les factures
    facture_filters = {'statut__in': ['EMISE', 'ENVOYEE', 'PAYEE', 'PARTIELLEMENT_PAYEE']}
    if date_debut:
        facture_filters['date_emission__gte'] = date_debut
    if date_fin:
        facture_filters['date_emission__lte'] = date_fin
    if mandat:
        facture_filters['mandat'] = mandat

    # Calculer le CA
    ca_data = Facture.objects.filter(**facture_filters).aggregate(ca_total=Sum('montant_ht'))
    ca_total = ca_data['ca_total'] or Decimal('0')

    if ca_total == 0:
        return {
            'has_data': False,
            'summary': {},
            'warnings': ["Aucune donnée de chiffre d'affaires pour cette période"],
        }

    # Filtres pour les écritures comptables
    ecriture_filters = {}
    if date_debut:
        ecriture_filters['date_ecriture__gte'] = date_debut
    if date_fin:
        ecriture_filters['date_ecriture__lte'] = date_fin
    if mandat:
        ecriture_filters['mandat'] = mandat

    # Récupérer les charges (classes 4, 5, 6, 8 selon plan comptable suisse PME)
    charges_data = EcritureComptable.objects.filter(
        **ecriture_filters,
        compte__classe__in=[4, 5, 6, 8]
    ).aggregate(
        total_debit=Sum('montant_debit'),
        total_credit=Sum('montant_credit')
    )
    total_charges = (charges_data['total_debit'] or Decimal('0')) - (charges_data['total_credit'] or Decimal('0'))

    # Récupérer les produits (classes 3, 7 selon plan comptable suisse PME)
    produits_data = EcritureComptable.objects.filter(
        **ecriture_filters,
        compte__classe__in=[3, 7]
    ).aggregate(
        total_debit=Sum('montant_debit'),
        total_credit=Sum('montant_credit')
    )
    total_produits = (produits_data['total_credit'] or Decimal('0')) - (produits_data['total_debit'] or Decimal('0'))

    # Calculs
    marge_brute_montant = ca_total - total_charges if ca_total > 0 else Decimal('0')
    marge_brute_pct = float((marge_brute_montant / ca_total) * 100) if ca_total > 0 else 0

    resultat_net = total_produits - total_charges
    taux_rentabilite = float((resultat_net / total_produits) * 100) if total_produits > 0 else 0

    # Estimation du taux de facturation
    if date_debut and date_fin:
        nb_mois = max(1, (date_fin - date_debut).days // 30)
    else:
        nb_mois = 1
    ca_mensuel_moyen = float(ca_total / nb_mois)
    objectif_mensuel = 100000
    taux_facturation = min(100, (ca_mensuel_moyen / objectif_mensuel) * 100) if objectif_mensuel > 0 else 0

    # Heures facturées (estimation)
    heures_estimees = int(float(ca_total) / 150) if ca_total > 0 else 0

    return {
        'has_data': True,
        'summary': {
            'CA HT': ca_total,
            'Charges': total_charges,
            'Marge brute': marge_brute_montant,
            'Résultat net': resultat_net,
            'Taux de marge': f"{marge_brute_pct:.1f}%",
            'Heures facturées (est.)': heures_estimees,
        },
        'chart_type': 'bar',
        'chart_data': {
            'categories': ['CA HT', 'Charges', 'Marge brute', 'Résultat'],
            'series': [{
                'name': 'Montants',
                'data': [float(ca_total), float(total_charges), float(marge_brute_montant), float(resultat_net)]
            }],
        },
        # Tableau de synthèse pour la preview
        'table_preview': [
            {'Indicateur': 'Marge brute', 'Valeur': f"{marge_brute_pct:.1f}%"},
            {'Indicateur': 'Taux de rentabilité', 'Valeur': f"{taux_rentabilite:.1f}%"},
            {'Indicateur': 'Taux de facturation', 'Valeur': f"{taux_facturation:.1f}%"},
            {'Indicateur': 'Heures facturées (est.)', 'Valeur': f"{heures_estimees}h"},
        ],
        'warnings': [],
    }


def _get_preview_salaires(mandat, date_debut, date_fin):
    """Preview pour les salaires - avec détail par employé comme le PDF."""
    from django.apps import apps
    from django.db.models import Sum, Q

    try:
        FicheSalaire = apps.get_model('salaires', 'FicheSalaire')
    except LookupError:
        return {'has_data': False, 'warnings': ["Module salaires non disponible"]}

    # Le modèle FicheSalaire utilise 'mois' et 'annee' au lieu de date_debut/date_fin
    filters = Q()
    if date_debut and date_fin:
        filters &= Q(annee__gte=date_debut.year, annee__lte=date_fin.year)
        if date_debut.year == date_fin.year:
            filters &= Q(mois__gte=date_debut.month, mois__lte=date_fin.month)
    elif date_debut:
        filters &= Q(annee__gte=date_debut.year)
    elif date_fin:
        filters &= Q(annee__lte=date_fin.year)

    if mandat:
        filters &= Q(employe__mandat=mandat)

    fiches = FicheSalaire.objects.filter(filters).select_related('employe')

    if not fiches.exists():
        return {
            'has_data': False,
            'summary': {},
            'warnings': ["Aucune fiche de salaire pour cette période"],
        }

    totaux = fiches.aggregate(
        total_brut=Sum('salaire_brut_total'),
        total_charges=Sum('total_cotisations_employe'),
        total_net=Sum('salaire_net'),
    )

    total_brut = totaux['total_brut'] or Decimal('0')
    total_charges = totaux['total_charges'] or Decimal('0')
    total_net = totaux['total_net'] or Decimal('0')
    nb_fiches = fiches.count()

    # Détail par employé (top 10)
    table_preview = []
    employes_data = fiches.values('employe__id').annotate(
        brut=Sum('salaire_brut_total'),
        charges=Sum('total_cotisations_employe'),
        net=Sum('salaire_net')
    ).order_by('-brut')[:10]

    for i, emp in enumerate(employes_data, 1):
        table_preview.append({
            'N°': i,
            'Brut': float(emp['brut'] or 0),
            'Charges': float(emp['charges'] or 0),
            'Net': float(emp['net'] or 0),
        })

    # Statistiques
    salaire_moyen = float(total_brut / nb_fiches) if nb_fiches > 0 else 0
    taux_charges = float((total_charges / total_brut) * 100) if total_brut > 0 else 0

    return {
        'has_data': True,
        'summary': {
            'Nombre de fiches': nb_fiches,
            'Total brut': total_brut,
            'Charges sociales': total_charges,
            'Total net': total_net,
            'Salaire moyen': salaire_moyen,
            'Taux de charges': f"{taux_charges:.1f}%",
        },
        'chart_type': 'donut',
        'chart_data': {
            'labels': ['Salaires nets', 'Charges sociales'],
            'series': [float(total_net), float(total_charges)],
        },
        'table_preview': table_preview if table_preview else None,
        'warnings': [],
    }


def _get_preview_custom(mandat, date_debut, date_fin):
    """Preview pour un rapport personnalisé."""
    from django.apps import apps
    from django.db.models import Sum, Count

    # Pour un rapport personnalisé, on affiche un résumé général
    summary = {}
    has_data = False

    try:
        EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')
        filters = {}
        if date_debut:
            filters['date_ecriture__gte'] = date_debut
        if date_fin:
            filters['date_ecriture__lte'] = date_fin
        if mandat:
            filters['mandat'] = mandat

        ecritures_count = EcritureComptable.objects.filter(**filters).count()
        if ecritures_count > 0:
            summary['Écritures comptables'] = ecritures_count
            has_data = True
    except LookupError:
        pass

    try:
        Facture = apps.get_model('facturation', 'Facture')
        filters = {}
        if date_debut:
            filters['date_emission__gte'] = date_debut
        if date_fin:
            filters['date_emission__lte'] = date_fin
        if mandat:
            filters['mandat'] = mandat

        factures_data = Facture.objects.filter(**filters).aggregate(
            count=Count('id'),
            total=Sum('montant_ht')
        )
        if factures_data['count'] > 0:
            summary['Factures'] = factures_data['count']
            summary['CA HT'] = factures_data['total'] or Decimal('0')
            has_data = True
    except LookupError:
        pass

    return {
        'has_data': has_data,
        'summary': summary,
        'chart_type': 'bar',
        'chart_data': {
            'categories': list(summary.keys())[:4],
            'series': [{
                'name': 'Valeur',
                'data': [float(v) if isinstance(v, (int, float, Decimal)) else 0 for v in list(summary.values())[:4]]
            }],
        } if has_data else None,
        'warnings': [] if has_data else ["Aucune donnée disponible pour cette période"],
    }


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

        # Filtres disponibles
        context['annees'] = list(range(datetime.now().year, datetime.now().year - 5, -1))

        # Paramètres de filtrage
        annee = self.request.GET.get('annee')
        if annee:
            try:
                context['annee_selectionnee'] = int(annee)
            except ValueError:
                context['annee_selectionnee'] = datetime.now().year
        else:
            context['annee_selectionnee'] = datetime.now().year

        context['periode'] = self.request.GET.get('periode', 'annee')

        # Calculer les valeurs des indicateurs selon la configuration
        kpi_values = {}

        # Si la configuration contient des widgets, essayer de calculer leurs métriques
        if tableau.configuration and 'widgets' in tableau.configuration:
            try:
                from .services import KPICalculator
                calculator = KPICalculator()

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
            except ImportError:
                # services.py n'existe pas encore, on utilise les données de démo dans le template
                pass

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


class TableauBordUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un tableau de bord"""

    model = TableauBord
    form_class = TableauBordForm
    template_name = "analytics/tableau_bord_form.html"
    business_permission = 'analytics.view_tableaux_bord'

    def get_success_url(self):
        return reverse_lazy("analytics:tableau-bord-detail", kwargs={"pk": self.object.pk})

    def get_queryset(self):
        # Seul le propriétaire ou un superadmin peut modifier
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(proprietaire=self.request.user)
        return qs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, _("Tableau de bord modifié avec succès"))
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Vérifier si l'email est configuré
        try:
            from mailing.models import ConfigurationEmail
            email_configured = ConfigurationEmail.objects.filter(
                type_config='SMTP',
                actif=True
            ).exists()
        except Exception:
            email_configured = False

        context['email_configured'] = email_configured
        return context


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
@require_http_methods(["POST"])
def rapport_regenerer(request, pk):
    """Régénère un rapport existant (en cas d'erreur ou blocage)."""
    from analytics.tasks import (
        _generer_pdf, _generer_excel, _generer_csv, _generer_html
    )
    from django.core.files.base import ContentFile

    rapport = get_object_or_404(Rapport, pk=pk)
    start_time = time.time()

    try:
        # Générer le contenu selon le format
        if rapport.format_fichier == 'PDF':
            content, filename, nb_pages = _generer_pdf(rapport)
            rapport.nombre_pages = nb_pages
        elif rapport.format_fichier in ['EXCEL', 'XLSX']:
            content, filename = _generer_excel(rapport)
        elif rapport.format_fichier == 'CSV':
            content, filename = _generer_csv(rapport)
        elif rapport.format_fichier == 'HTML':
            content, filename = _generer_html(rapport)
        else:
            raise ValueError(f"Format non supporté: {rapport.format_fichier}")

        # Sauvegarder
        rapport.fichier.save(filename, ContentFile(content))
        rapport.taille_fichier = len(content)
        rapport.statut = 'TERMINE'
        rapport.duree_generation_secondes = int(time.time() - start_time)
        rapport.parametres.pop('erreur', None)  # Supprimer l'erreur précédente
        rapport.save()

        messages.success(request, _("Rapport régénéré avec succès."))

        # Retourner le fichier directement
        def file_iterator(content, chunk_size=8192):
            if isinstance(content, bytes):
                for i in range(0, len(content), chunk_size):
                    yield content[i:i + chunk_size]
            else:
                yield content

        response = StreamingHttpResponse(file_iterator(content))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(content)
        return response

    except Exception as e:
        logger.exception(f"Erreur régénération rapport {pk}")
        rapport.statut = 'ERREUR'
        rapport.parametres['erreur'] = str(e)
        rapport.save()
        messages.error(request, _("Erreur: %(error)s") % {'error': str(e)})
        return redirect("analytics:rapport-detail", pk=pk)


@login_required
@require_http_methods(["POST"])
def rapport_envoyer_email(request, pk):
    """Envoie un rapport par email"""
    rapport = get_object_or_404(Rapport, pk=pk)

    # Vérifier que le rapport est prêt
    if rapport.statut != 'TERMINE' or not rapport.fichier:
        messages.error(request, _("Ce rapport n'est pas prêt pour l'envoi."))
        return redirect("analytics:rapport-detail", pk=pk)

    # Récupérer les emails
    emails_str = request.POST.get('emails', '').strip()
    if not emails_str:
        messages.error(request, _("Veuillez saisir au moins une adresse email."))
        return redirect("analytics:rapport-detail", pk=pk)

    # Parser les emails (séparés par virgules)
    emails = [e.strip() for e in emails_str.split(',') if e.strip()]
    if not emails:
        messages.error(request, _("Aucune adresse email valide trouvée."))
        return redirect("analytics:rapport-detail", pk=pk)

    # Vérifier la configuration email
    try:
        from mailing.models import ConfigurationEmail
        config = ConfigurationEmail.objects.filter(
            type_config='SMTP',
            actif=True
        ).first()

        if not config:
            messages.error(
                request,
                _("Aucune configuration email active trouvée. Veuillez d'abord configurer les paramètres email.")
            )
            return redirect("analytics:rapport-detail", pk=pk)

    except Exception as e:
        messages.error(request, _("Erreur de configuration email: %(error)s") % {'error': str(e)})
        return redirect("analytics:rapport-detail", pk=pk)

    # Message personnalisé
    message_perso = request.POST.get('message', '').strip()

    # Envoyer l'email via Celery
    try:
        from analytics.tasks import envoyer_rapport_email_async
        envoyer_rapport_email_async.delay(
            rapport_id=str(rapport.id),
            destinataires=emails,
            message_personnalise=message_perso,
            expediteur_id=str(request.user.id)
        )

        # Mettre à jour le rapport
        rapport.envoi_email = True
        rapport.destinataires = emails
        rapport.save(update_fields=['envoi_email', 'destinataires'])

        messages.success(
            request,
            _("Le rapport est en cours d'envoi à %(count)d destinataire(s).") % {'count': len(emails)}
        )

    except Exception as e:
        messages.error(request, _("Erreur lors de l'envoi: %(error)s") % {'error': str(e)})

    return redirect("analytics:rapport-detail", pk=pk)


@login_required
def rapport_generer(request):
    """
    Génère un nouveau rapport avec StreamingHttpResponse.

    Le rapport est généré de manière synchrone et retourné directement
    à l'utilisateur comme fichier téléchargeable.
    """
    from analytics.tasks import (
        _generer_pdf, _generer_excel, _generer_csv, _generer_html,
        envoyer_rapport_email_async
    )

    if request.method == "POST":
        form = RapportForm(request.POST)
        if form.is_valid():
            start_time = time.time()
            logger.info(f"Début génération rapport: {form.cleaned_data.get('nom')}")

            rapport = form.save(commit=False)
            rapport.genere_par = request.user
            rapport.statut = "EN_COURS"

            # Récupérer les paramètres du formulaire
            rapport.parametres = form.cleaned_data.get('parametres', {})

            # Gérer l'envoi par email (sera fait après téléchargement)
            destinataires = form.cleaned_data.get('destinataires_list', [])
            if destinataires:
                rapport.envoi_email = True
                rapport.destinataires = destinataires

            rapport.save()
            logger.info(f"Rapport {rapport.id} créé en base de données")

            # Créer les sections du rapport à partir des données JSON
            sections_data = form.cleaned_data.get('sections', [])
            logger.info(f"Nombre de sections à créer: {len(sections_data)}")
            for ordre, section_data in enumerate(sections_data):
                section = SectionRapport(
                    rapport=rapport,
                    type_section=section_data.get('type_section', 'texte'),
                    contenu_texte=section_data.get('contenu_texte', ''),
                    visible=section_data.get('visible', True),
                    ordre=ordre * 10,
                    config=section_data.get('config', {})
                )
                # Associer le type de graphique si présent
                type_graphique_data = section_data.get('type_graphique')
                if type_graphique_data and section_data.get('type_section') == 'graphique':
                    code_graphique = section_data.get('config', {}).get('code_graphique')
                    if code_graphique:
                        try:
                            section.type_graphique = TypeGraphiqueRapport.objects.get(code=code_graphique)
                        except TypeGraphiqueRapport.DoesNotExist:
                            pass
                section.save()

            try:
                # Générer le contenu selon le format - SYNCHRONE
                logger.info(f"Début génération {rapport.format_fichier} pour rapport {rapport.id}")
                if rapport.format_fichier == 'PDF':
                    content, filename, nb_pages = _generer_pdf(rapport)
                    rapport.nombre_pages = nb_pages
                    content_type = 'application/pdf'
                    logger.info(f"PDF généré: {len(content)} bytes, {nb_pages} pages")
                elif rapport.format_fichier in ['EXCEL', 'XLSX']:
                    content, filename = _generer_excel(rapport)
                    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                elif rapport.format_fichier == 'CSV':
                    content, filename = _generer_csv(rapport)
                    content_type = 'text/csv; charset=utf-8'
                elif rapport.format_fichier == 'HTML':
                    content, filename = _generer_html(rapport)
                    content_type = 'text/html; charset=utf-8'
                else:
                    raise ValueError(f"Format non supporté: {rapport.format_fichier}")

                # Mettre à jour le rapport
                from django.core.files.base import ContentFile
                rapport.fichier.save(filename, ContentFile(content))
                rapport.taille_fichier = len(content)
                rapport.statut = 'TERMINE'
                rapport.duree_generation_secondes = int(time.time() - start_time)
                rapport.save()

                logger.info(f"Rapport {rapport.nom} généré avec succès en {rapport.duree_generation_secondes}s")

                # Envoyer par email si demandé (async via Celery - seul cas vraiment async)
                if rapport.envoi_email and rapport.destinataires:
                    envoyer_rapport_email_async.delay(
                        rapport_id=str(rapport.id),
                        destinataires=rapport.destinataires,
                        message_personnalise='',
                        expediteur_id=str(request.user.id)
                    )
                    messages.info(
                        request,
                        _("Le rapport sera également envoyé par email aux destinataires spécifiés.")
                    )

                # Retourner directement le fichier via StreamingHttpResponse
                def file_iterator(content, chunk_size=8192):
                    """Générateur pour streamer le contenu par morceaux."""
                    if isinstance(content, bytes):
                        for i in range(0, len(content), chunk_size):
                            yield content[i:i + chunk_size]
                    else:
                        yield content

                response = StreamingHttpResponse(
                    file_iterator(content),
                    content_type=content_type
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                response['Content-Length'] = len(content)

                return response

            except Exception as e:
                logger.exception(f"Erreur lors de la génération du rapport {rapport.id}")
                rapport.statut = 'ERREUR'
                rapport.parametres['erreur'] = str(e)
                rapport.save()

                messages.error(
                    request,
                    _("Erreur lors de la génération du rapport: %(error)s") % {'error': str(e)}
                )
                return redirect("analytics:rapport-detail", pk=rapport.pk)
        else:
            # Le formulaire est invalide
            logger.warning(f"Formulaire rapport invalide: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RapportForm()

    # Contexte pour le nouvel éditeur de rapport
    # Note: TypeGraphiqueRapport et ModeleRapport sont importés en haut du fichier

    context = {
        "form": form,
        "types_graphiques": list(TypeGraphiqueRapport.objects.filter(actif=True).values(
            'id', 'code', 'nom', 'description', 'type_graphique',
            'types_rapport_compatibles', 'options_affichage'
        )),
        "modeles_rapport": list(ModeleRapport.objects.filter(actif=True).values(
            'id', 'nom', 'description', 'type_rapport', 'sections_defaut'
        )),
    }

    return render(request, "analytics/rapport_generer_v2.html", context)


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


# ============================================================================
# API SECTIONS DE RAPPORT
# ============================================================================


@login_required
@require_http_methods(["GET", "POST"])
def rapport_sections_api(request, rapport_id):
    """
    API pour gérer les sections d'un rapport.

    GET: Liste toutes les sections du rapport
    POST: Crée une nouvelle section
    """
    rapport = get_object_or_404(Rapport, pk=rapport_id)

    if request.method == "GET":
        sections = RapportSectionService.get_sections_rapport(rapport)
        data = []
        for section in sections:
            section_data = {
                'id': str(section.id),
                'ordre': section.ordre,
                'type_section': section.type_section,
                'type_section_display': section.get_type_section_display(),
                'contenu_texte': section.contenu_texte,
                'visible': section.visible,
                'config': section.config,
            }
            if section.type_graphique:
                section_data['type_graphique'] = {
                    'id': str(section.type_graphique.id),
                    'code': section.type_graphique.code,
                    'nom': section.type_graphique.nom,
                    'type': section.type_graphique.type_graphique,
                }
            data.append(section_data)
        return JsonResponse({'sections': data})

    elif request.method == "POST":
        try:
            body = json.loads(request.body)
            type_section = body.get('type_section')
            contenu_texte = body.get('contenu_texte', '')
            code_graphique = body.get('code_graphique')
            config = body.get('config', {})
            position = body.get('position')

            type_graphique = None
            if code_graphique:
                type_graphique = TypeGraphiqueRapport.objects.filter(
                    code=code_graphique,
                    actif=True
                ).first()

            section = RapportSectionService.creer_section(
                rapport=rapport,
                type_section=type_section,
                contenu_texte=contenu_texte,
                type_graphique=type_graphique,
                config=config,
                position=position,
            )

            return JsonResponse({
                'success': True,
                'section': {
                    'id': str(section.id),
                    'ordre': section.ordre,
                    'type_section': section.type_section,
                    'type_section_display': section.get_type_section_display(),
                }
            })
        except Exception as e:
            logger.exception(f"Erreur création section: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def rapport_section_detail_api(request, rapport_id, section_id):
    """
    API pour une section spécifique.

    GET: Détails de la section
    PUT: Modifier la section
    DELETE: Supprimer la section
    """
    rapport = get_object_or_404(Rapport, pk=rapport_id)
    section = get_object_or_404(SectionRapport, pk=section_id, rapport=rapport)

    if request.method == "GET":
        data = {
            'id': str(section.id),
            'ordre': section.ordre,
            'type_section': section.type_section,
            'type_section_display': section.get_type_section_display(),
            'contenu_texte': section.contenu_texte,
            'visible': section.visible,
            'config': section.config,
        }
        if section.type_graphique:
            data['type_graphique'] = {
                'id': str(section.type_graphique.id),
                'code': section.type_graphique.code,
                'nom': section.type_graphique.nom,
            }
        return JsonResponse(data)

    elif request.method == "PUT":
        try:
            body = json.loads(request.body)

            contenu_texte = body.get('contenu_texte')
            config = body.get('config')
            visible = body.get('visible')

            # Gestion du changement de graphique
            code_graphique = body.get('code_graphique')
            type_graphique = None
            if code_graphique:
                type_graphique = TypeGraphiqueRapport.objects.filter(
                    code=code_graphique,
                    actif=True
                ).first()

            section = RapportSectionService.modifier_section(
                section=section,
                contenu_texte=contenu_texte,
                type_graphique=type_graphique if code_graphique else None,
                config=config,
                visible=visible,
            )

            return JsonResponse({'success': True})
        except Exception as e:
            logger.exception(f"Erreur modification section: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    elif request.method == "DELETE":
        try:
            RapportSectionService.supprimer_section(section)
            return JsonResponse({'success': True})
        except Exception as e:
            logger.exception(f"Erreur suppression section: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def rapport_sections_reorder_api(request, rapport_id):
    """
    API pour réordonner les sections d'un rapport.

    POST body: {"ordre": ["section-id-1", "section-id-2", ...]}
    """
    rapport = get_object_or_404(Rapport, pk=rapport_id)

    try:
        body = json.loads(request.body)
        ordre_ids = body.get('ordre', [])

        RapportSectionService.reordonner_sections(rapport, ordre_ids)

        return JsonResponse({'success': True})
    except Exception as e:
        logger.exception(f"Erreur réordonnancement sections: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def rapport_preview_pdf_api(request, rapport_id):
    """
    API pour générer un preview PDF du rapport.

    Retourne le PDF en bytes pour affichage dans un iframe.
    """
    rapport = get_object_or_404(Rapport, pk=rapport_id)

    try:
        # Import ici pour éviter les imports circulaires
        from .tasks import generer_pdf_preview

        # Générer le PDF preview
        pdf_bytes = generer_pdf_preview(rapport)

        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="preview.pdf"'
            return response
        else:
            return JsonResponse({'error': 'Impossible de générer le PDF'}, status=500)

    except Exception as e:
        logger.exception(f"Erreur génération preview PDF: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def rapport_preview_live_api(request):
    """
    API pour générer un preview PDF en temps réel sans rapport existant.

    Reçoit les données de configuration en POST et retourne le PDF.
    Utilise StreamingHttpResponse pour une meilleure performance.
    """
    try:
        data = json.loads(request.body)

        type_rapport = data.get('type_rapport')
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        mandat_id = data.get('mandat_id')
        sections = data.get('sections', [])
        options = data.get('options', {})

        if not type_rapport or not date_debut or not date_fin:
            return JsonResponse({
                'error': 'Paramètres manquants: type_rapport, date_debut, date_fin requis'
            }, status=400)

        # Import ici pour éviter les imports circulaires
        from .tasks import generer_pdf_preview_live

        # Récupérer le mandat si spécifié
        mandat = None
        if mandat_id:
            try:
                mandat = Mandat.objects.get(pk=mandat_id)
            except Mandat.DoesNotExist:
                pass

        # Générer le PDF preview
        pdf_bytes = generer_pdf_preview_live(
            type_rapport=type_rapport,
            date_debut=date_debut,
            date_fin=date_fin,
            mandat=mandat,
            sections=sections,
            options=options
        )

        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="preview.pdf"'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response
        else:
            return JsonResponse({'error': 'Impossible de générer le PDF'}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)
    except Exception as e:
        logger.exception(f"Erreur génération preview live: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def graphiques_disponibles_api(request, type_rapport):
    """
    API pour récupérer les graphiques prédéfinis disponibles pour un type de rapport.
    """
    graphiques = RapportSectionService.get_graphiques_compatibles(type_rapport)

    data = []
    for g in graphiques:
        data.append({
            'id': str(g.id),
            'code': g.code,
            'nom': g.nom,
            'description': g.description,
            'type_graphique': g.type_graphique,
            'type_graphique_display': g.get_type_graphique_display(),
            'unite_donnees': g.unite_donnees,
            'unite_donnees_display': g.get_unite_donnees_display(),
        })

    return JsonResponse({'graphiques': data})


@login_required
@require_http_methods(["GET"])
def modeles_rapport_api(request, type_rapport):
    """
    API pour récupérer les modèles de rapport disponibles pour un type.
    """
    # Modèles système + modèles de l'utilisateur
    modeles = ModeleRapport.objects.filter(
        type_rapport=type_rapport,
        actif=True
    ).filter(
        Q(proprietaire__isnull=True) | Q(proprietaire=request.user)
    ).order_by('ordre', 'nom')

    data = []
    for m in modeles:
        data.append({
            'id': str(m.id),
            'nom': m.nom,
            'description': m.description,
            'est_systeme': m.proprietaire is None,
            'nombre_sections': len(m.sections_defaut),
        })

    return JsonResponse({'modeles': data})
