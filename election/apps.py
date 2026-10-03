from django.apps import AppConfig


class ElectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'election'

    def ready(self):
        from . import signals  # noqa: F401  (registers the result-history receivers)
