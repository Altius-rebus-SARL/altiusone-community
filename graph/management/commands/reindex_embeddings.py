# graph/management/commands/reindex_embeddings.py
"""
Réindexe les embeddings de toutes les entités du graphe.

Usage:
    python manage.py reindex_embeddings
    python manage.py reindex_embeddings --batch-size 50
    python manage.py reindex_embeddings --type Personne
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Réindexe les embeddings vectoriels de toutes les entités du graphe'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Nombre d\'entités par batch (défaut: 100)',
        )
        parser.add_argument(
            '--type',
            type=str,
            default=None,
            help='Filtrer par nom de type d\'ontologie',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Réindexer même les entités ayant déjà un embedding',
        )

    def handle(self, *args, **options):
        from graph.models import Entite
        from graph.services.embedding import mettre_a_jour_embedding

        batch_size = options['batch_size']
        type_name = options['type']
        force = options['force']

        queryset = Entite.objects.filter(is_active=True)

        if type_name:
            queryset = queryset.filter(type__nom=type_name)

        if not force:
            queryset = queryset.filter(embedding__isnull=True)

        total = queryset.count()
        self.stdout.write(self.style.WARNING(
            f'Réindexation: {total} entités à traiter (batch={batch_size})'
        ))

        updated = 0
        errors = 0
        pks = queryset.values_list('pk', flat=True)

        for i, pk in enumerate(pks.iterator(chunk_size=batch_size)):
            try:
                if mettre_a_jour_embedding(pk):
                    updated += 1
            except Exception as e:
                self.stderr.write(f'Erreur entité {pk}: {e}')
                errors += 1

            if (i + 1) % batch_size == 0:
                self.stdout.write(f'  ... {i + 1}/{total} traités')

        self.stdout.write(self.style.SUCCESS(
            f'Réindexation terminée: {updated}/{total} mis à jour, {errors} erreurs'
        ))
