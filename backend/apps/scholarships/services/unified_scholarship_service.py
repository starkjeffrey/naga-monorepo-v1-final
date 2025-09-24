"""Unified scholarship service for handling both NGO-funded and non-NGO scholarships.

This service provides a single interface for determining scholarship eligibility
and calculating discounts, regardless of whether the scholarship comes from
the Scholarship model (non-NGO) or SponsoredStudent relationship (NGO).

Key features:
- Temporal validation to ensure scholarships match billing periods
- Automatic detection of NGO vs non-NGO scholarships
- Support for both direct payment and bulk invoice modes
- Transparent audit trail for all scholarship decisions
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from django.db import models

from apps.scholarships.models import PaymentMode, Scholarship, Sponsor, SponsoredStudent

if TYPE_CHECKING:
    from apps.curriculum.models import Term
    from apps.people.models import StudentProfile


@dataclass
class ScholarshipBenefit:
    """Unified scholarship benefit information."""

    has_scholarship: bool
    discount_percentage: Decimal
    discount_amount: Decimal | None
    source_type: Literal["NGO", "NON_NGO", "NONE"]
    source_name: str
    payment_mode: str
    sponsor_code: str | None
    scholarship_id: int | None
    sponsored_student_id: int | None
    notes: str

    @property
    def is_ngo_funded(self) -> bool:
        """Check if this is an NGO-funded scholarship."""
        return self.source_type == "NGO"

    @property
    def requires_bulk_invoice(self) -> bool:
        """Check if this scholarship requires bulk invoicing to NGO."""
        return self.is_ngo_funded and self.payment_mode == PaymentMode.BULK_INVOICE


class UnifiedScholarshipService:
    """Service for unified scholarship resolution and calculation."""

    @classmethod
    def get_scholarship_for_term(
        cls,
        student: StudentProfile,
        term: Term,
    ) -> ScholarshipBenefit:
        """Get applicable scholarship for a student in a specific term.

        This is the main entry point for the finance system to determine
        scholarship eligibility. It checks both NGO-funded (via SponsoredStudent)
        and non-NGO scholarships, applying temporal validation to ensure
        the scholarship was active during the term period.

        Args:
            student: Student to check scholarships for
            term: Academic term to validate against

        Returns:
            ScholarshipBenefit with applicable discount information
        """
        # First check for NGO-funded scholarships via SponsoredStudent
        ngo_benefit = cls._check_ngo_scholarship(student, term)
        if ngo_benefit.has_scholarship:
            return ngo_benefit

        # If no NGO scholarship, check for non-NGO scholarships
        non_ngo_benefit = cls._check_non_ngo_scholarship(student, term)
        if non_ngo_benefit.has_scholarship:
            return non_ngo_benefit

        # No applicable scholarship found
        return ScholarshipBenefit(
            has_scholarship=False,
            discount_percentage=Decimal("0.00"),
            discount_amount=None,
            source_type="NONE",
            source_name="None",
            payment_mode=PaymentMode.DIRECT,
            sponsor_code=None,
            scholarship_id=None,
            sponsored_student_id=None,
            notes="No applicable scholarship found for this term",
        )

    @classmethod
    def _check_ngo_scholarship(
        cls,
        student: StudentProfile,
        term: Term,
    ) -> ScholarshipBenefit:
        """Check for NGO-funded scholarships via SponsoredStudent model."""
        # Find active sponsored student relationships during the term
        sponsored_relationships = (
            SponsoredStudent.objects.filter(
                student=student,
                start_date__lte=term.end_date,
            )
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=term.start_date))
            .select_related("sponsor")
            .order_by("-sponsor__default_discount_percentage")
        )

        # Get the best NGO sponsorship (highest discount)
        best_sponsorship = sponsored_relationships.first()
        if not best_sponsorship:
            return ScholarshipBenefit(
                has_scholarship=False,
                discount_percentage=Decimal("0.00"),
                discount_amount=None,
                source_type="NONE",
                source_name="None",
                payment_mode=PaymentMode.DIRECT,
                sponsor_code=None,
                scholarship_id=None,
                sponsored_student_id=None,
                notes="No NGO sponsorship found",
            )

        # Validate sponsor is active and MOU is valid
        sponsor = best_sponsorship.sponsor
        if not sponsor.is_active:
            return cls._no_scholarship("NGO sponsor is inactive")

        if not cls._is_mou_active_during_term(sponsor, term):
            return cls._no_scholarship("NGO MOU not active during term")

        # Return NGO scholarship benefit
        return ScholarshipBenefit(
            has_scholarship=True,
            discount_percentage=sponsor.default_discount_percentage,
            discount_amount=None,  # NGO scholarships use percentage
            source_type="NGO",
            source_name=sponsor.name,
            payment_mode=sponsor.payment_mode,
            sponsor_code=sponsor.code,
            scholarship_id=None,
            sponsored_student_id=best_sponsorship.id,
            notes=f"NGO scholarship from {sponsor.name} ({sponsor.code})",
        )

    @classmethod
    def _check_non_ngo_scholarship(
        cls,
        student: StudentProfile,
        term: Term,
    ) -> ScholarshipBenefit:
        """Check for non-NGO scholarships from Scholarship model."""
        # Find active scholarships during the term
        scholarships = (
            Scholarship.objects.filter(
                student=student,
                status__in=[Scholarship.AwardStatus.APPROVED, Scholarship.AwardStatus.ACTIVE],
                start_date__lte=term.end_date,
            )
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=term.start_date))
            .exclude(sponsored_student__isnull=False)  # Exclude NGO-linked scholarships
        )

        # Get the best scholarship
        best_scholarship = cls._select_best_scholarship(scholarships)
        if not best_scholarship:
            return cls._no_scholarship("No non-NGO scholarship found")

        # Return non-NGO scholarship benefit
        return ScholarshipBenefit(
            has_scholarship=True,
            discount_percentage=best_scholarship.award_percentage or Decimal("0.00"),
            discount_amount=best_scholarship.award_amount,
            source_type="NON_NGO",
            source_name=best_scholarship.name,
            payment_mode=PaymentMode.DIRECT,  # Non-NGO always direct
            sponsor_code=None,
            scholarship_id=best_scholarship.id,
            sponsored_student_id=None,
            notes=f"Individual scholarship: {best_scholarship.name}",
        )

    @classmethod
    def _is_mou_active_during_term(cls, sponsor: Sponsor, term: Term) -> bool:
        """Check if sponsor MOU was active during the term."""
        # MOU must cover at least part of the term
        if term.start_date < sponsor.mou_start_date:
            # Term starts before MOU
            if term.end_date < sponsor.mou_start_date:
                return False  # Term completely before MOU

        if sponsor.mou_end_date:
            if term.start_date > sponsor.mou_end_date:
                return False  # Term completely after MOU

        return True

    @classmethod
    def _select_best_scholarship(cls, scholarships: models.QuerySet) -> Scholarship | None:
        """Select the best scholarship from a queryset."""
        best_scholarship = None
        best_value = Decimal("0.00")

        for scholarship in scholarships:
            # Fixed amounts (monks) always win
            if scholarship.award_amount:
                return scholarship

            # Compare percentages
            if scholarship.award_percentage and scholarship.award_percentage > best_value:
                best_scholarship = scholarship
                best_value = scholarship.award_percentage

        return best_scholarship

    @classmethod
    def _no_scholarship(cls, reason: str) -> ScholarshipBenefit:
        """Return a no-scholarship benefit with reason."""
        return ScholarshipBenefit(
            has_scholarship=False,
            discount_percentage=Decimal("0.00"),
            discount_amount=None,
            source_type="NONE",
            source_name="None",
            payment_mode=PaymentMode.DIRECT,
            sponsor_code=None,
            scholarship_id=None,
            sponsored_student_id=None,
            notes=reason,
        )

    @classmethod
    def calculate_scholarship_discount(
        cls,
        student: StudentProfile,
        term: Term,
        base_tuition_amount: Decimal,
    ) -> dict[str, Decimal | str | bool | None]:
        """Calculate the actual scholarship discount for a billing amount.

        Args:
            student: Student receiving the scholarship
            term: Term for which tuition is being calculated
            base_tuition_amount: Base tuition before any discounts

        Returns:
            Dictionary with discount calculation details
        """
        benefit = cls.get_scholarship_for_term(student, term)

        if not benefit.has_scholarship:
            return {
                "original_amount": base_tuition_amount,
                "discount_amount": Decimal("0.00"),
                "final_amount": base_tuition_amount,
                "discount_source": "none",
                "payment_mode": PaymentMode.DIRECT,
                "sponsor_code": None,
            }

        # Calculate discount amount
        if benefit.discount_amount:
            # Fixed amount discount (monks)
            discount_amount = min(benefit.discount_amount, base_tuition_amount)
        else:
            # Percentage discount
            discount_amount = (base_tuition_amount * benefit.discount_percentage / Decimal("100.00")).quantize(
                Decimal("0.01")
            )

        final_amount = base_tuition_amount - discount_amount

        return {
            "original_amount": base_tuition_amount,
            "discount_amount": discount_amount,
            "final_amount": final_amount,
            "discount_source": benefit.source_type,
            "payment_mode": benefit.payment_mode,
            "sponsor_code": benefit.sponsor_code,
            "scholarship_name": benefit.source_name,
            "requires_bulk_invoice": benefit.requires_bulk_invoice,
        }
