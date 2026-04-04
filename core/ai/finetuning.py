# core/ai/finetuning.py
"""
Service de fine-tuning évolutif des embeddings.

Utilise les feedbacks utilisateur (👍/👎) pour améliorer la pertinence
des embeddings via contrastive learning (sentence-transformers).

Architecture:
1. Collecte: feedbacks Message.feedback → paires (query, document)
2. Training: fine-tune le modèle d'embedding avec les paires positives/négatives
3. Re-embedding: régénère tous les embeddings en batch (Celery task nocturne)
4. Versioning: sauvegarde le modèle fine-tuné avec un numéro de version

Données nécessaires:
- Paires positives: (requête utilisateur, document/entité que l'IA a correctement trouvé)
- Paires négatives (hard negatives): (requête, document mal classé ou feedback négatif)
- Minimum ~50 paires pour commencer, idéalement 200-500 pour un gain significatif

Compatible CPU (pas besoin de GPU, ~10min pour 500 paires sur 8 vCPUs).
"""
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

# Répertoire pour les modèles fine-tunés
FINETUNED_DIR = os.path.join(
    getattr(settings, 'BASE_DIR', '/app'),
    'data', 'models', 'embeddings'
)


class TrainingPair:
    """Paire d'entraînement pour contrastive learning."""

    def __init__(self, anchor: str, positive: str, negative: str = '', score: float = 1.0):
        self.anchor = anchor      # Requête utilisateur
        self.positive = positive  # Texte du résultat pertinent
        self.negative = negative  # Texte d'un résultat non pertinent (optionnel)
        self.score = score        # Score de similarité cible (0-1)


class EmbeddingFineTuner:
    """
    Fine-tuning évolutif du modèle d'embedding.

    Collecte les feedbacks, génère des paires d'entraînement,
    et fine-tune le modèle sentence-transformers.
    """

    MIN_PAIRS_FOR_TRAINING = 30  # Minimum de paires pour lancer un fine-tuning
    DEFAULT_EPOCHS = 3
    DEFAULT_BATCH_SIZE = 16
    DEFAULT_WARMUP_RATIO = 0.1

    def collect_training_pairs(self) -> List[TrainingPair]:
        """
        Collecte les paires d'entraînement depuis les feedbacks utilisateur.

        Sources:
        1. Messages avec feedback POSITIF → paires positives (query → sources)
        2. Messages avec feedback NEGATIF → hard negatives
        3. Clics de recherche (si trackés) → paires positives implicites

        Returns:
            Liste de TrainingPair prêtes pour l'entraînement
        """
        from documents.models import Message

        pairs = []

        # 1. Feedbacks positifs → paires (requête → sources pertinentes)
        positive_messages = Message.objects.filter(
            role='ASSISTANT',
            feedback='POSITIF',
            sources__isnull=False,
        ).select_related('conversation').order_by('-created_at')[:500]

        for msg in positive_messages:
            # Trouver le message utilisateur précédent
            user_msg = Message.objects.filter(
                conversation=msg.conversation,
                role='USER',
                created_at__lt=msg.created_at,
            ).order_by('-created_at').first()

            if not user_msg or not user_msg.contenu:
                continue

            query = user_msg.contenu.strip()
            if len(query) < 5:
                continue

            # Extraire les textes des sources
            sources = msg.sources or []
            for source in sources:
                title = source.get('title', '')
                subtitle = source.get('subtitle', '')
                snippet = source.get('snippet', '')

                positive_text = f"{title} {subtitle} {snippet}".strip()
                if positive_text and len(positive_text) > 10:
                    pairs.append(TrainingPair(
                        anchor=query,
                        positive=positive_text,
                        score=1.0,
                    ))

        # 2. Feedbacks négatifs → hard negatives
        negative_messages = Message.objects.filter(
            role='ASSISTANT',
            feedback='NEGATIF',
            sources__isnull=False,
        ).select_related('conversation').order_by('-created_at')[:200]

        for msg in negative_messages:
            user_msg = Message.objects.filter(
                conversation=msg.conversation,
                role='USER',
                created_at__lt=msg.created_at,
            ).order_by('-created_at').first()

            if not user_msg or not user_msg.contenu:
                continue

            query = user_msg.contenu.strip()
            sources = msg.sources or []

            for source in sources:
                title = source.get('title', '')
                subtitle = source.get('subtitle', '')

                negative_text = f"{title} {subtitle}".strip()
                if negative_text and len(negative_text) > 10:
                    # Chercher un exemple positif pour la même requête
                    # (créer une paire anchor/positive/negative)
                    for existing in pairs:
                        if existing.anchor == query and not existing.negative:
                            existing.negative = negative_text
                            break

        logger.info(
            f"Paires collectées: {len(pairs)} "
            f"(avec negatives: {sum(1 for p in pairs if p.negative)})"
        )
        return pairs

    def train(
        self,
        pairs: Optional[List[TrainingPair]] = None,
        epochs: int = DEFAULT_EPOCHS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        output_dir: Optional[str] = None,
    ) -> Dict:
        """
        Fine-tune le modèle d'embedding avec les paires collectées.

        Utilise MultipleNegativesRankingLoss (contrastive learning) qui
        apprend à rapprocher les paires positives et éloigner les négatives.

        Args:
            pairs: Paires d'entraînement (si None, collecte automatiquement)
            epochs: Nombre d'époques
            batch_size: Taille des batches
            output_dir: Répertoire de sortie (défaut: FINETUNED_DIR/vN)

        Returns:
            Dict avec les métriques d'entraînement
        """
        if pairs is None:
            pairs = self.collect_training_pairs()

        if len(pairs) < self.MIN_PAIRS_FOR_TRAINING:
            return {
                'status': 'skipped',
                'reason': f'Pas assez de paires ({len(pairs)}/{self.MIN_PAIRS_FOR_TRAINING})',
                'pairs_count': len(pairs),
            }

        from sentence_transformers import SentenceTransformer, InputExample, losses
        from torch.utils.data import DataLoader

        # Déterminer la version et le répertoire de sortie
        version = self._get_next_version()
        if output_dir is None:
            output_dir = os.path.join(FINETUNED_DIR, f'v{version}')

        os.makedirs(output_dir, exist_ok=True)

        logger.info(
            f"Fine-tuning v{version}: {len(pairs)} paires, "
            f"{epochs} époques, batch_size={batch_size}"
        )
        start = time.time()

        # Charger le modèle de base
        base_model_name = getattr(
            settings, 'EMBEDDING_MODEL',
            'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
        )

        # Utiliser le dernier modèle fine-tuné comme base si disponible
        latest_dir = self._get_latest_model_dir()
        if latest_dir and os.path.isdir(latest_dir):
            logger.info(f"Base: modèle fine-tuné précédent ({latest_dir})")
            model = SentenceTransformer(latest_dir)
        else:
            logger.info(f"Base: modèle original ({base_model_name})")
            model = SentenceTransformer(base_model_name)

        # Convertir en InputExamples
        train_examples = []
        for pair in pairs:
            if pair.negative:
                # Triplet: anchor, positive, negative
                train_examples.append(InputExample(
                    texts=[pair.anchor, pair.positive, pair.negative]
                ))
            else:
                # Paire: anchor, positive
                train_examples.append(InputExample(
                    texts=[pair.anchor, pair.positive],
                    label=pair.score,
                ))

        train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)

        # Loss: MultipleNegativesRankingLoss (contrastive)
        # Efficace même avec peu de paires, utilise les in-batch negatives
        train_loss = losses.MultipleNegativesRankingLoss(model)

        # Warmup
        warmup_steps = int(len(train_dataloader) * epochs * self.DEFAULT_WARMUP_RATIO)

        # Entraîner
        model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=warmup_steps,
            output_path=output_dir,
            show_progress_bar=True,
        )

        elapsed = time.time() - start

        # Sauvegarder les métadonnées
        metadata = {
            'version': version,
            'base_model': base_model_name,
            'pairs_count': len(pairs),
            'pairs_with_negatives': sum(1 for p in pairs if p.negative),
            'epochs': epochs,
            'batch_size': batch_size,
            'training_time_seconds': round(elapsed, 1),
            'trained_at': datetime.now().isoformat(),
        }
        metadata_path = os.path.join(output_dir, 'training_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            f"Fine-tuning v{version} terminé en {elapsed:.0f}s — "
            f"{len(pairs)} paires, sauvegardé dans {output_dir}"
        )

        return {
            'status': 'success',
            'version': version,
            'output_dir': output_dir,
            **metadata,
        }

    def apply_finetuned_model(self) -> bool:
        """
        Active le dernier modèle fine-tuné comme modèle d'embedding par défaut.

        Met à jour le singleton embedding_service pour utiliser le nouveau modèle.

        Returns:
            True si le modèle a été activé, False sinon
        """
        latest_dir = self._get_latest_model_dir()
        if not latest_dir or not os.path.isdir(latest_dir):
            logger.info("Aucun modèle fine-tuné disponible")
            return False

        from core.ai.embeddings import embedding_service

        try:
            from sentence_transformers import SentenceTransformer
            new_model = SentenceTransformer(latest_dir)

            # Remplacer le modèle en mémoire
            embedding_service._model = new_model
            embedding_service._model_name = latest_dir

            logger.info(f"Modèle fine-tuné activé: {latest_dir}")
            return True
        except Exception as e:
            logger.error(f"Erreur activation modèle fine-tuné: {e}")
            return False

    def reembed_all(self, batch_size: int = 100) -> Dict:
        """
        Régénère tous les embeddings avec le modèle actuel.

        À appeler après apply_finetuned_model() pour mettre à jour
        tous les vecteurs pgvector avec le nouveau modèle.

        Returns:
            Dict avec les statistiques de re-embedding
        """
        from core.models import ModelEmbedding
        from core.ai.embeddings import embedding_service

        total = ModelEmbedding.objects.count()
        updated = 0
        errors = 0

        logger.info(f"Re-embedding de {total} vecteurs...")
        start = time.time()

        # Traiter par batch
        offset = 0
        while offset < total:
            batch = list(
                ModelEmbedding.objects.order_by('id')[offset:offset + batch_size]
            )
            if not batch:
                break

            texts = [me.text_preview or '' for me in batch]
            embeddings = embedding_service.generate_embeddings_batch(texts)

            for me, emb in zip(batch, embeddings):
                if emb is not None:
                    me.embedding = emb
                    try:
                        me.save(update_fields=['embedding'])
                        updated += 1
                    except Exception as e:
                        logger.error(f"Erreur re-embedding {me.id}: {e}")
                        errors += 1
                else:
                    errors += 1

            offset += batch_size
            if offset % 500 == 0:
                logger.info(f"Re-embedding: {offset}/{total}")

        elapsed = time.time() - start
        stats = {
            'total': total,
            'updated': updated,
            'errors': errors,
            'duration_seconds': round(elapsed, 1),
        }
        logger.info(f"Re-embedding terminé: {stats}")
        return stats

    def get_training_stats(self) -> Dict:
        """Retourne les statistiques de feedback et training disponibles."""
        from documents.models import Message

        positive_count = Message.objects.filter(
            role='ASSISTANT', feedback='POSITIF'
        ).count()
        negative_count = Message.objects.filter(
            role='ASSISTANT', feedback='NEGATIF'
        ).count()

        latest_version = self._get_current_version()
        latest_dir = self._get_latest_model_dir()
        metadata = {}
        if latest_dir:
            meta_path = os.path.join(latest_dir, 'training_metadata.json')
            if os.path.isfile(meta_path):
                with open(meta_path) as f:
                    metadata = json.load(f)

        return {
            'feedbacks_positifs': positive_count,
            'feedbacks_negatifs': negative_count,
            'total_feedbacks': positive_count + negative_count,
            'paires_estimees': positive_count * 2,  # ~2 sources par réponse
            'ready_for_training': positive_count >= self.MIN_PAIRS_FOR_TRAINING,
            'current_version': f'v{latest_version}',
            'current_model_dir': latest_dir,
            'last_training': metadata,
        }

    def _get_current_version(self) -> str:
        """Retourne la version actuelle du modèle fine-tuné (semver)."""
        if not os.path.isdir(FINETUNED_DIR):
            return '0.0.0'
        versions = []
        for d in os.listdir(FINETUNED_DIR):
            if d.startswith('v'):
                parts = d[1:].split('.')
                if len(parts) == 3 and all(p.isdigit() for p in parts):
                    versions.append(tuple(int(p) for p in parts))
        if not versions:
            return '0.0.0'
        latest = max(versions)
        return f'{latest[0]}.{latest[1]}.{latest[2]}'

    def _get_next_version(self) -> str:
        """Incrémente le patch: 0.0.1 → 0.0.2, etc."""
        current = self._get_current_version()
        major, minor, patch = (int(p) for p in current.split('.'))
        return f'{major}.{minor}.{patch + 1}'

    def _get_latest_model_dir(self) -> Optional[str]:
        """Retourne le chemin du dernier modèle fine-tuné."""
        version = self._get_current_version()
        if version == '0.0.0':
            return None
        path = os.path.join(FINETUNED_DIR, f'v{version}')
        return path if os.path.isdir(path) else None


# Singleton
finetuner = EmbeddingFineTuner()
