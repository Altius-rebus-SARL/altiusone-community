from django.apps import AppConfig


class EditeurConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'editeur'
    verbose_name = 'Éditeur Collaboratif'

    def ready(self):
        # Import des signaux pour la synchronisation
        try:
            import editeur.signals  # noqa
        except ImportError:
            pass
