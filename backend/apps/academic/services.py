"""Academic services - backwards compatibility module.

This module imports all services from the new services package
for backwards compatibility with existing code.
"""

from .services.canonical import CanonicalRequirementService
from .services.degree_audit import DegreeAuditService
from .services.exceptions import (
    StudentCourseOverrideService,
    StudentRequirementExceptionService,
)
from .services.transfer import CourseEquivalencyService, TransferCreditService

__all__ = [
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
