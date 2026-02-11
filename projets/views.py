import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.models import Mandat

from .forms import OperationForm, OperationNoteForm, PositionForm
from .models import Operation, Position


# =============================================================================
# POSITIONS CRUD
# =============================================================================


@login_required
@require_GET
def position_list_partial(request, mandat_pk):
    """Liste des positions d'un mandat (partial HTMX)."""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    positions = (
        mandat.positions.filter(is_active=True)
        .select_related("responsable", "devise")
        .prefetch_related("operations")
        .order_by("ordre")
    )
    form = PositionForm()
    return render(request, "projets/partials/position_list.html", {
        "mandat": mandat,
        "positions": positions,
        "form": form,
    })


@login_required
@require_POST
def position_create(request, mandat_pk):
    """Crée une nouvelle position dans un mandat."""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    form = PositionForm(request.POST)
    if form.is_valid():
        position = form.save(commit=False)
        position.mandat = mandat
        position.created_by = request.user
        # Auto-calcul de l'ordre
        last_ordre = mandat.positions.filter(is_active=True).aggregate(
            max_ordre=models.Max("ordre")
        )["max_ordre"]
        position.ordre = (last_ordre or 0) + 1
        position.save()
        # Return the updated list
        positions = (
            mandat.positions.filter(is_active=True)
            .select_related("responsable", "devise")
            .prefetch_related("operations")
            .order_by("ordre")
        )
        return render(request, "projets/partials/position_list.html", {
            "mandat": mandat,
            "positions": positions,
            "form": PositionForm(),
        })
    return render(request, "projets/partials/position_form.html", {
        "mandat": mandat,
        "form": form,
    })


@login_required
@require_GET
def position_detail(request, pk):
    """Détail d'une position (accordéon avec opérations)."""
    position = get_object_or_404(
        Position.objects.select_related("responsable", "devise", "mandat")
        .prefetch_related("operations__assigne_a", "operations__contacts_assignes"),
        pk=pk,
    )
    operation_form = OperationForm()
    return render(request, "projets/partials/position_card.html", {
        "position": position,
        "operations": position.operations.all().order_by("ordre"),
        "operation_form": operation_form,
    })


@login_required
@require_http_methods(["GET", "POST"])
def position_update(request, pk):
    """Modifie une position existante."""
    position = get_object_or_404(Position.objects.select_related("mandat"), pk=pk)
    if request.method == "POST":
        form = PositionForm(request.POST, instance=position)
        if form.is_valid():
            form.save()
            # Return the updated list
            mandat = position.mandat
            positions = (
                mandat.positions.filter(is_active=True)
                .select_related("responsable", "devise")
                .prefetch_related("operations")
                .order_by("ordre")
            )
            return render(request, "projets/partials/position_list.html", {
                "mandat": mandat,
                "positions": positions,
                "form": PositionForm(),
            })
        return render(request, "projets/partials/position_form.html", {
            "mandat": position.mandat,
            "form": form,
            "position": position,
        })
    else:
        form = PositionForm(instance=position)
        return render(request, "projets/partials/position_form.html", {
            "mandat": position.mandat,
            "form": form,
            "position": position,
        })


@login_required
@require_http_methods(["DELETE", "POST"])
def position_delete(request, pk):
    """Supprime une position (soft delete via is_active)."""
    position = get_object_or_404(Position.objects.select_related("mandat"), pk=pk)
    mandat = position.mandat
    position.is_active = False
    position.save(update_fields=["is_active"])
    # Return updated list
    positions = (
        mandat.positions.filter(is_active=True)
        .select_related("responsable", "devise")
        .prefetch_related("operations")
        .order_by("ordre")
    )
    return render(request, "projets/partials/position_list.html", {
        "mandat": mandat,
        "positions": positions,
        "form": PositionForm(),
    })


# =============================================================================
# OPERATIONS CRUD
# =============================================================================


@login_required
@require_POST
def operation_create(request, position_pk):
    """Crée une opération dans une position."""
    position = get_object_or_404(Position.objects.select_related("mandat"), pk=position_pk)
    form = OperationForm(request.POST)
    if form.is_valid():
        operation = form.save(commit=False)
        operation.position = position
        operation.created_by = request.user
        # Auto-calcul de l'ordre
        last_ordre = position.operations.filter(is_active=True).aggregate(
            max_ordre=models.Max("ordre")
        )["max_ordre"]
        operation.ordre = (last_ordre or 0) + 1
        operation.save()
        form.save_m2m()
        # Recalculate budget
        position.recalculer_budget_reel()
        operations = position.operations.filter(is_active=True).prefetch_related("assigne_a", "contacts_assignes").order_by("ordre")
        return render(request, "projets/partials/operation_list.html", {
            "position": position,
            "operations": operations,
            "operation_form": OperationForm(),
        })
    return render(request, "projets/partials/operation_form.html", {
        "position": position,
        "form": form,
    })


@login_required
@require_http_methods(["GET", "POST"])
def operation_update(request, pk):
    """Modifie une opération."""
    operation = get_object_or_404(
        Operation.objects.select_related("position", "position__mandat"),
        pk=pk,
    )
    position = operation.position
    if request.method == "POST":
        form = OperationForm(request.POST, instance=operation)
        if form.is_valid():
            form.save()
            position.recalculer_budget_reel()
            operations = position.operations.filter(is_active=True).prefetch_related("assigne_a", "contacts_assignes").order_by("ordre")
            return render(request, "projets/partials/operation_list.html", {
                "position": position,
                "operations": operations,
                "operation_form": OperationForm(),
            })
        return render(request, "projets/partials/operation_form.html", {
            "position": position,
            "form": form,
            "operation": operation,
        })
    else:
        form = OperationForm(instance=operation)
        return render(request, "projets/partials/operation_form.html", {
            "position": position,
            "form": form,
            "operation": operation,
        })


@login_required
@require_http_methods(["DELETE", "POST"])
def operation_delete(request, pk):
    """Supprime une opération (soft delete)."""
    operation = get_object_or_404(
        Operation.objects.select_related("position", "position__mandat"),
        pk=pk,
    )
    position = operation.position
    operation.is_active = False
    operation.save(update_fields=["is_active"])
    position.recalculer_budget_reel()
    operations = position.operations.filter(is_active=True).prefetch_related("assigne_a", "contacts_assignes").order_by("ordre")
    return render(request, "projets/partials/operation_list.html", {
        "position": position,
        "operations": operations,
        "operation_form": OperationForm(),
    })


@login_required
@require_POST
def operation_change_statut(request, pk):
    """Change le statut d'une opération (AJAX)."""
    operation = get_object_or_404(Operation, pk=pk)
    new_statut = request.POST.get("statut")
    if new_statut in dict(Operation.STATUT_CHOICES):
        operation.statut = new_statut
        operation.save(update_fields=["statut"])
        return render(request, "projets/partials/operation_item.html", {
            "operation": operation,
        })
    return JsonResponse({"error": "Statut invalide"}, status=400)


@login_required
@require_POST
def operation_reorder(request, position_pk):
    """Réordonne les opérations d'une position (Sortable.js)."""
    position = get_object_or_404(Position, pk=position_pk)
    try:
        order_data = json.loads(request.body)
        order_ids = order_data.get("order", [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Données invalides"}, status=400)

    for idx, op_id in enumerate(order_ids):
        Operation.objects.filter(pk=op_id, position=position).update(ordre=idx)

    return JsonResponse({"success": True})


@login_required
@require_POST
def operation_add_note(request, pk):
    """Ajoute une note à une opération."""
    operation = get_object_or_404(Operation, pk=pk)
    form = OperationNoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.operation = operation
        note.auteur = request.user
        note.created_by = request.user
        note.save()
    notes = operation.notes.select_related("auteur").all()
    return render(request, "projets/partials/operation_notes.html", {
        "operation": operation,
        "notes": notes,
        "note_form": OperationNoteForm(),
    })


# =============================================================================
# GANTT / TIMELINE
# =============================================================================


POSITION_COLORS = ["#088178", "#2c3e50", "#27ae60", "#c0392b", "#8e44ad", "#f39c12", "#2980b9", "#e74c3c"]


@login_required
@require_GET
def gantt_data(request, mandat_pk):
    """Retourne les données Gantt au format ApexCharts rangeBar (JSON)."""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    positions = (
        mandat.positions.filter(is_active=True)
        .prefetch_related("operations", "operations__assigne_a")
        .order_by("ordre")
    )

    series = []
    today_str = date.today().isoformat()

    for idx, pos in enumerate(positions):
        color = POSITION_COLORS[idx % len(POSITION_COLORS)]
        data_points = []

        # Position bar itself
        if pos.date_debut and pos.date_fin:
            data_points.append({
                "x": f"[P] {pos.titre}",
                "y": [pos.date_debut.isoformat(), pos.date_fin.isoformat()],
                "fillColor": color,
                "meta": {"type": "position", "id": str(pos.pk), "statut": pos.statut},
            })

        # Operations within this position
        for op in pos.operations.filter(is_active=True).order_by("ordre"):
            if op.date_debut and op.date_fin:
                op_color = color
                # Striped if overdue
                is_overdue = op.date_fin < date.today() and op.statut not in ("TERMINEE", "ANNULEE")
                data_points.append({
                    "x": op.titre,
                    "y": [op.date_debut.isoformat(), op.date_fin.isoformat()],
                    "fillColor": op_color,
                    "meta": {
                        "type": "operation",
                        "id": str(op.pk),
                        "statut": op.statut,
                        "assigne": ", ".join(str(u) for u in op.assigne_a.all()) if op.assigne_a.exists() else "",
                        "overdue": is_overdue,
                    },
                })

        if data_points:
            series.append({
                "name": pos.titre,
                "data": data_points,
            })

    return JsonResponse({
        "series": series,
        "today": today_str,
    })


@login_required
@require_GET
def gantt_view(request, mandat_pk):
    """Vue partielle Gantt (conteneur ApexCharts)."""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    return render(request, "projets/partials/gantt_view.html", {
        "mandat": mandat,
    })


# =============================================================================
# BUDGET SUMMARY
# =============================================================================


@login_required
@require_GET
def budget_summary(request, mandat_pk):
    """Vue partielle du dashboard budget."""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    positions = (
        mandat.positions.filter(is_active=True)
        .select_related("devise")
        .order_by("ordre")
    )

    total_prevu = Decimal("0")
    total_reel = Decimal("0")
    total_sous_traite_prevu = Decimal("0")
    total_interne_prevu = Decimal("0")
    positions_data = []

    for pos in positions:
        prevu = pos.budget_prevu or Decimal("0")
        reel = pos.budget_reel or Decimal("0")
        ecart = prevu - reel
        pourcent = pos.budget_consomme_pourcent

        total_prevu += prevu
        total_reel += reel

        if pos.est_sous_traite:
            total_sous_traite_prevu += prevu
        else:
            total_interne_prevu += prevu

        positions_data.append({
            "position": pos,
            "prevu": prevu,
            "reel": reel,
            "ecart": ecart,
            "pourcent": pourcent,
        })

    total_ecart = total_prevu - total_reel
    total_pourcent = (
        (total_reel / total_prevu * 100).quantize(Decimal("0.1"))
        if total_prevu > 0
        else Decimal("0")
    )

    return render(request, "projets/partials/budget_summary.html", {
        "mandat": mandat,
        "positions_data": positions_data,
        "total_prevu": total_prevu,
        "total_reel": total_reel,
        "total_ecart": total_ecart,
        "total_pourcent": total_pourcent,
        "total_interne_prevu": total_interne_prevu,
        "total_sous_traite_prevu": total_sous_traite_prevu,
        # JSON for charts
        "chart_labels_json": json.dumps([pd["position"].titre for pd in positions_data]),
        "chart_prevu_json": json.dumps([float(pd["prevu"]) for pd in positions_data]),
        "chart_reel_json": json.dumps([float(pd["reel"]) for pd in positions_data]),
        "chart_interne": float(total_interne_prevu),
        "chart_sous_traite": float(total_sous_traite_prevu),
    })


# =============================================================================
# MAP / CARTE
# =============================================================================


@login_required
@require_GET
def map_data(request, mandat_pk):
    """Retourne les données géographiques en GeoJSON."""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    features = []

    positions = mandat.positions.filter(is_active=True, coordonnees__isnull=False)
    for pos in positions:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [pos.coordonnees.x, pos.coordonnees.y],
            },
            "properties": {
                "type": "position",
                "id": str(pos.pk),
                "titre": pos.titre,
                "numero": pos.numero,
                "statut": pos.statut,
                "budget_prevu": float(pos.budget_prevu),
                "progression": float(pos.progression_pourcent),
            },
        })

    operations = Operation.objects.filter(
        position__mandat=mandat,
        is_active=True,
        coordonnees__isnull=False,
    ).select_related("position")
    for op in operations:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [op.coordonnees.x, op.coordonnees.y],
            },
            "properties": {
                "type": "operation",
                "id": str(op.pk),
                "titre": op.titre,
                "numero": op.numero,
                "statut": op.statut,
                "position_titre": op.position.titre,
            },
        })

    return JsonResponse({
        "type": "FeatureCollection",
        "features": features,
    })


@login_required
@require_GET
def map_view(request, mandat_pk):
    """Vue partielle carte Leaflet."""
    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    return render(request, "projets/partials/map_view.html", {
        "mandat": mandat,
    })
