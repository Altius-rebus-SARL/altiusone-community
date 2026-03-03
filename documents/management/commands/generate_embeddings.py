# documents/management/commands/generate_embeddings.py
"""
Commande pour generer les embeddings des documents.

Usage:
    python manage.py generate_embeddings
    python manage.py generate_embeddings --mandat MAN-2025-001
    python manage.py generate_embeddings --batch-size 50
    python manage.py generate_embeddings --force  # Regenerer tous les embeddings
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
import time


class Command(BaseCommand):
    help = "Genere les embeddings pour les documents (necessaire pour la recherche semantique et le chat IA)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--mandat',
            type=str,
            help='Numero du mandat a traiter (ex: MAN-2025-001)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=20,
            help='Nombre de documents a traiter par batch (default: 20)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerer les embeddings meme si ils existent deja',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Afficher les documents sans generer les embeddings',
        )

    def handle(self, *args, **options):
        from documents.models import Document, DocumentEmbedding
        from documents.ai_service import ai_service
        from documents.embeddings import embedding_service

        mandat_numero = options['mandat']
        batch_size = options['batch_size']
        force = options['force']
        dry_run = options['dry_run']

        # Verifier que le service AI est configure
        if not ai_service.enabled:
            raise CommandError(
                "Le service AI n'est pas configure. "
                "Verifiez AI_API_KEY et AI_API_URL dans votre .env"
            )

        self.stdout.write(self.style.NOTICE("Verification du service AI..."))
        health = ai_service.health_check()
        if not health.get('connected'):
            raise CommandError(f"Service AI non disponible: {health.get('error')}")

        self.stdout.write(self.style.SUCCESS(f"Service AI connecte (version: {health.get('api_version', 'unknown')})"))

        # Construire la requete
        qs = Document.objects.filter(
            is_active=True
        ).exclude(
            Q(ocr_text='') | Q(ocr_text__isnull=True)
        ).select_related('mandat')

        if mandat_numero:
            qs = qs.filter(mandat__numero=mandat_numero)
            self.stdout.write(f"Filtrage par mandat: {mandat_numero}")

        # Exclure les documents qui ont deja des embeddings (sauf si --force)
        if not force:
            existing_ids = DocumentEmbedding.objects.values_list('document_id', flat=True)
            qs = qs.exclude(id__in=existing_ids)

        total_docs = qs.count()

        if total_docs == 0:
            self.stdout.write(self.style.WARNING("Aucun document a traiter."))
            if not force:
                existing = DocumentEmbedding.objects.count()
                self.stdout.write(f"({existing} embeddings existent deja. Utilisez --force pour regenerer)")
            return

        self.stdout.write(f"\nDocuments a traiter: {total_docs}")

        if dry_run:
            self.stdout.write(self.style.NOTICE("\n[DRY RUN] Documents qui seraient traites:"))
            for doc in qs[:20]:
                mandat_info = doc.mandat.numero if doc.mandat else "Sans mandat"
                text_len = len(doc.ocr_text) if doc.ocr_text else 0
                self.stdout.write(f"  - {doc.nom_fichier} [{mandat_info}] ({text_len} chars)")
            if total_docs > 20:
                self.stdout.write(f"  ... et {total_docs - 20} autres")
            return

        # Traiter par batch
        success_count = 0
        error_count = 0
        start_time = time.time()

        self.stdout.write(f"\nGeneration des embeddings (batch size: {batch_size})...\n")

        for i, doc in enumerate(qs.iterator(chunk_size=batch_size), 1):
            try:
                text = doc.ocr_text[:30000]  # Limite API

                # Generer l'embedding
                embedding = embedding_service.generate_embedding(text)

                if embedding is None:
                    self.stdout.write(self.style.WARNING(f"  [{i}/{total_docs}] {doc.nom_fichier}: Pas d'embedding genere"))
                    error_count += 1
                    continue

                # Sauvegarder
                DocumentEmbedding.create_or_update(
                    document=doc,
                    text=text,
                    embedding=embedding,
                    model_used='altiusone-768'
                )

                success_count += 1

                # Afficher la progression
                if i % 10 == 0 or i == total_docs:
                    elapsed = time.time() - start_time
                    rate = i / elapsed if elapsed > 0 else 0
                    eta = (total_docs - i) / rate if rate > 0 else 0
                    self.stdout.write(
                        f"  [{i}/{total_docs}] {success_count} succes, {error_count} erreurs "
                        f"({rate:.1f} docs/s, ETA: {eta:.0f}s)"
                    )

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"  [{i}/{total_docs}] {doc.nom_fichier}: {str(e)}"))

        # Resume
        elapsed = time.time() - start_time
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Generation terminee en {elapsed:.1f}s"))
        self.stdout.write(f"  Succes: {success_count}")
        self.stdout.write(f"  Erreurs: {error_count}")
        self.stdout.write(f"  Total embeddings: {DocumentEmbedding.objects.count()}")
