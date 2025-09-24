"""Academic Records views package."""

from .transcript_views import (
    TranscriptDashboardView,
    bulk_generate_transcripts,
    generate_transcript,
    generate_transcript_pdf,
    transcript_dashboard,
    transcript_preview,
    transcript_wizard,
)

__all__ = [
    "TranscriptDashboardView",
    "bulk_generate_transcripts",
    "generate_transcript",
    "generate_transcript_pdf",
    "transcript_dashboard",
    "transcript_preview",
    "transcript_wizard",
]
