from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EnrollmentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.enrollment"
    verbose_name = _("Enrollment")
