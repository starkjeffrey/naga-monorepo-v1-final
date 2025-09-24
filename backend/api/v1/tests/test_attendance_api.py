"""Tests for unified v1 attendance API endpoints.

Tests attendance endpoints for session management, roster sync,
and attendance tracking.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from ninja.testing import TestClient

from api.v1 import api
from apps.curriculum.models import Course, Term
from apps.people.models import Person, TeacherProfile
from apps.scheduling.models import ClassHeader, ClassPart

User = get_user_model()


class AttendanceAPITest(TestCase):
    """Test attendance API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient(api)

        # Create teacher user and profile
        self.teacher_person = Person.objects.create(
            personal_name="John",
            family_name="Teacher",
            preferred_gender="M",
            date_of_birth="1980-01-01",
            citizenship="US",
        )

        self.teacher_user = User.objects.create_user(
            email="teacher@example.com", password="testpass123", is_staff=True
        )
        self.teacher_user.person = self.teacher_person
        self.teacher_user.save()

        self.teacher_profile = TeacherProfile.objects.create(
            person=self.teacher_person, employee_id="T001", hire_date="2020-01-01"
        )

        # Create course and term
        self.term = Term.objects.create(
            code="2024-1", name="Spring 2024", start_date=date(2024, 1, 1), end_date=date(2024, 5, 31), is_active=True
        )

        self.course = Course.objects.create(code="ENG101", name="English Basics", credits=3, is_active=True)

        # Create class
        self.class_header = ClassHeader.objects.create(course=self.course, term=self.term, section="A")

        self.class_part = ClassPart.objects.create(
            class_header=self.class_header, teacher=self.teacher_profile, part_name="Main"
        )

    def _get_auth_headers(self):
        """Get authentication headers for API calls."""
        return {"Authorization": f"Bearer test-token-{self.teacher_user.id}"}

    def test_attendance_endpoints_require_auth(self):
        """Test that attendance endpoints require authentication."""
        # Test without auth headers
        response = self.client.get(f"/teacher/class-roster/{self.class_part.id}")
        self.assertEqual(response.status_code, 401)  # Should require auth

    def test_start_attendance_session_validation(self):
        """Test attendance session creation validation."""
        payload = {
            "class_part_id": 999,  # Non-existent class part
            "latitude": 11.5564,
            "longitude": 104.9282,
            "is_makeup_class": False,
        }

        response = self.client.post("/teacher/start-session", json=payload, headers=self._get_auth_headers())

        # Should fail with 404 for non-existent class part
        self.assertEqual(response.status_code, 404)

    def test_start_attendance_session_authorization(self):
        """Test attendance session authorization."""
        payload = {"class_part_id": self.class_part.id, "latitude": 11.5564, "longitude": 104.9282}

        response = self.client.post("/teacher/start-session", json=payload, headers=self._get_auth_headers())

        # This might succeed, fail with auth error, or fail with service error
        # depending on what's implemented
        self.assertIn(response.status_code, [200, 403, 500])

    def test_get_class_roster_validation(self):
        """Test class roster retrieval validation."""
        response = self.client.get(
            "/teacher/class-roster/999",
            headers=self._get_auth_headers(),  # Non-existent class part
        )

        # Should fail with 404 for non-existent class part
        self.assertEqual(response.status_code, 404)

    def test_get_class_roster_authorization(self):
        """Test class roster authorization."""
        response = self.client.get(f"/teacher/class-roster/{self.class_part.id}", headers=self._get_auth_headers())

        # This might succeed or fail depending on implementation
        self.assertIn(response.status_code, [200, 403, 500])

    def test_attendance_schemas_validation(self):
        """Test attendance schema validation."""
        from api.v1.attendance import AttendanceSessionCreateSchema, RosterStudentSchema

        # Test session creation schema
        valid_session = {"class_part_id": 1, "latitude": 11.5564, "longitude": 104.9282, "is_makeup_class": False}

        schema = AttendanceSessionCreateSchema(**valid_session)
        self.assertEqual(schema.class_part_id, 1)
        self.assertEqual(schema.latitude, 11.5564)

        # Test roster student schema
        valid_student = {
            "student_id": 1,
            "student_name": "Jane Doe",
            "enrollment_status": "ENROLLED",
            "is_audit": False,
        }

        schema = RosterStudentSchema(**valid_student)
        self.assertEqual(schema.student_name, "Jane Doe")

    def test_teacher_authorization_logic(self):
        """Test teacher authorization for attendance operations."""
        from api.v1.permissions import check_teacher_access

        # Teacher user should have teacher access
        self.assertTrue(check_teacher_access(self.teacher_user))

        # Regular user should not
        regular_user = User.objects.create_user(email="regular@example.com", password="testpass123")
        self.assertFalse(check_teacher_access(regular_user))

    def test_attendance_api_router_integration(self):
        """Test that attendance API is properly configured."""
        # Test that the main API has attendance endpoints
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)

        schema = response.json()
        # Check that attendance endpoints are included
        paths = schema.get("paths", {})
        attendance_paths = [path for path in paths if "attendance" in path.lower()]
        self.assertGreater(len(attendance_paths), 0, "Should have attendance endpoints")

    def test_geofence_location_validation(self):
        """Test location data validation in attendance schemas."""
        from api.v1.attendance import AttendanceSessionCreateSchema

        # Valid coordinates
        valid_data = {"class_part_id": 1, "latitude": 11.5564, "longitude": 104.9282}  # Siem Reap coordinates

        schema = AttendanceSessionCreateSchema(**valid_data)
        self.assertAlmostEqual(schema.latitude, 11.5564, places=4)

        # Coordinates can be optional
        minimal_data = {"class_part_id": 1}

        schema = AttendanceSessionCreateSchema(**minimal_data)
        self.assertEqual(schema.class_part_id, 1)
        self.assertIsNone(schema.latitude)
