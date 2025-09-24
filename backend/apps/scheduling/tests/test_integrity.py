"""Comprehensive tests for scheduling integrity system.

This module tests the complete integrity system implemented for the scheduling app,
ensuring that ALL ClassParts MUST go through ClassSession and that the
ClassHeader → ClassSession → ClassPart architecture is properly enforced.

Test Coverage:
- Model integrity methods (ClassHeader, ClassSession)
- Signal handlers for automatic integrity enforcement
- ClassSchedulingService operations
- Management command functionality
- Admin interface integrity features
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, TransactionTestCase

from apps.curriculum.models import Course, Cycle, Division, Term
from apps.scheduling.class_part_types import ClassPartType
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession
from apps.scheduling.services import ClassSchedulingService

User = get_user_model()


@pytest.fixture
def sample_course():
    """Create a sample course for testing."""
    return Course.objects.create(code="TEST101", title="Test Course", credits=3)


@pytest.fixture
def sample_term():
    """Create a sample term for testing."""
    return Term.objects.create(code="2024T1", start_date="2024-01-15", end_date="2024-04-30")


@pytest.fixture
def ieap_course():
    """Create an IEAP course for testing."""
    return Course.objects.create(code="IEAP101", title="IEAP Test Course", credits=3)


class TestClassHeaderIntegrity(TransactionTestCase):
    """Test ClassHeader integrity methods and behavior."""

    def setUp(self):
        self.division = Division.objects.create(name="Test Division", short_name="TEST")
        self.cycle = Cycle.objects.create(name="Test Cycle", division=self.division)
        self.course = Course.objects.create(code="TEST101", title="Test Course", credits=3, cycle=self.cycle)
        self.ieap_course = Course.objects.create(code="IEAP101", title="IEAP Course", credits=3, cycle=self.cycle)
        self.term = Term.objects.create(code="2024T1", start_date="2024-01-15", end_date="2024-04-30")

    def test_is_ieap_class_detection(self):
        """Test IEAP class detection based on course code."""
        # Regular class
        regular_class = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")
        self.assertFalse(regular_class.is_ieap_class())

        # IEAP class
        ieap_class = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")
        self.assertTrue(ieap_class.is_ieap_class())

    def test_ensure_sessions_exist_regular_class(self):
        """Test that regular classes get exactly 1 session."""
        class_header = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")

        # Should have no sessions initially due to manual creation
        self.assertEqual(class_header.class_sessions.count(), 0)

        # Ensure sessions exist
        created_count, sessions = class_header.ensure_sessions_exist()

        self.assertEqual(created_count, 1)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(class_header.class_sessions.count(), 1)

        session = sessions[0]
        self.assertEqual(session.session_number, 1)
        self.assertEqual(session.grade_weight, Decimal("1.0"))

    def test_ensure_sessions_exist_ieap_class(self):
        """Test that IEAP classes get exactly 2 sessions."""
        class_header = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")

        # Ensure sessions exist
        created_count, sessions = class_header.ensure_sessions_exist()

        self.assertEqual(created_count, 2)
        self.assertEqual(len(sessions), 2)
        self.assertEqual(class_header.class_sessions.count(), 2)

        # Check session details
        session1, session2 = sorted(sessions, key=lambda s: s.session_number)

        self.assertEqual(session1.session_number, 1)
        self.assertEqual(session1.grade_weight, Decimal("0.5"))
        self.assertEqual(session1.session_name, "IEAP Session 1")

        self.assertEqual(session2.session_number, 2)
        self.assertEqual(session2.grade_weight, Decimal("0.5"))
        self.assertEqual(session2.session_name, "IEAP Session 2")

    def test_ensure_sessions_exist_idempotent(self):
        """Test that ensure_sessions_exist is idempotent."""
        class_header = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")

        # First call
        created_count1, sessions1 = class_header.ensure_sessions_exist()
        self.assertEqual(created_count1, 1)

        # Second call should not create additional sessions
        created_count2, sessions2 = class_header.ensure_sessions_exist()
        self.assertEqual(created_count2, 0)
        self.assertEqual(len(sessions2), 1)
        self.assertEqual(class_header.class_sessions.count(), 1)

    def test_validate_session_structure_valid_regular(self):
        """Test validation of valid regular class structure."""
        class_header = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")
        class_header.ensure_sessions_exist()

        validation = class_header.validate_session_structure()

        self.assertTrue(validation["valid"])
        self.assertEqual(len(validation["errors"]), 0)
        self.assertEqual(validation["session_count"], 1)
        self.assertEqual(validation["expected_count"], 1)

    def test_validate_session_structure_valid_ieap(self):
        """Test validation of valid IEAP class structure."""
        class_header = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")
        class_header.ensure_sessions_exist()

        validation = class_header.validate_session_structure()

        self.assertTrue(validation["valid"])
        self.assertEqual(len(validation["errors"]), 0)
        self.assertEqual(validation["session_count"], 2)
        self.assertEqual(validation["expected_count"], 2)

    def test_validate_session_structure_no_sessions(self):
        """Test validation when class has no sessions."""
        class_header = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")

        validation = class_header.validate_session_structure()

        self.assertFalse(validation["valid"])
        self.assertIn("has no sessions", validation["errors"][0])

    def test_validate_session_structure_wrong_count(self):
        """Test validation when class has wrong session count."""
        class_header = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")

        # Create wrong number of sessions
        ClassSession.objects.create(class_header=class_header, session_number=1, grade_weight=Decimal("0.5"))
        ClassSession.objects.create(class_header=class_header, session_number=2, grade_weight=Decimal("0.5"))

        validation = class_header.validate_session_structure()

        self.assertFalse(validation["valid"])
        self.assertIn("should have 1 session", validation["errors"][0])

    def test_helper_methods(self):
        """Test helper methods on ClassHeader."""
        class_header = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")
        class_header.ensure_sessions_exist()

        # Create a part with teacher and room
        session = class_header.class_sessions.first()
        part = ClassPart.objects.create(
            class_session=session,
            class_part_code="A",
            class_part_type=ClassPartType.MAIN,
            meeting_days="MW",
            grade_weight=Decimal("1.0"),
        )

        # Test helper methods
        all_parts = class_header.get_all_parts()
        self.assertEqual(len(all_parts), 1)
        self.assertEqual(all_parts[0], part)

        # Test meeting days aggregation
        meeting_days = class_header.get_all_meeting_days()
        self.assertEqual(meeting_days, ["MW"])


class TestClassSessionIntegrity(TransactionTestCase):
    """Test ClassSession integrity methods and behavior."""

    def setUp(self):
        self.division = Division.objects.create(name="Test Division", short_name="TEST")
        self.cycle = Cycle.objects.create(name="Test Cycle", division=self.division)
        self.course = Course.objects.create(code="TEST101", title="Test Course", credits=3, cycle=self.cycle)
        self.term = Term.objects.create(code="2024T1", start_date="2024-01-15", end_date="2024-04-30")
        self.class_header = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")
        self.session = ClassSession.objects.create(
            class_header=self.class_header, session_number=1, grade_weight=Decimal("1.0")
        )

    def test_ensure_parts_exist(self):
        """Test that sessions get at least one part."""
        # Should have no parts initially
        self.assertEqual(self.session.class_parts.count(), 0)

        # Ensure parts exist
        created_count = self.session.ensure_parts_exist()

        self.assertEqual(created_count, 1)
        self.assertEqual(self.session.class_parts.count(), 1)

        part = self.session.class_parts.first()
        self.assertEqual(part.class_part_code, "A")
        self.assertEqual(part.class_part_type, ClassPartType.MAIN)
        self.assertEqual(part.grade_weight, Decimal("1.0"))

    def test_ensure_parts_exist_idempotent(self):
        """Test that ensure_parts_exist is idempotent."""
        # First call
        created_count1 = self.session.ensure_parts_exist()
        self.assertEqual(created_count1, 1)

        # Second call should not create additional parts
        created_count2 = self.session.ensure_parts_exist()
        self.assertEqual(created_count2, 0)
        self.assertEqual(self.session.class_parts.count(), 1)

    def test_validate_parts_structure_valid(self):
        """Test validation of valid parts structure."""
        ClassPart.objects.create(
            class_session=self.session,
            class_part_code="A",
            class_part_type=ClassPartType.MAIN,
            grade_weight=Decimal("1.0"),
        )

        validation = self.session.validate_parts_structure()

        self.assertTrue(validation["valid"])
        self.assertEqual(len(validation["errors"]), 0)
        self.assertEqual(validation["part_count"], 1)

    def test_validate_parts_structure_no_parts(self):
        """Test validation when session has no parts."""
        validation = self.session.validate_parts_structure()

        self.assertFalse(validation["valid"])
        self.assertIn("has no parts", validation["errors"][0])

    def test_validate_parts_structure_weight_issues(self):
        """Test validation of grade weight issues."""
        # Create parts with incorrect weights
        ClassPart.objects.create(
            class_session=self.session,
            class_part_code="A",
            class_part_type=ClassPartType.MAIN,
            grade_weight=Decimal("0.6"),
        )
        ClassPart.objects.create(
            class_session=self.session,
            class_part_code="B",
            class_part_type=ClassPartType.LAB,
            grade_weight=Decimal("0.3"),
        )

        validation = self.session.validate_parts_structure()

        # Should be valid but have warnings
        self.assertTrue(validation["valid"])
        self.assertGreater(len(validation["warnings"]), 0)
        self.assertIn("total weight", validation["warnings"][0])


class TestSignalHandlers(TransactionTestCase):
    """Test signal handlers for automatic integrity enforcement."""

    def setUp(self):
        self.division = Division.objects.create(name="Test Division", short_name="TEST")
        self.cycle = Cycle.objects.create(name="Test Cycle", division=self.division)
        self.course = Course.objects.create(code="TEST101", title="Test Course", credits=3, cycle=self.cycle)
        self.ieap_course = Course.objects.create(code="IEAP101", title="IEAP Course", credits=3, cycle=self.cycle)
        self.term = Term.objects.create(code="2024T1", start_date="2024-01-15", end_date="2024-04-30")

    def test_auto_create_sessions_on_class_creation(self):
        """Test that sessions are automatically created when ClassHeader is created."""
        # Regular class
        regular_class = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")

        # Signal should have created 1 session
        self.assertEqual(regular_class.class_sessions.count(), 1)

        # IEAP class
        ieap_class = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")

        # Signal should have created 2 sessions
        self.assertEqual(ieap_class.class_sessions.count(), 2)

    def test_auto_create_part_on_session_creation(self):
        """Test that parts are automatically created when ClassSession is created."""
        class_header = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")

        # Get the auto-created session
        session = class_header.class_sessions.first()

        # Signal should have created a default part
        self.assertEqual(session.class_parts.count(), 1)

        part = session.class_parts.first()
        self.assertEqual(part.class_part_code, "A")
        self.assertEqual(part.class_part_type, ClassPartType.MAIN)

    def test_prevent_last_session_deletion(self):
        """Test that deletion of required sessions is prevented."""
        class_header = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")

        session = class_header.class_sessions.first()

        # Should not be able to delete the only session
        with self.assertRaises(ValidationError):
            session.delete()

    def test_prevent_ieap_session_deletion(self):
        """Test that IEAP sessions cannot be deleted below minimum."""
        ieap_class = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")

        sessions = list(ieap_class.class_sessions.all())
        self.assertEqual(len(sessions), 2)

        # Should not be able to delete any session from IEAP class
        with self.assertRaises(ValidationError):
            sessions[0].delete()


class TestClassSchedulingService(TestCase):
    """Test ClassSchedulingService operations."""

    def setUp(self):
        self.division = Division.objects.create(name="Test Division", short_name="TEST")
        self.cycle = Cycle.objects.create(name="Test Cycle", division=self.division)
        self.course = Course.objects.create(code="TEST101", title="Test Course", credits=3, cycle=self.cycle)
        self.ieap_course = Course.objects.create(code="IEAP101", title="IEAP Course", credits=3, cycle=self.cycle)
        self.term = Term.objects.create(code="2024T1", start_date="2024-01-15", end_date="2024-04-30")

    def test_create_class_with_structure_regular(self):
        """Test creating a regular class with proper structure."""
        result = ClassSchedulingService.create_class_with_structure(course=self.course, term=self.term, section_id="A")

        self.assertIn("class_header", result)
        self.assertIn("sessions", result)
        self.assertIn("parts", result)

        class_header = result["class_header"]
        self.assertEqual(class_header.course, self.course)
        self.assertEqual(class_header.section_id, "A")

        self.assertFalse(result["is_ieap"])
        self.assertEqual(result["session_count"], 1)
        self.assertEqual(result["part_count"], 1)

        # Verify structure
        self.assertEqual(class_header.class_sessions.count(), 1)
        session = class_header.class_sessions.first()
        self.assertEqual(session.class_parts.count(), 1)

    def test_create_class_with_structure_ieap(self):
        """Test creating an IEAP class with proper structure."""
        result = ClassSchedulingService.create_class_with_structure(
            course=self.ieap_course, term=self.term, section_id="A"
        )

        class_header = result["class_header"]

        self.assertTrue(result["is_ieap"])
        self.assertEqual(result["session_count"], 2)
        self.assertEqual(result["part_count"], 2)

        # Verify structure
        self.assertEqual(class_header.class_sessions.count(), 2)
        for session in class_header.class_sessions.all():
            self.assertEqual(session.class_parts.count(), 1)

    def test_duplicate_class_structure(self):
        """Test duplicating a class structure."""
        # Create source class
        source_result = ClassSchedulingService.create_class_with_structure(
            course=self.course, term=self.term, section_id="A", max_enrollment=25
        )
        source_class = source_result["class_header"]

        # Add some details to source
        session = source_class.class_sessions.first()
        part = session.class_parts.first()
        part.meeting_days = "MW"
        part.start_time = "09:00:00"
        part.end_time = "10:30:00"
        part.save()

        # Duplicate to new section
        result = ClassSchedulingService.duplicate_class_structure(source_class=source_class, section_id="B")

        new_class = result["class_header"]

        self.assertEqual(new_class.course, source_class.course)
        self.assertEqual(new_class.term, source_class.term)
        self.assertEqual(new_class.section_id, "B")
        self.assertEqual(new_class.max_enrollment, 25)

        # Verify structure was copied
        self.assertEqual(new_class.class_sessions.count(), 1)
        new_session = new_class.class_sessions.first()
        self.assertEqual(new_session.class_parts.count(), 1)

        new_part = new_session.class_parts.first()
        self.assertEqual(new_part.meeting_days, "MW")
        self.assertEqual(str(new_part.start_time), "09:00:00")
        self.assertEqual(str(new_part.end_time), "10:30:00")

    def test_validate_all_classes_in_term(self):
        """Test validating all classes in a term."""
        # Create some classes with various issues

        # Valid class
        ClassSchedulingService.create_class_with_structure(course=self.course, term=self.term, section_id="A")

        # Class with no sessions (create manually)
        broken_class = ClassHeader.objects.create(course=self.course, term=self.term, section_id="B")
        # Clear sessions that might be auto-created
        broken_class.class_sessions.all().delete()

        # Validate term
        results = ClassSchedulingService.validate_all_classes_in_term(self.term)

        self.assertEqual(results["total_classes"], 2)
        self.assertEqual(results["valid_classes"], 1)
        self.assertEqual(results["invalid_classes"], 1)

        # Check specific issues
        self.assertEqual(len(results["issues"]["no_sessions"]), 1)
        self.assertIn(broken_class, results["issues"]["no_sessions"])

    def test_fix_class_structure_issues_dry_run(self):
        """Test dry run of structure issue fixes."""
        # Create broken class
        broken_class = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")
        broken_class.class_sessions.all().delete()

        # Dry run fix
        results = ClassSchedulingService.fix_class_structure_issues(self.term, dry_run=True)

        self.assertTrue(results["dry_run"])
        self.assertGreater(len(results["actions_taken"]), 0)
        self.assertIn("Would create", results["actions_taken"][0])

        # Should not have actually fixed anything
        self.assertEqual(broken_class.class_sessions.count(), 0)

    def test_fix_class_structure_issues_actual(self):
        """Test actual fixing of structure issues."""
        # Create broken class
        broken_class = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")
        broken_class.class_sessions.all().delete()

        # Actual fix
        results = ClassSchedulingService.fix_class_structure_issues(self.term, dry_run=False)

        self.assertFalse(results["dry_run"])
        self.assertGreater(len(results["actions_taken"]), 0)
        self.assertIn("Created", results["actions_taken"][0])

        # Should have fixed the issue
        broken_class.refresh_from_db()
        self.assertEqual(broken_class.class_sessions.count(), 1)


class TestManagementCommand(TestCase):
    """Test the check_class_integrity management command."""

    def setUp(self):
        self.division = Division.objects.create(name="Test Division", short_name="TEST")
        self.cycle = Cycle.objects.create(name="Test Cycle", division=self.division)
        self.course = Course.objects.create(code="TEST101", title="Test Course", credits=3, cycle=self.cycle)
        self.term = Term.objects.create(code="2024T1", start_date="2024-01-15", end_date="2024-04-30")

    def test_command_check_only(self):
        """Test command in check-only mode."""
        # Create a broken class
        broken_class = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")
        broken_class.class_sessions.all().delete()

        # Run command
        call_command("check_class_integrity", "--term", self.term.id)

        # Should not have fixed anything
        self.assertEqual(broken_class.class_sessions.count(), 0)

    def test_command_with_fix(self):
        """Test command with fix mode."""
        # Create a broken class
        broken_class = ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")
        broken_class.class_sessions.all().delete()

        # Run command with fix
        call_command("check_class_integrity", "--fix", "--term", self.term.id)

        # Should have fixed the issue
        broken_class.refresh_from_db()
        self.assertEqual(broken_class.class_sessions.count(), 1)

    def test_command_all_terms(self):
        """Test command running on all terms."""
        # Create classes in multiple terms
        term2 = Term.objects.create(code="2024T2", start_date="2024-05-01", end_date="2024-08-30")

        ClassSchedulingService.create_class_with_structure(course=self.course, term=self.term, section_id="A")
        ClassSchedulingService.create_class_with_structure(course=self.course, term=term2, section_id="A")

        # Run command without term filter
        call_command("check_class_integrity")

        # Command should complete without errors


class TestIntegrityIntegration(TransactionTestCase):
    """Integration tests for the complete integrity system."""

    def setUp(self):
        self.division = Division.objects.create(name="Test Division", short_name="TEST")
        self.cycle = Cycle.objects.create(name="Test Cycle", division=self.division)
        self.course = Course.objects.create(code="TEST101", title="Test Course", credits=3, cycle=self.cycle)
        self.ieap_course = Course.objects.create(code="IEAP101", title="IEAP Course", credits=3, cycle=self.cycle)
        self.term = Term.objects.create(code="2024T1", start_date="2024-01-15", end_date="2024-04-30")
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass")

    def test_complete_class_creation_workflow(self):
        """Test complete workflow from class creation to validation."""
        # Create class using service (highest level)
        result = ClassSchedulingService.create_class_with_structure(
            course=self.course, term=self.term, section_id="A", max_enrollment=25
        )

        class_header = result["class_header"]

        # Verify complete structure was created
        self.assertEqual(class_header.class_sessions.count(), 1)
        session = class_header.class_sessions.first()
        self.assertEqual(session.class_parts.count(), 1)

        # Validate using service
        validation_results = ClassSchedulingService.validate_all_classes_in_term(self.term)
        self.assertEqual(validation_results["valid_classes"], 1)
        self.assertEqual(validation_results["invalid_classes"], 0)

        # Test model-level validation
        header_validation = class_header.validate_session_structure()
        self.assertTrue(header_validation["valid"])

        session_validation = session.validate_parts_structure()
        self.assertTrue(session_validation["valid"])

    def test_ieap_complete_workflow(self):
        """Test complete workflow for IEAP classes."""
        # Create IEAP class
        result = ClassSchedulingService.create_class_with_structure(
            course=self.ieap_course, term=self.term, section_id="A"
        )

        class_header = result["class_header"]

        # Verify IEAP structure
        self.assertTrue(class_header.is_ieap_class())
        self.assertEqual(class_header.class_sessions.count(), 2)

        # Each session should have parts
        for session in class_header.class_sessions.all():
            self.assertEqual(session.class_parts.count(), 1)
            self.assertEqual(session.grade_weight, Decimal("0.5"))

    def test_duplicate_and_validate_workflow(self):
        """Test workflow for duplicating classes and validating results."""
        # Create source class
        source_result = ClassSchedulingService.create_class_with_structure(
            course=self.course, term=self.term, section_id="A"
        )
        source_class = source_result["class_header"]

        # Duplicate to multiple sections
        sections = ["B", "C", "D"]
        for section in sections:
            ClassSchedulingService.duplicate_class_structure(source_class=source_class, section_id=section)

        # Validate all classes
        validation_results = ClassSchedulingService.validate_all_classes_in_term(self.term)

        self.assertEqual(validation_results["total_classes"], 4)  # A, B, C, D
        self.assertEqual(validation_results["valid_classes"], 4)
        self.assertEqual(validation_results["invalid_classes"], 0)

    def test_error_recovery_workflow(self):
        """Test workflow for detecting and fixing errors."""
        # Create some classes
        ClassSchedulingService.create_class_with_structure(course=self.course, term=self.term, section_id="A")

        # Manually break one class (simulate data corruption)
        broken_class = ClassHeader.objects.create(course=self.course, term=self.term, section_id="B")
        broken_class.class_sessions.all().delete()

        # Detect issues
        validation_results = ClassSchedulingService.validate_all_classes_in_term(self.term)
        self.assertEqual(validation_results["invalid_classes"], 1)

        # Fix issues
        fix_results = ClassSchedulingService.fix_class_structure_issues(self.term, dry_run=False)
        self.assertGreater(len(fix_results["actions_taken"]), 0)

        # Verify fixes
        validation_results2 = ClassSchedulingService.validate_all_classes_in_term(self.term)
        self.assertEqual(validation_results2["invalid_classes"], 0)

    def test_concurrent_class_creation(self):
        """Test that concurrent class creation maintains integrity."""

        def create_class(section_id):
            return ClassSchedulingService.create_class_with_structure(
                course=self.course, term=self.term, section_id=section_id
            )

        # Create multiple classes concurrently (simulated)
        results = []
        for section in ["A", "B", "C"]:
            with transaction.atomic():
                result = create_class(section)
                results.append(result)

        # Validate all were created properly
        validation_results = ClassSchedulingService.validate_all_classes_in_term(self.term)
        self.assertEqual(validation_results["total_classes"], 3)
        self.assertEqual(validation_results["valid_classes"], 3)

    def test_mixed_class_types_validation(self):
        """Test validation with mixed regular and IEAP classes."""
        # Create regular class
        ClassSchedulingService.create_class_with_structure(course=self.course, term=self.term, section_id="A")

        # Create IEAP class
        ClassSchedulingService.create_class_with_structure(course=self.ieap_course, term=self.term, section_id="A")

        # Validate term
        validation_results = ClassSchedulingService.validate_all_classes_in_term(self.term)

        self.assertEqual(validation_results["total_classes"], 2)
        self.assertEqual(validation_results["valid_classes"], 2)
        self.assertEqual(validation_results["statistics"]["regular_classes"], 1)
        self.assertEqual(validation_results["statistics"]["ieap_classes"], 1)
        self.assertEqual(validation_results["statistics"]["total_sessions"], 3)  # 1 + 2
        self.assertEqual(validation_results["statistics"]["total_parts"], 3)  # 1 + 2
