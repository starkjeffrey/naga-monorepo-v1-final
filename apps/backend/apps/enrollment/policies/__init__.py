"""Enrollment business policies for centralized rule management.

This module contains enrollment-specific policies that integrate with the
centralized policy engine for transparent, auditable business rule enforcement.
"""

from .enrollment_policies import EnrollmentCapacityPolicy

__all__ = [
    "EnrollmentCapacityPolicy",
]
