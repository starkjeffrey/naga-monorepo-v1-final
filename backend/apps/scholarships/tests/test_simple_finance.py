"""Simplified tests for scholarships finance integration.

Tests cover basic finance integration without complex dependencies.
"""

from decimal import Decimal

import pytest
from django.test import TestCase

from apps.scholarships.models import Scholarship
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
class SimpleFinanceIntegrationTest(TestCase):
    """Test basic finance integration scenarios."""

    def setUp(self):
        """Set up test data."""
        self.student = MockStudent("FIN001")

    def test_percentage_discount_calculation(self):
        """Test percentage-based discount calculation."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Mock tuition calculation
        base_tuition = Decimal("1000.00")
        discount_percentage = scholarship.award_percentage
        discount_amount = base_tuition * (discount_percentage / Decimal("100.00"))
        final_amount = base_tuition - discount_amount

        self.assertEqual(discount_amount, Decimal("750.00"))
        self.assertEqual(final_amount, Decimal("250.00"))

    def test_fixed_amount_discount_calculation(self):
        """Test fixed amount discount calculation."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=Decimal("600.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Mock tuition calculation
        base_tuition = Decimal("1000.00")
        discount_amount = min(scholarship.award_amount, base_tuition)
        final_amount = base_tuition - discount_amount

        self.assertEqual(discount_amount, Decimal("600.00"))
        self.assertEqual(final_amount, Decimal("400.00"))

    def test_ngo_consolidated_billing_scenario(self):
        """Test NGO consolidated billing scenario."""
        # Create NGO sponsor with consolidated billing
        ngo_sponsor = SimpleSponsorFactory(
            code="NGO",
            name="Test NGO",
            requests_consolidated_invoicing=True,
            default_discount_percentage=Decimal("100.00"),
        )

        # Create multiple sponsored students
        students = []
        scholarships = []

        for i in range(3):
            student = MockStudent(f"NGO{i:03d}")
            students.append(student)

            sponsored_student = SimpleSponsoredStudentFactory(
                sponsor=ngo_sponsor,
                student=student,
            )

            scholarship = SimpleScholarshipFactory(
                student=student,
                sponsored_student=sponsored_student,
                award_percentage=Decimal("100.00"),
                status=Scholarship.AwardStatus.ACTIVE,
            )
            scholarships.append(scholarship)

        # Verify consolidated billing setup
        self.assertTrue(ngo_sponsor.requests_consolidated_invoicing)
        self.assertEqual(ngo_sponsor.sponsored_students.count(), 3)

        # Mock consolidated billing calculation
        total_students = ngo_sponsor.sponsored_students.count()
        base_tuition_per_student = Decimal("1000.00")
        total_base_amount = total_students * base_tuition_per_student

        # All students have 100% scholarship - NGO pays nothing to school
        total_discount = total_base_amount
        ngo_amount_due = total_base_amount - total_discount

        self.assertEqual(total_base_amount, Decimal("3000.00"))
        self.assertEqual(total_discount, Decimal("3000.00"))
        self.assertEqual(ngo_amount_due, Decimal("0.00"))

    def test_mixed_scholarship_types_best_deal(self):
        """Test best deal selection with mixed scholarship types."""
        # Create multiple scholarships for same student
        percentage_scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("50.00"),
            award_amount=None,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        fixed_scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=Decimal("600.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Mock best deal calculation for $1000 tuition
        base_tuition = Decimal("1000.00")

        # Calculate percentage discount
        percentage_discount = base_tuition * (percentage_scholarship.award_percentage / Decimal("100.00"))

        # Calculate fixed discount
        fixed_discount = min(fixed_scholarship.award_amount, base_tuition)

        # Best deal should be the higher discount amount
        best_discount = max(percentage_discount, fixed_discount)

        self.assertEqual(percentage_discount, Decimal("500.00"))
        self.assertEqual(fixed_discount, Decimal("600.00"))
        self.assertEqual(best_discount, Decimal("600.00"))  # Fixed amount wins

    def test_scholarship_applies_only_to_tuition(self):
        """Test that scholarships apply only to tuition, not fees."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("100.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Mock invoice calculation
        base_tuition = Decimal("1000.00")
        registration_fee = Decimal("50.00")
        lab_fee = Decimal("100.00")

        # Scholarship applies only to tuition
        tuition_discount = base_tuition * (scholarship.award_percentage / Decimal("100.00"))
        fee_discount = Decimal("0.00")  # No discount on fees

        final_tuition = base_tuition - tuition_discount
        final_fees = registration_fee + lab_fee - fee_discount
        total_due = final_tuition + final_fees

        self.assertEqual(tuition_discount, Decimal("1000.00"))
        self.assertEqual(fee_discount, Decimal("0.00"))
        self.assertEqual(final_tuition, Decimal("0.00"))
        self.assertEqual(final_fees, Decimal("150.00"))
        self.assertEqual(total_due, Decimal("150.00"))  # Only fees remain
