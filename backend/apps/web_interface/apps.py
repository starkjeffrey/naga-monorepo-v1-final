from django.apps import AppConfig


class WebInterfaceConfig(AppConfig):
    """Configuration for the web interface app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.web_interface"
    verbose_name = "Web Interface"

    def ready(self):
        """Initialize the app when Django starts."""
        # Import signals here if needed
        pass
