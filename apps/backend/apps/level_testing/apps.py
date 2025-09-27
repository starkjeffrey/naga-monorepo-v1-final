import contextlib

from django.apps import AppConfig


class LevelTestingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.level_testing"
    verbose_name = "Level Testing"

    def ready(self) -> None:
        """Import signal handlers when app is ready."""
        with contextlib.suppress(ImportError):
            pass
