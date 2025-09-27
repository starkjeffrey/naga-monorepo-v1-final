"""Finance integration for scholarships app.

This module provides integration between scholarships and the finance system,
following clean architecture principles with minimal coupling between apps.

Key functions:
- Calculate scholarship discounts for invoicing
- Handle NGO bulk payment coordination
- Provide scholarship data for financial reporting
- Maintain separation between scholarship logic and billing logic

Business rules:
- Scholarships apply only to tuition, never fees
- Only one scholarship per student (non-stacking)
- NGOs receive consolidated invoices for their students
- Standard processing for all students (estimates, invoices, etc.)
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from django.db import models, transaction
from django.utils import timezone

# Avoid strict binding to scholarship services at type-check time; import lazily in methods

if TYPE_CHECKING:
    from apps.people.models import StudentProfile


class ScholarshipFinanceIntegrationService:
    """Service for integrating scholarship data with finance operations.

    This service acts as the bridge between scholarship business logic
    and finance app operations, maintaining clean separation of concerns.
    """

    @classmethod
    def calculate_student_tuition_discount(
        cls,
        student: "StudentProfile",
        base_tuition_amount: Decimal,
    ) -> dict[str, Decimal | str | bool]:
        """Calculate tuition discount for a student based on active scholarships.

        This is the primary integration point called by the finance app
        when generating estimates and invoices.

        Args:
            student: StudentProfile instance
            base_tuition_amount: Base tuition before scholarships

        Returns:
            Dictionary with discount information for finance processing
        """
        from apps.scholarships import services as _sch_services

        discount_info = cast("Any", _sch_services).ScholarshipCalculationService.calculate_tuition_discount(
            student, base_tuition_amount
        )

        # Add finance-specific metadata
        discount_info.update(
            {
                "has_discount": discount_info["discount_amount"] > Decimal("0.00"),
                "applies_to_fees": False,  # Scholarships never apply to fees
                "requires_special_billing": cls._check_special_billing_requirements(student),
                "ngo_billing_info": cls._get_ngo_billing_info(student),
            },
        )

        return discount_info

    @classmethod
    def _check_special_billing_requirements(cls, student: "StudentProfile") -> bool:
        """Check if student requires special billing handling (NGO bulk payment)."""
        from apps.scholarships.models import SponsoredStudent

        # Use custom manager to get active sponsorships with consolidated billing
        active_sponsorships = SponsoredStudent.objects.get_active_for_student(student).filter(
            sponsor__requests_consolidated_invoicing=True,
            sponsor__is_active=True,
        )

        return active_sponsorships.exists()

    @classmethod
    def _get_ngo_billing_info(cls, student: "StudentProfile") -> dict[str, str | bool] | None:
        """Get NGO billing information for special payment handling."""
        from apps.scholarships.models import SponsoredStudent

        # Use custom manager to find active sponsorship with consolidated billing
        active_sponsorship = (
            SponsoredStudent.objects.get_active_for_student(student)
            .filter(
                sponsor__requests_consolidated_invoicing=True,
                sponsor__is_active=True,
            )
            .select_related("sponsor")
            .first()
        )

        if not active_sponsorship:
            return None

        sponsor = active_sponsorship.sponsor

        return {
            "sponsor_code": sponsor.code,
            "sponsor_name": sponsor.name,
            "billing_email": sponsor.billing_email,
            "consolidated_invoicing": True,
            "add_tax": sponsor.requests_tax_addition,
            "billing_contact": sponsor.contact_email or sponsor.billing_email,
        }

    @classmethod
    def get_students_for_consolidated_billing(cls, sponsor_code: str) -> list[dict]:
        """Get list of students for NGO consolidated billing.

        Used by finance app to generate consolidated invoices for sponsors.

        Args:
            sponsor_code: Sponsor code (e.g., 'CRST', 'PLF')

        Returns:
            List of student billing information for consolidated invoice
        """
        from apps.scholarships.models import Sponsor, SponsoredStudent

        try:
            sponsor = Sponsor.objects.get(code=sponsor_code, is_active=True, requests_consolidated_invoicing=True)
        except Sponsor.DoesNotExist:
            return []

        today = timezone.now().date()

        # Get active sponsored students
        sponsored_students = (
            SponsoredStudent.objects.filter(sponsor=sponsor, start_date__lte=today)
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=today))
            .select_related("student__person")
            .order_by("student__person__family_name")
        )

        # Pre-fetch scholarship data to avoid N+1 queries
        from apps.scholarships.models import Scholarship

        student_ids_with_scholarships = set(
            Scholarship.objects.filter(
                student__in=[s.student for s in sponsored_students],
                status__in=[
                    Scholarship.AwardStatus.ACTIVE,
                    Scholarship.AwardStatus.APPROVED,
                ],
            ).values_list("student_id", flat=True),
        )

        billing_students = []

        for sponsored_student in sponsored_students:
            student = sponsored_student.student

            # Get scholarship discount information
            # Note: This would typically receive base_tuition_amount from finance app
            # For now, we'll return the structure without calculating actual amounts

            billing_students.append(
                {
                    "student_id": student.student_id,
                    "student_name": student.person.full_name,
                    "person_id": student.person.id,
                    "sponsorship_type": sponsored_student.sponsorship_type,
                    "sponsorship_start": sponsored_student.start_date,
                    "has_scholarship_discount": student.id in student_ids_with_scholarships,
                    # Finance app calls calculate_student_tuition_discount
                    "discount_info": "calculated_by_finance_app",
                },
            )

        return billing_students

    @classmethod
    def _student_has_active_scholarship(cls, student: "StudentProfile") -> bool:
        """Quick check if student has any active scholarship."""
        from apps.scholarships import services as _sch_services

        active_scholarships = cast(
            "Any", _sch_services
        ).ScholarshipCalculationService._get_active_scholarships_for_student(student)
        return len(active_scholarships) > 0

    @classmethod
    def get_sponsor_billing_preferences(cls, sponsor_code: str) -> dict[str, bool | str] | None:
        """Get sponsor billing preferences for finance processing.

        Args:
            sponsor_code: Sponsor code

        Returns:
            Dictionary with billing preferences or None if sponsor not found
        """
        from apps.scholarships.models import Sponsor

        try:
            sponsor = Sponsor.objects.get(code=sponsor_code, is_active=True)
        except Sponsor.DoesNotExist:
            return None

        return {
            "consolidated_invoicing": sponsor.requests_consolidated_invoicing,
            "add_tax": sponsor.requests_tax_addition,
            "billing_email": sponsor.billing_email,
            "contact_email": sponsor.contact_email,
            "sponsor_name": sponsor.name,
            "is_mou_active": sponsor.is_mou_active,
        }

    @classmethod
    @transaction.atomic
    def handle_scholarship_status_change(
        cls,
        scholarship_id: int,
        old_status: str,
        new_status: str,
        changed_by_user_id: int,
    ) -> dict[str, bool | str]:
        """Handle scholarship status changes that may affect billing.

        Called when scholarship status changes to update any related
        financial records or trigger billing updates.

        Args:
            scholarship_id: ID of changed scholarship
            old_status: Previous status
            new_status: New status
            changed_by_user_id: User who made the change

        Returns:
            Dictionary with processing results
        """
        from apps.scholarships.models import Scholarship

        try:
            scholarship = Scholarship.objects.select_related("student__person", "sponsored_student__sponsor").get(
                id=scholarship_id,
            )
        except Scholarship.DoesNotExist:
            return {"success": False, "error": "Scholarship not found"}

        # Check if this is a status change that affects billing
        billing_affecting_statuses = [
            Scholarship.AwardStatus.APPROVED,
            Scholarship.AwardStatus.ACTIVE,
            Scholarship.AwardStatus.SUSPENDED,
            Scholarship.AwardStatus.CANCELLED,
        ]

        affects_billing = old_status in billing_affecting_statuses or new_status in billing_affecting_statuses

        if not affects_billing:
            return {"success": True, "action": "no_billing_impact"}

        # Log the change for audit purposes
        cls._log_scholarship_billing_change(scholarship, old_status, new_status, changed_by_user_id)

        # Check for scholarship conflicts (multiple active scholarships)
        from apps.scholarships import services as _sch_services

        conflicts = cast("Any", _sch_services).ScholarshipCalculationService.get_scholarship_conflicts(
            scholarship.student
        )

        result = {
            "success": True,
            "action": "billing_affected",
            "student_id": scholarship.student.student_id,
            "has_conflicts": conflicts["has_conflicts"],
            "ngo_billing": cls._check_special_billing_requirements(scholarship.student),
        }

        if conflicts["has_conflicts"]:
            result["conflicts"] = {
                "total": conflicts["total_conflicts"],
                "recommended_action": conflicts["recommended_action"],
            }

        return result

    @classmethod
    def _log_scholarship_billing_change(
        cls,
        scholarship,
        old_status: str,
        new_status: str,
        changed_by_user_id: int,
    ) -> None:
        """Log scholarship changes that affect billing for audit trail."""
        # This would integrate with the audit logging system
        # For now, we'll use a simple approach

        from django.contrib.auth import get_user_model

        from apps.people.models import PersonEventLog

        User = get_user_model()

        try:
            changed_by = User.objects.get(id=changed_by_user_id)
        except User.DoesNotExist:
            return

        PersonEventLog.objects.create(
            person=scholarship.student.person,
            action=PersonEventLog.ActionType.OTHER,
            changed_by=changed_by,
            details={
                "action_type": "scholarship_status_change",
                "scholarship_id": scholarship.id,
                "scholarship_name": scholarship.name,
                "old_status": old_status,
                "new_status": new_status,
                "billing_impact": True,
                "timestamp": timezone.now().isoformat(),
            },
            notes=(
                f"Scholarship '{scholarship.name}' status changed from {old_status} to {new_status} - billing impact"
            ),
        )

    @classmethod
    def generate_scholarship_financial_report(cls, date_from=None, date_to=None) -> dict:
        """Generate financial report for scholarship impacts.

        Used for institutional reporting and financial analysis.

        Args:
            date_from: Start date for report (optional)
            date_to: End date for report (optional)

        Returns:
            Dictionary with financial impact analysis
        """
        from apps.scholarships.models import Scholarship

        if not date_from:
            date_from = timezone.now().date().replace(month=1, day=1)  # Start of year
        if not date_to:
            date_to = timezone.now().date()

        # Get active scholarships in date range
        active_scholarships = (
            Scholarship.objects.filter(
                status__in=[
                    Scholarship.AwardStatus.APPROVED,
                    Scholarship.AwardStatus.ACTIVE,
                ],
                start_date__lte=date_to,
            )
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=date_from))
            .select_related("student__person", "sponsored_student__sponsor")
        )

        # Categorize by type and sponsor
        report = {
            "report_period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
            "summary": {
                "total_scholarships": active_scholarships.count(),
                "sponsored_scholarships": 0,
                "independent_scholarships": 0,
                "total_students_affected": 0,
            },
            "by_sponsor": {},
            "by_type": {},
            "discount_analysis": {
                "percentage_based": 0,
                "fixed_amount": 0,
                "total_percentage_points": Decimal("0.00"),
            },
        }

        students_affected = set()

        for scholarship in active_scholarships:
            students_affected.add(scholarship.student.id)

            # Categorize by sponsor vs independent
            if scholarship.sponsored_student:
                report["summary"]["sponsored_scholarships"] += 1
                sponsor_code = scholarship.sponsored_student.sponsor.code

                if sponsor_code not in report["by_sponsor"]:
                    report["by_sponsor"][sponsor_code] = {
                        "name": scholarship.sponsored_student.sponsor.name,
                        "count": 0,
                        "students": [],
                    }

                report["by_sponsor"][sponsor_code]["count"] += 1
                report["by_sponsor"][sponsor_code]["students"].append(
                    {
                        "student_id": scholarship.student.student_id,
                        "student_name": scholarship.student.person.full_name,
                        "award": scholarship.award_display,
                    },
                )
            else:
                report["summary"]["independent_scholarships"] += 1

            # Categorize by scholarship type
            scholarship_type = scholarship.scholarship_type
            if scholarship_type not in report["by_type"]:
                report["by_type"][scholarship_type] = 0
            report["by_type"][scholarship_type] += 1

            # Analyze discount structure
            if scholarship.award_percentage:
                report["discount_analysis"]["percentage_based"] += 1
                report["discount_analysis"]["total_percentage_points"] += scholarship.award_percentage
            elif scholarship.award_amount:
                report["discount_analysis"]["fixed_amount"] += 1

        report["summary"]["total_students_affected"] = len(students_affected)

        if report["discount_analysis"]["percentage_based"] > 0:
            avg_percentage = (
                report["discount_analysis"]["total_percentage_points"]
                / report["discount_analysis"]["percentage_based"]
            ).quantize(Decimal("0.01"))
            report["discount_analysis"]["average_percentage"] = avg_percentage

        return report
