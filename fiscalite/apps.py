from django.apps import AppConfig


class FiscaliteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fiscalite'

    def ready(self):
        import fiscalite.signals  # noqa: F401
