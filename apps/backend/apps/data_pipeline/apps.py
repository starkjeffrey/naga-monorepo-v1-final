"""
Data Pipeline App Configuration
"""

from django.apps import AppConfig


class DataPipelineConfig(AppConfig):
    """Configuration for the data_pipeline Django app"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.data_pipeline"
    verbose_name = "Data Pipeline"

    def ready(self):
        """Initialize app components when Django starts"""
        # Import signal handlers if any
        pass
