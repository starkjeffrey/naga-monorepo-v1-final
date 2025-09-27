"""Django app configuration for grading app."""

import contextlib

from django.apps import AppConfig


class GradingConfig(AppConfig):
    """Configuration for the grading app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.grading"
    verbose_name = "Grading Management"

    def ready(self):
        """Import signals when app is ready."""
        with contextlib.suppress(ImportError):
            pass
