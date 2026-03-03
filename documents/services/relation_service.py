# documents/services/relation_service.py
"""
Service de detection des relations inter-documents.

Utilise la similarite cosine et l'analyse IA pour decouvrir
les liens entre documents d'un mandat.
"""
import logging
from typing import List, Optional

from django.db.models import Q

logger = logging.getLogger(__name__)


class RelationService:
    """
    Detecte les relations semantiques entre documents.

    Utilise:
    - DocumentEmbedding.search_similar() pour la similarite cosine
    - ai_service.chat() pour l'analyse qualitative des relations
    """

    # Seuils de similarite
    THRESHOLD_RELATION = 0.7   # Seuil pour chercher des relations
    THRESHOLD_DOUBLON = 0.85   # Seuil pour detection de doublons
    MAX_SIMILAR = 10           # Nombre max de documents similaires a analyser

    def __init__(self):
        self._ai_service = None

    @property
    def ai_service(self):
        if self._ai_service is None:
            from documents.ai_service import ai_service
            self._ai_service = ai_service
        return self._ai_service

    def decouvrir_relations(self, document) -> list:
        """
        Detecte les relations d'un document avec les documents existants.

        1. Recherche les N documents les plus similaires via embedding
        2. Pour chaque paire a forte similarite, analyse IA la relation
        3. Cree les DocumentRelation correspondantes

        Args:
            document: Instance Document

        Returns:
            Liste des DocumentRelation creees
        """
        from documents.models import DocumentEmbedding
        from documents.models_intelligence import DocumentRelation

        relations_creees = []

        # Verifier que le document a un embedding
        try:
            embedding_obj = DocumentEmbedding.objects.get(document=document)
        except DocumentEmbedding.DoesNotExist:
            logger.warning(f"Document {document.id} n'a pas d'embedding, skip relations")
            return []

        if embedding_obj.embedding is None:
            return []

        # Rechercher les documents similaires dans le meme mandat
        similar = DocumentEmbedding.search_similar(
            query_embedding=embedding_obj.embedding,
            limit=self.MAX_SIMILAR + 1,
            threshold=self.THRESHOLD_RELATION,
            mandat_id=str(document.mandat_id)
        )

        for s in similar:
            if str(s.document_id) == str(document.id):
                continue

            similarity = 1 - s.distance

            # Verifier si la relation existe deja
            exists = DocumentRelation.objects.filter(
                Q(document_source=document, document_cible=s.document) |
                Q(document_source=s.document, document_cible=document)
            ).exists()
            if exists:
                continue

            # Determiner le type de relation via IA
            type_relation, description = self._classifier_relation(
                document, s.document, similarity
            )

            if type_relation:
                relation = DocumentRelation.objects.create(
                    document_source=document,
                    document_cible=s.document,
                    type_relation=type_relation,
                    score_similarite=round(similarity, 3),
                    description=description,
                    metadata={
                        'methode': 'cosine_similarity',
                        'auto_detected': True,
                    }
                )
                relations_creees.append(relation)

        logger.info(
            f"Document {document.id}: {len(relations_creees)} relations decouvertes"
        )
        return relations_creees

    def detecter_doublons_mandat(self, mandat_id: str) -> list:
        """
        Detecte les doublons potentiels dans un mandat.

        1. Recupere tous les embeddings du mandat
        2. Pour les paires > 0.85, cree des relations DOUBLON
        3. Genere un MandatInsight si des doublons trouves

        Args:
            mandat_id: UUID du mandat

        Returns:
            Liste des DocumentRelation de type DOUBLON creees
        """
        from documents.models import DocumentEmbedding
        from documents.models_intelligence import DocumentRelation, MandatInsight
        from core.models import Mandat

        mandat = Mandat.objects.get(id=mandat_id)
        embeddings = list(
            DocumentEmbedding.objects.filter(
                document__mandat_id=mandat_id,
                embedding__isnull=False
            ).select_related('document')
        )

        doublons = []
        checked = set()

        for i, emb_a in enumerate(embeddings):
            for emb_b in embeddings[i + 1:]:
                pair_key = tuple(sorted([str(emb_a.document_id), str(emb_b.document_id)]))
                if pair_key in checked:
                    continue
                checked.add(pair_key)

                similarity = self.ai_service.compute_similarity(
                    emb_a.embedding, emb_b.embedding
                )

                if similarity >= self.THRESHOLD_DOUBLON:
                    # Verifier si la relation existe deja
                    exists = DocumentRelation.objects.filter(
                        document_source=emb_a.document,
                        document_cible=emb_b.document,
                        type_relation='DOUBLON'
                    ).exists()
                    if exists:
                        continue

                    relation = DocumentRelation.objects.create(
                        document_source=emb_a.document,
                        document_cible=emb_b.document,
                        type_relation='DOUBLON',
                        score_similarite=round(similarity, 3),
                        description=(
                            f"Similarité très élevée ({similarity:.0%}) entre "
                            f"'{emb_a.document.nom_fichier}' et "
                            f"'{emb_b.document.nom_fichier}'"
                        ),
                        metadata={'methode': 'batch_cosine', 'auto_detected': True}
                    )
                    doublons.append(relation)

        # Creer un insight si des doublons trouves
        if doublons:
            docs_info = [
                f"- {r.document_source.nom_fichier} ↔ {r.document_cible.nom_fichier} ({r.score_similarite:.0%})"
                for r in doublons
            ]
            insight = MandatInsight.objects.create(
                mandat=mandat,
                type_insight='DOUBLON',
                severite='WARNING',
                titre=f"{len(doublons)} doublon(s) potentiel(s) détecté(s)",
                description=(
                    f"L'analyse a détecté {len(doublons)} paire(s) de documents "
                    f"très similaires dans le mandat {mandat.numero}:\n"
                    + "\n".join(docs_info)
                ),
                donnees={
                    'nb_doublons': len(doublons),
                    'paires': [
                        {
                            'source': str(r.document_source_id),
                            'cible': str(r.document_cible_id),
                            'score': float(r.score_similarite),
                        }
                        for r in doublons
                    ]
                }
            )
            # Lier les documents concernes
            doc_ids = set()
            for r in doublons:
                doc_ids.add(r.document_source_id)
                doc_ids.add(r.document_cible_id)
            from documents.models import Document
            insight.documents.set(Document.objects.filter(id__in=doc_ids))

        logger.info(f"Mandat {mandat_id}: {len(doublons)} doublons detectes")
        return doublons

    def analyser_contradiction(self, doc1, doc2) -> Optional['DocumentRelation']:
        """
        Analyse si deux documents contiennent des informations contradictoires.

        Args:
            doc1: Premier document
            doc2: Deuxieme document

        Returns:
            DocumentRelation de type CONTRADICTION si detectee, None sinon
        """
        from documents.models_intelligence import DocumentRelation

        if not self.ai_service.enabled:
            return None

        # Preparer les metadonnees
        meta1 = {
            'nom': doc1.nom_fichier,
            'type': doc1.prediction_type or 'inconnu',
            'metadata': doc1.metadata_extraite or {},
            'texte': (doc1.ocr_text or '')[:2000],
        }
        meta2 = {
            'nom': doc2.nom_fichier,
            'type': doc2.prediction_type or 'inconnu',
            'metadata': doc2.metadata_extraite or {},
            'texte': (doc2.ocr_text or '')[:2000],
        }

        prompt = f"""Analyse ces 2 documents et determine s'ils contiennent des informations contradictoires.

Document 1: {meta1['nom']} (type: {meta1['type']})
Métadonnées: {meta1['metadata']}
Extrait: {meta1['texte'][:1000]}

Document 2: {meta2['nom']} (type: {meta2['type']})
Métadonnées: {meta2['metadata']}
Extrait: {meta2['texte'][:1000]}

Reponds en JSON:
{{"contradiction": true/false, "explication": "description de la contradiction ou 'Aucune contradiction'"}}"""

        try:
            response = self.ai_service.chat(
                message=prompt,
                system="Tu es un expert en analyse documentaire. Detecte les contradictions entre documents.",
                temperature=0.2,
                max_tokens=500
            )

            import json
            response_text = response.get('response', '')
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
            else:
                return None

            if result.get('contradiction'):
                relation = DocumentRelation.objects.create(
                    document_source=doc1,
                    document_cible=doc2,
                    type_relation='CONTRADICTION',
                    score_similarite=0.5,
                    description=result.get('explication', 'Contradiction détectée par IA'),
                    metadata={'methode': 'ai_analysis', 'auto_detected': True}
                )
                return relation

        except Exception as e:
            logger.error(f"Erreur analyse contradiction: {e}")

        return None

    def _classifier_relation(self, doc1, doc2, similarity: float) -> tuple:
        """
        Classifie le type de relation entre deux documents via IA.

        Returns:
            Tuple (type_relation, description) ou (None, None)
        """
        # Si tres haute similarite, c'est probablement un doublon
        if similarity >= self.THRESHOLD_DOUBLON:
            return 'DOUBLON', (
                f"Similarité très élevée ({similarity:.0%}) suggérant un doublon"
            )

        if not self.ai_service.enabled:
            return 'REFERENCE', (
                f"Relation détectée par similarité cosine ({similarity:.0%})"
            )

        prompt = f"""Deux documents sont sémantiquement proches (similarité: {similarity:.0%}).
Determine le type de relation:

Document 1: {doc1.nom_fichier}
Type: {doc1.prediction_type or 'inconnu'}
Date: {doc1.date_document or 'inconnue'}
Extrait: {(doc1.ocr_text or '')[:500]}

Document 2: {doc2.nom_fichier}
Type: {doc2.prediction_type or 'inconnu'}
Date: {doc2.date_document or 'inconnue'}
Extrait: {(doc2.ocr_text or '')[:500]}

Types possibles: VERSION (versions successives), REFERENCE (reference croisee), COMPLEMENT (complementaire), REPONSE (reponse a)

Reponds en JSON: {{"type": "TYPE", "description": "breve explication"}}"""

        try:
            response = self.ai_service.chat(
                message=prompt,
                system="Tu es un expert en analyse documentaire.",
                temperature=0.2,
                max_tokens=300
            )

            import json
            response_text = response.get('response', '')
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
                type_rel = result.get('type', 'REFERENCE')
                valid_types = ['VERSION', 'REFERENCE', 'COMPLEMENT', 'REPONSE']
                if type_rel not in valid_types:
                    type_rel = 'REFERENCE'
                return type_rel, result.get('description', '')
        except Exception as e:
            logger.error(f"Erreur classification relation: {e}")

        return 'REFERENCE', f"Similarité cosine: {similarity:.0%}"
