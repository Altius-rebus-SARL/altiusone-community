# documents/search.py
"""
Service de recherche semantique pour les documents.

Combine recherche classique (full-text) et recherche vectorielle (PGVector).
Utilise le SDK AltiusOne AI pour la generation d'embeddings 768D.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from django.db.models import Q, F, Value, FloatField
from django.db.models.functions import Greatest
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Résultat de recherche avec scores."""
    document: Any
    score: float
    match_type: str  # 'semantic', 'fulltext', 'combined'
    snippet: str = ''
    highlights: List[str] = None

    def __post_init__(self):
        if self.highlights is None:
            self.highlights = []


class DocumentSearchService:
    """
    Service de recherche hybride pour les documents.

    Combine:
    - Recherche full-text PostgreSQL (ts_vector)
    - Recherche par trigrammes (pg_trgm)
    - Recherche sémantique (PGVector embeddings)
    """

    def __init__(self):
        from documents.embeddings import embedding_service
        self.embedding_service = embedding_service

    def search(
        self,
        query: str,
        mandat_id: Optional[str] = None,
        user=None,
        search_type: str = 'hybrid',
        limit: int = 50,
        semantic_threshold: float = 0.5,
        fulltext_weight: float = 0.4,
        semantic_weight: float = 0.6,
    ) -> List[SearchResult]:
        """
        Recherche de documents avec différentes stratégies.

        Args:
            query: Texte de recherche
            mandat_id: Filtrer par mandat (optionnel)
            user: Utilisateur pour filtrage des permissions
            search_type: 'fulltext', 'semantic', ou 'hybrid'
            limit: Nombre max de résultats
            semantic_threshold: Seuil de similarité pour recherche sémantique
            fulltext_weight: Poids de la recherche full-text dans le score final
            semantic_weight: Poids de la recherche sémantique dans le score final

        Returns:
            Liste de SearchResult triés par pertinence
        """
        if not query or not query.strip():
            return []

        query = query.strip()

        if search_type == 'fulltext':
            return self._search_fulltext(query, mandat_id, user, limit)
        elif search_type == 'semantic':
            return self._search_semantic(query, mandat_id, user, limit, semantic_threshold)
        else:  # hybrid
            return self._search_hybrid(
                query, mandat_id, user, limit,
                semantic_threshold, fulltext_weight, semantic_weight
            )

    def _search_fulltext(
        self,
        query: str,
        mandat_id: Optional[str],
        user,
        limit: int
    ) -> List[SearchResult]:
        """Recherche full-text avec PostgreSQL."""
        from documents.models import Document

        # Construire la requête de base
        qs = Document.objects.filter(is_active=True).select_related(
            'mandat__client', 'type_document', 'categorie'
        )

        # Filtrer par mandat
        if mandat_id:
            qs = qs.filter(mandat_id=mandat_id)

        # Filtrer par permissions utilisateur
        if user and not user.is_manager():
            qs = qs.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Recherche full-text sur plusieurs champs
        search_vector = SearchVector(
            'nom_fichier', weight='A',
            config='french'
        ) + SearchVector(
            'description', weight='B',
            config='french'
        ) + SearchVector(
            'ocr_text', weight='C',
            config='french'
        )

        search_query = SearchQuery(query, config='french')

        # Recherche par trigrammes pour la tolérance aux fautes
        qs = qs.annotate(
            search_rank=SearchRank(search_vector, search_query),
            trigram_similarity=Greatest(
                TrigramSimilarity('nom_fichier', query),
                TrigramSimilarity('description', query),
            )
        ).filter(
            Q(search_rank__gt=0.01) | Q(trigram_similarity__gt=0.3) |
            Q(nom_fichier__icontains=query) | Q(ocr_text__icontains=query)
        ).annotate(
            final_score=Greatest(
                F('search_rank') * 0.7 + F('trigram_similarity') * 0.3,
                Value(0.01, output_field=FloatField())
            )
        ).order_by('-final_score')[:limit]

        results = []
        for doc in qs:
            snippet = self._extract_snippet(doc.ocr_text or doc.description, query)
            results.append(SearchResult(
                document=doc,
                score=float(doc.final_score),
                match_type='fulltext',
                snippet=snippet
            ))

        return results

    def _search_semantic(
        self,
        query: str,
        mandat_id: Optional[str],
        user,
        limit: int,
        threshold: float
    ) -> List[SearchResult]:
        """Recherche sémantique avec PGVector."""
        from documents.models import DocumentEmbedding, Document

        # Générer l'embedding de la requête
        query_embedding = self.embedding_service.generate_embedding(query)
        if query_embedding is None:
            logger.warning("Impossible de générer l'embedding pour la requête")
            return []

        # Recherche par similarité
        similar_docs = DocumentEmbedding.search_similar(
            query_embedding=query_embedding,
            limit=limit,
            threshold=threshold,
            mandat_id=mandat_id
        )

        results = []
        for doc_emb in similar_docs:
            doc = doc_emb.document

            # Vérifier permissions utilisateur
            if user and not user.is_manager():
                if doc.mandat.responsable != user and user not in doc.mandat.equipe.all():
                    continue

            # Calculer le score de similarité (1 - distance)
            similarity = 1 - doc_emb.distance

            snippet = self._extract_snippet(doc.ocr_text or doc.description, query)
            results.append(SearchResult(
                document=doc,
                score=float(similarity),
                match_type='semantic',
                snippet=snippet
            ))

        return results

    def _search_hybrid(
        self,
        query: str,
        mandat_id: Optional[str],
        user,
        limit: int,
        semantic_threshold: float,
        fulltext_weight: float,
        semantic_weight: float
    ) -> List[SearchResult]:
        """
        Recherche hybride combinant full-text et sémantique.

        Fusion des scores avec pondération configurable.
        """
        # Effectuer les deux recherches
        fulltext_results = self._search_fulltext(query, mandat_id, user, limit * 2)
        semantic_results = self._search_semantic(query, mandat_id, user, limit * 2, semantic_threshold)

        # Créer un dictionnaire pour fusion des scores
        combined_scores: Dict[str, Dict[str, Any]] = {}

        # Normaliser et ajouter les scores full-text
        if fulltext_results:
            max_ft_score = max(r.score for r in fulltext_results) or 1
            for result in fulltext_results:
                doc_id = str(result.document.id)
                normalized_score = result.score / max_ft_score
                combined_scores[doc_id] = {
                    'document': result.document,
                    'fulltext_score': normalized_score,
                    'semantic_score': 0,
                    'snippet': result.snippet
                }

        # Normaliser et ajouter les scores sémantiques
        if semantic_results:
            max_sem_score = max(r.score for r in semantic_results) or 1
            for result in semantic_results:
                doc_id = str(result.document.id)
                normalized_score = result.score / max_sem_score

                if doc_id in combined_scores:
                    combined_scores[doc_id]['semantic_score'] = normalized_score
                    # Préférer le snippet sémantique s'il existe
                    if result.snippet:
                        combined_scores[doc_id]['snippet'] = result.snippet
                else:
                    combined_scores[doc_id] = {
                        'document': result.document,
                        'fulltext_score': 0,
                        'semantic_score': normalized_score,
                        'snippet': result.snippet
                    }

        # Calculer le score final combiné
        results = []
        for doc_id, data in combined_scores.items():
            final_score = (
                data['fulltext_score'] * fulltext_weight +
                data['semantic_score'] * semantic_weight
            )

            # Déterminer le type de match
            if data['fulltext_score'] > 0 and data['semantic_score'] > 0:
                match_type = 'combined'
            elif data['semantic_score'] > 0:
                match_type = 'semantic'
            else:
                match_type = 'fulltext'

            results.append(SearchResult(
                document=data['document'],
                score=final_score,
                match_type=match_type,
                snippet=data['snippet']
            ))

        # Trier par score final
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    def _extract_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Extrait un snippet du texte autour des termes de recherche."""
        if not text:
            return ''

        text_lower = text.lower()
        query_lower = query.lower()

        # Chercher la position du terme de recherche
        pos = text_lower.find(query_lower)

        if pos == -1:
            # Si pas trouvé, chercher les mots individuels
            words = query_lower.split()
            for word in words:
                pos = text_lower.find(word)
                if pos != -1:
                    break

        if pos == -1:
            # Retourner le début du texte
            return text[:max_length] + ('...' if len(text) > max_length else '')

        # Extraire le snippet autour de la position trouvée
        start = max(0, pos - max_length // 2)
        end = min(len(text), pos + max_length // 2)

        snippet = text[start:end]

        # Ajouter des ellipses si nécessaire
        if start > 0:
            snippet = '...' + snippet
        if end < len(text):
            snippet = snippet + '...'

        return snippet

    def index_document(self, document) -> bool:
        """
        Indexe un document pour la recherche sémantique.

        Args:
            document: Instance Document avec ocr_text

        Returns:
            True si indexé avec succès
        """
        from documents.models import DocumentEmbedding

        text = document.ocr_text or document.description or document.nom_fichier
        if not text:
            logger.warning(f"Document {document.id} n'a pas de texte à indexer")
            return False

        # Générer l'embedding
        embedding = self.embedding_service.generate_embedding(text)
        if embedding is None:
            logger.error(f"Impossible de générer l'embedding pour document {document.id}")
            return False

        # Sauvegarder
        try:
            DocumentEmbedding.create_or_update(
                document=document,
                text=text,
                embedding=embedding,
                model_used=self._get_model_name()
            )
            logger.info(f"Document {document.id} indexé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur indexation document {document.id}: {e}")
            return False

    def index_document_with_chunks(self, document, chunk_size: int = 1000, overlap: int = 200) -> int:
        """
        Indexe un document en le découpant en chunks.
        Utile pour les documents longs.

        Args:
            document: Instance Document
            chunk_size: Taille des chunks en caractères
            overlap: Chevauchement entre chunks

        Returns:
            Nombre de chunks indexés
        """
        from documents.models import TextChunkEmbedding

        text = document.ocr_text or document.description
        if not text:
            return 0

        # Découper en chunks avec chevauchement
        chunks = self._split_text_into_chunks(text, chunk_size, overlap)

        # Générer les embeddings en batch
        embeddings = self.embedding_service.generate_embeddings_batch(
            [c['text'] for c in chunks]
        )

        # Supprimer les anciens chunks
        TextChunkEmbedding.objects.filter(document=document).delete()

        # Sauvegarder les nouveaux chunks
        indexed_count = 0
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if embedding is None:
                continue

            TextChunkEmbedding.objects.create(
                document=document,
                chunk_index=i,
                chunk_start=chunk['start'],
                chunk_end=chunk['end'],
                chunk_text=chunk['text'],
                embedding=embedding,
                model_used=self._get_model_name()
            )
            indexed_count += 1

        logger.info(f"Document {document.id} indexé en {indexed_count} chunks")
        return indexed_count

    def _split_text_into_chunks(self, text: str, chunk_size: int, overlap: int) -> List[Dict]:
        """Découpe un texte en chunks avec chevauchement."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Ajuster pour ne pas couper au milieu d'un mot
            if end < len(text):
                # Chercher le dernier espace
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space

            chunks.append({
                'text': text[start:end],
                'start': start,
                'end': end
            })

            # Avancer avec chevauchement
            start = end - overlap

        return chunks

    def _get_model_name(self) -> str:
        """Retourne le nom du modele d'embedding utilise."""
        return self.embedding_service.model_name

    def reindex_all_documents(self, mandat_id: Optional[str] = None, batch_size: int = 100):
        """
        Réindexe tous les documents.

        Args:
            mandat_id: Filtrer par mandat (optionnel)
            batch_size: Nombre de documents par batch

        Returns:
            Tuple (indexed_count, error_count)
        """
        from documents.models import Document

        qs = Document.objects.filter(is_active=True)
        if mandat_id:
            qs = qs.filter(mandat_id=mandat_id)

        # Filtrer les documents avec du texte
        qs = qs.exclude(Q(ocr_text='') | Q(ocr_text__isnull=True))

        indexed_count = 0
        error_count = 0

        for doc in qs.iterator(chunk_size=batch_size):
            if self.index_document(doc):
                indexed_count += 1
            else:
                error_count += 1

        logger.info(f"Réindexation terminée: {indexed_count} succès, {error_count} erreurs")
        return indexed_count, error_count


# Instance singleton
search_service = DocumentSearchService()
