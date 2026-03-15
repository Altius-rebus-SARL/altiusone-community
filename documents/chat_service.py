# documents/chat_service.py
"""
Service de chat IA avec tool use (function calling).

L'assistant IA utilise Qwen 2.5 14B avec tool use pour chercher
les donnees dont il a besoin via des outils ORM.
Le LLM decide lui-meme quels outils appeler selon la question.

Le flux:
1. Message utilisateur -> LLM avec tools
2. LLM retourne des tool_calls -> execution ORM -> resultats
3. Resultats reinjectes -> LLM genere la reponse finale
4. Max 3 iterations de tool calls

L'ancienne recherche universelle (universal_search.py) reste
intacte pour la navbar.
"""
import json as _json
import logging
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .chat_tools import CHAT_TOOLS, execute_tool_call
from .universal_search import (
    UniversalSearchService,
    SearchContext,
    SearchResult,
    EntityType,
    universal_search
)

logger = logging.getLogger(__name__)

# Nombre max d'iterations de tool calls (eviter les boucles infinies)
MAX_TOOL_ITERATIONS = 3


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

    # Prompt systeme pour le mode tool use (Qwen 2.5 14B)
    TOOL_SYSTEM_PROMPT = """Tu es l'assistant IA d'AltiusOne, logiciel de gestion pour fiduciaires suisses.

REGLES:
1. Reponds dans la langue de l'utilisateur (francais, allemand, italien ou anglais).
2. Utilise les outils disponibles pour chercher les donnees. N'invente JAMAIS de donnees.
3. Presente les resultats clairement. Les sources sont affichees automatiquement — ne mets pas de liens.
4. Montants au format suisse: 1'234.56 CHF.
5. Si les outils ne trouvent rien, dis-le simplement.
6. Ne corrige JAMAIS les noms propres ou raisons sociales.
"""

    # Ancien prompt pour fallback (sans tools)
    DEFAULT_SYSTEM_PROMPT = """Tu es l'assistant IA d'AltiusOne, logiciel de gestion d'entreprise suisse.

REGLES:
1. Reponds en francais, de maniere directe et concise.
2. Utilise UNIQUEMENT les donnees fournies ci-dessous. N'invente rien.
3. Si des donnees sont trouvees, presente-les clairement. Les sources sont affichees automatiquement sous ta reponse — ne mets PAS de liens/URLs dans ton texte.
4. Montants au format suisse: 1'234.56 CHF.
5. Si aucune donnee n'est trouvee, dis simplement que tu n'as pas trouve l'information.
6. Ne corrige JAMAIS les noms propres, raisons sociales ou termes metier de l'utilisateur. Utilise-les exactement tels quels.

DONNEES TROUVEES:
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
        EntityType.UTILISATEUR,
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

        Utilise le tool use: le LLM decide quels outils appeler
        pour chercher les donnees, puis genere la reponse.

        Args:
            conversation: Instance Conversation
            message: Message de l'utilisateur
            use_semantic_search: (ignore — garde pour compatibilite)
            max_context_results: (ignore — garde pour compatibilite)
            similarity_threshold: (ignore — garde pour compatibilite)
            entity_types: (ignore — garde pour compatibilite)

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

            # 2. Construire le system prompt et l'historique
            system_prompt = self.TOOL_SYSTEM_PROMPT
            if conversation.contexte_systeme:
                system_prompt = conversation.contexte_systeme

            # Ajouter le contexte mandat si specifie
            if conversation.mandat:
                mandat_ctx = (
                    f"\nContexte: Mandat {conversation.mandat.numero} - "
                    f"{conversation.mandat.client.raison_sociale if conversation.mandat.client else 'N/A'}"
                )
                system_prompt += mandat_ctx

            history = self._build_conversation_history(conversation)

            # 3. Construire les messages initiaux
            messages = [{'role': 'system', 'content': system_prompt}]
            # Ajouter l'historique (exclure le dernier user car on l'ajoute apres)
            if history:
                for msg in history[:-1]:
                    role = msg.get('role', '').lower()
                    content = msg.get('content', '')
                    if role in ['user', 'assistant'] and content:
                        messages.append({'role': role, 'content': content})
            messages.append({'role': 'user', 'content': message})

            # 4. Boucle tool use
            all_sources = []
            total_tokens_prompt = 0
            total_tokens_completion = 0

            for iteration in range(MAX_TOOL_ITERATIONS + 1):
                ai_response = self.ai_service.chat(
                    messages_override=messages,
                    temperature=float(conversation.temperature),
                    tools=CHAT_TOOLS if iteration < MAX_TOOL_ITERATIONS else None,
                )

                total_tokens_prompt += ai_response.get('tokens_prompt', 0)
                total_tokens_completion += ai_response.get('tokens_completion', 0)

                tool_calls = ai_response.get('tool_calls')
                if not tool_calls:
                    # Pas de tool calls -> reponse finale
                    break

                # Ajouter le message assistant avec tool_calls
                messages.append({
                    'role': 'assistant',
                    'content': ai_response.get('response', ''),
                    'tool_calls': tool_calls,
                })

                # Executer chaque tool call
                for tc in tool_calls:
                    func = tc.get('function', {})
                    tool_name = func.get('name', '')
                    tool_args = func.get('arguments', {})
                    if isinstance(tool_args, str):
                        try:
                            tool_args = _json.loads(tool_args)
                        except _json.JSONDecodeError:
                            tool_args = {'query': tool_args}

                    logger.info(f"Tool call: {tool_name}({tool_args})")

                    result_text, result_sources = execute_tool_call(
                        tool_name, tool_args, conversation.utilisateur
                    )
                    all_sources.extend(result_sources)

                    # Ajouter le resultat comme message tool
                    messages.append({
                        'role': 'tool',
                        'content': result_text,
                    })

            duree_ms = int((time.time() - start_time) * 1000)
            response_text = ai_response.get('response', '')

            # 5. Separer sources et entities
            sources = [s for s in all_sources if s.get('entity_type') == 'document']
            entities = [s for s in all_sources if s.get('entity_type') != 'document']

            # 6. Sauvegarder la reponse de l'assistant
            assistant_message = Message.objects.create(
                conversation=conversation,
                role='ASSISTANT',
                contenu=response_text,
                tokens_prompt=total_tokens_prompt,
                tokens_completion=total_tokens_completion,
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
                contenu=response_text,
                sources=sources,
                entities=entities,
                tokens_prompt=total_tokens_prompt,
                tokens_completion=total_tokens_completion,
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
        Stream a chat response as SSE events with tool use.

        Le flux tool use est non-streaming (les appels d'outils se font
        en synchrone), puis la reponse finale est streamee token par token.

        Yields JSON-serializable dicts with a 'type' field:
        - sources: tool call results (entities trouvees)
        - token: individual AI token
        - done: AI generation finished
        - message_saved: assistant message persisted
        - error: something went wrong
        """
        from documents.models import Message, Document

        start_time = time.time()

        try:
            # 1. Save user message
            user_message = Message.objects.create(
                conversation=conversation,
                role='USER',
                contenu=message
            )

            # 2. Build system prompt and history
            system_prompt = self.TOOL_SYSTEM_PROMPT
            if conversation.contexte_systeme:
                system_prompt = conversation.contexte_systeme

            if conversation.mandat:
                mandat_ctx = (
                    f"\nContexte: Mandat {conversation.mandat.numero} - "
                    f"{conversation.mandat.client.raison_sociale if conversation.mandat.client else 'N/A'}"
                )
                system_prompt += mandat_ctx

            history = self._build_conversation_history(conversation)

            # 3. Build initial messages
            messages = [{'role': 'system', 'content': system_prompt}]
            if history:
                for msg in history[:-1]:
                    role = msg.get('role', '').lower()
                    content = msg.get('content', '')
                    if role in ['user', 'assistant'] and content:
                        messages.append({'role': role, 'content': content})
            messages.append({'role': 'user', 'content': message})

            # 4. Tool use loop (non-streaming, uses chat() not chat_stream())
            all_sources = []
            total_tokens = 0

            for iteration in range(MAX_TOOL_ITERATIONS):
                ai_response = self.ai_service.chat(
                    messages_override=messages,
                    temperature=float(conversation.temperature),
                    tools=CHAT_TOOLS,
                )
                total_tokens += ai_response.get('tokens_completion', 0)

                tool_calls = ai_response.get('tool_calls')
                if not tool_calls:
                    # Pas de tool calls -> on va streamer la reponse finale
                    break

                # Ajouter le message assistant avec tool_calls
                messages.append({
                    'role': 'assistant',
                    'content': ai_response.get('response', ''),
                    'tool_calls': tool_calls,
                })

                # Executer chaque tool call
                for tc in tool_calls:
                    func = tc.get('function', {})
                    tool_name = func.get('name', '')
                    tool_args = func.get('arguments', {})
                    if isinstance(tool_args, str):
                        try:
                            tool_args = _json.loads(tool_args)
                        except _json.JSONDecodeError:
                            tool_args = {'query': tool_args}

                    logger.info(f"Tool call: {tool_name}({tool_args})")

                    result_text, result_sources = execute_tool_call(
                        tool_name, tool_args, conversation.utilisateur
                    )
                    all_sources.extend(result_sources)

                    messages.append({
                        'role': 'tool',
                        'content': result_text,
                    })
            else:
                # Max iterations atteint, on a deja la derniere reponse non-streaming
                pass

            # 5. Yield sources event (from tool calls)
            sources = [s for s in all_sources if s.get('entity_type') == 'document']
            entities = [s for s in all_sources if s.get('entity_type') != 'document']

            yield _json.dumps({
                'type': 'sources',
                'sources': sources,
                'entities': entities,
            }) + '\n'

            # 6. Stream the final response
            # If the last non-streaming call already has the answer, use it directly
            # Otherwise, make a streaming call WITHOUT tools for the final answer
            last_response_text = ai_response.get('response', '')

            if last_response_text and not ai_response.get('tool_calls'):
                # La derniere reponse non-streaming est la reponse finale
                # On la yield comme un seul token pour simplicite
                yield _json.dumps({
                    'type': 'token',
                    'token': last_response_text,
                }) + '\n'
                yield _json.dumps({
                    'type': 'done',
                    'model': '',
                    'tokens_used': total_tokens,
                    'processing_time_ms': int((time.time() - start_time) * 1000),
                }) + '\n'
                full_response = last_response_text
            else:
                # Stream la reponse finale (sans tools)
                full_response = ''
                for event in self.ai_service.chat_stream(
                    messages_override=messages,
                    temperature=float(conversation.temperature),
                ):
                    if event.get('error'):
                        yield _json.dumps({
                            'type': 'error',
                            'error': event['error'],
                        }) + '\n'
                        return

                    if event.get('done'):
                        total_tokens += event.get('tokens_used', 0)
                        yield _json.dumps({
                            'type': 'done',
                            'model': event.get('model', ''),
                            'tokens_used': total_tokens,
                            'processing_time_ms': event.get('processing_time_ms', 0),
                        }) + '\n'
                    elif event.get('type') == 'token':
                        token = event.get('token', '')
                        if token:
                            full_response += token
                            yield _json.dumps({
                                'type': 'token',
                                'token': token,
                            }) + '\n'

            # 7. Save assistant message
            duree_ms = int((time.time() - start_time) * 1000)

            assistant_message = Message.objects.create(
                conversation=conversation,
                role='ASSISTANT',
                contenu=full_response,
                tokens_prompt=0,
                tokens_completion=total_tokens,
                duree_ms=duree_ms,
                sources=all_sources
            )

            doc_ids = [s['entity_id'] for s in sources]
            if doc_ids:
                docs = Document.objects.filter(id__in=doc_ids)
                assistant_message.documents_contexte.set(docs)

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
        """Formate un resultat pour inclusion dans le contexte IA.

        N'inclut PAS de lien/URL — les sources cliquables sont affichees
        separement dans l'interface.
        """
        lines = [
            f"\n--- {result.entity_type.value.upper()}: {result.title} ---",
        ]

        if result.subtitle:
            lines.append(f"Info: {result.subtitle}")

        if result.description:
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
