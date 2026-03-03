from django.apps import AppConfig


class FacturationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facturation'

    def ready(self):
        import facturation.signals  # noqa: F401
