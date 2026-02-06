# documents/schemas.py
"""
Schemas d'extraction personnalises pour documents fiduciaires suisses.

Ces schemas definissent les champs a extraire pour chaque type de document.
Optimises pour le contexte suisse (TVA, AVS, IBAN CH, etc.)
"""

# =============================================================================
# FACTURES
# =============================================================================

FACTURE_SCHEMA = {
    # Identification
    "numero_facture": "string",
    "date_facture": "string",
    "date_echeance": "string?",
    "reference": "string?",

    # Emetteur
    "emetteur": {
        "nom": "string",
        "adresse": "string?",
        "npa": "string?",
        "localite": "string?",
        "pays": "string?",
        "telephone": "string?",
        "email": "string?",
        "site_web": "string?",
        "numero_tva": "string?",  # CHE-123.456.789 TVA
        "numero_ide": "string?",  # CHE-123.456.789
        "iban": "string?",
    },

    # Destinataire
    "destinataire": {
        "nom": "string",
        "adresse": "string?",
        "npa": "string?",
        "localite": "string?",
        "pays": "string?",
        "numero_client": "string?",
    },

    # Montants
    "devise": "string",  # CHF, EUR
    "montant_ht": "number",
    "montant_tva": "number?",
    "taux_tva": "number?",  # 8.1, 2.6, 0
    "montant_ttc": "number",

    # Lignes de facture
    "lignes": [{
        "description": "string",
        "quantite": "number?",
        "prix_unitaire": "number?",
        "montant": "number",
    }],

    # Paiement QR-facture
    "qr_reference": "string?",  # Reference QR
    "qr_iban": "string?",
}

FACTURE_MINIMAL_SCHEMA = {
    "numero_facture": "string",
    "date_facture": "string",
    "emetteur_nom": "string",
    "destinataire_nom": "string?",
    "montant_ttc": "number",
    "devise": "string",
    "iban": "string?",
}


# =============================================================================
# CONTRATS
# =============================================================================

CONTRAT_GENERAL_SCHEMA = {
    "type_contrat": "string",  # Travail, Bail, Prestation, Vente, etc.
    "titre": "string?",
    "date_signature": "string?",
    "lieu_signature": "string?",

    # Parties
    "parties": [{
        "role": "string",  # Employeur, Employe, Bailleur, Locataire, etc.
        "nom": "string",
        "adresse": "string?",
        "npa_localite": "string?",
        "numero_ide": "string?",
    }],

    # Duree
    "date_debut": "string?",
    "date_fin": "string?",
    "duree": "string?",
    "reconduction": "string?",  # Tacite, Expresse, Non

    # Conditions financieres
    "montant": "number?",
    "devise": "string?",
    "periodicite": "string?",  # Mensuel, Annuel, Unique

    # Clauses importantes
    "delai_resiliation": "string?",
    "conditions_particulieres": "string[]?",
}

CONTRAT_TRAVAIL_SCHEMA = {
    "type_contrat": "string",  # CDI, CDD, Stage, Apprentissage
    "date_signature": "string?",

    # Employeur
    "employeur": {
        "nom": "string",
        "adresse": "string?",
        "npa_localite": "string?",
        "numero_ide": "string?",
    },

    # Employe
    "employe": {
        "nom": "string",
        "prenom": "string",
        "date_naissance": "string?",
        "adresse": "string?",
        "npa_localite": "string?",
        "nationalite": "string?",
        "numero_avs": "string?",  # 756.1234.5678.90
        "permis_travail": "string?",  # B, C, L, G
    },

    # Poste
    "fonction": "string",
    "taux_activite": "number?",  # 100, 80, 50
    "lieu_travail": "string?",
    "date_debut": "string",
    "date_fin": "string?",  # Pour CDD

    # Remuneration
    "salaire_brut": "number",
    "devise": "string",
    "periodicite_salaire": "string",  # Mensuel, Horaire, Annuel
    "nombre_salaires": "number?",  # 12, 13
    "bonus": "string?",

    # Conges et horaires
    "jours_vacances": "number?",
    "horaire_hebdomadaire": "number?",

    # Prevoyance
    "caisse_pension": "string?",
    "assurance_accident": "string?",

    # Resiliation
    "delai_preavis": "string?",
    "periode_essai": "string?",
}

CONTRAT_BAIL_SCHEMA = {
    "type_bail": "string",  # Habitation, Commercial, Parking
    "date_signature": "string?",

    # Bailleur
    "bailleur": {
        "nom": "string",
        "adresse": "string?",
        "telephone": "string?",
        "email": "string?",
    },

    # Locataire
    "locataire": {
        "nom": "string",
        "adresse_actuelle": "string?",
        "telephone": "string?",
        "email": "string?",
    },

    # Objet loue
    "adresse_bien": "string",
    "type_bien": "string?",  # Appartement, Bureau, Local, Parking
    "nombre_pieces": "number?",
    "surface_m2": "number?",
    "etage": "string?",

    # Duree
    "date_debut": "string",
    "date_fin": "string?",
    "duree_bail": "string?",

    # Loyer
    "loyer_mensuel": "number",
    "charges": "number?",
    "loyer_total": "number?",
    "devise": "string",
    "garantie_loyer": "number?",
    "banque_garantie": "string?",

    # Conditions
    "animaux_autorises": "boolean?",
    "sous_location": "boolean?",
    "delai_resiliation": "string?",
}


# =============================================================================
# FICHES DE SALAIRE
# =============================================================================

FICHE_SALAIRE_SCHEMA = {
    # Periode
    "mois": "string",
    "annee": "number",
    "periode": "string?",  # Janvier 2024

    # Employeur
    "employeur": {
        "nom": "string",
        "adresse": "string?",
        "numero_ide": "string?",
    },

    # Employe
    "employe": {
        "nom": "string",
        "prenom": "string",
        "numero_avs": "string?",
        "date_naissance": "string?",
        "date_entree": "string?",
        "fonction": "string?",
        "taux_activite": "number?",
    },

    # Salaire brut
    "salaire_base": "number",
    "heures_supplementaires": "number?",
    "primes": "number?",
    "commissions": "number?",
    "indemnites": "number?",
    "allocations_familiales": "number?",
    "salaire_brut_total": "number",

    # Deductions
    "avs_ai_apg": "number?",
    "taux_avs": "number?",
    "assurance_chomage": "number?",
    "taux_ac": "number?",
    "lpp": "number?",  # 2eme pilier
    "aanp": "number?",  # Accident non-pro
    "assurance_maladie": "number?",
    "impot_source": "number?",
    "taux_impot_source": "number?",
    "autres_deductions": "number?",
    "total_deductions": "number",

    # Net
    "salaire_net": "number",
    "devise": "string",

    # Versement
    "iban": "string?",
    "date_versement": "string?",

    # Cumuls annuels
    "cumul_brut_annuel": "number?",
    "cumul_net_annuel": "number?",
}


# =============================================================================
# RELEVES BANCAIRES
# =============================================================================

RELEVE_BANCAIRE_SCHEMA = {
    # Compte
    "banque": "string",
    "iban": "string?",
    "numero_compte": "string?",
    "titulaire": "string",
    "devise": "string",

    # Periode
    "date_debut": "string",
    "date_fin": "string",

    # Soldes
    "solde_initial": "number",
    "solde_final": "number",
    "total_credits": "number?",
    "total_debits": "number?",

    # Mouvements (optionnel, peut etre tres long)
    "nombre_operations": "number?",
    "operations": [{
        "date": "string",
        "libelle": "string",
        "montant": "number",
        "type": "string?",  # Credit, Debit
    }],
}


# =============================================================================
# DECLARATIONS TVA
# =============================================================================

DECLARATION_TVA_SCHEMA = {
    # Identification
    "numero_tva": "string",
    "raison_sociale": "string",
    "periode": "string",  # T1 2024, Janvier 2024
    "methode": "string?",  # Effective, Forfait, TDFN

    # Chiffre d'affaires
    "ca_total": "number",
    "ca_exonere": "number?",
    "ca_imposable": "number",

    # TVA due
    "tva_normale": "number?",  # 8.1%
    "tva_reduite": "number?",  # 2.6%
    "tva_hebergement": "number?",  # 3.8%
    "tva_totale_due": "number",

    # TVA deductible
    "tva_deductible_achats": "number?",
    "tva_deductible_investissements": "number?",
    "tva_totale_deductible": "number?",

    # Solde
    "tva_a_payer": "number?",
    "tva_a_recuperer": "number?",

    "date_declaration": "string?",
}


# =============================================================================
# ATTESTATIONS ET CERTIFICATS
# =============================================================================

ATTESTATION_SCHEMA = {
    "type_attestation": "string",  # Domicile, Travail, Etudes, etc.
    "date_emission": "string",
    "lieu_emission": "string?",

    # Emetteur
    "emetteur": {
        "nom": "string",
        "fonction": "string?",
        "organisation": "string?",
        "adresse": "string?",
        "telephone": "string?",
        "email": "string?",
    },

    # Beneficiaire
    "beneficiaire": {
        "nom": "string",
        "prenom": "string?",
        "date_naissance": "string?",
        "adresse": "string?",
        "numero_avs": "string?",
    },

    # Contenu
    "objet": "string?",
    "contenu_principal": "string?",
    "validite": "string?",
    "numero_reference": "string?",
}

CERTIFICAT_SALAIRE_SCHEMA = {
    # Annee fiscale
    "annee": "number",

    # Employeur
    "employeur": {
        "nom": "string",
        "adresse": "string?",
        "numero_ide": "string?",
    },

    # Employe
    "employe": {
        "nom": "string",
        "prenom": "string",
        "numero_avs": "string",
        "date_naissance": "string?",
        "adresse": "string?",
    },

    # Revenus
    "salaire_brut": "number",
    "indemnites_frais": "number?",
    "prestations_nature": "number?",  # Voiture, logement
    "actions_participations": "number?",
    "autres_revenus": "number?",
    "revenu_total": "number",

    # Deductions
    "cotisations_avs": "number?",
    "cotisations_lpp": "number?",
    "cotisations_3a": "number?",
    "impot_source_retenu": "number?",

    # Informations complementaires
    "taux_activite_moyen": "number?",
    "nombre_enfants": "number?",
    "transport_domicile_travail": "string?",
}


# =============================================================================
# DEVIS / OFFRES
# =============================================================================

DEVIS_SCHEMA = {
    "numero_devis": "string",
    "date_devis": "string",
    "validite": "string?",  # 30 jours, jusqu'au 31.12.2024

    # Emetteur
    "emetteur": {
        "nom": "string",
        "adresse": "string?",
        "telephone": "string?",
        "email": "string?",
        "numero_tva": "string?",
    },

    # Client
    "client": {
        "nom": "string",
        "adresse": "string?",
        "reference": "string?",
    },

    # Objet
    "objet": "string",
    "description": "string?",

    # Montants
    "montant_ht": "number",
    "taux_tva": "number?",
    "montant_tva": "number?",
    "montant_ttc": "number",
    "devise": "string",

    # Lignes
    "lignes": [{
        "description": "string",
        "quantite": "number?",
        "unite": "string?",
        "prix_unitaire": "number?",
        "montant": "number",
    }],

    # Conditions
    "delai_execution": "string?",
    "conditions_paiement": "string?",
    "conditions_particulieres": "string?",
}


# =============================================================================
# CORRESPONDANCE / COURRIERS
# =============================================================================

CORRESPONDANCE_SCHEMA = {
    "type": "string",  # Lettre, Email, Fax
    "date": "string",
    "reference": "string?",

    # Expediteur
    "expediteur": {
        "nom": "string",
        "organisation": "string?",
        "adresse": "string?",
        "telephone": "string?",
        "email": "string?",
    },

    # Destinataire
    "destinataire": {
        "nom": "string",
        "organisation": "string?",
        "adresse": "string?",
    },

    # Contenu
    "objet": "string?",
    "resume": "string?",  # Resume du contenu
    "pieces_jointes": "string[]?",

    # Actions requises
    "action_requise": "string?",
    "delai_reponse": "string?",
}


# =============================================================================
# MAPPING TYPE DOCUMENT -> SCHEMA
# =============================================================================

DOCUMENT_TYPE_SCHEMAS = {
    # Factures
    'FACTURE_ACHAT': FACTURE_SCHEMA,
    'FACTURE_VENTE': FACTURE_SCHEMA,
    'FACTURE': FACTURE_SCHEMA,

    # Contrats
    'CONTRAT': CONTRAT_GENERAL_SCHEMA,
    'CONTRAT_TRAVAIL': CONTRAT_TRAVAIL_SCHEMA,
    'CONTRAT_BAIL': CONTRAT_BAIL_SCHEMA,

    # Salaires
    'FICHE_SALAIRE': FICHE_SALAIRE_SCHEMA,
    'CERTIFICAT_SALAIRE': CERTIFICAT_SALAIRE_SCHEMA,

    # Banque
    'RELEVE_BANQUE': RELEVE_BANCAIRE_SCHEMA,
    'EXTRAIT_BANCAIRE': RELEVE_BANCAIRE_SCHEMA,

    # Fiscal
    'DECLARATION_TVA': DECLARATION_TVA_SCHEMA,

    # Attestations
    'ATTESTATION': ATTESTATION_SCHEMA,

    # Devis
    'DEVIS': DEVIS_SCHEMA,
    'OFFRE': DEVIS_SCHEMA,

    # Correspondance
    'CORRESPONDANCE': CORRESPONDANCE_SCHEMA,
    'COURRIER': CORRESPONDANCE_SCHEMA,
    'EMAIL': CORRESPONDANCE_SCHEMA,
}


def get_schema_for_document_type(document_type: str) -> dict:
    """
    Retourne le schema d'extraction pour un type de document.

    Args:
        document_type: Type de document (FACTURE_ACHAT, CONTRAT_TRAVAIL, etc.)

    Returns:
        Schema dict ou schema generique si type inconnu
    """
    return DOCUMENT_TYPE_SCHEMAS.get(document_type.upper(), CORRESPONDANCE_SCHEMA)


def get_available_document_types() -> list:
    """Retourne la liste des types de documents supportes."""
    return list(DOCUMENT_TYPE_SCHEMAS.keys())
