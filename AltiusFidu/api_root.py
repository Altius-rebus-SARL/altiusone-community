# AltiusFidu/api_root.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "core": {
                "users": reverse("user-list", request=request, format=format),
                "clients": reverse("client-list", request=request, format=format),
                "contacts": reverse("contact-list", request=request, format=format),
                "mandats": reverse("mandat-list", request=request, format=format),
                "exercices": reverse("exercice-list", request=request, format=format),
                "notifications": reverse(
                    "notification-list", request=request, format=format
                ),
                "taches": reverse("tache-list", request=request, format=format),
            },
            "comptabilite": {
                "plans-comptables": reverse(
                    "plancomptable-list", request=request, format=format
                ),
                "comptes": reverse("compte-list", request=request, format=format),
                "journaux": reverse("journal-list", request=request, format=format),
                "ecritures": reverse(
                    "ecriturecomptable-list", request=request, format=format
                ),
            },
            "tva": {
                "configurations": reverse(
                    "configurationtva-list", request=request, format=format
                ),
                "declarations": reverse(
                    "declarationtva-list", request=request, format=format
                ),
                "codes": reverse("codetva-list", request=request, format=format),
            },
            "facturation": {
                "factures": reverse("facture-list", request=request, format=format),
                "prestations": reverse(
                    "prestation-list", request=request, format=format
                ),
                "paiements": reverse("paiement-list", request=request, format=format),
            },
            "salaires": {
                "employes": reverse("employe-list", request=request, format=format),
                "fiches-salaire": reverse(
                    "fichesalaire-list", request=request, format=format
                ),
            },
            "documents": {
                "dossiers": reverse("dossier-list", request=request, format=format),
                "documents": reverse("document-list", request=request, format=format),
            },
            "analytics": {
                "tableaux-bord": reverse(
                    "tableaubord-list", request=request, format=format
                ),
                "indicateurs": reverse(
                    "indicateur-list", request=request, format=format
                ),
                "rapports": reverse("rapport-list", request=request, format=format),
            },
        }
    )
