# mcp/resources.py
"""MCP Resources — semi-static context data for AI clients."""
import logging

logger = logging.getLogger(__name__)

RESOURCES = [
    {
        "uri": "altiusone://entreprise",
        "name": "Company information",
        "description": "Company name, address, IDE number, VAT, legal form.",
        "mimeType": "application/json",
    },
    {
        "uri": "altiusone://utilisateur",
        "name": "Current user",
        "description": "Authenticated user info: name, role, permissions.",
        "mimeType": "application/json",
    },
    {
        "uri": "altiusone://prestations",
        "name": "Service types",
        "description": "Available service/prestation types for time tracking and invoicing.",
        "mimeType": "application/json",
    },
    {
        "uri": "altiusone://devises",
        "name": "Currencies",
        "description": "Active currencies with exchange rates.",
        "mimeType": "application/json",
    },
    {
        "uri": "graph://ontologie",
        "name": "Knowledge graph ontology",
        "description": "Entity and relation type definitions for the knowledge graph.",
        "mimeType": "application/json",
    },
]


def get_resources():
    return RESOURCES


def read_resource(uri, user):
    """Read a resource. Returns dict."""
    try:
        fn = RESOURCE_DISPATCH.get(uri)
        if not fn:
            return {"error": f"Unknown resource: {uri}"}
        return fn(user)
    except Exception as e:
        logger.error(f"MCP resource error ({uri}): {e}", exc_info=True)
        return {"error": str(e)}


def resource_entreprise(user):
    from core.models import Entreprise

    ent = Entreprise.objects.filter(est_defaut=True).select_related("adresse").first()
    if not ent:
        return {"error": "No default company configured"}

    addr = ent.adresse
    return {
        "raison_sociale": ent.raison_sociale,
        "nom_commercial": ent.nom_commercial,
        "forme_juridique": ent.forme_juridique,
        "ide_number": ent.ide_number,
        "tva_number": ent.tva_number,
        "email": ent.email,
        "telephone": ent.telephone,
        "site_web": ent.site_web,
        "adresse": {
            "rue": addr.rue if addr else None,
            "code_postal": addr.code_postal if addr else None,
            "localite": addr.localite if addr else None,
            "canton": addr.canton if addr else None,
            "pays": addr.pays if addr else None,
        } if addr else None,
    }


def resource_utilisateur(user):
    return {
        "id": str(user.pk),
        "username": user.username,
        "nom_complet": user.get_full_name(),
        "email": user.email,
        "role": user.role.nom if user.role else None,
        "role_code": user.role.code if user.role else None,
        "type_utilisateur": user.type_utilisateur,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


def resource_prestations(user):
    from facturation.models import Prestation

    prestations = Prestation.objects.filter(is_active=True).select_related("type_prestation")
    results = []
    for p in prestations.order_by("libelle")[:100]:
        results.append({
            "id": str(p.pk),
            "libelle": p.libelle,
            "type": p.type_prestation.libelle if p.type_prestation else None,
            "taux_horaire": float(p.taux_horaire) if p.taux_horaire else None,
            "mandat_id": str(p.mandat_id) if p.mandat_id else None,
        })
    return {"prestations": results, "count": len(results)}


def resource_devises(user):
    from core.models import Devise

    devises = Devise.objects.filter(actif=True).order_by("code")
    results = []
    for d in devises:
        results.append({
            "code": d.code,
            "nom": d.nom,
            "symbole": d.symbole,
            "taux_change": float(d.taux_change) if d.taux_change else None,
        })
    return {"devises": results}


def resource_ontologie(user):
    from graph.models import OntologieType

    types = OntologieType.objects.filter(is_active=True).order_by("categorie", "ordre_affichage")
    result = {"entity_types": [], "relation_types": []}

    for t in types:
        data = {
            "id": str(t.pk),
            "nom": t.nom,
            "description": t.description,
            "icone": t.icone,
            "couleur": t.couleur,
        }
        if t.categorie == "entity":
            result["entity_types"].append(data)
        else:
            data["verbe"] = t.verbe
            data["verbe_inverse"] = t.verbe_inverse
            data["bidirectionnel"] = t.bidirectionnel
            result["relation_types"].append(data)

    return result


RESOURCE_DISPATCH = {
    "altiusone://entreprise": resource_entreprise,
    "altiusone://utilisateur": resource_utilisateur,
    "altiusone://prestations": resource_prestations,
    "altiusone://devises": resource_devises,
    "graph://ontologie": resource_ontologie,
}
