"""Tests for scholarships app services.

Tests cover business logic services including scholarship calculation,
eligibility validation, and reporting functionality.
"""

from decimal import Decimal

import pytest
from django.test import TestCase

from apps.scholarships.models import Scholarship
from apps.scholarships.services import (
    ScholarshipCalculationService,
    ScholarshipEligibilityService,
    ScholarshipReportingService,
)
from apps.scholarships.tests.test_factories import (
    SimpleScholarshipFactory,
    SimpleSponsoredStudentFactory,
    SimpleSponsorFactory,
)


# Mock student for tests without people app dependency
class MockStudent:
    def __init__(self, student_id="TEST001"):
        self.student_id = student_id
        self.id = 1
        self.person = MockPerson()

    def __str__(self):
        return f"Student {self.student_id}"


class MockPerson:
    def __init__(self, full_name="Test Student"):
        self.full_name = full_name


@pytest.mark.django_db
class ScholarshipCalculationServiceTest(TestCase):
    """Test ScholarshipCalculationService functionality."""

    def setUp(self):
        """Set up test data."""
        self.student = MockStudent("TEST001")

    def test_get_best_scholarship_no_scholarships(self):
        """Test best scholarship selection with no active scholarships."""
        result = ScholarshipCalculationService.get_best_scholarship_for_student(self.student)

        self.assertIsNone(result["scholarship"])
        self.assertEqual(result["discount_percentage"], Decimal("0.00"))
        self.assertEqual(result["discount_type"], "none")
        self.assertEqual(result["benefit_source"], "none")

    def test_get_best_scholarship_single_percentage(self):
        """Test best scholarship selection with single percentage scholarship."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            award_amount=None,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = ScholarshipCalculationService.get_best_scholarship_for_student(self.student)

        self.assertEqual(result["scholarship"], scholarship)
        self.assertEqual(result["discount_percentage"], Decimal("75.00"))
        self.assertEqual(result["discount_type"], "percentage")

    def test_get_best_scholarship_single_fixed_amount(self):
        """Test best scholarship selection with single fixed amount scholarship."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=Decimal("1000.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = ScholarshipCalculationService.get_best_scholarship_for_student(self.student)

        self.assertEqual(result["scholarship"], scholarship)
        self.assertEqual(result["discount_type"], "fixed_amount")

    def test_get_best_scholarship_multiple_scholarships_percentage_wins(self):
        """Test best scholarship selection with multiple scholarships - higher percentage wins."""
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("50.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )
        scholarship2 = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = ScholarshipCalculationService.get_best_scholarship_for_student(self.student)

        self.assertEqual(result["scholarship"], scholarship2)
        self.assertEqual(result["discount_percentage"], Decimal("75.00"))

    def test_get_best_scholarship_fixed_amount_wins_over_percentage(self):
        """Test that fixed amount (monks) always wins over percentage."""
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("100.00"),
            award_amount=None,
            status=Scholarship.AwardStatus.ACTIVE,
        )
        scholarship2 = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=Decimal("500.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = ScholarshipCalculationService.get_best_scholarship_for_student(self.student)

        # Fixed amount should win even if percentage is higher
        self.assertEqual(result["scholarship"], scholarship2)
        self.assertEqual(result["discount_type"], "fixed_amount")

    def test_calculate_tuition_discount_percentage(self):
        """Test tuition discount calculation with percentage scholarship."""
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        base_tuition = Decimal("1000.00")
        result = ScholarshipCalculationService.calculate_tuition_discount(self.student, base_tuition)

        self.assertEqual(result["original_amount"], Decimal("1000.00"))
        self.assertEqual(result["discount_amount"], Decimal("750.00"))
        self.assertEqual(result["final_amount"], Decimal("250.00"))
        self.assertEqual(result["discount_percentage"], Decimal("75.00"))

    def test_calculate_tuition_discount_fixed_amount(self):
        """Test tuition discount calculation with fixed amount scholarship."""
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=Decimal("600.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        base_tuition = Decimal("1000.00")
        result = ScholarshipCalculationService.calculate_tuition_discount(self.student, base_tuition)

        self.assertEqual(result["original_amount"], Decimal("1000.00"))
        self.assertEqual(result["discount_amount"], Decimal("600.00"))
        self.assertEqual(result["final_amount"], Decimal("400.00"))

    def test_calculate_tuition_discount_fixed_amount_exceeds_tuition(self):
        """Test fixed amount discount that exceeds tuition amount."""
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=Decimal("1200.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        base_tuition = Decimal("1000.00")
        result = ScholarshipCalculationService.calculate_tuition_discount(self.student, base_tuition)

        # Discount should be capped at tuition amount
        self.assertEqual(result["discount_amount"], Decimal("1000.00"))
        self.assertEqual(result["final_amount"], Decimal("0.00"))

    def test_get_active_scholarships_includes_sponsored_student_scholarships(self):
        """Test that active scholarships include both direct and sponsored student scholarships."""
        # Direct scholarship
        direct_scholarship = SimpleScholarshipFactory(
            student=self.student,
            sponsored_student=None,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Sponsored student scholarship
        sponsored_student = SimpleSponsoredStudentFactory(student=self.student)
        sponsored_scholarship = SimpleScholarshipFactory(
            student=self.student,
            sponsored_student=sponsored_student,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Get all active scholarships
        active_scholarships = ScholarshipCalculationService._get_active_scholarships_for_student(self.student)

        self.assertEqual(len(active_scholarships), 2)
        scholarship_ids = [s.id for s in active_scholarships]
        self.assertIn(direct_scholarship.id, scholarship_ids)
        self.assertIn(sponsored_scholarship.id, scholarship_ids)


@pytest.mark.django_db
class ScholarshipEligibilityServiceTest(TestCase):
    """Test ScholarshipEligibilityService functionality."""

    def setUp(self):
        """Set up test data."""
        self.student = MockStudent("TEST001")

    def test_validate_scholarship_eligibility_valid(self):
        """Test scholarship eligibility validation for valid scholarship."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            status=Scholarship.AwardStatus.ACTIVE,
            award_percentage=Decimal("50.00"),
            award_amount=None,
        )

        result = ScholarshipEligibilityService.validate_scholarship_eligibility(self.student, scholarship)

        self.assertTrue(result["is_eligible"])
        self.assertEqual(len(result["issues"]), 0)

    def test_validate_scholarship_eligibility_inactive_scholarship(self):
        """Test scholarship eligibility validation for inactive scholarship."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            status=Scholarship.AwardStatus.SUSPENDED,
        )

        result = ScholarshipEligibilityService.validate_scholarship_eligibility(self.student, scholarship)

        self.assertFalse(result["is_eligible"])
        self.assertIn("not currently active", result["issues"][0])

    def test_validate_scholarship_eligibility_no_award_configured(self):
        """Test scholarship eligibility validation with no award configured."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=None,
        )

        result = ScholarshipEligibilityService.validate_scholarship_eligibility(self.student, scholarship)

        self.assertFalse(result["is_eligible"])
        self.assertIn("no award amount or percentage configured", result["issues"][0])

    def test_validate_scholarship_eligibility_both_awards_configured(self):
        """Test scholarship eligibility validation with both percentage and amount."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("50.00"),
            award_amount=Decimal("1000.00"),
        )

        result = ScholarshipEligibilityService.validate_scholarship_eligibility(self.student, scholarship)

        self.assertFalse(result["is_eligible"])
        self.assertIn("cannot have both percentage and fixed amount", result["issues"][0])

    def test_get_scholarship_conflicts_no_conflicts(self):
        """Test scholarship conflict detection with no conflicts."""
        SimpleScholarshipFactory(
            student=self.student,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = ScholarshipEligibilityService.get_scholarship_conflicts(self.student)

        self.assertFalse(result["has_conflicts"])
        self.assertEqual(result["recommended_action"], "none")

    def test_get_scholarship_conflicts_multiple_scholarships(self):
        """Test scholarship conflict detection with multiple scholarships."""
        scholarship1 = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("50.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )
        scholarship2 = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = ScholarshipEligibilityService.get_scholarship_conflicts(self.student)

        self.assertTrue(result["has_conflicts"])
        self.assertEqual(result["total_conflicts"], 1)
        self.assertEqual(result["recommended_action"], "suspend_conflicting_scholarships")

        # Higher percentage scholarship should be recommended as best
        self.assertEqual(result["best_scholarship"], scholarship2)
        self.assertIn(scholarship1, result["conflicting_scholarships"])


@pytest.mark.django_db
class ScholarshipReportingServiceTest(TestCase):
    """Test ScholarshipReportingService functionality."""

    def test_get_sponsor_scholarship_summary_not_found(self):
        """Test sponsor summary for non-existent sponsor."""
        result = ScholarshipReportingService.get_sponsor_scholarship_summary("NONEXISTENT")

        self.assertIn("error", result)
        self.assertIn("not found", result["error"])

    def test_get_sponsor_scholarship_summary_no_students(self):
        """Test sponsor summary with no sponsored students."""
        SimpleSponsorFactory(code="TEST")

        result = ScholarshipReportingService.get_sponsor_scholarship_summary("TEST")

        self.assertEqual(result["sponsor"]["code"], "TEST")
        self.assertEqual(result["summary"]["total_sponsored_students"], 0)
        self.assertEqual(result["summary"]["total_active_scholarships"], 0)

    def test_get_sponsor_scholarship_summary_with_students(self):
        """Test sponsor summary with sponsored students and scholarships."""
        sponsor = SimpleSponsorFactory(
            code="TEST",
            name="Test Sponsor",
            default_discount_percentage=Decimal("75.00"),
            requests_consolidated_invoicing=True,
        )

        # Create sponsored students with scholarships
        sponsored_student1 = SimpleSponsoredStudentFactory(sponsor=sponsor)
        sponsored_student2 = SimpleSponsoredStudentFactory(sponsor=sponsor)

        SimpleScholarshipFactory(
            student=self.student,
            sponsored_student=sponsored_student1,
            scholarship_type=Scholarship.ScholarshipType.SPONSORED,
            award_percentage=Decimal("100.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )
        SimpleScholarshipFactory(
            student=self.student,
            sponsored_student=sponsored_student2,
            scholarship_type=Scholarship.ScholarshipType.SPONSORED,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = ScholarshipReportingService.get_sponsor_scholarship_summary("TEST")

        # Verify sponsor information
        self.assertEqual(result["sponsor"]["code"], "TEST")
        self.assertEqual(result["sponsor"]["name"], "Test Sponsor")

        # Verify summary statistics
        self.assertEqual(result["summary"]["total_sponsored_students"], 2)
        self.assertEqual(result["summary"]["total_active_scholarships"], 2)
        self.assertEqual(result["summary"]["average_discount"], Decimal("75.00"))

        # Verify billing preferences
        self.assertTrue(result["billing_preferences"]["consolidated_invoicing"])

        # Verify scholarship breakdown
        self.assertIn("SPONSORED", result["scholarship_breakdown"])
        sponsored_breakdown = result["scholarship_breakdown"]["SPONSORED"]
        self.assertEqual(sponsored_breakdown["count"], 2)
        self.assertEqual(sponsored_breakdown["total_percentage"], Decimal("175.00"))
        self.assertEqual(len(sponsored_breakdown["students"]), 2)


@pytest.mark.django_db
class ScholarshipBusinessLogicIntegrationTest(TestCase):
    """Integration tests for scholarship business logic."""

    def setUp(self):
        """Set up test data."""
        self.student = MockStudent("TEST001")

    def test_non_stacking_scholarship_rule(self):
        """Test that scholarships don't stack - only best one applies."""
        # Create multiple scholarships for same student
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("50.00"),
            status=Scholarship.AwardStatus.ACTIVE,
            name="Merit Scholarship",
        )
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
            name="Need-Based Aid",
        )

        # Calculate discount - should use only the best (75%)
        base_tuition = Decimal("1000.00")
        result = ScholarshipCalculationService.calculate_tuition_discount(self.student, base_tuition)

        # Should get 75% discount, not 125% (50% + 75%)
        self.assertEqual(result["discount_amount"], Decimal("750.00"))
        self.assertEqual(result["final_amount"], Decimal("250.00"))
        self.assertEqual(result["scholarship_name"], "Need-Based Aid")

    def test_monks_fixed_amount_priority(self):
        """Test that monks with fixed amounts get priority over percentages."""
        # High percentage scholarship
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("100.00"),
            award_amount=None,
            status=Scholarship.AwardStatus.ACTIVE,
            name="Full Merit Scholarship",
        )

        # Fixed amount scholarship (for monks)
        fixed_scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=Decimal("800.00"),
            status=Scholarship.AwardStatus.ACTIVE,
            name="Monk Support",
        )

        # Fixed amount should win even if percentage would give more discount
        best_deal = ScholarshipCalculationService.get_best_scholarship_for_student(self.student)
        self.assertEqual(best_deal["scholarship"], fixed_scholarship)

        # Verify calculation uses fixed amount
        base_tuition = Decimal("1000.00")
        result = ScholarshipCalculationService.calculate_tuition_discount(self.student, base_tuition)
        self.assertEqual(result["discount_amount"], Decimal("800.00"))
        self.assertEqual(result["scholarship_name"], "Monk Support")

    def test_sponsored_student_scholarship_integration(self):
        """Test integration between sponsored students and scholarships."""
        sponsor = SimpleSponsorFactory(
            code="CRST",
            name="Christian Reformed Service Team",
            default_discount_percentage=Decimal("100.00"),
        )

        sponsored_student = SimpleSponsoredStudentFactory(
            sponsor=sponsor,
            student=self.student,
        )

        scholarship = SimpleScholarshipFactory(
            student=self.student,
            sponsored_student=sponsored_student,
            scholarship_type=Scholarship.ScholarshipType.SPONSORED,
            award_percentage=Decimal("100.00"),
            status=Scholarship.AwardStatus.ACTIVE,
            name="CRST Full Scholarship",
        )

        # Verify best deal selection includes sponsored scholarship
        best_deal = ScholarshipCalculationService.get_best_scholarship_for_student(self.student)
        self.assertEqual(best_deal["scholarship"], scholarship)
        self.assertEqual(best_deal["benefit_source"], "sponsor_CRST")

        # Verify full discount calculation
        base_tuition = Decimal("1000.00")
        result = ScholarshipCalculationService.calculate_tuition_discount(self.student, base_tuition)
        self.assertEqual(result["discount_amount"], Decimal("1000.00"))
        self.assertEqual(result["final_amount"], Decimal("0.00"))
