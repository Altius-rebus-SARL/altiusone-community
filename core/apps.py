from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Importer les signals existants (Client, Mandat, Notification)
        import core.signals  # noqa: F401

        # Connecter les signals d'embedding pour tous les modèles configurés
        from core.signals import register_embedding_signals
        register_embedding_signals()
