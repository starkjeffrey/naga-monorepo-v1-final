"""Scholarship services package.

This package provides services for managing both NGO-funded and non-NGO scholarships.

Key services:
- UnifiedScholarshipService: Main entry point for scholarship resolution
- NGOPortalService: Bulk operations and reporting for NGO sponsors
- NGOScholarshipTransferService: Handle dropped NGO students
- Import services for legacy data migration
"""

from apps.scholarships.services.import_service import ScholarshipImportService
from apps.scholarships.services.ngo_portal_service import NGOPortalService
from apps.scholarships.services.ngo_transfer_service import (
    NGOScholarshipTransferService,
    TransferResult,
)
from apps.scholarships.services.unified_scholarship_service import (
    ScholarshipBenefit,
    UnifiedScholarshipService,
)

__all__ = [
    # NGO services
    "NGOPortalService",
    "NGOScholarshipTransferService",
    "ScholarshipBenefit",
    # Import services
    "ScholarshipImportService",
    "TransferResult",
    # Primary services
    "UnifiedScholarshipService",
]
