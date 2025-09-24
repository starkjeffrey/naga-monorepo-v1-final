"""Enrollment app custom exceptions.

This module contains custom exceptions for enrollment-related validation errors,
particularly for major declaration and enrollment consistency checking.

Following clean architecture principles with clear exception hierarchy
for different types of enrollment conflicts and validation errors.
"""

from __future__ import annotations

from typing import Any


class EnrollmentValidationError(Exception):
    """Base exception for enrollment validation errors."""


class MajorDeclarationError(EnrollmentValidationError):
    """Exception raised when major declaration operations fail."""


class MajorConflictError(EnrollmentValidationError):
    """Exception raised when student's major declaration conflicts with enrollment history.

    This occurs when a student attempts to register for courses that belong to their
    historical major but contradict their new major declaration. The MajorDeclaration
    and actual ProgramEnrollment must make sense when viewed together.
    """

    def __init__(
        self,
        message: str,
        declared_major: Any = None,
        conflicting_course: Any = None,
        enrollment_major: Any = None,
    ) -> None:
        super().__init__(message)
        self.declared_major = declared_major
        self.conflicting_course = conflicting_course
        self.enrollment_major = enrollment_major


class CourseRegistrationError(EnrollmentValidationError):
    """Exception raised when course registration validation fails."""

    def __init__(self, message: str, student: Any = None, course: Any = None, reason: Any = None) -> None:
        super().__init__(message)
        self.student = student
        self.course = course
        self.reason = reason


class InactiveMajorDeclarationError(MajorDeclarationError):
    """Exception raised when operating on inactive major declarations."""


class OverlappingMajorDeclarationError(MajorDeclarationError):
    """Exception raised when major declarations have overlapping date ranges."""
