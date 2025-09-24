"""Django app configuration for attendance app."""

import contextlib

from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    """Configuration for the attendance app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.attendance"
    verbose_name = "Attendance Management"

    def ready(self):
        """Import signals when app is ready."""
        with contextlib.suppress(ImportError):
            pass
