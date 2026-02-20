# analytics/d3_views.py
"""
Endpoints API JSON pour les visualisations D3.js.
"""
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from core.models import Mandat
from .services.d3_data_service import D3DataService
import logging

logger = logging.getLogger(__name__)


def _decimal_to_float(obj):
    """Convertit récursivement les Decimal en float pour JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_decimal_to_float(item) for item in obj]
    return obj


def _get_service(request):
    """Instancie D3DataService depuis les paramètres GET."""
    annee = request.GET.get('annee')
    mandat_id = request.GET.get('mandat')
    mandat = None
    if mandat_id:
        try:
            mandat = Mandat.objects.get(pk=mandat_id)
        except (Mandat.DoesNotExist, ValueError):
            pass
    if annee:
        try:
            annee = int(annee)
        except ValueError:
            annee = None
    return D3DataService(mandat=mandat, annee=annee)


@login_required
@require_GET
def d3_plan_comptable(request):
    """GET /analytics/api/d3/plan-comptable/ → arbre JSON du plan comptable."""
    try:
        service = _get_service(request)
        data = service.get_plan_comptable_tree()
        return JsonResponse(_decimal_to_float(data))
    except Exception as e:
        logger.exception("Erreur D3 plan-comptable: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def d3_flux_tresorerie(request):
    """GET /analytics/api/d3/flux-tresorerie/ → nœuds et liens Sankey."""
    try:
        service = _get_service(request)
        data = service.get_flux_tresorerie()
        return JsonResponse(_decimal_to_float(data))
    except Exception as e:
        logger.exception("Erreur D3 flux-tresorerie: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def d3_calendrier_activite(request):
    """GET /analytics/api/d3/calendrier-activite/?metric=factures → heatmap data."""
    try:
        service = _get_service(request)
        metric = request.GET.get('metric', 'factures')
        if metric not in ('factures', 'heures', 'paiements'):
            metric = 'factures'
        data = service.get_calendrier_activite(metric=metric)
        return JsonResponse(_decimal_to_float(data))
    except Exception as e:
        logger.exception("Erreur D3 calendrier-activite: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def d3_reseau_clients(request):
    """GET /analytics/api/d3/reseau-clients/ → nœuds et liens force-directed."""
    try:
        service = _get_service(request)
        data = service.get_reseau_clients()
        return JsonResponse(_decimal_to_float(data))
    except Exception as e:
        logger.exception("Erreur D3 reseau-clients: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def d3_decomposition_salaires(request):
    """GET /analytics/api/d3/decomposition-salaires/?mois=1 → arbre JSON salaires."""
    try:
        service = _get_service(request)
        mois = request.GET.get('mois')
        if mois:
            try:
                mois = int(mois)
                if not 1 <= mois <= 12:
                    mois = None
            except ValueError:
                mois = None
        data = service.get_decomposition_salaires(mois=mois)
        return JsonResponse(_decimal_to_float(data))
    except Exception as e:
        logger.exception("Erreur D3 decomposition-salaires: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def d3_timeline_projets(request):
    """GET /analytics/api/d3/timeline-projets/ → données Gantt."""
    try:
        service = _get_service(request)
        data = service.get_timeline_projets()
        return JsonResponse(_decimal_to_float(data))
    except Exception as e:
        logger.exception("Erreur D3 timeline-projets: %s", e)
        return JsonResponse({'error': str(e)}, status=500)
