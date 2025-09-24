"""Academic models package.

This package organizes academic models into logical modules:
- canonical: Canonical requirements and degree progress tracking
- transfer: Transfer credits and course equivalencies
- exceptions: Student-specific exceptions and overrides
"""

# Import all models for backwards compatibility
from .canonical import CanonicalRequirement
from .exceptions import StudentCourseOverride, StudentRequirementException
from .fulfillment import StudentDegreeProgress
from .transfer import CourseEquivalency, TransferCredit

__all__ = [
    # Canonical models
    "CanonicalRequirement",
    # Transfer models
    "CourseEquivalency",
    "StudentCourseOverride",
    # Progress tracking (renamed from CanonicalRequirementFulfillment for human-friendliness)
    "StudentDegreeProgress",
    # Exception models
    "StudentRequirementException",
    "TransferCredit",
]
