"""Canonical services - backwards compatibility module.

This module imports canonical services from the new structure
for backwards compatibility with existing imports.
"""

from .services.canonical import CanonicalRequirementService
from .services.degree_audit import DegreeAuditService

__all__ = [
    "CanonicalRequirementService",
    "DegreeAuditService",
]
