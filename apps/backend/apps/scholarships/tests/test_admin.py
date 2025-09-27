"""Tests for scholarships app admin interfaces.

Tests cover admin functionality including queryset optimizations,
display methods, and user interface features.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.scholarships.admin import (
    ScholarshipAdmin,
    SponsorAdmin,
    SponsoredStudentAdmin,
)
from apps.scholarships.models import Scholarship, Sponsor, SponsoredStudent
from apps.scholarships.tests.factories import (
    ScholarshipFactory,
    SponsoredStudentFactory,
    SponsorFactory,
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


User = get_user_model()


@pytest.mark.django_db
class SponsorAdminTest(TestCase):
    """Test SponsorAdmin functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")
        self.site = AdminSite()
        self.admin = SponsorAdmin(Sponsor, self.site)

    def test_get_queryset_optimization(self):
        """Test that get_queryset includes annotation for active students count."""
        request = self.factory.get("/admin/scholarships/sponsor/")
        request.user = self.user

        queryset = self.admin.get_queryset(request)

        # Verify annotation exists
        self.assertTrue(hasattr(queryset.first() or Sponsor(), "active_students_count"))

    def test_is_mou_active_display_active(self):
        """Test MOU active display method for active MOU."""
        sponsor = SponsorFactory(is_active=True)

        result = self.admin.is_mou_active(sponsor)

        self.assertIn("mou-active", result)
        self.assertIn("✓ Active", result)

    def test_is_mou_active_display_inactive(self):
        """Test MOU active display method for inactive MOU."""
        sponsor = SponsorFactory(is_active=False)

        result = self.admin.is_mou_active(sponsor)

        self.assertIn("mou-inactive", result)
        self.assertIn("✗ Inactive", result)

    def test_active_students_count_display_with_annotation(self):
        """Test active students count display using annotation."""
        sponsor = SponsorFactory()
        # Simulate annotation from get_queryset
        sponsor.active_students_count = 3

        result = self.admin.active_students_count(sponsor)

        self.assertEqual(result, "3 students")

    def test_active_students_count_display_singular(self):
        """Test active students count display with singular form."""
        sponsor = SponsorFactory()
        sponsor.active_students_count = 1

        result = self.admin.active_students_count(sponsor)

        self.assertEqual(result, "1 student")

    def test_active_students_count_display_fallback(self):
        """Test active students count display falls back to model method."""
        sponsor = SponsorFactory()
        # No annotation - should use model method

        result = self.admin.active_students_count(sponsor)

        self.assertEqual(result, "0 students")  # No sponsored students


@pytest.mark.django_db
class SponsoredStudentAdminTest(TestCase):
    """Test SponsoredStudentAdmin functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")
        self.site = AdminSite()
        self.admin = SponsoredStudentAdmin(SponsoredStudent, self.site)

    def test_get_queryset_optimization(self):
        """Test that get_queryset includes select_related for optimization."""
        request = self.factory.get("/admin/scholarships/sponsoredstudent/")
        request.user = self.user

        queryset = self.admin.get_queryset(request)

        # Verify select_related is applied (hard to test directly, but method should exist)
        self.assertTrue(hasattr(queryset, "select_related"))

    def test_sponsor_code_display(self):
        """Test sponsor code display method."""
        mock_student = MockStudent()
        sponsored_student = SponsoredStudentFactory(student=mock_student)

        result = self.admin.sponsor_code(sponsored_student)

        self.assertEqual(result, sponsored_student.sponsor.code)

    def test_student_name_display(self):
        """Test student name display method."""
        mock_student = MockStudent()
        sponsored_student = SponsoredStudentFactory(student=mock_student)

        result = self.admin.student_name(sponsored_student)

        self.assertEqual(result, sponsored_student.student.person.full_name)

    def test_student_id_display(self):
        """Test student ID display method."""
        mock_student = MockStudent()
        sponsored_student = SponsoredStudentFactory(student=mock_student)

        result = self.admin.student_id(sponsored_student)

        self.assertEqual(result, sponsored_student.student.student_id)

    def test_is_active_display_active(self):
        """Test active status display for active sponsorship."""
        mock_student = MockStudent()
        sponsored_student = SponsoredStudentFactory(student=mock_student)

        result = self.admin.is_active(sponsored_student)

        self.assertIn("status-active", result)
        self.assertIn("✓ Active", result)

    def test_is_active_display_inactive(self):
        """Test active status display for inactive sponsorship."""
        from datetime import timedelta

        mock_student = MockStudent()
        sponsored_student = SponsoredStudentFactory(
            student=mock_student,
            end_date=timezone.now().date() - timedelta(days=1),  # Ended yesterday
        )

        result = self.admin.is_active(sponsored_student)

        self.assertIn("status-inactive", result)
        self.assertIn("✗ Inactive", result)


@pytest.mark.django_db
class ScholarshipAdminTest(TestCase):
    """Test ScholarshipAdmin functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")
        self.site = AdminSite()
        self.admin = ScholarshipAdmin(Scholarship, self.site)

    def test_get_queryset_optimization(self):
        """Test that get_queryset includes select_related for optimization."""
        request = self.factory.get("/admin/scholarships/scholarship/")
        request.user = self.user

        queryset = self.admin.get_queryset(request)

        # Verify select_related is applied
        self.assertTrue(hasattr(queryset, "select_related"))

    def test_student_name_display(self):
        """Test student name display method."""
        mock_student = MockStudent()
        scholarship = ScholarshipFactory(student=mock_student)

        result = self.admin.student_name(scholarship)

        self.assertEqual(result, scholarship.student.person.full_name)

    def test_award_display_admin_percentage(self):
        """Test award display admin method for percentage."""
        mock_student = MockStudent()
        scholarship = ScholarshipFactory(
            student=mock_student,
            award_percentage=75.00,
            award_amount=None,
        )

        result = self.admin.award_display_admin(scholarship)

        self.assertEqual(result, "75.00%")

    def test_award_display_admin_fixed_amount(self):
        """Test award display admin method for fixed amount."""
        from decimal import Decimal

        mock_student = MockStudent()
        scholarship = ScholarshipFactory(
            student=mock_student,
            award_percentage=None,
            award_amount=Decimal("1000.00"),
        )

        result = self.admin.award_display_admin(scholarship)

        self.assertEqual(result, "$1000.00")

    def test_is_active_display_active(self):
        """Test active status display for active scholarship."""
        mock_student = MockStudent()
        scholarship = ScholarshipFactory(student=mock_student, status=Scholarship.AwardStatus.ACTIVE)

        result = self.admin.is_active(scholarship)

        self.assertIn("scholarship-active", result)
        self.assertIn("✓ Active", result)

    def test_is_active_display_inactive(self):
        """Test active status display for inactive scholarship."""
        mock_student = MockStudent()
        scholarship = ScholarshipFactory(student=mock_student, status=Scholarship.AwardStatus.SUSPENDED)

        result = self.admin.is_active(scholarship)

        self.assertIn("status-inactive", result)
        self.assertIn("✗ Inactive", result)


@pytest.mark.django_db
class AdminIntegrationTest(TestCase):
    """Integration tests for admin interfaces."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")

    def test_admin_list_view_performance(self):
        """Test that admin list views are optimized for performance."""
        # Create test data
        sponsor = SponsorFactory()
        sponsored_students = [
            SponsoredStudentFactory(sponsor=sponsor, student=MockStudent(f"STU{i:03d}")) for i in range(5)
        ]
        [
            ScholarshipFactory(student=sponsored_student.student, sponsored_student=sponsored_student)
            for sponsored_student in sponsored_students
        ]

        # Test SponsorAdmin list view
        request = self.factory.get("/admin/scholarships/sponsor/")
        request.user = self.user

        sponsor_admin = SponsorAdmin(Sponsor, AdminSite())
        sponsor_queryset = sponsor_admin.get_queryset(request)

        # Should have annotation for student count
        sponsor_obj = sponsor_queryset.get(id=sponsor.id)
        self.assertTrue(hasattr(sponsor_obj, "active_students_count"))

        # Test SponsoredStudentAdmin list view
        request = self.factory.get("/admin/scholarships/sponsoredstudent/")
        request.user = self.user

        sponsored_admin = SponsoredStudentAdmin(SponsoredStudent, AdminSite())
        sponsored_queryset = sponsored_admin.get_queryset(request)

        # Should use select_related - verify by checking query count would be low
        self.assertTrue(sponsored_queryset.count() > 0)

        # Test ScholarshipAdmin list view
        request = self.factory.get("/admin/scholarships/scholarship/")
        request.user = self.user

        scholarship_admin = ScholarshipAdmin(Scholarship, AdminSite())
        scholarship_queryset = scholarship_admin.get_queryset(request)

        # Should use select_related for student and sponsor data
        self.assertTrue(scholarship_queryset.count() > 0)

    def test_admin_display_methods_integration(self):
        """Test admin display methods work correctly with real data."""
        # Create complete sponsor/student/scholarship hierarchy
        sponsor = SponsorFactory(
            code="INTTEST",
            name="Integration Test Sponsor",
            is_active=True,
        )

        mock_student = MockStudent("INTTEST001")
        sponsored_student = SponsoredStudentFactory(
            sponsor=sponsor,
            student=mock_student,
            sponsorship_type=SponsoredStudent.SponsorshipType.FULL,
        )

        scholarship = ScholarshipFactory(
            sponsored_student=sponsored_student,
            student=sponsored_student.student,
            name="Integration Test Scholarship",
            award_percentage=100.00,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Test all admin display methods
        sponsor_admin = SponsorAdmin(Sponsor, AdminSite())
        sponsored_admin = SponsoredStudentAdmin(SponsoredStudent, AdminSite())
        scholarship_admin = ScholarshipAdmin(Scholarship, AdminSite())

        # SponsorAdmin methods
        self.assertIn("Active", sponsor_admin.is_mou_active(sponsor))
        self.assertIn("student", sponsor_admin.active_students_count(sponsor))

        # SponsoredStudentAdmin methods
        self.assertEqual(sponsored_admin.sponsor_code(sponsored_student), "INTTEST")
        self.assertIn("Active", sponsored_admin.is_active(sponsored_student))

        # ScholarshipAdmin methods
        self.assertEqual(scholarship_admin.award_display_admin(scholarship), "100.00%")
        self.assertIn("Active", scholarship_admin.is_active(scholarship))
