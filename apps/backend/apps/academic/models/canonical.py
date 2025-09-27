"""Canonical requirement models implementing "Canonical as default, exception as override" pattern.

This module defines the new canonical requirement system that addresses the architectural
flaws in the flexible requirement system. The new design follows these principles:

DESIGN PRINCIPLES:
1. Single Source of Truth: Course.credits is the ONLY source for course credit values
2. Canonical Requirements: Exactly 43 courses for BA degree (rigid, non-negotiable)
3. Exception-Based Overrides: Study abroad, transfers, substitutions handled separately
4. Clean Architecture: No dual credit authority, no flexible credit systems

IMPLEMENTATION STATUS:
- CanonicalRequirement: Complete, populated for 5 majors (BUSADMIN, TESOL, FIN-BANK, IR, TOUR-HOSP)
- StudentDegreeProgress: Structure complete, recalculate_progress() in services
"""

from decimal import Decimal
from typing import ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel


class CanonicalRequirement(AuditModel):
    """Canonical degree requirements - exactly 43 courses for BA degree.

    This model represents the rigid, non-negotiable course sequence that every
    student in a major must complete. There are no flexible credits or electives
    at the canonical level - every requirement specifies exactly one course.

    Key features:
    - Rigid 1-to-1 mapping: requirement → course
    - Sequential numbering (1-43 for BA degree, 1-24 for MA degree)
    - Single source of truth for credit values (Course.credits)
    - Term-based versioning for curriculum changes
    - No override fields or flexible credit systems
    - Supports multiple major programs with different requirement counts

    Example usage:
        # Get all requirements for a major
        requirements = CanonicalRequirement.objects.filter(
            major__code='BUSADMIN',
            is_active=True
        ).order_by('sequence_number')

        # Check canonical credits for a requirement
        credits = requirement.canonical_credits  # From Course.credits
    """

    major = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        related_name="canonical_requirements",
        verbose_name=_("Major"),
        help_text=_("The major program this canonical requirement applies to"),
    )
    sequence_number = models.PositiveSmallIntegerField(
        _("Sequence Number"),
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text=_("Order in degree sequence (1-43 for BA, 1-24 for MA, etc.)"),
        null=True,
        blank=True,
        default=1,
    )
    required_course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.PROTECT,
        related_name="canonical_requirements",
        verbose_name=_("Required Course"),
        help_text=_("The exact course required at this sequence position"),
    )
    name = models.CharField(
        _("Requirement Name"),
        max_length=200,
        help_text=_("Descriptive name for this requirement slot"),
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Additional context about this requirement"),
    )

    # Term-based versioning for curriculum changes
    effective_term = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="canonical_requirements_starting",
        verbose_name=_("Effective Term"),
        help_text=_("Term when this canonical requirement becomes effective"),
    )
    end_term = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="canonical_requirements_ending",
        null=True,
        blank=True,
        verbose_name=_("End Term"),
        help_text=_("Term when this requirement is no longer effective (optional)"),
    )

    # Administrative tracking
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this canonical requirement is currently in use"),
    )
    notes = models.TextField(
        _("Administrative Notes"),
        blank=True,
        help_text=_("Internal notes for curriculum committee"),
    )

    class Meta:
        app_label = "academic"
        verbose_name = _("Canonical Requirement")
        verbose_name_plural = _("Canonical Requirements")
        ordering = ["major", "sequence_number"]
        unique_together = [
            ["major", "sequence_number", "effective_term"],
            ["major", "required_course", "effective_term"],
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["major", "sequence_number"]),
            models.Index(fields=["major", "is_active"]),
            models.Index(fields=["effective_term", "end_term"]),
            models.Index(fields=["required_course"]),
        ]

    def __str__(self) -> str:
        return f"{self.major.code} #{self.sequence_number}: {self.required_course.code}"

    @property
    def canonical_credits(self) -> Decimal:
        """Get canonical credit value from the required course."""
        return Decimal(str(self.required_course.credits))

    @property
    def is_currently_effective(self) -> bool:
        """Check if requirement is currently effective based on terms."""
        if not self.is_active:
            return False

        # This would require current term tracking implementation
        return self.end_term is None

    def clean(self) -> None:
        """Validate canonical requirement data."""
        super().clean()

        # Validate term ordering
        if (
            self.end_term
            and self.effective_term_id
            and self.end_term_id
            and self.effective_term.start_date >= self.end_term.start_date
        ):
            raise ValidationError(
                {"end_term": _("End term must be after effective term.")},
            )

        # Validate no overlapping time periods for same course code within major
        if self.major_id and self.required_course_id and self.effective_term_id:
            overlapping_requirements = CanonicalRequirement.objects.filter(
                major=self.major,
                required_course__code=self.required_course.code,
                is_active=True,
            )
            if self.pk:
                overlapping_requirements = overlapping_requirements.exclude(pk=self.pk)

            for other_req in overlapping_requirements:
                # Check for time period overlap
                other_start = other_req.effective_term.start_date
                other_end = other_req.end_term.start_date if other_req.end_term else None

                this_start = self.effective_term.start_date
                this_end = self.end_term.start_date if self.end_term else None

                # Overlap detection logic
                overlaps = False

                if this_end is None and other_end is None:
                    # Both are open-ended, always overlap
                    overlaps = True
                elif this_end is None:
                    # This requirement is open-ended, overlaps if other starts before this ends
                    overlaps = other_start <= this_start or (other_end is not None and other_end > this_start)
                elif other_end is None:
                    # Other requirement is open-ended, overlaps if this starts before other ends
                    overlaps = this_start <= other_start or this_end > other_start
                else:
                    # Both have end dates, check for any overlap
                    overlaps = this_start < other_end and this_end > other_start

                if overlaps:
                    raise ValidationError(
                        _(
                            "Course {course_code} is already required for {major} "
                            "in overlapping time period ({other_start} - {other_end}). "
                            "Time periods for the same course code cannot overlap.",
                        ).format(
                            course_code=self.required_course.code,
                            major=self.major.code,
                            other_start=other_start,
                            other_end=other_end or "present",
                        ),
                    )
