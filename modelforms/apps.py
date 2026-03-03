# apps/modelforms/apps.py
from django.apps import AppConfig


class ModelformsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modelforms'
    verbose_name = 'Model-Driven Forms'
