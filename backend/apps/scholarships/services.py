"""Scholarship business logic services.

This module provides business logic services for scholarship management including:
- Unified scholarship resolution (NGO and non-NGO)
- Date-based scholarship validation for billing periods
- NGO bulk operations and portal services
- Transfer mechanisms for dropped NGO students
- Legacy compatibility for existing code

Business rules:
- NGO-funded scholarships use SponsoredStudent relationships
- Non-NGO scholarships use individual Scholarship records
- Scholarships apply only to tuition, never to fees
- Scholarships never stack - only one applies per student
- System automatically selects "best deal" for student
- Fixed amounts only for monks, all others are percentages
- NGOs can use direct payment or bulk invoice modes
"""

import warnings
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from apps.scholarships.models import Scholarship, SponsoredStudent

# Import new unified services
from apps.scholarships.services.ngo_portal_service import NGOPortalService
from apps.scholarships.services.ngo_transfer_service import NGOScholarshipTransferService
from apps.scholarships.services.unified_scholarship_service import (
    ScholarshipBenefit,
    UnifiedScholarshipService,
)

if TYPE_CHECKING:
    from apps.people.models import StudentProfile


# Expose new services at module level for easy access
__all__ = [
    "NGOPortalService",
    "NGOScholarshipTransferService",
    "ScholarshipBenefit",
    # Legacy services (deprecated but kept for compatibility)
    "ScholarshipCalculationService",
    "ScholarshipEligibilityService",
    "ScholarshipReportingService",
    # New unified services
    "UnifiedScholarshipService",
]


# Python 3.13+ Type Aliases
type BestDealResult = dict[str, Scholarship | Decimal | str | None]


class ScholarshipCalculationService:
    """Service for calculating scholarship benefits and selecting best deals.

    DEPRECATED: This service is maintained for backward compatibility only.
    Please use UnifiedScholarshipService for new code, which properly handles
    both NGO-funded and non-NGO scholarships with date-based validation.
    """

    @classmethod
    def get_best_scholarship_for_student(cls, student: "StudentProfile") -> BestDealResult:
        warnings.warn(
            "ScholarshipCalculationService is deprecated. "
            "Use UnifiedScholarshipService.get_scholarship_for_term() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        """Find the best scholarship/discount available for a student.

        Business rule: Only one scholarship applies per student - never stacking.
        System automatically selects the highest benefit available.

        Args:
            student: StudentProfile instance

        Returns:
            Dictionary with best scholarship info and calculated benefit
        """
        # Get all active scholarships for this student
        active_scholarships = cls._get_active_scholarships_for_student(student)

        if not active_scholarships:
            return {
                "scholarship": None,
                "discount_percentage": Decimal("0.00"),
                "discount_type": "none",
                "benefit_source": "none",
                "notes": "No active scholarships available",
            }

        # Calculate benefit for each scholarship and find the best one
        best_scholarship = None
        best_discount = Decimal("0.00")
        best_type = "none"

        for scholarship in active_scholarships:
            discount_info = cls._calculate_scholarship_benefit(scholarship)

            # Compare benefits - higher percentage or fixed amount wins
            if cls._is_better_deal(discount_info["discount_percentage"], best_discount, scholarship):
                best_scholarship = scholarship
                best_discount = discount_info["discount_percentage"]
                best_type = discount_info["discount_type"]

        return {
            "scholarship": best_scholarship,
            "discount_percentage": best_discount,
            "discount_type": best_type,
            "benefit_source": cls._get_benefit_source(best_scholarship),
            "notes": f"Best available from {len(active_scholarships)} option(s)",
        }

    @classmethod
    def _get_active_scholarships_for_student(cls, student: "StudentProfile") -> list[Scholarship]:
        """Get all currently active scholarships for a student."""
        today = timezone.now().date()

        # Get direct scholarships
        direct_scholarships = Scholarship.objects.filter(
            student=student,
            status__in=[
                Scholarship.AwardStatus.APPROVED,
                Scholarship.AwardStatus.ACTIVE,
            ],
            start_date__lte=today,
        ).filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=today))

        # Get sponsored student scholarships
        sponsored_scholarships = (
            Scholarship.objects.filter(
                sponsored_student__student=student,
                sponsored_student__start_date__lte=today,
                status__in=[
                    Scholarship.AwardStatus.APPROVED,
                    Scholarship.AwardStatus.ACTIVE,
                ],
                start_date__lte=today,
            )
            .filter(
                models.Q(sponsored_student__end_date__isnull=True) | models.Q(sponsored_student__end_date__gte=today),
            )
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=today))
        )

        # Combine querysets efficiently using union
        all_scholarships = direct_scholarships.union(sponsored_scholarships)
        return list(all_scholarships)

    @classmethod
    def _calculate_scholarship_benefit(cls, scholarship: Scholarship) -> ScholarshipBenefit:
        """Calculate the benefit provided by a scholarship."""
        if scholarship.award_percentage:
            return {
                "discount_percentage": scholarship.award_percentage,
                "discount_type": "percentage",
                "fixed_amount": None,
            }
        if scholarship.award_amount:
            # Fixed amounts are only for monks - convert to percentage for comparison
            # This is a simplification - in practice, you'd need tuition amount to calculate
            return {
                "discount_percentage": Decimal("100.00"),  # Treat fixed as max for comparison
                "discount_type": "fixed_amount",
                "fixed_amount": scholarship.award_amount,
            }
        return {
            "discount_percentage": Decimal("0.00"),
            "discount_type": "none",
            "fixed_amount": None,
        }

    @classmethod
    def _is_better_deal(cls, new_discount: Decimal, current_best: Decimal, scholarship: Scholarship) -> bool:
        """Determine if a new scholarship is a better deal than the current best."""
        # Fixed amounts (monks) always win if they exist
        if scholarship.award_amount and scholarship.award_amount > 0:
            return True

        # Otherwise, higher percentage wins
        return new_discount > current_best

    @classmethod
    def _get_benefit_source(cls, scholarship: Scholarship | None) -> str:
        """Get a description of where the scholarship benefit comes from."""
        if not scholarship:
            return "none"

        if scholarship.sponsored_student:
            return f"sponsor_{scholarship.sponsored_student.sponsor.code}"
        return f"scholarship_{scholarship.scholarship_type.lower()}"

    @classmethod
    def calculate_tuition_discount(
        cls,
        student: "StudentProfile",
        base_tuition_amount: Decimal,
    ) -> dict[str, Decimal | str]:
        """Calculate the actual tuition discount for a student.

        Args:
            student: StudentProfile instance
            base_tuition_amount: Base tuition before any discounts

        Returns:
            Dictionary with discount details and final amount
        """
        best_deal = cls.get_best_scholarship_for_student(student)

        if not best_deal["scholarship"]:
            return {
                "original_amount": base_tuition_amount,
                "discount_amount": Decimal("0.00"),
                "final_amount": base_tuition_amount,
                "discount_source": "none",
                "discount_percentage": Decimal("0.00"),
            }

        scholarship = best_deal["scholarship"]

        if scholarship.award_amount:
            # Fixed amount (monks only)
            discount_amount = min(scholarship.award_amount, base_tuition_amount)
        else:
            # Percentage discount
            discount_percentage = scholarship.award_percentage or Decimal("0.00")
            discount_amount = (base_tuition_amount * discount_percentage / Decimal("100.00")).quantize(Decimal("0.01"))

        final_amount = base_tuition_amount - discount_amount

        return {
            "original_amount": base_tuition_amount,
            "discount_amount": discount_amount,
            "final_amount": final_amount,
            "discount_source": best_deal["benefit_source"],
            "discount_percentage": scholarship.award_percentage or Decimal("0.00"),
            "scholarship_name": scholarship.name,
        }


class ScholarshipEligibilityService:
    """Service for validating scholarship eligibility and business rules."""

    @classmethod
    def validate_scholarship_eligibility(
        cls,
        student: "StudentProfile",
        scholarship: Scholarship,
    ) -> dict[str, bool | list[str]]:
        """Validate if a student is eligible for a specific scholarship.

        Args:
            student: StudentProfile instance
            scholarship: Scholarship instance

        Returns:
            Dictionary with eligibility status and any issues
        """
        issues = []

        # Check if scholarship is currently active
        if not scholarship.is_currently_active:
            issues.append("Scholarship is not currently active")

        # Check if student already has this scholarship
        if scholarship.student == student:
            # This is the student's scholarship - check for conflicts
            other_active = ScholarshipCalculationService._get_active_scholarships_for_student(student)
            other_active = [s for s in other_active if s.id != scholarship.id]

            if other_active:
                issues.append(f"Student has {len(other_active)} other active scholarship(s) - only one applies")

        # Check sponsored student requirements
        if scholarship.sponsored_student:
            if scholarship.sponsored_student.student != student:
                issues.append("Scholarship is linked to a different student's sponsorship")

            if not scholarship.sponsored_student.is_currently_active:
                issues.append("Associated sponsorship is not currently active")

        # Validate award configuration
        if not scholarship.award_percentage and not scholarship.award_amount:
            issues.append("Scholarship has no award amount or percentage configured")

        if scholarship.award_percentage and scholarship.award_amount:
            issues.append("Scholarship cannot have both percentage and fixed amount")

        return {"is_eligible": len(issues) == 0, "issues": issues}

    @classmethod
    def get_scholarship_conflicts(cls, student: "StudentProfile") -> dict[str, list[Scholarship]]:
        """Identify scholarship conflicts for a student.

        Since scholarships don't stack, having multiple active scholarships
        creates a conflict that needs resolution.

        Args:
            student: StudentProfile instance

        Returns:
            Dictionary categorizing scholarship conflicts
        """
        active_scholarships = ScholarshipCalculationService._get_active_scholarships_for_student(student)

        if len(active_scholarships) <= 1:
            return {
                "has_conflicts": False,
                "active_scholarships": active_scholarships,
                "recommended_action": "none",
            }

        # Multiple scholarships found - this is a conflict
        best_deal = ScholarshipCalculationService.get_best_scholarship_for_student(student)
        best_scholarship = best_deal["scholarship"]

        conflicting_scholarships = [s for s in active_scholarships if s.id != best_scholarship.id]

        return {
            "has_conflicts": True,
            "active_scholarships": active_scholarships,
            "best_scholarship": best_scholarship,
            "conflicting_scholarships": conflicting_scholarships,
            "recommended_action": "suspend_conflicting_scholarships",
            "total_conflicts": len(conflicting_scholarships),
        }


class ScholarshipReportingService:
    """Service for generating scholarship reports for sponsors and administration."""

    @classmethod
    def get_sponsor_scholarship_summary(cls, sponsor_code: str) -> dict:
        """Generate scholarship summary for a specific sponsor.

        Used for NGO reporting and bulk payment coordination.

        Args:
            sponsor_code: Sponsor code (e.g., 'CRST', 'PLF')

        Returns:
            Dictionary with sponsor scholarship statistics
        """
        from apps.scholarships.models import Sponsor

        try:
            sponsor = Sponsor.objects.get(code=sponsor_code)
        except Sponsor.DoesNotExist:
            return {"error": f"Sponsor {sponsor_code} not found"}

        # Get active scholarships directly (optimized single query)
        today = timezone.now().date()
        active_scholarships = (
            Scholarship.objects.filter(
                sponsored_student__sponsor=sponsor,
                sponsored_student__start_date__lte=today,
                status__in=[
                    Scholarship.AwardStatus.APPROVED,
                    Scholarship.AwardStatus.ACTIVE,
                ],
            )
            .filter(
                models.Q(sponsored_student__end_date__isnull=True) | models.Q(sponsored_student__end_date__gte=today),
            )
            .select_related("student__person", "sponsored_student__sponsor")
        )

        # Get sponsored students count efficiently
        active_sponsored_students_count = (
            SponsoredStudent.objects.filter(sponsor=sponsor, start_date__lte=today)
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=today))
            .count()
        )

        # Calculate totals
        total_students = active_sponsored_students_count
        total_scholarships = active_scholarships.count()

        # Categorize by scholarship type and amount
        scholarship_breakdown = {}
        for scholarship in active_scholarships:
            scholarship_type = scholarship.scholarship_type
            if scholarship_type not in scholarship_breakdown:
                scholarship_breakdown[scholarship_type] = {
                    "count": 0,
                    "total_percentage": Decimal("0.00"),
                    "students": [],
                }

            scholarship_breakdown[scholarship_type]["count"] += 1
            if scholarship.award_percentage:
                scholarship_breakdown[scholarship_type]["total_percentage"] += scholarship.award_percentage

            scholarship_breakdown[scholarship_type]["students"].append(
                {
                    "student_id": scholarship.student.student_id,
                    "student_name": scholarship.student.person.full_name,
                    "award": scholarship.award_display,
                },
            )

        return {
            "sponsor": {
                "code": sponsor.code,
                "name": sponsor.name,
                "is_active": sponsor.is_active,
                "is_mou_active": sponsor.is_mou_active,
            },
            "summary": {
                "total_sponsored_students": total_students,
                "total_active_scholarships": total_scholarships,
                "average_discount": sponsor.default_discount_percentage,
            },
            "scholarship_breakdown": scholarship_breakdown,
            "billing_preferences": {
                "consolidated_invoicing": sponsor.requests_consolidated_invoicing,
                "tax_addition": sponsor.requests_tax_addition,
            },
        }
