# documents/chat_service.py
"""
Service de chat IA avec recherche universelle.

Fournit une interface pour interagir avec l'assistant AI
en utilisant le contexte de TOUTES les donnees de la base:
- Documents (avec recherche semantique)
- Clients, Mandats, Employes
- Factures, Ecritures comptables
- Declarations TVA/fiscales
- Et plus encore...

Chaque resultat est cliquable et renvoie vers la fiche correspondante.
"""
import logging
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .universal_search import (
    UniversalSearchService,
    SearchContext,
    SearchResult,
    EntityType,
    universal_search
)

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """Reponse du service de chat."""
    contenu: str
    sources: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]  # Entites trouvees (clients, employes, etc.)
    tokens_prompt: int
    tokens_completion: int
    duree_ms: int
    erreur: Optional[str] = None


@dataclass
class SourceInfo:
    """Information sur une source utilisee."""
    entity_type: str
    entity_id: str
    title: str
    subtitle: str
    url: str
    icon: str
    color: str
    score: float
    snippet: str = ''
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'title': self.title,
            'subtitle': self.subtitle,
            'url': self.url,
            'icon': self.icon,
            'color': self.color,
            'score': round(self.score, 3),
            'snippet': self.snippet,
            'metadata': self.metadata,
        }


class ChatService:
    """
    Service de chat avec contexte universel.

    Combine:
    - Recherche universelle dans toutes les entites
    - Recherche semantique pour les documents
    - Generation de reponse via l'API AltiusOne AI
    - Gestion de l'historique de conversation
    - Resultats cliquables avec liens vers les fiches
    """

    # Prompt systeme par defaut - enrichi pour gerer tous les types de donnees
    DEFAULT_SYSTEM_PROMPT = """Tu es un assistant IA specialise pour une fiduciaire suisse.
Tu as acces a toutes les donnees de l'entreprise:
- Documents (factures, contrats, releves, etc.)
- Clients et contacts
- Mandats et dossiers
- Employes et fiches de salaire
- Types de plans comptables (PME Suisse, OHADA, Swiss GAAP RPC, etc.)
- Classes comptables (structure des comptes par type de plan)
- Plans comptables (instances pour chaque mandat)
- Comptes et journaux comptables
- Pieces comptables (factures d'achat/vente, notes de frais, etc.)
- Ecritures comptables
- Declarations TVA et fiscales
- Taches et projets

REGLES IMPORTANTES:
1. Reponds toujours en francais
2. Base tes reponses UNIQUEMENT sur les donnees fournies en contexte
3. Si tu trouves des informations, cite TOUJOURS la source avec son type et son lien
4. Pour les montants, utilise le format suisse (ex: 1'000.00 CHF)
5. Si tu ne trouves pas l'information demandee, dis-le clairement
6. Quand tu mentionnes une entite (client, employe, document, plan comptable, etc.),
   indique qu'elle est cliquable pour voir la fiche complete

FORMAT DES SOURCES:
Quand tu cites une source, utilise ce format:
- Pour un document: [Document: nom_fichier]
- Pour un client: [Client: raison_sociale]
- Pour un employe: [Employe: prenom nom]
- Pour une facture: [Facture: numero]
- Pour une piece comptable: [Piece: numero - libelle]
- Pour un type de plan: [Type de plan: code - nom]
- Pour une classe comptable: [Classe: numero - libelle]
- Pour un plan comptable: [Plan comptable: nom]
- Pour un journal: [Journal: code - libelle]
- Pour un compte: [Compte: numero - libelle]
- etc.

CONTEXTE DISPONIBLE:
{contexte}
"""

    # Types d'entites a rechercher par defaut
    DEFAULT_ENTITY_TYPES = [
        EntityType.DOCUMENT,
        EntityType.CLIENT,
        EntityType.MANDAT,
        EntityType.EMPLOYE,
        EntityType.CONTACT,
        EntityType.FACTURE,
        EntityType.ECRITURE,
        EntityType.PIECE_COMPTABLE,
        EntityType.COMPTE,
        EntityType.TYPE_PLAN_COMPTABLE,
        EntityType.CLASSE_COMPTABLE,
        EntityType.PLAN_COMPTABLE,
        EntityType.JOURNAL,
        EntityType.DECLARATION_TVA,
        EntityType.DECLARATION_FISCALE,
        EntityType.TACHE,
        EntityType.DOSSIER,
    ]

    def __init__(self):
        self._ai_service = None
        self._search_service = None
        self._universal_search = universal_search

    @property
    def ai_service(self):
        """Acces au service AI (lazy loading)."""
        if self._ai_service is None:
            from documents.ai_service import ai_service
            self._ai_service = ai_service
        return self._ai_service

    @property
    def search_service(self):
        """Acces au service de recherche documentaire (lazy loading)."""
        if self._search_service is None:
            from documents.search import search_service
            self._search_service = search_service
        return self._search_service

    def chat(
        self,
        conversation,
        message: str,
        use_semantic_search: bool = True,
        max_context_results: int = 10,
        similarity_threshold: float = 0.3,
        entity_types: Optional[List[EntityType]] = None
    ) -> ChatResponse:
        """
        Envoie un message dans une conversation et retourne la reponse.

        Args:
            conversation: Instance Conversation
            message: Message de l'utilisateur
            use_semantic_search: Utiliser la recherche semantique
            max_context_results: Nombre max de resultats pour le contexte
            similarity_threshold: Seuil de similarite
            entity_types: Types d'entites a rechercher (None = tous)

        Returns:
            ChatResponse avec la reponse, sources et entites
        """
        from documents.models import Message, Document

        start_time = time.time()

        try:
            # 1. Sauvegarder le message utilisateur
            user_message = Message.objects.create(
                conversation=conversation,
                role='USER',
                contenu=message
            )

            # 2. Recherche universelle
            search_results = []
            sources = []
            entities = []

            if use_semantic_search:
                search_results = self._search_all_entities(
                    query=message,
                    conversation=conversation,
                    limit=max_context_results,
                    entity_types=entity_types or self.DEFAULT_ENTITY_TYPES
                )

                # Separer documents et autres entites
                for result in search_results:
                    source_info = SourceInfo(
                        entity_type=result.entity_type.value,
                        entity_id=result.entity_id,
                        title=result.title,
                        subtitle=result.subtitle,
                        url=result.url,
                        icon=result.icon,
                        color=result.color,
                        score=result.score,
                        snippet=result.description[:200] if result.description else '',
                        metadata=result.metadata
                    )

                    if result.entity_type == EntityType.DOCUMENT:
                        sources.append(source_info.to_dict())
                    else:
                        entities.append(source_info.to_dict())

            # 3. Construire le prompt systeme avec contexte
            system_prompt = self._build_system_prompt(
                conversation=conversation,
                search_results=search_results
            )

            # 4. Construire l'historique de conversation
            history = self._build_conversation_history(conversation)

            # 5. Appeler l'API AI
            ai_response = self.ai_service.chat(
                message=message,
                history=history,
                system_prompt=system_prompt,
                temperature=float(conversation.temperature)
            )

            duree_ms = int((time.time() - start_time) * 1000)

            # 6. Sauvegarder la reponse de l'assistant
            # Combiner sources et entities pour le stockage
            all_sources = sources + entities

            assistant_message = Message.objects.create(
                conversation=conversation,
                role='ASSISTANT',
                contenu=ai_response.get('response', ''),
                tokens_prompt=ai_response.get('tokens_prompt', 0),
                tokens_completion=ai_response.get('tokens_completion', 0),
                duree_ms=duree_ms,
                sources=all_sources
            )

            # Associer les documents de contexte
            doc_ids = [s['entity_id'] for s in sources]
            if doc_ids:
                docs = Document.objects.filter(id__in=doc_ids)
                assistant_message.documents_contexte.set(docs)

            # Generer le titre si c'est le premier message
            if conversation.nombre_messages <= 2:
                conversation.generer_titre()

            return ChatResponse(
                contenu=ai_response.get('response', ''),
                sources=sources,
                entities=entities,
                tokens_prompt=ai_response.get('tokens_prompt', 0),
                tokens_completion=ai_response.get('tokens_completion', 0),
                duree_ms=duree_ms
            )

        except Exception as e:
            logger.error(f"Erreur chat conversation {conversation.id}: {e}")
            duree_ms = int((time.time() - start_time) * 1000)

            # Sanitize error message (never save raw HTML)
            error_str = str(e)
            if '<html' in error_str.lower() or '<!doctype' in error_str.lower():
                error_str = "Le service IA est temporairement indisponible"

            # Sauvegarder le message d'erreur
            Message.objects.create(
                conversation=conversation,
                role='SYSTEM',
                contenu=f"Erreur: {error_str}",
                duree_ms=duree_ms
            )

            return ChatResponse(
                contenu="Desolee, une erreur s'est produite lors du traitement de votre message.",
                sources=[],
                entities=[],
                tokens_prompt=0,
                tokens_completion=0,
                duree_ms=duree_ms,
                erreur=error_str
            )

    def chat_stream(
        self,
        conversation,
        message: str,
        use_semantic_search: bool = True,
        max_context_results: int = 10,
        entity_types=None
    ):
        """
        Stream a chat response as SSE events.

        Yields JSON-serializable dicts with a 'type' field:
        - sources: search results found
        - token: individual AI token
        - done: AI generation finished
        - message_saved: assistant message persisted
        - error: something went wrong
        """
        import json as _json
        import time
        from documents.models import Message, Document

        start_time = time.time()

        try:
            # 1. Save user message
            user_message = Message.objects.create(
                conversation=conversation,
                role='USER',
                contenu=message
            )

            # 2. Universal search
            search_results = []
            sources = []
            entities = []

            if use_semantic_search:
                search_results = self._search_all_entities(
                    query=message,
                    conversation=conversation,
                    limit=max_context_results,
                    entity_types=entity_types or self.DEFAULT_ENTITY_TYPES
                )

                for result in search_results:
                    source_info = SourceInfo(
                        entity_type=result.entity_type.value,
                        entity_id=result.entity_id,
                        title=result.title,
                        subtitle=result.subtitle,
                        url=result.url,
                        icon=result.icon,
                        color=result.color,
                        score=result.score,
                        snippet=result.description[:200] if result.description else '',
                        metadata=result.metadata
                    )

                    if result.entity_type == EntityType.DOCUMENT:
                        sources.append(source_info.to_dict())
                    else:
                        entities.append(source_info.to_dict())

            # 3. Yield sources event
            yield _json.dumps({
                'type': 'sources',
                'sources': sources,
                'entities': entities,
            }) + '\n'

            # 4. Build system prompt and history
            system_prompt = self._build_system_prompt(
                conversation=conversation,
                search_results=search_results
            )
            history = self._build_conversation_history(conversation)

            # 5. Stream AI response
            full_response = ''
            model_name = ''
            tokens_used = 0
            processing_time_ms = 0

            for event in self.ai_service.chat_stream(
                message=message,
                history=history,
                system_prompt=system_prompt,
                temperature=float(conversation.temperature)
            ):
                if event.get('error'):
                    yield _json.dumps({
                        'type': 'error',
                        'error': event['error'],
                    }) + '\n'
                    return

                if event.get('done'):
                    model_name = event.get('model', '')
                    tokens_used = event.get('tokens_used', 0)
                    processing_time_ms = event.get('processing_time_ms', 0)
                    yield _json.dumps({
                        'type': 'done',
                        'model': model_name,
                        'tokens_used': tokens_used,
                        'processing_time_ms': processing_time_ms,
                    }) + '\n'
                else:
                    token = event.get('token', '')
                    if token:
                        full_response += token
                        yield _json.dumps({
                            'type': 'token',
                            'token': token,
                        }) + '\n'

            # 6. Save assistant message
            duree_ms = int((time.time() - start_time) * 1000)
            all_sources = sources + entities

            assistant_message = Message.objects.create(
                conversation=conversation,
                role='ASSISTANT',
                contenu=full_response,
                tokens_prompt=0,
                tokens_completion=tokens_used,
                duree_ms=duree_ms,
                sources=all_sources
            )

            doc_ids = [s['entity_id'] for s in sources]
            if doc_ids:
                docs = Document.objects.filter(id__in=doc_ids)
                assistant_message.documents_contexte.set(docs)

            # 7. Yield message_saved event
            yield _json.dumps({
                'type': 'message_saved',
                'message_id': str(assistant_message.id),
            }) + '\n'

            # 8. Generate title if first message
            if conversation.nombre_messages <= 2:
                conversation.generer_titre()

        except Exception as e:
            logger.error(f"Erreur chat stream conversation {conversation.id}: {e}")
            error_str = str(e)
            if '<html' in error_str.lower() or '<!doctype' in error_str.lower():
                error_str = "Le service IA est temporairement indisponible"

            yield _json.dumps({
                'type': 'error',
                'error': error_str,
            }) + '\n'

    def _search_all_entities(
        self,
        query: str,
        conversation,
        limit: int,
        entity_types: List[EntityType]
    ) -> List[SearchResult]:
        """
        Recherche dans toutes les entites.

        Args:
            query: Requete de recherche
            conversation: Conversation pour le contexte
            limit: Nombre max de resultats
            entity_types: Types a rechercher

        Returns:
            Liste de SearchResult
        """
        # Construire le contexte de recherche
        mandat_ids = None
        if conversation.mandat:
            mandat_ids = [str(conversation.mandat.id)]

        context = SearchContext(
            user=conversation.utilisateur,
            mandat_ids=mandat_ids,
            entity_types=entity_types
        )

        # Recherche universelle
        results = self._universal_search.search(
            query=query,
            context=context,
            limit=limit,
            semantic_weight=0.6
        )

        logger.info(f"Recherche universelle '{query}': {len(results)} resultats")

        return results

    def _build_system_prompt(
        self,
        conversation,
        search_results: List[SearchResult]
    ) -> str:
        """
        Construit le prompt systeme avec le contexte universel.

        Args:
            conversation: Conversation
            search_results: Resultats de recherche

        Returns:
            Prompt systeme complet
        """
        # Utiliser le contexte personnalise si defini
        if conversation.contexte_systeme:
            base_prompt = conversation.contexte_systeme
        else:
            base_prompt = self.DEFAULT_SYSTEM_PROMPT

        # Construire le contexte a partir des resultats
        contexte_parts = []

        if not search_results:
            contexte_parts.append("""
ATTENTION: Aucune donnee n'a ete trouvee correspondant a cette requete.
Cela peut signifier:
- Les donnees n'ont pas encore ete indexees
- La requete ne correspond a aucune entite dans la base
- L'utilisateur n'a pas acces aux donnees demandees

Reponds en indiquant que tu n'as pas trouve de donnees pertinentes.
""")
        else:
            # Grouper par type d'entite
            by_type = {}
            for result in search_results:
                type_name = result.entity_type.value
                if type_name not in by_type:
                    by_type[type_name] = []
                by_type[type_name].append(result)

            for type_name, results in by_type.items():
                contexte_parts.append(f"\n=== {type_name.upper()}S TROUVES ({len(results)}) ===")

                for result in results:
                    contexte_parts.append(self._format_result_for_context(result))

        contexte = "\n".join(contexte_parts)

        # Ajouter info sur le mandat si specifie
        if conversation.mandat:
            contexte = f"Contexte: Mandat {conversation.mandat.numero} - {conversation.mandat.client.raison_sociale if conversation.mandat.client else 'N/A'}\n\n" + contexte

        # Ajouter le contexte intelligence (insights, relations, digest)
        intelligence_context = self._build_intelligence_context(conversation)
        if intelligence_context:
            contexte += "\n\n" + intelligence_context

        return base_prompt.format(contexte=contexte)

    def _build_intelligence_context(self, conversation) -> str:
        """
        Construit le contexte intelligence (insights, relations, digest).
        """
        sections = []
        mandat = conversation.mandat
        if not mandat:
            return ""

        try:
            from documents.models_intelligence import MandatInsight, MandatDigest, DocumentRelation
            from django.db.models import Q
            from django.utils import timezone

            # Insights non traites
            insights = MandatInsight.objects.filter(
                mandat=mandat, traite=False
            ).filter(
                Q(date_expiration__isnull=True) | Q(date_expiration__gt=timezone.now())
            ).order_by('-severite', '-created_at')[:10]

            if insights:
                sections.append("## Alertes et Insights actifs")
                for i in insights:
                    sections.append(
                        f"- [{i.get_severite_display()}] {i.titre}: "
                        f"{i.description[:200]}"
                    )

            # Relations des documents en contexte
            from documents.models import Message
            doc_ids = list(
                Message.objects.filter(
                    conversation=conversation
                ).values_list(
                    'documents_contexte', flat=True
                ).distinct()
            )
            doc_ids = [d for d in doc_ids if d is not None]

            if doc_ids:
                relations = DocumentRelation.objects.filter(
                    Q(document_source_id__in=doc_ids) | Q(document_cible_id__in=doc_ids)
                ).select_related(
                    'document_source', 'document_cible'
                )[:10]

                if relations:
                    sections.append("## Relations entre documents")
                    for r in relations:
                        sections.append(
                            f"- {r.document_source.nom_fichier} <-> "
                            f"{r.document_cible.nom_fichier}: "
                            f"{r.get_type_relation_display()} "
                            f"(score: {r.score_similarite})"
                        )

            # Dernier digest
            digest = MandatDigest.objects.filter(
                mandat=mandat
            ).order_by('-periode_fin').first()

            if digest:
                sections.append(
                    f"## Dernier résumé ({digest.get_type_digest_display()} "
                    f"{digest.periode_debut} - {digest.periode_fin})"
                )
                sections.append(digest.resume[:500])

        except Exception as e:
            logger.warning(f"Erreur construction contexte intelligence: {e}")

        return "\n".join(sections)

    def _format_result_for_context(self, result: SearchResult) -> str:
        """Formate un resultat pour inclusion dans le contexte."""
        lines = [
            f"\n--- {result.entity_type.value.upper()}: {result.title} ---",
            f"Lien: {result.url}",
        ]

        if result.subtitle:
            lines.append(f"Info: {result.subtitle}")

        if result.description:
            # Limiter la description
            desc = result.description[:1500]
            if len(result.description) > 1500:
                desc += "..."
            lines.append(f"Details: {desc}")

        # Ajouter les metadonnees importantes
        important_keys = ['email', 'telephone', 'montant', 'montant_ttc', 'statut',
                         'date_document', 'date_emission', 'type_document', 'fonction']

        for key in important_keys:
            if key in result.metadata and result.metadata[key]:
                lines.append(f"{key}: {result.metadata[key]}")

        # Ajouter le texte OCR pour les documents
        if result.entity_type == EntityType.DOCUMENT:
            ocr_preview = result.metadata.get('ocr_text_preview')
            if ocr_preview:
                lines.append(f"Contenu OCR:\n{ocr_preview}")

        return "\n".join(lines)

    def _build_conversation_history(self, conversation, max_messages: int = 10) -> List[Dict]:
        """
        Construit l'historique de conversation pour l'API.

        Args:
            conversation: Instance Conversation
            max_messages: Nombre max de messages a inclure

        Returns:
            Liste de messages au format API
        """
        from documents.models import Message

        messages = Message.objects.filter(
            conversation=conversation,
            role__in=['USER', 'ASSISTANT']
        ).order_by('-created_at')[:max_messages]

        # Inverser pour avoir l'ordre chronologique
        messages = list(reversed(messages))

        history = []
        for msg in messages:
            history.append({
                'role': msg.role.lower(),
                'content': msg.contenu
            })

        return history

    def search_entities(
        self,
        query: str,
        user,
        mandat_id: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Recherche des entites pour l'interface (autocomplete, etc.).

        Args:
            query: Requete de recherche
            user: Utilisateur
            mandat_id: Filtrer par mandat
            entity_types: Types a rechercher (noms string)
            limit: Limite de resultats

        Returns:
            Liste de resultats en dict
        """
        # Convertir les noms en EntityType
        types = None
        if entity_types:
            types = []
            for type_name in entity_types:
                try:
                    types.append(EntityType(type_name))
                except ValueError:
                    logger.warning(f"Type d'entite inconnu: {type_name}")

        context = SearchContext(
            user=user,
            mandat_ids=[mandat_id] if mandat_id else None,
            entity_types=types
        )

        results = self._universal_search.search(
            query=query,
            context=context,
            limit=limit
        )

        return [r.to_dict() for r in results]

    def get_conversation_summary(self, conversation) -> Dict:
        """
        Genere un resume de la conversation.

        Returns:
            Dict avec resume et statistiques
        """
        from documents.models import Message

        stats = {
            'nombre_messages': conversation.nombre_messages,
            'tokens_utilises': conversation.tokens_utilises,
            'documents_references': set(),
            'entities_references': {},
            'themes': []
        }

        # Collecter les entites referencees
        messages = Message.objects.filter(
            conversation=conversation
        ).prefetch_related('documents_contexte')

        for msg in messages:
            # Documents
            for doc in msg.documents_contexte.all():
                stats['documents_references'].add(doc.nom_fichier)

            # Autres entites depuis les sources
            if msg.sources:
                for source in msg.sources:
                    entity_type = source.get('entity_type', 'unknown')
                    if entity_type not in stats['entities_references']:
                        stats['entities_references'][entity_type] = set()
                    stats['entities_references'][entity_type].add(source.get('title', ''))

        # Convertir sets en listes
        stats['documents_references'] = list(stats['documents_references'])
        for key in stats['entities_references']:
            stats['entities_references'][key] = list(stats['entities_references'][key])

        return stats

    # Methodes de compatibilite avec l'ancien service
    def search_documents(
        self,
        query: str,
        mandat_id: str,
        limit: int = 10,
        search_type: str = 'hybrid'
    ) -> List[Dict]:
        """
        Recherche des documents (compatibilite).

        Returns:
            Liste de documents avec scores de pertinence
        """
        results = self.search_service.search(
            query=query,
            mandat_id=mandat_id,
            search_type=search_type,
            limit=limit
        )

        return [{
            'id': str(r.document.id),
            'nom': r.document.nom_fichier,
            'type': r.document.prediction_type,
            'date': r.document.date_document.isoformat() if r.document.date_document else None,
            'score': round(r.score, 3),
            'snippet': r.snippet,
            'match_type': r.match_type,
            'url': f'/documents/documents/{r.document.id}/'
        } for r in results]


# Instance singleton
chat_service = ChatService()
