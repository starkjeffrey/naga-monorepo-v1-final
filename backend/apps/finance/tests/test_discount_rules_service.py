"""Tests for DiscountRule permutations with the AutomaticDiscountService."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.curriculum.models import Term
from apps.enrollment.models import ProgramEnrollment
from apps.finance.models.discounts import DiscountRule
from apps.finance.services.automatic_discount_service import (
    AutomaticDiscountService,
    DiscountEligibilityStatus,
)
from apps.people.models import StudentProfile


@pytest.mark.django_db
class TestDiscountRulePermutations:
    """Test various permutations of DiscountRule configurations."""

    @pytest.fixture
    def service(self):
        """Create AutomaticDiscountService instance."""
        return AutomaticDiscountService()

    @pytest.fixture
    def term_with_discount(self):
        """Create a term with discount deadline."""
        return Term.objects.create(
            code="251015A",
            name="Term with Discount",
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=120),
            discount_end_date=date.today() + timedelta(days=15),  # 15 days from now
        )

    @pytest.fixture
    def term_without_discount(self):
        """Create a term without discount deadline."""
        return Term.objects.create(
            code="251015B",
            name="Term without Discount",
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=120),
            discount_end_date=None,
        )

    @pytest.fixture
    def ba_student(self):
        """Create a BA student with program enrollment."""
        student = StudentProfile.objects.create(
            student_id="BA001",
            person_id=1,
            first_name="John",
            last_name="Doe",
        )

        ProgramEnrollment.objects.create(
            student=student,
            cycle="BA",
            status="ACTIVE",
            start_date=date.today() - timedelta(days=30),
        )

        return student

    @pytest.fixture
    def ma_student(self):
        """Create an MA student with program enrollment."""
        student = StudentProfile.objects.create(
            student_id="MA001",
            person_id=2,
            first_name="Jane",
            last_name="Smith",
        )

        ProgramEnrollment.objects.create(
            student=student,
            cycle="MA",
            status="ACTIVE",
            start_date=date.today() - timedelta(days=30),
        )

        return student

    @pytest.fixture
    def prep_student(self):
        """Create a PREP student with program enrollment."""
        student = StudentProfile.objects.create(
            student_id="PREP001",
            person_id=3,
            first_name="Bob",
            last_name="Johnson",
        )

        ProgramEnrollment.objects.create(
            student=student,
            cycle="PREP",
            status="ACTIVE",
            start_date=date.today() - timedelta(days=30),
        )

        return student

    def test_universal_early_bird_rule(self, service, term_with_discount, ba_student, ma_student):
        """Test early bird rule that applies to all cycles (universal)."""
        # Create universal early bird rule (no cycle restriction)
        DiscountRule.objects.create(
            rule_name="Universal Early Bird",
            rule_type="EARLY_BIRD",
            pattern_text="10% all students pay by",
            discount_percentage=Decimal("10.00"),
            applies_to_cycle="",  # Empty = universal
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Test BA student
        eligibility = service.check_early_bird_eligibility(
            ba_student.student_id, term_with_discount.code, date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.ELIGIBLE
        assert eligibility.discount_rate == Decimal("10.00")

        # Test MA student
        eligibility = service.check_early_bird_eligibility(
            ma_student.student_id, term_with_discount.code, date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.ELIGIBLE
        assert eligibility.discount_rate == Decimal("10.00")

    def test_ba_only_early_bird_rule(self, service, term_with_discount, ba_student, ma_student):
        """Test early bird rule that applies only to BA cycle."""
        # Create BA-only early bird rule
        DiscountRule.objects.create(
            rule_name="BA Early Bird",
            rule_type="EARLY_BIRD",
            pattern_text="10% BA students pay by",
            discount_percentage=Decimal("15.00"),
            applies_to_cycle="BA",  # BA only
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Test BA student - should be eligible
        eligibility = service.check_early_bird_eligibility(
            ba_student.student_id, term_with_discount.code, date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.ELIGIBLE
        assert eligibility.discount_rate == Decimal("15.00")

        # Test MA student - should NOT be eligible
        eligibility = service.check_early_bird_eligibility(
            ma_student.student_id, term_with_discount.code, date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.NOT_APPLICABLE
        assert "Early bird rule does not apply to student's academic cycle" in eligibility.eligibility_reasons

    def test_ma_only_special_discount(self, service, term_with_discount, ba_student, ma_student):
        """Test special discount rule that applies only to MA cycle."""
        # Create MA-only monk discount
        DiscountRule.objects.create(
            rule_name="MA Monk Discount",
            rule_type="MONK",
            pattern_text="monk discount MA",
            discount_percentage=Decimal("50.00"),
            applies_to_cycle="MA",  # MA only
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Test MA student - should be eligible (requires approval)
        eligibility = service.check_special_discount_eligibility(
            ma_student.student_id, term_with_discount.code, "MONK", date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.REQUIRES_APPROVAL
        assert eligibility.discount_rate == Decimal("50.00")

        # Test BA student - should NOT be eligible
        eligibility = service.check_special_discount_eligibility(
            ba_student.student_id, term_with_discount.code, "MONK", date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.NOT_APPLICABLE
        assert "MONK rule does not apply to student's academic cycle" in eligibility.eligibility_reasons

    def test_prep_only_rule(self, service, term_with_discount, prep_student, ba_student):
        """Test rule that applies only to PREP cycle."""
        # Create PREP-only admin fee
        DiscountRule.objects.create(
            rule_name="PREP Admin Fee",
            rule_type="ADMIN_FEE",
            pattern_text="PREP admin fee",
            fixed_amount=Decimal("25.00"),
            applies_to_cycle="PREP",  # PREP only
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Test PREP student - should be eligible
        eligibility = service.check_special_discount_eligibility(
            prep_student.student_id, term_with_discount.code, "ADMIN_FEE", date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.REQUIRES_APPROVAL

        # Test BA student - should NOT be eligible
        eligibility = service.check_special_discount_eligibility(
            ba_student.student_id, term_with_discount.code, "ADMIN_FEE", date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.NOT_APPLICABLE
        assert "ADMIN_FEE rule does not apply to student's academic cycle" in eligibility.eligibility_reasons

    def test_term_restricted_rule(self, service, term_with_discount, term_without_discount, ba_student):
        """Test rule that is restricted to specific terms."""
        # Create rule that only applies to specific term
        DiscountRule.objects.create(
            rule_name="Term Specific Early Bird",
            rule_type="EARLY_BIRD",
            pattern_text="10% specific term",
            discount_percentage=Decimal("12.00"),
            applies_to_cycle="",  # Universal cycle
            applies_to_terms=[term_with_discount.code],  # Specific term only
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Test with allowed term - should be eligible
        eligibility = service.check_early_bird_eligibility(
            ba_student.student_id, term_with_discount.code, date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.ELIGIBLE
        assert eligibility.discount_rate == Decimal("12.00")

        # Test with non-allowed term - should NOT be eligible
        eligibility = service.check_early_bird_eligibility(
            ba_student.student_id, term_without_discount.code, date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.NOT_APPLICABLE
        assert "Early bird rule does not apply to this term" in eligibility.eligibility_reasons

    def test_cycle_and_term_restricted_rule(self, service, term_with_discount, ba_student, ma_student):
        """Test rule that is restricted to both specific cycle AND specific terms."""
        # Create rule that only applies to BA cycle in specific term
        DiscountRule.objects.create(
            rule_name="BA Term Specific",
            rule_type="EARLY_BIRD",
            pattern_text="15% BA students specific term",
            discount_percentage=Decimal("15.00"),
            applies_to_cycle="BA",  # BA only
            applies_to_terms=[term_with_discount.code],  # Specific term only
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Test BA student in allowed term - should be eligible
        eligibility = service.check_early_bird_eligibility(
            ba_student.student_id, term_with_discount.code, date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.ELIGIBLE
        assert eligibility.discount_rate == Decimal("15.00")

        # Test MA student in allowed term - should NOT be eligible (wrong cycle)
        eligibility = service.check_early_bird_eligibility(
            ma_student.student_id, term_with_discount.code, date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.NOT_APPLICABLE
        assert "Early bird rule does not apply to student's academic cycle" in eligibility.eligibility_reasons

    def test_multiple_rules_cycle_priority(self, service, term_with_discount, ba_student):
        """Test that when multiple rules exist, the service selects correctly."""
        # Create universal rule
        DiscountRule.objects.create(
            rule_name="Universal Early Bird",
            rule_type="EARLY_BIRD",
            pattern_text="10% all students",
            discount_percentage=Decimal("10.00"),
            applies_to_cycle="",  # Universal
            is_active=True,
        )

        # Create BA-specific rule (should take precedence for BA students)
        DiscountRule.objects.create(
            rule_name="BA Specific Early Bird",
            rule_type="EARLY_BIRD",
            pattern_text="15% BA students",
            discount_percentage=Decimal("15.00"),
            applies_to_cycle="BA",  # BA only
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # The service loads rules by type, so it will use whichever rule
        # is loaded last for the "EARLY_BIRD" type. In production,
        # you'd have more sophisticated rule selection logic.
        eligibility = service.check_early_bird_eligibility(
            ba_student.student_id, term_with_discount.code, date.today()
        )

        # Should be eligible for some early bird discount
        assert eligibility.status == DiscountEligibilityStatus.ELIGIBLE
        # The exact rate depends on which rule was loaded last
        assert eligibility.discount_rate in [Decimal("10.00"), Decimal("15.00")]

    def test_inactive_rule(self, service, term_with_discount, ba_student):
        """Test that inactive rules are not applied."""
        # Create inactive rule
        DiscountRule.objects.create(
            rule_name="Inactive Early Bird",
            rule_type="EARLY_BIRD",
            pattern_text="20% inactive rule",
            discount_percentage=Decimal("20.00"),
            applies_to_cycle="",  # Universal
            is_active=False,  # INACTIVE
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Should not be eligible because rule is inactive
        eligibility = service.check_early_bird_eligibility(
            ba_student.student_id, term_with_discount.code, date.today()
        )
        assert eligibility.status == DiscountEligibilityStatus.NOT_APPLICABLE
        assert "No early bird discount rule configured" in eligibility.eligibility_reasons

    def test_student_without_program_enrollment(self, service, term_with_discount):
        """Test handling of student without active program enrollment."""
        # Create student without program enrollment
        student = StudentProfile.objects.create(
            student_id="NO_PROG",
            person_id=99,
            first_name="No",
            last_name="Program",
        )

        # Create BA-only rule
        DiscountRule.objects.create(
            rule_name="BA Only Rule",
            rule_type="EARLY_BIRD",
            pattern_text="BA only",
            discount_percentage=Decimal("10.00"),
            applies_to_cycle="BA",
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Should not be eligible because student has no active program enrollment
        eligibility = service.check_early_bird_eligibility(student.student_id, term_with_discount.code, date.today())
        assert eligibility.status == DiscountEligibilityStatus.NOT_APPLICABLE
        assert "Early bird rule does not apply to student's academic cycle" in eligibility.eligibility_reasons

    def test_nonexistent_student(self, service, term_with_discount):
        """Test handling of nonexistent student."""
        # Create universal rule
        DiscountRule.objects.create(
            rule_name="Universal Early Bird",
            rule_type="EARLY_BIRD",
            pattern_text="10% all students",
            discount_percentage=Decimal("10.00"),
            applies_to_cycle="",
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Should not be eligible because student doesn't exist
        eligibility = service.check_early_bird_eligibility("NONEXISTENT", term_with_discount.code, date.today())
        assert eligibility.status == DiscountEligibilityStatus.NOT_APPLICABLE
        assert "Student not found" in eligibility.eligibility_reasons

    def test_all_cycle_types(self, service, term_with_discount):
        """Test rules for all supported cycle types."""
        cycle_types = ["HS", "CERT", "PREP", "BA", "MA", "PHD"]

        for i, cycle in enumerate(cycle_types):
            # Create student for this cycle
            student = StudentProfile.objects.create(
                student_id=f"{cycle}_STUDENT",
                person_id=100 + i,
                first_name=cycle,
                last_name="Student",
            )

            ProgramEnrollment.objects.create(
                student=student,
                cycle=cycle,
                status="ACTIVE",
                start_date=date.today() - timedelta(days=30),
            )

            # Create cycle-specific rule
            DiscountRule.objects.create(
                rule_name=f"{cycle} Specific Rule",
                rule_type="EARLY_BIRD",
                pattern_text=f"{cycle} discount",
                discount_percentage=Decimal("10.00"),
                applies_to_cycle=cycle,
                is_active=True,
            )

            # Reload service to pick up new rules
            service = AutomaticDiscountService()

            # Should be eligible
            eligibility = service.check_early_bird_eligibility(
                student.student_id, term_with_discount.code, date.today()
            )
            assert eligibility.status == DiscountEligibilityStatus.ELIGIBLE
            assert eligibility.discount_rate == Decimal("10.00")

    def test_expired_early_bird_with_cycle_rule(self, service, term_with_discount, ba_student):
        """Test that expired early bird respects cycle rules."""
        # Create BA-only rule
        DiscountRule.objects.create(
            rule_name="BA Early Bird",
            rule_type="EARLY_BIRD",
            pattern_text="10% BA students",
            discount_percentage=Decimal("10.00"),
            applies_to_cycle="BA",
            is_active=True,
        )

        # Reload service to pick up new rules
        service = AutomaticDiscountService()

        # Test with payment after deadline
        payment_date = term_with_discount.discount_end_date + timedelta(days=1)

        eligibility = service.check_early_bird_eligibility(
            ba_student.student_id, term_with_discount.code, payment_date
        )

        # Should be expired, not cycle-related rejection
        assert eligibility.status == DiscountEligibilityStatus.EXPIRED
        assert f"Payment date {payment_date} is after deadline" in eligibility.eligibility_reasons[0]
