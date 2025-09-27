"""Tests for scholarships finance integration.

Tests cover the integration between scholarships and finance systems,
including NGO billing coordination and tuition discount calculations.
"""

from decimal import Decimal

import pytest
from django.test import TestCase

from apps.scholarships.finance_integration import ScholarshipFinanceIntegrationService
from apps.scholarships.models import Scholarship, SponsoredStudent
from apps.scholarships.tests.factories import (
    ScholarshipFactory,
    SponsoredStudentFactory,
    SponsorFactory,
)


@pytest.mark.django_db
class ScholarshipFinanceIntegrationServiceTest(TestCase):
    """Test ScholarshipFinanceIntegrationService functionality."""

    def setUp(self):
        """Set up test data."""
        from apps.people.tests.factories import StudentProfileFactory

        self.student = StudentProfileFactory()

    def test_calculate_student_tuition_discount_no_scholarships(self):
        """Test tuition discount calculation with no scholarships."""
        base_tuition = Decimal("1000.00")
        result = ScholarshipFinanceIntegrationService.calculate_student_tuition_discount(self.student, base_tuition)

        self.assertEqual(result["original_amount"], base_tuition)
        self.assertEqual(result["discount_amount"], Decimal("0.00"))
        self.assertEqual(result["final_amount"], base_tuition)
        self.assertFalse(result["has_discount"])
        self.assertFalse(result["applies_to_fees"])
        self.assertEqual(result["discount_source"], "none")

    def test_calculate_student_tuition_discount_with_scholarship(self):
        """Test tuition discount calculation with active scholarship."""
        ScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
            name="Merit Scholarship",
        )

        base_tuition = Decimal("1000.00")
        result = ScholarshipFinanceIntegrationService.calculate_student_tuition_discount(self.student, base_tuition)

        self.assertEqual(result["original_amount"], Decimal("1000.00"))
        self.assertEqual(result["discount_amount"], Decimal("750.00"))
        self.assertEqual(result["final_amount"], Decimal("250.00"))
        self.assertTrue(result["has_discount"])
        self.assertFalse(result["applies_to_fees"])  # Never applies to fees
        self.assertEqual(result["scholarship_name"], "Merit Scholarship")

    def test_check_special_billing_requirements_no_sponsorship(self):
        """Test special billing check with no sponsorship."""
        result = ScholarshipFinanceIntegrationService._check_special_billing_requirements(self.student)
        self.assertFalse(result)

    def test_check_special_billing_requirements_with_consolidated_billing(self):
        """Test special billing check with consolidated billing sponsorship."""
        sponsor = SponsorFactory(
            requests_consolidated_invoicing=True,
            is_active=True,
        )
        SponsoredStudentFactory(
            sponsor=sponsor,
            student=self.student,
        )

        result = ScholarshipFinanceIntegrationService._check_special_billing_requirements(self.student)
        self.assertTrue(result)

    def test_check_special_billing_requirements_no_consolidated_billing(self):
        """Test special billing check without consolidated billing."""
        sponsor = SponsorFactory(
            requests_consolidated_invoicing=False,
            is_active=True,
        )
        SponsoredStudentFactory(
            sponsor=sponsor,
            student=self.student,
        )

        result = ScholarshipFinanceIntegrationService._check_special_billing_requirements(self.student)
        self.assertFalse(result)

    def test_get_ngo_billing_info_no_sponsorship(self):
        """Test NGO billing info with no sponsorship."""
        result = ScholarshipFinanceIntegrationService._get_ngo_billing_info(self.student)
        self.assertIsNone(result)

    def test_get_ngo_billing_info_with_consolidated_billing(self):
        """Test NGO billing info with consolidated billing sponsorship."""
        sponsor = SponsorFactory(
            code="CRST",
            name="Christian Reformed Service Team",
            billing_email="billing@crst.org",
            contact_email="contact@crst.org",
            requests_consolidated_invoicing=True,
            requests_tax_addition=True,
            is_active=True,
        )
        SponsoredStudentFactory(
            sponsor=sponsor,
            student=self.student,
        )

        result = ScholarshipFinanceIntegrationService._get_ngo_billing_info(self.student)

        self.assertIsNotNone(result)
        self.assertEqual(result["sponsor_code"], "CRST")
        self.assertEqual(result["sponsor_name"], "Christian Reformed Service Team")
        self.assertEqual(result["billing_email"], "billing@crst.org")
        self.assertTrue(result["consolidated_invoicing"])
        self.assertTrue(result["add_tax"])
        self.assertEqual(result["billing_contact"], "contact@crst.org")

    def test_get_students_for_consolidated_billing_nonexistent_sponsor(self):
        """Test consolidated billing student list for non-existent sponsor."""
        result = ScholarshipFinanceIntegrationService.get_students_for_consolidated_billing("NONEXISTENT")
        self.assertEqual(result, [])

    def test_get_students_for_consolidated_billing_no_consolidated_billing(self):
        """Test consolidated billing student list for sponsor without consolidated billing."""
        SponsorFactory(
            code="TEST",
            requests_consolidated_invoicing=False,
            is_active=True,
        )

        result = ScholarshipFinanceIntegrationService.get_students_for_consolidated_billing("TEST")
        self.assertEqual(result, [])

    def test_get_students_for_consolidated_billing_with_students(self):
        """Test consolidated billing student list with sponsored students."""
        sponsor = SponsorFactory(
            code="CRST",
            requests_consolidated_invoicing=True,
            is_active=True,
        )

        # Create multiple sponsored students
        from apps.people.tests.factories import StudentProfileFactory

        student1 = StudentProfileFactory()
        student2 = StudentProfileFactory()

        SponsoredStudentFactory(
            sponsor=sponsor,
            student=student1,
            sponsorship_type=SponsoredStudent.SponsorshipType.FULL,
        )
        SponsoredStudentFactory(
            sponsor=sponsor,
            student=student2,
            sponsorship_type=SponsoredStudent.SponsorshipType.PARTIAL,
        )

        # Add scholarships to test scholarship detection
        ScholarshipFactory(
            student=student1,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = ScholarshipFinanceIntegrationService.get_students_for_consolidated_billing("CRST")

        self.assertEqual(len(result), 2)

        # Verify student information
        student_ids = [s["student_id"] for s in result]
        self.assertIn(student1.student_id, student_ids)
        self.assertIn(student2.student_id, student_ids)

        # Verify scholarship detection
        student1_info = next(s for s in result if s["student_id"] == student1.student_id)
        student2_info = next(s for s in result if s["student_id"] == student2.student_id)

        self.assertTrue(student1_info["has_scholarship_discount"])  # Has scholarship
        self.assertFalse(student2_info["has_scholarship_discount"])  # No scholarship

        # Verify sponsorship information
        self.assertEqual(student1_info["sponsorship_type"], "FULL")
        self.assertEqual(student2_info["sponsorship_type"], "PARTIAL")

    def test_get_sponsor_billing_preferences_not_found(self):
        """Test sponsor billing preferences for non-existent sponsor."""
        result = ScholarshipFinanceIntegrationService.get_sponsor_billing_preferences("NONEXISTENT")
        self.assertIsNone(result)

    def test_get_sponsor_billing_preferences_inactive_sponsor(self):
        """Test sponsor billing preferences for inactive sponsor."""
        SponsorFactory(
            code="INACTIVE",
            is_active=False,
        )

        result = ScholarshipFinanceIntegrationService.get_sponsor_billing_preferences("INACTIVE")
        self.assertIsNone(result)

    def test_get_sponsor_billing_preferences_active_sponsor(self):
        """Test sponsor billing preferences for active sponsor."""
        SponsorFactory(
            code="ACTIVE",
            name="Active Sponsor",
            billing_email="billing@active.org",
            contact_email="contact@active.org",
            requests_consolidated_invoicing=True,
            requests_tax_addition=False,
            is_active=True,
        )

        result = ScholarshipFinanceIntegrationService.get_sponsor_billing_preferences("ACTIVE")

        self.assertIsNotNone(result)
        self.assertTrue(result["consolidated_invoicing"])
        self.assertFalse(result["add_tax"])
        self.assertEqual(result["billing_email"], "billing@active.org")
        self.assertEqual(result["contact_email"], "contact@active.org")
        self.assertEqual(result["sponsor_name"], "Active Sponsor")

    def test_handle_scholarship_status_change_not_found(self):
        """Test scholarship status change handling for non-existent scholarship."""
        result = ScholarshipFinanceIntegrationService.handle_scholarship_status_change(999999, "PENDING", "ACTIVE", 1)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Scholarship not found")

    def test_handle_scholarship_status_change_no_billing_impact(self):
        """Test scholarship status change with no billing impact."""
        scholarship = ScholarshipFactory()

        result = ScholarshipFinanceIntegrationService.handle_scholarship_status_change(
            scholarship.id,
            "PENDING",
            "DRAFT",
            1,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "no_billing_impact")

    def test_handle_scholarship_status_change_billing_impact(self):
        """Test scholarship status change with billing impact."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="testuser", password="testpass")

        scholarship = ScholarshipFactory(
            student=self.student,
            status=Scholarship.AwardStatus.PENDING,
        )

        result = ScholarshipFinanceIntegrationService.handle_scholarship_status_change(
            scholarship.id,
            "PENDING",
            "ACTIVE",
            user.id,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "billing_affected")
        self.assertEqual(result["student_id"], self.student.student_id)
        self.assertFalse(result["has_conflicts"])  # Single scholarship, no conflicts

    def test_handle_scholarship_status_change_with_conflicts(self):
        """Test scholarship status change that creates conflicts."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="testuser", password="testpass")

        # Create multiple scholarships for same student
        ScholarshipFactory(
            student=self.student,
            status=Scholarship.AwardStatus.ACTIVE,
        )
        scholarship2 = ScholarshipFactory(
            student=self.student,
            status=Scholarship.AwardStatus.PENDING,
        )

        result = ScholarshipFinanceIntegrationService.handle_scholarship_status_change(
            scholarship2.id,
            "PENDING",
            "ACTIVE",
            user.id,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "billing_affected")
        self.assertTrue(result["has_conflicts"])  # Multiple active scholarships
        self.assertEqual(result["conflicts"]["total"], 1)
        self.assertEqual(
            result["conflicts"]["recommended_action"],
            "suspend_conflicting_scholarships",
        )

    def test_integration_with_ngo_billing_workflow(self):
        """Test complete NGO billing workflow integration."""
        # Set up NGO sponsor with consolidated billing
        sponsor = SponsorFactory(
            code="USAID",
            name="US Agency for International Development",
            billing_email="billing@usaid.gov",
            requests_consolidated_invoicing=True,
            requests_tax_addition=True,
            is_active=True,
        )

        # Create sponsored student with scholarship
        sponsored_student = SponsoredStudentFactory(
            sponsor=sponsor,
            student=self.student,
            sponsorship_type=SponsoredStudent.SponsorshipType.FULL,
        )

        ScholarshipFactory(
            student=self.student,
            sponsored_student=sponsored_student,
            award_percentage=Decimal("100.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Test tuition discount calculation
        base_tuition = Decimal("1000.00")
        discount_result = ScholarshipFinanceIntegrationService.calculate_student_tuition_discount(
            self.student,
            base_tuition,
        )

        # Verify full discount
        self.assertEqual(discount_result["discount_amount"], Decimal("1000.00"))
        self.assertEqual(discount_result["final_amount"], Decimal("0.00"))
        self.assertTrue(discount_result["requires_special_billing"])

        # Verify NGO billing info
        ngo_info = discount_result["ngo_billing_info"]
        self.assertEqual(ngo_info["sponsor_code"], "USAID")
        self.assertTrue(ngo_info["consolidated_invoicing"])
        self.assertTrue(ngo_info["add_tax"])

        # Test consolidated billing student list
        students = ScholarshipFinanceIntegrationService.get_students_for_consolidated_billing("USAID")
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0]["student_id"], self.student.student_id)
        self.assertTrue(students[0]["has_scholarship_discount"])

        # Test sponsor billing preferences
        preferences = ScholarshipFinanceIntegrationService.get_sponsor_billing_preferences("USAID")
        self.assertTrue(preferences["consolidated_invoicing"])
        self.assertTrue(preferences["add_tax"])
        self.assertEqual(preferences["billing_email"], "billing@usaid.gov")
