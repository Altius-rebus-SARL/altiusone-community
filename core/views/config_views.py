# core/views/config_views.py
"""Vues pour la gestion des paramètres métier configurables."""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _
from django.db.models import Count

from core.models import ParametreMetier
from core.permissions import permission_required_business


# ============================================================================
# Catégories avec labels humains par module
# ============================================================================

CATEGORIES_META = {
    'core': {
        'label': 'Général',
        'icon': 'ti-settings',
        'categories': {
            'type_mandat': 'Types de mandat',
            'periodicite': 'Périodicités',
            'type_facturation': 'Types de facturation',
            'forme_juridique': 'Formes juridiques',
            'type_tiers': 'Types de tiers',
            'priorite': 'Priorités',
            'fonction_contact': 'Fonctions de contact',
        }
    },
    'salaires': {
        'label': 'Salaires',
        'icon': 'ti-users',
        'categories': {
            'type_contrat': 'Types de contrat',
            'type_cotisation': 'Types de cotisation',
            'type_allocation': 'Types d\'allocation',
            'organisme_declaration': 'Organismes de déclaration',
            'type_certificat_travail': 'Types de certificat de travail',
            'motif_depart': 'Motifs de départ',
        }
    },
    'facturation': {
        'label': 'Facturation',
        'icon': 'ti-file-invoice',
        'categories': {
            'type_facture': 'Types de facture',
            'mode_paiement': 'Modes de paiement',
        }
    },
    'comptabilite': {
        'label': 'Comptabilité',
        'icon': 'ti-calculator',
        'categories': {
            'type_journal': 'Types de journal',
            'type_compte_bancaire': 'Types de compte bancaire',
        }
    },
    'fiscalite': {
        'label': 'Fiscalité',
        'icon': 'ti-building-bank',
        'categories': {
            'type_declaration': 'Types de déclaration',
            'type_impot': 'Types d\'impôt',
            'type_annexe': 'Types d\'annexe',
            'type_correction': 'Types de correction',
            'categorie_optimisation': 'Catégories d\'optimisation',
        }
    },
    'tva': {
        'label': 'TVA',
        'icon': 'ti-receipt-tax',
        'categories': {
            'methode_calcul': 'Méthodes de calcul',
            'type_taux_tva': 'Types de taux',
        }
    },
    'documents': {
        'label': 'Documents',
        'icon': 'ti-files',
        'categories': {
            'type_document': 'Types de document',
        }
    },
    'projets': {
        'label': 'Projets',
        'icon': 'ti-briefcase',
        'categories': {
            'statut_projet': 'Statuts de projet',
        }
    },
}


@permission_required_business('core.view_parametremetier')
def configuration_index(request):
    """Page principale de configuration avec tabs par module."""
    active_module = request.GET.get('module', 'core')
    active_categorie = request.GET.get('categorie', '')

    # Stats par module
    stats = (
        ParametreMetier.objects
        .values('module')
        .annotate(total=Count('id'))
        .order_by('module')
    )
    stats_dict = {s['module']: s['total'] for s in stats}

    # Enrichir les modules avec le nombre de paramètres
    modules = []
    for mod_code, mod_info in CATEGORIES_META.items():
        modules.append({
            'code': mod_code,
            'label': mod_info['label'],
            'icon': mod_info['icon'],
            'count': stats_dict.get(mod_code, 0),
            'categories': mod_info['categories'],
        })

    # Paramètres du module actif
    if active_module in CATEGORIES_META:
        categories = CATEGORIES_META[active_module]['categories']
        if not active_categorie and categories:
            active_categorie = list(categories.keys())[0]
    else:
        categories = {}

    parametres = ParametreMetier.objects.filter(
        module=active_module,
    )
    if active_categorie:
        parametres = parametres.filter(categorie=active_categorie)

    return render(request, 'core/configuration/index.html', {
        'modules': modules,
        'active_module': active_module,
        'active_categorie': active_categorie,
        'categories': categories,
        'parametres': parametres,
        'is_active': 'configuration',
    })


@permission_required_business('core.view_parametremetier')
def configuration_list_partial(request, module, categorie):
    """Retourne le partial HTMX de la liste des paramètres."""
    cat_label = ''
    if module in CATEGORIES_META:
        cat_label = CATEGORIES_META[module]['categories'].get(categorie, categorie)

    parametres = ParametreMetier.objects.filter(
        module=module,
        categorie=categorie,
    )

    return render(request, 'core/configuration/partials/parametre_list.html', {
        'parametres': parametres,
        'module': module,
        'categorie': categorie,
        'categorie_label': cat_label,
    })


@permission_required_business('core.change_parametremetier')
def configuration_create(request, module, categorie):
    """Crée un nouveau paramètre métier (HTMX)."""
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        libelle = request.POST.get('libelle', '').strip()
        description = request.POST.get('description', '').strip()

        if not code or not libelle:
            return HttpResponse(
                '<div class="alert alert-danger">Code et libellé sont requis.</div>',
                status=422
            )

        if ParametreMetier.objects.filter(
            module=module, categorie=categorie, code=code
        ).exists():
            return HttpResponse(
                '<div class="alert alert-danger">Ce code existe déjà dans cette catégorie.</div>',
                status=422
            )

        # Déterminer le prochain ordre
        max_ordre = ParametreMetier.objects.filter(
            module=module, categorie=categorie
        ).order_by('-ordre').values_list('ordre', flat=True).first() or 0

        ParametreMetier.objects.create(
            module=module,
            categorie=categorie,
            code=code,
            libelle=libelle,
            description=description,
            ordre=max_ordre + 10,
            systeme=False,
        )

        return configuration_list_partial(request, module, categorie)

    return render(request, 'core/configuration/partials/parametre_form.html', {
        'module': module,
        'categorie': categorie,
        'is_new': True,
    })


@permission_required_business('core.change_parametremetier')
@require_http_methods(["POST"])
def configuration_update(request, pk):
    """Met à jour un paramètre métier (HTMX inline)."""
    param = get_object_or_404(ParametreMetier, pk=pk)

    libelle = request.POST.get('libelle', '').strip()
    description = request.POST.get('description', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    if libelle:
        param.libelle = libelle
    param.description = description
    param.is_active = is_active
    param.save(update_fields=['libelle', 'description', 'is_active', 'updated_at'])

    return configuration_list_partial(request, param.module, param.categorie)


@permission_required_business('core.delete_parametremetier')
@require_http_methods(["POST"])
def configuration_delete(request, pk):
    """Supprime un paramètre métier (seulement les non-système)."""
    param = get_object_or_404(ParametreMetier, pk=pk)

    if param.systeme:
        return HttpResponse(
            '<div class="alert alert-warning">Impossible de supprimer un paramètre système. '
            'Vous pouvez le désactiver.</div>',
            status=403
        )

    module = param.module
    categorie = param.categorie
    param.delete()

    return configuration_list_partial(request, module, categorie)


@permission_required_business('core.change_parametremetier')
@require_http_methods(["POST"])
def configuration_toggle(request, pk):
    """Active/désactive un paramètre métier (HTMX)."""
    param = get_object_or_404(ParametreMetier, pk=pk)
    param.is_active = not param.is_active
    param.save(update_fields=['is_active', 'updated_at'])
    return configuration_list_partial(request, param.module, param.categorie)


@permission_required_business('core.change_parametremetier')
@require_http_methods(["POST"])
def configuration_reorder(request, module, categorie):
    """Réordonne les paramètres (HTMX, reçoit une liste d'IDs)."""
    import json
    try:
        order = json.loads(request.body)
        for idx, pk in enumerate(order):
            ParametreMetier.objects.filter(pk=pk).update(ordre=idx * 10)
    except (json.JSONDecodeError, TypeError):
        return HttpResponse(status=400)
    return HttpResponse(status=204)


# ============================================================================
# Quick-create pour les modèles de référence (modal AJAX)
# ============================================================================

QUICK_CREATE_MODELS = {
    'type_mandat': 'TypeMandat',
    'periodicite': 'Periodicite',
    'type_facturation': 'TypeFacturation',
}


@permission_required_business('core.change_parametremetier')
@require_http_methods(["POST"])
def quick_create_reference(request, model_type):
    """Crée rapidement un item de référence (TypeMandat, Periodicite, TypeFacturation)."""
    import json
    from core.models import TypeMandat, Periodicite, TypeFacturation

    model_map = {
        'type_mandat': TypeMandat,
        'periodicite': Periodicite,
        'type_facturation': TypeFacturation,
    }

    Model = model_map.get(model_type)
    if not Model:
        return JsonResponse({'error': 'Type invalide'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    code = (data.get('code') or '').strip().upper()
    libelle = (data.get('libelle') or '').strip()

    if not code or not libelle:
        return JsonResponse({'error': 'Code et libellé sont requis'}, status=422)

    if Model.objects.filter(code=code).exists():
        return JsonResponse({'error': 'Ce code existe déjà'}, status=422)

    obj = Model.objects.create(
        code=code,
        libelle=libelle,
        description=data.get('description', ''),
    )

    return JsonResponse({
        'id': str(obj.pk),
        'code': obj.code,
        'libelle': obj.libelle,
    })
