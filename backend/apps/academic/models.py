"""Academic app models.

This module imports all models from the organized models package
for backwards compatibility with existing code.
"""

# Import all models from the models package
from .models.canonical import CanonicalRequirement
from .models.exceptions import StudentCourseOverride, StudentRequirementException
from .models.fulfillment import StudentDegreeProgress
from .models.transfer import CourseEquivalency, TransferCredit

# Re-export all models
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
