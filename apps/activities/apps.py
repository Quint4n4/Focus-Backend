from django.apps import AppConfig


class ActivitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.activities'
    verbose_name = 'Actividades'

    def ready(self):
        import apps.activities.signals  # noqa: F401
