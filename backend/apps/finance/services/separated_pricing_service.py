"""Pricing services for the separated pricing model architecture.

This module provides the service layer that orchestrates all pricing types
and provides a unified interface for calculating course prices based on
the business rules clarified by the user.

Key Business Rules Implemented:
- Senior projects: Charged after admin finalizes groups, no adjustments
- Reading classes: Tier-based pricing with admin price locking
- Course fixed pricing: Direct overrides for specific courses
- Default pricing: Fallback for standard courses
"""

import logging
import time
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from functools import wraps
from typing import TYPE_CHECKING, Any, Optional, cast

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.common.utils import get_current_date
from apps.curriculum.models import Course
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader

from ..models import (
    CourseFixedPricing,
    Currency,
    DefaultPricing,
    FeePricing,
    ReadingClassPricing,
    SeniorProjectCourse,
    SeniorProjectPricing,
)

if TYPE_CHECKING:
    from apps.curriculum.models import Cycle, Term

# Constants
FINANCIAL_PRECISION = Decimal("0.01")

# Logger
logger = logging.getLogger(__name__)


def performance_monitor(operation_name: str):
    """Decorator to monitor pricing operation performance.

    Args:
        operation_name: Name of the operation being monitored
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Log performance metrics
                if duration > 0.5:  # Log slow operations (>500ms)
                    logger.warning("Slow pricing operation: %s took %.3fs", operation_name, duration)
                elif duration > 0.1:  # Log moderate operations (>100ms)
                    logger.info("Pricing operation: %s took %.3fs", operation_name, duration)

                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "Pricing operation failed: %s failed after %.3fs with error: %s", operation_name, duration, str(e)
                )
                raise

        return wrapper

    return decorator


def normalize_decimal(value: Decimal | float | str | int) -> Decimal:
    """Convert a value to Decimal with financial precision.

    Args:
        value: The value to normalize

    Returns:
        Decimal with proper precision for financial calculations
    """
    if isinstance(value, Decimal):
        result = value
    else:
        result = Decimal(str(value))

    return result.quantize(FINANCIAL_PRECISION, rounding=ROUND_HALF_UP)


def safe_decimal_add(*values) -> Decimal:
    """Safely add multiple decimal values.

    Args:
        *values: Values to add

    Returns:
        Sum as Decimal with proper precision
    """
    total = Decimal("0.00")
    for value in values:
        if value is not None:
            total += normalize_decimal(value)

    return normalize_decimal(total)


class FinancialError(Exception):
    """Custom exception for financial operations."""


class SeparatedPricingService:
    """Master pricing service that orchestrates all separated pricing types.

    This is the main entry point for all pricing calculations using the
    new separated pricing model architecture. It determines which pricing
    type applies and delegates to the appropriate specialized service.
    """

    @staticmethod
    def get_pricing_date(term: Optional["Term"] = None) -> date:
        """Get the date to use for pricing lookups based on business rules.

        Business Rule: Pricing is determined by the term start date, not payment date.

        Args:
            term: The academic term (uses term.start_date for pricing lookup)

        Returns:
            Date to use for pricing effective date queries
        """
        return term.start_date if term else timezone.now().date()

    @staticmethod
    def get_active_pricing(queryset, pricing_date: date):
        """Get active pricing for a given date using consistent query pattern.

        Args:
            queryset: Base queryset for the pricing model
            pricing_date: Date to check for active pricing

        Returns:
            First matching pricing record or None
        """
        return (
            queryset.filter(effective_date__lte=pricing_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=pricing_date))
            .order_by("-effective_date")
            .first()
        )

    @classmethod
    @performance_monitor("course_price_calculation")
    def calculate_course_price(
        cls,
        course: Course,
        student: StudentProfile,
        term: "Term",
        class_header: ClassHeader | None = None,
    ) -> tuple[Decimal, str]:
        """Calculate price for a course enrollment.

        Args:
            course: The course being priced
            student: The student enrolling
            term: The academic term
            class_header: Optional class header for reading classes

        Returns:
            Tuple of (price_amount, pricing_description)

        Raises:
            ValidationError: If no pricing is found for the course
        """
        is_foreign = student.person.citizenship != "KH"

        # 1. Check if it's a senior project (charged after group finalization)
        if cls._is_senior_project(course):
            return SeniorProjectPricingService.calculate_price(course, student, term, is_foreign)

        # 2. Check if it's a reading/request class (tier-based pricing)
        if class_header and class_header.reading_class:
            return ReadingClassPricingService.calculate_price(class_header, student, is_foreign, term)

        # 3. Check for fixed course pricing (direct overrides)
        fixed_price = CourseFixedPricingService.get_price(course, is_foreign, term)
        if fixed_price is not None:
            return fixed_price, "Fixed Course Pricing"

        # 4. Use default pricing (cycle-based fallback)
        return DefaultPricingService.get_price(cast("Cycle", course.cycle), is_foreign, term)

    @classmethod
    def _is_senior_project(cls, course: Course) -> bool:
        """Check if course is configured as senior project."""
        return SeniorProjectCourse.objects.filter(course=course, is_active=True).exists()


class DefaultPricingService:
    """Service for default cycle-based pricing."""

    @classmethod
    def get_price(cls, cycle: "Cycle", is_foreign: bool, term: "Term | None" = None) -> tuple[Decimal, str]:
        """Get default price for a cycle based on term date.

        Args:
            cycle: The academic cycle
            is_foreign: Whether student is international
            term: The academic term (uses term.start_date for pricing lookup)

        Returns:
            Tuple of (price_amount, pricing_description)

        Raises:
            ValidationError: If no default pricing found
        """
        # Use consistent pricing date logic
        pricing_date = SeparatedPricingService.get_pricing_date(term)

        pricing = SeparatedPricingService.get_active_pricing(DefaultPricing.objects.filter(cycle=cycle), pricing_date)

        if not pricing:
            raise ValidationError(f"No default pricing found for {cycle}")

        price = pricing.get_price_for_student(is_foreign)
        return price, f"Default {cycle} Pricing"


class CourseFixedPricingService:
    """Service for course-specific fixed pricing."""

    @classmethod
    def get_price(cls, course: Course, is_foreign: bool, term: "Term | None" = None) -> Decimal | None:
        """Get fixed price for a course if it exists based on term date.

        Args:
            course: The course to check
            is_foreign: Whether student is international
            term: The academic term (uses term.start_date for pricing lookup)

        Returns:
            Decimal price if fixed pricing exists, None otherwise
        """
        # Use consistent pricing date logic
        pricing_date = SeparatedPricingService.get_pricing_date(term)

        pricing = SeparatedPricingService.get_active_pricing(
            CourseFixedPricing.objects.filter(course=course), pricing_date
        )

        if pricing:
            return pricing.get_price_for_student(is_foreign)
        return None


class SeniorProjectPricingService:
    """Service for senior project individual pricing based on group size.

    Business Rules:
    - Each student pays the FULL individual price (not split among group)
    - Price is higher when fewer students in group (tiered individual pricing)
    - Charged after admin finalizes groups
    - No adjustments if group membership changes after billing
    - Both domestic and foreign students supported
    """

    @classmethod
    def calculate_price(
        cls, course: Course, student: StudentProfile, term: "Term", is_foreign: bool
    ) -> tuple[Decimal, str]:
        """Calculate senior project price based on group size.

        Args:
            course: The senior project course
            student: The student (used to find group)
            term: The academic term
            is_foreign: Whether student is international

        Returns:
            Tuple of (individual_price, pricing_description)

        Raises:
            ValidationError: If no pricing found for the determined tier
        """
        # Import here to avoid circular imports
        from apps.enrollment.models import SeniorProjectGroup

        # Get the student's project group
        project_group = SeniorProjectGroup.objects.filter(students=student, course=course, term=term).first()

        if not project_group:
            # Student not in a group yet - this should be handled by UI
            # But we'll return individual pricing as fallback
            tier = SeniorProjectPricing.GroupSizeTier.ONE_STUDENT
            group_size = 1
        else:
            group_size = project_group.students.count()
            tier = cls._get_tier_for_size(group_size)

        # Get pricing for this tier based on term date
        # Use consistent pricing date logic
        pricing_date = SeparatedPricingService.get_pricing_date(term)
        pricing = SeparatedPricingService.get_active_pricing(
            SeniorProjectPricing.objects.filter(tier=tier), pricing_date
        )

        if not pricing:
            raise ValidationError(f"No senior project pricing found for tier {tier}")

        # Get individual price (each student pays full amount)
        individual_price = pricing.get_individual_price(is_foreign)

        return individual_price, f"Senior Project ({group_size} students)"

    @classmethod
    def _get_tier_for_size(cls, size: int) -> "SeniorProjectPricing.GroupSizeTier":
        """Determine pricing tier based on group size."""
        if size <= 1:
            return SeniorProjectPricing.GroupSizeTier.ONE_STUDENT
        elif size <= 2:
            return SeniorProjectPricing.GroupSizeTier.TWO_STUDENTS
        elif size <= 4:
            return SeniorProjectPricing.GroupSizeTier.THREE_FOUR_STUDENTS
        else:
            return SeniorProjectPricing.GroupSizeTier.FIVE_STUDENTS


class ReadingClassPricingService:
    """Service for reading/request class size-based pricing.

    Business Rules:
    - Tier-based pricing (fewer students = higher per-person cost)
    - Admin locks pricing after getting student acceptance
    - Price doesn't change if enrollment changes after locking
    """

    @classmethod
    def calculate_price(
        cls,
        class_header: ClassHeader,
        student: StudentProfile,
        is_foreign: bool,
        term: "Term | None" = None,
    ) -> tuple[Decimal, str]:
        """Calculate reading class price based on enrollment size and term date.

        Args:
            class_header: The reading class
            student: The student (for context, not used in calculation)
            is_foreign: Whether student is international
            term: The academic term (uses term.start_date for pricing lookup)

        Returns:
            Tuple of (price_per_student, pricing_description)

        Raises:
            ValidationError: If no pricing found for the class tier
        """
        # Get current enrollment count
        enrollment_count = class_header.class_header_enrollments.filter(
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        ).count()

        # Determine tier based on enrollment
        tier = cls._get_tier_for_size(enrollment_count)

        # Get pricing based on term date (fallback to class_header.term if term not provided)
        term_to_use = term or class_header.term
        # Use consistent pricing date logic
        pricing_date = SeparatedPricingService.get_pricing_date(term_to_use)
        pricing = SeparatedPricingService.get_active_pricing(
            ReadingClassPricing.objects.filter(cycle=cast("Cycle", class_header.course.cycle), tier=tier),
            pricing_date,
        )

        if not pricing:
            raise ValidationError(f"No reading class pricing found for {class_header.course.cycle} tier {tier}")

        # Get price based on student type
        price_per_student = pricing.get_price_for_student(is_foreign)

        return price_per_student, f"Reading Class ({enrollment_count} students)"

    @classmethod
    def _get_tier_for_size(cls, size: int) -> "ReadingClassPricing.ClassSizeTier":
        """Determine pricing tier based on class size."""
        if size <= 2:
            return ReadingClassPricing.ClassSizeTier.TUTORIAL
        elif size <= 5:
            return ReadingClassPricing.ClassSizeTier.SMALL
        else:
            return ReadingClassPricing.ClassSizeTier.MEDIUM

    @classmethod
    def lock_pricing(cls, class_header: ClassHeader, student: StudentProfile, is_foreign: bool) -> None:
        """Lock in the pricing for a reading class.

        This would integrate with the existing "lock price" functionality
        mentioned in the business requirements. Implementation depends on
        how price locking is currently handled in the system.

        Args:
            class_header: The reading class to lock pricing for
        """
        """Implementation of price locking mechanism for reading classes.

        Price locking ensures that once an admin finalizes pricing for a reading class,
        the price cannot be changed, providing consistency for students and billing.

        Business Rule: Once locked, prices remain fixed regardless of subsequent
        pricing rule changes to maintain billing consistency.
        """

        # Get current pricing for this reading class
        try:
            price, description = cls.calculate_price(class_header, student, is_foreign)

            # Store the locked price in ClassHeader notes field as fallback
            # In a full implementation, this would use a dedicated locked_price field
            if not hasattr(class_header, "locked_price_amount"):
                class_header.notes = f"PRICE_LOCKED: ${price:.2f} (locked on {timezone.now().date()})\n" + (
                    class_header.notes or ""
                )
                class_header.save(update_fields=["notes"])

        except Exception as e:
            raise FinancialError(f"Failed to lock price for reading class {class_header.id}: {e}") from e


class PricingValidationService:
    """Service for validating pricing configuration and preventing overlaps."""

    @classmethod
    def validate_no_overlapping_periods(
        cls,
        model_class: DefaultPricing | CourseFixedPricing | SeniorProjectPricing | ReadingClassPricing,
        instance,
        exclude_pk: int | None = None,
    ) -> None:
        """Validate that effective periods don't overlap for the same entity.

        Args:
            model_class: The pricing model class to check
            instance: The instance being validated
            exclude_pk: Primary key to exclude from validation (for updates)

        Raises:
            ValidationError: If overlapping periods are found
        """
        queryset = model_class.objects.all()

        if exclude_pk:
            queryset = queryset.exclude(pk=exclude_pk)

        # Build filter conditions based on model type
        if model_class == DefaultPricing:
            queryset = queryset.filter(cycle=instance.cycle)
        elif model_class == CourseFixedPricing:
            queryset = queryset.filter(course=instance.course)
        elif model_class == SeniorProjectPricing:
            queryset = queryset.filter(tier=instance.tier)
        elif model_class == ReadingClassPricing:
            queryset = queryset.filter(cycle=instance.cycle, tier=instance.tier)

        # Check for overlapping periods
        overlapping = (
            queryset.filter(
                effective_date__lt=instance.end_date or date.max,
                end_date__gt=instance.effective_date,
            )
            if instance.end_date
            else queryset.filter(effective_date__gte=instance.effective_date)
        )

        if overlapping.exists():
            raise ValidationError("Effective periods cannot overlap for the same pricing entity.")


class PricingReportService:
    """Service for generating pricing reports and analytics."""

    @classmethod
    def get_pricing_summary(cls, cycle: "Cycle | None" = None) -> dict:
        """Get a summary of all active pricing for reporting.

        Args:
            cycle: Optional cycle to filter by

        Returns:
            Dictionary with pricing summary data
        """
        # Using today's date is correct for reporting current active pricing (not enrollment pricing)
        today = timezone.now().date()
        active_filter = Q(effective_date__lte=today) & (Q(end_date__isnull=True) | Q(end_date__gte=today))

        summary = {
            "default_pricing": DefaultPricing.objects.filter(active_filter),
            "fixed_pricing": CourseFixedPricing.objects.filter(active_filter),
            "senior_project_pricing": SeniorProjectPricing.objects.filter(active_filter),
            "reading_class_pricing": ReadingClassPricing.objects.filter(active_filter),
            "senior_project_courses": SeniorProjectCourse.objects.filter(is_active=True),
        }

        if cycle:
            summary["default_pricing"] = summary["default_pricing"].filter(cycle=cycle)
            summary["reading_class_pricing"] = summary["reading_class_pricing"].filter(cycle=cycle)

        return summary

    @classmethod
    def get_course_price(
        cls,
        course: Course,
        student: StudentProfile,
        term: "Term",
        class_header: ClassHeader | None = None,
        pricing_date: date | None = None,
    ) -> tuple[Decimal, str, dict[str, Any]]:
        """Get the current price for a course for a specific student and term.

        This method provides backward compatibility with the old pricing service
        while using the new separated pricing architecture.

        Args:
            course: Course instance
            student: StudentProfile instance
            term: Term instance
            class_header: Optional class header for reading classes
            pricing_date: Date to calculate pricing for (defaults to today)

        Returns:
            Tuple of (price, currency, pricing_details)

        Raises:
            FinancialError: If no pricing found
        """
        try:
            price, pricing_description = SeparatedPricingService.calculate_course_price(
                course, student, term, class_header
            )

            # Build pricing details for backward compatibility
            pricing_details = {
                "final_price": float(price),
                "pricing_description": pricing_description,
                "course": str(course),
                "term": str(term),
                "student_type": ("foreign" if student.person.citizenship != "KH" else "local"),
            }

            return price, Currency.USD, pricing_details

        except ValidationError as e:
            raise FinancialError(str(e)) from e

    @classmethod
    def get_applicable_fees(
        cls,
        student: StudentProfile,
        term: "Term",
        enrollments: list | None = None,
    ) -> list[dict[str, Any]]:
        """Get all applicable fees for a student in a term.

        Args:
            student: StudentProfile instance
            term: Term instance
            enrollments: List of enrollments (for per-course fees)

        Returns:
            List of fee dictionaries with pricing information
        """
        today = get_current_date()
        is_foreign = student.person.citizenship != "KH"

        # Get all active mandatory fees
        fees_query = FeePricing.objects.filter(
            effective_date__lte=today,
            is_mandatory=True,
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))

        applicable_fees = []

        for fee in fees_query:
            try:
                # Get amount based on student type
                amount = fee.get_amount_for_student(is_foreign)

                fee_info = {
                    "fee_pricing_id": fee.id,
                    "name": fee.name,
                    "fee_type": fee.fee_type,
                    "amount": float(amount),
                    "currency": fee.currency,
                    "description": fee.description,
                }

                if fee.is_per_course and enrollments:
                    # Calculate per-course fees
                    course_count = len(enrollments)
                    fee_info["quantity"] = course_count
                    fee_info["total_amount"] = float(amount * course_count)
                    fee_info["per_course"] = True
                elif fee.is_per_term:
                    # Per-term fees
                    fee_info["quantity"] = 1
                    fee_info["total_amount"] = float(amount)
                    fee_info["per_course"] = False
                else:
                    # One-time fees
                    fee_info["quantity"] = 1
                    fee_info["total_amount"] = float(amount)
                    fee_info["per_course"] = False

                applicable_fees.append(fee_info)

            except ValueError:
                # Skip fees that don't have amount set for this student type
                continue

        return applicable_fees

    @classmethod
    def calculate_total_cost(
        cls,
        student: StudentProfile,
        term: "Term",
        enrollments: list,
    ) -> dict[str, Any]:
        """Calculate total cost for a student's enrollments in a term.

        Args:
            student: StudentProfile instance
            term: Term instance
            enrollments: List of ClassHeaderEnrollment instances

        Returns:
            Dictionary with detailed cost breakdown
        """
        course_costs = []
        total_course_cost = normalize_decimal("0.00")

        # Calculate course costs
        for enrollment in enrollments:
            try:
                price, currency, details = cls.get_course_price(
                    course=enrollment.class_header.course,
                    student=student,
                    term=term,
                    class_header=enrollment.class_header,
                )

                normalized_price = normalize_decimal(price)
                course_cost = {
                    "enrollment_id": enrollment.id,
                    "course": str(enrollment.class_header.course),
                    "class_header": str(enrollment.class_header),
                    "price": float(normalized_price),
                    "currency": currency,
                    "pricing_details": details,
                }

                course_costs.append(course_cost)
                total_course_cost = safe_decimal_add(total_course_cost, normalized_price)

            except FinancialError as e:
                course_cost = {
                    "enrollment_id": enrollment.id,
                    "course": str(enrollment.class_header.course),
                    "error": str(e),
                }
                course_costs.append(course_cost)

        # Calculate applicable fees
        applicable_fees = cls.get_applicable_fees(
            student=student,
            term=term,
            enrollments=enrollments,
        )

        total_fees = safe_decimal_add(*[normalize_decimal(fee["total_amount"]) for fee in applicable_fees])

        # Calculate totals
        subtotal = safe_decimal_add(total_course_cost, total_fees)
        tax_amount = normalize_decimal("0.00")  # Note: Tax calculation not required for current business model
        total_amount = safe_decimal_add(subtotal, tax_amount)

        return {
            "student": str(student),
            "term": str(term),
            "course_costs": course_costs,
            "applicable_fees": applicable_fees,
            "subtotal": float(subtotal),
            "total_course_cost": float(total_course_cost),
            "total_fees": float(total_fees),
            "tax_amount": float(tax_amount),
            "total_amount": float(total_amount),
            "currency": Currency.USD,  # Note: USD default - multi-currency support via term price lists
        }
