# graph/management/commands/populate_graph.py
"""
Peuple le graphe relationnel à partir des modèles Django existants.

Usage:
    python manage.py populate_graph
    python manage.py populate_graph --model core.Client
    python manage.py populate_graph --clear
    python manage.py populate_graph --dry-run
    python manage.py populate_graph --full  (force re-sync de tout)
"""
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Peuple le graphe relationnel depuis les modèles Django mappés'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default=None,
            help='Ne traiter qu\'un modèle spécifique (ex: core.Client)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprime toutes les entités source=systeme avant la population',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Compte les instances sans créer d\'entités',
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Force le re-sync de toutes les instances (même celles déjà dans le graphe)',
        )

    def handle(self, *args, **options):
        from graph.models import Entite, Relation
        from graph.sync_config import MODEL_GRAPH_CONFIG
        from graph.services.sync import sync_instance, sync_relations, invalidate_type_cache

        model_filter = options['model']
        clear = options['clear']
        dry_run = options['dry_run']
        full = options['full']

        # Filtrer les modèles à traiter
        if model_filter:
            if model_filter not in MODEL_GRAPH_CONFIG:
                self.stderr.write(self.style.ERROR(
                    f"Modèle '{model_filter}' non trouvé dans MODEL_GRAPH_CONFIG.\n"
                    f"Modèles disponibles: {', '.join(MODEL_GRAPH_CONFIG.keys())}"
                ))
                return
            configs = {model_filter: MODEL_GRAPH_CONFIG[model_filter]}
        else:
            configs = MODEL_GRAPH_CONFIG

        # Clear si demandé
        if clear and not dry_run:
            self.stdout.write(self.style.WARNING('Suppression des entités systeme...'))
            with transaction.atomic():
                systeme_entites = Entite.objects.filter(source='systeme')
                rel_count = Relation.objects.filter(
                    source__in=systeme_entites
                ).delete()[0]
                rel_count += Relation.objects.filter(
                    cible__in=systeme_entites
                ).delete()[0]
                ent_count = systeme_entites.delete()[0]
                self.stdout.write(f'  Supprimé: {ent_count} entités, {rel_count} relations')
            invalidate_type_cache()

        # Collecter les object_id déjà dans le graphe pour skip rapide
        existing_ids = set()
        if not full and not clear:
            existing_ids = set(
                Entite.objects.filter(source='systeme')
                .values_list('object_id', flat=True)
            )
            if existing_ids:
                self.stdout.write(
                    f'  {len(existing_ids)} entités systeme déjà dans le graphe'
                )

        self.stdout.write(self.style.WARNING('Population du graphe...'))

        total_created = 0
        total_skipped = 0

        for model_key, config in configs.items():
            app_label, model_name = model_key.split('.')
            try:
                Model = apps.get_model(app_label, model_name)
            except LookupError:
                self.stderr.write(self.style.ERROR(f"  Modèle introuvable: {model_key}"))
                continue

            qs = Model.objects.all()
            if hasattr(Model, 'is_active'):
                qs = qs.filter(is_active=True)

            # Exclure les instances déjà synchronisées
            if existing_ids and not full:
                qs = qs.exclude(pk__in=existing_ids)

            count = qs.count()
            if count == 0:
                self.stdout.write(f"  {model_key}: rien à synchroniser")
                continue

            self.stdout.write(f"\n  {model_key} ({count} nouvelles instances)...")

            if dry_run:
                total_created += count
                continue

            created = 0
            for instance in qs.iterator():
                try:
                    entite = sync_instance(instance)
                    if entite:
                        created += 1
                except Exception as e:
                    self.stderr.write(f"    Erreur {model_key} #{instance.pk}: {e}")

            total_created += created
            self.stdout.write(f"    {created} entités créées")

        # Deuxième passe : relations
        if not dry_run and total_created > 0:
            self.stdout.write(self.style.WARNING('\nCréation des relations...'))
            rel_total = 0
            for model_key, config in configs.items():
                app_label, model_name = model_key.split('.')
                try:
                    Model = apps.get_model(app_label, model_name)
                except LookupError:
                    continue

                qs = Model.objects.all()
                if hasattr(Model, 'is_active'):
                    qs = qs.filter(is_active=True)

                rel_before = Relation.objects.count()
                for instance in qs.iterator():
                    try:
                        sync_relations(instance)
                    except Exception as e:
                        self.stderr.write(f"    Erreur relation {model_key} #{instance.pk}: {e}")

                rel_created = Relation.objects.count() - rel_before
                if rel_created:
                    self.stdout.write(f"  {model_key}: {rel_created} relations")
                    rel_total += rel_created

            self.stdout.write(self.style.SUCCESS(
                f'\nPopulation terminée: {total_created} entités, {rel_total} relations'
            ))
        elif dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\n[DRY RUN] {total_created} instances à synchroniser'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\nGraphe déjà à jour.'))
