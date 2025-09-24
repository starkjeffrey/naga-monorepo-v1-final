"""Constants for Academic Records application.

This module centralizes all hardcoded values to improve maintainability
and make configuration changes easier.
"""

# PDF Generation Constants
COURSE_TITLE_TRUNCATE_LENGTH = 30
PDF_MARGIN_INCHES = 0.75
PDF_CONTENT_WIDTH_REDUCTION = 2  # Multiplier for margins

# Document Verification
VERIFICATION_CODE_LENGTH = 16
DEFAULT_VERIFICATION_CODE_ENTROPY = 32  # bits

# Fee Configuration
DEFAULT_CURRENCY = "USD"
DEFAULT_PROCESSING_TIME_HOURS = 24

# File Storage
MAX_FILE_SIZE_MB = 10
ALLOWED_FILE_EXTENSIONS = [".pdf", ".doc", ".docx"]

# Security Settings
CRYPTOGRAPHIC_HASH_ALGORITHM = "sha256"
MIN_VERIFICATION_CODE_LENGTH = 12

# Status Colors for Admin Display
STATUS_COLORS = {
    "PENDING": "#ffc107",  # Yellow/Amber
    "APPROVED": "#17a2b8",  # Blue
    "IN_PROGRESS": "#007bff",  # Primary Blue
    "COMPLETED": "#28a745",  # Green
    "CANCELLED": "#6c757d",  # Gray
    "REJECTED": "#dc3545",  # Red
    "ON_HOLD": "#fd7e14",  # Orange
}

# Priority Colors
PRIORITY_COLORS = {
    "LOW": "#6c757d",  # Gray
    "NORMAL": "#17a2b8",  # Blue
    "HIGH": "#ffc107",  # Yellow
    "URGENT": "#dc3545",  # Red
}

# Document Type Codes (for initial data)
DEFAULT_DOCUMENT_TYPES = {
    "OFFICIAL_TRANSCRIPT": {
        "name": "Official Transcript",
        "category": "academic_transcript",
        "description": "Official academic transcript with all courses and grades",
        "requires_approval": True,
        "auto_generate": False,
        "processing_time_hours": 48,
        "requires_grade_data": True,
        "has_fee": True,
        "fee_amount": 10.00,
        "free_allowance_per_year": 2,
    },
    "UNOFFICIAL_TRANSCRIPT": {
        "name": "Unofficial Transcript",
        "category": "academic_transcript",
        "description": "Unofficial academic transcript for student use",
        "requires_approval": False,
        "auto_generate": True,
        "processing_time_hours": 1,
        "requires_grade_data": True,
        "has_fee": False,
    },
    "ENROLLMENT_VERIFICATION": {
        "name": "Enrollment Verification Letter",
        "category": "enrollment_verification",
        "description": "Letter verifying current enrollment status",
        "requires_approval": False,
        "auto_generate": True,
        "processing_time_hours": 2,
        "has_fee": True,
        "fee_amount": 5.00,
        "free_allowance_per_term": 1,
    },
    "GRADE_REPORT": {
        "name": "Grade Report",
        "category": "grade_report",
        "description": "Detailed report of grades for specific term",
        "requires_approval": False,
        "auto_generate": True,
        "processing_time_hours": 1,
        "requires_grade_data": True,
        "has_fee": False,
    },
}

# Bulk Action Batch Sizes
ADMIN_BULK_ACTION_BATCH_SIZE = 100
BULK_UPDATE_BATCH_SIZE = 500

DEFAULT_EMAIL_TEMPLATES = {
    "REQUEST_SUBMITTED": "academic_records/emails/request_submitted.html",
    "REQUEST_APPROVED": "academic_records/emails/request_approved.html",
    "DOCUMENT_READY": "academic_records/emails/document_ready.html",
    "REQUEST_REJECTED": "academic_records/emails/request_rejected.html",
}

# Permissions
PERMISSION_CODENAMES = {
    "REQUEST_OWN_DOCUMENTS": "request_own_documents",
    "REQUEST_ANY_DOCUMENTS": "request_any_documents",
    "APPROVE_REQUESTS": "approve_document_requests",
    "GENERATE_DOCUMENTS": "generate_documents",
    "VIEW_ALL_REQUESTS": "view_all_document_requests",
    "MANAGE_DOCUMENT_TYPES": "manage_document_types",
}

# API Rate Limiting
API_RATE_LIMITS = {
    "DOCUMENT_REQUEST": "10/hour",
    "DOCUMENT_DOWNLOAD": "30/hour",
    "VERIFICATION_CHECK": "100/hour",
}
