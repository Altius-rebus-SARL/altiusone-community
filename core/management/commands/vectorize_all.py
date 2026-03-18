# core/management/commands/vectorize_all.py
"""
Management command pour vectoriser tous les modèles en batch.

Usage:
    python manage.py vectorize_all                     # Tout vectoriser (tier 1-3)
    python manage.py vectorize_all --tier 1            # Tier 1 seulement (Client, Mandat, Facture, Employe)
    python manage.py vectorize_all --model core.Client # Un seul modèle
    python manage.py vectorize_all --dry-run           # Afficher les compteurs sans rien faire
    python manage.py vectorize_all --force             # Re-vectoriser même si inchangé
    python manage.py vectorize_all --batch-size 100    # Taille de batch
"""
import hashlib
import logging
import time

from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Vectorise tous les modèles configurés dans ModelEmbedding (pgvector 768D)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tier', type=int, default=3,
            help='Tier maximum à vectoriser (1=critique, 2=important, 3=tout). Défaut: 3'
        )
        parser.add_argument(
            '--model', type=str, default=None,
            help='Vectoriser un seul modèle (ex: core.Client)'
        )
        parser.add_argument(
            '--batch-size', type=int, default=50,
            help='Taille des batches d\'embedding. Défaut: 50'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Afficher les compteurs sans vectoriser'
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Re-vectoriser même si le texte n\'a pas changé'
        )

    def handle(self, *args, **options):
        from core.ai.embeddings import embedding_service
        from core.models import ModelEmbedding
        from core.embedding_config import MODEL_EMBEDDING_CONFIG, get_models_for_tier, get_model_class

        tier = options['tier']
        target_model = options['model']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        force = options['force']

        # Vérifier que le service d'embedding fonctionne
        if not dry_run:
            self.stdout.write("Vérification du service d'embedding...")
            if not embedding_service.is_available():
                self.stderr.write(self.style.ERROR("Service d'embedding non disponible"))
                return

            test = embedding_service.generate_embedding("test")
            if test is None or len(test) != 768:
                self.stderr.write(self.style.ERROR("Embedding test échoué"))
                return
            self.stdout.write(self.style.SUCCESS(f"OK — modèle: {embedding_service.model_name} ({len(test)}D)"))

        # Déterminer les modèles à traiter
        if target_model:
            if target_model not in MODEL_EMBEDDING_CONFIG:
                self.stderr.write(self.style.ERROR(
                    f"Modèle '{target_model}' non trouvé dans MODEL_EMBEDDING_CONFIG.\n"
                    f"Modèles disponibles: {', '.join(MODEL_EMBEDDING_CONFIG.keys())}"
                ))
                return
            configs = {target_model: MODEL_EMBEDDING_CONFIG[target_model]}
        else:
            configs = get_models_for_tier(tier)

        self.stdout.write(f"\nModèles à vectoriser (tier <= {tier}): {len(configs)}")
        self.stdout.write("-" * 60)

        total_indexed = 0
        total_skipped = 0
        total_errors = 0
        start_time = time.time()

        for app_model, cfg in configs.items():
            try:
                model_class = get_model_class(app_model)
                ct = ContentType.objects.get_for_model(model_class)

                # Compter les objets
                qs = model_class.objects.all()
                # Filtrer par is_active si le champ existe
                if hasattr(model_class, 'is_active'):
                    qs = qs.filter(is_active=True)
                elif hasattr(model_class, 'actif'):
                    qs = qs.filter(actif=True)

                extra_filter = cfg.get('filter')
                if extra_filter:
                    qs = qs.filter(**extra_filter)

                count = qs.count()

                # Compter les déjà indexés
                indexed_count = ModelEmbedding.objects.filter(content_type=ct).count()

                tier_label = f"T{cfg.get('tier', '?')}"
                self.stdout.write(
                    f"  [{tier_label}] {app_model}: "
                    f"{count} objets, {indexed_count} déjà indexés"
                )

                if dry_run:
                    total_indexed += count - indexed_count
                    continue

                # Vectoriser par batch
                batch_texts = []
                batch_objects = []

                for obj in qs.iterator(chunk_size=batch_size):
                    if not hasattr(obj, 'texte_pour_embedding'):
                        total_skipped += 1
                        continue

                    text = obj.texte_pour_embedding()
                    if not text or not text.strip():
                        total_skipped += 1
                        continue

                    text_hash = hashlib.sha256(text.encode()).hexdigest()

                    # Vérifier si déjà indexé avec même hash (skip si pas --force)
                    if not force:
                        existing = ModelEmbedding.objects.filter(
                            content_type=ct, object_id=obj.pk
                        ).values_list('text_hash', flat=True).first()

                        if existing == text_hash:
                            total_skipped += 1
                            continue

                    batch_texts.append(text)
                    batch_objects.append((obj, text_hash))

                    if len(batch_texts) >= batch_size:
                        indexed, errors = self._process_batch(
                            embedding_service, batch_texts, batch_objects, ct
                        )
                        total_indexed += indexed
                        total_errors += errors
                        batch_texts = []
                        batch_objects = []

                # Dernier batch
                if batch_texts:
                    indexed, errors = self._process_batch(
                        embedding_service, batch_texts, batch_objects, ct
                    )
                    total_indexed += indexed
                    total_errors += errors

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Erreur {app_model}: {e}"))
                total_errors += 1

        elapsed = time.time() - start_time
        self.stdout.write("-" * 60)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN — {total_indexed} objets à vectoriser"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Terminé en {elapsed:.1f}s — "
                f"{total_indexed} indexés, {total_skipped} inchangés, {total_errors} erreurs"
            ))

    def _process_batch(self, embedding_service, texts, objects, ct):
        """Traite un batch de textes."""
        from core.models import ModelEmbedding

        embeddings = embedding_service.generate_embeddings_batch(texts)
        indexed = 0
        errors = 0

        for (obj, text_hash), embedding in zip(objects, embeddings):
            if embedding is None:
                errors += 1
                continue

            try:
                ModelEmbedding.objects.update_or_create(
                    content_type=ct,
                    object_id=obj.pk,
                    defaults={
                        'embedding': embedding,
                        'text_hash': text_hash,
                        'text_preview': texts[indexed][:200] if indexed < len(texts) else '',
                        'model_used': embedding_service.model_name,
                    }
                )
                indexed += 1
            except Exception as e:
                logger.error(f"Erreur save embedding {obj.pk}: {e}")
                errors += 1

        return indexed, errors
