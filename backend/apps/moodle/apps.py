"""Moodle app configuration."""

from django.apps import AppConfig


class MoodleConfig(AppConfig):
    """Configuration for Moodle integration app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.moodle"
    verbose_name = "Moodle Integration"

    def ready(self):
        """Import signals when app is ready."""
