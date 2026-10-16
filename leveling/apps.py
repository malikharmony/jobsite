from django.apps import AppConfig


class LevelingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leveling'

    def ready(self):
        import leveling.signals
