"""
Configurations de style par defaut et utilitaires de merge pour le Document Studio.

Fournit les configs par defaut par type de document et une fonction de merge
pour combiner les defaults avec les overrides utilisateur.
"""
from copy import deepcopy


# ==============================================================================
# Defaults par type de document
# ==============================================================================

_BASE_DEFAULTS = {
    'couleur_primaire': '#02312e',
    'couleur_accent': '#2c3e50',
    'couleur_texte': '#333333',
    'police': 'Helvetica',
    'marge_haut': 20,
    'marge_bas': 25,
    'marge_gauche': 20,
    'marge_droite': 15,
    'textes': {},
    'blocs_visibles': {
        'logo': True,
        'introduction': True,
        'conclusion': True,
        'conditions': True,
    },
    'config': {},
}

DEFAULTS = {
    'FACTURE': {
        **_BASE_DEFAULTS,
        'blocs_visibles': {
            'logo': True,
            'introduction': True,
            'conclusion': True,
            'conditions': True,
            'qr_bill': False,
            'remise': True,
            'tva': True,
            'paiement': True,
        },
        'textes': {
            'entete': '',
            'pied_page': '',
            'introduction': '',
            'conclusion': '',
            'conditions': '',
        },
    },
    'AVOIR': {
        **_BASE_DEFAULTS,
        'blocs_visibles': {
            'logo': True,
            'introduction': True,
            'conclusion': True,
            'conditions': True,
            'qr_bill': False,
            'remise': True,
            'tva': True,
        },
    },
    'ACOMPTE': {
        **_BASE_DEFAULTS,
        'blocs_visibles': {
            'logo': True,
            'introduction': True,
            'conclusion': True,
            'conditions': True,
            'qr_bill': False,
        },
    },
    'FICHE_SALAIRE': {
        **_BASE_DEFAULTS,
        'blocs_visibles': {
            'logo': True,
            'presence': True,
            'cotisations_employeur': True,
            'informations_bancaires': True,
            'remarques': True,
        },
    },
    'CERTIFICAT_SALAIRE': {
        **_BASE_DEFAULTS,
        'blocs_visibles': {
            'logo': True,
            'remarques': True,
            'signature': True,
        },
    },
    'CERTIFICAT_TRAVAIL': {
        **_BASE_DEFAULTS,
        'blocs_visibles': {
            'logo': True,
            'description_taches': True,
            'formations': True,
            'projets_speciaux': True,
            'evaluation': True,
            'motif_depart': True,
            'formule_fin': True,
            'signature': True,
        },
    },
    'DECLARATION_COTISATIONS': {
        **_BASE_DEFAULTS,
        'blocs_visibles': {
            'logo': True,
            'detail_employes': True,
            'resume': True,
        },
    },
}


def get_default_style_config(type_document):
    """Retourne la configuration de style par defaut pour un type de document."""
    return deepcopy(DEFAULTS.get(type_document, _BASE_DEFAULTS))


def merge_style_config(defaults, overrides):
    """
    Deep-merge des overrides sur les defaults.
    Les valeurs None dans overrides sont ignorees.
    Les dicts sont fusionnes recursivement.
    """
    if not overrides:
        return deepcopy(defaults)

    result = deepcopy(defaults)
    for key, value in overrides.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_style_config(result[key], value)
        else:
            result[key] = value
    return result
