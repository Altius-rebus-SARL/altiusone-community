# documents/chat_service.py
"""
Service de chat IA — flux sémantique direct.

Le flux (1 seul appel LLM, ~30s au lieu de ~2min):
1. Embedding de la question (~50ms)
2. Recherche pgvector sur TOUS les modules (~100ms)
3. Contexte pré-mâché injecté dans le prompt
4. UN SEUL appel LLM pour formuler la réponse (~30s)
5. Sources cliquables affichées automatiquement
"""
import json as _json
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

    # Prompt systeme — flux sémantique (embedding → pgvector → contexte → LLM)
    # Le LLM reçoit les données pré-trouvées, pas d'outil à appeler.
    SYSTEM_PROMPT = """Tu es l'assistant IA d'AltiusOne, logiciel de gestion pour fiduciaires suisses.

REGLES:
1. Reponds dans la langue de l'utilisateur (francais, allemand, italien ou anglais).
2. Utilise UNIQUEMENT les donnees fournies ci-dessous. N'invente JAMAIS de donnees.
3. Presente les resultats clairement. Les sources sont affichees automatiquement — ne mets pas de liens.
4. Montants au format suisse: 1'234.56 CHF.
5. Si aucune donnee n'est trouvee, dis simplement que tu n'as pas trouve l'information.
6. Ne corrige JAMAIS les noms propres ou raisons sociales.

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
        max_context_results: int = 5,
        similarity_threshold: float = 0.3,
        entity_types: Optional[List[EntityType]] = None
    ) -> ChatResponse:
        """
        Flux sémantique direct — 1 seul appel LLM.

        1. Embedding de la question (~50ms)
        2. Recherche pgvector sur TOUS les modules (~100ms)
        3. Contexte pré-mâché injecté dans le prompt
        4. UN SEUL appel LLM pour formuler la réponse (~30s)

        Total: ~30s au lieu de ~2min avec le tool calling.
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

            # 2. Recherche sémantique dans TOUS les modules (pgvector)
            search_results = self._search_all_entities(
                query=message,
                conversation=conversation,
                limit=max_context_results,
                entity_types=entity_types or self.DEFAULT_ENTITY_TYPES,
            )

            # 3. Construire le contexte à partir des résultats
            all_sources = []
            for r in search_results:
                all_sources.append({
                    'entity_type': r.entity_type.value,
                    'entity_id': r.entity_id,
                    'title': r.title,
                    'subtitle': r.subtitle,
                    'url': r.url,
                    'icon': r.icon,
                    'color': r.color,
                    'score': round(r.score, 3),
                })

            # 4. Construire le system prompt avec le contexte
            system_prompt = self._build_system_prompt(conversation, search_results)

            # Ajouter le contexte mandat(s)
            mandats_qs = conversation.mandats.select_related('client').all()
            if mandats_qs.exists():
                parts = [
                    f"Mandat {m.numero} - {m.client.raison_sociale if m.client else 'N/A'}"
                    for m in mandats_qs
                ]
                system_prompt += f"\nContexte: {' | '.join(parts)}"

            history = self._build_conversation_history(conversation)

            # 5. Construire les messages — PAS de tools, juste system + history + user
            messages = [{'role': 'system', 'content': system_prompt}]
            if history:
                for msg in history[:-1]:
                    role = msg.get('role', '').lower()
                    content = msg.get('content', '')
                    if role in ['user', 'assistant'] and content:
                        messages.append({'role': role, 'content': content})
            messages.append({'role': 'user', 'content': message})

            # 6. UN SEUL appel LLM (pas de tools)
            ai_response = self.ai_service.chat(
                messages_override=messages,
                temperature=float(conversation.temperature),
            )

            duree_ms = int((time.time() - start_time) * 1000)
            response_text = ai_response.get('response', '')

            # 7. Séparer sources et entités
            sources = [s for s in all_sources if s.get('entity_type') == 'document']
            entities = [s for s in all_sources if s.get('entity_type') != 'document']

            # 8. Sauvegarder la réponse
            assistant_message = Message.objects.create(
                conversation=conversation,
                role='ASSISTANT',
                contenu=response_text,
                tokens_prompt=ai_response.get('tokens_prompt', 0),
                tokens_completion=ai_response.get('tokens_completion', 0),
                duree_ms=duree_ms,
                sources=all_sources
            )

            doc_ids = [s['entity_id'] for s in sources]
            if doc_ids:
                docs = Document.objects.filter(id__in=doc_ids)
                assistant_message.documents_contexte.set(docs)

            if conversation.nombre_messages <= 2:
                conversation.generer_titre()

            return ChatResponse(
                contenu=response_text,
                sources=sources,
                entities=entities,
                tokens_prompt=ai_response.get('tokens_prompt', 0),
                tokens_completion=ai_response.get('tokens_completion', 0),
                duree_ms=duree_ms
            )

        except Exception as e:
            logger.error(f"Erreur chat conversation {conversation.id}: {e}")
            duree_ms = int((time.time() - start_time) * 1000)

            error_str = str(e)
            if '<html' in error_str.lower() or '<!doctype' in error_str.lower():
                error_str = "Le service IA est temporairement indisponible"

            Message.objects.create(
                conversation=conversation,
                role='SYSTEM',
                contenu=f"Erreur: {error_str}",
                duree_ms=duree_ms
            )

            return ChatResponse(
                contenu="Désolé, une erreur s'est produite lors du traitement de votre message.",
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
        max_context_results: int = 5,
        entity_types=None
    ):
        """
        Flux sémantique direct en streaming.

        1. Recherche pgvector (~100ms) — pas d'appel LLM
        2. Yield les sources immédiatement
        3. Stream la réponse LLM token par token (~30s)

        Yields JSON dicts: sources, token, done, message_saved, error
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

            # 2. Recherche sémantique pgvector (~100ms)
            search_results = self._search_all_entities(
                query=message,
                conversation=conversation,
                limit=max_context_results,
                entity_types=entity_types or self.DEFAULT_ENTITY_TYPES,
            )

            all_sources = []
            for r in search_results:
                all_sources.append({
                    'entity_type': r.entity_type.value,
                    'entity_id': r.entity_id,
                    'title': r.title,
                    'subtitle': r.subtitle,
                    'url': r.url,
                    'icon': r.icon,
                    'color': r.color,
                    'score': round(r.score, 3),
                })

            # 3. Yield sources immédiatement (avant le LLM)
            sources = [s for s in all_sources if s.get('entity_type') == 'document']
            entities = [s for s in all_sources if s.get('entity_type') != 'document']

            yield _json.dumps({
                'type': 'sources',
                'sources': sources,
                'entities': entities,
            }) + '\n'

            # 4. Construire le prompt avec contexte
            system_prompt = self._build_system_prompt(conversation, search_results)
            mandats_qs = conversation.mandats.select_related('client').all()
            if mandats_qs.exists():
                parts = [
                    f"Mandat {m.numero} - {m.client.raison_sociale if m.client else 'N/A'}"
                    for m in mandats_qs
                ]
                system_prompt += f"\nContexte: {' | '.join(parts)}"

            history = self._build_conversation_history(conversation)
            messages = [{'role': 'system', 'content': system_prompt}]
            if history:
                for msg in history[:-1]:
                    role = msg.get('role', '').lower()
                    content = msg.get('content', '')
                    if role in ['user', 'assistant'] and content:
                        messages.append({'role': role, 'content': content})
            messages.append({'role': 'user', 'content': message})

            # 5. Stream la réponse LLM (UN SEUL appel, pas de tools)
            full_response = ''
            total_tokens = 0

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
                    total_tokens = event.get('tokens_used', 0)
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

            # 6. Save assistant message
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
        mandats_qs = conversation.mandats.all()
        if mandats_qs.exists():
            mandat_ids = [str(m.id) for m in mandats_qs]

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
        Construit le prompt système — compact pour modèle 3B.

        Max ~2000 tokens de contexte pour éviter les timeouts.
        """
        base_prompt = conversation.contexte_systeme or self.SYSTEM_PROMPT

        if not search_results:
            contexte = "Aucune donnee trouvee pour cette requete."
        else:
            # Format compact — 1 ligne par résultat, max 5
            lines = []
            for r in search_results[:5]:
                line = f"- [{r.entity_type.value}] {r.title}"
                if r.subtitle:
                    line += f" | {r.subtitle}"
                # Métadonnées importantes seulement
                for key in ('montant_ttc', 'statut', 'date_emission', 'date_document', 'email'):
                    val = r.metadata.get(key)
                    if val:
                        line += f" | {key}: {val}"
                lines.append(line)
            contexte = "\n".join(lines)

        # Ajouter mandats si spécifiés
        mandats_qs = conversation.mandats.select_related('client').all()
        if mandats_qs.exists():
            parts = [
                f"Mandat {m.numero} - {m.client.raison_sociale if m.client else 'N/A'}"
                for m in mandats_qs
            ]
            contexte = " | ".join(parts) + "\n\n" + contexte

        return base_prompt.format(contexte=contexte)

    def _build_intelligence_context(self, conversation) -> str:
        """
        Construit le contexte intelligence (insights, relations, digest).
        """
        sections = []
        mandats_qs = conversation.mandats.all()
        if not mandats_qs.exists():
            return ""

        try:
            from documents.models_intelligence import MandatInsight, MandatDigest, DocumentRelation
            from django.db.models import Q
            from django.utils import timezone

            # Insights non traites
            insights = MandatInsight.objects.filter(
                mandat__in=mandats_qs, traite=False
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
                mandat__in=mandats_qs
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
