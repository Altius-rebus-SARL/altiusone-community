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
    'regimes': {
        'label': 'Régimes & Pays',
        'icon': 'ti-world',
        'is_advanced': True,
        'categories': {
            'regime_fiscal': 'Régimes fiscaux',
            'type_identifiant_legal': 'Identifiants légaux',
            'mention_legale': 'Mentions légales factures',
            'niveau_relance': 'Niveaux de relance',
            'compte_par_defaut': 'Comptes par défaut',
            'taux_cotisation': 'Cotisations sociales',
            'allocation_familiale': 'Allocations familiales',
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

    is_advanced = CATEGORIES_META.get(active_module, {}).get('is_advanced', False)

    return render(request, 'core/configuration/index.html', {
        'modules': modules,
        'active_module': active_module,
        'active_categorie': active_categorie,
        'categories': categories,
        'parametres': parametres,
        'is_active': 'configuration',
        'is_advanced': is_advanced,
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


# ============================================================================
# Modèles avancés — CRUD pour RegimeFiscal, TauxCotisation, etc.
# ============================================================================

ADVANCED_MODEL_MAP = {
    'regime_fiscal': {
        'module': 'tva.models', 'model': 'RegimeFiscal',
        'fields': ['code', 'nom', 'pays', 'taux_normal', 'nom_taxe', 'devise_defaut'],
        'form_fields': ['code', 'nom', 'pays', 'devise_defaut', 'taux_normal', 'nom_taxe',
                        'a_taux_reduit', 'a_taux_special', 'supporte_xml',
                        'suppression_facture_emise', 'seuil_facture_simplifiee',
                        'delai_paiement_defaut', 'nombre_relances_max'],
    },
    'type_identifiant_legal': {
        'module': 'core.models', 'model': 'TypeIdentifiantLegal',
        'fields': ['code', 'libelle', 'pays', 'obligatoire_entreprise', 'obligatoire_client'],
        'form_fields': ['code', 'libelle', 'pays', 'regime_fiscal', 'format_validation',
                        'exemple', 'obligatoire_entreprise', 'obligatoire_client', 'afficher_sur_facture'],
    },
    'mention_legale': {
        'module': 'facturation.models', 'model': 'MentionLegale',
        'fields': ['regime_fiscal', 'code', 'libelle', 'type_document', 'obligatoire'],
        'form_fields': ['regime_fiscal', 'code', 'libelle', 'texte', 'type_document', 'obligatoire', 'ordre'],
    },
    'niveau_relance': {
        'module': 'facturation.models', 'model': 'NiveauRelance',
        'fields': ['regime_fiscal', 'niveau', 'libelle', 'delai_jours', 'frais', 'interets'],
        'form_fields': ['regime_fiscal', 'niveau', 'libelle', 'delai_jours', 'frais', 'interets', 'taux_interet'],
    },
    'compte_par_defaut': {
        'module': 'comptabilite.models', 'model': 'CompteParDefaut',
        'fields': ['plan_comptable', 'type_compte', 'compte'],
        'form_fields': ['plan_comptable', 'type_compte', 'compte'],
    },
    'taux_cotisation': {
        'module': 'salaires.models', 'model': 'TauxCotisation',
        'fields': ['regime_fiscal', 'type_cotisation', 'libelle', 'taux_employe', 'taux_employeur'],
        'form_fields': ['regime_fiscal', 'type_cotisation', 'libelle', 'taux_employe', 'taux_employeur',
                        'taux_total', 'salaire_min', 'salaire_max', 'devise', 'date_debut', 'date_fin'],
    },
    'allocation_familiale': {
        'module': 'salaires.models', 'model': 'AllocationFamiliale',
        'fields': ['canton', 'type_allocation', 'montant', 'date_debut'],
        'form_fields': ['canton', 'type_allocation', 'montant', 'date_debut', 'date_fin'],
    },
}


def _get_advanced_model(categorie):
    """Résout le modèle Django depuis ADVANCED_MODEL_MAP."""
    config = ADVANCED_MODEL_MAP.get(categorie)
    if not config:
        return None, None, None
    from importlib import import_module as _imp
    mod = _imp(config['module'])
    Model = getattr(mod, config['model'])
    return Model, config, config['fields']


@permission_required_business('core.view_parametremetier')
def configuration_advanced_list(request, module, categorie):
    """Retourne le partial HTMX pour les modèles avancés."""
    Model, config, display_fields = _get_advanced_model(categorie)
    if not Model:
        return HttpResponse('<div class="alert alert-warning">Catégorie inconnue</div>')

    items = Model.objects.all().order_by(*(['-created_at'] if hasattr(Model, 'created_at') else ['pk']))[:100]
    cat_label = CATEGORIES_META.get(module, {}).get('categories', {}).get(categorie, categorie)

    return render(request, 'core/configuration/partials/advanced_list.html', {
        'items': items,
        'fields': display_fields,
        'model_name': config['model'],
        'categorie': categorie,
        'categorie_label': cat_label,
        'module': module,
        'form_fields': config.get('form_fields', []),
    })


@permission_required_business('core.change_parametremetier')
@require_http_methods(["GET", "POST"])
def configuration_advanced_edit(request, module, categorie, pk=None):
    """Créer ou modifier un item d'un modèle avancé (HTMX modal ou inline)."""
    from django.forms import modelform_factory

    Model, config, _ = _get_advanced_model(categorie)
    if not Model:
        return HttpResponse('<div class="alert alert-danger">Modèle inconnu</div>', status=400)

    form_fields = config.get('form_fields', [])
    Form = modelform_factory(Model, fields=form_fields)
    instance = get_object_or_404(Model, pk=pk) if pk else None

    if request.method == 'POST':
        form = Form(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Enregistré avec succès"))
            # Retourner la liste mise à jour
            return configuration_advanced_list(request, module, categorie)
    else:
        form = Form(instance=instance)

    # Ajouter les classes Bootstrap aux champs
    for field in form.fields.values():
        css = field.widget.attrs.get('class', '')
        if 'form-check-input' not in css:
            field.widget.attrs['class'] = f"{css} form-control form-control-sm".strip()

    cat_label = CATEGORIES_META.get(module, {}).get('categories', {}).get(categorie, categorie)

    return render(request, 'core/configuration/partials/advanced_form.html', {
        'form': form,
        'instance': instance,
        'categorie': categorie,
        'categorie_label': cat_label,
        'module': module,
        'model_name': config['model'],
    })


@permission_required_business('core.delete_parametremetier')
@require_http_methods(["POST"])
def configuration_advanced_delete(request, module, categorie, pk):
    """Supprime un item d'un modèle avancé."""
    Model, config, _ = _get_advanced_model(categorie)
    if not Model:
        return HttpResponse(status=400)

    obj = get_object_or_404(Model, pk=pk)
    obj.delete()
    messages.success(request, _("Supprimé avec succès"))
    return configuration_advanced_list(request, module, categorie)


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
