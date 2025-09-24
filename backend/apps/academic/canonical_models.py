"""Canonical models - backwards compatibility module.

This module imports canonical models from the new structure
for backwards compatibility with existing imports.
"""

from .models.canonical import CanonicalRequirement
from .models.exceptions import StudentRequirementException
from .models.fulfillment import StudentDegreeProgress

__all__ = [
    "CanonicalRequirement",
    "StudentDegreeProgress",
    "StudentRequirementException",
]
