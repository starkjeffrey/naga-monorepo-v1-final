"""Reconciliation service for payment and enrollment matching.

This module contains the core reconciliation logic including tiered matching,
validation, monitoring, and error reporting for legacy data migration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models import (
    MaterialityThreshold,
    Payment,
    ReconciliationAdjustment,
    ReconciliationBatch,
    ReconciliationStatus,
)

if TYPE_CHECKING:
    from apps.curriculum.models import Term
    from apps.people.models import StudentProfile

logger = logging.getLogger(__name__)


class ReconciliationMatchResult:
    """Container for reconciliation match results."""

    def __init__(
        self,
        enrollments: list[ClassHeaderEnrollment] | None = None,
        confidence_score: Decimal = Decimal("0"),
        variance_amount: Decimal = Decimal("0"),
        variance_percentage: Decimal | None = None,
        pricing_method: str | None = None,
        match_reason: str = "",
        error_details: dict | None = None,
    ):
        self.enrollments = enrollments or []
        self.confidence_score = confidence_score
        self.variance_amount = variance_amount
        self.variance_percentage = variance_percentage
        self.pricing_method = pricing_method
        self.match_reason = match_reason
        self.error_details = error_details or {}


class ReconciliationService:
    """Main reconciliation service with tiered matching logic."""

    def __init__(self):
        self.validator = ReconciliationValidator()
        self.error_reporter = ReconciliationErrorReport()

    def reconcile_payment(self, payment: Payment, batch: ReconciliationBatch | None = None) -> ReconciliationStatus:
        """Apply tiered reconciliation logic to a payment."""

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
            # Tier 1: Perfect matches
            if result := self.try_perfect_match(payment):
                return self._mark_reconciled(
                    status,
                    result,
                    confidence="HIGH",
                    status_value=ReconciliationStatus.Status.FULLY_RECONCILED,
                )

            # Tier 2: Good matches with minor variances
            if result := self.try_good_match(payment):
                if result.variance_percentage and result.variance_percentage <= 5:  # Within 5% tolerance
                    return self._mark_reconciled(
                        status,
                        result,
                        confidence="HIGH",
                        status_value=ReconciliationStatus.Status.AUTO_ALLOCATED,
                    )

            # Tier 3: Pattern-based allocation
            if result := self.try_pattern_match(payment):
                confidence = self._calculate_confidence(result)
                return self._mark_reconciled(
                    status,
                    result,
                    confidence=confidence,
                    status_value=ReconciliationStatus.Status.AUTO_ALLOCATED,
                )

            # Tier 4: Mark for manual review
            return self._mark_for_review(status, "No automated match found")

        except Exception as e:
            logger.error(f"Error reconciling payment {payment.payment_reference}: {e}")
            return self._mark_error(status, str(e))

    def try_perfect_match(self, payment: Payment) -> ReconciliationMatchResult | None:
        """Attempt perfect match based on exact amount and student enrollments."""

        # Find enrollments for the same student and term
        enrollments = ClassHeaderEnrollment.objects.filter(
            student__user_id=payment.invoice.student.user,  # type: ignore[attr-defined]
            class_header__term=payment.invoice.term,  # type: ignore[attr-defined]
            status__in=["ENROLLED", "COMPLETED"],
        )

        if not enrollments.exists():
            return None

        # Calculate expected amount based on pricing
        expected_amount = self._calculate_expected_amount(list(enrollments.all()), payment.invoice.term)  # type: ignore[attr-defined]

        # Check for perfect match (within $1 tolerance for rounding)
        variance = abs(payment.amount - expected_amount)
        if variance <= Decimal("1.00"):
            variance_percentage = (variance / payment.amount * 100) if payment.amount > 0 else Decimal("0")

            return ReconciliationMatchResult(
                enrollments=list(enrollments),
                confidence_score=Decimal("100"),
                variance_amount=variance,
                variance_percentage=variance_percentage,
                pricing_method=ReconciliationStatus.PricingMethod.DEFAULT_PRICING,
                match_reason="Perfect amount match with student enrollments",
            )

        return None

    def try_good_match(self, payment: Payment) -> ReconciliationMatchResult | None:
        """Attempt good match with allowable variance."""

        # Find enrollments for the same student and term
        enrollments = ClassHeaderEnrollment.objects.filter(
            student__user_id=payment.invoice.student.user,  # type: ignore[attr-defined]
            class_header__term=payment.invoice.term,  # type: ignore[attr-defined]
            status__in=["ENROLLED", "COMPLETED"],
        )

        if not enrollments.exists():
            return None

        # Calculate expected amount
        expected_amount = self._calculate_expected_amount(list(enrollments.all()), payment.invoice.term)  # type: ignore[attr-defined]

        # Check variance within acceptable range (≤10%)
        variance = abs(payment.amount - expected_amount)
        variance_percentage = (variance / payment.amount * 100) if payment.amount > 0 else Decimal("0")

        if variance_percentage <= 10:  # Within 10% tolerance
            confidence_score = max(Decimal("60"), Decimal("100") - variance_percentage * 2)

            return ReconciliationMatchResult(
                enrollments=list(enrollments),
                confidence_score=confidence_score,
                variance_amount=variance,
                variance_percentage=variance_percentage,
                pricing_method=ReconciliationStatus.PricingMethod.DEFAULT_PRICING,
                match_reason=f"Good match within {variance_percentage:.1f}% variance",
            )

        return None

    def try_pattern_match(self, payment: Payment) -> ReconciliationMatchResult | None:
        """Attempt pattern-based matching using historical data."""

        # Look for similar payment patterns for this student
        student = payment.invoice.student  # type: ignore[attr-defined]
        similar_payments = Payment.objects.filter(
            invoice__student=student,
            amount__range=(
                payment.amount * Decimal("0.8"),
                payment.amount * Decimal("1.2"),
            ),
        ).exclude(id=payment.id)

        if not similar_payments.exists():
            return None

        # Find the most common enrollment pattern
        common_enrollments = self._find_common_enrollment_patterns(student, payment.amount)

        if common_enrollments:
            expected_amount = self._calculate_expected_amount(common_enrollments, payment.invoice.term)  # type: ignore[attr-defined]
            variance = abs(payment.amount - expected_amount)
            variance_percentage = (variance / payment.amount * 100) if payment.amount > 0 else Decimal("0")

            # Lower confidence for pattern matches
            confidence_score = max(Decimal("40"), Decimal("80") - variance_percentage)

            return ReconciliationMatchResult(
                enrollments=common_enrollments,
                confidence_score=confidence_score,
                variance_amount=variance,
                variance_percentage=variance_percentage,
                pricing_method=ReconciliationStatus.PricingMethod.HISTORICAL_MATCH,
                match_reason="Pattern match based on historical enrollments",
            )

        return None

    def _calculate_expected_amount(self, enrollments: list[ClassHeaderEnrollment], term: Term) -> Decimal:
        """Calculate expected payment amount based on enrollments."""
        total = Decimal("0")

        for _enrollment in enrollments:
            # Use basic pricing calculation - this would be enhanced with actual pricing service
            # For now, use a simple default amount per course
            total += Decimal("500.00")  # Placeholder amount

        return total

    def _find_common_enrollment_patterns(
        self, student: StudentProfile, amount: Decimal
    ) -> list[ClassHeaderEnrollment]:
        """Find common enrollment patterns for similar amounts."""

        # Find enrollments in current term
        current_enrollments = ClassHeaderEnrollment.objects.filter(
            student=student, status__in=["ENROLLED", "COMPLETED"]
        ).order_by("-created_at")[:5]  # Last 5 enrollments

        return list(current_enrollments)

    def _calculate_confidence(self, result: ReconciliationMatchResult) -> str:
        """Calculate confidence level from result."""
        score = result.confidence_score

        if score >= 95:
            return "HIGH"
        elif score >= 80:
            return "MEDIUM"
        elif score > 0:
            return "LOW"
        else:
            return "NONE"

    def _mark_reconciled(
        self,
        status: ReconciliationStatus,
        result: ReconciliationMatchResult,
        confidence: str,
        status_value: str,
    ) -> ReconciliationStatus:
        """Mark payment as reconciled with given result."""

        with transaction.atomic():
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
            status.matched_enrollments.set(result.enrollments)

            # Create adjustment if needed
            if result.variance_amount > Decimal("0"):
                self._create_adjustment(status, result)

        return status

    def _mark_for_review(self, status: ReconciliationStatus, reason: str) -> ReconciliationStatus:
        """Mark payment for manual review."""

        status.status = ReconciliationStatus.Status.PENDING_REVIEW
        status.confidence_level = ReconciliationStatus.ConfidenceLevel.NONE
        status.confidence_score = Decimal("0")
        status.notes = reason
        status.save()

        return status

    def _mark_error(self, status: ReconciliationStatus, error_message: str) -> ReconciliationStatus:
        """Mark payment as having an error."""

        status.status = ReconciliationStatus.Status.EXCEPTION_ERROR
        status.confidence_level = ReconciliationStatus.ConfidenceLevel.NONE
        status.confidence_score = Decimal("0")
        status.error_category = "PROCESSING_ERROR"
        status.error_details = {
            "error": error_message,
            "timestamp": timezone.now().isoformat(),
        }
        status.save()

        return status

    def _create_adjustment(self, status: ReconciliationStatus, result: ReconciliationMatchResult):
        """Create reconciliation adjustment for variance."""

        # Get reconciliation GL account (create a default one if needed)
        from apps.finance.models import GLAccount

        recon_account, _ = GLAccount.objects.get_or_create(
            account_code="9999-RECON",
            defaults={
                "account_name": "Reconciliation Adjustments",
                "account_type": GLAccount.AccountType.ASSET,
                "account_category": GLAccount.AccountCategory.CURRENT_ASSET,
                "description": "Temporary account for reconciliation adjustments",
            },
        )

        # Determine adjustment type based on variance
        if result.variance_percentage and result.variance_percentage <= 5:
            adjustment_type = ReconciliationAdjustment.AdjustmentType.PRICING_VARIANCE
        else:
            adjustment_type = ReconciliationAdjustment.AdjustmentType.CLERICAL_ERROR

        # Check if adjustment requires approval based on materiality
        threshold = MaterialityThreshold.get_threshold(MaterialityThreshold.ThresholdContext.INDIVIDUAL_PAYMENT)
        requires_approval = threshold and abs(result.variance_amount) >= threshold.absolute_threshold

        ReconciliationAdjustment.objects.create(
            gl_account=recon_account,
            adjustment_type=adjustment_type,
            description=f"Reconciliation variance: {result.match_reason}",
            original_amount=status.payment.amount,
            adjusted_amount=status.payment.amount - result.variance_amount,
            variance=result.variance_amount,
            payment=status.payment,
            reconciliation_status=status,
            student=status.payment.invoice.student,
            term=status.payment.invoice.term,
            reconciliation_batch=status.reconciliation_batch,
            requires_approval=requires_approval,
        )


class ReconciliationValidator:
    """Validate reconciliation results."""

    def validate_payment(self, payment: Payment, reconciliation_status: ReconciliationStatus) -> list[dict]:
        """Validate a payment reconciliation."""
        validations = []

        # Check unusual patterns
        if self._is_unusual_student_load(payment.invoice.student, reconciliation_status):  # type: ignore[attr-defined]
            validations.append(
                {
                    "type": "UNUSUAL_COURSE_LOAD",
                    "severity": "WARNING",
                    "message": f"Student has {reconciliation_status.matched_enrollments.count()} courses",
                }
            )

        # Check pricing model consistency
        if self._has_pricing_inconsistency(reconciliation_status):
            validations.append(
                {
                    "type": "PRICING_INCONSISTENCY",
                    "severity": "ERROR",
                    "message": "Multiple pricing models detected for same term",
                }
            )

        # Check for negative balances
        if payment.invoice.amount_due < 0:  # type: ignore[attr-defined]
            validations.append(
                {
                    "type": "NEGATIVE_BALANCE",
                    "severity": "ERROR",
                    "message": f"Negative balance: {payment.invoice.amount_due}",  # type: ignore[attr-defined]
                }
            )

        # Check variance thresholds
        threshold = MaterialityThreshold.get_threshold(MaterialityThreshold.ThresholdContext.INDIVIDUAL_PAYMENT)
        if threshold and abs(reconciliation_status.variance_amount) >= threshold.absolute_threshold:
            validations.append(
                {
                    "type": "MATERIAL_VARIANCE",
                    "severity": "WARNING",
                    "message": (
                        f"Variance ${reconciliation_status.variance_amount} exceeds "
                        f"threshold ${threshold.absolute_threshold}"
                    ),
                }
            )

        return validations

    def _is_unusual_student_load(self, student: StudentProfile, reconciliation_status: ReconciliationStatus) -> bool:
        """Flag if student has unusual number of courses."""
        course_count = reconciliation_status.matched_enrollments.count()

        # Define thresholds based on student type (simplified logic)
        max_courses = 7  # Most students take ≤7 courses
        return course_count > max_courses

    def _has_pricing_inconsistency(self, reconciliation_status: ReconciliationStatus) -> bool:
        """Check for pricing model inconsistencies."""
        # Simplified check - in practice would compare against expected pricing
        return False


class ReconciliationMonitor:
    """Real-time monitoring of reconciliation health."""

    def get_dashboard_metrics(self) -> dict[str, Any]:
        """Get dashboard metrics for monitoring."""
        today = timezone.now().date()

        return {
            "daily_stats": {
                "payments_received": self._get_today_payments(),
                "auto_reconciled": self._get_auto_reconciled_rate(today),
                "pending_review": self._get_pending_count(),
                "error_rate": self._get_error_rate(today),
            },
            "alerts": self._get_active_alerts(),
            "trends": {
                "reconciliation_rate_7d": self._get_trend_data(days=7),
                "error_categories_7d": self._get_error_trends(days=7),
            },
        }

    def _get_today_payments(self) -> int:
        """Get count of payments received today."""
        today = timezone.now().date()
        return Payment.objects.filter(payment_date__date=today).count()

    def _get_auto_reconciled_rate(self, date) -> Decimal:
        """Get auto-reconciliation rate for given date."""
        total = ReconciliationStatus.objects.filter(created_at__date=date).count()

        if total == 0:
            return Decimal("0")

        auto_reconciled = ReconciliationStatus.objects.filter(
            created_at__date=date,
            status__in=[
                ReconciliationStatus.Status.FULLY_RECONCILED,
                ReconciliationStatus.Status.AUTO_ALLOCATED,
            ],
        ).count()

        return Decimal(auto_reconciled) / Decimal(total) * 100

    def _get_pending_count(self) -> int:
        """Get count of payments pending review."""
        return ReconciliationStatus.objects.filter(status=ReconciliationStatus.Status.PENDING_REVIEW).count()

    def _get_error_rate(self, date) -> Decimal:
        """Get error rate for given date."""
        total = ReconciliationStatus.objects.filter(created_at__date=date).count()

        if total == 0:
            return Decimal("0")

        errors = ReconciliationStatus.objects.filter(
            created_at__date=date, status=ReconciliationStatus.Status.EXCEPTION_ERROR
        ).count()

        return Decimal(errors) / Decimal(total) * 100

    def _get_active_alerts(self) -> list[dict]:
        """Get active system alerts."""
        alerts = []

        # Check for degrading reconciliation rate
        if self._is_reconciliation_rate_declining():
            alerts.append(
                {
                    "type": "DECLINING_RATE",
                    "severity": "WARNING",
                    "message": "Reconciliation rate declining over past 3 days",
                }
            )

        # Check for unusual error patterns
        if unusual := self._detect_unusual_patterns():
            alerts.append(
                {
                    "type": "UNUSUAL_PATTERN",
                    "severity": "HIGH",
                    "message": f"Unusual pattern detected: {unusual}",
                }
            )

        return alerts

    def _get_trend_data(self, days: int) -> list[dict]:
        """Get trend data for specified number of days."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        trends = []
        current_date = start_date

        while current_date <= end_date:
            rate = self._get_auto_reconciled_rate(current_date)
            trends.append({"date": current_date.isoformat(), "reconciliation_rate": float(rate)})
            current_date += timedelta(days=1)

        return trends

    def _get_error_trends(self, days: int) -> dict[str, int]:
        """Get error category trends."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        queryset = (
            ReconciliationAdjustment.objects.filter(created_at__date__range=[start_date, end_date])
            .values("adjustment_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return {item["adjustment_type"]: item["count"] for item in queryset}

    def _is_reconciliation_rate_declining(self) -> bool:
        """Check if reconciliation rate is declining."""
        # Get rates for last 3 days
        rates = []
        for i in range(3):
            date = timezone.now().date() - timedelta(days=i)
            rates.append(self._get_auto_reconciled_rate(date))

        # Check if trend is declining
        return len(rates) >= 3 and rates[0] < rates[1] < rates[2]

    def _detect_unusual_patterns(self) -> str | None:
        """Detect unusual error patterns."""
        # Check for spike in specific error types
        recent_errors = (
            ReconciliationAdjustment.objects.filter(created_at__gte=timezone.now() - timedelta(hours=24))
            .values("adjustment_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        if recent_errors and recent_errors[0]["count"] > 10:
            return f"Spike in {recent_errors[0]['adjustment_type']} errors"

        return None


class ReconciliationErrorReport:
    """Generate error reports with materiality thresholds."""

    # Default materiality thresholds if not configured
    DEFAULT_MATERIALITY_THRESHOLDS = {
        "individual_transaction": Decimal("50.00"),
        "student_account": Decimal("500.00"),
        "aggregate_category": Decimal("10000.00"),
        "percentage_variance": Decimal("5.0"),  # 5%
    }

    def generate_executive_summary(self, period: tuple[datetime, datetime]) -> dict[str, Any]:
        """Generate executive summary for given period."""
        start_date, end_date = period

        return {
            "total_payments_processed": self._get_payment_count(period),
            "total_amount_processed": self._get_total_amount(period),
            "reconciliation_rate": self._calculate_reconciliation_rate(period),
            "material_errors": self._get_material_errors(period),
            "error_trends": self._analyze_error_trends(period),
            "recommendations": self._generate_recommendations(period),
        }

    def _get_payment_count(self, period: tuple[datetime, datetime]) -> int:
        """Get total payment count for period."""
        start_date, end_date = period
        return ReconciliationStatus.objects.filter(created_at__range=[start_date, end_date]).count()

    def _get_total_amount(self, period: tuple[datetime, datetime]) -> Decimal:
        """Get total amount processed for period."""
        start_date, end_date = period
        result = ReconciliationStatus.objects.filter(created_at__range=[start_date, end_date]).aggregate(
            total=Sum("payment__amount")
        )

        return result["total"] or Decimal("0")

    def _calculate_reconciliation_rate(self, period: tuple[datetime, datetime]) -> Decimal:
        """Calculate reconciliation rate for period."""
        start_date, end_date = period
        total = ReconciliationStatus.objects.filter(created_at__range=[start_date, end_date]).count()

        if total == 0:
            return Decimal("0")

        reconciled = ReconciliationStatus.objects.filter(
            created_at__range=[start_date, end_date],
            status__in=[
                ReconciliationStatus.Status.FULLY_RECONCILED,
                ReconciliationStatus.Status.AUTO_ALLOCATED,
            ],
        ).count()

        return Decimal(reconciled) / Decimal(total) * 100

    def _get_material_errors(self, period: tuple[datetime, datetime]) -> list[dict]:
        """Get errors above materiality threshold."""
        start_date, end_date = period
        errors = []

        # Get materiality threshold
        threshold = MaterialityThreshold.get_threshold(MaterialityThreshold.ThresholdContext.ERROR_CATEGORY)
        aggregate_threshold = (
            threshold.absolute_threshold if threshold else self.DEFAULT_MATERIALITY_THRESHOLDS["aggregate_category"]
        )

        # Group errors by category
        error_categories = (
            ReconciliationAdjustment.objects.filter(created_at__range=[start_date, end_date])
            .values("adjustment_type")
            .annotate(
                total_variance=Sum("variance"),
                count=Count("id"),
                avg_variance=Avg("variance"),
            )
        )

        for category in error_categories:
            if abs(category["total_variance"]) >= aggregate_threshold:
                errors.append(
                    {
                        "category": category["adjustment_type"],
                        "total_impact": category["total_variance"],
                        "frequency": category["count"],
                        "average_error": category["avg_variance"],
                    }
                )

        return errors

    def _analyze_error_trends(self, period: tuple[datetime, datetime]) -> dict[str, Any]:
        """Analyze error trends for period."""
        start_date, end_date = period

        # Get error counts by day
        daily_errors = (
            ReconciliationAdjustment.objects.filter(created_at__range=[start_date, end_date])
            .extra(select={"day": "date(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        return {
            "daily_error_counts": list(daily_errors),
            "trend_direction": self._calculate_trend_direction(daily_errors),
        }

    def _calculate_trend_direction(self, daily_data) -> str:
        """Calculate if errors are trending up, down, or stable."""
        if len(daily_data) < 3:
            return "insufficient_data"

        recent = daily_data[-3:]
        if recent[0]["count"] < recent[1]["count"] < recent[2]["count"]:
            return "increasing"
        elif recent[0]["count"] > recent[1]["count"] > recent[2]["count"]:
            return "decreasing"
        else:
            return "stable"

    def _generate_recommendations(self, period: tuple[datetime, datetime]) -> list[str]:
        """Generate recommendations based on error analysis."""
        recommendations = []

        # Analyze common error patterns
        common_errors = (
            ReconciliationAdjustment.objects.filter(created_at__range=period)
            .values("adjustment_type")
            .annotate(count=Count("id"))
            .order_by("-count")[:3]
        )

        for error in common_errors:
            if error["count"] > 10:
                error_type = error["adjustment_type"]
                if error_type == "PRICING_VARIANCE":
                    recommendations.append("Review pricing rules and update tolerances")
                elif error_type == "MISSING_ENROLLMENT":
                    recommendations.append("Improve enrollment data validation")
                elif error_type == "DUPLICATE_PAYMENT":
                    recommendations.append("Implement duplicate payment detection")

        if not recommendations:
            recommendations.append("Continue monitoring reconciliation performance")

        return recommendations
