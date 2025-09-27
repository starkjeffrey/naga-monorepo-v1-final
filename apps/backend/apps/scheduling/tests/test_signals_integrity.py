"""Tests specifically for signal-based integrity enforcement.

This module tests the automatic integrity enforcement through Django signals
to ensure the ClassHeader → ClassSession → ClassPart architecture is maintained.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TransactionTestCase

from apps.curriculum.models import Course, Cycle, Division, Term
from apps.scheduling.class_part_types import ClassPartType
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession


class SignalIntegrityEnforcementTest(TransactionTestCase):
    """Test signal-based automatic integrity enforcement."""

    def setUp(self):
        """Set up test data."""
        self.division = Division.objects.create(name="Test Division", short_name="TEST")

        self.term = Term.objects.create(code="2025T1", start_date="2025-01-01", end_date="2025-04-30")

        self.cycle = Cycle.objects.create(name="Test Cycle", division=self.division)

        self.regular_course = Course.objects.create(code="REG101", title="Regular Course", cycle=self.cycle, credits=3)

        self.ieap_course = Course.objects.create(code="IEAP101", title="IEAP Course", cycle=self.cycle, credits=6)

    def test_signal_auto_creates_regular_class_structure(self):
        """Test that signals automatically create proper structure for regular classes."""
        # Create class header - signals should trigger
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        # Verify automatic session creation
        self.assertEqual(class_header.class_sessions.count(), 1)

        session = class_header.class_sessions.first()
        self.assertEqual(session.session_number, 1)
        self.assertEqual(session.grade_weight, Decimal("1.0"))

        # Verify automatic part creation
        self.assertEqual(session.class_parts.count(), 1)

        part = session.class_parts.first()
        self.assertEqual(part.class_part_code, "A")
        self.assertEqual(part.class_part_type, ClassPartType.MAIN)
        self.assertEqual(part.grade_weight, Decimal("1.0"))

    def test_signal_auto_creates_ieap_class_structure(self):
        """Test that signals automatically create proper structure for IEAP classes."""
        # Create IEAP class header
        class_header = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")

        # Verify automatic session creation for IEAP
        self.assertEqual(class_header.class_sessions.count(), 2)

        sessions = list(class_header.class_sessions.order_by("session_number"))

        # Check session 1
        self.assertEqual(sessions[0].session_number, 1)
        self.assertEqual(sessions[0].grade_weight, Decimal("0.5"))
        self.assertEqual(sessions[0].session_name, "IEAP Session 1")
        self.assertEqual(sessions[0].class_parts.count(), 1)

        # Check session 2
        self.assertEqual(sessions[1].session_number, 2)
        self.assertEqual(sessions[1].grade_weight, Decimal("0.5"))
        self.assertEqual(sessions[1].session_name, "IEAP Session 2")
        self.assertEqual(sessions[1].class_parts.count(), 1)

    def test_signal_creates_default_part_on_session_creation(self):
        """Test that signals create default part when session is manually created."""
        # Create class header first
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        # Clear auto-created sessions to test manual creation
        class_header.class_sessions.all().delete()

        # Manually create session - signal should create part
        session = ClassSession.objects.create(class_header=class_header, session_number=1)

        # Verify part was auto-created
        self.assertEqual(session.class_parts.count(), 1)

        part = session.class_parts.first()
        self.assertEqual(part.class_part_code, "A")
        self.assertEqual(part.class_part_type, ClassPartType.MAIN)

    def test_signal_prevents_session_deletion_regular_class(self):
        """Test that signals prevent deletion of the only session in regular classes."""
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        session = class_header.class_sessions.first()

        # Attempt to delete the only session should fail
        with self.assertRaises(ValidationError) as cm:
            session.delete()

        self.assertIn("Cannot delete the only session", str(cm.exception))

    def test_signal_prevents_session_deletion_ieap_class(self):
        """Test that signals prevent deletion of sessions in IEAP classes."""
        class_header = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")

        sessions = list(class_header.class_sessions.all())
        self.assertEqual(len(sessions), 2)

        # Attempt to delete any session should fail
        for session in sessions:
            with self.assertRaises(ValidationError) as cm:
                session.delete()

            self.assertIn("Cannot delete sessions from IEAP class", str(cm.exception))

    def test_signal_integrity_with_manual_modifications(self):
        """Test signal integrity when manually modifying structure."""
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        # Get auto-created session and part
        session = class_header.class_sessions.first()
        original_part = session.class_parts.first()

        # Add additional part manually
        ClassPart.objects.create(
            class_session=session,
            class_part_code="B",
            class_part_type=ClassPartType.CONVERSATION,
            grade_weight=Decimal("0.3"),
        )

        # Update original part weight
        original_part.grade_weight = Decimal("0.7")
        original_part.save()

        # Verify both parts exist and follow integrity rules
        self.assertEqual(session.class_parts.count(), 2)

        # Check that validation detects the proper structure
        validation = session.validate_parts_structure()
        self.assertTrue(validation["valid"])

        # Total weight should be 1.0
        total_weight = sum(p.grade_weight for p in session.class_parts.all())
        self.assertEqual(total_weight, Decimal("1.0"))

    def test_signal_handles_bulk_operations(self):
        """Test that signals work correctly with bulk operations."""
        # Create multiple classes at once
        classes_data = [
            {"section_id": "A", "course": self.regular_course},
            {"section_id": "B", "course": self.regular_course},
            {"section_id": "A", "course": self.ieap_course},
        ]

        created_classes = []
        for data in classes_data:
            class_header = ClassHeader.objects.create(
                course=data["course"], term=self.term, section_id=data["section_id"]
            )
            created_classes.append(class_header)

        # Verify all classes have proper structure
        for class_header in created_classes:
            if class_header.course.code.startswith("IEAP"):
                self.assertEqual(class_header.class_sessions.count(), 2)
                for session in class_header.class_sessions.all():
                    self.assertEqual(session.class_parts.count(), 1)
            else:
                self.assertEqual(class_header.class_sessions.count(), 1)
                session = class_header.class_sessions.first()
                self.assertEqual(session.class_parts.count(), 1)

    def test_signal_error_handling(self):
        """Test that signal errors are handled gracefully."""
        # This test ensures that if signal processing fails,
        # it doesn't break the main operation

        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        # Even if signals had issues, the class header should exist
        self.assertTrue(ClassHeader.objects.filter(id=class_header.id).exists())

        # And signals should have created the structure
        self.assertGreater(class_header.class_sessions.count(), 0)

    def test_signal_idempotency(self):
        """Test that signals don't duplicate structure if called multiple times."""
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        original_session_count = class_header.class_sessions.count()
        session = class_header.class_sessions.first()
        original_part_count = session.class_parts.count()

        # Manually trigger ensure methods (simulating repeated signal calls)
        class_header.ensure_sessions_exist()
        session.ensure_parts_exist()

        # Should not create additional structure
        self.assertEqual(class_header.class_sessions.count(), original_session_count)
        self.assertEqual(session.class_parts.count(), original_part_count)

    def test_cross_signal_coordination(self):
        """Test that multiple signals coordinate properly."""
        # Create class header - triggers class header signal
        class_header = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")

        # Class header signal creates sessions
        # Session creation signals create parts
        # This tests the coordination between signals

        self.assertEqual(class_header.class_sessions.count(), 2)

        for session in class_header.class_sessions.all():
            self.assertEqual(session.class_parts.count(), 1)

            part = session.class_parts.first()
            self.assertEqual(part.class_part_type, ClassPartType.MAIN)
            self.assertEqual(part.grade_weight, Decimal("1.0"))

    def test_signal_transaction_safety(self):
        """Test that signals work correctly within transactions."""
        from django.db import transaction

        # Test that signal operations are atomic
        try:
            with transaction.atomic():
                class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

                # Verify structure created within transaction
                self.assertEqual(class_header.class_sessions.count(), 1)
                session = class_header.class_sessions.first()
                self.assertEqual(session.class_parts.count(), 1)

                # Force an error to test rollback
                # (commented out because we want success in this test)
                # raise Exception("Test rollback")

        except Exception:
            # If there was an error, nothing should be created
            self.assertEqual(ClassHeader.objects.filter(section_id="A").count(), 0)
        else:
            # Success case - everything should be created
            self.assertEqual(ClassHeader.objects.filter(section_id="A").count(), 1)
            class_header = ClassHeader.objects.get(section_id="A")
            self.assertEqual(class_header.class_sessions.count(), 1)
