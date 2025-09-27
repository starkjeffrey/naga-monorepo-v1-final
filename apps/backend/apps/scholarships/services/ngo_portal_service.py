"""Service for NGO portal operations and bulk management.

This service provides functionality for NGOs to manage their sponsored students
efficiently, generate reports, and handle bulk operations. It's designed to
minimize clerical work while providing transparency to NGOs.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models, transaction
from django.utils import timezone

from apps.people.models import StudentProfile
from apps.scholarships.models import PaymentMode, Sponsor, SponsoredStudent

if TYPE_CHECKING:
    from apps.curriculum.models import Term
    from apps.finance.models import Invoice


class NGOPortalService:
    """Service for NGO portal operations and reporting."""

    @classmethod
    def get_ngo_dashboard_data(cls, sponsor_code: str) -> dict:
        """Get comprehensive dashboard data for an NGO sponsor.

        Args:
            sponsor_code: Code of the NGO sponsor

        Returns:
            Dictionary with dashboard data including students, financials, and reports
        """
        try:
            sponsor = Sponsor.objects.get(code=sponsor_code)
        except Sponsor.DoesNotExist:
            return {"error": f"Sponsor {sponsor_code} not found"}

        # Get active sponsored students
        active_students = cls._get_active_sponsored_students(sponsor)

        # Get financial summary
        financial_summary = cls._get_financial_summary(sponsor)

        # Get performance metrics
        performance_metrics = cls._get_student_performance_metrics(sponsor)

        # Get upcoming events
        upcoming_events = cls._get_upcoming_events(sponsor)

        return {
            "sponsor": {
                "code": sponsor.code,
                "name": sponsor.name,
                "payment_mode": sponsor.payment_mode,
                "discount_percentage": sponsor.default_discount_percentage,
                "is_active": sponsor.is_active,
            },
            "students": {
                "active_count": len(active_students),
                "details": active_students,
            },
            "financial_summary": financial_summary,
            "performance_metrics": performance_metrics,
            "upcoming_events": upcoming_events,
            "reporting_preferences": {
                "attendance": sponsor.requests_attendance_reporting,
                "grades": sponsor.requests_grade_reporting,
                "scheduling": sponsor.requests_scheduling_reporting,
            },
        }

    @classmethod
    def _get_active_sponsored_students(cls, sponsor: Sponsor) -> list[dict]:
        """Get list of active sponsored students with details."""
        active_sponsorships = (
            SponsoredStudent.objects.filter(
                sponsor=sponsor,
                start_date__lte=timezone.now().date(),
            )
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now().date()))
            .select_related("student__person", "student__program_enrollment__program")
            .order_by("student__person__family_name_en", "student__person__given_name_en")
        )

        students = []
        for sponsorship in active_sponsorships:
            student = sponsorship.student
            program_enrollment = getattr(student, "program_enrollment", None)

            students.append(
                {
                    "student_id": student.student_id,
                    "name": student.person.full_name,
                    "program": program_enrollment.program.name if program_enrollment else "Not enrolled",
                    "year": program_enrollment.current_year if program_enrollment else None,
                    "gpa": cls._get_student_gpa(student),
                    "attendance_rate": cls._get_attendance_rate(student),
                    "sponsorship_start": sponsorship.start_date,
                    "sponsorship_type": sponsorship.sponsorship_type,
                }
            )

        return students

    @classmethod
    def _get_financial_summary(cls, sponsor: Sponsor) -> dict:
        """Get financial summary for the sponsor."""
        from apps.finance.models import FinancialTransaction

        current_year = timezone.now().year

        # Calculate total sponsored amount this year
        from typing import Any, cast

        sponsor_id = cast("Any", sponsor).id
        yearly_transactions = FinancialTransaction.objects.filter(
            payer_type="SPONSOR",
            payer_id=sponsor_id,
            transaction_date__year=current_year,
            transaction_type="SPONSOR_PAYMENT",
        )

        total_paid = yearly_transactions.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        # Calculate outstanding balance
        pending_transactions = FinancialTransaction.objects.filter(
            payer_type="SPONSOR",
            payer_id=sponsor_id,
            payment_status="PENDING",
        )

        outstanding_balance = pending_transactions.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        # Get active student count
        active_count = sponsor.get_active_sponsored_students_count()

        # Calculate average support per student
        avg_support = total_paid / active_count if active_count > 0 else Decimal("0.00")

        return {
            "current_year": current_year,
            "total_paid_ytd": total_paid,
            "outstanding_balance": outstanding_balance,
            "active_students": active_count,
            "average_support_per_student": avg_support,
            "payment_mode": sponsor.payment_mode,
            "next_invoice_date": cls._get_next_invoice_date(sponsor),
        }

    @classmethod
    def _get_student_performance_metrics(cls, sponsor: Sponsor) -> dict:
        """Get aggregate performance metrics for sponsored students."""
        # This would integrate with grading and attendance systems
        # For now, return sample data structure
        return {
            "average_gpa": Decimal("3.45"),
            "attendance_rate": Decimal("92.5"),
            "graduation_rate": Decimal("87.0"),
            "students_on_probation": 2,
            "students_with_honors": 5,
        }

    @classmethod
    def _get_upcoming_events(cls, sponsor: Sponsor) -> list[dict]:
        """Get upcoming events relevant to the sponsor."""
        events = []

        # Next invoice date
        if sponsor.payment_mode == PaymentMode.BULK_INVOICE:
            next_invoice = cls._get_next_invoice_date(sponsor)
            if next_invoice:
                events.append(
                    {
                        "type": "invoice",
                        "date": next_invoice,
                        "description": "Next bulk invoice generation",
                    }
                )

        # Report generation dates
        if sponsor.requests_grade_reporting:
            # Assume quarterly reports
            events.append(
                {
                    "type": "report",
                    "date": cls._get_next_quarter_end(),
                    "description": "Quarterly grade report",
                }
            )

        return sorted(events, key=lambda x: x["date"])

    @classmethod
    def generate_bulk_invoice(cls, sponsor: Sponsor, term: Term) -> Invoice:
        """Generate consolidated invoice for all sponsored students.

        Args:
            sponsor: NGO sponsor
            term: Academic term to invoice for

        Returns:
            Generated Invoice object
        """
        from apps.finance.services import InvoiceService
        from apps.scholarships.services.unified_scholarship_service import UnifiedScholarshipService

        if sponsor.payment_mode != PaymentMode.BULK_INVOICE:
            raise ValueError(f"Sponsor {sponsor.code} does not use bulk invoicing")

        # Get all active sponsored students
        active_sponsorships = (
            SponsoredStudent.objects.filter(
                sponsor=sponsor,
                start_date__lte=term.end_date,
            )
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=term.start_date))
            .select_related("student")
        )

        # Calculate invoice details
        invoice_lines = []
        total_amount = Decimal("0.00")

        for sponsorship in active_sponsorships:
            student = sponsorship.student

            # Get base tuition for the term
            base_tuition = cls._get_term_tuition(student, term)

            # Calculate discounted amount
            discount_info = UnifiedScholarshipService.calculate_scholarship_discount(student, term, base_tuition)

            # Normalize discount amounts to Decimal for type safety
            discount_amount = Decimal(str(discount_info["discount_amount"]))
            final_amount = Decimal(str(discount_info["final_amount"]))

            # Add to invoice
            invoice_lines.append(
                {
                    "student_id": student.student_id,
                    "student_name": student.person.full_name,
                    "base_amount": base_tuition,
                    "discount_percentage": sponsor.default_discount_percentage,
                    "discount_amount": discount_amount,
                    "net_amount": final_amount,
                }
            )
            total_amount += final_amount

        # Create consolidated invoice
        from typing import Any as _Any
        from typing import cast as _cast

        invoice = _cast("_Any", InvoiceService).create_sponsor_invoice(
            sponsor=sponsor,
            term=term,
            invoice_lines=invoice_lines,
            total_amount=total_amount,
            due_date=cls._calculate_due_date(sponsor),
        )

        return invoice

    @classmethod
    @transaction.atomic
    def bulk_import_sponsored_students(
        cls,
        sponsor_code: str,
        student_data: list[dict],
    ) -> dict:
        """Bulk import sponsored students from CSV or other data source.

        Args:
            sponsor_code: Code of the NGO sponsor
            student_data: List of dictionaries with student information

        Returns:
            Dictionary with import results
        """
        try:
            sponsor = Sponsor.objects.get(code=sponsor_code)
        except Sponsor.DoesNotExist:
            return {"error": f"Sponsor {sponsor_code} not found"}

        successful = 0
        failed = 0
        errors: list[dict[str, str]] = []
        created_sponsorships: list[int] = []

        for row in student_data:
            try:
                # Validate student exists
                student = StudentProfile.objects.get(student_id=row["student_id"])

                # Check for existing sponsorship
                existing = SponsoredStudent.objects.filter(
                    sponsor=sponsor,
                    student=student,
                    end_date__isnull=True,
                ).exists()

                if existing:
                    errors.append(
                        {
                            "student_id": row["student_id"],
                            "error": "Already has active sponsorship",
                        }
                    )
                    failed += 1
                    continue

                # Create sponsorship
                sponsorship = SponsoredStudent.objects.create(
                    sponsor=sponsor,
                    student=student,
                    sponsorship_type=row.get("type", "FULL"),
                    start_date=row.get("start_date", timezone.now().date()),
                    notes=row.get("notes", ""),
                )

                successful += 1
                created_sponsorships.append(sponsorship.id)

            except StudentProfile.DoesNotExist:
                errors.append(
                    {
                        "student_id": row["student_id"],
                        "error": "Student not found",
                    }
                )
                failed += 1
            except Exception as e:
                errors.append(
                    {
                        "student_id": row.get("student_id", "Unknown"),
                        "error": str(e),
                    }
                )
                failed += 1

        return {
            "successful": successful,
            "failed": failed,
            "errors": errors,
            "created_sponsorships": created_sponsorships,
        }

    @classmethod
    def generate_sponsor_report(
        cls,
        sponsor_code: str,
        report_type: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Generate various reports for NGO sponsors.

        Args:
            sponsor_code: Code of the NGO sponsor
            report_type: Type of report (grades, attendance, financial, comprehensive)
            start_date: Report period start
            end_date: Report period end

        Returns:
            Dictionary with report data
        """
        try:
            sponsor = Sponsor.objects.get(code=sponsor_code)
        except Sponsor.DoesNotExist:
            return {"error": f"Sponsor {sponsor_code} not found"}

        if report_type == "grades" and sponsor.requests_grade_reporting:
            return cls._generate_grade_report(sponsor, start_date, end_date)
        elif report_type == "attendance" and sponsor.requests_attendance_reporting:
            return cls._generate_attendance_report(sponsor, start_date, end_date)
        elif report_type == "financial":
            return cls._generate_financial_report(sponsor, start_date, end_date)
        elif report_type == "comprehensive":
            return cls._generate_comprehensive_report(sponsor, start_date, end_date)
        else:
            return {"error": f"Invalid or unauthorized report type: {report_type}"}

    @classmethod
    def _get_student_gpa(cls, student: StudentProfile) -> Decimal | None:
        """Get student's current GPA."""
        # This would integrate with the grading system
        # Placeholder implementation
        return Decimal("3.50")

    @classmethod
    def _get_attendance_rate(cls, student: StudentProfile) -> Decimal | None:
        """Get student's attendance rate."""
        # This would integrate with the attendance system
        # Placeholder implementation
        return Decimal("95.0")

    @classmethod
    def _get_term_tuition(cls, student: StudentProfile, term: Term) -> Decimal:
        """Get base tuition amount for a student in a term."""
        # This would integrate with the finance system
        # Placeholder implementation
        return Decimal("1500.00")

    @classmethod
    def _get_next_invoice_date(cls, sponsor: Sponsor) -> date | None:
        """Calculate next invoice generation date."""
        if sponsor.payment_mode != PaymentMode.BULK_INVOICE:
            return None

        # Logic based on billing cycle
        today = timezone.now().date()

        if sponsor.billing_cycle == "MONTHLY":
            # Next month on invoice_generation_day
            from datetime import timedelta

            next_month = today.replace(day=1) + timedelta(days=32)
            return next_month.replace(day=sponsor.invoice_generation_day or 1)
        elif sponsor.billing_cycle == "TERM":
            # Would need to check academic calendar
            from datetime import timedelta

            return today + timedelta(days=90)

        return None

    @classmethod
    def _calculate_due_date(cls, sponsor: Sponsor) -> date:
        """Calculate invoice due date based on payment terms."""
        from datetime import timedelta

        return timezone.now().date() + timedelta(days=sponsor.payment_terms_days)

    @classmethod
    def _get_next_quarter_end(cls) -> date:
        """Get next quarter end date."""
        today = timezone.now().date()
        quarter = (today.month - 1) // 3 + 1

        if quarter == 4:
            return date(today.year + 1, 3, 31)
        else:
            return date(today.year, (quarter + 1) * 3, 31 if quarter != 1 else 30)

    @classmethod
    def _generate_grade_report(cls, sponsor: Sponsor, start_date: date, end_date: date) -> dict:
        """Generate grade report for sponsored students."""
        # Placeholder - would integrate with grading system
        return {
            "report_type": "grades",
            "sponsor": sponsor.name,
            "period": f"{start_date} to {end_date}",
            "generated_at": timezone.now(),
            "data": "Grade report data would go here",
        }

    @classmethod
    def _generate_attendance_report(cls, sponsor: Sponsor, start_date: date, end_date: date) -> dict:
        """Generate attendance report for sponsored students."""
        # Placeholder - would integrate with attendance system
        return {
            "report_type": "attendance",
            "sponsor": sponsor.name,
            "period": f"{start_date} to {end_date}",
            "generated_at": timezone.now(),
            "data": "Attendance report data would go here",
        }

    @classmethod
    def _generate_financial_report(cls, sponsor: Sponsor, start_date: date, end_date: date) -> dict:
        """Generate financial report for sponsor."""
        # Placeholder - would integrate with finance system
        return {
            "report_type": "financial",
            "sponsor": sponsor.name,
            "period": f"{start_date} to {end_date}",
            "generated_at": timezone.now(),
            "data": "Financial report data would go here",
        }

    @classmethod
    def _generate_comprehensive_report(cls, sponsor: Sponsor, start_date: date, end_date: date) -> dict:
        """Generate comprehensive report combining all data."""
        return {
            "report_type": "comprehensive",
            "sponsor": sponsor.name,
            "period": f"{start_date} to {end_date}",
            "generated_at": timezone.now(),
            "sections": {
                "grades": cls._generate_grade_report(sponsor, start_date, end_date),
                "attendance": cls._generate_attendance_report(sponsor, start_date, end_date),
                "financial": cls._generate_financial_report(sponsor, start_date, end_date),
            },
        }
