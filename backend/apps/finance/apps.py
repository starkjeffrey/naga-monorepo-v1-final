"""Django app configuration for finance app.

This app handles financial operations including:
- Course and fee pricing management
- Student billing and invoicing
- Payment processing and tracking
- Financial transaction audit trails

Following clean architecture principles with no circular dependencies.
"""

import contextlib

from django.apps import AppConfig


class FinanceConfig(AppConfig):
    """Configuration for the finance app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance"
    verbose_name = "Financial Management"

    def ready(self):
        """Import signals when app is ready."""
        with contextlib.suppress(ImportError):
            pass
