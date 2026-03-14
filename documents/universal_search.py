# documents/universal_search.py
"""
Service de recherche universelle pour le chat IA.

Permet de rechercher dans TOUTES les entites de la base de donnees:
- Documents (avec recherche semantique)
- Clients
- Mandats
- Employes
- Factures
- Ecritures comptables
- Declarations TVA/fiscales
- Contacts
- Taches
- etc.

Chaque resultat inclut:
- Le type d'entite
- Les informations pertinentes
- Un lien cliquable vers la fiche
- Le score de pertinence
"""
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from django.db.models import Q, Value, CharField
from django.db.models.functions import Concat
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types d'entites recherchables."""
    DOCUMENT = 'document'
    CLIENT = 'client'
    MANDAT = 'mandat'
    EMPLOYE = 'employe'
    CONTACT = 'contact'
    FACTURE = 'facture'
    ECRITURE = 'ecriture'
    PIECE_COMPTABLE = 'piece_comptable'
    DECLARATION_TVA = 'declaration_tva'
    DECLARATION_FISCALE = 'declaration_fiscale'
    TACHE = 'tache'
    COMPTE = 'compte'
    DOSSIER = 'dossier'
    TYPE_PLAN_COMPTABLE = 'type_plan_comptable'
    CLASSE_COMPTABLE = 'classe_comptable'
    PLAN_COMPTABLE = 'plan_comptable'
    JOURNAL = 'journal'
    UTILISATEUR = 'utilisateur'


@dataclass
class SearchResult:
    """Resultat de recherche universel."""
    entity_type: EntityType
    entity_id: str
    title: str
    subtitle: str
    description: str
    score: float
    url: str
    icon: str
    color: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    permissions_required: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict pour JSON."""
        return {
            'entity_type': self.entity_type.value,
            'entity_id': self.entity_id,
            'title': self.title,
            'subtitle': self.subtitle,
            'description': self.description,
            'score': round(self.score, 3),
            'url': self.url,
            'icon': self.icon,
            'color': self.color,
            'metadata': self.metadata
        }


@dataclass
class SearchContext:
    """Contexte de recherche."""
    user: Any  # User Django
    mandat_ids: Optional[List[str]] = None  # Filtrer par mandats
    entity_types: Optional[List[EntityType]] = None  # Filtrer par types
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    include_archived: bool = False


class UniversalSearchService:
    """
    Service de recherche universelle.

    Recherche dans toutes les entites de la base avec:
    - Recherche textuelle (fulltext PostgreSQL)
    - Recherche semantique (embeddings) pour les documents
    - Filtrage par permissions
    - Resultats enrichis avec liens
    """

    # Configuration des entites recherchables
    # Note: Les URLs utilisent le prefixe de langue /fr/ par defaut
    ENTITY_CONFIG = {
        EntityType.DOCUMENT: {
            'icon': 'ph-file-text',
            'color': 'primary',
            'url_pattern': '/fr/documents/{id}/',
            'search_fields': ['nom_fichier', 'ocr_text', 'description', 'tags'],
        },
        EntityType.CLIENT: {
            'icon': 'ph-buildings',
            'color': 'info',
            'url_pattern': '/fr/clients/{id}/',
            'search_fields': ['raison_sociale', 'nom_commercial', 'ide_number', 'email'],
        },
        EntityType.MANDAT: {
            'icon': 'ph-briefcase',
            'color': 'success',
            'url_pattern': '/fr/mandats/{id}/',
            'search_fields': ['numero', 'description', 'type_mandat'],
        },
        EntityType.EMPLOYE: {
            'icon': 'ph-user',
            'color': 'warning',
            'url_pattern': '/fr/salaires/employes/{id}/',
            'search_fields': ['nom', 'prenom', 'matricule', 'fonction', 'email'],
        },
        EntityType.CONTACT: {
            'icon': 'ph-address-book',
            'color': 'secondary',
            'url_pattern': '/fr/clients/{client_id}/',  # Contacts affiches dans la fiche client
            'search_fields': ['nom', 'prenom', 'email', 'fonction'],
        },
        EntityType.FACTURE: {
            'icon': 'ph-receipt',
            'color': 'danger',
            'url_pattern': '/fr/facturation/factures/{id}/',
            'search_fields': ['numero_facture', 'reference'],
        },
        EntityType.ECRITURE: {
            'icon': 'ph-calculator',
            'color': 'dark',
            'url_pattern': '/fr/comptabilite/ecritures/{id}/',
            'search_fields': ['libelle', 'numero_piece'],
        },
        EntityType.PIECE_COMPTABLE: {
            'icon': 'ph-file-text',
            'color': 'success',
            'url_pattern': '/fr/comptabilite/pieces/{id}/',
            'search_fields': ['numero_piece', 'libelle', 'reference_externe', 'tiers_nom'],
        },
        EntityType.DECLARATION_TVA: {
            'icon': 'ph-percent',
            'color': 'info',
            'url_pattern': '/fr/tva/declarations/{id}/',
            'search_fields': ['numero_declaration'],
        },
        EntityType.DECLARATION_FISCALE: {
            'icon': 'ph-bank',
            'color': 'warning',
            'url_pattern': '/fr/fiscalite/declarations/{id}/',
            'search_fields': ['numero_declaration', 'type_impot'],
        },
        EntityType.TACHE: {
            'icon': 'ph-check-square',
            'color': 'primary',
            'url_pattern': '/fr/taches/{id}/',
            'search_fields': ['titre', 'description'],
        },
        EntityType.COMPTE: {
            'icon': 'ph-list-numbers',
            'color': 'secondary',
            'url_pattern': '/fr/comptabilite/comptes/{id}/',
            'search_fields': ['numero', 'libelle'],
        },
        EntityType.DOSSIER: {
            'icon': 'ph-folder',
            'color': 'warning',
            'url_pattern': '/fr/documents/dossiers/{id}/',
            'search_fields': ['nom', 'description'],
        },
        EntityType.TYPE_PLAN_COMPTABLE: {
            'icon': 'ph-stack',
            'color': 'primary',
            'url_pattern': '/fr/comptabilite/types-plans/{id}/',
            'search_fields': ['code', 'nom', 'description', 'pays', 'norme_comptable'],
        },
        EntityType.CLASSE_COMPTABLE: {
            'icon': 'ph-list-numbers',
            'color': 'info',
            'url_pattern': '/fr/comptabilite/types-plans/{type_plan_id}/classes/',
            'search_fields': ['numero', 'libelle', 'type_compte'],
        },
        EntityType.PLAN_COMPTABLE: {
            'icon': 'ph-tree-structure',
            'color': 'success',
            'url_pattern': '/fr/comptabilite/plans/{id}/',
            'search_fields': ['nom', 'description'],
        },
        EntityType.JOURNAL: {
            'icon': 'ph-book-open',
            'color': 'info',
            'url_pattern': '/fr/comptabilite/journaux/{id}/',
            'search_fields': ['code', 'libelle', 'type_journal'],
        },
        EntityType.UTILISATEUR: {
            'icon': 'ph-user-circle',
            'color': 'info',
            'url_pattern': '/fr/admin/utilisateurs/{id}/',
            'search_fields': ['first_name', 'last_name', 'email', 'username'],
        },
    }

    def __init__(self):
        self._search_service = None
        self._ai_service = None

    @property
    def search_service(self):
        """Service de recherche documentaire."""
        if self._search_service is None:
            from documents.search import search_service
            self._search_service = search_service
        return self._search_service

    @property
    def ai_service(self):
        """Service AI pour embeddings."""
        if self._ai_service is None:
            from documents.ai_service import ai_service
            self._ai_service = ai_service
        return self._ai_service

    # Mots vides a ignorer lors de l'extraction de mots-cles
    STOP_WORDS = frozenset({
        # Francais
        'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'au', 'aux',
        'ce', 'ces', 'cet', 'cette', 'mon', 'ton', 'son', 'ma', 'ta', 'sa',
        'mes', 'tes', 'ses', 'nos', 'vos', 'leur', 'leurs',
        'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'on',
        'me', 'te', 'se', 'lui', 'y', 'en',
        'et', 'ou', 'mais', 'donc', 'ni', 'car', 'que', 'qui', 'quoi',
        'est', 'sont', 'a', 'ont', 'fait', 'font', 'dit', 'va', 'vont',
        'dans', 'sur', 'sous', 'avec', 'pour', 'par', 'chez', 'entre',
        'pas', 'plus', 'moins', 'bien', 'mal', 'tout', 'tous', 'toute',
        'quel', 'quelle', 'quels', 'quelles', 'comment', 'pourquoi',
        'quand', 'combien',
        "c'est", "qu'est", "l'", "d'", "j'", "n'", "s'",
        'oui', 'non', 'si', 'ne', 'tres', 'aussi', 'comme',
        'moi', 'toi', 'eux', 'nous',
        'etre', 'avoir', 'faire', 'dire', 'aller', 'voir', 'savoir',
        'pouvoir', 'vouloir', 'falloir', 'devoir',
        # Questions courantes
        'quoi', 'donne', 'montre', 'affiche', 'trouve', 'cherche',
        'explique', 'raconte', 'parle',
    })

    def _extract_search_keywords(self, message: str) -> str:
        """
        Extrait les mots-cles significatifs d'un message utilisateur.

        Supprime les mots vides pour ne garder que les termes pertinents
        pour la recherche dans la base de donnees.
        """
        import re
        # Nettoyer la ponctuation sauf apostrophes internes
        clean = re.sub(r"[^\w\s'-]", ' ', message.lower())
        # Gerer les apostrophes en debut de mot (l', d', etc.)
        clean = re.sub(r"\b[a-z]'", ' ', clean)

        words = clean.split()
        keywords = [w for w in words if w not in self.STOP_WORDS and len(w) > 1]

        if not keywords:
            # Fallback: utiliser le message original
            return message.strip()

        return ' '.join(keywords)

    def search(
        self,
        query: str,
        context: SearchContext,
        limit: int = 20,
        semantic_weight: float = 0.6
    ) -> List[SearchResult]:
        """
        Recherche universelle dans toutes les entites.

        Args:
            query: Requete de recherche (message utilisateur brut)
            context: Contexte (user, filtres, permissions)
            limit: Nombre max de resultats
            semantic_weight: Poids de la recherche semantique (0-1)

        Returns:
            Liste de SearchResult tries par pertinence
        """
        # Extraire les mots-cles significatifs du message
        search_query = self._extract_search_keywords(query)
        logger.info(f"Recherche: '{query}' -> mots-cles: '{search_query}'")

        results = []
        entity_types = context.entity_types or list(EntityType)

        # Limite par type pour equilibrer les resultats
        limit_per_type = max(5, limit // len(entity_types))

        for entity_type in entity_types:
            try:
                type_results = self._search_entity_type(
                    query=search_query,
                    entity_type=entity_type,
                    context=context,
                    limit=limit_per_type,
                    semantic_weight=semantic_weight
                )
                results.extend(type_results)
            except Exception as e:
                logger.error(f"Erreur recherche {entity_type.value}: {e}")

        # Si pas de resultats avec les mots-cles, essayer avec la requete brute
        if not results and search_query != query.strip():
            logger.info(f"Aucun resultat avec mots-cles, retry avec requete brute")
            for entity_type in entity_types:
                try:
                    type_results = self._search_entity_type(
                        query=query.strip(),
                        entity_type=entity_type,
                        context=context,
                        limit=limit_per_type,
                        semantic_weight=semantic_weight
                    )
                    results.extend(type_results)
                except Exception as e:
                    pass

        # Trier par score decroissant
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:limit]

    def _search_entity_type(
        self,
        query: str,
        entity_type: EntityType,
        context: SearchContext,
        limit: int,
        semantic_weight: float
    ) -> List[SearchResult]:
        """Recherche dans un type d'entite specifique."""

        if entity_type == EntityType.DOCUMENT:
            return self._search_documents(query, context, limit, semantic_weight)
        elif entity_type == EntityType.CLIENT:
            return self._search_clients(query, context, limit)
        elif entity_type == EntityType.MANDAT:
            return self._search_mandats(query, context, limit)
        elif entity_type == EntityType.EMPLOYE:
            return self._search_employes(query, context, limit)
        elif entity_type == EntityType.CONTACT:
            return self._search_contacts(query, context, limit)
        elif entity_type == EntityType.FACTURE:
            return self._search_factures(query, context, limit)
        elif entity_type == EntityType.ECRITURE:
            return self._search_ecritures(query, context, limit)
        elif entity_type == EntityType.PIECE_COMPTABLE:
            return self._search_pieces_comptables(query, context, limit)
        elif entity_type == EntityType.DECLARATION_TVA:
            return self._search_declarations_tva(query, context, limit)
        elif entity_type == EntityType.DECLARATION_FISCALE:
            return self._search_declarations_fiscales(query, context, limit)
        elif entity_type == EntityType.TACHE:
            return self._search_taches(query, context, limit)
        elif entity_type == EntityType.COMPTE:
            return self._search_comptes(query, context, limit)
        elif entity_type == EntityType.DOSSIER:
            return self._search_dossiers(query, context, limit)
        elif entity_type == EntityType.TYPE_PLAN_COMPTABLE:
            return self._search_types_plans_comptables(query, context, limit)
        elif entity_type == EntityType.CLASSE_COMPTABLE:
            return self._search_classes_comptables(query, context, limit)
        elif entity_type == EntityType.PLAN_COMPTABLE:
            return self._search_plans_comptables(query, context, limit)
        elif entity_type == EntityType.JOURNAL:
            return self._search_journaux(query, context, limit)
        elif entity_type == EntityType.UTILISATEUR:
            return self._search_utilisateurs(query, context, limit)

        return []

    def _search_documents(
        self,
        query: str,
        context: SearchContext,
        limit: int,
        semantic_weight: float
    ) -> List[SearchResult]:
        """Recherche dans les documents avec semantique."""
        from documents.models import Document

        results = []
        config = self.ENTITY_CONFIG[EntityType.DOCUMENT]

        # Utiliser le service de recherche existant
        try:
            mandat_id = context.mandat_ids[0] if context.mandat_ids and len(context.mandat_ids) == 1 else None

            search_results = self.search_service.search(
                query=query,
                mandat_id=mandat_id,
                user=context.user,
                search_type='hybrid',
                limit=limit,
                semantic_threshold=0.3
            )

            for sr in search_results:
                doc = sr.document
                results.append(SearchResult(
                    entity_type=EntityType.DOCUMENT,
                    entity_id=str(doc.id),
                    title=doc.nom_fichier,
                    subtitle=f"{doc.prediction_type or 'Document'} - {doc.mandat.numero if doc.mandat else 'Sans mandat'}",
                    description=sr.snippet[:200] if sr.snippet else (doc.description or doc.ocr_text[:200] if doc.ocr_text else ''),
                    score=sr.score,
                    url=config['url_pattern'].format(id=doc.id),
                    icon=config['icon'],
                    color=config['color'],
                    metadata={
                        'mandat_id': str(doc.mandat.id) if doc.mandat else None,
                        'mandat_numero': doc.mandat.numero if doc.mandat else None,
                        'type_document': doc.prediction_type,
                        'date_document': doc.date_document.isoformat() if doc.date_document else None,
                        'mime_type': doc.mime_type,
                        'taille': doc.taille,
                        'ocr_text_preview': doc.ocr_text[:500] if doc.ocr_text else None,
                    }
                ))
        except Exception as e:
            logger.error(f"Erreur recherche documents: {e}")

        return results

    def _build_term_filter(self, query: str, fields: List[str]) -> Q:
        """
        Construit un filtre Q qui cherche CHAQUE terme individuellement
        dans les champs specifies. Tous les termes doivent matcher (AND).
        """
        terms = query.lower().split()
        if not terms:
            return Q(pk__isnull=True)  # Aucun resultat

        combined = Q()
        for term in terms:
            term_q = Q()
            for field_name in fields:
                term_q |= Q(**{f'{field_name}__icontains': term})
            combined &= term_q

        return combined

    def _search_clients(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les clients."""
        from core.models import Client

        results = []
        config = self.ENTITY_CONFIG[EntityType.CLIENT]

        # Chercher chaque mot-cle dans les champs (AND entre termes)
        search_fields = ['raison_sociale', 'nom_commercial', 'ide_number',
                         'tva_number', 'email', 'telephone']
        q_filter = Q(is_active=True) & self._build_term_filter(query, search_fields)

        # Filtrer par mandats si specifie
        if context.mandat_ids:
            q_filter &= Q(mandats__id__in=context.mandat_ids)

        clients = Client.objects.filter(q_filter).distinct()[:limit]

        for client in clients:
            # Calculer un score simple base sur la correspondance
            score = self._calculate_text_score(query, [
                client.raison_sociale,
                client.nom_commercial or '',
                client.ide_number or '',
            ])

            results.append(SearchResult(
                entity_type=EntityType.CLIENT,
                entity_id=str(client.id),
                title=client.raison_sociale,
                subtitle=f"{client.forme_juridique or ''} - {client.statut}",
                description=f"IDE: {client.ide_number or 'N/A'} | Email: {client.email or 'N/A'}",
                score=score,
                url=config['url_pattern'].format(id=client.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'ide_number': client.ide_number,
                    'tva_number': client.tva_number,
                    'email': client.email,
                    'telephone': client.telephone,
                    'statut': client.statut,
                    'nombre_mandats': client.mandats.count() if hasattr(client, 'mandats') else 0,
                }
            ))

        return results

    def _search_mandats(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les mandats."""
        from core.models import Mandat

        results = []
        config = self.ENTITY_CONFIG[EntityType.MANDAT]

        search_fields = ['numero', 'description', 'type_mandat', 'client__raison_sociale']
        q_filter = Q(is_active=True) & self._build_term_filter(query, search_fields)

        # Filtrer par mandats autorises
        if context.mandat_ids:
            q_filter &= Q(id__in=context.mandat_ids)

        mandats = Mandat.objects.filter(q_filter).select_related('client')[:limit]

        for mandat in mandats:
            score = self._calculate_text_score(query, [
                mandat.numero,
                mandat.type_mandat,
                mandat.client.raison_sociale if mandat.client else '',
            ])

            results.append(SearchResult(
                entity_type=EntityType.MANDAT,
                entity_id=str(mandat.id),
                title=f"Mandat {mandat.numero}",
                subtitle=f"{mandat.client.raison_sociale if mandat.client else 'N/A'} - {mandat.type_mandat}",
                description=mandat.description or f"Statut: {mandat.statut}",
                score=score,
                url=config['url_pattern'].format(id=mandat.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'client_id': str(mandat.client.id) if mandat.client else None,
                    'client_nom': mandat.client.raison_sociale if mandat.client else None,
                    'type_mandat': mandat.type_mandat,
                    'statut': mandat.statut,
                    'date_debut': mandat.date_debut.isoformat() if mandat.date_debut else None,
                }
            ))

        return results

    def _search_employes(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les employes."""
        try:
            from salaires.models import Employe
        except ImportError:
            logger.debug("Module salaires non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.EMPLOYE]

        search_fields = ['nom', 'prenom', 'matricule', 'email', 'fonction', 'avs_number']
        q_filter = Q(is_active=True) & self._build_term_filter(query, search_fields)

        # Multi-word: also search concatenated full name
        q_fullname = self._build_term_filter(query, ['full_name', 'full_name_rev'])

        if context.mandat_ids:
            q_filter &= Q(mandat_id__in=context.mandat_ids)

        employes = Employe.objects.annotate(
            full_name=Concat('prenom', Value(' '), 'nom', output_field=CharField()),
            full_name_rev=Concat('nom', Value(' '), 'prenom', output_field=CharField()),
        ).filter(q_filter | q_fullname).select_related('mandat').distinct()[:limit]

        for emp in employes:
            score = self._calculate_text_score(query, [
                f"{emp.prenom} {emp.nom}",
                emp.nom,
                emp.prenom,
                emp.matricule or '',
                emp.fonction or '',
            ])

            results.append(SearchResult(
                entity_type=EntityType.EMPLOYE,
                entity_id=str(emp.id),
                title=f"{emp.prenom} {emp.nom}",
                subtitle=f"{emp.fonction or 'N/A'} - {emp.matricule or 'N/A'}",
                description=f"Email: {emp.email or 'N/A'} | Statut: {emp.statut}",
                score=score,
                url=config['url_pattern'].format(id=emp.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'mandat_id': str(emp.mandat.id) if emp.mandat else None,
                    'matricule': emp.matricule,
                    'fonction': emp.fonction,
                    'email': emp.email,
                    'statut': emp.statut,
                    'date_entree': emp.date_entree.isoformat() if emp.date_entree else None,
                }
            ))

        return results

    def _search_contacts(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les contacts."""
        from core.models import Contact

        results = []
        config = self.ENTITY_CONFIG[EntityType.CONTACT]

        q_filter = Q(is_active=True) & (
            Q(nom__icontains=query) |
            Q(prenom__icontains=query) |
            Q(email__icontains=query) |
            Q(fonction__icontains=query) |
            Q(telephone__icontains=query)
        )

        # Multi-word: also search concatenated full name
        q_fullname = Q(full_name__icontains=query)
        q_fullname_rev = Q(full_name_rev__icontains=query)

        contacts = Contact.objects.annotate(
            full_name=Concat('prenom', Value(' '), 'nom', output_field=CharField()),
            full_name_rev=Concat('nom', Value(' '), 'prenom', output_field=CharField()),
        ).filter(q_filter | q_fullname | q_fullname_rev).select_related('client').distinct()[:limit]

        for contact in contacts:
            score = self._calculate_text_score(query, [
                f"{contact.prenom or ''} {contact.nom}".strip(),
                contact.nom,
                contact.prenom or '',
                contact.email or '',
            ])

            # Les contacts sont affiches dans la fiche client (onglet contacts)
            url = config['url_pattern'].format(
                client_id=contact.client.id if contact.client else ''
            )

            results.append(SearchResult(
                entity_type=EntityType.CONTACT,
                entity_id=str(contact.id),
                title=f"{contact.prenom or ''} {contact.nom}".strip(),
                subtitle=f"{contact.fonction or 'Contact'} - {contact.client.raison_sociale if contact.client else 'N/A'}",
                description=f"Email: {contact.email or 'N/A'} | Tel: {contact.telephone or 'N/A'}",
                score=score,
                url=url,
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'client_id': str(contact.client.id) if contact.client else None,
                    'email': contact.email,
                    'telephone': contact.telephone,
                    'fonction': contact.fonction,
                    'principal': contact.principal,
                }
            ))

        return results

    def _search_factures(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les factures."""
        try:
            from facturation.models import Facture
        except ImportError:
            logger.debug("Module facturation non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.FACTURE]

        search_fields = ['numero_facture', 'client__raison_sociale', 'qr_reference']
        q_filter = Q(is_active=True) & self._build_term_filter(query, search_fields)

        if context.mandat_ids:
            q_filter &= Q(mandat_id__in=context.mandat_ids)

        factures = Facture.objects.filter(q_filter).select_related('client', 'mandat')[:limit]

        for facture in factures:
            score = self._calculate_text_score(query, [
                facture.numero_facture,
                facture.client.raison_sociale if facture.client else '',
            ])

            results.append(SearchResult(
                entity_type=EntityType.FACTURE,
                entity_id=str(facture.id),
                title=f"Facture {facture.numero_facture}",
                subtitle=f"{facture.client.raison_sociale if facture.client else 'N/A'} - {facture.statut}",
                description=f"Montant: {facture.montant_ttc or 0} CHF | Date: {facture.date_emission}",
                score=score,
                url=config['url_pattern'].format(id=facture.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'montant_ttc': float(facture.montant_ttc) if facture.montant_ttc else 0,
                    'statut': facture.statut,
                    'date_emission': facture.date_emission.isoformat() if facture.date_emission else None,
                    'client_nom': facture.client.raison_sociale if facture.client else None,
                }
            ))

        return results

    def _search_ecritures(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les ecritures comptables."""
        try:
            from comptabilite.models import EcritureComptable
        except ImportError:
            logger.debug("Module comptabilite non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.ECRITURE]

        q_filter = Q(is_active=True) & (
            Q(libelle__icontains=query) |
            Q(numero_piece__icontains=query) |
            Q(compte__numero__icontains=query) |
            Q(compte__libelle__icontains=query)
        )

        if context.mandat_ids:
            q_filter &= Q(mandat_id__in=context.mandat_ids)

        ecritures = EcritureComptable.objects.filter(q_filter).select_related('compte', 'mandat')[:limit]

        for ecriture in ecritures:
            score = self._calculate_text_score(query, [
                ecriture.libelle,
                ecriture.numero_piece or '',
            ])

            montant = ecriture.montant_debit or ecriture.montant_credit or 0
            sens = 'D' if ecriture.montant_debit else 'C'

            results.append(SearchResult(
                entity_type=EntityType.ECRITURE,
                entity_id=str(ecriture.id),
                title=f"{ecriture.numero_piece} - {ecriture.libelle[:50]}",
                subtitle=f"Compte {ecriture.compte.numero if ecriture.compte else 'N/A'}",
                description=f"Montant: {montant} CHF ({sens}) | Date: {ecriture.date_ecriture}",
                score=score,
                url=config['url_pattern'].format(id=ecriture.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'montant': float(montant),
                    'sens': sens,
                    'compte_numero': ecriture.compte.numero if ecriture.compte else None,
                    'date_ecriture': ecriture.date_ecriture.isoformat() if ecriture.date_ecriture else None,
                }
            ))

        return results

    def _search_pieces_comptables(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les pieces comptables."""
        try:
            from comptabilite.models import PieceComptable
        except ImportError:
            logger.debug("Module comptabilite non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.PIECE_COMPTABLE]

        q_filter = Q(is_active=True) & (
            Q(numero_piece__icontains=query) |
            Q(libelle__icontains=query) |
            Q(reference_externe__icontains=query) |
            Q(tiers_nom__icontains=query) |
            Q(tiers_numero_tva__icontains=query) |
            Q(type_piece__libelle__icontains=query) |
            Q(type_piece__code__icontains=query)
        )

        if context.mandat_ids:
            q_filter &= Q(mandat_id__in=context.mandat_ids)

        pieces = PieceComptable.objects.filter(q_filter).select_related(
            'mandat', 'mandat__client', 'type_piece', 'journal', 'dossier'
        )[:limit]

        for piece in pieces:
            score = self._calculate_text_score(query, [
                piece.numero_piece,
                piece.libelle,
                piece.reference_externe or '',
                piece.tiers_nom or '',
                piece.type_piece.libelle if piece.type_piece else '',
            ])

            # Construire le sous-titre
            type_info = piece.type_piece.libelle if piece.type_piece else 'Pièce'
            mandat_info = piece.mandat.numero if piece.mandat else 'N/A'
            subtitle = f"{type_info} - {mandat_info} - {piece.statut}"

            # Montant à afficher
            montant = piece.montant_ttc or piece.montant_ht or 0

            results.append(SearchResult(
                entity_type=EntityType.PIECE_COMPTABLE,
                entity_id=str(piece.id),
                title=f"{piece.numero_piece} - {piece.libelle[:50]}",
                subtitle=subtitle,
                description=f"Montant: {montant} CHF | Date: {piece.date_piece} | Tiers: {piece.tiers_nom or 'N/A'}",
                score=score,
                url=config['url_pattern'].format(id=piece.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'numero_piece': piece.numero_piece,
                    'date_piece': piece.date_piece.isoformat() if piece.date_piece else None,
                    'type_piece': piece.type_piece.code if piece.type_piece else None,
                    'type_piece_libelle': piece.type_piece.libelle if piece.type_piece else None,
                    'montant_ht': float(piece.montant_ht) if piece.montant_ht else None,
                    'montant_tva': float(piece.montant_tva) if piece.montant_tva else None,
                    'montant_ttc': float(piece.montant_ttc) if piece.montant_ttc else None,
                    'tiers_nom': piece.tiers_nom,
                    'tiers_numero_tva': piece.tiers_numero_tva,
                    'reference_externe': piece.reference_externe,
                    'statut': piece.statut,
                    'mandat_id': str(piece.mandat.id) if piece.mandat else None,
                    'mandat_numero': piece.mandat.numero if piece.mandat else None,
                    'client_nom': piece.mandat.client.raison_sociale if piece.mandat and piece.mandat.client else None,
                    'journal_code': piece.journal.code if piece.journal else None,
                    'dossier_nom': piece.dossier.nom if piece.dossier else None,
                }
            ))

        return results

    def _search_declarations_tva(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les declarations TVA."""
        try:
            from tva.models import DeclarationTVA
        except ImportError:
            logger.debug("Module tva non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.DECLARATION_TVA]

        q_filter = Q(is_active=True) & (
            Q(numero_declaration__icontains=query) |
            Q(mandat__numero__icontains=query)
        )

        if context.mandat_ids:
            q_filter &= Q(mandat_id__in=context.mandat_ids)

        declarations = DeclarationTVA.objects.filter(q_filter).select_related('mandat')[:limit]

        for decl in declarations:
            score = self._calculate_text_score(query, [
                decl.numero_declaration or '',
                decl.mandat.numero if decl.mandat else '',
            ])

            periode = f"T{decl.trimestre}/{decl.annee}" if decl.trimestre else f"{decl.annee}"

            results.append(SearchResult(
                entity_type=EntityType.DECLARATION_TVA,
                entity_id=str(decl.id),
                title=f"Declaration TVA {decl.numero_declaration or periode}",
                subtitle=f"{decl.mandat.numero if decl.mandat else 'N/A'} - {decl.statut}",
                description=f"Periode: {periode} | Solde: {decl.solde_tva or 0} CHF",
                score=score,
                url=config['url_pattern'].format(id=decl.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'periode': periode,
                    'solde_tva': float(decl.solde_tva) if decl.solde_tva else 0,
                    'statut': decl.statut,
                }
            ))

        return results

    def _search_declarations_fiscales(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les declarations fiscales."""
        try:
            from fiscalite.models import DeclarationFiscale
        except ImportError:
            logger.debug("Module fiscalite non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.DECLARATION_FISCALE]

        q_filter = Q(is_active=True) & (
            Q(numero_declaration__icontains=query) |
            Q(type_impot__icontains=query) |
            Q(mandat__numero__icontains=query)
        )

        if context.mandat_ids:
            q_filter &= Q(mandat_id__in=context.mandat_ids)

        declarations = DeclarationFiscale.objects.filter(q_filter).select_related('mandat')[:limit]

        for decl in declarations:
            score = self._calculate_text_score(query, [
                decl.numero_declaration or '',
                decl.type_impot or '',
            ])

            results.append(SearchResult(
                entity_type=EntityType.DECLARATION_FISCALE,
                entity_id=str(decl.id),
                title=f"Declaration {decl.type_impot} {decl.annee_fiscale}",
                subtitle=f"{decl.mandat.numero if decl.mandat else 'N/A'} - {decl.statut}",
                description=f"Impot total: {decl.impot_total or 0} CHF | Canton: {decl.canton or 'N/A'}",
                score=score,
                url=config['url_pattern'].format(id=decl.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'type_impot': decl.type_impot,
                    'annee_fiscale': decl.annee_fiscale,
                    'impot_total': float(decl.impot_total) if decl.impot_total else 0,
                    'canton': decl.canton,
                    'statut': decl.statut,
                }
            ))

        return results

    def _search_taches(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les taches."""
        from core.models import Tache

        results = []
        config = self.ENTITY_CONFIG[EntityType.TACHE]

        q_filter = Q(is_active=True) & (
            Q(titre__icontains=query) |
            Q(description__icontains=query)
        )

        # Filtrer par user ou mandats
        if context.mandat_ids:
            q_filter &= Q(mandat_id__in=context.mandat_ids)

        taches = Tache.objects.filter(q_filter).select_related('mandat').prefetch_related('assignes')[:limit]

        for tache in taches:
            score = self._calculate_text_score(query, [
                tache.titre,
                tache.description or '',
            ])

            results.append(SearchResult(
                entity_type=EntityType.TACHE,
                entity_id=str(tache.id),
                title=tache.titre,
                subtitle=f"{tache.statut} - Priorite: {tache.priorite}",
                description=tache.description[:150] if tache.description else '',
                score=score,
                url=config['url_pattern'].format(id=tache.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'statut': tache.statut,
                    'priorite': tache.priorite,
                    'assignes': [str(u) for u in tache.assignes.all()],
                    'date_echeance': tache.date_echeance.isoformat() if tache.date_echeance else None,
                }
            ))

        return results

    def _search_comptes(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les comptes."""
        try:
            from comptabilite.models import Compte
        except ImportError:
            logger.debug("Module comptabilite non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.COMPTE]

        q_filter = Q(is_active=True) & (
            Q(numero__icontains=query) |
            Q(libelle__icontains=query)
        )

        comptes = Compte.objects.filter(q_filter)[:limit]

        for compte in comptes:
            score = self._calculate_text_score(query, [
                compte.numero,
                compte.libelle,
            ])

            results.append(SearchResult(
                entity_type=EntityType.COMPTE,
                entity_id=str(compte.id),
                title=f"{compte.numero} - {compte.libelle}",
                subtitle=f"Type: {compte.type_compte} | Classe: {compte.classe}",
                description=f"Solde: {compte.solde_debit - compte.solde_credit if hasattr(compte, 'solde_debit') else 0} CHF",
                score=score,
                url=config['url_pattern'].format(id=compte.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'numero': compte.numero,
                    'type_compte': compte.type_compte,
                    'classe': compte.classe,
                }
            ))

        return results

    def _search_dossiers(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les dossiers."""
        from documents.models import Dossier

        results = []
        config = self.ENTITY_CONFIG[EntityType.DOSSIER]

        q_filter = Q(is_active=True) & (
            Q(nom__icontains=query) |
            Q(description__icontains=query) |
            Q(chemin_complet__icontains=query)
        )

        if context.mandat_ids:
            q_filter &= Q(mandat_id__in=context.mandat_ids)

        dossiers = Dossier.objects.filter(q_filter).select_related('mandat', 'client')[:limit]

        for dossier in dossiers:
            score = self._calculate_text_score(query, [
                dossier.nom,
                dossier.description or '',
            ])

            results.append(SearchResult(
                entity_type=EntityType.DOSSIER,
                entity_id=str(dossier.id),
                title=dossier.nom,
                subtitle=f"{dossier.type_dossier} - {dossier.nombre_documents or 0} documents",
                description=dossier.chemin_complet or '',
                score=score,
                url=config['url_pattern'].format(id=dossier.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'type_dossier': dossier.type_dossier,
                    'nombre_documents': dossier.nombre_documents,
                    'chemin_complet': dossier.chemin_complet,
                }
            ))

        return results

    def _search_types_plans_comptables(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les types de plans comptables (PME, OHADA, Swiss GAAP, etc.)."""
        try:
            from comptabilite.models import TypePlanComptable
        except ImportError:
            logger.debug("Module comptabilite non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.TYPE_PLAN_COMPTABLE]

        # Recherche par code, nom, description, pays, norme
        q_filter = Q(is_active=True) & (
            Q(code__icontains=query) |
            Q(nom__icontains=query) |
            Q(description__icontains=query) |
            Q(pays__icontains=query) |
            Q(region__icontains=query) |
            Q(norme_comptable__icontains=query)
        )

        types_plans = TypePlanComptable.objects.filter(q_filter).prefetch_related('classes', 'plans')[:limit]

        for type_plan in types_plans:
            nb_classes = type_plan.classes.count()
            nb_plans = type_plan.plans.count()

            score = self._calculate_text_score(query, [
                type_plan.code,
                type_plan.nom,
                type_plan.description or '',
                type_plan.pays or '',
                type_plan.norme_comptable or '',
            ])

            # Construire le sous-titre
            region_info = f" ({type_plan.region})" if type_plan.region else ""
            subtitle = f"{type_plan.pays or 'International'}{region_info} - {nb_classes} classes, {nb_plans} plans"

            results.append(SearchResult(
                entity_type=EntityType.TYPE_PLAN_COMPTABLE,
                entity_id=str(type_plan.id),
                title=f"{type_plan.code} - {type_plan.nom}",
                subtitle=subtitle,
                description=type_plan.description[:200] if type_plan.description else f"Type de plan comptable {type_plan.nom}",
                score=score,
                url=config['url_pattern'].format(id=type_plan.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'code': type_plan.code,
                    'pays': type_plan.pays,
                    'region': type_plan.region,
                    'norme_comptable': type_plan.norme_comptable,
                    'version': type_plan.version,
                    'nb_classes': nb_classes,
                    'nb_plans': nb_plans,
                }
            ))

        return results

    def _search_classes_comptables(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les classes comptables."""
        try:
            from comptabilite.models import ClasseComptable
        except ImportError:
            logger.debug("Module comptabilite non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.CLASSE_COMPTABLE]

        # Recherche par numero, libelle, type_compte
        q_filter = Q(is_active=True) & (
            Q(numero__icontains=query) |
            Q(libelle__icontains=query) |
            Q(type_compte__icontains=query) |
            Q(type_plan__code__icontains=query) |
            Q(type_plan__nom__icontains=query)
        )

        classes = ClasseComptable.objects.filter(q_filter).select_related('type_plan')[:limit]

        for classe in classes:
            score = self._calculate_text_score(query, [
                str(classe.numero),
                classe.libelle,
                classe.type_compte,
                classe.type_plan.code if classe.type_plan else '',
            ])

            # Construire le sous-titre
            type_plan_info = classe.type_plan.code if classe.type_plan else 'N/A'
            subtitle = f"Classe {classe.numero} - {classe.get_type_compte_display()} ({type_plan_info})"

            results.append(SearchResult(
                entity_type=EntityType.CLASSE_COMPTABLE,
                entity_id=str(classe.id),
                title=f"Classe {classe.numero} - {classe.libelle}",
                subtitle=subtitle,
                description=f"Classe {classe.numero}: {classe.libelle} - Type: {classe.get_type_compte_display()}",
                score=score,
                url=config['url_pattern'].format(type_plan_id=classe.type_plan.id if classe.type_plan else ''),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'numero': classe.numero,
                    'libelle': classe.libelle,
                    'type_compte': classe.type_compte,
                    'type_compte_display': classe.get_type_compte_display(),
                    'type_plan_id': str(classe.type_plan.id) if classe.type_plan else None,
                    'type_plan_code': classe.type_plan.code if classe.type_plan else None,
                    'numero_debut': classe.numero_debut,
                    'numero_fin': classe.numero_fin,
                }
            ))

        return results

    def _search_plans_comptables(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les plans comptables."""
        try:
            from comptabilite.models import PlanComptable
        except ImportError:
            logger.debug("Module comptabilite non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.PLAN_COMPTABLE]

        # Recherche par nom, type_plan (FK vers TypePlanComptable), description
        q_filter = Q(is_active=True) & (
            Q(nom__icontains=query) |
            Q(type_plan__code__icontains=query) |
            Q(type_plan__nom__icontains=query) |
            Q(description__icontains=query)
        )

        # Filtrer par mandats si specifie
        if context.mandat_ids:
            q_filter &= (Q(mandat_id__in=context.mandat_ids) | Q(is_template=True))

        plans = PlanComptable.objects.filter(q_filter).select_related('mandat', 'type_plan')[:limit]

        for plan in plans:
            type_plan_code = plan.type_plan.code if plan.type_plan else ''
            type_plan_nom = plan.type_plan.nom if plan.type_plan else ''

            score = self._calculate_text_score(query, [
                plan.nom,
                type_plan_code,
                type_plan_nom,
                plan.description or '',
            ])

            # Construire le sous-titre
            if plan.is_template:
                subtitle = f"Template - {type_plan_nom}"
            else:
                mandat_info = plan.mandat.numero if plan.mandat else 'Sans mandat'
                subtitle = f"{type_plan_nom} - {mandat_info}"

            results.append(SearchResult(
                entity_type=EntityType.PLAN_COMPTABLE,
                entity_id=str(plan.id),
                title=plan.nom,
                subtitle=subtitle,
                description=plan.description[:200] if plan.description else f"Plan comptable {type_plan_nom}",
                score=score,
                url=config['url_pattern'].format(id=plan.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'type_plan_code': type_plan_code,
                    'type_plan_nom': type_plan_nom,
                    'is_template': plan.is_template,
                    'mandat_id': str(plan.mandat.id) if plan.mandat else None,
                    'mandat_numero': plan.mandat.numero if plan.mandat else None,
                    'nombre_comptes': plan.comptes.count() if hasattr(plan, 'comptes') else 0,
                }
            ))

        return results

    def _search_journaux(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les journaux comptables."""
        try:
            from comptabilite.models import Journal
        except ImportError:
            logger.debug("Module comptabilite non disponible")
            return []

        results = []
        config = self.ENTITY_CONFIG[EntityType.JOURNAL]

        # Recherche par code, libelle, type_journal
        q_filter = Q(is_active=True) & (
            Q(code__icontains=query) |
            Q(libelle__icontains=query) |
            Q(type_journal__icontains=query)
        )

        # Filtrer par mandats si specifie
        if context.mandat_ids:
            q_filter &= Q(mandat_id__in=context.mandat_ids)

        journaux = Journal.objects.filter(q_filter).select_related('mandat')[:limit]

        for journal in journaux:
            score = self._calculate_text_score(query, [
                journal.code,
                journal.libelle,
                journal.type_journal,
            ])

            results.append(SearchResult(
                entity_type=EntityType.JOURNAL,
                entity_id=str(journal.id),
                title=f"{journal.code} - {journal.libelle}",
                subtitle=f"{journal.get_type_journal_display()} - {journal.mandat.numero if journal.mandat else 'N/A'}",
                description=f"Type: {journal.get_type_journal_display()} | Prefixe: {journal.prefixe_piece or 'Aucun'}",
                score=score,
                url=config['url_pattern'].format(id=journal.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'code': journal.code,
                    'type_journal': journal.type_journal,
                    'type_journal_display': journal.get_type_journal_display(),
                    'mandat_id': str(journal.mandat.id) if journal.mandat else None,
                    'mandat_numero': journal.mandat.numero if journal.mandat else None,
                    'prefixe_piece': journal.prefixe_piece,
                    'numerotation_auto': journal.numerotation_auto,
                }
            ))

        return results

    def _search_utilisateurs(self, query: str, context: SearchContext, limit: int) -> List[SearchResult]:
        """Recherche dans les utilisateurs."""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        results = []
        config = self.ENTITY_CONFIG[EntityType.UTILISATEUR]

        q_filter = Q(is_active=True) & (
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

        # Multi-word: also search concatenated full name
        q_fullname = Q(full_name__icontains=query)
        q_fullname_rev = Q(full_name_rev__icontains=query)

        utilisateurs = User.objects.annotate(
            full_name=Concat('first_name', Value(' '), 'last_name', output_field=CharField()),
            full_name_rev=Concat('last_name', Value(' '), 'first_name', output_field=CharField()),
        ).filter(q_filter | q_fullname | q_fullname_rev).select_related('role').distinct()[:limit]

        for user in utilisateurs:
            score = self._calculate_text_score(query, [
                f"{user.first_name} {user.last_name}",
                user.last_name,
                user.first_name,
                user.username,
                user.email or '',
            ])

            role_nom = user.role.nom if user.role else 'Utilisateur'

            results.append(SearchResult(
                entity_type=EntityType.UTILISATEUR,
                entity_id=str(user.id),
                title=f"{user.first_name} {user.last_name}".strip() or user.username,
                subtitle=role_nom,
                description=f"Email: {user.email or 'N/A'} | Role: {role_nom}",
                score=score,
                url=config['url_pattern'].format(id=user.id),
                icon=config['icon'],
                color=config['color'],
                metadata={
                    'username': user.username,
                    'email': user.email,
                    'role': role_nom,
                    'type_utilisateur': user.type_utilisateur,
                }
            ))

        return results

    def _calculate_text_score(self, query: str, fields: List[str]) -> float:
        """Calcule un score simple de correspondance textuelle."""
        query_lower = query.lower()
        query_terms = query_lower.split()

        max_score = 0.0

        for field in fields:
            if not field:
                continue
            field_lower = field.lower()

            # Correspondance exacte
            if query_lower == field_lower:
                max_score = max(max_score, 1.0)
            # Contient la requete complete
            elif query_lower in field_lower:
                max_score = max(max_score, 0.8)
            # Commence par la requete
            elif field_lower.startswith(query_lower):
                max_score = max(max_score, 0.7)
            # Correspondance partielle (termes)
            else:
                matching_terms = sum(1 for term in query_terms if term in field_lower)
                if matching_terms > 0:
                    partial_score = 0.5 * (matching_terms / len(query_terms))
                    max_score = max(max_score, partial_score)

        return max_score

    def get_entity_by_id(self, entity_type: EntityType, entity_id: str) -> Optional[Any]:
        """Recupere une entite par son type et ID."""
        try:
            if entity_type == EntityType.DOCUMENT:
                from documents.models import Document
                return Document.objects.get(id=entity_id)
            elif entity_type == EntityType.CLIENT:
                from core.models import Client
                return Client.objects.get(id=entity_id)
            elif entity_type == EntityType.MANDAT:
                from core.models import Mandat
                return Mandat.objects.get(id=entity_id)
            elif entity_type == EntityType.EMPLOYE:
                from salaires.models import Employe
                return Employe.objects.get(id=entity_id)
            # ... autres types
        except Exception as e:
            logger.error(f"Erreur recuperation entite {entity_type.value}/{entity_id}: {e}")
        return None

    def format_entity_for_context(self, result: SearchResult) -> str:
        """Formate une entite pour inclusion dans le contexte du chat."""
        lines = [
            f"--- {result.entity_type.value.upper()}: {result.title} ---",
            f"Type: {result.entity_type.value}",
            f"Lien: {result.url}",
        ]

        if result.subtitle:
            lines.append(f"Info: {result.subtitle}")

        if result.description:
            lines.append(f"Description: {result.description}")

        # Ajouter les metadonnees pertinentes
        for key, value in result.metadata.items():
            if value and key not in ['ocr_text_preview']:
                lines.append(f"{key}: {value}")

        return "\n".join(lines)


# Instance singleton
universal_search = UniversalSearchService()
