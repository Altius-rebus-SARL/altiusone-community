# mcp/tools.py
"""
MCP Tools for AltiusOne — exposes business data to AI clients.

Each tool is a read or write operation against the Django ORM,
authenticated via the user passed from server.py.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

# ─── Tool Registry ────────────────────────────────────────────────────────────

TOOLS = [
    # ── Core ──────────────────────────────────────────────────────────────
    {
        "name": "search_clients",
        "description": "Search clients (customers) by name, IDE number, or status. Returns a list of matching clients with key info.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term (name, IDE number, email)"},
                "statut": {"type": "string", "description": "Filter by status: ACTIF, INACTIF, ANNULE"},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
        },
    },
    {
        "name": "get_client",
        "description": "Get detailed information about a specific client, including contacts, mandates, and address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "search_mandats",
        "description": "Search mandates (engagements/contracts) by number, client name, or status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term (mandate number, client name)"},
                "statut": {"type": "string", "description": "Filter: ACTIF, CLOS, RESILIE"},
                "client_id": {"type": "string", "description": "Filter by client UUID"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_mandat",
        "description": "Get detailed info about a mandate: client, team, budget, fiscal years, billing type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandat_id": {"type": "string", "description": "Mandate UUID"},
            },
            "required": ["mandat_id"],
        },
    },
    {
        "name": "list_taches",
        "description": "List tasks, optionally filtered by status, assignee, or mandate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "statut": {"type": "string", "description": "NOUVEAU, EN_COURS, TERMINE, ANNULEE"},
                "assignee": {"type": "string", "description": "Username of assignee"},
                "mandat_id": {"type": "string", "description": "Mandate UUID"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "create_tache",
        "description": "Create a new task assigned to a user, optionally linked to a mandate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "titre": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Task description"},
                "priorite": {"type": "string", "description": "BASSE, NORMAL, HAUTE, CRITIQUE", "default": "NORMAL"},
                "date_echeance": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
                "assigne_a": {"type": "string", "description": "Username to assign to"},
                "mandat_id": {"type": "string", "description": "Mandate UUID"},
            },
            "required": ["titre"],
        },
    },
    # ── Facturation ───────────────────────────────────────────────────────
    {
        "name": "search_factures",
        "description": "Search invoices by number, client, status, or date range. Returns amounts, status, and due dates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search (invoice number, client name)"},
                "statut": {"type": "string", "description": "BROUILLON, EMISE, PAYEE, PARTIELLEMENT_PAYEE, ANNULEE"},
                "client_id": {"type": "string", "description": "Client UUID"},
                "mandat_id": {"type": "string", "description": "Mandate UUID"},
                "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "limit": {"type": "integer", "default": 30},
            },
        },
    },
    {
        "name": "get_facture",
        "description": "Get full invoice detail: lines, payments, reminders, amounts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "facture_id": {"type": "string", "description": "Invoice UUID"},
            },
            "required": ["facture_id"],
        },
    },
    {
        "name": "factures_impayees",
        "description": "List overdue/unpaid invoices with aging analysis. Shows total amounts owed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Filter by client UUID"},
                "jours_retard_min": {"type": "integer", "description": "Minimum days overdue (default 0)", "default": 0},
            },
        },
    },
    {
        "name": "search_time_entries",
        "description": "Search time tracking entries by date, user, mandate, or description.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "utilisateur": {"type": "string", "description": "Username"},
                "mandat_id": {"type": "string", "description": "Mandate UUID"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    },
    {
        "name": "create_time_entry",
        "description": "Log a time entry for a mandate and service type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandat_id": {"type": "string", "description": "Mandate UUID"},
                "prestation_id": {"type": "string", "description": "Service/prestation UUID"},
                "date_travail": {"type": "string", "description": "Work date (YYYY-MM-DD)"},
                "duree_minutes": {"type": "integer", "description": "Duration in minutes"},
                "description": {"type": "string", "description": "Work description"},
                "facturable": {"type": "boolean", "description": "Billable? (default true)", "default": True},
            },
            "required": ["mandat_id", "prestation_id", "duree_minutes", "description"],
        },
    },
    {
        "name": "chiffre_affaires",
        "description": "Revenue summary: total billed, paid, and outstanding, by period or client.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "annee": {"type": "integer", "description": "Year (default current)"},
                "mois": {"type": "integer", "description": "Month (1-12, optional)"},
                "client_id": {"type": "string", "description": "Filter by client UUID"},
            },
        },
    },
    # ── Comptabilité ──────────────────────────────────────────────────────
    {
        "name": "search_comptes",
        "description": "Search accounting chart of accounts by number or label.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Account number or label"},
                "mandat_id": {"type": "string", "description": "Mandate UUID (required)"},
                "classe": {"type": "integer", "description": "Account class (1-9)"},
                "limit": {"type": "integer", "default": 30},
            },
            "required": ["mandat_id"],
        },
    },
    {
        "name": "search_ecritures",
        "description": "Search accounting entries by date, account, journal, or description.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandat_id": {"type": "string", "description": "Mandate UUID (required)"},
                "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "compte_numero": {"type": "string", "description": "Account number"},
                "journal_code": {"type": "string", "description": "Journal code (ACH, VEN, BQ...)"},
                "query": {"type": "string", "description": "Search in description"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["mandat_id"],
        },
    },
    {
        "name": "balance_generale",
        "description": "Trial balance (balance générale) for a mandate and period. Shows debit/credit totals per account.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandat_id": {"type": "string", "description": "Mandate UUID (required)"},
                "date_from": {"type": "string", "description": "Period start (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "Period end (YYYY-MM-DD)"},
            },
            "required": ["mandat_id"],
        },
    },
    # ── Salaires ──────────────────────────────────────────────────────────
    {
        "name": "list_employes",
        "description": "List employees for a mandate, with contract type, salary, and status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandat_id": {"type": "string", "description": "Mandate UUID"},
                "statut": {"type": "string", "description": "ACTIF, SUSPENDU, LICENCIE"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    },
    {
        "name": "get_employe",
        "description": "Get detailed employee information: contract, salary, AVS number, address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "employe_id": {"type": "string", "description": "Employee UUID"},
            },
            "required": ["employe_id"],
        },
    },
    {
        "name": "list_fiches_salaire",
        "description": "List payslips for a mandate or employee, by year/month.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandat_id": {"type": "string", "description": "Mandate UUID"},
                "employe_id": {"type": "string", "description": "Employee UUID"},
                "annee": {"type": "integer", "description": "Year"},
                "mois": {"type": "integer", "description": "Month (1-12)"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    },
    # ── Documents ─────────────────────────────────────────────────────────
    {
        "name": "search_documents",
        "description": "Search documents by name, type, or mandate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term (file name, description)"},
                "mandat_id": {"type": "string", "description": "Mandate UUID"},
                "categorie": {"type": "string", "description": "Document category"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    # ── Projets ───────────────────────────────────────────────────────────
    {
        "name": "list_positions",
        "description": "List project positions (phases/lots) for a mandate with budget and progress info.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandat_id": {"type": "string", "description": "Mandate UUID (required)"},
            },
            "required": ["mandat_id"],
        },
    },
    {
        "name": "list_operations",
        "description": "List operations (tasks) for a project position.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "position_id": {"type": "string", "description": "Position UUID (required)"},
            },
            "required": ["position_id"],
        },
    },
    # ── Dashboard / Analytics ─────────────────────────────────────────────
    {
        "name": "dashboard",
        "description": "Key business metrics: active clients, mandates, unpaid invoices, revenue, pending tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    # ── Graph (existing) ──────────────────────────────────────────────────
    {
        "name": "graph_search",
        "description": "Full-text search on graph entities (knowledge graph) by name or description.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term"},
                "type_nom": {"type": "string", "description": "Entity type filter (e.g. Personne, Entreprise)"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "graph_explore",
        "description": "Explore the knowledge graph from an entity, returning neighboring nodes and links (BFS traversal).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entite_id": {"type": "string", "description": "Entity UUID"},
                "profondeur": {"type": "integer", "description": "Traversal depth (1-5)", "default": 2},
            },
            "required": ["entite_id"],
        },
    },
    {
        "name": "graph_semantic_search",
        "description": "Semantic vector search on graph entities using natural language (pgvector embeddings).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language description"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "graph_stats",
        "description": "Knowledge graph statistics: entity/relation counts, types breakdown, open anomalies.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def get_tools():
    return TOOLS


def execute_tool(name, arguments, user):
    """Execute a tool. Returns dict result."""
    try:
        fn = _TOOL_DISPATCH.get(name)
        if not fn:
            return {"error": f"Unknown tool: {name}"}
        return fn(arguments, user)
    except Exception as e:
        logger.error(f"MCP tool error ({name}): {e}", exc_info=True)
        return {"error": str(e)}


# ─── Tool Implementations ─────────────────────────────────────────────────────

def _fmt_decimal(val):
    """Format decimal for JSON output."""
    if val is None:
        return None
    return float(val) if isinstance(val, Decimal) else val


def _fmt_date(val):
    if val is None:
        return None
    return val.isoformat() if hasattr(val, "isoformat") else str(val)


def _addr_str(adresse):
    if not adresse:
        return None
    parts = [adresse.rue]
    if adresse.numero:
        parts[0] = f"{adresse.rue} {adresse.numero}"
    if adresse.complement:
        parts.append(adresse.complement)
    parts.append(f"{adresse.code_postal} {adresse.localite}")
    if adresse.canton:
        parts[-1] += f" ({adresse.canton})"
    return ", ".join(parts)


# ── Core tools ────────────────────────────────────────────────────────────────

def _search_clients(args, user):
    from core.models import Client
    from django.db.models import Q, Count

    query = args.get("query", "")
    statut = args.get("statut")
    limit = min(args.get("limit", 20), 100)

    qs = Client.objects.filter(is_active=True).select_related("adresse_siege", "responsable")
    if query:
        qs = qs.filter(
            Q(raison_sociale__icontains=query)
            | Q(nom_commercial__icontains=query)
            | Q(ide_number__icontains=query)
            | Q(email__icontains=query)
        )
    if statut:
        qs = qs.filter(statut=statut)

    qs = qs.annotate(nb_mandats=Count("mandats")).order_by("raison_sociale")

    results = []
    for c in qs[:limit]:
        results.append({
            "id": str(c.pk),
            "raison_sociale": c.raison_sociale,
            "nom_commercial": c.nom_commercial,
            "forme_juridique": c.get_forme_juridique_display() if c.forme_juridique else None,
            "ide_number": c.ide_number,
            "statut": c.statut,
            "email": c.email,
            "telephone": c.telephone,
            "adresse": _addr_str(c.adresse_siege),
            "responsable": c.responsable.get_full_name() if c.responsable else None,
            "nb_mandats": c.nb_mandats,
        })
    return {"results": results, "count": len(results)}


def _get_client(args, user):
    from core.models import Client

    client = Client.objects.select_related(
        "adresse_siege", "adresse_correspondance", "responsable", "contact_principal"
    ).get(pk=args["client_id"], is_active=True)

    mandats = list(
        client.mandats.filter(is_active=True)
        .values("id", "numero", "statut", "type_mandat", "date_debut", "date_fin")
        .order_by("-date_debut")[:20]
    )
    for m in mandats:
        m["id"] = str(m["id"])

    contacts = list(
        client.contacts.filter(is_active=True)
        .values("id", "nom", "prenom", "fonction", "email", "telephone")[:20]
    )
    for c in contacts:
        c["id"] = str(c["id"])

    return {
        "id": str(client.pk),
        "raison_sociale": client.raison_sociale,
        "nom_commercial": client.nom_commercial,
        "forme_juridique": client.get_forme_juridique_display() if client.forme_juridique else None,
        "ide_number": client.ide_number,
        "statut": client.statut,
        "email": client.email,
        "telephone": client.telephone,
        "website": client.website,
        "adresse_siege": _addr_str(client.adresse_siege),
        "adresse_correspondance": _addr_str(client.adresse_correspondance),
        "responsable": client.responsable.get_full_name() if client.responsable else None,
        "contact_principal": {
            "nom": client.contact_principal.nom,
            "prenom": client.contact_principal.prenom,
            "email": client.contact_principal.email,
        } if client.contact_principal else None,
        "mandats": mandats,
        "contacts": contacts,
        "created_at": _fmt_date(client.created_at),
    }


def _search_mandats(args, user):
    from core.models import Mandat
    from django.db.models import Q

    query = args.get("query", "")
    statut = args.get("statut")
    client_id = args.get("client_id")
    limit = min(args.get("limit", 20), 100)

    qs = Mandat.objects.filter(is_active=True).select_related("client", "responsable")
    if query:
        qs = qs.filter(Q(numero__icontains=query) | Q(client__raison_sociale__icontains=query))
    if statut:
        qs = qs.filter(statut=statut)
    if client_id:
        qs = qs.filter(client_id=client_id)

    results = []
    for m in qs.order_by("-date_debut")[:limit]:
        results.append({
            "id": str(m.pk),
            "numero": m.numero,
            "client": m.client.raison_sociale,
            "client_id": str(m.client_id),
            "type_mandat": m.type_mandat,
            "statut": m.statut,
            "date_debut": _fmt_date(m.date_debut),
            "date_fin": _fmt_date(m.date_fin),
            "responsable": m.responsable.get_full_name() if m.responsable else None,
            "taux_horaire": _fmt_decimal(m.taux_horaire),
            "montant_forfait": _fmt_decimal(m.montant_forfait),
        })
    return {"results": results, "count": len(results)}


def _get_mandat(args, user):
    from core.models import Mandat, ExerciceComptable

    m = Mandat.objects.select_related("client", "responsable", "devise").get(
        pk=args["mandat_id"], is_active=True
    )

    equipe = list(m.equipe.values_list("username", flat=True)) if m.equipe.exists() else []

    exercices = list(
        ExerciceComptable.objects.filter(mandat=m, is_active=True)
        .values("id", "annee", "date_debut", "date_fin", "statut")
        .order_by("-annee")[:5]
    )
    for ex in exercices:
        ex["id"] = str(ex["id"])

    # Budget info from projets
    from projets.models import Position
    positions = Position.objects.filter(mandat=m, is_active=True)
    budget_prevu = sum(p.budget_prevu or 0 for p in positions)
    budget_reel = sum(p.budget_reel or 0 for p in positions)

    return {
        "id": str(m.pk),
        "numero": m.numero,
        "client": m.client.raison_sociale,
        "client_id": str(m.client_id),
        "type_mandat": m.type_mandat,
        "statut": m.statut,
        "date_debut": _fmt_date(m.date_debut),
        "date_fin": _fmt_date(m.date_fin),
        "responsable": m.responsable.get_full_name() if m.responsable else None,
        "equipe": equipe,
        "type_facturation": m.type_facturation if hasattr(m, "type_facturation") else None,
        "taux_horaire": _fmt_decimal(m.taux_horaire),
        "montant_forfait": _fmt_decimal(m.montant_forfait),
        "devise": m.devise.code if m.devise else "CHF",
        "description": m.description,
        "exercices": exercices,
        "budget": {
            "prevu": _fmt_decimal(budget_prevu),
            "reel": _fmt_decimal(budget_reel),
            "pourcent": round(budget_reel / budget_prevu * 100, 1) if budget_prevu else 0,
        },
        "created_at": _fmt_date(m.created_at),
    }


def _list_taches(args, user):
    from core.models import Tache

    statut = args.get("statut")
    assignee = args.get("assignee")
    mandat_id = args.get("mandat_id")
    limit = min(args.get("limit", 20), 100)

    qs = Tache.objects.filter(is_active=True).select_related("cree_par", "mandat")
    if statut:
        qs = qs.filter(statut=statut)
    if assignee:
        qs = qs.filter(assignes__username=assignee)
    if mandat_id:
        qs = qs.filter(mandat_id=mandat_id)

    results = []
    for t in qs.order_by("-created_at")[:limit]:
        results.append({
            "id": str(t.pk),
            "titre": t.titre,
            "priorite": t.priorite,
            "statut": t.statut,
            "date_echeance": _fmt_date(t.date_echeance),
            "assignes": list(t.assignes.values_list("username", flat=True)),
            "mandat": t.mandat.numero if t.mandat else None,
            "cree_par": t.cree_par.get_full_name() if t.cree_par else None,
            "created_at": _fmt_date(t.created_at),
        })
    return {"results": results, "count": len(results)}


def _create_tache(args, user):
    from core.models import Tache, User, Mandat

    tache = Tache(
        titre=args["titre"],
        description=args.get("description", ""),
        priorite=args.get("priorite", "NORMAL"),
        cree_par=user,
    )
    if args.get("date_echeance"):
        tache.date_echeance = args["date_echeance"]
    if args.get("mandat_id"):
        tache.mandat = Mandat.objects.get(pk=args["mandat_id"], is_active=True)

    tache.save()

    if args.get("assigne_a"):
        u = User.objects.get(username=args["assigne_a"], is_active=True)
        tache.assignes.add(u)

    return {"id": str(tache.pk), "titre": tache.titre, "statut": tache.statut}


# ── Facturation tools ─────────────────────────────────────────────────────────

def _search_factures(args, user):
    from facturation.models import Facture
    from django.db.models import Q

    query = args.get("query", "")
    statut = args.get("statut")
    client_id = args.get("client_id")
    mandat_id = args.get("mandat_id")
    date_from = args.get("date_from")
    date_to = args.get("date_to")
    limit = min(args.get("limit", 30), 100)

    qs = Facture.objects.filter(is_active=True).select_related("client", "mandat")
    if query:
        qs = qs.filter(
            Q(numero_facture__icontains=query) | Q(client__raison_sociale__icontains=query)
        )
    if statut:
        qs = qs.filter(statut=statut)
    if client_id:
        qs = qs.filter(client_id=client_id)
    if mandat_id:
        qs = qs.filter(mandat_id=mandat_id)
    if date_from:
        qs = qs.filter(date_emission__gte=date_from)
    if date_to:
        qs = qs.filter(date_emission__lte=date_to)

    results = []
    for f in qs.order_by("-date_emission")[:limit]:
        results.append({
            "id": str(f.pk),
            "numero": f.numero_facture,
            "client": f.client.raison_sociale if f.client else None,
            "mandat": f.mandat.numero if f.mandat else None,
            "date_emission": _fmt_date(f.date_emission),
            "date_echeance": _fmt_date(f.date_echeance),
            "montant_ht": _fmt_decimal(f.montant_ht),
            "montant_ttc": _fmt_decimal(f.montant_ttc),
            "montant_restant": _fmt_decimal(f.montant_restant),
            "statut": f.statut,
            "devise": f.devise.code if hasattr(f, "devise") and f.devise else "CHF",
        })
    return {"results": results, "count": len(results)}


def _get_facture(args, user):
    from facturation.models import Facture

    f = Facture.objects.select_related("client", "mandat", "devise").get(
        pk=args["facture_id"], is_active=True
    )

    lignes = []
    for l in f.lignes.all().order_by("numero_ligne"):
        lignes.append({
            "numero": l.numero_ligne,
            "description": l.description,
            "quantite": _fmt_decimal(l.quantite),
            "prix_unitaire": _fmt_decimal(l.prix_unitaire),
            "montant_ht": _fmt_decimal(l.montant_ht),
            "taux_tva": _fmt_decimal(l.taux_tva),
            "montant_ttc": _fmt_decimal(l.montant_ttc),
        })

    paiements = []
    for p in f.paiements.all().order_by("-date_paiement"):
        paiements.append({
            "date": _fmt_date(p.date_paiement),
            "montant": _fmt_decimal(p.montant),
            "methode": p.methode if hasattr(p, "methode") else None,
            "reference": p.reference,
        })

    relances = []
    for r in f.relances.all().order_by("-date_relance"):
        relances.append({
            "niveau": r.niveau_relance,
            "date": _fmt_date(r.date_relance),
            "montant_frais": _fmt_decimal(r.montant_frais),
            "statut": r.statut,
        })

    return {
        "id": str(f.pk),
        "numero": f.numero_facture,
        "client": f.client.raison_sociale if f.client else None,
        "mandat": f.mandat.numero if f.mandat else None,
        "date_emission": _fmt_date(f.date_emission),
        "date_echeance": _fmt_date(f.date_echeance),
        "montant_ht": _fmt_decimal(f.montant_ht),
        "montant_tva": _fmt_decimal(f.montant_tva),
        "montant_ttc": _fmt_decimal(f.montant_ttc),
        "montant_restant": _fmt_decimal(f.montant_restant),
        "statut": f.statut,
        "notes": f.notes,
        "lignes": lignes,
        "paiements": paiements,
        "relances": relances,
    }


def _factures_impayees(args, user):
    from facturation.models import Facture
    from django.db.models import Sum

    jours_min = args.get("jours_retard_min", 0)
    cutoff = date.today() - timedelta(days=jours_min)

    qs = Facture.objects.filter(
        is_active=True,
        statut__in=["EMISE", "PARTIELLEMENT_PAYEE"],
        date_echeance__lte=cutoff,
    ).select_related("client", "mandat")

    if args.get("client_id"):
        qs = qs.filter(client_id=args["client_id"])

    totals = qs.aggregate(
        total_restant=Sum("montant_restant"),
        total_ttc=Sum("montant_ttc"),
    )

    results = []
    for f in qs.order_by("date_echeance")[:50]:
        jours_retard = (date.today() - f.date_echeance).days if f.date_echeance else 0
        results.append({
            "id": str(f.pk),
            "numero": f.numero_facture,
            "client": f.client.raison_sociale if f.client else None,
            "mandat": f.mandat.numero if f.mandat else None,
            "date_echeance": _fmt_date(f.date_echeance),
            "montant_ttc": _fmt_decimal(f.montant_ttc),
            "montant_restant": _fmt_decimal(f.montant_restant),
            "jours_retard": jours_retard,
            "statut": f.statut,
        })

    # Aging buckets
    buckets = {"0_30": 0, "31_60": 0, "61_90": 0, "90_plus": 0}
    for r in results:
        j = r["jours_retard"]
        amt = r["montant_restant"] or 0
        if j <= 30:
            buckets["0_30"] += amt
        elif j <= 60:
            buckets["31_60"] += amt
        elif j <= 90:
            buckets["61_90"] += amt
        else:
            buckets["90_plus"] += amt

    return {
        "factures": results,
        "count": len(results),
        "total_restant": _fmt_decimal(totals["total_restant"] or 0),
        "aging": {k: _fmt_decimal(v) for k, v in buckets.items()},
    }


def _search_time_entries(args, user):
    from facturation.models import TimeTracking

    date_from = args.get("date_from")
    date_to = args.get("date_to")
    utilisateur = args.get("utilisateur")
    mandat_id = args.get("mandat_id")
    limit = min(args.get("limit", 50), 200)

    qs = TimeTracking.objects.filter(is_active=True).select_related(
        "mandat", "utilisateur", "prestation"
    )
    if date_from:
        qs = qs.filter(date_travail__gte=date_from)
    if date_to:
        qs = qs.filter(date_travail__lte=date_to)
    if utilisateur:
        qs = qs.filter(utilisateur__username=utilisateur)
    if mandat_id:
        qs = qs.filter(mandat_id=mandat_id)

    results = []
    total_minutes = 0
    for t in qs.order_by("-date_travail")[:limit]:
        results.append({
            "id": str(t.pk),
            "date": _fmt_date(t.date_travail),
            "utilisateur": t.utilisateur.get_full_name() if t.utilisateur else None,
            "mandat": t.mandat.numero if t.mandat else None,
            "prestation": t.prestation.libelle if t.prestation else None,
            "duree_minutes": t.duree_minutes,
            "description": t.description,
            "facturable": t.facturable,
            "taux_horaire": _fmt_decimal(t.taux_horaire),
        })
        total_minutes += t.duree_minutes or 0

    return {
        "results": results,
        "count": len(results),
        "total_minutes": total_minutes,
        "total_heures": round(total_minutes / 60, 2),
    }


def _create_time_entry(args, user):
    from facturation.models import TimeTracking
    from core.models import Mandat
    from facturation.models import Prestation

    mandat = Mandat.objects.get(pk=args["mandat_id"], is_active=True)
    prestation = Prestation.objects.get(pk=args["prestation_id"], is_active=True)

    entry = TimeTracking(
        mandat=mandat,
        prestation=prestation,
        utilisateur=user,
        date_travail=args.get("date_travail", date.today()),
        duree_minutes=args["duree_minutes"],
        description=args["description"],
        facturable=args.get("facturable", True),
        taux_horaire=prestation.taux_horaire or mandat.taux_horaire or 0,
    )
    entry.save()

    return {
        "id": str(entry.pk),
        "date": _fmt_date(entry.date_travail),
        "duree_minutes": entry.duree_minutes,
        "mandat": mandat.numero,
        "prestation": prestation.libelle,
    }


def _chiffre_affaires(args, user):
    from facturation.models import Facture
    from django.db.models import Sum, Q

    annee = args.get("annee", date.today().year)
    mois = args.get("mois")
    client_id = args.get("client_id")

    qs = Facture.objects.filter(is_active=True, date_emission__year=annee)
    if mois:
        qs = qs.filter(date_emission__month=mois)
    if client_id:
        qs = qs.filter(client_id=client_id)

    # Exclude drafts and cancelled
    qs_valid = qs.exclude(statut__in=["BROUILLON", "ANNULEE"])

    agg = qs_valid.aggregate(
        total_ht=Sum("montant_ht"),
        total_tva=Sum("montant_tva"),
        total_ttc=Sum("montant_ttc"),
        total_paye=Sum("montant_ttc", filter=Q(statut="PAYEE")),
        total_restant=Sum("montant_restant"),
    )

    nb_factures = qs_valid.count()
    nb_payees = qs_valid.filter(statut="PAYEE").count()

    return {
        "annee": annee,
        "mois": mois,
        "nb_factures": nb_factures,
        "nb_payees": nb_payees,
        "total_ht": _fmt_decimal(agg["total_ht"] or 0),
        "total_tva": _fmt_decimal(agg["total_tva"] or 0),
        "total_ttc": _fmt_decimal(agg["total_ttc"] or 0),
        "total_paye": _fmt_decimal(agg["total_paye"] or 0),
        "total_restant": _fmt_decimal(agg["total_restant"] or 0),
    }


# ── Comptabilité tools ────────────────────────────────────────────────────────

def _search_comptes(args, user):
    from comptabilite.models import Compte, PlanComptable
    from django.db.models import Q

    mandat_id = args["mandat_id"]
    query = args.get("query", "")
    classe = args.get("classe")
    limit = min(args.get("limit", 30), 200)

    plan = PlanComptable.objects.filter(mandat_id=mandat_id, is_active=True).first()
    if not plan:
        return {"error": "No chart of accounts found for this mandate", "results": []}

    qs = Compte.objects.filter(plan_comptable=plan, is_active=True)
    if query:
        qs = qs.filter(Q(numero__icontains=query) | Q(libelle__icontains=query))
    if classe:
        qs = qs.filter(classe=classe)

    # Only imputable accounts (can post entries to)
    qs = qs.filter(imputable=True)

    results = []
    for c in qs.order_by("numero")[:limit]:
        results.append({
            "id": str(c.pk),
            "numero": c.numero,
            "libelle": c.libelle,
            "type_compte": c.type_compte,
            "classe": c.classe,
            "solde_debit": _fmt_decimal(c.solde_debit),
            "solde_credit": _fmt_decimal(c.solde_credit),
            "solde": _fmt_decimal((c.solde_debit or 0) - (c.solde_credit or 0)),
        })
    return {"results": results, "count": len(results)}


def _search_ecritures(args, user):
    from comptabilite.models import EcritureComptable
    from django.db.models import Q

    mandat_id = args["mandat_id"]
    date_from = args.get("date_from")
    date_to = args.get("date_to")
    compte_numero = args.get("compte_numero")
    journal_code = args.get("journal_code")
    query = args.get("query", "")
    limit = min(args.get("limit", 50), 200)

    qs = EcritureComptable.objects.filter(
        mandat_id=mandat_id, is_active=True
    ).select_related("compte", "journal")

    if date_from:
        qs = qs.filter(date_ecriture__gte=date_from)
    if date_to:
        qs = qs.filter(date_ecriture__lte=date_to)
    if compte_numero:
        qs = qs.filter(compte__numero=compte_numero)
    if journal_code:
        qs = qs.filter(journal__code=journal_code)
    if query:
        qs = qs.filter(Q(libelle__icontains=query) | Q(numero_piece__icontains=query))

    results = []
    for e in qs.order_by("-date_ecriture", "numero_piece")[:limit]:
        results.append({
            "id": str(e.pk),
            "date": _fmt_date(e.date_ecriture),
            "journal": e.journal.code if e.journal else None,
            "numero_piece": e.numero_piece,
            "compte": e.compte.numero if e.compte else None,
            "compte_libelle": e.compte.libelle if e.compte else None,
            "libelle": e.libelle,
            "debit": _fmt_decimal(e.montant_debit),
            "credit": _fmt_decimal(e.montant_credit),
            "statut": e.statut,
        })
    return {"results": results, "count": len(results)}


def _balance_generale(args, user):
    from comptabilite.models import EcritureComptable, PlanComptable
    from django.db.models import Sum

    mandat_id = args["mandat_id"]
    date_from = args.get("date_from")
    date_to = args.get("date_to")

    plan = PlanComptable.objects.filter(mandat_id=mandat_id, is_active=True).first()
    if not plan:
        return {"error": "No chart of accounts for this mandate"}

    qs = EcritureComptable.objects.filter(mandat_id=mandat_id, is_active=True, statut="VALIDE")
    if date_from:
        qs = qs.filter(date_ecriture__gte=date_from)
    if date_to:
        qs = qs.filter(date_ecriture__lte=date_to)

    balance = (
        qs.values("compte__numero", "compte__libelle", "compte__type_compte", "compte__classe")
        .annotate(total_debit=Sum("montant_debit"), total_credit=Sum("montant_credit"))
        .order_by("compte__numero")
    )

    results = []
    total_debit = 0
    total_credit = 0
    for b in balance:
        d = _fmt_decimal(b["total_debit"] or 0)
        c = _fmt_decimal(b["total_credit"] or 0)
        total_debit += d
        total_credit += c
        results.append({
            "compte": b["compte__numero"],
            "libelle": b["compte__libelle"],
            "type": b["compte__type_compte"],
            "classe": b["compte__classe"],
            "debit": d,
            "credit": c,
            "solde": round(d - c, 2),
        })

    return {
        "comptes": results,
        "count": len(results),
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "ecart": round(total_debit - total_credit, 2),
    }


# ── Salaires tools ────────────────────────────────────────────────────────────

def _list_employes(args, user):
    from salaires.models import Employe

    mandat_id = args.get("mandat_id")
    statut = args.get("statut")
    limit = min(args.get("limit", 50), 200)

    qs = Employe.objects.filter(is_active=True).select_related("mandat")
    if mandat_id:
        qs = qs.filter(mandat_id=mandat_id)
    if statut:
        qs = qs.filter(statut=statut)

    results = []
    for e in qs.order_by("nom", "prenom")[:limit]:
        results.append({
            "id": str(e.pk),
            "matricule": e.matricule,
            "nom": e.nom,
            "prenom": e.prenom,
            "fonction": e.fonction,
            "type_contrat": e.type_contrat,
            "statut": e.statut,
            "salaire_brut_mensuel": _fmt_decimal(e.salaire_brut_mensuel),
            "date_embauche": _fmt_date(e.date_embauche),
            "mandat": e.mandat.numero if e.mandat else None,
        })
    return {"results": results, "count": len(results)}


def _get_employe(args, user):
    from salaires.models import Employe

    e = Employe.objects.select_related("mandat", "adresse").get(
        pk=args["employe_id"], is_active=True
    )

    return {
        "id": str(e.pk),
        "matricule": e.matricule,
        "nom": e.nom,
        "prenom": e.prenom,
        "fonction": e.fonction,
        "date_naissance": _fmt_date(e.date_naissance),
        "sexe": e.sexe,
        "type_contrat": e.type_contrat,
        "statut": e.statut,
        "salaire_brut_mensuel": _fmt_decimal(e.salaire_brut_mensuel),
        "avs_number": e.avs_number,
        "date_embauche": _fmt_date(e.date_embauche),
        "date_fin_emploi": _fmt_date(e.date_fin_emploi),
        "adresse": _addr_str(e.adresse),
        "mandat": e.mandat.numero if e.mandat else None,
        "notes": e.notes,
    }


def _list_fiches_salaire(args, user):
    from salaires.models import FicheSalaire

    mandat_id = args.get("mandat_id")
    employe_id = args.get("employe_id")
    annee = args.get("annee")
    mois = args.get("mois")
    limit = min(args.get("limit", 50), 200)

    qs = FicheSalaire.objects.filter(is_active=True).select_related("employe", "mandat")
    if mandat_id:
        qs = qs.filter(mandat_id=mandat_id)
    if employe_id:
        qs = qs.filter(employe_id=employe_id)
    if annee:
        qs = qs.filter(annee=annee)
    if mois:
        qs = qs.filter(mois=mois)

    results = []
    for f in qs.order_by("-annee", "-mois")[:limit]:
        results.append({
            "id": str(f.pk),
            "numero": f.numero_fiche,
            "employe": f"{f.employe.prenom} {f.employe.nom}" if f.employe else None,
            "annee": f.annee,
            "mois": f.mois,
            "salaire_brut": _fmt_decimal(f.salaire_brut_total),
            "salaire_net": _fmt_decimal(f.salaire_net),
            "statut": f.statut,
            "mandat": f.mandat.numero if f.mandat else None,
        })
    return {"results": results, "count": len(results)}


# ── Documents tools ───────────────────────────────────────────────────────────

def _search_documents(args, user):
    from documents.models import Document
    from django.db.models import Q

    query = args.get("query", "")
    mandat_id = args.get("mandat_id")
    categorie = args.get("categorie")
    limit = min(args.get("limit", 20), 100)

    qs = Document.objects.filter(is_active=True).select_related("mandat", "type_document")
    if query:
        qs = qs.filter(
            Q(nom_fichier__icontains=query)
            | Q(nom_original__icontains=query)
            | Q(description__icontains=query)
        )
    if mandat_id:
        qs = qs.filter(mandat_id=mandat_id)
    if categorie:
        qs = qs.filter(categorie=categorie)

    results = []
    for d in qs.order_by("-created_at")[:limit]:
        results.append({
            "id": str(d.pk),
            "nom": d.nom_original or d.nom_fichier,
            "extension": d.extension,
            "taille": d.taille,
            "date_document": _fmt_date(d.date_document),
            "type": d.type_document.libelle if d.type_document else None,
            "categorie": d.categorie,
            "mandat": d.mandat.numero if d.mandat else None,
            "description": (d.description or "")[:200],
        })
    return {"results": results, "count": len(results)}


# ── Projets tools ─────────────────────────────────────────────────────────────

def _list_positions(args, user):
    from projets.models import Position

    mandat_id = args["mandat_id"]
    qs = Position.objects.filter(mandat_id=mandat_id, is_active=True).select_related("responsable")

    results = []
    for p in qs.order_by("ordre", "numero"):
        results.append({
            "id": str(p.pk),
            "numero": p.numero,
            "titre": p.titre,
            "statut": p.statut,
            "budget_prevu": _fmt_decimal(p.budget_prevu),
            "budget_reel": _fmt_decimal(p.budget_reel),
            "budget_pourcent": round(
                (p.budget_reel or 0) / p.budget_prevu * 100, 1
            ) if p.budget_prevu else 0,
            "date_debut": _fmt_date(p.date_debut),
            "date_fin": _fmt_date(p.date_fin),
            "responsable": p.responsable.get_full_name() if p.responsable else None,
            "nb_operations": p.operations.filter(is_active=True).count(),
        })
    return {"results": results, "count": len(results)}


def _list_operations(args, user):
    from projets.models import Operation

    position_id = args["position_id"]
    qs = Operation.objects.filter(
        position_id=position_id, is_active=True
    ).select_related("position")

    results = []
    for o in qs.order_by("numero"):
        results.append({
            "id": str(o.pk),
            "numero": o.numero,
            "titre": o.titre,
            "statut": o.statut,
            "budget_prevu": _fmt_decimal(o.budget_prevu),
            "cout_reel": _fmt_decimal(o.cout_reel),
            "date_debut": _fmt_date(o.date_debut),
            "date_fin": _fmt_date(o.date_fin),
            "assignes": list(o.assigne_a.values_list("username", flat=True)),
        })
    return {"results": results, "count": len(results)}


# ── Dashboard tool ────────────────────────────────────────────────────────────

def _dashboard(args, user):
    from core.models import Client, Mandat, Tache
    from facturation.models import Facture, TimeTracking
    from django.db.models import Sum, Q

    today = date.today()
    month_start = today.replace(day=1)

    clients_actifs = Client.objects.filter(is_active=True, statut="ACTIF").count()
    mandats_actifs = Mandat.objects.filter(is_active=True, statut="ACTIF").count()

    factures_impayees = Facture.objects.filter(
        is_active=True, statut__in=["EMISE", "PARTIELLEMENT_PAYEE"]
    )
    nb_impayees = factures_impayees.count()
    total_impaye = factures_impayees.aggregate(t=Sum("montant_restant"))["t"] or 0

    factures_en_retard = factures_impayees.filter(date_echeance__lt=today).count()

    # Revenue this month
    ca_mois = Facture.objects.filter(
        is_active=True, date_emission__gte=month_start,
        statut__in=["EMISE", "PAYEE", "PARTIELLEMENT_PAYEE"],
    ).aggregate(t=Sum("montant_ttc"))["t"] or 0

    # Time logged this month
    heures_mois = TimeTracking.objects.filter(
        is_active=True, date_travail__gte=month_start,
    ).aggregate(t=Sum("duree_minutes"))["t"] or 0

    # Pending tasks
    taches_en_cours = Tache.objects.filter(
        is_active=True, statut__in=["NOUVEAU", "EN_COURS"]
    ).count()
    taches_en_retard = Tache.objects.filter(
        is_active=True, statut__in=["NOUVEAU", "EN_COURS"],
        date_echeance__lt=today,
    ).count()

    return {
        "date": today.isoformat(),
        "clients_actifs": clients_actifs,
        "mandats_actifs": mandats_actifs,
        "factures": {
            "nb_impayees": nb_impayees,
            "total_impaye": _fmt_decimal(total_impaye),
            "en_retard": factures_en_retard,
        },
        "ca_mois": _fmt_decimal(ca_mois),
        "heures_mois": round(heures_mois / 60, 1),
        "taches": {
            "en_cours": taches_en_cours,
            "en_retard": taches_en_retard,
        },
    }


# ── Graph tools (kept from v1) ───────────────────────────────────────────────

def _graph_search(args, user):
    from graph.models import Entite
    from django.db.models import Q

    query = args.get("query", "")
    limit = args.get("limit", 10)
    type_nom = args.get("type_nom")

    qs = Entite.objects.filter(
        Q(nom__icontains=query) | Q(description__icontains=query), is_active=True
    ).select_related("type")

    if type_nom:
        qs = qs.filter(type__nom__icontains=type_nom)

    results = []
    for e in qs[:limit]:
        results.append({
            "id": str(e.pk),
            "nom": e.nom,
            "type": e.type.nom,
            "description": (e.description or "")[:200],
            "confiance": e.confiance,
        })
    return {"results": results, "count": len(results)}


def _graph_explore(args, user):
    from graph.services.exploration import explorer_graphe
    return explorer_graphe(args.get("entite_id"), profondeur=args.get("profondeur", 2))


def _graph_semantic_search(args, user):
    from graph.models import Entite
    from documents.embeddings import embedding_service
    from pgvector.django import CosineDistance

    query = args.get("query", "")
    limit = args.get("limit", 10)

    embedding = embedding_service.generate_embedding(query)
    if not embedding:
        return {"error": "Could not generate embedding", "results": []}

    qs = (
        Entite.objects.filter(is_active=True, embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", embedding))
        .order_by("distance")[:limit]
    )

    results = []
    for e in qs.select_related("type"):
        results.append({
            "id": str(e.pk),
            "nom": e.nom,
            "type": e.type.nom,
            "similarity": round(1 - e.distance, 4),
        })
    return {"results": results}


def _graph_stats(args, user):
    from graph.models import OntologieType, Entite, Relation, Anomalie
    from django.db.models import Count

    return {
        "entities": Entite.objects.filter(is_active=True).count(),
        "relations": Relation.objects.filter(is_active=True).count(),
        "types": OntologieType.objects.filter(is_active=True).count(),
        "open_anomalies": Anomalie.objects.filter(
            statut__in=["nouveau", "en_cours"], is_active=True
        ).count(),
        "entities_by_type": list(
            Entite.objects.filter(is_active=True)
            .values("type__nom")
            .annotate(count=Count("id"))
            .order_by("-count")
        ),
    }


# ─── Dispatch table ───────────────────────────────────────────────────────────

_TOOL_DISPATCH = {
    # Core
    "search_clients": _search_clients,
    "get_client": _get_client,
    "search_mandats": _search_mandats,
    "get_mandat": _get_mandat,
    "list_taches": _list_taches,
    "create_tache": _create_tache,
    # Facturation
    "search_factures": _search_factures,
    "get_facture": _get_facture,
    "factures_impayees": _factures_impayees,
    "search_time_entries": _search_time_entries,
    "create_time_entry": _create_time_entry,
    "chiffre_affaires": _chiffre_affaires,
    # Comptabilité
    "search_comptes": _search_comptes,
    "search_ecritures": _search_ecritures,
    "balance_generale": _balance_generale,
    # Salaires
    "list_employes": _list_employes,
    "get_employe": _get_employe,
    "list_fiches_salaire": _list_fiches_salaire,
    # Documents
    "search_documents": _search_documents,
    # Projets
    "list_positions": _list_positions,
    "list_operations": _list_operations,
    # Dashboard
    "dashboard": _dashboard,
    # Graph
    "graph_search": _graph_search,
    "graph_explore": _graph_explore,
    "graph_semantic_search": _graph_semantic_search,
    "graph_stats": _graph_stats,
}
