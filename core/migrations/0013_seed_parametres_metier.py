# core/migrations/0013_seed_parametres_metier.py
"""Seed initial ParametreMetier data from all hardcoded CHOICES."""
from django.db import migrations


# ============================================================================
# Données initiales par module/catégorie
# Format: (module, categorie, code, libelle, ordre, systeme)
# ============================================================================

PARAMETRES = [
    # =========================================================================
    # CORE
    # =========================================================================
    # Type de mandat
    ('core', 'type_mandat', 'COMPTA', 'Comptabilité', 10, True),
    ('core', 'type_mandat', 'TVA', 'TVA', 20, True),
    ('core', 'type_mandat', 'SALAIRES', 'Salaires', 30, True),
    ('core', 'type_mandat', 'FISCALITE', 'Fiscalité', 40, True),
    ('core', 'type_mandat', 'AUDIT', 'Audit', 50, True),
    ('core', 'type_mandat', 'CONSEILS', 'Conseils', 60, True),
    ('core', 'type_mandat', 'GLOBAL', 'Mandat global', 70, True),
    # Périodicité
    ('core', 'periodicite', 'MENSUEL', 'Mensuel', 10, True),
    ('core', 'periodicite', 'TRIMESTRIEL', 'Trimestriel', 20, True),
    ('core', 'periodicite', 'SEMESTRIEL', 'Semestriel', 30, True),
    ('core', 'periodicite', 'ANNUEL', 'Annuel', 40, True),
    ('core', 'periodicite', 'PONCTUEL', 'Ponctuel', 50, True),
    # Type de facturation
    ('core', 'type_facturation', 'FORFAIT', 'Forfait', 10, True),
    ('core', 'type_facturation', 'HORAIRE', 'Taux horaire', 20, True),
    ('core', 'type_facturation', 'MIXTE', 'Mixte', 30, True),
    # Forme juridique
    ('core', 'forme_juridique', 'EI', 'Entreprise individuelle', 10, True),
    ('core', 'forme_juridique', 'RC', 'Raison collective', 20, True),
    ('core', 'forme_juridique', 'SC', 'Société en commandite', 30, True),
    ('core', 'forme_juridique', 'SA', 'Société anonyme', 40, True),
    ('core', 'forme_juridique', 'SARL', 'Société à responsabilité limitée', 50, True),
    ('core', 'forme_juridique', 'COOP', 'Coopérative', 60, True),
    ('core', 'forme_juridique', 'FOND', 'Fondation', 70, True),
    # Type de tiers
    ('core', 'type_tiers', 'FOURNISSEUR', 'Fournisseur', 10, True),
    ('core', 'type_tiers', 'CLIENT', 'Client', 20, True),
    ('core', 'type_tiers', 'EMPLOYE', 'Employé', 30, True),
    ('core', 'type_tiers', 'PRETEUR', 'Prêteur', 40, True),
    ('core', 'type_tiers', 'AUTRE', 'Autre', 50, True),
    # Priorité
    ('core', 'priorite', 'BASSE', 'Basse', 10, True),
    ('core', 'priorite', 'NORMALE', 'Normale', 20, True),
    ('core', 'priorite', 'HAUTE', 'Haute', 30, True),
    ('core', 'priorite', 'URGENTE', 'Urgente', 40, True),
    # Fonction contact
    ('core', 'fonction_contact', 'DIRECTEUR', 'Directeur', 10, True),
    ('core', 'fonction_contact', 'GERANT', 'Gérant', 20, True),
    ('core', 'fonction_contact', 'ADMIN', 'Administrateur', 30, True),
    ('core', 'fonction_contact', 'COMPTABLE', 'Comptable', 40, True),
    ('core', 'fonction_contact', 'RESPONSABLE_RH', 'Responsable RH', 50, True),
    ('core', 'fonction_contact', 'RESPONSABLE_VENTES', 'Responsable ventes', 60, True),
    ('core', 'fonction_contact', 'AUTRE', 'Autre', 70, True),

    # =========================================================================
    # SALAIRES
    # =========================================================================
    # Type de contrat
    ('salaires', 'type_contrat', 'CDI', 'Contrat durée indéterminée', 10, True),
    ('salaires', 'type_contrat', 'CDD', 'Contrat durée déterminée', 20, True),
    ('salaires', 'type_contrat', 'APPRENTI', 'Apprentissage', 30, True),
    ('salaires', 'type_contrat', 'STAGE', 'Stage', 40, True),
    # Type de cotisation
    ('salaires', 'type_cotisation', 'AVS', 'AVS/AI/APG', 10, True),
    ('salaires', 'type_cotisation', 'AC', 'Assurance chômage', 20, True),
    ('salaires', 'type_cotisation', 'LAA', 'Assurance accidents', 30, True),
    ('salaires', 'type_cotisation', 'LPP', 'Prévoyance professionnelle', 40, True),
    ('salaires', 'type_cotisation', 'CAF', 'Allocations familiales', 50, True),
    ('salaires', 'type_cotisation', 'CANTONALE', 'Cotisation cantonale', 60, False),
    ('salaires', 'type_cotisation', 'COMMUNALE', 'Cotisation communale', 70, False),
    ('salaires', 'type_cotisation', 'AUTRE', 'Autre cotisation', 80, False),
    # Type d'allocation
    ('salaires', 'type_allocation', 'NAISSANCE', 'Allocation de naissance', 10, True),
    ('salaires', 'type_allocation', 'ENFANT', 'Allocation pour enfant (0-16 ans)', 20, True),
    ('salaires', 'type_allocation', 'FORMATION', 'Allocation de formation (16-25 ans)', 30, True),
    ('salaires', 'type_allocation', 'INTEGRATION', "Allocation d'intégration", 40, False),
    # Organisme déclaration
    ('salaires', 'organisme_declaration', 'AVS', 'Caisse AVS/AI/APG/AC', 10, True),
    ('salaires', 'organisme_declaration', 'LPP', 'Institution de prévoyance LPP', 20, True),
    ('salaires', 'organisme_declaration', 'LAA', 'Assurance accidents LAA/LAAC', 30, True),
    ('salaires', 'organisme_declaration', 'CAF', 'Caisse allocations familiales', 40, True),
    ('salaires', 'organisme_declaration', 'IJM', 'Assurance indemnités journalières maladie', 50, True),
    # Type certificat travail
    ('salaires', 'type_certificat_travail', 'COMPLET', 'Certificat complet (qualifié)', 10, True),
    ('salaires', 'type_certificat_travail', 'SIMPLE', 'Attestation de travail (simple)', 20, True),
    ('salaires', 'type_certificat_travail', 'INTERMEDIAIRE', 'Certificat intermédiaire', 30, True),
    # Motif de départ
    ('salaires', 'motif_depart', 'DEMISSION', 'Démission', 10, True),
    ('salaires', 'motif_depart', 'FIN_CONTRAT', 'Fin de contrat', 20, True),
    ('salaires', 'motif_depart', 'LICENCIEMENT', 'Licenciement', 30, True),
    ('salaires', 'motif_depart', 'MUTUELLEMENT', 'Résiliation mutuelle', 40, True),
    ('salaires', 'motif_depart', 'DECES', 'Décès', 50, True),
    ('salaires', 'motif_depart', 'AUTRE', 'Autre', 60, True),

    # =========================================================================
    # FACTURATION
    # =========================================================================
    # Type de facture
    ('facturation', 'type_facture', 'FACTURE', 'Facture', 10, True),
    ('facturation', 'type_facture', 'DEVIS', 'Devis', 20, True),
    ('facturation', 'type_facture', 'AVOIR', 'Avoir', 30, True),
    ('facturation', 'type_facture', 'ACOMPTE', "Facture d'acompte", 40, True),
    # Mode de paiement
    ('facturation', 'mode_paiement', 'VIREMENT', 'Virement bancaire', 10, True),
    ('facturation', 'mode_paiement', 'QR_BILL', 'QR-Bill', 20, True),
    ('facturation', 'mode_paiement', 'CARTE', 'Carte bancaire', 30, True),
    ('facturation', 'mode_paiement', 'ESPECE', 'Espèces', 40, True),
    ('facturation', 'mode_paiement', 'CHEQUE', 'Chèque', 50, True),
    ('facturation', 'mode_paiement', 'VIREMENT_INTERNATIONAL', 'Virement international', 60, False),
    ('facturation', 'mode_paiement', 'CRYPTO', 'Cryptomonnaie', 70, False),
    ('facturation', 'mode_paiement', 'AUTRE', 'Autre', 80, False),

    # =========================================================================
    # COMPTABILITE
    # =========================================================================
    # Type de journal
    ('comptabilite', 'type_journal', 'VTE', 'Ventes', 10, True),
    ('comptabilite', 'type_journal', 'ACH', 'Achats', 20, True),
    ('comptabilite', 'type_journal', 'BNQ', 'Banque', 30, True),
    ('comptabilite', 'type_journal', 'CAI', 'Caisse', 40, True),
    ('comptabilite', 'type_journal', 'OD', 'Opérations diverses', 50, True),
    ('comptabilite', 'type_journal', 'SALAIRES', 'Salaires', 60, True),
    ('comptabilite', 'type_journal', 'TVA', 'TVA', 70, True),
    # Type de compte bancaire
    ('comptabilite', 'type_compte_bancaire', 'COURANT', 'Compte courant', 10, True),
    ('comptabilite', 'type_compte_bancaire', 'EPARGNE', 'Compte épargne', 20, True),
    ('comptabilite', 'type_compte_bancaire', 'SALAIRE', 'Compte salaire', 30, True),
    ('comptabilite', 'type_compte_bancaire', 'TITRE', 'Compte titres', 40, True),

    # =========================================================================
    # FISCALITE
    # =========================================================================
    # Type de déclaration
    ('fiscalite', 'type_declaration', 'PERSONNE_PHYSIQUE', 'Personne physique', 10, True),
    ('fiscalite', 'type_declaration', 'PERSONNE_MORALE', 'Personne morale', 20, True),
    # Type d'impôt
    ('fiscalite', 'type_impot', 'IFD', 'Impôt fédéral direct (IFD)', 10, True),
    ('fiscalite', 'type_impot', 'ICC', 'Impôt cantonal et communal (ICC)', 20, True),
    ('fiscalite', 'type_impot', 'BENEFICE', 'Impôt sur le bénéfice', 30, True),
    ('fiscalite', 'type_impot', 'CAPITAL', 'Impôt sur le capital', 40, True),
    ('fiscalite', 'type_impot', 'PATRIMOINE', 'Impôt sur le patrimoine', 50, True),
    ('fiscalite', 'type_impot', 'SUCCESSION', 'Impôt de succession/donation', 60, False),
    ('fiscalite', 'type_impot', 'PLUS_VALUE', 'Impôt sur les plus-values', 70, False),
    ('fiscalite', 'type_impot', 'AUTRE', 'Autre impôt', 80, False),
    # Type d'annexe
    ('fiscalite', 'type_annexe', 'BILAN', 'Bilan fiscal', 10, True),
    ('fiscalite', 'type_annexe', 'COMPTE_RESULTATS', 'Compte de résultats', 20, True),
    ('fiscalite', 'type_annexe', 'TABLEAU_AMORTISSEMENTS', 'Tableau des amortissements', 30, True),
    ('fiscalite', 'type_annexe', 'TABLEAU_PROVISIONS', 'Tableau des provisions', 40, True),
    ('fiscalite', 'type_annexe', 'CALCUL_IMPOT', "Calcul de l'impôt", 50, True),
    ('fiscalite', 'type_annexe', 'ANNEXE_GENERALE', 'Annexe générale', 60, True),
    ('fiscalite', 'type_annexe', 'AUTRE', 'Autre annexe', 70, False),
    # Type de correction fiscale
    ('fiscalite', 'type_correction', 'AMORTISSEMENT', 'Amortissement supplémentaire', 10, True),
    ('fiscalite', 'type_correction', 'PROVISION', 'Provision non admise', 20, True),
    ('fiscalite', 'type_correction', 'CHARGE_NON_DEDUCTIBLE', 'Charge non déductible', 30, True),
    ('fiscalite', 'type_correction', 'BENEFICE_NON_IMPOSABLE', 'Bénéfice non imposable', 40, True),
    ('fiscalite', 'type_correction', 'PLUS_VALUE_EXONERATION', 'Plus-value exonérée', 50, True),
    ('fiscalite', 'type_correction', 'AUTRE', 'Autre correction', 60, False),
    # Catégorie optimisation
    ('fiscalite', 'categorie_optimisation', 'AMORTISSEMENT', 'Amortissement accéléré', 10, True),
    ('fiscalite', 'categorie_optimisation', 'PROVISION', 'Constitution provisions', 20, True),
    ('fiscalite', 'categorie_optimisation', 'INVESTISSEMENT', 'Investissements déductibles', 30, True),
    ('fiscalite', 'categorie_optimisation', 'ORGANISATION', 'Optimisation organisation', 40, True),
    ('fiscalite', 'categorie_optimisation', 'AUTRE', 'Autre optimisation', 50, False),

    # =========================================================================
    # TVA
    # =========================================================================
    # Méthode de calcul TVA
    ('tva', 'methode_calcul', 'EFFECTIVE', 'Méthode effective', 10, True),
    ('tva', 'methode_calcul', 'TAUX_DETTE', 'Méthode des taux de la dette fiscale nette', 20, True),
    ('tva', 'methode_calcul', 'TAUX_FORFAITAIRE', 'Méthode des taux forfaitaires', 30, True),
    ('tva', 'methode_calcul', 'DEDUCTIBLE', 'Sur la base du déductible', 40, True),
    ('tva', 'methode_calcul', 'REGIME_SPECIAL_AGRICOLE', 'Régime spécial agricole', 50, False),
    # Type de taux TVA
    ('tva', 'type_taux_tva', 'NORMAL', 'Taux normal', 10, True),
    ('tva', 'type_taux_tva', 'REDUIT', 'Taux réduit', 20, True),
    ('tva', 'type_taux_tva', 'SPECIAL', 'Taux spécial hébergement', 30, True),
    ('tva', 'type_taux_tva', 'TRES_REDUIT', 'Taux très réduit', 40, False),
    ('tva', 'type_taux_tva', 'ZERO', 'Taux zéro', 50, True),

    # =========================================================================
    # DOCUMENTS
    # =========================================================================
    # Type de document
    ('documents', 'type_document', 'FACTURE_VENTE', 'Facture de vente', 10, True),
    ('documents', 'type_document', 'FACTURE_ACHAT', "Facture d'achat", 20, True),
    ('documents', 'type_document', 'DEVIS', 'Devis', 30, True),
    ('documents', 'type_document', 'AVOIR', 'Avoir', 40, True),
    ('documents', 'type_document', 'BON_COMMANDE', 'Bon de commande', 50, True),
    ('documents', 'type_document', 'BILAN', 'Bilan', 60, True),
    ('documents', 'type_document', 'FICHE_SALAIRE', 'Fiche de salaire', 70, True),
    ('documents', 'type_document', 'DECLARATION_TVA', 'Déclaration TVA', 80, True),
    ('documents', 'type_document', 'DECLARATION_FISCALE', 'Déclaration fiscale', 90, True),
    ('documents', 'type_document', 'CONTRAT', 'Contrat', 100, True),
    ('documents', 'type_document', 'RAPPORT', 'Rapport', 110, True),
    ('documents', 'type_document', 'AUTRE', 'Autre', 120, False),

    # =========================================================================
    # PROJETS
    # =========================================================================
    # Statut projet
    ('projets', 'statut_projet', 'PLANIFIE', 'Planifié', 10, True),
    ('projets', 'statut_projet', 'EN_COURS', 'En cours', 20, True),
    ('projets', 'statut_projet', 'TERMINE', 'Terminé', 30, True),
    ('projets', 'statut_projet', 'ANNULE', 'Annulé', 40, True),
]


def seed_parametres(apps, schema_editor):
    ParametreMetier = apps.get_model('core', 'ParametreMetier')
    for module, categorie, code, libelle, ordre, systeme in PARAMETRES:
        ParametreMetier.objects.get_or_create(
            module=module,
            categorie=categorie,
            code=code,
            defaults={
                'libelle': libelle,
                'ordre': ordre,
                'systeme': systeme,
                'is_active': True,
            }
        )


def reverse_seed(apps, schema_editor):
    ParametreMetier = apps.get_model('core', 'ParametreMetier')
    ParametreMetier.objects.filter(systeme=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_add_parametre_metier'),
    ]

    operations = [
        migrations.RunPython(seed_parametres, reverse_seed),
    ]
