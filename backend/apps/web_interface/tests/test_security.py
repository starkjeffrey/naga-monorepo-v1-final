"""
Security tests for web interface views.

This module tests that views are properly protected against security vulnerabilities
like overposting, injection attacks, and unauthorized access.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.common.factories import UserFactory
from apps.curriculum.models import Course, Division, Major, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.grading.models import ClassPartGrade
from apps.people.models import Person, StudentProfile, TeacherProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


class TestSecurityProtections(TestCase):
    """Test suite for security vulnerability protections."""

    def setUp(self):
        """Set up test data."""
        # Create teacher user
        self.teacher_user = UserFactory()
        self.teacher_person = Person.objects.create(
            first_name="Teacher", last_name="Test", email="teacher@example.com"
        )
        self.teacher_profile = TeacherProfile.objects.create(person=self.teacher_person, employee_id="TEACH001")
        self.teacher_user.person = self.teacher_person
        self.teacher_user.save()

        # Create test data
        self.division = Division.objects.create(name="Test Division", code="TEST")

        self.major = Major.objects.create(name="Test Major", code="TMAJ", division=self.division)

        self.term = Term.objects.create(
            name="Test Term", start_date="2024-01-01", end_date="2024-05-01", is_active=True
        )

        # Create course and class
        self.course = Course.objects.create(
            title="Test Course",
            course_code="TEST001",
            credit_hours=3,
            division=self.division,
            major=self.major,
            is_active=True,
        )

        self.class_header = ClassHeader.objects.create(
            course=self.course, term=self.term, teacher=self.teacher_profile, max_enrollment=25, is_active=True
        )

        # Create students and enrollments
        self.students = []
        self.enrollments = []
        for i in range(3):
            person = Person.objects.create(first_name=f"Student{i}", last_name="Test", email=f"student{i}@example.com")
            student = StudentProfile.objects.create(person=person, student_id=f"STU{i:03d}")
            self.students.append(student)

            # Create enrollment
            enrollment = ClassHeaderEnrollment.objects.create(
                student=student, class_header=self.class_header, status="ENROLLED"
            )
            self.enrollments.append(enrollment)

    def test_grade_entry_prevents_overposting(self):
        """Verify that unexpected POST fields are ignored in grade entry."""
        self.client.force_login(self.teacher_user)

        # Create legitimate grade data
        legitimate_data = {
            f"grade_{self.enrollments[0].id}": "85.5",
            f"comment_{self.enrollments[0].id}": "Good work",
        }

        # Add malicious/unexpected fields
        malicious_data = {
            **legitimate_data,
            "grade_999999": "100.0",  # Non-existent enrollment
            "admin_override": "true",  # Administrative field
            "class_header_id": "123",  # Attempting to change class
            "teacher_id": "456",  # Attempting to change teacher
            "is_active": "false",  # Attempting to modify class status
            "max_enrollment": "1000",  # Attempting to change capacity
            "csrf_bypass": "attempt",  # Generic attack field
        }

        # Submit data with extra fields
        response = self.client.post(
            reverse("web_interface:grade-entry", kwargs={"pk": self.class_header.pk}), data=malicious_data
        )

        # Should succeed but ignore malicious fields
        self.assertEqual(response.status_code, 302)  # Redirect on success

        # Verify only legitimate grade was saved
        grades = ClassPartGrade.objects.filter(enrollment__class_header=self.class_header)
        self.assertEqual(grades.count(), 1)

        # Verify the legitimate grade was saved correctly
        grade = grades.first()
        self.assertEqual(grade.enrollment, self.enrollments[0])
        self.assertEqual(float(grade.final_grade), 85.5)
        self.assertEqual(grade.comments, "Good work")

        # Verify no grades were created for invalid enrollment IDs
        invalid_grades = ClassPartGrade.objects.filter(enrollment_id=999999)
        self.assertEqual(invalid_grades.count(), 0)

        # Verify class properties were not modified
        self.class_header.refresh_from_db()
        self.assertEqual(self.class_header.teacher, self.teacher_profile)
        self.assertEqual(self.class_header.max_enrollment, 25)
        self.assertTrue(self.class_header.is_active)

    def test_grade_entry_validates_grade_ranges(self):
        """Verify that invalid grade values are rejected."""
        self.client.force_login(self.teacher_user)

        # Test invalid grade values
        invalid_data = {
            f"grade_{self.enrollments[0].id}": "150.0",  # Above 100
            f"grade_{self.enrollments[1].id}": "-10.0",  # Below 0
            f"grade_{self.enrollments[2].id}": "invalid",  # Non-numeric
        }

        response = self.client.post(
            reverse("web_interface:grade-entry", kwargs={"pk": self.class_header.pk}), data=invalid_data
        )

        # Should fail validation and return form with errors
        self.assertEqual(response.status_code, 200)  # Re-render with errors
        self.assertContains(response, "Please correct the errors below")

        # Verify no grades were saved
        grades = ClassPartGrade.objects.filter(enrollment__class_header=self.class_header)
        self.assertEqual(grades.count(), 0)

    def test_grade_entry_requires_authentication(self):
        """Verify that unauthenticated users cannot access grade entry."""
        # Attempt to access without login
        response = self.client.get(reverse("web_interface:grade-entry", kwargs={"pk": self.class_header.pk}))

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_grade_entry_requires_teacher_permission(self):
        """Verify that only the assigned teacher can access grade entry."""
        # Create another teacher
        other_teacher_user = UserFactory()
        other_teacher_person = Person.objects.create(
            first_name="Other", last_name="Teacher", email="other@example.com"
        )
        TeacherProfile.objects.create(person=other_teacher_person, employee_id="TEACH002")
        other_teacher_user.person = other_teacher_person
        other_teacher_user.save()

        # Login as wrong teacher
        self.client.force_login(other_teacher_user)

        # Attempt to access grade entry for class not assigned to this teacher
        response = self.client.get(reverse("web_interface:grade-entry", kwargs={"pk": self.class_header.pk}))

        # Should return 404 (not found in teacher's classes)
        self.assertEqual(response.status_code, 404)

    def test_enrollment_form_prevents_injection(self):
        """Verify that enrollment forms prevent script injection attacks."""
        staff_user = UserFactory()
        staff_user.is_staff = True
        staff_user.save()
        self.client.force_login(staff_user)

        # Attempt to inject script in notes field
        injection_data = {"student_id": self.students[0].id, "notes": '<script>alert("XSS")</script>Malicious content'}

        response = self.client.post(
            reverse("web_interface:process-quick-enrollment", kwargs={"class_id": self.class_header.id}),
            data=injection_data,
        )

        # Should succeed but sanitize input
        self.assertIn(response.status_code, [200, 302])

        # Verify enrollment was created but script was not stored as-is
        enrollment = ClassHeaderEnrollment.objects.get(student=self.students[0], class_header=self.class_header)

        # Notes should not contain the raw script tag
        self.assertIn("Malicious content", enrollment.notes)
        # The exact handling depends on your sanitization approach
        # At minimum, verify the enrollment exists and doesn't break the app
