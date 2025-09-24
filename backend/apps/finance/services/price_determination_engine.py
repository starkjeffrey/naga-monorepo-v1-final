"""Price Determination Engine for Reconciliation.

This module implements the logic to determine the correct price for courses
based on the pricing rules documented in BA Academic Pricing and LANGUAGE.pdf.
It handles default pricing, fixed course pricing, senior project pricing,
and reading class pricing with proper historical date handling.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from django.db.models import Q

from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models import (
    CourseFixedPricing,
    DefaultPricing,
    ReadingClassPricing,
    SeniorProjectCourse,
    SeniorProjectPricing,
)

if TYPE_CHECKING:
    from apps.curriculum.models import Course, Term
    from apps.people.models import StudentProfile
    from apps.scheduling.models import ClassHeader

logger = logging.getLogger(__name__)


class PriceType:
    """Types of pricing that can be applied."""

    DEFAULT = "DEFAULT"
    FIXED = "FIXED"
    SENIOR_PROJECT = "SENIOR_PROJECT"
    READING_CLASS = "READING_CLASS"
    UNKNOWN = "UNKNOWN"


class PriceDeterminationResult:
    """Container for price determination results."""

    def __init__(
        self,
        unit_price: Decimal,
        total_price: Decimal,
        price_type: str,
        pricing_record_id: int | None = None,
        confidence: Decimal = Decimal("100"),
        notes: str = "",
        is_foreign: bool = False,
        courses_priced: list[dict] | None = None,
    ):
        self.unit_price = unit_price
        self.total_price = total_price
        self.price_type = price_type
        self.pricing_record_id = pricing_record_id
        self.confidence = confidence
        self.notes = notes
        self.is_foreign = is_foreign
        self.courses_priced = courses_priced or []


class PriceDeterminationEngine:
    """Engine for determining course prices based on various pricing rules."""

    # Senior project course codes
    SENIOR_PROJECT_CODES = {"IR-489", "BUS-489", "FIN-489", "THM-433"}

    # Reading class identifiers - look for any of these in the class part
    READING_CLASS_PATTERNS = [r"\bREAD\b", r"\bREQ\b", r"\bSPECIAL\b"]

    # Language course prefixes that always use fixed pricing
    LANGUAGE_PREFIXES = {"EHSS", "IEAP", "GESL"}

    def __init__(self):
        self._cache = {}
        self._senior_project_courses = None

    def determine_student_pricing(
        self,
        student: StudentProfile,
        term: Term,
        enrollments: list[ClassHeaderEnrollment],
    ) -> list[PriceDeterminationResult]:
        """Determine pricing for all of a student's enrollments in a term."""

        # Determine if student is foreign
        is_foreign = self._is_foreign_student(student)

        # Group enrollments by pricing type
        grouped = self._group_enrollments_by_type(enrollments, term)

        results = []

        # Process each pricing type
        for price_type, enrollment_group in grouped.items():
            if price_type == PriceType.DEFAULT:
                result = self._calculate_default_pricing(enrollment_group, term, is_foreign)
                results.append(result)

            elif price_type == PriceType.FIXED:
                # Fixed pricing is per course
                for enrollment in enrollment_group:
                    result = self._calculate_fixed_pricing(enrollment, term, is_foreign)
                    results.append(result)

            elif price_type == PriceType.SENIOR_PROJECT:
                # Senior projects need special handling for group size
                for enrollment in enrollment_group:
                    result = self._calculate_senior_project_pricing(enrollment, term, is_foreign)
                    results.append(result)

            elif price_type == PriceType.READING_CLASS:
                # Reading classes are priced based on class size
                for enrollment in enrollment_group:
                    result = self._calculate_reading_class_pricing(enrollment, term, is_foreign)
                    results.append(result)

        return results

    def _is_foreign_student(self, student: StudentProfile) -> bool:
        """Determine if a student is foreign based on citizenship."""
        if not hasattr(student, "citizenship") or not student.citizenship:
            return False

        # Cambodian or blank = domestic, Other = foreign
        citizenship = str(student.citizenship).upper()
        return citizenship not in ["CAMBODIA", "CAMBODIAN", "KH", ""]

    def _group_enrollments_by_type(
        self, enrollments: list[ClassHeaderEnrollment], term: Term
    ) -> dict[str, list[ClassHeaderEnrollment]]:
        """Group enrollments by their pricing type."""

        grouped: dict[str, list] = {
            PriceType.DEFAULT: [],
            PriceType.FIXED: [],
            PriceType.SENIOR_PROJECT: [],
            PriceType.READING_CLASS: [],
        }

        for enrollment in enrollments:
            price_type = self._determine_price_type(enrollment, term)
            grouped[price_type].append(enrollment)

        return grouped

    def _determine_price_type(self, enrollment: ClassHeaderEnrollment, term: Term) -> str:
        """Determine which pricing type applies to an enrollment."""

        # Type annotation to help mypy understand the concrete type
        class_header: ClassHeader = cast("ClassHeader", enrollment.class_header)
        course = class_header.course

        # Check for senior project first
        if self._is_senior_project(course):
            return PriceType.SENIOR_PROJECT

        # Check for reading class
        if self._is_reading_class(class_header):
            return PriceType.READING_CLASS

        # Check for fixed pricing
        if self._has_fixed_pricing(course, term):
            return PriceType.FIXED

        # Default pricing
        return PriceType.DEFAULT

    def _is_senior_project(self, course: Course) -> bool:
        """Check if a course is a senior project."""
        # Check against known codes
        if course.code in self.SENIOR_PROJECT_CODES:
            return True

        # Also check the SeniorProjectCourse table
        if self._senior_project_courses is None:
            self._senior_project_courses = set(
                SeniorProjectCourse.objects.filter(is_active=True).values_list("course__code", flat=True)
            )

        return course.code in self._senior_project_courses

    def _is_reading_class(self, class_header: ClassHeader) -> bool:
        """Determine if a class is a reading/special/request class."""

        # First check if ClassHeader has is_reading_class attribute
        if hasattr(class_header, "is_reading_class"):
            return class_header.is_reading_class

        # Check class type if available
        if hasattr(class_header, "class_type"):
            if class_header.class_type == "READING":
                return True

        # Check for patterns in the normalized part or class ID
        text_to_check = []

        if hasattr(class_header, "normalized_part"):
            text_to_check.append(str(class_header.normalized_part))

        if hasattr(class_header, "parsed_classpart"):
            text_to_check.append(str(class_header.parsed_classpart))

        if hasattr(class_header, "legacy_class_id"):
            text_to_check.append(str(class_header.legacy_class_id))

        # Search for reading class patterns
        combined_text = " ".join(text_to_check).upper()
        for pattern in self.READING_CLASS_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True

        return False

    def _has_fixed_pricing(self, course: Course, term: Term) -> bool:
        """Check if a course has fixed pricing for the term."""

        # Language courses always have fixed pricing
        if any(course.code.startswith(prefix) for prefix in self.LANGUAGE_PREFIXES):
            return True

        # Check CourseFixedPricing table
        pricing_date = term.start_date
        return (
            CourseFixedPricing.objects.filter(course=course, effective_date__lte=pricing_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=pricing_date))
            .exists()
        )

    def _calculate_default_pricing(
        self, enrollments: list[ClassHeaderEnrollment], term: Term, is_foreign: bool
    ) -> PriceDeterminationResult:
        """Calculate total price for default-priced courses."""

        if not enrollments:
            return PriceDeterminationResult(
                unit_price=Decimal("0"),
                total_price=Decimal("0"),
                price_type=PriceType.DEFAULT,
                confidence=Decimal("100"),
                is_foreign=is_foreign,
            )

        # Get the cycle from the first enrollment
        first_enrollment = enrollments[0]
        course = cast("ClassHeader", first_enrollment.class_header).course
        cycle = course.cycle

        # Get pricing for the term
        pricing_date = term.start_date
        pricing = (
            DefaultPricing.objects.filter(cycle=cycle, effective_date__lte=pricing_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=pricing_date))
            .order_by("-effective_date")
            .first()
        )

        if not pricing:
            logger.warning(f"No default pricing found for cycle {cycle} on {pricing_date}")
            return PriceDeterminationResult(
                unit_price=Decimal("0"),
                total_price=Decimal("0"),
                price_type=PriceType.DEFAULT,
                confidence=Decimal("0"),
                notes=f"No default pricing found for {cycle}",
                is_foreign=is_foreign,
            )

        unit_price = pricing.get_price_for_student(is_foreign)
        course_count = len(enrollments)
        total_price = unit_price * course_count

        courses_priced = [
            {
                "course_code": cast("ClassHeader", e.class_header).course.code,
                "course_name": cast("ClassHeader", e.class_header).course.title,
                "unit_price": unit_price,
            }
            for e in enrollments
        ]

        return PriceDeterminationResult(
            unit_price=unit_price,
            total_price=total_price,
            price_type=PriceType.DEFAULT,
            pricing_record_id=pricing.id,
            confidence=Decimal("100"),
            notes=f"{course_count} courses at default {cycle} pricing",
            is_foreign=is_foreign,
            courses_priced=courses_priced,
        )

    def _calculate_fixed_pricing(
        self, enrollment: ClassHeaderEnrollment, term: Term, is_foreign: bool
    ) -> PriceDeterminationResult:
        """Calculate price for a fixed-price course."""

        course = cast("ClassHeader", enrollment.class_header).course
        pricing_date = term.start_date

        pricing = (
            CourseFixedPricing.objects.filter(course=course, effective_date__lte=pricing_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=pricing_date))
            .order_by("-effective_date")
            .first()
        )

        if not pricing:
            logger.warning(f"No fixed pricing found for course {course.code} on {pricing_date}")
            return PriceDeterminationResult(
                unit_price=Decimal("0"),
                total_price=Decimal("0"),
                price_type=PriceType.FIXED,
                confidence=Decimal("0"),
                notes=f"No fixed pricing found for {course.code}",
                is_foreign=is_foreign,
            )

        unit_price = pricing.get_price_for_student(is_foreign)

        return PriceDeterminationResult(
            unit_price=unit_price,
            total_price=unit_price,
            price_type=PriceType.FIXED,
            pricing_record_id=pricing.id,
            confidence=Decimal("100"),
            notes=f"Fixed pricing for {course.code}",
            is_foreign=is_foreign,
            courses_priced=[
                {
                    "course_code": course.code,
                    "course_name": course.title,
                    "unit_price": unit_price,
                }
            ],
        )

    def _calculate_senior_project_pricing(
        self, enrollment: ClassHeaderEnrollment, term: Term, is_foreign: bool
    ) -> PriceDeterminationResult:
        """Calculate price for a senior project."""

        # For reconciliation, we need to determine group size
        # Since we can't determine from enrollments, we'll need to
        # try different tiers and see which one matches the payment

        course = cast("ClassHeader", enrollment.class_header).course
        pricing_date = term.start_date

        # Get all possible tiers
        tiers = (
            SeniorProjectPricing.objects.filter(effective_date__lte=pricing_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=pricing_date))
            .order_by("tier")
        )

        if not tiers:
            logger.warning(f"No senior project pricing found for {pricing_date}")
            return PriceDeterminationResult(
                unit_price=Decimal("0"),
                total_price=Decimal("0"),
                price_type=PriceType.SENIOR_PROJECT,
                confidence=Decimal("0"),
                notes="No senior project pricing found",
                is_foreign=is_foreign,
            )

        # Return the most expensive tier (1 student) as default
        # The reconciliation process will try to match against actual payment
        pricing = tiers.filter(tier="1").first() or tiers.first()
        if not pricing:
            return PriceDeterminationResult(
                unit_price=Decimal("0.00"),
                total_price=Decimal("0.00"),
                price_type=PriceType.UNKNOWN,
                pricing_record_id=None,
                confidence=Decimal("0"),
                notes=f"Senior project {course.code} - no pricing found",
                is_foreign=is_foreign,
            )

        unit_price = pricing.get_individual_price(is_foreign)

        return PriceDeterminationResult(
            unit_price=unit_price,
            total_price=unit_price,
            price_type=PriceType.SENIOR_PROJECT,
            pricing_record_id=pricing.id,
            confidence=Decimal("50"),  # Lower confidence since we're guessing tier
            notes=f"Senior project {course.code} (tier uncertain)",
            is_foreign=is_foreign,
            courses_priced=[
                {
                    "course_code": course.code,
                    "course_name": course.title,
                    "unit_price": unit_price,
                    "tier": pricing.tier,
                }
            ],
        )

    def _calculate_reading_class_pricing(
        self, enrollment: ClassHeaderEnrollment, term: Term, is_foreign: bool
    ) -> PriceDeterminationResult:
        """Calculate price for a reading class."""

        class_header = cast("ClassHeader", enrollment.class_header)
        course = class_header.course
        pricing_date = term.start_date

        # Determine class size to get tier
        enrolled_count = ClassHeaderEnrollment.objects.filter(
            class_header=class_header, status__in=["ENROLLED", "COMPLETED"]
        ).count()

        # Determine tier based on enrollment
        if enrolled_count <= 2:
            tier = "1-2"
        elif enrolled_count <= 5:
            tier = "3-5"
        else:
            tier = "6-15"

        cycle = course.cycle
        pricing = (
            ReadingClassPricing.objects.filter(cycle=cycle, tier=tier, effective_date__lte=pricing_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=pricing_date))
            .order_by("-effective_date")
            .first()
        )

        if not pricing:
            logger.warning(f"No reading class pricing found for {course.cycle} tier {tier} on {pricing_date}")
            return PriceDeterminationResult(
                unit_price=Decimal("0"),
                total_price=Decimal("0"),
                price_type=PriceType.READING_CLASS,
                confidence=Decimal("0"),
                notes="No reading class pricing found",
                is_foreign=is_foreign,
            )

        unit_price = pricing.get_price_for_student(is_foreign)

        return PriceDeterminationResult(
            unit_price=unit_price,
            total_price=unit_price,
            price_type=PriceType.READING_CLASS,
            pricing_record_id=pricing.id,
            confidence=Decimal("90"),
            notes=f"Reading class {course.code} ({enrolled_count} students)",
            is_foreign=is_foreign,
            courses_priced=[
                {
                    "course_code": course.code,
                    "course_name": course.title,
                    "unit_price": unit_price,
                    "tier": tier,
                    "class_size": enrolled_count,
                }
            ],
        )

    def attempt_senior_project_tier_match(
        self,
        enrollment: ClassHeaderEnrollment,
        payment_amount: Decimal,
        term: Term,
        is_foreign: bool,
    ) -> PriceDeterminationResult | None:
        """Try to determine senior project tier by matching payment amount."""

        course = cast("ClassHeader", enrollment.class_header).course
        pricing_date = term.start_date

        # Get all tiers
        tiers = (
            SeniorProjectPricing.objects.filter(effective_date__lte=pricing_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=pricing_date))
            .order_by("tier")
        )

        # Try each tier to see if it matches the payment
        for pricing in tiers:
            price = pricing.get_individual_price(is_foreign)
            if abs(price - payment_amount) <= Decimal("1.00"):  # Within $1
                return PriceDeterminationResult(
                    unit_price=price,
                    total_price=price,
                    price_type=PriceType.SENIOR_PROJECT,
                    pricing_record_id=pricing.id,
                    confidence=Decimal("95"),
                    notes=f"Senior project {course.code} tier {pricing.tier} (matched payment)",
                    is_foreign=is_foreign,
                    courses_priced=[
                        {
                            "course_code": course.code,
                            "course_name": course.title,
                            "unit_price": price,
                            "tier": pricing.tier,
                        }
                    ],
                )

        return None
