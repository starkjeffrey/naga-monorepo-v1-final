"""Enhanced Reconciliation Service with Price Determination Engine.

This service extends the base reconciliation service to use the price
determination engine for more accurate matching based on the business
rules in BA Academic Pricing and LANGUAGE.pdf.
"""

import logging
from collections import defaultdict
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from apps.curriculum.models import Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models import (
    MaterialityThreshold,
    Payment,
    ReconciliationAdjustment,
    ReconciliationBatch,
    ReconciliationStatus,
)
from apps.finance.services.price_determination_engine import (
    PriceDeterminationEngine,
    PriceType,
)
from apps.people.models import StudentProfile

logger = logging.getLogger(__name__)


class EnhancedReconciliationService:
    """Enhanced reconciliation service using price determination engine."""

    def __init__(self):
        self.price_engine = PriceDeterminationEngine()
        self.materiality_threshold = None

    def reconcile_payment(self, payment: Payment, batch: ReconciliationBatch | None = None) -> ReconciliationStatus:
        """Reconcile a payment using the price determination engine."""

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
            # Get student and term from payment
            student = payment.invoice.student
            term = payment.invoice.term

            # Handle dropped courses first
            result = self._try_dropped_course_match(payment, student, term)
            if result:
                return self._update_status(status, result)

            # Get all enrollments for the student in the term
            enrollments = self._get_student_enrollments(student, term)

            if not enrollments:
                return self._mark_unmatched(status, "No enrollments found for student in term")

            # Try exact match first
            result = self._try_exact_match(payment, student, term, enrollments)
            if result:
                return self._update_status(status, result)

            # Try combination matches
            result = self._try_combination_match(payment, student, term, enrollments)
            if result:
                return self._update_status(status, result)

            # Try senior project tier matching
            result = self._try_senior_project_match(payment, student, term, enrollments)
            if result:
                return self._update_status(status, result)

            # Try partial match with variance
            result = self._try_partial_match(payment, student, term, enrollments)
            if result:
                return self._update_status(status, result)

            # No match found
            return self._mark_unmatched(status, "No matching enrollment combination found")

        except Exception as e:
            logger.error(f"Error reconciling payment {payment.payment_reference}: {e}")
            return self._mark_error(status, str(e))

    def _get_student_enrollments(
        self, student: StudentProfile, term: Term, include_dropped: bool = False
    ) -> list[ClassHeaderEnrollment]:
        """Get all enrollments for a student in a term."""

        query = ClassHeaderEnrollment.objects.filter(student=student, class_header__term=term)

        if not include_dropped:
            # Only include Normal attendance (not Drop)
            query = query.exclude(Q(attendance_status="Drop") | Q(status="DROPPED"))

        return list(query.select_related("class_header__course", "class_header__term"))

    def _try_dropped_course_match(self, payment: Payment, student: StudentProfile, term: Term) -> dict | None:
        """Check if payment is zero due to all dropped courses."""

        if payment.amount != Decimal("0"):
            return None

        # Get dropped enrollments
        dropped = ClassHeaderEnrollment.objects.filter(student=student, class_header__term=term).filter(
            Q(attendance_status="Drop") | Q(status="DROPPED")
        )

        if dropped.exists():
            return {
                "status": ReconciliationStatus.Status.FULLY_RECONCILED,
                "confidence": Decimal("100"),
                "pricing_method": ReconciliationStatus.PricingMethod.DEFAULT_PRICING,
                "matched_enrollments": list(dropped),
                "variance_amount": Decimal("0"),
                "notes": f"All {dropped.count()} courses dropped - no payment required",
            }

        return None

    def _try_exact_match(
        self,
        payment: Payment,
        student: StudentProfile,
        term: Term,
        enrollments: list[ClassHeaderEnrollment],
    ) -> dict | None:
        """Try to find exact match using price determination."""

        # Get pricing for all enrollments
        pricing_results = self.price_engine.determine_student_pricing(student, term, enrollments)

        # Calculate total
        total_expected = sum(r.total_price for r in pricing_results)

        # Check for exact match (within $1 for rounding)
        variance = abs(payment.amount - total_expected)

        if variance <= Decimal("1.00"):
            # Determine pricing method
            pricing_methods = {r.price_type for r in pricing_results}
            if len(pricing_methods) == 1:
                method_map = {
                    PriceType.DEFAULT: ReconciliationStatus.PricingMethod.DEFAULT_PRICING,
                    PriceType.FIXED: ReconciliationStatus.PricingMethod.FIXED_PRICING,
                    PriceType.SENIOR_PROJECT: ReconciliationStatus.PricingMethod.SENIOR_PROJECT,
                    PriceType.READING_CLASS: ReconciliationStatus.PricingMethod.READING_CLASS,
                }
                pricing_method = method_map.get(
                    pricing_methods.pop(),
                    ReconciliationStatus.PricingMethod.DEFAULT_PRICING,
                )
            else:
                pricing_method = ReconciliationStatus.PricingMethod.HYBRID_MATCH

            return {
                "status": ReconciliationStatus.Status.FULLY_RECONCILED,
                "confidence": Decimal("100"),
                "pricing_method": pricing_method,
                "matched_enrollments": enrollments,
                "variance_amount": variance,
                "variance_percentage": ((variance / payment.amount * 100) if payment.amount > 0 else Decimal("0")),
                "notes": f"Exact match: {len(enrollments)} courses = ${total_expected}",
            }

        return None

    def _try_combination_match(
        self,
        payment: Payment,
        student: StudentProfile,
        term: Term,
        enrollments: list[ClassHeaderEnrollment],
    ) -> dict | None:
        """Try different combinations of courses to match payment."""

        # Group enrollments by pricing type
        grouped = defaultdict(list)
        for enrollment in enrollments:
            price_type = self.price_engine._determine_price_type(enrollment, term)
            grouped[price_type].append(enrollment)

        # Start with default-priced courses as they're most predictable
        if PriceType.DEFAULT in grouped:
            default_courses = grouped[PriceType.DEFAULT]

            # Try dividing payment by default price to get course count
            pricing_results = self.price_engine.determine_student_pricing(
                student,
                term,
                default_courses[:1],  # Get one course to find unit price
            )

            if pricing_results:
                unit_price = pricing_results[0].unit_price
                if unit_price > 0:
                    # Calculate how many courses at default price
                    implied_count = payment.amount / unit_price

                    # Check if it's a whole number (within tolerance)
                    if abs(implied_count - round(implied_count)) < 0.1:
                        course_count = round(implied_count)

                        # Try to find that many courses
                        if course_count <= len(enrollments):
                            # Prioritize default-priced courses
                            selected = default_courses[:course_count]

                            # Add other courses if needed
                            if len(selected) < course_count:
                                for price_type in [
                                    PriceType.FIXED,
                                    PriceType.READING_CLASS,
                                ]:
                                    if price_type in grouped:
                                        remaining = course_count - len(selected)
                                        selected.extend(grouped[price_type][:remaining])

                            # Verify the match
                            pricing_results = self.price_engine.determine_student_pricing(student, term, selected)
                            total = sum(r.total_price for r in pricing_results)
                            variance = abs(payment.amount - total)

                            if variance <= Decimal("5.00"):  # Within $5
                                return {
                                    "status": ReconciliationStatus.Status.AUTO_ALLOCATED,
                                    "confidence": Decimal("90"),
                                    "pricing_method": ReconciliationStatus.PricingMethod.DEFAULT_PRICING,
                                    "matched_enrollments": selected,
                                    "variance_amount": variance,
                                    "variance_percentage": (
                                        (variance / payment.amount * 100) if payment.amount > 0 else Decimal("0")
                                    ),
                                    "notes": f"Matched {course_count} courses at default pricing",
                                }

        return None

    def _try_senior_project_match(
        self,
        payment: Payment,
        student: StudentProfile,
        term: Term,
        enrollments: list[ClassHeaderEnrollment],
    ) -> dict | None:
        """Try to match senior project courses with tier detection."""

        # Find senior project enrollments
        senior_projects = [e for e in enrollments if self.price_engine._is_senior_project(e.class_header.course)]

        if not senior_projects:
            return None

        # For each senior project, try to determine tier by payment amount
        best_match = None
        best_variance = Decimal("999999")

        for sp_enrollment in senior_projects:
            # Get other non-senior project enrollments
            other_enrollments = [e for e in enrollments if e != sp_enrollment]

            # Calculate price for other courses
            if other_enrollments:
                other_pricing = self.price_engine.determine_student_pricing(student, term, other_enrollments)
                other_total = sum(r.total_price for r in other_pricing)
            else:
                other_total = Decimal("0")

            # Remaining amount should be for senior project
            sp_amount = payment.amount - other_total

            # Try to match tier
            is_foreign = self.price_engine._is_foreign_student(student)
            tier_result = self.price_engine.attempt_senior_project_tier_match(
                sp_enrollment, sp_amount, term, is_foreign
            )

            if tier_result:
                # Calculate total with this tier
                total = other_total + tier_result.total_price
                variance = abs(payment.amount - total)

                if variance < best_variance:
                    best_variance = variance
                    best_match = {
                        "status": ReconciliationStatus.Status.AUTO_ALLOCATED,
                        "confidence": tier_result.confidence,
                        "pricing_method": ReconciliationStatus.PricingMethod.SENIOR_PROJECT,
                        "matched_enrollments": enrollments,
                        "variance_amount": variance,
                        "variance_percentage": (
                            (variance / payment.amount * 100) if payment.amount > 0 else Decimal("0")
                        ),
                        "notes": (
                            f"Senior project {tier_result.courses_priced[0]['tier']} + "
                            f"{len(other_enrollments)} other courses"
                        ),
                    }

        # Return best match if variance is acceptable
        if best_match and best_variance <= Decimal("10.00"):
            return best_match

        return None

    def _try_partial_match(
        self,
        payment: Payment,
        student: StudentProfile,
        term: Term,
        enrollments: list[ClassHeaderEnrollment],
    ) -> dict | None:
        """Try partial match with acceptable variance."""

        # Get pricing for all enrollments
        pricing_results = self.price_engine.determine_student_pricing(student, term, enrollments)

        total_expected = sum(r.total_price for r in pricing_results)
        variance = abs(payment.amount - total_expected)
        variance_percentage = (variance / payment.amount * 100) if payment.amount > 0 else Decimal("0")

        # Check if variance is within acceptable range
        threshold = self._get_materiality_threshold()

        if variance <= threshold or variance_percentage <= 10:  # 10% or threshold
            # Calculate confidence based on variance
            if variance_percentage <= 2:
                confidence = Decimal("95")
            elif variance_percentage <= 5:
                confidence = Decimal("85")
            elif variance_percentage <= 10:
                confidence = Decimal("75")
            else:
                confidence = Decimal("60")

            return {
                "status": ReconciliationStatus.Status.AUTO_ALLOCATED,
                "confidence": confidence,
                "pricing_method": ReconciliationStatus.PricingMethod.DEFAULT_PRICING,
                "matched_enrollments": enrollments,
                "variance_amount": variance,
                "variance_percentage": variance_percentage,
                "notes": f"Partial match with {variance_percentage:.1f}% variance",
            }

        return None

    def _get_materiality_threshold(self) -> Decimal:
        """Get the materiality threshold for reconciliation."""

        if not self.materiality_threshold:
            threshold = MaterialityThreshold.get_threshold(MaterialityThreshold.ThresholdContext.INDIVIDUAL_PAYMENT)
            self.materiality_threshold = threshold.absolute_threshold if threshold else Decimal("50.00")

        return self.materiality_threshold

    def _update_status(self, status: ReconciliationStatus, result: dict) -> ReconciliationStatus:
        """Update reconciliation status with results."""

        status.status = result["status"]
        status.confidence_score = result["confidence"]
        status.confidence_level = self._get_confidence_level(result["confidence"])
        status.pricing_method_applied = result["pricing_method"]
        status.variance_amount = result["variance_amount"]
        status.variance_percentage = result.get("variance_percentage")
        status.notes = result["notes"]
        status.reconciled_date = timezone.now()

        # Clear and add matched enrollments
        status.matched_enrollments.clear()
        status.matched_enrollments.add(*result["matched_enrollments"])

        status.save()

        # Create adjustment if there's a variance
        if result["variance_amount"] > Decimal("0.01"):
            self._create_adjustment(status, result)

        return status

    def _get_confidence_level(self, score: Decimal) -> str:
        """Convert confidence score to level."""
        if score >= 95:
            return ReconciliationStatus.ConfidenceLevel.HIGH
        elif score >= 80:
            return ReconciliationStatus.ConfidenceLevel.MEDIUM
        elif score > 0:
            return ReconciliationStatus.ConfidenceLevel.LOW
        else:
            return ReconciliationStatus.ConfidenceLevel.NONE

    def _create_adjustment(self, status: ReconciliationStatus, result: dict) -> ReconciliationAdjustment:
        """Create reconciliation adjustment for variance."""

        # Determine adjustment type
        if result["variance_percentage"] and result["variance_percentage"] <= 2:
            adj_type = ReconciliationAdjustment.AdjustmentType.PRICING_VARIANCE
        elif "dropped" in result["notes"].lower():
            adj_type = ReconciliationAdjustment.AdjustmentType.MISSING_ENROLLMENT
        else:
            adj_type = ReconciliationAdjustment.AdjustmentType.CLERICAL_ERROR

        adjustment = ReconciliationAdjustment.objects.create(
            gl_account_id=self._get_reconciliation_gl_account(),
            adjustment_type=adj_type,
            description=f"Reconciliation variance: {result['notes']}",
            original_amount=status.payment.amount,
            adjusted_amount=status.payment.amount - result["variance_amount"],
            variance=result["variance_amount"],
            payment=status.payment,
            reconciliation_status=status,
            student=status.payment.invoice.student,
            term=status.payment.invoice.term,
            reconciliation_batch=status.reconciliation_batch,
            requires_approval=result["variance_amount"] > self._get_materiality_threshold(),
        )

        return adjustment

    def _mark_unmatched(self, status: ReconciliationStatus, reason: str) -> ReconciliationStatus:
        """Mark a payment as unmatched."""

        status.status = ReconciliationStatus.Status.UNMATCHED
        status.confidence_score = Decimal("0")
        status.confidence_level = ReconciliationStatus.ConfidenceLevel.NONE
        status.notes = reason
        status.save()

        return status

    def _mark_error(self, status: ReconciliationStatus, error: str) -> ReconciliationStatus:
        """Mark a payment with an error."""

        status.status = ReconciliationStatus.Status.EXCEPTION_ERROR
        status.confidence_score = Decimal("0")
        status.confidence_level = ReconciliationStatus.ConfidenceLevel.NONE
        status.error_category = "SYSTEM_ERROR"
        status.error_details = {"error": error}
        status.notes = f"Error: {error}"
        status.save()

        return status

    @classmethod
    def _get_reconciliation_gl_account(cls) -> int:
        """Get the GL account ID for reconciliation adjustments.

        Returns:
            The GL account ID to use for reconciliation adjustments.

        Note:
            In a production system, this would be configurable or looked up
            from a GL account mapping table. Using 9999 as a default
            reconciliation suspense account.
        """
        from ..models import GLAccount

        try:
            # Try to find a reconciliation or suspense account
            reconciliation_account = GLAccount.objects.filter(
                Q(account_name__icontains="reconciliation")
                | Q(account_name__icontains="suspense")
                | Q(account_number="9999")
            ).first()

            if reconciliation_account:
                return reconciliation_account.id

        except Exception:
            # Fallback if GL accounts not set up
            pass

        # Default fallback reconciliation account ID
        return 9999
