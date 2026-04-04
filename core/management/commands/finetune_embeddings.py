"""
Commande de management pour le fine-tuning évolutif des embeddings.

Usage:
  python manage.py finetune_embeddings              # Collecte + train + apply + re-embed
  python manage.py finetune_embeddings --stats       # Affiche les stats de feedback
  python manage.py finetune_embeddings --train-only  # Train sans re-embedding
  python manage.py finetune_embeddings --reembed     # Re-embed avec le modèle actuel
  python manage.py finetune_embeddings --epochs 5    # Nombre d'époques personnalisé
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Fine-tune le modèle d\'embedding à partir des feedbacks utilisateur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--stats', action='store_true',
            help='Afficher les statistiques de feedback sans entraîner'
        )
        parser.add_argument(
            '--train-only', action='store_true',
            help='Entraîner sans re-embedder'
        )
        parser.add_argument(
            '--reembed', action='store_true',
            help='Re-embedder avec le modèle actuel (sans entraîner)'
        )
        parser.add_argument(
            '--epochs', type=int, default=3,
            help='Nombre d\'époques (défaut: 3)'
        )
        parser.add_argument(
            '--batch-size', type=int, default=16,
            help='Taille de batch (défaut: 16)'
        )

    def handle(self, *args, **options):
        from core.ai.finetuning import finetuner

        if options['stats']:
            stats = finetuner.get_training_stats()
            self.stdout.write(self.style.SUCCESS('\n=== Statistiques Fine-tuning ==='))
            self.stdout.write(f"Feedbacks positifs: {stats['feedbacks_positifs']}")
            self.stdout.write(f"Feedbacks négatifs: {stats['feedbacks_negatifs']}")
            self.stdout.write(f"Paires estimées:    {stats['paires_estimees']}")
            self.stdout.write(f"Prêt pour training: {'Oui' if stats['ready_for_training'] else 'Non'}")
            self.stdout.write(f"Version actuelle:   {stats['current_version']}")
            if stats['last_training']:
                lt = stats['last_training']
                self.stdout.write(f"Dernier training:   {lt.get('trained_at', 'N/A')}")
                self.stdout.write(f"  Paires utilisées: {lt.get('pairs_count', 0)}")
                self.stdout.write(f"  Durée:            {lt.get('training_time_seconds', 0)}s")
            return

        if options['reembed']:
            self.stdout.write('Activation du modèle fine-tuné...')
            if finetuner.apply_finetuned_model():
                self.stdout.write('Re-embedding de tous les vecteurs...')
                stats = finetuner.reembed_all()
                self.stdout.write(self.style.SUCCESS(
                    f"Re-embedding terminé: {stats['updated']}/{stats['total']} "
                    f"({stats['errors']} erreurs) en {stats['duration_seconds']}s"
                ))
            else:
                self.stdout.write(self.style.WARNING('Aucun modèle fine-tuné disponible'))
            return

        # Mode complet: collecte → train → apply → re-embed
        self.stdout.write('Collecte des paires d\'entraînement...')
        pairs = finetuner.collect_training_pairs()
        self.stdout.write(f"  {len(pairs)} paires collectées")

        self.stdout.write('Entraînement...')
        result = finetuner.train(
            pairs=pairs,
            epochs=options['epochs'],
            batch_size=options['batch_size'],
        )

        if result['status'] == 'skipped':
            self.stdout.write(self.style.WARNING(f"Entraînement ignoré: {result['reason']}"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Fine-tuning v{result['version']} terminé en {result['training_time_seconds']}s"
        ))

        if not options['train_only']:
            self.stdout.write('Activation du nouveau modèle...')
            finetuner.apply_finetuned_model()

            self.stdout.write('Re-embedding de tous les vecteurs...')
            stats = finetuner.reembed_all()
            self.stdout.write(self.style.SUCCESS(
                f"Re-embedding: {stats['updated']}/{stats['total']} en {stats['duration_seconds']}s"
            ))
