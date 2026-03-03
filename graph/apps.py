from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GraphConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'graph'
    verbose_name = _('Graphe relationnel')

    def ready(self):
        import graph.signals  # noqa: F401
        graph.signals.register_sync_signals()
