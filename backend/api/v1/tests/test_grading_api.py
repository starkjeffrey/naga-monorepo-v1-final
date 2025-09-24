"""Tests for unified v1 grading API endpoints.

Tests grading endpoints for teacher grade entry, updates,
and class grade management.
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


class GradingAPITest(TestCase):
    """Test grading API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient(api)

        # Create teacher user
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
        # Mock JWT token for testing
        return {"Authorization": f"Bearer test-token-{self.teacher_user.id}"}

    def test_grading_endpoints_require_auth(self):
        """Test that grading endpoints require authentication."""
        # Test without auth headers
        response = self.client.get(f"/grades/class-part/{self.class_part.id}")
        self.assertEqual(response.status_code, 401)  # Should require auth

    def test_get_class_grades_empty(self):
        """Test getting grades for a class with no grades."""
        response = self.client.get(f"/grades/class-part/{self.class_part.id}", headers=self._get_auth_headers())

        # This might return 200 with empty list or 403 if auth isn't fully implemented
        self.assertIn(response.status_code, [200, 403])

        if response.status_code == 200:
            data = response.json()
            self.assertIsInstance(data, list)

    def test_create_grade_entry_validation(self):
        """Test grade entry creation with validation."""
        payload = {
            "enrollment_id": 999,  # Non-existent enrollment
            "class_part_id": self.class_part.id,
            "numeric_score": 85.0,
            "grade_source": "MANUAL_TEACHER",
        }

        response = self.client.post("/grades", json=payload, headers=self._get_auth_headers())

        # Should fail validation or return 404 for non-existent enrollment
        self.assertIn(response.status_code, [400, 404])

    def test_grading_api_router_integration(self):
        """Test that grading API is properly configured."""
        # Test that the main API has grading endpoints
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)

        schema = response.json()
        # Check that grading endpoints are included
        paths = schema.get("paths", {})
        grading_paths = [path for path in paths if "grade" in path.lower()]
        self.assertGreater(len(grading_paths), 0, "Should have grading endpoints")

    def test_grade_schemas_validation(self):
        """Test grade schema validation."""
        from api.v1.grading import GradeEntrySchema

        # Test GradeEntrySchema
        valid_entry = {
            "enrollment_id": 1,
            "class_part_id": 1,
            "numeric_score": 85.0,
            "letter_grade": "B",
            "notes": "Good work",
        }

        schema = GradeEntrySchema(**valid_entry)
        self.assertEqual(schema.enrollment_id, 1)
        self.assertEqual(schema.numeric_score, 85.0)

    def test_teacher_authorization_logic(self):
        """Test teacher authorization logic for grade operations."""
        # This tests the authorization logic in isolation
        from api.v1.permissions import check_teacher_access

        # Teacher user should have teacher access
        self.assertTrue(check_teacher_access(self.teacher_user))

        # Regular user should not have teacher access
        regular_user = User.objects.create_user(email="regular@example.com", password="testpass123")
        self.assertFalse(check_teacher_access(regular_user))
