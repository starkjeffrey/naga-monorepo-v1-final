"""Scholarships app configuration.

This app handles sponsorships, scholarships, and student financial aid
following clean architecture principles with no circular dependencies.
"""

from django.apps import AppConfig


class ScholarshipsConfig(AppConfig):
    """Configuration for the scholarships app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.scholarships"
    verbose_name = "Scholarships and Sponsorships"
