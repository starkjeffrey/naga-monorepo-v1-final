"""URL configuration for the academic_records app."""

from django.urls import path

from .views import transcript_views

app_name = "academic_records"

urlpatterns = [
    # Main dashboard
    path("", transcript_views.TranscriptDashboardView.as_view(), name="dashboard"),
    # Transcript management
    path("transcripts/", transcript_views.transcript_dashboard, name="transcript_dashboard"),
    path("transcript/generate/<int:student_id>/", transcript_views.generate_transcript, name="generate_transcript"),
    path("transcript/preview/<int:request_id>/", transcript_views.transcript_preview, name="transcript_preview"),
    path("transcript/wizard/", transcript_views.transcript_wizard, name="transcript_wizard"),
    # HTMX endpoints
    path("bulk-generate/", transcript_views.bulk_generate_transcripts, name="bulk_generate"),
    # Future endpoints for document detail, verification, etc.
    path("transcript/detail/<int:request_id>/", transcript_views.transcript_preview, name="transcript_detail"),
]
