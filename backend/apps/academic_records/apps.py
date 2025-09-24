from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AcademicRecordsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.academic_records"
    verbose_name = _("Academic Records")
