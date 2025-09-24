"""Curriculum app models following clean architecture principles.

This module contains models for managing courses, academic structure, terms, and
curriculum-related entities. All models are designed to avoid circular dependencies
with other apps while serving both language and academic sections of the school.

Key architectural decisions:
- Replaced SchoolStructuralUnit MPTT hierarchy with explicit Division, Cycle, Major models
- Course model serves both language and academic sections
- Clean separation from enrollment, grading, and scheduling concerns
- Historical tracking via base model mixins

Models:
- Division: Top-level organizational units (e.g., Language Division, Academic Division)
- Cycle: Program cycles within divisions (e.g., Foundation, Bachelor's, Master's)
- Major: Specific degree programs within cycles
- Term: Academic terms/semesters with cohort tracking
- Course: All courses in the system (language and academic)
- Textbook: Course textbooks and materials
- CoursePartTemplate: Defines required parts for course levels with curriculum weights
- CoursePrerequisite: Course prerequisite relationships
"""

import datetime
from decimal import Decimal
from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    ForeignKey,
    IntegerField,
    PositiveSmallIntegerField,
    Sum,
    TextField,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel
from apps.scheduling.class_part_types import ClassPartType


class Division(AuditModel):
    """Top-level organizational divisions within the school.

    Represents major organizational units like Language Division, Academic Division,
    or specialized divisions. This replaces the top level of the old SchoolStructuralUnit
    hierarchy with a cleaner, more explicit model.

    Key features:
    - Simple hierarchy with explicit purpose
    - Optional grading scale assignment
    - Short name for abbreviations and codes
    - Active status tracking
    """

    name: CharField = models.CharField(
        _("Division Name"),
        max_length=255,
        help_text=_("Full name of the division (e.g., 'Language Division')"),
    )
    short_name: CharField = models.CharField(
        _("Short Name"),
        max_length=50,
        blank=True,
        help_text=_("Abbreviated name for codes and displays"),
    )
    description: TextField = models.TextField(_("Description"), blank=True)
    is_active: BooleanField = models.BooleanField(_("Is Active"), default=True)
    display_order: IntegerField = models.IntegerField(_("Display Order"), default=100)

    class Meta:
        verbose_name = _("Division")
        verbose_name_plural = _("Divisions")
        ordering = ["display_order", "name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["is_active", "display_order"]),
            models.Index(fields=["short_name"]),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        """Validate division data."""
        super().clean()
        if self.short_name:
            self.short_name = self.short_name.upper()


class Cycle(AuditModel):
    """Program cycles within divisions (e.g., Foundation, Bachelor's, Master's).

    Represents different levels or cycles of study within a division.
    This replaces the cycle level of the old SchoolStructuralUnit hierarchy.

    Key features:
    - Belongs to a specific division
    - Academic level designation (undergrad, postgrad, language)
    - Duration in terms/semesters
    - No degree tracking (degrees are determined by Major, not Cycle)
    """

    division: ForeignKey = models.ForeignKey(
        Division,
        on_delete=models.PROTECT,
        related_name="cycles",
        verbose_name=_("Division"),
    )
    name: CharField = models.CharField(
        _("Cycle Name"),
        max_length=255,
        help_text=_(
            "Name of the cycle (e.g., 'Foundation Year', 'Bachelor's Program')",
        ),
    )
    short_name: CharField = models.CharField(
        _("Short Name"),
        max_length=50,
        blank=True,
        help_text=_("Abbreviated name for codes"),
    )
    typical_duration_terms: PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Typical Duration (Terms)"),
        null=True,
        blank=True,
        help_text=_("Expected number of terms to complete this cycle"),
    )
    description: models.TextField = models.TextField(_("Description"), blank=True)
    is_active: models.BooleanField = models.BooleanField(_("Is Active"), default=True)
    display_order: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Display Order"),
        default=100,
        help_text=_("Order for display (positive integers only)"),
    )

    class Meta:
        verbose_name = _("Cycle")
        verbose_name_plural = _("Cycles")
        ordering = ["division", "display_order", "name"]
        unique_together = [["division", "short_name"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["division", "is_active"]),
            models.Index(fields=["display_order"]),
        ]

    def __str__(self) -> str:
        return f"{self.division.short_name or self.division.name} - {self.name}"

    def clean(self) -> None:
        """Validate cycle data."""
        super().clean()
        if self.short_name:
            self.short_name = self.short_name.upper()


class Major(AuditModel):
    """Unified model for academic majors and language programs.

    This model represents both types of programs offered at PUCSR:

    **Academic Programs (degree-granting):**
    - Bachelor's programs (BA): BUSADMIN, FIN-BANK, TOUR-HOSP, TESOL, IR, etc.
    - Master's programs (MBA, MEd): MBA, MED-LEAD, MED-TESOL
    - Certificate programs: ADULTENGL, etc.

    **Language Programs (non-degree):**
    - Language learning programs (LANG): IEAP, GESL, EHSS, EXPRESS, IELTS, ELL
    - High school is language-only (no academic majors in HS cycle)

    Both program types share similar administrative needs (enrollment tracking,
    course associations, student declarations, cycle organization), justifying
    the unified model approach while maintaining clear type distinctions.

    Key features:
    - Unified model for both academic and language programs
    - Faculty display information for transcripts (no business rules)
    - Program type distinction (program_type field) for academic vs language programs
    - Degree awarded tracking for academic programs (degree_awarded field)
    - Support for all PUCSR program types across all cycles
    - Language programs use degree_awarded = NONE
    """

    class ProgramType(models.TextChoices):
        """Types of programs offered."""

        ACADEMIC = "ACADEMIC", _("Academic Degree Program")
        LANGUAGE = "LANGUAGE", _("Language Program")

    class DegreeAwarded(models.TextChoices):
        """Degrees awarded upon program completion."""

        BA = "BA", _("Bachelor of Arts")
        MBA = "MBA", _("Master of Business Administration")
        MED = "MEd", _("Master of Education")
        MA = "MA", _("Master of Arts")
        AA = "AA", _("Associate of Arts")
        PHD = "PHD", _("Doctor of Philosophy")
        CERT = "CERT", _("Certificate")
        NONE = "NONE", _("No degree awarded")

    cycle: models.ForeignKey = models.ForeignKey(
        Cycle,
        on_delete=models.PROTECT,
        related_name="majors",
        verbose_name=_("Cycle"),
    )
    name: models.CharField = models.CharField(
        _("Program Name"),
        max_length=255,
        help_text=_("Full name of the major or program"),
    )
    short_name: models.CharField = models.CharField(
        _("Short Name"),
        max_length=50,
        blank=True,
        help_text=_("Abbreviated name for transcripts and codes"),
    )
    code: models.CharField = models.CharField(
        _("Program Code"),
        max_length=20,
        blank=True,
        help_text=_("Official code for this program"),
    )

    # Faculty information for transcript display (no business rules)
    faculty_display_name: models.CharField = models.CharField(
        _("Faculty Display Name"),
        max_length=255,
        blank=True,
        help_text=_("Faculty name for transcript display only (e.g., 'Faculty of Business & Economics')"),
    )
    faculty_code: models.CharField = models.CharField(
        _("Faculty Code"),
        max_length=10,
        blank=True,
        help_text=_("Faculty abbreviation for display (SSIR, BE, EDUC, IFL)"),
    )

    # Program type and degree information
    program_type: models.CharField = models.CharField(
        _("Program Type"),
        max_length=20,
        choices=ProgramType.choices,
        default=ProgramType.ACADEMIC,
        db_index=True,
        help_text=_(
            "Distinguishes between ACADEMIC (degree-granting programs like BA, MBA, MEd) "
            "and LANGUAGE (non-degree programs like IEAP, GESL, EHSS)"
        ),
    )
    degree_awarded: models.CharField = models.CharField(
        _("Degree Awarded"),
        max_length=20,
        choices=DegreeAwarded.choices,
        default=DegreeAwarded.NONE,
        help_text=_("Degree or certification awarded upon completion"),
    )

    description: models.TextField = models.TextField(_("Description"), blank=True)
    total_credits_required: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Total Credits Required"),
        null=True,
        blank=True,
        help_text=_("Total credits required to complete this program"),
    )
    is_active: models.BooleanField = models.BooleanField(_("Is Active"), default=True)
    display_order: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Display Order"),
        default=100,
        help_text=_("Order for display (positive integers only)"),
    )

    class Meta:
        verbose_name = _("Major")
        verbose_name_plural = _("Majors")
        ordering = ["cycle", "display_order", "name"]
        unique_together = [["cycle", "code"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["cycle", "is_active"]),
            models.Index(fields=["code"]),
            models.Index(fields=["program_type", "is_active"]),
            models.Index(fields=["faculty_code"]),
            models.Index(fields=["degree_awarded"]),
        ]

    def __str__(self) -> str:
        return f"{self.cycle} - {self.name}"

    @property
    def full_hierarchy_name(self) -> str:
        """Return the full hierarchy name for display."""
        return f"{self.cycle.division.name} > {self.cycle.name} > {self.name}"

    @property
    def faculty_display(self) -> str:
        """Return faculty display information for transcripts."""
        if self.faculty_display_name:
            return self.faculty_display_name
        return ""

    def can_transfer_credit_from(self, other_major: "Major", course_code: str) -> bool:
        """Simple transfer credit logic: credit if class already fulfilled.

        Based on PUCSR policy: if a student completes a course (like "Introduction to Ethics")
        that exists across multiple programs, they get credit when changing majors regardless
        of their original major.

        Args:
            other_major: The major the student is transferring from
            course_code: The course code being evaluated for transfer

        Returns:
            bool: True if credit can be transferred (same course exists in both programs)
        """
        # Get courses for both majors
        current_courses = set(self.courses.values_list("code", flat=True))
        set(other_major.courses.values_list("code", flat=True))

        # Credit transfers if the course exists in the target major
        # regardless of the source major
        return course_code in current_courses

    def clean(self) -> None:
        """Validate major data."""
        super().clean()
        if self.code:
            self.code = self.code.upper()
        if self.faculty_code:
            self.faculty_code = self.faculty_code.upper()

        # Validate program type and degree consistency
        if self.program_type == self.ProgramType.LANGUAGE:
            if self.degree_awarded not in [
                self.DegreeAwarded.CERT,
                self.DegreeAwarded.NONE,
            ]:
                raise ValidationError(
                    {"degree_awarded": _("Language programs should award certificates or no degree.")},
                )
        elif self.program_type == self.ProgramType.ACADEMIC:
            if self.degree_awarded == self.DegreeAwarded.CERT:
                raise ValidationError({"degree_awarded": _("Academic programs should not award certificates.")})


class Term(AuditModel):
    """Academic terms/semesters with comprehensive date and cohort tracking.

    Represents academic periods with support for different term types,
    cohort tracking, and important academic dates. Serves both language
    and academic divisions.

    Key features:
    - Multiple term types for different programs
    - Cohort number tracking for BA and MA programs
    - Comprehensive academic calendar dates
    - Enrollment and payment deadline tracking
    """

    class TermType(models.TextChoices):
        """Types of academic terms."""

        ENGLISH_A = "ENG A", _("English Term A")
        ENGLISH_B = "ENG B", _("English Term B")
        BACHELORS = "BA", _("BA Term")
        MASTERS = "MA", _("MA Term")
        SPECIAL = "X", _("Special Term")

    code: models.CharField = models.CharField(
        _("Term Code"),
        max_length=100,
        help_text=_("Unique identifier/code for the term (e.g., 'Fall 2024', 'BA15-T2')"),
    )
    description: models.TextField = models.TextField(_("Description"), blank=True)
    term_type: models.CharField = models.CharField(
        _("Term Type"),
        max_length=20,
        choices=TermType.choices,
        db_index=True,
        help_text=_("Type of academic term"),
    )

    # Cohort tracking for degree programs
    ba_cohort_number: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("BA Cohort Number"),
        null=True,
        blank=True,
        help_text=_("Bachelor's cohort number for this term"),
    )
    ma_cohort_number: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("MA Cohort Number"),
        null=True,
        blank=True,
        help_text=_("Master's cohort number for this term"),
    )

    # Academic calendar dates
    start_date: models.DateField = models.DateField(_("Start Date"), help_text=_("First day of classes"))
    end_date: models.DateField = models.DateField(_("End Date"), help_text=_("Last day of classes"))

    # Important deadlines
    discount_end_date: models.DateField = models.DateField(
        _("Discount End Date"),
        null=True,
        blank=True,
        help_text=_("Last day for early enrollment discounts"),
    )
    add_date: models.DateField = models.DateField(
        _("Add Deadline"),
        null=True,
        blank=True,
        help_text=_("Last day to add courses"),
    )
    drop_date: models.DateField = models.DateField(
        _("Drop Deadline"),
        null=True,
        blank=True,
        help_text=_("Last day to drop courses without penalty"),
    )
    payment_deadline_date: models.DateField = models.DateField(
        _("Payment Deadline"),
        null=True,
        blank=True,
        help_text=_("Final payment deadline"),
    )

    is_active: models.BooleanField = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Term")
        verbose_name_plural = _("Terms")
        ordering = ["-start_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["term_type", "-start_date"]),
            models.Index(fields=["is_active", "-start_date"]),
            models.Index(fields=["ba_cohort_number"]),
            models.Index(fields=["ma_cohort_number"]),
        ]

    @classmethod
    def get_current_term(cls):
        """Get the current active term based on date."""
        from django.utils import timezone

        now = timezone.now().date()
        return cls.objects.filter(is_active=True, start_date__lte=now, end_date__gte=now).first()

    @classmethod
    def suggest_target_term(cls, source_term: "Term") -> "Term | None":
        """Suggest appropriate target term for language program promotions.

        Business rules:
        - Target term must have the same term_type as source term
        - Target term must start after source term ends
        - ENG_A promotes to next ENG_A, BA promotes to next BA, etc.

        Args:
            source_term: The term students are completing

        Returns:
            Next available term of same type, or None if no suitable term found
        """
        if not source_term:
            return None

        return (
            cls.objects.filter(term_type=source_term.term_type, start_date__gt=source_term.end_date, is_active=True)
            .order_by("start_date")
            .first()
        )

    @property
    def academic_year(self) -> int:
        """Get academic year from start date for API compatibility."""
        return self.start_date.year

    @property
    def is_current(self) -> bool:
        """Check if this is the current active term."""
        return self == self.get_current_term()

    def __str__(self) -> str:
        return self.code

    def clean(self) -> None:
        """Validate term dates."""
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({"end_date": _("End date must be after start date.")})

        if self.add_date and self.start_date and self.add_date < self.start_date:
            raise ValidationError(
                {"add_date": _("Add deadline should be on or after start date.")},
            )


class Course(AuditModel):
    """All courses in the system serving both language and academic sections.

    Represents individual courses with comprehensive metadata for curriculum
    planning, progression tracking, and scheduling. Designed to serve both
    language instruction and academic degree programs.

    Key features:
    - Serves both language and academic sections
    - Course progression planning fields
    - Credit and level tracking
    - Major association via many-to-many
    - Foundation year identification
    - Failure retry priority for student planning
    """

    # Basic course information
    code: models.CharField = models.CharField(
        _("Course Code"),
        max_length=15,
        db_index=True,
        help_text=_(
            "Course code (e.g., 'ENGL-110', 'MATH-101'). Multiple versions allowed with different effective dates.",
        ),
    )
    title: models.CharField = models.CharField(
        _("Course Title"),
        max_length=100,
        help_text=_("Full course title"),
    )
    short_title: models.CharField = models.CharField(
        _("Short Title"),
        max_length=30,
        help_text=_("Abbreviated title for transcripts"),
    )
    description: models.TextField = models.TextField(_("Description"), blank=True)

    # Academic organization
    cycle: models.ForeignKey = models.ForeignKey(
        Cycle,
        on_delete=models.PROTECT,
        related_name="courses",
        verbose_name=_("Cycle"),
        help_text=_("Academic cycle for this course"),
    )
    majors: models.ManyToManyField = models.ManyToManyField(
        Major,
        blank=True,
        related_name="courses",
        verbose_name=_("Majors"),
        help_text=_("Majors that include this course in their curriculum"),
    )

    # Course metadata
    credits: models.IntegerField = models.IntegerField(
        _("Credits"),
        default=3,
        help_text=_("Number of credit hours for this course"),
    )
    is_language: models.BooleanField = models.BooleanField(
        _("Is Language Course"),
        default=True,
        help_text=_("Whether this is a language instruction course"),
    )
    is_foundation_year: models.BooleanField = models.BooleanField(
        _("Is Foundation Year"),
        default=False,
        help_text=_("Whether this course is part of foundation year curriculum"),
    )
    is_senior_project: models.BooleanField = models.BooleanField(
        _("Is Senior Project"),
        default=False,
        help_text=_("Whether this course is a senior project requiring group formation and tiered pricing"),
    )

    # Course progression and planning
    recommended_term: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Recommended Term"),
        null=True,
        blank=True,
        help_text=_("Recommended term number for taking this course"),
    )
    earliest_term: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Earliest Term"),
        null=True,
        blank=True,
        help_text=_("Earliest term when this course can be taken"),
    )
    latest_term: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Latest Term"),
        null=True,
        blank=True,
        help_text=_("Latest term when this course should be taken"),
    )
    failure_retry_priority: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Failure Retry Priority"),
        default=1,
        help_text=_("Priority for retaking if failed (1=highest priority)"),
    )

    # Effective date range
    start_date: models.DateField = models.DateField(
        _("Start Date"),
        default=datetime.date(2009, 4, 7),
        help_text=_("Date when this course becomes available"),
    )
    end_date: models.DateField = models.DateField(
        _("End Date"),
        blank=True,
        null=True,
        help_text=_("Date when this course is discontinued (if applicable)"),
    )

    is_active: models.BooleanField = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")
        ordering = ["code"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["code"]),
            models.Index(fields=["cycle", "is_active"]),
            models.Index(fields=["is_foundation_year"]),
            models.Index(fields=["is_senior_project"]),
        ]

    def __str__(self) -> str:
        cycle_name = self.cycle.short_name if self.cycle else "N/A"
        return f"{self.code}: {self.title} ({self.credits}cr, {cycle_name})"

    @property
    def division(self):
        """Access division through cycle for backward compatibility."""
        return self.cycle.division if self.cycle else None

    @property
    def textbooks(self):
        """Get all textbooks associated with this course through part templates."""

        return Textbook.objects.filter(part_templates__course=self).distinct()

    @property
    def course_level(self) -> str:
        """Get course level from cycle for API compatibility."""
        return self.cycle.name if self.cycle else "Unknown"

    # Note: is_language is now a model field, not a computed property

    @property
    def is_currently_active(self) -> bool:
        """Check if course is currently active based on dates."""
        today = timezone.now().date()

        if not self.is_active:
            return False

        if self.start_date > today:
            return False

        return not (self.end_date and self.end_date < today)

    def clean(self) -> None:
        """Validate course data."""
        super().clean()

        # Validate date range
        if self.end_date and self.start_date >= self.end_date:
            raise ValidationError({"end_date": _("End date must be after start date.")})

        # Validate term progression
        if self.earliest_term and self.latest_term and self.earliest_term > self.latest_term:
            raise ValidationError(
                {
                    "latest_term": _(
                        "Latest term must be after or equal to earliest term.",
                    ),
                },
            )

        if self.recommended_term and self.earliest_term and self.recommended_term < self.earliest_term:
            raise ValidationError(
                {
                    "recommended_term": _(
                        "Recommended term cannot be before earliest term.",
                    ),
                },
            )

        if self.recommended_term and self.latest_term and self.recommended_term > self.latest_term:
            raise ValidationError(
                {
                    "recommended_term": _(
                        "Recommended term cannot be after latest term.",
                    ),
                },
            )

        # Validate no overlapping date ranges for same course code
        if self.code and self.start_date:
            other_courses = Course.objects.filter(code=self.code)
            if self.pk:
                other_courses = other_courses.exclude(pk=self.pk)

            for other_course in other_courses:
                other_start = other_course.start_date
                other_end = other_course.end_date
                this_end = self.end_date

                # Check for overlap using interval logic
                # Two intervals [a,b] and [c,d] overlap if: max(a,c) <= min(b,d)
                # Special handling for None end dates (treat as far future)

                this_effective_end = this_end or datetime.date(9999, 12, 31)
                other_effective_end = other_end or datetime.date(9999, 12, 31)

                # Intervals overlap if start of one is <= end of other for both directions
                if self.start_date <= other_effective_end and other_start <= this_effective_end:
                    overlap_desc = f"from {other_start}"
                    if other_end:
                        overlap_desc += f" to {other_end}"
                    else:
                        overlap_desc += " (ongoing)"

                    raise ValidationError(
                        {
                            "start_date": _(
                                f"Course code '{self.code}' already exists with overlapping dates "
                                f"({overlap_desc}). Course versions must have non-overlapping date ranges.",
                            ),
                        },
                    )


class Textbook(AuditModel):
    """Textbooks and course materials.

    Represents textbooks, course materials, and resources used in courses.
    Designed to be simple and focused on essential bibliographic information.

    Key features:
    - Standard bibliographic fields
    - ISBN tracking for ordering
    - Edition and year tracking
    - Simple and focused design
    """

    title: models.CharField = models.CharField(
        _("Title"),
        max_length=200,
        help_text=_("Full title of the textbook"),
    )
    author: models.CharField = models.CharField(
        _("Author"),
        max_length=200,
        help_text=_("Author(s) of the textbook"),
    )
    isbn: models.CharField = models.CharField(
        _("ISBN"),
        max_length=20,
        blank=True,
        help_text=_("ISBN for ordering and identification"),
    )
    publisher: models.CharField = models.CharField(
        _("Publisher"),
        max_length=100,
        blank=True,
        help_text=_("Publishing company"),
    )
    edition: models.CharField = models.CharField(
        _("Edition"),
        max_length=20,
        blank=True,
        help_text=_("Edition number or description"),
    )
    year: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Publication Year"),
        blank=True,
        null=True,
        help_text=_("Year of publication"),
    )
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this textbook"),
    )

    class Meta:
        verbose_name = _("Textbook")
        verbose_name_plural = _("Textbooks")
        ordering = ["title", "author"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["title"]),
            models.Index(fields=["author"]),
            models.Index(fields=["isbn"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} by {self.author}"

    @property
    def citation(self) -> str:
        """Generate a basic citation for the textbook."""
        parts = [self.author, self.title]

        if self.edition:
            parts.append(f"{self.edition} edition")

        if self.publisher:
            parts.append(self.publisher)

        if self.year:
            parts.append(str(self.year))

        return ", ".join(filter(None, parts))


class CoursePrerequisite(AuditModel):
    """Course prerequisite relationships.

    Represents prerequisite relationships between courses, indicating which
    courses must be completed before a student can enroll in another course.

    Key features:
    - Clear prerequisite → course relationship
    - Optional notes for complex prerequisites
    - Effective date range support
    - Simple and focused design
    """

    prerequisite: models.ForeignKey = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enables_courses",
        verbose_name=_("Prerequisite Course"),
        help_text=_("Course that must be completed first"),
    )
    course: models.ForeignKey = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="required_prerequisites",
        verbose_name=_("Course"),
        help_text=_("Course that requires the prerequisite"),
    )
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this prerequisite relationship"),
    )

    # Effective date range
    start_date: models.DateField = models.DateField(
        _("Effective Start Date"),
        default=datetime.date.today,
        help_text=_("Date when this prerequisite becomes effective"),
    )
    end_date: models.DateField = models.DateField(
        _("Effective End Date"),
        blank=True,
        null=True,
        help_text=_("Date when this prerequisite is no longer required"),
    )

    is_active: models.BooleanField = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Course Prerequisite")
        verbose_name_plural = _("Course Prerequisites")
        unique_together = [["prerequisite", "course"]]
        ordering = ["course__code", "prerequisite__code"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["course", "is_active"]),
            models.Index(fields=["prerequisite", "is_active"]),
        ]

    @property
    def relationship_type(self) -> str:
        """Get relationship type for API compatibility."""
        return "prerequisite"  # Default relationship type

    @property
    def is_required(self) -> bool:
        """Check if prerequisite is required for API compatibility."""
        return True  # All prerequisites are required by default

    def __str__(self) -> str:
        return f"{self.prerequisite.code} → {self.course.code}"

    def clean(self) -> None:
        """Validate prerequisite relationship."""
        super().clean()

        # Prevent self-prerequisites
        if self.prerequisite == self.course:
            raise ValidationError(_("A course cannot be a prerequisite for itself."))

        # Validate date range
        if self.end_date and self.start_date >= self.end_date:
            raise ValidationError({"end_date": _("End date must be after start date.")})


class CoursePartTemplate(AuditModel):
    """Defines required parts for a course level with curriculum-defined weights.

    This model specifies the standard structure for a course, including what parts
    (Grammar, Computer Lab, etc.) should be created when a class is instantiated.
    Grade weights are curriculum decisions made during course design.

    CRITICAL: Course creation FAILS if template missing - no fallback cloning.
    This ensures curriculum integrity and proper textbook assignments.

    Key features:
    - Curriculum-defined grade weights (not scheduling decisions)
    - IEAP session support (1 or 2, but scheduling order flexible)
    - Required textbook assignments per part
    - Meeting day templates (can be adjusted during scheduling)
    - Validation ensures session weights sum to 1.0
    """

    course: models.ForeignKey = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="part_templates",
        verbose_name=_("Course"),
        help_text=_("Course this template defines parts for"),
    )

    # Part definition
    part_type: models.CharField = models.CharField(
        _("Part Type"),
        max_length=15,
        choices=ClassPartType.choices,
        default=ClassPartType.MAIN,
        help_text=_("Type of class component"),
    )
    part_code: models.CharField = models.CharField(
        _("Part Code"),
        max_length=10,
        help_text=_("Code for this part (A, B, C, etc.)"),
    )
    name: models.CharField = models.CharField(
        _("Part Name"),
        max_length=100,
        help_text=_("Display name (e.g., 'Grammar', 'Computer Lab')"),
    )

    # IEAP session assignment (1 or 2, but scheduling order flexible)
    session_number: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Session Number"),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(2)],
        help_text=_("Session assignment (1 or 2 for IEAP, 1 for regular classes)"),
    )

    meeting_days: models.CharField = models.CharField(
        _("Meeting Days"),
        max_length=20,
        help_text=_("Default meeting pattern (MON,WED,FRI) - can be adjusted during scheduling"),
    )

    # CURRICULUM-DEFINED grade weight (core business rule)
    grade_weight: models.DecimalField = models.DecimalField(
        _("Grade Weight"),
        max_digits=4,
        decimal_places=3,
        default=Decimal("1.000"),
        validators=[
            MinValueValidator(Decimal("0.000")),
            MaxValueValidator(Decimal("1.000")),
        ],
        help_text=_(
            "CURRICULUM WEIGHT: Predetermined during curriculum design. Parts in same session should sum to 1.0",
        ),
    )

    # Resources assigned by curriculum
    textbooks: models.ManyToManyField = models.ManyToManyField(
        Textbook,
        blank=True,
        related_name="part_templates",
        verbose_name=_("Textbooks"),
        help_text=_("Required textbooks for this part (curriculum decision)"),
    )

    # Organization
    display_order: models.IntegerField = models.IntegerField(
        _("Display Order"),
        default=100,
        help_text=_("Display order within session"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this template is currently active"),
    )

    class Meta:
        verbose_name = _("Course Part Template")
        verbose_name_plural = _("Course Part Templates")
        unique_together = [["course", "part_code"]]
        ordering = ["course", "session_number", "display_order"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["course", "is_active"]),
            models.Index(fields=["course", "session_number"]),
            models.Index(fields=["part_type"]),
        ]

    def __str__(self) -> str:
        session_display = f" (Session {self.session_number})" if self.session_number > 1 else ""
        return f"{self.course.code} - {self.name} ({self.part_code}){session_display}"

    @property
    def full_name(self) -> str:
        """Get full descriptive name including course."""
        return f"{self.course.code}: {self.name}"

    def clean(self) -> None:
        """Validate template weights sum correctly within sessions."""
        super().clean()

        if self.course and self.session_number:
            # Check that weights for same course/session sum to 1.0
            same_session_templates = CoursePartTemplate.objects.filter(
                course=self.course,
                session_number=self.session_number,
                is_active=True,
            )
            if self.pk:
                same_session_templates = same_session_templates.exclude(pk=self.pk)

            existing_weight_sum = same_session_templates.aggregate(total_sum=Sum("grade_weight"))[
                "total_sum"
            ] or Decimal("0.000")
            total_weight = existing_weight_sum + self.grade_weight

            if abs(total_weight - Decimal("1.000")) > Decimal("0.001"):
                raise ValidationError(
                    {
                        "grade_weight": _(
                            f"Grade weights for session {self.session_number} must sum to 1.000. "
                            f"Current total would be {total_weight:.3f}",
                        ),
                    },
                )

        # Validate meeting days format
        if self.meeting_days:
            valid_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
            days = [day.strip().upper() for day in self.meeting_days.split(",")]
            invalid_days = [day for day in days if day not in valid_days]
            if invalid_days:
                raise ValidationError(
                    {"meeting_days": _(f"Invalid days: {', '.join(invalid_days)}. Use: {', '.join(valid_days)}")},
                )

    @classmethod
    def get_templates_for_course(cls, course, session_number=None):
        """Get active templates for a course, optionally filtered by session."""
        queryset = cls.objects.filter(course=course, is_active=True)
        if session_number is not None:
            queryset = queryset.filter(session_number=session_number)
        return queryset.order_by("session_number", "display_order")

    @classmethod
    def validate_course_template_completeness(cls, course) -> dict[str, Any]:
        """Validate that a course has complete templates.

        Returns:
            dict: {'valid': bool, 'errors': list, 'warnings': list}
        """
        templates = cls.get_templates_for_course(course)
        errors: list[str] = []
        warnings: list[str] = []

        if not templates.exists():
            errors.append(f"Course {course.code} has no part templates defined")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check session weight totals
        sessions = templates.values_list("session_number", flat=True).distinct()
        for session_num in sessions:
            session_templates = templates.filter(session_number=session_num)
            total_weight = session_templates.aggregate(total_sum=Sum("grade_weight"))["total_sum"] or Decimal("0.000")

            if abs(total_weight - Decimal("1.000")) > Decimal("0.001"):
                errors.append(f"Session {session_num} weights sum to {total_weight:.3f}, should be 1.000")

        # Check IEAP requirements
        if course.code.startswith("IEAP"):
            if len(sessions) != 2:
                errors.append(f"IEAP course {course.code} should have exactly 2 sessions, has {len(sessions)}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


class SeniorProjectGroup(AuditModel):
    """Senior project groups for BA-level capstone projects.

    Senior projects are conducted by 1-5 students working together on a
    research project under faculty supervision. Groups form themselves
    and are charged tiered pricing based on group size.

    Key features:
    - Links to senior project course (BUS-489, FIN-489, IR-489, THM-433, EDUC-408)
    - Tracks 1-5 student members with tiered pricing
    - Project topic and final paper title tracking
    - Faculty advisor assignment
    - Important milestone dates
    - Project status management
    """

    class ProjectStatus(models.TextChoices):
        """Status of the senior project."""

        PROPOSED = "PROPOSED", _("Proposed")
        APPROVED = "APPROVED", _("Approved")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        SUBMITTED = "SUBMITTED", _("Submitted")
        DEFENDED = "DEFENDED", _("Defended")
        COMPLETED = "COMPLETED", _("Completed")
        WITHDRAWN = "WITHDRAWN", _("Withdrawn")

    # Core project information
    course: models.ForeignKey = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="curriculum_senior_project_groups",
        verbose_name=_("Senior Project Course"),
        help_text=_("Course this senior project is associated with"),
        limit_choices_to={"is_senior_project": True},
    )
    term: models.ForeignKey = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="curriculum_senior_project_groups",
        verbose_name=_("Term"),
        help_text=_("Term when this project is being conducted"),
    )

    # Group members (1-5 students)
    students: models.ManyToManyField = models.ManyToManyField(
        "people.StudentProfile",
        related_name="curriculum_senior_project_groups",
        verbose_name=_("Group Members"),
        help_text=_("Students participating in this senior project (1-5 students)"),
    )

    # Faculty supervision
    advisor: models.ForeignKey = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.PROTECT,
        related_name="curriculum_advised_senior_projects",
        verbose_name=_("Faculty Advisor"),
        help_text=_("Faculty member supervising this project"),
    )

    # Project details
    project_title: models.CharField = models.CharField(
        _("Project Title"),
        max_length=255,
        help_text=_("Working title of the senior project"),
    )
    final_title: models.CharField = models.CharField(
        _("Final Paper Title"),
        max_length=255,
        blank=True,
        help_text=_("Final title of the completed research paper"),
    )
    project_description: models.TextField = models.TextField(
        _("Project Description"),
        blank=True,
        help_text=_("Detailed description of the project scope and objectives"),
    )

    # Status and timeline
    status: models.CharField = models.CharField(
        _("Project Status"),
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.PROPOSED,
        db_index=True,
        help_text=_("Current status of the project"),
    )

    # Important dates
    proposal_date: models.DateField = models.DateField(
        _("Proposal Date"),
        null=True,
        blank=True,
        help_text=_("Date when project proposal was submitted"),
    )
    approval_date: models.DateField = models.DateField(
        _("Approval Date"),
        null=True,
        blank=True,
        help_text=_("Date when project was approved by advisor/committee"),
    )
    submission_date: models.DateField = models.DateField(
        _("Submission Date"),
        null=True,
        blank=True,
        help_text=_("Date when final paper was submitted"),
    )
    defense_date: models.DateField = models.DateField(
        _("Defense Date"),
        null=True,
        blank=True,
        help_text=_("Date of project defense/presentation"),
    )
    completion_date: models.DateField = models.DateField(
        _("Completion Date"),
        null=True,
        blank=True,
        help_text=_("Date when project was officially completed"),
    )

    # Administrative
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Administrative notes about the project"),
    )

    class Meta:
        verbose_name = _("Senior Project Group")
        verbose_name_plural = _("Senior Project Groups")
        ordering = ["-created_at"]
        unique_together = [["course", "term", "project_title"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["course", "term"]),
            models.Index(fields=["status"]),
            models.Index(fields=["advisor"]),
        ]

    def __str__(self) -> str:
        return f"{self.course.code} - {self.project_title} ({self.get_group_size()} students)"

    @property
    def group_size(self) -> int:
        """Get the number of students in this project group."""
        return self.students.count()

    def get_group_size(self) -> int:
        """Get the number of students in this project group (for admin display)."""
        return self.students.count()

    @property
    def pricing_tier_code(self) -> str | None:
        """Get the appropriate pricing tier code based on group size."""
        size = self.group_size
        if size <= 2:
            return "SENIOR_1_2"
        if size <= 5:
            return "SENIOR_3_5"
        return None  # Invalid group size

    def clean(self) -> None:
        """Validate senior project group data."""
        super().clean()

        # Validate that the course is actually a senior project
        if self.course and not getattr(self.course, "is_senior_project", False):
            raise ValidationError({"course": _("Selected course must be marked as a senior project.")})

    def add_student(self, student) -> bool:
        """Add a student to the project group if within size limits."""
        if self.group_size >= 5:
            return False
        self.students.add(student)
        return True

    def remove_student(self, student) -> bool:
        """Remove a student from the project group."""
        if self.group_size <= 1:
            return False  # Must have at least one student
        self.students.remove(student)
        return True

    def approve_project(self, approved_by=None) -> None:
        """Mark project as approved and set approval date."""
        if self.status == self.ProjectStatus.PROPOSED:
            self.status = self.ProjectStatus.APPROVED
            self.approval_date = timezone.now().date()
            self.save(update_fields=["status", "approval_date"])

    def submit_project(self) -> None:
        """Mark project as submitted and set submission date."""
        if self.status == self.ProjectStatus.IN_PROGRESS:
            self.status = self.ProjectStatus.SUBMITTED
            self.submission_date = timezone.now().date()
            self.save(update_fields=["status", "submission_date"])

    def complete_project(self) -> None:
        """Mark project as completed and set completion date."""
        if self.status in [self.ProjectStatus.DEFENDED, self.ProjectStatus.SUBMITTED]:
            self.status = self.ProjectStatus.COMPLETED
            self.completion_date = timezone.now().date()
            self.save(update_fields=["status", "completion_date"])
