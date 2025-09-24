"""Language app configuration.

This app handles language program specific logic including:
- Language level progression and promotion
- Language program term preparation
- Bulk class cloning for language programs
- Student cohort management for language tracks
"""

from django.apps import AppConfig


class LanguageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.language"
    verbose_name = "Language Programs"
