# AltiusOne/api_root.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(["GET"])
def api_root(request, format=None):
    """
    Point d'entrée de l'API AltiusOne v1.
    Liste tous les endpoints disponibles organisés par module.
    """
    return Response(
        {
            # ============================================
            # CORE - Gestion des entités principales
            # ============================================
            "core": {
                "users": reverse("core-user-list", request=request, format=format),
                "clients": reverse("core-client-list", request=request, format=format),
                "contacts": reverse("core-contact-list", request=request, format=format),
                "mandats": reverse("core-mandat-list", request=request, format=format),
                "exercices": reverse("core-exercice-list", request=request, format=format),
                "audit-logs": reverse("core-auditlog-list", request=request, format=format),
                "notifications": reverse(
                    "core-notification-list", request=request, format=format
                ),
                "taches": reverse("core-tache-list", request=request, format=format),
            },
            # ============================================
            # COMPTABILITE - Gestion comptable
            # ============================================
            "comptabilite": {
                "plans-comptables": reverse(
                    "compta-plan-comptable-list", request=request, format=format
                ),
                "comptes": reverse("compta-compte-list", request=request, format=format),
                "journaux": reverse("compta-journal-list", request=request, format=format),
                "ecritures": reverse("compta-ecriture-list", request=request, format=format),
                "pieces": reverse("compta-piece-list", request=request, format=format),
                "lettrages": reverse("compta-lettrage-list", request=request, format=format),
                "rapports": reverse("compta-rapport-list", request=request, format=format),
            },
            # ============================================
            # TVA - Gestion de la TVA
            # ============================================
            "tva": {
                "configurations": reverse(
                    "tva-configuration-list", request=request, format=format
                ),
                "taux": reverse("tva-taux-list", request=request, format=format),
                "codes": reverse("tva-code-list", request=request, format=format),
                "declarations": reverse(
                    "tva-declaration-list", request=request, format=format
                ),
                "lignes": reverse("tva-ligne-list", request=request, format=format),
                "operations": reverse("tva-operation-list", request=request, format=format),
                "corrections": reverse(
                    "tva-correction-list", request=request, format=format
                ),
            },
            # ============================================
            # FACTURATION - Facturation et paiements
            # ============================================
            "facturation": {
                "prestations": reverse(
                    "factu-prestation-list", request=request, format=format
                ),
                "temps": reverse("factu-temps-list", request=request, format=format),
                "factures": reverse("factu-facture-list", request=request, format=format),
                "lignes": reverse("factu-ligne-list", request=request, format=format),
                "paiements": reverse("factu-paiement-list", request=request, format=format),
                "relances": reverse("factu-relance-list", request=request, format=format),
            },
            # ============================================
            # SALAIRES - Gestion des salaires
            # ============================================
            "salaires": {
                "employes": reverse("salaires-employe-list", request=request, format=format),
                "taux-cotisations": reverse(
                    "salaires-taux-cotisation-list", request=request, format=format
                ),
                "fiches-salaire": reverse("salaires-fiche-list", request=request, format=format),
                "certificats": reverse(
                    "salaires-certificat-list", request=request, format=format
                ),
                "declarations": reverse(
                    "salaires-declaration-list", request=request, format=format
                ),
            },
            # ============================================
            # DOCUMENTS - Gestion documentaire et Chat IA
            # ============================================
            "documents": {
                "dossiers": reverse("docs-dossier-list", request=request, format=format),
                "types": reverse("docs-type-list", request=request, format=format),
                "documents": reverse("docs-document-list", request=request, format=format),
                "chat-conversations": reverse(
                    "docs-conversation-list", request=request, format=format
                ),
                "chat-health": reverse("chat-health", request=request, format=format),
                "chat-search": reverse("chat-search", request=request, format=format),
                "chat-quick": reverse("chat-quick", request=request, format=format),
            },
            # ============================================
            # FISCALITE - Gestion fiscale
            # ============================================
            "fiscalite": {
                "declarations": reverse(
                    "fisc-declaration-list", request=request, format=format
                ),
                "annexes": reverse("fisc-annexe-list", request=request, format=format),
                "corrections": reverse(
                    "fisc-correction-list", request=request, format=format
                ),
                "reports-pertes": reverse(
                    "fisc-report-perte-list", request=request, format=format
                ),
                "taux-imposition": reverse(
                    "fisc-taux-list", request=request, format=format
                ),
                "optimisations": reverse(
                    "fisc-optimisation-list", request=request, format=format
                ),
            },
            # ============================================
            # ANALYTICS - Tableaux de bord et rapports
            # ============================================
            "analytics": {
                "tableaux-bord": reverse(
                    "analytics-tableau-bord-list", request=request, format=format
                ),
                "indicateurs": reverse(
                    "analytics-indicateur-list", request=request, format=format
                ),
                "valeurs": reverse("analytics-valeur-list", request=request, format=format),
                "rapports": reverse("analytics-rapport-list", request=request, format=format),
                "planifications": reverse(
                    "analytics-planification-list", request=request, format=format
                ),
                "comparaisons": reverse(
                    "analytics-comparaison-list", request=request, format=format
                ),
                "alertes": reverse("analytics-alerte-list", request=request, format=format),
                "exports": reverse("analytics-export-list", request=request, format=format),
            },
            # ============================================
            # MAILING - Gestion des emails
            # ============================================
            "mailing": {
                "configurations": reverse(
                    "mailing-configuration-list", request=request, format=format
                ),
                "templates": reverse(
                    "mailing-template-list", request=request, format=format
                ),
                "envoyes": reverse(
                    "mailing-envoye-list", request=request, format=format
                ),
                "recus": reverse("mailing-recu-list", request=request, format=format),
            },
            # ============================================
            # EDITEUR - Edition collaborative
            # ============================================
            "editeur": {
                "documents": reverse("editeur-document-list", request=request, format=format),
                "modeles": reverse("editeur-modele-list", request=request, format=format),
                "health": reverse("docs_health", request=request, format=format),
            },
        }
    )
