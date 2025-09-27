"""
Automatic Discount Service

Implements automatic early bird and term-based discount application
based on Term.discount_end_date instead of manual notes pattern matching.

This service replaces the human-memory-dependent pattern matching system
with automatic, rule-based discount application tied to term deadlines.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from django.utils import timezone

from apps.curriculum.models import Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models.discounts import DiscountRule
from apps.people.models import StudentProfile


class DiscountEligibilityStatus(Enum):
    ELIGIBLE = "eligible"
    EXPIRED = "expired"
    NOT_APPLICABLE = "not_applicable"
    REQUIRES_APPROVAL = "requires_approval"
    ALREADY_APPLIED = "already_applied"


@dataclass
class DiscountEligibility:
    """Result of discount eligibility check."""

    student_id: str
    term_code: str
    discount_type: str
    status: DiscountEligibilityStatus
    discount_rate: Decimal | None
    eligible_amount: Decimal | None
    deadline: date | None
    days_remaining: int | None
    approval_required: bool
    eligibility_reasons: list[str]
    restrictions: list[str]


@dataclass
class DiscountApplication:
    """Result of applying a discount."""

    student_id: str
    term_code: str
    discount_type: str
    original_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    discount_rate: Decimal
    applied_date: datetime
    authority: str
    approval_status: str
    notes: str


class AutomaticDiscountService:
    """
    Service for automatic discount application based on term dates and business rules.

    Replaces pattern-matching system with automatic rule-based discounts.
    """

    def __init__(self):
        self.discount_rules = self._load_active_discount_rules()
        self.term_cache = {}

    def _load_active_discount_rules(self) -> dict[str, DiscountRule]:
        """Load all active discount rules."""
        rules = {}
        for rule in DiscountRule.objects.filter(is_active=True):
            rules[rule.rule_type] = rule
        return rules

    def check_early_bird_eligibility(
        self, student_id: str, term_code: str, payment_date: date | None = None
    ) -> DiscountEligibility:
        """
        Check if student is eligible for early bird discount.

        Based on Term.discount_end_date, not pattern matching.
        """
        payment_date = payment_date or date.today()

        # Get term information
        try:
            term = self._get_term(term_code)
        except Term.DoesNotExist:
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type="EARLY_BIRD",
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=None,
                days_remaining=None,
                approval_required=False,
                eligibility_reasons=["Term not found"],
                restrictions=[],
            )

        # Check if term has discount deadline configured
        if not term.discount_end_date:
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type="EARLY_BIRD",
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=None,
                days_remaining=None,
                approval_required=False,
                eligibility_reasons=["No discount deadline configured for term"],
                restrictions=[],
            )

        # Check if payment is before deadline
        days_remaining = (term.discount_end_date - payment_date).days

        if payment_date > term.discount_end_date:
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type="EARLY_BIRD",
                status=DiscountEligibilityStatus.EXPIRED,
                discount_rate=None,
                eligible_amount=None,
                deadline=term.discount_end_date,
                days_remaining=days_remaining,
                approval_required=False,
                eligibility_reasons=[f"Payment date {payment_date} is after deadline {term.discount_end_date}"],
                restrictions=[],
            )

        # Get early bird discount rule
        early_bird_rule = self.discount_rules.get("EARLY_BIRD")
        if not early_bird_rule:
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type="EARLY_BIRD",
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=term.discount_end_date,
                days_remaining=days_remaining,
                approval_required=False,
                eligibility_reasons=["No early bird discount rule configured"],
                restrictions=[],
            )

        # Check if rule applies to this term
        if not self._rule_applies_to_term(early_bird_rule, term_code):
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type="EARLY_BIRD",
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=term.discount_end_date,
                days_remaining=days_remaining,
                approval_required=False,
                eligibility_reasons=["Early bird rule does not apply to this term"],
                restrictions=[],
            )

        # Check if rule applies to this student's cycle
        if not self._rule_applies_to_student(early_bird_rule, student_id, term_code):
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type="EARLY_BIRD",
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=term.discount_end_date,
                days_remaining=days_remaining,
                approval_required=False,
                eligibility_reasons=["Early bird rule does not apply to student's academic cycle"],
                restrictions=[],
            )

        # Check student enrollment status
        enrollment_check = self._check_student_enrollment(student_id, term_code)
        if not enrollment_check["eligible"]:
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type="EARLY_BIRD",
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=term.discount_end_date,
                days_remaining=days_remaining,
                approval_required=False,
                eligibility_reasons=enrollment_check["reasons"],
                restrictions=[],
            )

        # Calculate eligible amount
        eligible_amount = enrollment_check["total_amount"]
        discount_rate = early_bird_rule.discount_percentage or Decimal("0")

        return DiscountEligibility(
            student_id=student_id,
            term_code=term_code,
            discount_type="EARLY_BIRD",
            status=DiscountEligibilityStatus.ELIGIBLE,
            discount_rate=discount_rate,
            eligible_amount=eligible_amount,
            deadline=term.discount_end_date,
            days_remaining=days_remaining,
            approval_required=False,
            eligibility_reasons=[
                f"Payment before deadline ({days_remaining} days remaining)",
                f"Student enrolled in {enrollment_check['course_count']} courses",
                f"Early bird discount: {discount_rate}%",
            ],
            restrictions=[],
        )

    def check_special_discount_eligibility(
        self,
        student_id: str,
        term_code: str,
        discount_type: str,
        payment_date: date | None = None,
    ) -> DiscountEligibility:
        """
        Check eligibility for special discounts (monk, staff, sibling).

        These are not time-based but require approval/verification.
        """
        payment_date = payment_date or date.today()

        # Get discount rule
        discount_rule = self.discount_rules.get(discount_type)
        if not discount_rule:
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type=discount_type,
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=None,
                days_remaining=None,
                approval_required=False,
                eligibility_reasons=[f"No {discount_type} discount rule configured"],
                restrictions=[],
            )

        # Check if rule applies to this term
        if not self._rule_applies_to_term(discount_rule, term_code):
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type=discount_type,
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=None,
                days_remaining=None,
                approval_required=False,
                eligibility_reasons=[f"{discount_type} rule does not apply to this term"],
                restrictions=[],
            )

        # Check if rule applies to this student's cycle
        if not self._rule_applies_to_student(discount_rule, student_id, term_code):
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type=discount_type,
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=None,
                days_remaining=None,
                approval_required=False,
                eligibility_reasons=[f"{discount_type} rule does not apply to student's academic cycle"],
                restrictions=[],
            )

        # Check student enrollment status
        enrollment_check = self._check_student_enrollment(student_id, term_code)
        if not enrollment_check["eligible"]:
            return DiscountEligibility(
                student_id=student_id,
                term_code=term_code,
                discount_type=discount_type,
                status=DiscountEligibilityStatus.NOT_APPLICABLE,
                discount_rate=None,
                eligible_amount=None,
                deadline=None,
                days_remaining=None,
                approval_required=True,
                eligibility_reasons=enrollment_check["reasons"],
                restrictions=[],
            )

        # Special discounts require approval
        eligible_amount = enrollment_check["total_amount"]
        discount_rate = discount_rule.discount_percentage or Decimal("0")

        return DiscountEligibility(
            student_id=student_id,
            term_code=term_code,
            discount_type=discount_type,
            status=DiscountEligibilityStatus.REQUIRES_APPROVAL,
            discount_rate=discount_rate,
            eligible_amount=eligible_amount,
            deadline=None,
            days_remaining=None,
            approval_required=True,
            eligibility_reasons=[
                f"Student enrolled in {enrollment_check['course_count']} courses",
                f"{discount_type} discount: {discount_rate}%",
                "Requires administrative approval",
            ],
            restrictions=[f"{discount_type} discount requires verification of eligibility status"],
        )

    def apply_discount(
        self,
        student_id: str,
        term_code: str,
        discount_type: str,
        original_amount: Decimal,
        authority: str = "SYSTEM",
        payment_date: date | None = None,
        force_apply: bool = False,
    ) -> DiscountApplication:
        """
        Apply a discount to a student's charges.

        Args:
            student_id: Student ID
            term_code: Term code
            discount_type: Type of discount to apply
            original_amount: Original amount before discount
            authority: Who authorized the discount
            payment_date: Date of payment (for early bird eligibility)
            force_apply: Skip eligibility checks
        """
        payment_date = payment_date or date.today()
        applied_date = timezone.now()

        # Check eligibility unless forced
        if not force_apply:
            if discount_type == "EARLY_BIRD":
                eligibility = self.check_early_bird_eligibility(student_id, term_code, payment_date)
            else:
                eligibility = self.check_special_discount_eligibility(
                    student_id, term_code, discount_type, payment_date
                )

            if eligibility.status not in [
                DiscountEligibilityStatus.ELIGIBLE,
                DiscountEligibilityStatus.REQUIRES_APPROVAL,
            ]:
                # Return failed application
                return DiscountApplication(
                    student_id=student_id,
                    term_code=term_code,
                    discount_type=discount_type,
                    original_amount=original_amount,
                    discount_amount=Decimal("0"),
                    final_amount=original_amount,
                    discount_rate=Decimal("0"),
                    applied_date=applied_date,
                    authority=authority,
                    approval_status="REJECTED",
                    notes=f"Not eligible: {', '.join(eligibility.eligibility_reasons)}",
                )

        # Get discount rule
        discount_rule = self.discount_rules.get(discount_type)
        if not discount_rule:
            return DiscountApplication(
                student_id=student_id,
                term_code=term_code,
                discount_type=discount_type,
                original_amount=original_amount,
                discount_amount=Decimal("0"),
                final_amount=original_amount,
                discount_rate=Decimal("0"),
                applied_date=applied_date,
                authority=authority,
                approval_status="REJECTED",
                notes=f"No discount rule configured for {discount_type}",
            )

        # Calculate discount
        discount_rate = discount_rule.discount_percentage or Decimal("0")
        discount_amount = original_amount * (discount_rate / Decimal("100"))
        final_amount = original_amount - discount_amount

        # Determine approval status
        if discount_type == "EARLY_BIRD":
            approval_status = "APPROVED"  # Automatic for early bird
        else:
            approval_status = "PENDING_APPROVAL" if authority == "SYSTEM" else "APPROVED"

        # Generate notes
        notes = f"Applied {discount_type} discount: {discount_rate}% on ${original_amount}"
        if discount_type == "EARLY_BIRD":
            try:
                term = self._get_term(term_code)
                if term.discount_end_date:
                    days_before = (term.discount_end_date - payment_date).days
                    notes += f" (payment {days_before} days before deadline)"
            except Exception:
                pass

        return DiscountApplication(
            student_id=student_id,
            term_code=term_code,
            discount_type=discount_type,
            original_amount=original_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            discount_rate=discount_rate,
            applied_date=applied_date,
            authority=authority,
            approval_status=approval_status,
            notes=notes,
        )

    def get_term_discount_summary(self, term_code: str) -> dict[str, Any]:
        """Get discount summary for a term."""
        try:
            term = self._get_term(term_code)
        except Term.DoesNotExist:
            return {"error": "Term not found"}

        summary: dict[str, Any] = {
            "term_code": term_code,
            "term_name": str(term),
            "discount_end_date": term.discount_end_date,
            "days_until_deadline": None,
            "early_bird_status": "not_configured",
            "available_discounts": [],
            "configuration_issues": [],
        }

        # Calculate days until deadline
        if term.discount_end_date:
            days_until = (term.discount_end_date - date.today()).days
            summary["days_until_deadline"] = days_until

            if days_until > 0:
                summary["early_bird_status"] = "active"
            else:
                summary["early_bird_status"] = "expired"
        else:
            summary["configuration_issues"].append("No discount_end_date configured")

        # Check available discount rules
        for rule_type, rule in self.discount_rules.items():
            if self._rule_applies_to_term(rule, term_code):
                summary["available_discounts"].append(
                    {
                        "type": rule_type,
                        "rate": float(rule.discount_percentage or 0),
                        "name": rule.rule_name,
                        "requires_approval": rule_type != "EARLY_BIRD",
                    }
                )

        if not summary["available_discounts"]:
            summary["configuration_issues"].append("No discount rules configured")

        return summary

    def _get_term(self, term_code: str) -> Term:
        """Get term with caching."""
        if term_code not in self.term_cache:
            self.term_cache[term_code] = Term.objects.get(code=term_code)
        return self.term_cache[term_code]

    def _rule_applies_to_term(self, rule: DiscountRule, term_code: str) -> bool:
        """Check if discount rule applies to specific term."""
        # If no term restrictions, applies to all terms
        if not rule.applies_to_terms:
            return True

        # Check if term is in the allowed terms list
        return term_code in rule.applies_to_terms

    def _rule_applies_to_student(self, rule: DiscountRule, student_id: str, term_code: str) -> bool:
        """Check if discount rule applies to specific student based on their cycle and schedule."""
        # If no cycle restriction, applies to all cycles
        if not rule.applies_to_cycle:
            return True

        # Get student's current program enrollment to determine cycle
        try:
            student = StudentProfile.objects.get(student_id=student_id)
            # Get active program enrollment for the term
            program_enrollment = student.program_enrollments.filter(
                status="ACTIVE",
                start_date__lte=timezone.now().date(),
            ).first()

            if program_enrollment:
                # Check if the student's cycle matches the rule's cycle
                cycle_matches = program_enrollment.cycle == rule.applies_to_cycle

                # If rule has schedule criteria, check that too
                if cycle_matches and rule.applies_to_cycle:
                    return self._rule_applies_to_schedule(rule, student_id, term_code)

                return cycle_matches
            else:
                # No active enrollment, can't determine cycle
                return False
        except StudentProfile.DoesNotExist:
            return False

    def _rule_applies_to_schedule(self, rule: DiscountRule, student_id: str, term_code: str) -> bool:
        """Check if discount rule applies based on student's class schedule (time-of-day)."""

        # If no schedule criteria, applies to all schedules
        if not rule.applies_to_cycle:
            return True

        schedule_criteria = rule.applies_to_cycle
        # Note: applies_to_cycle is a string field, but may need JSON parsing for complex criteria
        if isinstance(schedule_criteria, dict):
            time_of_day_filter = schedule_criteria.get("time_of_day", [])
            min_courses = schedule_criteria.get("min_courses", 1)
        else:
            time_of_day_filter: list[str] = []
            min_courses = 1

        if not time_of_day_filter:
            return True

        # Get student's enrollments for this term
        try:
            student = StudentProfile.objects.get(student_id=student_id)
            term = self._get_term(term_code)

            enrollments = ClassHeaderEnrollment.objects.filter(
                student=student, class_header__term=term, status__in=["ENROLLED", "ACTIVE", "COMPLETED"]
            ).select_related("class_header")

            # Check if student has classes matching the time criteria
            matching_enrollments = []
            for enrollment in enrollments:
                if enrollment.class_header.time_of_day in time_of_day_filter:
                    matching_enrollments.append(enrollment)

            # Must have at least min_courses matching classes
            return len(matching_enrollments) >= min_courses

        except Exception:
            return False

    def _check_student_enrollment(self, student_id: str, term_code: str) -> dict[str, Any]:
        """Check student enrollment status and calculate total amount."""
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return {
                "eligible": False,
                "reasons": ["Student not found"],
                "total_amount": Decimal("0"),
                "course_count": 0,
            }

        try:
            term = self._get_term(term_code)
        except Term.DoesNotExist:
            return {
                "eligible": False,
                "reasons": ["Term not found"],
                "total_amount": Decimal("0"),
                "course_count": 0,
            }

        # Get student enrollments for this term
        enrollments = ClassHeaderEnrollment.objects.filter(student=student, class_header__term=term).select_related(
            "class_header__course"
        )

        if not enrollments.exists():
            return {
                "eligible": False,
                "reasons": ["No enrollments found for this term"],
                "total_amount": Decimal("0"),
                "course_count": 0,
            }

        # Calculate total amount (simplified - would integrate with pricing service)
        total_amount = Decimal("0")
        course_count = enrollments.count()

        # This would integrate with the actual pricing service
        # For now, use a placeholder calculation
        for _enrollment in enrollments:
            # Would get actual course pricing here
            total_amount += Decimal("100.00")  # Placeholder

        return {
            "eligible": True,
            "reasons": [f"Enrolled in {course_count} courses"],
            "total_amount": total_amount,
            "course_count": course_count,
        }

    def get_student_discount_history(self, student_id: str, term_code: str | None = None) -> list[dict[str, Any]]:
        """Get student's discount application history."""
        # This would query the actual discount application records
        # For now, return placeholder structure
        return [
            {
                "term_code": term_code or "240109E",
                "discount_type": "EARLY_BIRD",
                "amount": "100.00",
                "rate": "10.0",
                "applied_date": "2024-01-05",
                "authority": "SYSTEM",
                "status": "APPROVED",
            }
        ]

    def bulk_apply_early_bird_discounts(
        self, term_code: str, payment_date: date | None = None, dry_run: bool = True
    ) -> dict[str, Any]:
        """
        Bulk apply early bird discounts for eligible students in a term.

        Used for processing payments received before deadline.
        """
        payment_date = payment_date or date.today()

        results: dict[str, Any] = {
            "term_code": term_code,
            "payment_date": payment_date.isoformat(),
            "processed_count": 0,
            "eligible_count": 0,
            "applied_count": 0,
            "rejected_count": 0,
            "total_discount_amount": Decimal("0"),
            "applications": [],
            "errors": [],
        }

        try:
            term = self._get_term(term_code)
        except Term.DoesNotExist:
            results["errors"].append(f"Term {term_code} not found")
            return results

        if not term.discount_end_date:
            results["errors"].append(f"Term {term_code} has no discount deadline configured")
            return results

        if payment_date > term.discount_end_date:
            results["errors"].append(
                f"Payment date {payment_date} is after discount deadline {term.discount_end_date}"
            )
            return results

        # Get all students with enrollments in this term
        enrollments = (
            ClassHeaderEnrollment.objects.filter(class_header__term=term).select_related("student").distinct("student")
        )

        for enrollment in enrollments:
            student_id = str(enrollment.student.student_id)
            results["processed_count"] += 1

            try:
                # Check eligibility
                eligibility = self.check_early_bird_eligibility(student_id, term_code, payment_date)

                if eligibility.status == DiscountEligibilityStatus.ELIGIBLE:
                    results["eligible_count"] += 1

                    if not dry_run:
                        # Apply discount
                        application = self.apply_discount(
                            student_id=student_id,
                            term_code=term_code,
                            discount_type="EARLY_BIRD",
                            original_amount=eligibility.eligible_amount or Decimal("0"),
                            authority="SYSTEM_BULK",
                            payment_date=payment_date,
                        )

                        if application.approval_status == "APPROVED":
                            results["applied_count"] += 1
                            results["total_discount_amount"] += application.discount_amount
                        else:
                            results["rejected_count"] += 1

                        results["applications"].append(
                            {
                                "student_id": student_id,
                                "original_amount": float(application.original_amount),
                                "discount_amount": float(application.discount_amount),
                                "final_amount": float(application.final_amount),
                                "status": application.approval_status,
                            }
                        )
                    else:
                        # Dry run - just count eligible
                        results["applications"].append(
                            {
                                "student_id": student_id,
                                "eligible_amount": float(eligibility.eligible_amount or 0),
                                "discount_rate": float(eligibility.discount_rate or 0),
                                "status": "ELIGIBLE",
                            }
                        )
                else:
                    results["rejected_count"] += 1

            except Exception as e:
                results["errors"].append(f"Error processing student {student_id}: {e!s}")

        return results
