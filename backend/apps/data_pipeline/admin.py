"""
Data Pipeline Admin Interface - Simplified

Basic admin interface for data pipeline models.
"""

from django.contrib import admin

from .models import PipelineRun


@admin.register(PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    """Simple admin interface for Pipeline Runs"""

    list_display = ["id", "table_name", "status", "stage", "started_at"]
    list_filter = ["status", "stage", "table_name"]
    readonly_fields = ["started_at", "completed_at"]

    fieldsets = [
        ("Basic Information", {"fields": ("table_name", "status", "stage")}),
        ("Timing", {"fields": ("started_at", "completed_at")}),
    ]
