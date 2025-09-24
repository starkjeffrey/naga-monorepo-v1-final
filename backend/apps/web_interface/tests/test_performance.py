"""
Performance tests for web interface views.

This module tests that views are optimized and don't have N+1 query issues.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.curriculum.models import Course, Division, Major, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader

# from apps.common.factories import UserFactory  # Commented out due to cyclic dependency

User = get_user_model()


class ViewPerformanceTests(TestCase):
    """Test suite for view performance optimizations."""

    def setUp(self):
        """Set up test data."""
        # Create admin user with staff permissions
        self.staff_user = User.objects.create_user(username="teststaff", email="test@example.com", password="testpass")
        self.staff_user.is_staff = True
        self.staff_user.save()

        # Create test data
        self.division = Division.objects.create(name="Test Division", code="TEST")

        self.major = Major.objects.create(name="Test Major", code="TMAJ", division=self.division)

        self.term = Term.objects.create(
            name="Test Term", start_date="2024-01-01", end_date="2024-05-01", is_active=True
        )

        # Create multiple courses for testing
        self.courses = []
        for i in range(10):
            course = Course.objects.create(
                title=f"Test Course {i}",
                course_code=f"TEST{i:03d}",
                credit_hours=3,
                division=self.division,
                major=self.major,
                is_active=True,
            )
            self.courses.append(course)

            # Create class headers for enrollment testing
            ClassHeader.objects.create(course=course, term=self.term, max_enrollment=25, is_active=True)

    def test_course_list_view_no_duplicate_count_query(self):
        """Verify CourseListView doesn't execute duplicate count queries."""
        self.client.force_login(self.staff_user)

        # The view should only need:
        # 1. Query for courses with select_related and annotations
        # 2. Maybe 1 additional query for pagination or filtering
        # But NOT an extra query for .count() since we use len() on evaluated queryset
        with self.assertNumQueries(2):  # Allow 2 queries max for the view
            response = self.client.get(reverse("web_interface:course-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "total_courses")

    def test_enrollment_management_view_query_efficiency(self):
        """Verify EnrollmentManagementView doesn't have N+1 queries."""
        self.client.force_login(self.staff_user)

        # Create some test enrollments to make sure the queries are consistent
        student_person = Person.objects.create(first_name="Test", last_name="Student", email="test@example.com")
        student = StudentProfile.objects.create(person=student_person, student_id="TEST001")

        class_header = ClassHeader.objects.first()
        ClassHeaderEnrollment.objects.create(student=student, class_header=class_header, status="ENROLLED")

        # The view should be efficient regardless of the number of classes/enrollments
        # Allowing up to 10 queries for a complex dashboard view
        with self.assertNumQueries(10):
            response = self.client.get(reverse("web_interface:enrollment-management"))

        self.assertEqual(response.status_code, 200)
        # Verify the statistics are being calculated
        self.assertIn("stats", response.context)
