"""Unit tests for administrative fee API endpoints.

Tests the API layer for administrative fee management including
configuration, processing, and student cycle status tracking.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from ninja.testing import TestClient

from api.v1 import api
from apps.curriculum.models import Major, Term
from apps.enrollment.models import StudentCycleStatus
from apps.finance.models import AdministrativeFeeConfig, DocumentExcessFee
from apps.people.models import Person, StudentProfile

User = get_user_model()


class AdministrativeFeeAPITest(TestCase):
    """Test administrative fee API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient(api)

        # Create test user with permissions
        self.user = User.objects.create_user(email="admin@example.com", password="testpass123", is_staff=True)

        # Add permissions
        from django.contrib.auth.models import Permission

        permissions = Permission.objects.filter(
            codename__in=[
                "view_administrativefeeconfig",
                "add_administrativefeeconfig",
                "change_administrativefeeconfig",
                "view_documentexcessfee",
                "add_documentexcessfee",
                "change_documentexcessfee",
                "add_invoice",
                "view_studentcyclestatus",
                "add_studentcyclestatus",
            ]
        )
        self.user.user_permissions.add(*permissions)

        # Create term
        self.term = Term.objects.create(
            code="2024-1", name="Spring 2024", start_date=date(2024, 1, 1), end_date=date(2024, 5, 31), is_active=True
        )

        # Create majors
        self.language_major = Major.objects.create(
            code="ENG", name="English Language", major_type="LANGUAGE", is_active=True
        )

        self.bachelor_major = Major.objects.create(
            code="CS", name="Computer Science", major_type="BACHELOR", is_active=True
        )

    def _get_auth_headers(self):
        """Get authentication headers for API calls."""
        # In a real implementation, this would generate a JWT token
        # For testing, we'll use a mock auth
        return {"Authorization": f"Bearer test-token-{self.user.id}"}

    def test_list_admin_fee_configs(self):
        """Test listing administrative fee configurations."""
        # Create test configurations
        AdministrativeFeeConfig.objects.create(
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            fee_amount=Decimal("100.00"),
            included_document_units=10,
            description="New student fee",
            is_active=True,
            created_by=self.user,
        )

        AdministrativeFeeConfig.objects.create(
            cycle_type=StudentCycleStatus.CycleType.LANGUAGE_TO_BACHELOR,
            fee_amount=Decimal("150.00"),
            included_document_units=15,
            description="Transition fee",
            is_active=True,
            created_by=self.user,
        )

        # Make request
        response = self.client.get("/admin-fee-configs", headers=self._get_auth_headers())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        # Verify data
        data = response.json()
        self.assertEqual(data[0]["cycle_type"], "NEW_ENTRY")
        self.assertEqual(data[0]["fee_amount"], 100.0)
        self.assertEqual(data[0]["included_document_units"], 10)

        self.assertEqual(data[1]["cycle_type"], "LANGUAGE_TO_BACHELOR")
        self.assertEqual(data[1]["fee_amount"], 150.0)

    def test_create_admin_fee_config(self):
        """Test creating administrative fee configuration."""
        payload = {
            "cycle_type": "NEW_ENTRY",
            "fee_amount": 120.0,
            "included_document_units": 12,
            "description": "Test new student fee",
            "is_active": True,
        }

        response = self.client.post("/admin-fee-configs", json=payload, headers=self._get_auth_headers())

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify response
        self.assertEqual(data["cycle_type"], "NEW_ENTRY")
        self.assertEqual(data["cycle_type_display"], "New Student Entry")
        self.assertEqual(data["fee_amount"], 120.0)
        self.assertEqual(data["included_document_units"], 12)

        # Verify database
        config = AdministrativeFeeConfig.objects.get(cycle_type="NEW_ENTRY")
        self.assertEqual(config.fee_amount, Decimal("120.00"))
        self.assertEqual(config.created_by, self.user)

    def test_create_duplicate_admin_fee_config(self):
        """Test creating duplicate configuration fails."""
        # Create existing config
        AdministrativeFeeConfig.objects.create(
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            fee_amount=Decimal("100.00"),
            included_document_units=10,
            description="Existing fee",
            is_active=True,
            created_by=self.user,
        )

        # Try to create duplicate
        payload = {
            "cycle_type": "NEW_ENTRY",
            "fee_amount": 120.0,
            "included_document_units": 12,
            "description": "Duplicate fee",
            "is_active": True,
        }

        response = self.client.post("/admin-fee-configs", json=payload, headers=self._get_auth_headers())

        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.json()["detail"])

    def test_update_admin_fee_config(self):
        """Test updating administrative fee configuration."""
        config = AdministrativeFeeConfig.objects.create(
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            fee_amount=Decimal("100.00"),
            included_document_units=10,
            description="Original fee",
            is_active=True,
            created_by=self.user,
        )

        payload = {
            "cycle_type": "NEW_ENTRY",
            "fee_amount": 125.0,
            "included_document_units": 15,
            "description": "Updated fee",
            "is_active": False,
        }

        response = self.client.put(f"/admin-fee-configs/{config.id}", json=payload, headers=self._get_auth_headers())

        self.assertEqual(response.status_code, 200)

        # Verify update
        config.refresh_from_db()
        self.assertEqual(config.fee_amount, Decimal("125.00"))
        self.assertEqual(config.included_document_units, 15)
        self.assertFalse(config.is_active)
        self.assertEqual(config.updated_by, self.user)

    def test_list_document_excess_fees(self):
        """Test listing document excess fee configurations."""
        DocumentExcessFee.objects.create(
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            fee_per_unit=Decimal("5.00"),
            is_active=True,
            created_by=self.user,
        )

        DocumentExcessFee.objects.create(
            cycle_type=StudentCycleStatus.CycleType.BACHELOR_TO_MASTER,
            fee_per_unit=Decimal("7.50"),
            is_active=True,
            created_by=self.user,
        )

        response = self.client.get("/document-excess-fees", headers=self._get_auth_headers())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        data = response.json()
        self.assertEqual(data[0]["fee_per_unit"], 5.0)
        self.assertEqual(data[1]["fee_per_unit"], 7.5)

    def test_process_term_administrative_fees(self):
        """Test processing administrative fees for a term."""
        # Create fee configuration
        AdministrativeFeeConfig.objects.create(
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            fee_amount=Decimal("100.00"),
            included_document_units=10,
            description="New student fee",
            is_active=True,
            created_by=self.user,
        )

        # Create students with cycle status
        for i in range(3):
            person = Person.objects.create(
                personal_name=f"Test{i}",
                family_name="Student",
                date_of_birth=date(2000, 1, 1),
                preferred_gender="M",
                citizenship="KH",
            )

            student = StudentProfile.objects.create(
                person=person,
                student_id=f"24000{i + 1}",
                admission_date=date.today(),
                primary_major=self.language_major,
            )

            StudentCycleStatus.objects.create(
                student=student,
                cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
                target_program=self.language_major,
                is_active=True,
            )

        # Process fees
        response = self.client.post(f"/process-term-fees/{self.term.id}", headers=self._get_auth_headers())

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["processed"], 3)
        self.assertEqual(data["fees_applied"], 3)
        self.assertEqual(data["total_revenue"], 300.0)
        self.assertEqual(len(data["errors"]), 0)

    def test_list_student_cycle_statuses(self):
        """Test listing student cycle statuses."""
        # Create students with statuses
        person = Person.objects.create(
            personal_name="Test",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        student = StudentProfile.objects.create(
            person=person, student_id="240001", admission_date=date.today(), primary_major=self.language_major
        )

        StudentCycleStatus.objects.create(
            student=student,
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            target_program=self.language_major,
            is_active=True,
        )

        response = self.client.get("/student-cycle-statuses", headers=self._get_auth_headers())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        data = response.json()[0]
        self.assertEqual(data["student_number"], "240001")
        self.assertEqual(data["cycle_type"], "NEW_ENTRY")
        self.assertEqual(data["cycle_type_display"], "New Student Entry")
        self.assertTrue(data["is_active"])

    def test_permission_denied_without_auth(self):
        """Test that endpoints require proper authentication."""
        response = self.client.get("/admin-fee-configs")
        self.assertEqual(response.status_code, 401)  # Or 403 depending on auth implementation

    def test_permission_denied_without_proper_permissions(self):
        """Test that endpoints require proper permissions."""
        # Create user without permissions
        unprivileged_user = User.objects.create_user(email="user@example.com", password="testpass123")

        headers = {"Authorization": f"Bearer test-token-{unprivileged_user.id}"}

        response = self.client.get("/admin-fee-configs", headers=headers)

        self.assertEqual(response.status_code, 403)
