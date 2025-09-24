"""Enhanced Reconciliation Service with Scholarship Verification.

This service extends the existing reconciliation system to include scholarship
verification as a new reconciliation tier. It validates scholarship applications
against scholarship records and generates variance reports for audit purposes.
"""

import logging
from datetime import date as datetime_date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.curriculum.models import Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models import (
    Payment,
    ReconciliationAdjustment,
    ReconciliationBatch,
    ReconciliationStatus,
)
from apps.finance.services.reconciliation_service import (
    ReconciliationMatchResult,
    ReconciliationService,
)
from apps.people.models import StudentProfile
from apps.scholarships.models import Scholarship

logger = logging.getLogger(__name__)


class ScholarshipReconciliationService(ReconciliationService):
    """Enhanced reconciliation service with scholarship verification."""

    def __init__(self):
        super().__init__()
        self.scholarship_cache = {}

    def reconcile_payment(self, payment: Payment, batch: ReconciliationBatch | None = None) -> ReconciliationStatus:
        """Reconcile payment with scholarship verification tier."""

        # Get or create reconciliation status
        status, created = ReconciliationStatus.objects.get_or_create(
            payment=payment,
            defaults={
                "reconciliation_batch": batch,
                "status": ReconciliationStatus.Status.UNMATCHED,
            },
        )

        if not created and status.status == ReconciliationStatus.Status.FULLY_RECONCILED:
            return status  # Already reconciled

        try:
            # Tier 1: Perfect matches (existing logic)
            if result := self.try_perfect_match(payment):
                return self._mark_reconciled(
                    status,
                    result,
                    confidence="HIGH",
                    status_value=ReconciliationStatus.Status.FULLY_RECONCILED,
                )

            # Tier 2: Good matches with minor variances (existing logic)
            if result := self.try_good_match(payment):
                if result.variance_percentage and result.variance_percentage <= 5:
                    return self._mark_reconciled(
                        status,
                        result,
                        confidence="HIGH",
                        status_value=ReconciliationStatus.Status.AUTO_ALLOCATED,
                    )

            # Tier 3: NEW - Scholarship verification
            if result := self.try_scholarship_verification(payment):
                confidence = self._calculate_confidence(result)
                return self._mark_reconciled(
                    status,
                    result,
                    confidence=confidence,
                    status_value=ReconciliationStatus.Status.SCHOLARSHIP_VERIFIED,
                )

            # Tier 4: Pattern-based allocation (existing logic)
            if result := self.try_pattern_match(payment):
                confidence = self._calculate_confidence(result)
                return self._mark_reconciled(
                    status,
                    result,
                    confidence=confidence,
                    status_value=ReconciliationStatus.Status.AUTO_ALLOCATED,
                )

            # Tier 5: Mark for manual review
            return self._mark_for_review(status, "No automated match found")

        except Exception as e:
            logger.error(f"Error reconciling payment {payment.payment_reference}: {e}")
            return self._mark_error(status, str(e))

    def try_scholarship_verification(self, payment: Payment) -> ReconciliationMatchResult | None:
        """Verify payment against active scholarship records."""

        # 1. Check if payment has scholarship indicators
        if not self._payment_has_scholarship_indicators(payment):
            return None

        logger.debug(f"Attempting scholarship verification for payment {payment.payment_reference}")

        # 2. Find active scholarships for student in relevant period
        student = payment.invoice.student
        term = payment.invoice.term
        active_scholarships = self._find_active_scholarships(student, term)

        if not active_scholarships:
            # Scholarship indicated but no record found - flag for investigation
            logger.warning(f"Scholarship indicated but no active scholarship record found for student {student}")
            return ReconciliationMatchResult(
                confidence_score=Decimal("30"),
                variance_amount=Decimal("0"),
                match_reason="Scholarship indicated but no active scholarship record found",
                pricing_method=ReconciliationStatus.PricingMethod.SCHOLARSHIP_VERIFICATION,
                error_details={"issue": "MISSING_SCHOLARSHIP_RECORD", "student_id": getattr(student, "pk", None)},
            )

        # 3. Calculate expected vs actual scholarship application
        expected_amount = self._calculate_expected_scholarship_amount(active_scholarships, payment)
        actual_discount = self._calculate_actual_discount_applied(payment)

        variance = abs(actual_discount - expected_amount)
        variance_percentage = (variance / payment.amount * 100) if payment.amount > 0 else Decimal("0")

        # 4. Determine confidence and match quality based on variance
        if variance_percentage <= 1:  # Within 1% tolerance
            confidence_score = Decimal("95")
            match_reason = f"Scholarship application matches expected amount (variance: {variance_percentage:.2f}%)"
        elif variance_percentage <= 5:  # Within 5% tolerance
            confidence_score = Decimal("80")
            match_reason = f"Scholarship application within acceptable variance ({variance_percentage:.2f}%)"
        elif variance_percentage <= 10:  # Within 10% tolerance - needs review
            confidence_score = Decimal("60")
            match_reason = f"Scholarship application has moderate variance ({variance_percentage:.2f}%)"
        else:
            confidence_score = Decimal("40")
            match_reason = f"Scholarship application has significant variance ({variance_percentage:.2f}%)"

        # 5. Get enrollments for context
        enrollments = self._get_student_enrollments(student, term)

        return ReconciliationMatchResult(
            enrollments=list(enrollments),
            confidence_score=confidence_score,
            variance_amount=variance,
            variance_percentage=variance_percentage,
            pricing_method=ReconciliationStatus.PricingMethod.SCHOLARSHIP_VERIFICATION,
            match_reason=match_reason,
            error_details={
                "scholarship_count": len(active_scholarships),
            "scholarship_ids": [getattr(s, "pk", None) for s in active_scholarships],
                "expected_amount": str(expected_amount),
                "actual_discount": str(actual_discount),
            },
        )

    def _payment_has_scholarship_indicators(self, payment: Payment) -> bool:
        """Check if payment has scholarship indicators in notes or other fields."""

        # Check invoice notes for scholarship keywords
        invoice_notes = getattr(payment.invoice, "notes", "") or ""
        payment_notes = getattr(payment, "notes", "") or ""

        combined_notes = (invoice_notes + " " + payment_notes).lower()

        # Scholarship keywords from existing detection logic
        scholarship_keywords = [
            "scholarship",
            "grant",
            "aid",
            "award",
            "sponsor",
            "funded",
            "ngo",
            "foundation",
            "donor",
            "beneficiary",
            "sch.",
            "sponsored",
        ]

        # Check for scholarship indicators
        has_keywords = any(keyword in combined_notes for keyword in scholarship_keywords)

        # Additional check: zero or very low payment amount might indicate scholarship
        has_low_payment = payment.amount <= Decimal("50.00")

        return has_keywords or (has_low_payment and "discount" not in combined_notes)

    def _find_active_scholarships(self, student: StudentProfile, term: Term) -> list[Scholarship]:
        """Find active scholarships for student in the relevant time period."""

        cache_key = f"{getattr(student, 'pk', None)}_{getattr(term, 'pk', None)}"
        if cache_key in self.scholarship_cache:
            return self.scholarship_cache[cache_key]

        # Find scholarships active during the term period
        scholarships = (
            Scholarship.objects.filter(
                student=student,
                status__in=[Scholarship.AwardStatus.APPROVED, Scholarship.AwardStatus.ACTIVE],
                start_date__lte=term.end_date,
            )
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=term.start_date))
            .select_related("cycle")
        )

        # If term has a cycle, prefer scholarships for that cycle
        term_cycle = getattr(term, "cycle", None)
        if term_cycle:
            cycle_scholarships = scholarships.filter(cycle=term_cycle)
            if cycle_scholarships.exists():
                scholarships = cycle_scholarships

        scholarship_list = list(scholarships)
        self.scholarship_cache[cache_key] = scholarship_list

        logger.debug(f"Found {len(scholarship_list)} active scholarships for student {student} in term {term}")
        return scholarship_list

    def _calculate_expected_scholarship_amount(self, scholarships: list[Scholarship], payment: Payment) -> Decimal:
        """Calculate expected scholarship discount amount based on scholarship records."""

        total_discount = Decimal("0")

        for scholarship in scholarships:
            if scholarship.award_percentage:
                # Percentage-based scholarship
                discount = payment.amount * (scholarship.award_percentage / 100)
                total_discount += discount
            elif scholarship.award_amount:
                # Fixed amount scholarship
                total_discount += scholarship.award_amount

        # Cap at payment amount (can't discount more than 100%)
        return min(total_discount, payment.amount)

    def _calculate_actual_discount_applied(self, payment: Payment) -> Decimal:
        """Calculate actual discount applied based on payment data."""

        # This would need to be customized based on how discounts are tracked
        # For now, assume we can get it from invoice line items or payment notes

        # Check if payment has discount information
        # This is a simplified implementation - would need real logic based on data structure
        original_amount = getattr(payment, "original_amount", payment.amount)
        return original_amount - payment.amount

    def _get_student_enrollments(self, student: StudentProfile, term: Term) -> list[ClassHeaderEnrollment]:
        """Get student enrollments for the term."""

        return list(ClassHeaderEnrollment.objects.filter(
            student=student, class_header__term=term, status__in=["ENROLLED", "COMPLETED"]
        ).select_related("class_header__course"))

    def _mark_reconciled(
        self,
        status: ReconciliationStatus,
        result: ReconciliationMatchResult,
        confidence: str,
        status_value: str,
    ) -> ReconciliationStatus:
        """Mark payment as reconciled with scholarship-specific handling."""

        with transaction.atomic():
            # Update reconciliation status
            status.status = status_value
            status.confidence_score = result.confidence_score
            status.confidence_level = confidence
            status.variance_amount = result.variance_amount
            status.variance_percentage = result.variance_percentage
            status.pricing_method_applied = result.pricing_method
            status.reconciled_date = timezone.now()
            status.notes = result.match_reason
            status.save()

            # Set matched enrollments
            if result.enrollments:
                status.matched_enrollments.set(result.enrollments)

            # Create scholarship-specific adjustment if needed
            if result.variance_amount > Decimal("0"):
                self._create_scholarship_adjustment(status, result)

        return status

    def _create_scholarship_adjustment(self, status: ReconciliationStatus, result: ReconciliationMatchResult):
        """Create scholarship-specific reconciliation adjustment."""

        # Determine adjustment type based on error details
        if result.error_details and result.error_details.get("issue") == "MISSING_SCHOLARSHIP_RECORD":
            adjustment_type = ReconciliationAdjustment.AdjustmentType.MISSING_SCHOLARSHIP_RECORD
            description = "Scholarship indicated in payment but no scholarship record found"
        elif result.variance_percentage and result.variance_percentage > 10:
            # Significant variance - likely over or under application
            expected_amount = Decimal(result.error_details.get("expected_amount", "0"))
            actual_discount = Decimal(result.error_details.get("actual_discount", "0"))

            if actual_discount > expected_amount:
                adjustment_type = ReconciliationAdjustment.AdjustmentType.SCHOLARSHIP_OVERAPPLIED
                description = f"Scholarship over-applied by ${result.variance_amount}"
            else:
                adjustment_type = ReconciliationAdjustment.AdjustmentType.SCHOLARSHIP_UNDERAPPLIED
                description = f"Scholarship under-applied by ${result.variance_amount}"
        else:
            # General scholarship variance
            adjustment_type = ReconciliationAdjustment.AdjustmentType.SCHOLARSHIP_VARIANCE
            description = f"Scholarship application variance: {result.match_reason}"

        # Get or create reconciliation GL account
        from apps.finance.models import GLAccount

        recon_account, _ = GLAccount.objects.get_or_create(
            account_code="9999-SCHOLARSHIP-RECON",
            defaults={
                "account_name": "Scholarship Reconciliation Adjustments",
                "account_type": GLAccount.AccountType.ASSET,
                "account_category": GLAccount.AccountCategory.CURRENT_ASSET,
                "description": "Temporary account for scholarship reconciliation adjustments",
            },
        )

        # Create adjustment record
        ReconciliationAdjustment.objects.create(
            gl_account=recon_account,
            adjustment_type=adjustment_type,
            description=description,
            original_amount=status.payment.amount,
            adjusted_amount=status.payment.amount - result.variance_amount,
            variance=result.variance_amount,
            payment=status.payment,
            reconciliation_status=status,
            student=status.payment.invoice.student,
            term=status.payment.invoice.term,
            reconciliation_batch=status.reconciliation_batch,
            requires_approval=result.variance_amount >= Decimal("50.00"),  # Threshold for approval
        )

        logger.info(f"Created scholarship adjustment: {adjustment_type} for ${result.variance_amount}")


class ScholarshipVarianceReporter:
    """Generate variance reports for scholarship discrepancies."""

    @staticmethod
    def generate_daily_variance_report(date: datetime_date) -> dict:
        """Generate daily scholarship variance report."""

        # Get scholarship-related adjustments for the date
        scholarship_adjustments = ReconciliationAdjustment.objects.filter(
            created_at__date=date, adjustment_type__startswith="SCHOLARSHIP"
        ).select_related("payment__invoice__student__person", "reconciliation_status")

        # Categorize variances
        categories: dict[str, list[ReconciliationAdjustment]] = {
            "overapplied": [],
            "underapplied": [],
            "missing_records": [],
            "general_variances": [],
        }

        total_variance_amount = Decimal("0")

        for adjustment in scholarship_adjustments:
            total_variance_amount += abs(adjustment.variance)

            if adjustment.adjustment_type == ReconciliationAdjustment.AdjustmentType.SCHOLARSHIP_OVERAPPLIED:
                categories["overapplied"].append(adjustment)
            elif adjustment.adjustment_type == ReconciliationAdjustment.AdjustmentType.SCHOLARSHIP_UNDERAPPLIED:
                categories["underapplied"].append(adjustment)
            elif adjustment.adjustment_type == ReconciliationAdjustment.AdjustmentType.MISSING_SCHOLARSHIP_RECORD:
                categories["missing_records"].append(adjustment)
            else:
                categories["general_variances"].append(adjustment)

        # Calculate accuracy metrics
        total_scholarship_payments = ReconciliationStatus.objects.filter(
            created_at__date=date, pricing_method_applied=ReconciliationStatus.PricingMethod.SCHOLARSHIP_VERIFICATION
        ).count()

        accuracy_rate = 0.0
        if total_scholarship_payments > 0:
            accurate_payments = total_scholarship_payments - len(scholarship_adjustments)
            accuracy_rate = (accurate_payments / total_scholarship_payments) * 100

        return {
            "date": date.isoformat(),
            "total_variances": scholarship_adjustments.count(),
            "total_variance_amount": float(total_variance_amount),
            "categories": {
                "overapplied": len(categories["overapplied"]),
                "underapplied": len(categories["underapplied"]),
                "missing_records": len(categories["missing_records"]),
                "general_variances": len(categories["general_variances"]),
            },
            "clerk_accuracy_rate": round(accuracy_rate, 2),
            "total_scholarship_payments": total_scholarship_payments,
            "high_priority_items": [
                {
                    "student_name": adj.student.person.full_name if adj.student and adj.student.person else "Unknown",
                    "variance_amount": float(adj.variance),
                    "type": adj.get_adjustment_type_display(),
                    "payment_reference": adj.payment.payment_reference,
                }
                for adj in scholarship_adjustments.filter(variance__gte=100)
            ],
            "recommendations": ScholarshipVarianceReporter._generate_recommendations(categories),
        }

    @staticmethod
    def _generate_recommendations(categories: dict) -> list[str]:
        """Generate recommendations based on variance patterns."""
        recommendations = []

        if len(categories["overapplied"]) > 5:
            recommendations.append(
                "High number of over-applied scholarships - review staff training on scholarship amounts"
            )

        if len(categories["underapplied"]) > 5:
            recommendations.append(
                "High number of under-applied scholarships - verify scholarship records are up to date"
            )

        if len(categories["missing_records"]) > 3:
            recommendations.append(
                "Missing scholarship records detected - ensure all scholarships are properly imported"
            )

        if not recommendations:
            recommendations.append("Scholarship variance rates are within acceptable limits")

        return recommendations
