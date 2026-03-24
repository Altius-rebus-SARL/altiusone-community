# core/embedding_config.py
"""
Registre des modèles à vectoriser pour la recherche sémantique.

Chaque entrée définit:
- app_label.model_name: identifiant Django du modèle
- method: nom de la méthode qui retourne le texte (défaut: texte_pour_embedding)
- filter: filtre QuerySet optionnel pour exclure les objets non pertinents
- tier: priorité de vectorisation (1=critique, 2=important, 3=secondaire)
"""

MODEL_EMBEDDING_CONFIG = {
    # ===== TIER 1 : Entités métier principales =====
    'core.Client': {
        'tier': 1,
    },
    'core.Mandat': {
        'tier': 1,
    },
    'facturation.Facture': {
        'tier': 1,
    },
    'salaires.Employe': {
        'tier': 1,
    },

    # ===== TIER 2 : Entités comptables et projets =====
    'comptabilite.PieceComptable': {
        'tier': 2,
    },
    'comptabilite.Compte': {
        'tier': 2,
    },
    'comptabilite.Journal': {
        'tier': 2,
    },
    'comptabilite.EcritureComptable': {
        'tier': 2,
        'filter': {'libelle__regex': r'.{20,}'},  # libelle > 20 chars
    },
    'facturation.Prestation': {
        'tier': 2,
    },
    'facturation.TimeTracking': {
        'tier': 2,
        'filter': {'description__regex': r'.{1,}'},  # description non vide
    },
    'core.Tiers': {
        'tier': 2,
    },
    'core.Contact': {
        'tier': 2,
    },
    'projets.Position': {
        'tier': 2,
    },
    'projets.Operation': {
        'tier': 2,
    },

    # ===== TIER 3 : Déclarations, salaires, mailing =====
    'salaires.FicheSalaire': {
        'tier': 3,
    },
    'salaires.CertificatSalaire': {
        'tier': 3,
    },
    'tva.DeclarationTVA': {
        'tier': 3,
    },
    'fiscalite.DeclarationFiscale': {
        'tier': 3,
    },
    'fiscalite.CorrectionFiscale': {
        'tier': 3,
    },
    'projets.OperationNote': {
        'tier': 3,
    },
    'mailing.TemplateEmail': {
        'tier': 3,
    },
    'mailing.EmailRecu': {
        'tier': 3,
    },
    'mailing.EmailEnvoye': {
        'tier': 3,
    },

    # ===== Contrats & Analytique =====
    'core.Contrat': {
        'tier': 1,
    },
    'core.ModeleContrat': {
        'tier': 3,
    },
    'comptabilite.SectionAnalytique': {
        'tier': 2,
    },
    'comptabilite.AxeAnalytique': {
        'tier': 3,
    },
    'comptabilite.Immobilisation': {
        'tier': 2,
    },
    'comptabilite.ReleveBancaire': {
        'tier': 3,
    },
}


def get_models_for_tier(tier: int) -> dict:
    """Retourne les configs pour un tier donné."""
    return {
        key: cfg for key, cfg in MODEL_EMBEDDING_CONFIG.items()
        if cfg.get('tier', 3) <= tier
    }


def get_model_class(app_model: str):
    """Résout 'app_label.ModelName' -> classe Django."""
    from django.apps import apps
    app_label, model_name = app_model.split('.')
    return apps.get_model(app_label, model_name)
