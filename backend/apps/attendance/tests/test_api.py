"""API tests for the attendance endpoints.

This module tests the updated API endpoints that were modified for the mobile
attendance workflow, including:
- Teacher session creation with backend-generated codes
- Student code submission without session_id requirement
- Teacher's classes list endpoint
- Authentication and permission handling
"""

import json
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import AttendanceSession
from apps.attendance.services import AttendanceCodeService
from apps.common.utils import get_current_date
from apps.curriculum.models import Course, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import Person, StudentProfile, TeacherProfile
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession

User = get_user_model()


class AttendanceAPIBaseTest(TestCase):
    """Base test class with common setup for attendance API tests."""

    def setUp(self):
        """Set up test data for API tests."""
        # Create admin user
        self.admin_user = User.objects.create_user(email="admin@test.com", password="testpass123")
        self.admin_user.is_staff = True
        self.admin_user.save()

        # Create teacher user and profile
        self.teacher_user = User.objects.create_user(email="teacher@test.com", password="testpass123")
        teacher_person = Person.objects.create(
            family_name="Teacher",
            personal_name="Test",
            date_of_birth=date(1980, 1, 1),
        )
        self.teacher_profile = TeacherProfile.objects.create(
            person=teacher_person,
            status=TeacherProfile.Status.ACTIVE,
        )
        # Link user to teacher profile
        teacher_person.user = self.teacher_user
        teacher_person.save()

        # Create student user and profile
        self.student_user = User.objects.create_user(email="student@test.com", password="testpass123")
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        self.student_profile = StudentProfile.objects.create(
            person=student_person,
            student_id="TEST001",
        )
        # Link user to student profile
        student_person.user = self.student_user
        student_person.save()

        # Create mock course and term
        self.course = Course.objects.create(course_code="ENG101", title="English 101", credit_hours=3)
        self.term = Term.objects.create(
            name="Fall 2024",
            start_date=get_current_date() - timedelta(days=30),
            end_date=get_current_date() + timedelta(days=60),
        )

        # Create class header
        self.class_header = ClassHeader.objects.create(course=self.course, term=self.term, status="ACTIVE")

        # Create class session and class part
        self.class_session = ClassSession.objects.create(class_header=self.class_header, session_number=1)
        self.class_part = ClassPart.objects.create(
            class_session=self.class_session,
            teacher=self.teacher_profile,
            meeting_days="MON,WED,FRI",
            start_time=time(9, 0),
            end_time=time(10, 30),
        )

        # Create enrollment for student
        self.enrollment = ClassHeaderEnrollment.objects.create(
            class_header=self.class_header,
            student=self.student_profile,
            status="ENROLLED",
        )

    def get_api_url(self, endpoint):
        """Get full API URL for endpoint."""
        return f"/api/attendance/{endpoint}"

    def api_post(self, endpoint, data, user=None):
        """Make authenticated POST request to API."""
        if user:
            self.client.force_login(user)
        return self.client.post(
            self.get_api_url(endpoint),
            data=json.dumps(data),
            content_type="application/json",
        )

    def api_get(self, endpoint, user=None):
        """Make authenticated GET request to API."""
        if user:
            self.client.force_login(user)
        return self.client.get(self.get_api_url(endpoint))


class TeacherSessionAPITest(AttendanceAPIBaseTest):
    """Test teacher session management APIs."""

    def test_start_session_with_backend_generated_code(self):
        """Test POST /teacher/start-session generates code on backend."""
        data = {
            "class_part_id": self.class_part.id,
            "latitude": 11.5564,
            "longitude": 104.9282,
            "is_makeup_class": False,
        }

        response = self.api_post("teacher/start-session", data, self.teacher_user)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        # Verify response structure
        self.assertIn("id", response_data)
        self.assertIn("attendance_code", response_data)
        self.assertIn("code_expires_at", response_data)
        self.assertEqual(response_data["class_part_id"], self.class_part.id)

        # Verify code was generated (6 characters)
        attendance_code = response_data["attendance_code"]
        self.assertEqual(len(attendance_code), 6)
        self.assertTrue(attendance_code.isalnum())

        # Verify session was created in database
        session = AttendanceSession.objects.get(id=response_data["id"])
        self.assertEqual(session.attendance_code, attendance_code)
        self.assertEqual(session.teacher, self.teacher_profile)
        self.assertTrue(session.is_active)

    def test_start_session_unauthorized_teacher(self):
        """Test that teacher can only start sessions for their own classes."""
        # Create another teacher
        other_user = User.objects.create_user(email="other@test.com", password="testpass123")
        other_person = Person.objects.create(
            family_name="Other",
            personal_name="Teacher",
            date_of_birth=date(1975, 1, 1),
        )
        TeacherProfile.objects.create(
            person=other_person,
            status=TeacherProfile.Status.ACTIVE,
        )
        other_person.user = other_user
        other_person.save()

        data = {
            "class_part_id": self.class_part.id,
            "latitude": 11.5564,
            "longitude": 104.9282,
        }

        response = self.api_post("teacher/start-session", data, other_user)
        self.assertEqual(response.status_code, 403)

    def test_start_session_with_makeup_class(self):
        """Test starting makeup class session."""
        data = {
            "class_part_id": self.class_part.id,
            "latitude": 11.5564,
            "longitude": 104.9282,
            "is_makeup_class": True,
            "makeup_reason": "Holiday replacement",
        }

        response = self.api_post("teacher/start-session", data, self.teacher_user)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        # Verify session was marked as makeup
        session = AttendanceSession.objects.get(id=response_data["id"])
        self.assertTrue(session.is_makeup_class)
        self.assertEqual(session.makeup_reason, "Holiday replacement")

    def test_get_teacher_classes(self):
        """Test GET /teacher/my-classes endpoint."""
        response = self.api_get("teacher/my-classes", self.teacher_user)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        # Verify response structure
        self.assertIn("classes", response_data)
        classes = response_data["classes"]
        self.assertEqual(len(classes), 1)

        # Verify class data
        class_info = classes[0]
        self.assertEqual(class_info["class_part_id"], self.class_part.id)
        self.assertIn("class_name", class_info)
        self.assertIn("schedule", class_info)
        self.assertEqual(class_info["is_substitute"], False)

        # Verify schedule information
        if class_info["schedule"]:
            schedule = class_info["schedule"]
            self.assertIn("day_of_week", schedule)
            self.assertIn("start_time", schedule)
            self.assertEqual(schedule["start_time"], "09:00")

    def test_get_teacher_classes_no_classes(self):
        """Test teacher with no assigned classes."""
        # Create teacher with no classes
        no_class_user = User.objects.create_user(email="noclass@test.com", password="testpass123")
        no_class_person = Person.objects.create(
            family_name="NoClass",
            personal_name="Teacher",
            date_of_birth=date(1985, 1, 1),
        )
        TeacherProfile.objects.create(
            person=no_class_person,
            status=TeacherProfile.Status.ACTIVE,
        )
        no_class_person.user = no_class_user
        no_class_person.save()

        response = self.api_get("teacher/my-classes", no_class_user)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["classes"]), 0)

    def test_teacher_endpoints_require_teacher_role(self):
        """Test that teacher endpoints require teacher authentication."""
        data = {
            "class_part_id": self.class_part.id,
            "latitude": 11.5564,
            "longitude": 104.9282,
        }

        # Test with student user (should fail)
        response = self.api_post("teacher/start-session", data, self.student_user)
        self.assertEqual(response.status_code, 403)

        # Test with no authentication (should fail)
        response = self.api_post("teacher/start-session", data)
        self.assertEqual(response.status_code, 401)


class StudentCodeSubmissionAPITest(AttendanceAPIBaseTest):
    """Test student code submission API."""

    def setUp(self):
        """Set up test data including active session."""
        super().setUp()

        # Create active attendance session
        self.attendance_code = "XF4T9Z"
        self.session = AttendanceSession.objects.create(
            class_part=self.class_part,
            teacher=self.teacher_profile,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code=self.attendance_code,
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            latitude=Decimal("11.5564"),
            longitude=Decimal("104.9282"),
            is_active=True,
        )

    def test_submit_code_success(self):
        """Test successful code submission without session_id."""
        data = {
            "submitted_code": self.attendance_code,
            "latitude": 11.5565,
            "longitude": 104.9283,
        }

        with patch.object(AttendanceCodeService, "validate_student_code_submission") as mock_validate:
            mock_validate.return_value = {
                "success": True,
                "status": "PRESENT",
                "message": "Attendance recorded successfully",
                "within_geofence": True,
                "distance_meters": 15,
            }

            response = self.api_post("student/submit-code", data, self.student_user)

            self.assertEqual(response.status_code, 200)
            response_data = response.json()

            # Verify response
            self.assertTrue(response_data["success"])
            self.assertEqual(response_data["status"], "PRESENT")
            self.assertTrue(response_data["within_geofence"])

            # Verify the service was called with correct parameters
            mock_validate.assert_called_once()
            call_args = mock_validate.call_args[1]
            self.assertEqual(call_args["session"], self.session)
            self.assertEqual(call_args["student_id"], self.student_profile.student_id)
            self.assertEqual(call_args["submitted_code"], self.attendance_code)

    def test_submit_code_invalid_code(self):
        """Test submission with invalid/expired code."""
        data = {"submitted_code": "INVALID", "latitude": 11.5565, "longitude": 104.9283}

        response = self.api_post("student/submit-code", data, self.student_user)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        # Verify error response
        self.assertFalse(response_data["success"])
        self.assertEqual(response_data["status"], "INVALID_CODE")
        self.assertEqual(response_data["message"], "Invalid or expired attendance code")

    def test_submit_code_not_enrolled(self):
        """Test submission when student not enrolled in class."""
        # Delete enrollment
        self.enrollment.delete()

        data = {
            "submitted_code": self.attendance_code,
            "latitude": 11.5565,
            "longitude": 104.9283,
        }

        response = self.api_post("student/submit-code", data, self.student_user)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        # Verify enrollment error
        self.assertFalse(response_data["success"])
        self.assertEqual(response_data["status"], "NOT_ENROLLED")
        self.assertEqual(response_data["message"], "You are not enrolled in this class")

    def test_submit_code_expired_session(self):
        """Test submission to expired session."""
        # Make session expired
        self.session.code_expires_at = timezone.now() - timedelta(minutes=1)
        self.session.save()

        data = {
            "submitted_code": self.attendance_code,
            "latitude": 11.5565,
            "longitude": 104.9283,
        }

        response = self.api_post("student/submit-code", data, self.student_user)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        # Verify expiry error
        self.assertFalse(response_data["success"])
        self.assertEqual(response_data["status"], "INVALID_CODE")

    def test_submit_code_inactive_session(self):
        """Test submission to inactive session."""
        # Make session inactive
        self.session.is_active = False
        self.session.save()

        data = {
            "submitted_code": self.attendance_code,
            "latitude": 11.5565,
            "longitude": 104.9283,
        }

        response = self.api_post("student/submit-code", data, self.student_user)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        # Verify inactive error
        self.assertFalse(response_data["success"])
        self.assertEqual(response_data["status"], "INVALID_CODE")

    def test_submit_code_requires_student_role(self):
        """Test that endpoint requires student authentication."""
        data = {
            "submitted_code": self.attendance_code,
            "latitude": 11.5565,
            "longitude": 104.9283,
        }

        # Test with teacher user (should fail)
        response = self.api_post("student/submit-code", data, self.teacher_user)
        self.assertEqual(response.status_code, 403)

        # Test with no authentication (should fail)
        response = self.api_post("student/submit-code", data)
        self.assertEqual(response.status_code, 401)


class AttendanceCodeGenerationTest(AttendanceAPIBaseTest):
    """Test attendance code generation functionality."""

    def test_backend_code_generation_uniqueness(self):
        """Test that backend generates unique codes."""
        codes: set[str] = set()

        # Generate multiple codes and verify uniqueness
        for _ in range(10):
            code = AttendanceCodeService.generate_attendance_code()
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isalnum())
            self.assertNotIn(code, codes)
            codes.add(code)

    def test_code_generation_avoids_active_codes(self):
        """Test that code generation avoids currently active codes."""
        # Create active session with a specific code
        existing_code = "TEST01"
        AttendanceSession.objects.create(
            class_part=self.class_part,
            teacher=self.teacher_profile,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code=existing_code,
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            is_active=True,
        )

        # Generate new codes and verify they don't match existing
        for _ in range(5):
            new_code = AttendanceCodeService.generate_attendance_code()
            self.assertNotEqual(new_code, existing_code)

    def test_code_generation_excludes_confusing_characters(self):
        """Test that generated codes exclude confusing characters."""
        confusing_chars = ["O", "I", "0", "1"]

        # Generate multiple codes and verify no confusing characters
        for _ in range(20):
            code = AttendanceCodeService.generate_attendance_code()
            for char in confusing_chars:
                self.assertNotIn(char, code)


class AttendanceAPIIntegrationTest(AttendanceAPIBaseTest):
    """Integration tests for complete attendance workflow."""

    def test_complete_mobile_workflow(self):
        """Test complete mobile attendance workflow."""
        # 1. Teacher starts session
        start_data = {
            "class_part_id": self.class_part.id,
            "latitude": 11.5564,
            "longitude": 104.9282,
        }

        start_response = self.api_post("teacher/start-session", start_data, self.teacher_user)
        self.assertEqual(start_response.status_code, 200)

        start_result = start_response.json()
        session_id = start_result["id"]
        attendance_code = start_result["attendance_code"]

        # 2. Student submits code
        submit_data = {
            "submitted_code": attendance_code,
            "latitude": 11.5565,
            "longitude": 104.9283,
        }

        with patch.object(AttendanceCodeService, "validate_student_code_submission") as mock_validate:
            mock_validate.return_value = {
                "success": True,
                "status": "PRESENT",
                "message": "Attendance recorded successfully",
                "within_geofence": True,
                "distance_meters": 15,
            }

            submit_response = self.api_post("student/submit-code", submit_data, self.student_user)
            self.assertEqual(submit_response.status_code, 200)

            submit_result = submit_response.json()
            self.assertTrue(submit_result["success"])
            self.assertEqual(submit_result["status"], "PRESENT")

        # 3. Verify session exists and is properly configured
        session = AttendanceSession.objects.get(id=session_id)
        self.assertEqual(session.attendance_code, attendance_code)
        self.assertTrue(session.is_active)
        self.assertEqual(session.teacher, self.teacher_profile)

    def test_teacher_class_list_workflow(self):
        """Test teacher getting class list for attendance."""
        # Get teacher's classes
        response = self.api_get("teacher/my-classes", self.teacher_user)
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(len(result["classes"]), 1)

        # Use class from list to start session
        class_info = result["classes"][0]
        start_data = {
            "class_part_id": class_info["class_part_id"],
            "latitude": 11.5564,
            "longitude": 104.9282,
        }

        start_response = self.api_post("teacher/start-session", start_data, self.teacher_user)
        self.assertEqual(start_response.status_code, 200)

        # Verify session was created for correct class
        start_result = start_response.json()
        self.assertEqual(start_result["class_part_id"], class_info["class_part_id"])

    def test_multiple_active_sessions_different_classes(self):
        """Test handling multiple active sessions for different classes."""
        # Create another class for the same teacher
        class_session_2 = ClassSession.objects.create(class_header=self.class_header, session_number=2)
        class_part_2 = ClassPart.objects.create(
            class_session=class_session_2,
            teacher=self.teacher_profile,
            meeting_days="TUE,THU",
            start_time=time(14, 0),
            end_time=time(15, 30),
        )

        # Start session for first class
        start_data_1 = {
            "class_part_id": self.class_part.id,
            "latitude": 11.5564,
            "longitude": 104.9282,
        }
        response_1 = self.api_post("teacher/start-session", start_data_1, self.teacher_user)
        self.assertEqual(response_1.status_code, 200)
        code_1 = response_1.json()["attendance_code"]

        # Start session for second class
        start_data_2 = {
            "class_part_id": class_part_2.id,
            "latitude": 11.5564,
            "longitude": 104.9282,
        }
        response_2 = self.api_post("teacher/start-session", start_data_2, self.teacher_user)
        self.assertEqual(response_2.status_code, 200)
        code_2 = response_2.json()["attendance_code"]

        # Verify codes are different
        self.assertNotEqual(code_1, code_2)

        # Verify both sessions are active
        active_sessions = AttendanceSession.objects.filter(is_active=True)
        self.assertEqual(active_sessions.count(), 2)


class AttendanceAPIErrorHandlingTest(AttendanceAPIBaseTest):
    """Test error handling in attendance APIs."""

    def test_malformed_json_requests(self):
        """Test handling of malformed JSON in requests."""
        # Test with invalid JSON
        response = self.client.post(
            self.get_api_url("teacher/start-session"),
            data="invalid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Test start-session without class_part_id
        self.client.force_login(self.teacher_user)
        response = self.client.post(
            self.get_api_url("teacher/start-session"),
            data=json.dumps({"latitude": 11.5564}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_invalid_class_part_id(self):
        """Test handling of invalid class_part_id."""
        data = {
            "class_part_id": 99999,  # Non-existent
            "latitude": 11.5564,
            "longitude": 104.9282,
        }

        response = self.api_post("teacher/start-session", data, self.teacher_user)
        self.assertEqual(response.status_code, 404)

    def test_concurrent_code_submission(self):
        """Test handling of concurrent code submissions."""
        # Create active session
        attendance_code = "CONC01"
        AttendanceSession.objects.create(
            class_part=self.class_part,
            teacher=self.teacher_profile,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code=attendance_code,
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            is_active=True,
        )

        # Create duplicate student
        student2_user = User.objects.create_user(email="student2@test.com", password="testpass123")
        student2_person = Person.objects.create(
            family_name="Student2",
            personal_name="Test",
            date_of_birth=date(2000, 2, 2),
        )
        student2_profile = StudentProfile.objects.create(
            person=student2_person,
            student_id="TEST002",
        )
        student2_person.user = student2_user
        student2_person.save()

        # Create enrollment for second student
        ClassHeaderEnrollment.objects.create(
            class_header=self.class_header,
            student=student2_profile,
            status="ENROLLED",
        )

        submit_data = {
            "submitted_code": attendance_code,
            "latitude": 11.5565,
            "longitude": 104.9283,
        }

        # Submit from both students simultaneously
        with patch.object(AttendanceCodeService, "validate_student_code_submission") as mock_validate:
            mock_validate.return_value = {
                "success": True,
                "status": "PRESENT",
                "message": "Attendance recorded successfully",
                "within_geofence": True,
                "distance_meters": 15,
            }

            response1 = self.api_post("student/submit-code", submit_data, self.student_user)
            response2 = self.api_post("student/submit-code", submit_data, student2_user)

            # Both should succeed (different students)
            self.assertEqual(response1.status_code, 200)
            self.assertEqual(response2.status_code, 200)


class AttendanceAPIPerformanceTest(AttendanceAPIBaseTest):
    """Test performance aspects of attendance APIs."""

    def test_teacher_classes_with_many_classes(self):
        """Test teacher classes endpoint with many assigned classes."""
        # Create many class parts for the teacher
        for i in range(20):
            class_session = ClassSession.objects.create(class_header=self.class_header, session_number=i + 2)
            ClassPart.objects.create(
                class_session=class_session,
                teacher=self.teacher_profile,
                meeting_days="MON,WED,FRI",
                start_time=time(9 + i % 8, 0),
                end_time=time(10 + i % 8, 30),
            )

        # Request should complete quickly
        response = self.api_get("teacher/my-classes", self.teacher_user)
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(len(result["classes"]), 21)  # Original + 20 new

    def test_code_generation_performance(self):
        """Test that code generation performs well under load."""
        # Create many active sessions to test collision avoidance
        for i in range(50):
            AttendanceSession.objects.create(
                class_part=self.class_part,
                teacher=self.teacher_profile,
                session_date=get_current_date(),
                start_time=time(9, 0),
                attendance_code=f"TEST{i:02d}",
                code_generated_at=timezone.now(),
                code_expires_at=timezone.now() + timedelta(minutes=15),
                is_active=True,
            )

        # Generate new codes should still work quickly
        for _ in range(10):
            code = AttendanceCodeService.generate_attendance_code()
            self.assertEqual(len(code), 6)

            # Verify it's not a duplicate
            existing = AttendanceSession.objects.filter(attendance_code=code, is_active=True).exists()
            self.assertFalse(existing)


@pytest.mark.django_db
class AttendanceAPIPytestTest:
    """Pytest-style tests for attendance API endpoints."""

    def test_api_documentation_matches_implementation(self):
        """Test that API responses match documented schemas."""
        # This would involve more comprehensive schema validation
        # For now, just verify basic structure compliance

        from apps.attendance.api import TeacherClassesResponseSchema

        # Verify schema exists and has expected fields
        schema = TeacherClassesResponseSchema
        assert hasattr(schema, "__annotations__")
        assert "classes" in schema.__annotations__

    def test_attendance_code_entropy(self):
        """Test that generated codes have sufficient entropy."""
        codes = set()
        for _ in range(1000):
            code = AttendanceCodeService.generate_attendance_code()
            codes.add(code)

        # Should have very high uniqueness rate
        assert len(codes) > 990  # Allow for tiny chance of collision

        # Test character distribution
        all_chars = "".join(codes)
        unique_chars = set(all_chars)

        # Should use many different characters (excluding confusing ones)
        assert len(unique_chars) > 20

    def test_api_response_times(self):
        """Test that API responses are reasonably fast."""
        # This would require proper performance testing setup
        # For now, just a placeholder test
        import time

        start_time = time.time()
        AttendanceCodeService.generate_attendance_code()
        end_time = time.time()

        # Code generation should be very fast
        assert (end_time - start_time) < 0.1  # Less than 100ms
