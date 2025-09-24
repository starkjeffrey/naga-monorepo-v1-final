from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SchedulingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.scheduling"
    verbose_name = _("Scheduling")

    def ready(self):
        """Import signals when the app is ready."""
