"""
Enrollment concurrency tests for web interface views.

This module tests that enrollment operations are properly protected against
race conditions and concurrent access issues.
"""

import threading

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.urls import reverse

from apps.common.factories import UserFactory
from apps.curriculum.models import Course, Division, Major, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


class TestEnrollmentConcurrency(TransactionTestCase):
    """Test suite for enrollment concurrency and race conditions."""

    def setUp(self):
        """Set up test data."""
        # Create staff user
        self.staff_user = UserFactory()
        self.staff_user.is_staff = True
        self.staff_user.save()

        # Create test data
        self.division = Division.objects.create(name="Test Division", code="TEST")

        self.major = Major.objects.create(name="Test Major", code="TMAJ", division=self.division)

        self.term = Term.objects.create(
            name="Test Term", start_date="2024-01-01", end_date="2024-05-01", is_active=True
        )

        # Create course
        self.course = Course.objects.create(
            title="Test Course",
            course_code="TEST001",
            credit_hours=3,
            division=self.division,
            major=self.major,
            is_active=True,
        )

        # Create class with only 1 available seat
        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            max_enrollment=1,  # Only 1 seat available
            is_active=True,
        )

        # Create 2 students who will try to enroll simultaneously
        self.students = []
        for i in range(2):
            person = Person.objects.create(first_name=f"Student{i}", last_name="Test", email=f"student{i}@example.com")
            student = StudentProfile.objects.create(person=person, student_id=f"STU{i:03d}")
            self.students.append(student)

    def test_no_over_enrollment_race_condition(self):
        """Verify that concurrent enrollments don't exceed class capacity."""
        results = []
        barrier = threading.Barrier(2)  # Synchronize 2 threads

        def enroll_student(student):
            """Function to enroll a student - will be run in separate threads."""
            # Wait for both threads to be ready
            barrier.wait()

            # Try to enroll student
            from django.test import Client

            client = Client()
            client.force_login(self.staff_user)

            response = client.post(
                reverse("web_interface:process-quick-enrollment", kwargs={"class_id": self.class_header.id}),
                {"student_id": student.id, "notes": f"Concurrent enrollment test for {student.student_id}"},
            )
            results.append((student.id, response.status_code))

        # Create and start 2 threads trying to enroll simultaneously
        threads = []
        for student in self.students:
            thread = threading.Thread(target=enroll_student, args=(student,))
            threads.append(thread)
            thread.start()

        # Wait for both threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        self.assertEqual(len(results), 2)

        # Check actual enrollments in database
        actual_enrollments = ClassHeaderEnrollment.objects.filter(
            class_header=self.class_header, status="ENROLLED"
        ).count()

        # Only 1 enrollment should succeed (class capacity is 1)
        self.assertEqual(
            actual_enrollments, 1, "Race condition detected: more students enrolled than class capacity allows"
        )

        # Verify response codes - one should succeed (200), one should fail (409)
        status_codes = sorted([result[1] for result in results])
        success_responses = [code for code in status_codes if code in [200, 302]]  # Success or redirect
        error_responses = [code for code in status_codes if code in [409, 400]]  # Conflict or error

        # At least one should succeed and one should fail
        self.assertGreaterEqual(len(success_responses), 1, "At least one enrollment should succeed")
        self.assertGreaterEqual(len(error_responses), 1, "At least one enrollment should be rejected due to capacity")

    def test_enrollment_capacity_check_consistency(self):
        """Test that capacity checks remain consistent under load."""
        # Fill class to capacity - 1
        initial_student = self.students[0]
        ClassHeaderEnrollment.objects.create(
            student=initial_student, class_header=self.class_header, status="ENROLLED"
        )

        # Now class should have 0 seats available
        enrolled_count = ClassHeaderEnrollment.objects.filter(
            class_header=self.class_header, status="ENROLLED"
        ).count()

        self.assertEqual(enrolled_count, 1)
        self.assertEqual(self.class_header.max_enrollment - enrolled_count, 0)

        # Try to enroll another student - should fail
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.post(
            reverse("web_interface:process-quick-enrollment", kwargs={"class_id": self.class_header.id}),
            {"student_id": self.students[1].id, "notes": "Should fail - class is full"},
        )

        # Should receive error response
        self.assertIn(response.status_code, [409, 400])  # Conflict or Bad Request

        # Verify no additional enrollment was created
        final_count = ClassHeaderEnrollment.objects.filter(class_header=self.class_header, status="ENROLLED").count()

        self.assertEqual(final_count, 1, "No additional enrollment should be created when class is full")
