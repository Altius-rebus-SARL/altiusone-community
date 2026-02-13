# graph/management/commands/populate_graph.py
"""
Peuple le graphe relationnel à partir des modèles Django existants.

Usage:
    python manage.py populate_graph
    python manage.py populate_graph --model core.Client
    python manage.py populate_graph --clear
    python manage.py populate_graph --dry-run
"""
from django.apps import apps
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

    def handle(self, *args, **options):
        from graph.models import Entite, Relation
        from graph.sync_config import MODEL_GRAPH_CONFIG
        from graph.services.sync import sync_instance, sync_relations, invalidate_type_cache

        model_filter = options['model']
        clear = options['clear']
        dry_run = options['dry_run']

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
                # Supprimer les relations liées aux entités systeme
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

        self.stdout.write(self.style.WARNING('Population du graphe...'))

        total_entites = 0
        total_relations = 0

        for model_key, config in configs.items():
            app_label, model_name = model_key.split('.')
            try:
                Model = apps.get_model(app_label, model_name)
            except LookupError:
                self.stderr.write(self.style.ERROR(f"  Modèle introuvable: {model_key}"))
                continue

            # Filtrer les instances actives (si le modèle a is_active)
            qs = Model.objects.all()
            if hasattr(Model, 'is_active'):
                qs = qs.filter(is_active=True)

            count = qs.count()
            self.stdout.write(f"\n  {model_key} ({count} instances)...")

            if dry_run:
                total_entites += count
                continue

            # Sync des entités (première passe)
            created = 0
            updated = 0
            for instance in qs.iterator():
                try:
                    entite = sync_instance(instance)
                    if entite:
                        if entite._state.adding:
                            created += 1
                        else:
                            updated += 1
                        total_entites += 1
                except Exception as e:
                    self.stderr.write(f"    Erreur {model_key} #{instance.pk}: {e}")

            self.stdout.write(f"    Entités: {created} créées, {updated} MAJ")

        # Deuxième passe : relations (après que toutes les entités existent)
        if not dry_run:
            self.stdout.write(self.style.WARNING('\nCréation des relations...'))
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

                rel_after = Relation.objects.count()
                rel_created = rel_after - rel_before
                if rel_created:
                    self.stdout.write(f"  {model_key}: {rel_created} relations")
                    total_relations += rel_created

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\n[DRY RUN] {total_entites} instances à synchroniser'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nPopulation terminée: {total_entites} entités, {total_relations} relations'
            ))
