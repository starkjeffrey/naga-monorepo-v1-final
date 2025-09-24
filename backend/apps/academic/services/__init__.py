"""Academic services package.

This package organizes academic business logic into service modules:
- canonical: Canonical requirement and degree progress services
- transfer: Transfer credit and course equivalency services
- exceptions: Student exception and override services
- degree_audit: Degree audit and mobile app services
- fulfillment: Requirement fulfillment tracking services
"""

# Import all services for easy access
from .canonical import CanonicalRequirementService
from .degree_audit import DegreeAuditService
from .exceptions import (
    StudentCourseOverrideService,
    StudentRequirementExceptionService,
)
from .fulfillment import CanonicalFulfillmentService
from .transfer import CourseEquivalencyService, TransferCreditService
from .validation import AcademicOverrideService, AcademicValidationService

__all__ = [
    # Override services
    "AcademicOverrideService",
    "AcademicValidationService",
    # Fulfillment services
    "CanonicalFulfillmentService",
    # Canonical services
    "CanonicalRequirementService",
    "CourseEquivalencyService",
    # Degree audit services
    "DegreeAuditService",
    "StudentCourseOverrideService",
    # Exception services
    "StudentRequirementExceptionService",
    # Transfer services
    "TransferCreditService",
]
