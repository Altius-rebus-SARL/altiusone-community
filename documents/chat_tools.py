# documents/chat_tools.py
"""
Definitions des tools pour l'assistant IA (function calling).

Chaque tool correspond a une recherche ORM directe.
Le LLM decide quels outils appeler en fonction de la question.

Ces fonctions sont independantes de universal_search.py
(qui sert a la navbar).
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Q, Sum

logger = logging.getLogger(__name__)


# =========================================================================
# TOOL DEFINITIONS (format Ollama / OpenAI function calling)
# =========================================================================

CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_clients",
            "description": "Recherche des clients par nom, raison sociale, IDE, email ou numero TVA. Utilise cet outil quand l'utilisateur pose une question sur un client ou une entreprise.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Terme de recherche (nom, raison sociale, IDE, email...)",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_mandats",
            "description": "Recherche des mandats par numero, nom du client, type ou statut. Utilise cet outil quand l'utilisateur pose une question sur un mandat ou contrat de service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Terme de recherche (numero de mandat, nom du client...)",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_factures",
            "description": "Recherche des factures par numero, nom du client, statut ou montant. Utilise cet outil quand l'utilisateur pose une question sur des factures, montants ou paiements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Terme de recherche (numero de facture, nom du client, statut...)",
                    },
                    "statut": {
                        "type": "string",
                        "description": "Filtrer par statut: BROUILLON, EMISE, ENVOYEE, PAYEE, EN_RETARD, ANNULEE",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_employes",
            "description": "Recherche des employes par nom, prenom, matricule ou mandat. Utilise cet outil quand l'utilisateur pose une question sur des employes ou du personnel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Terme de recherche (nom, prenom, matricule, nom du mandat/client...)",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_ecritures",
            "description": "Recherche des ecritures comptables par libelle, numero de piece, compte ou montant. Utilise cet outil quand l'utilisateur pose une question sur la comptabilite, des ecritures ou des comptes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Terme de recherche (libelle, numero de piece, numero de compte...)",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Recherche des documents GED par nom de fichier, contenu OCR ou type. Utilise cet outil quand l'utilisateur pose une question sur des documents, fichiers ou pieces justificatives.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Terme de recherche (nom de fichier, contenu, type de document...)",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_taches",
            "description": "Recherche des taches/operations de projet par titre, description ou statut. Utilise cet outil quand l'utilisateur pose une question sur des taches, operations ou projets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Terme de recherche (titre, description, nom du projet...)",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_semantic",
            "description": "Recherche semantique dans toutes les entites (clients, factures, employes, ecritures, documents, etc.) en utilisant la similarite vectorielle. Utilise cet outil quand la recherche par mots-cles ne suffit pas ou quand l'utilisateur cherche quelque chose de vague ou conceptuel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Description en langage naturel de ce que tu cherches",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


# =========================================================================
# TOOL EXECUTION
# =========================================================================

def execute_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    user,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Execute un tool call et retourne le resultat + les sources.

    Args:
        tool_name: Nom de l'outil
        arguments: Arguments du tool call
        user: Utilisateur Django (pour filtrage des permissions)

    Returns:
        Tuple (texte_resultat, liste_sources)
        - texte_resultat: texte structure pour le LLM
        - liste_sources: metadonnees des entites (pour les chips UI)
    """
    handlers = {
        "search_clients": _search_clients,
        "search_mandats": _search_mandats,
        "search_factures": _search_factures,
        "search_employes": _search_employes,
        "search_ecritures": _search_ecritures,
        "search_documents": _search_documents,
        "search_taches": _search_taches,
        "search_semantic": _search_semantic,
    }

    handler = handlers.get(tool_name)
    if not handler:
        logger.warning(f"Tool inconnu: {tool_name}")
        return f"Outil '{tool_name}' non disponible.", []

    try:
        return handler(arguments, user)
    except Exception as e:
        logger.error(f"Erreur execution tool {tool_name}: {e}")
        return f"Erreur lors de la recherche: {e}", []


# =========================================================================
# SEARCH IMPLEMENTATIONS
# =========================================================================

def _search_clients(
    arguments: Dict[str, Any], user
) -> Tuple[str, List[Dict[str, Any]]]:
    from core.models import Client

    query = arguments.get("query", "").strip()
    if not query:
        return "Aucun terme de recherche fourni.", []

    clients = Client.objects.filter(
        Q(raison_sociale__icontains=query)
        | Q(nom_commercial__icontains=query)
        | Q(ide_number__icontains=query)
        | Q(email__icontains=query)
        | Q(tva_number__icontains=query),
        is_active=True,
    ).select_related("adresse_siege")[:10]

    if not clients:
        return f"Aucun client trouve pour '{query}'.", []

    lines = []
    sources = []
    for c in clients:
        ville = ""
        if c.adresse_siege:
            ville = f", {c.adresse_siege.localite}" if hasattr(c.adresse_siege, 'localite') else ""
        lines.append(
            f"- {c.raison_sociale} ({c.forme_juridique}, {c.statut}{ville})"
            f" | IDE: {c.ide_number or 'N/A'}"
            f" | Email: {c.email or 'N/A'}"
            f" | Tel: {c.telephone or 'N/A'}"
        )
        sources.append({
            "entity_type": "client",
            "entity_id": str(c.id),
            "title": c.raison_sociale,
            "subtitle": f"{c.forme_juridique} - {c.statut}",
            "url": f"/core/clients/{c.id}/",
            "icon": "bi-building",
            "color": "#3498db",
        })

    return f"Clients trouves ({len(clients)}):\n" + "\n".join(lines), sources


def _search_mandats(
    arguments: Dict[str, Any], user
) -> Tuple[str, List[Dict[str, Any]]]:
    from core.models import Mandat

    query = arguments.get("query", "").strip()
    if not query:
        return "Aucun terme de recherche fourni.", []

    mandats = Mandat.objects.filter(
        Q(numero__icontains=query)
        | Q(client__raison_sociale__icontains=query)
        | Q(description__icontains=query)
        | Q(type_mandat__icontains=query),
        is_active=True,
    ).select_related("client")[:10]

    if not mandats:
        return f"Aucun mandat trouve pour '{query}'.", []

    lines = []
    sources = []
    for m in mandats:
        client_name = m.client.raison_sociale if m.client else "N/A"
        lines.append(
            f"- {m.numero} | Client: {client_name}"
            f" | Type: {m.type_mandat}"
            f" | Statut: {m.statut}"
            f" | Debut: {m.date_debut}"
        )
        sources.append({
            "entity_type": "mandat",
            "entity_id": str(m.id),
            "title": m.numero,
            "subtitle": f"{client_name} - {m.statut}",
            "url": f"/core/mandats/{m.id}/",
            "icon": "bi-folder2-open",
            "color": "#2ecc71",
        })

    return f"Mandats trouves ({len(mandats)}):\n" + "\n".join(lines), sources


def _search_factures(
    arguments: Dict[str, Any], user
) -> Tuple[str, List[Dict[str, Any]]]:
    from facturation.models import Facture

    query = arguments.get("query", "").strip()
    statut = arguments.get("statut", "").strip().upper()
    if not query:
        return "Aucun terme de recherche fourni.", []

    filters = Q(
        Q(numero_facture__icontains=query)
        | Q(client__raison_sociale__icontains=query)
        | Q(mandat__numero__icontains=query),
        is_active=True,
    )

    if statut:
        filters &= Q(statut=statut)

    factures = Facture.objects.filter(filters).select_related(
        "client", "mandat"
    )[:10]

    if not factures:
        return f"Aucune facture trouvee pour '{query}'.", []

    lines = []
    sources = []
    for f in factures:
        client_name = f.client.raison_sociale if f.client else "N/A"
        lines.append(
            f"- {f.numero_facture} | Client: {client_name}"
            f" | Montant TTC: {_fmt_chf(f.montant_ttc)}"
            f" | Paye: {_fmt_chf(f.montant_paye)}"
            f" | Reste: {_fmt_chf(f.montant_restant)}"
            f" | Statut: {f.statut}"
            f" | Date: {f.date_emission}"
            f" | Echeance: {f.date_echeance}"
        )
        sources.append({
            "entity_type": "facture",
            "entity_id": str(f.id),
            "title": f.numero_facture,
            "subtitle": f"{client_name} - {_fmt_chf(f.montant_ttc)}",
            "url": f"/facturation/factures/{f.id}/",
            "icon": "bi-receipt",
            "color": "#e67e22",
        })

    # Ajouter un total si plusieurs factures
    if len(factures) > 1:
        total = sum(f.montant_ttc for f in factures)
        total_paye = sum(f.montant_paye for f in factures)
        lines.append(f"\nTotal: {_fmt_chf(total)} TTC | Paye: {_fmt_chf(total_paye)}")

    return f"Factures trouvees ({len(factures)}):\n" + "\n".join(lines), sources


def _search_employes(
    arguments: Dict[str, Any], user
) -> Tuple[str, List[Dict[str, Any]]]:
    from salaires.models import Employe

    query = arguments.get("query", "").strip()
    if not query:
        return "Aucun terme de recherche fourni.", []

    employes = Employe.objects.filter(
        Q(nom__icontains=query)
        | Q(prenom__icontains=query)
        | Q(matricule__icontains=query)
        | Q(mandat__client__raison_sociale__icontains=query)
        | Q(mandat__numero__icontains=query),
        is_active=True,
    ).select_related("mandat", "mandat__client")[:10]

    if not employes:
        return f"Aucun employe trouve pour '{query}'.", []

    lines = []
    sources = []
    for e in employes:
        client_name = e.mandat.client.raison_sociale if e.mandat and e.mandat.client else "N/A"
        lines.append(
            f"- {e.prenom} {e.nom} (Matricule: {e.matricule})"
            f" | Entreprise: {client_name}"
            f" | Fonction: {e.fonction}"
            f" | Contrat: {e.type_contrat}"
            f" | Statut: {e.statut}"
            f" | Entree: {e.date_entree}"
        )
        sources.append({
            "entity_type": "employe",
            "entity_id": str(e.id),
            "title": f"{e.prenom} {e.nom}",
            "subtitle": f"{e.fonction} - {client_name}",
            "url": f"/salaires/employes/{e.id}/",
            "icon": "bi-person-badge",
            "color": "#9b59b6",
        })

    return f"Employes trouves ({len(employes)}):\n" + "\n".join(lines), sources


def _search_ecritures(
    arguments: Dict[str, Any], user
) -> Tuple[str, List[Dict[str, Any]]]:
    from comptabilite.models import EcritureComptable

    query = arguments.get("query", "").strip()
    if not query:
        return "Aucun terme de recherche fourni.", []

    ecritures = EcritureComptable.objects.filter(
        Q(libelle__icontains=query)
        | Q(numero_piece__icontains=query)
        | Q(compte__numero__icontains=query)
        | Q(compte__nom__icontains=query),
        is_active=True,
    ).select_related("compte", "journal", "mandat")[:10]

    if not ecritures:
        return f"Aucune ecriture trouvee pour '{query}'.", []

    lines = []
    sources = []
    for ec in ecritures:
        compte_str = f"{ec.compte.numero} {ec.compte.nom}" if ec.compte else "N/A"
        lines.append(
            f"- Piece {ec.numero_piece} | {ec.date_ecriture}"
            f" | Compte: {compte_str}"
            f" | Libelle: {ec.libelle[:100]}"
            f" | Debit: {_fmt_chf(ec.montant_debit)}"
            f" | Credit: {_fmt_chf(ec.montant_credit)}"
            f" | Statut: {ec.statut}"
        )
        sources.append({
            "entity_type": "ecriture",
            "entity_id": str(ec.id),
            "title": f"Piece {ec.numero_piece}",
            "subtitle": f"{compte_str} - {ec.date_ecriture}",
            "url": f"/comptabilite/ecritures/{ec.id}/",
            "icon": "bi-journal-text",
            "color": "#1abc9c",
        })

    return f"Ecritures trouvees ({len(ecritures)}):\n" + "\n".join(lines), sources


def _search_documents(
    arguments: Dict[str, Any], user
) -> Tuple[str, List[Dict[str, Any]]]:
    from documents.models import Document

    query = arguments.get("query", "").strip()
    if not query:
        return "Aucun terme de recherche fourni.", []

    documents = Document.objects.filter(
        Q(nom_fichier__icontains=query)
        | Q(ocr_text__icontains=query)
        | Q(prediction_type__icontains=query)
        | Q(description__icontains=query),
        is_active=True,
    ).select_related("mandat", "mandat__client")[:10]

    if not documents:
        return f"Aucun document trouve pour '{query}'.", []

    lines = []
    sources = []
    for d in documents:
        client_name = d.mandat.client.raison_sociale if d.mandat and d.mandat.client else "N/A"
        lines.append(
            f"- {d.nom_fichier}"
            f" | Type: {d.prediction_type or 'Non classe'}"
            f" | Client: {client_name}"
            f" | Date: {d.date_document or 'N/A'}"
            f" | Traitement: {d.statut_traitement}"
        )
        # Ajouter un extrait OCR si disponible
        if d.ocr_text:
            preview = d.ocr_text[:200].replace("\n", " ")
            lines.append(f"  Contenu: {preview}...")
        sources.append({
            "entity_type": "document",
            "entity_id": str(d.id),
            "title": d.nom_fichier,
            "subtitle": f"{d.prediction_type or 'Document'} - {client_name}",
            "url": f"/documents/documents/{d.id}/",
            "icon": "bi-file-earmark-text",
            "color": "#e74c3c",
        })

    return f"Documents trouves ({len(documents)}):\n" + "\n".join(lines), sources


def _search_taches(
    arguments: Dict[str, Any], user
) -> Tuple[str, List[Dict[str, Any]]]:
    from projets.models import Operation

    query = arguments.get("query", "").strip()
    if not query:
        return "Aucun terme de recherche fourni.", []

    operations = Operation.objects.filter(
        Q(titre__icontains=query)
        | Q(description__icontains=query)
        | Q(position__titre__icontains=query)
        | Q(position__mandat__client__raison_sociale__icontains=query),
        is_active=True,
    ).select_related("position", "position__mandat", "position__mandat__client")[:10]

    if not operations:
        return f"Aucune tache trouvee pour '{query}'.", []

    lines = []
    sources = []
    for op in operations:
        position_name = op.position.titre if op.position else "N/A"
        client_name = ""
        if op.position and op.position.mandat and op.position.mandat.client:
            client_name = op.position.mandat.client.raison_sociale
        lines.append(
            f"- {op.titre} | Position: {position_name}"
            f" | Client: {client_name or 'N/A'}"
            f" | Statut: {op.statut}"
            f" | Debut: {op.date_debut or 'N/A'}"
            f" | Fin: {op.date_fin or 'N/A'}"
        )
        sources.append({
            "entity_type": "tache",
            "entity_id": str(op.id),
            "title": op.titre,
            "subtitle": f"{position_name} - {op.statut}",
            "url": f"/projets/operations/{op.id}/",
            "icon": "bi-check2-square",
            "color": "#f39c12",
        })

    return f"Taches trouvees ({len(operations)}):\n" + "\n".join(lines), sources


def _search_semantic(
    arguments: Dict[str, Any], user
) -> Tuple[str, List[Dict[str, Any]]]:
    """Recherche sémantique universelle via ModelEmbedding (pgvector)."""
    from core.ai.embeddings import embedding_service
    from core.models import ModelEmbedding

    query = arguments.get("query", "").strip()
    if not query:
        return "Aucun terme de recherche fourni.", []

    query_embedding = embedding_service.generate_embedding(query)
    if query_embedding is None:
        return "Impossible de générer l'embedding pour la recherche.", []

    similar = ModelEmbedding.search_similar(
        embedding=query_embedding,
        limit=15,
        threshold=0.4,
    )

    if not similar:
        return f"Aucun résultat sémantique pour '{query}'.", []

    lines = []
    sources = []
    for me in similar:
        try:
            obj = me.content_object
            if obj is None:
                continue

            model_name = me.content_type.model
            similarity = round(1 - me.distance, 3)

            title = str(obj)
            entity_type = model_name
            url = ''
            icon = 'bi-search'
            color = '#7f8c8d'

            # Déterminer les infos selon le type
            if hasattr(obj, 'raison_sociale'):
                title = obj.raison_sociale
                entity_type = 'client'
                url = f"/core/clients/{obj.id}/"
                icon = 'bi-building'
                color = '#3498db'
            elif hasattr(obj, 'numero_facture'):
                title = obj.numero_facture
                entity_type = 'facture'
                url = f"/facturation/factures/{obj.id}/"
                icon = 'bi-receipt'
                color = '#e67e22'
            elif hasattr(obj, 'matricule') and hasattr(obj, 'nom'):
                title = f"{getattr(obj, 'prenom', '')} {obj.nom}"
                entity_type = 'employe'
                url = f"/salaires/employes/{obj.id}/"
                icon = 'bi-person-badge'
                color = '#9b59b6'
            elif hasattr(obj, 'libelle') and hasattr(obj, 'numero_piece'):
                title = f"Pièce {obj.numero_piece}"
                entity_type = 'ecriture'
                url = f"/comptabilite/ecritures/{obj.id}/"
                icon = 'bi-journal-text'
                color = '#1abc9c'
            elif hasattr(obj, 'nom_fichier'):
                title = obj.nom_fichier
                entity_type = 'document'
                url = f"/documents/documents/{obj.id}/"
                icon = 'bi-file-earmark-text'
                color = '#e74c3c'

            lines.append(f"- [{entity_type}] {title} (similarité: {similarity})")
            if me.text_preview:
                lines.append(f"  Aperçu: {me.text_preview[:150]}")

            sources.append({
                "entity_type": entity_type,
                "entity_id": str(obj.pk),
                "title": title,
                "subtitle": f"Similarité: {similarity}",
                "url": url,
                "icon": icon,
                "color": color,
            })
        except Exception:
            continue

    return f"Résultats sémantiques ({len(sources)}):\n" + "\n".join(lines), sources


# =========================================================================
# HELPERS
# =========================================================================

def _fmt_chf(montant) -> str:
    """Formate un montant au format suisse: 1'234.56 CHF"""
    if montant is None:
        return "0.00 CHF"
    try:
        val = float(montant)
        # Separateur de milliers avec apostrophe
        if val < 0:
            return f"-{_fmt_chf(-val)}"
        int_part = int(val)
        dec_part = f"{val:.2f}".split(".")[1]
        # Format avec apostrophes
        s = f"{int_part:,}".replace(",", "'")
        return f"{s}.{dec_part} CHF"
    except (ValueError, TypeError):
        return f"{montant} CHF"
