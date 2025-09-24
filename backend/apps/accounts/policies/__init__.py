"""Accounts app policies for authorization and institutional governance.

This module contains policies related to:
- Teaching qualifications and assignments
- Institutional authority and hierarchy
- Position-based access control
- Override authority validation
"""

from .authority_policies import OverrideAuthorityPolicy
from .teaching_policies import TeachingQualificationPolicy

__all__ = [
    "OverrideAuthorityPolicy",
    "TeachingQualificationPolicy",
]
