"""Unit tests for CycleDetectionService.

Tests the business logic for detecting when students change academic cycles
(Language→Bachelor, Bachelor→Master) or are new students.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.curriculum.models import Major
from apps.enrollment.models import StudentCycleStatus
from apps.enrollment.services import CycleDetectionService
from apps.people.models import Person, StudentProfile

User = get_user_model()


class CycleDetectionServiceTest(TestCase):
    """Test cycle detection service business logic."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")

        # Create majors for different types
        self.language_major = Major.objects.create(
            code="ENG", name="English Language", major_type="LANGUAGE", is_active=True
        )

        self.bachelor_major = Major.objects.create(
            code="CS", name="Computer Science", major_type="BACHELOR", is_active=True
        )

        self.master_major = Major.objects.create(
            code="MBA", name="Master of Business Administration", major_type="MASTER", is_active=True
        )

        # Create test student
        person = Person.objects.create(
            personal_name="Test",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        self.student = StudentProfile.objects.create(
            person=person, student_id="240001", admission_date=date.today(), primary_major=self.language_major
        )

    def test_detect_new_student_entry(self):
        """Test detection of new student entry."""
        # Detect cycle change for new student
        cycle_status = CycleDetectionService.detect_cycle_change(self.student, self.language_major)

        self.assertIsNotNone(cycle_status)
        self.assertEqual(cycle_status.cycle_type, StudentCycleStatus.CycleType.NEW_ENTRY)
        self.assertIsNone(cycle_status.source_program)
        self.assertEqual(cycle_status.target_program, self.language_major)
        self.assertTrue(cycle_status.is_active)

    def test_detect_language_to_bachelor_transition(self):
        """Test detection of Language to Bachelor transition."""
        # First create initial entry status
        StudentCycleStatus.objects.create(
            student=self.student,
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            target_program=self.language_major,
            is_active=True,
        )

        # Update student's primary major
        self.student.primary_major = self.bachelor_major
        self.student.save()

        # Detect cycle change
        cycle_status = CycleDetectionService.detect_cycle_change(self.student, self.bachelor_major)

        self.assertIsNotNone(cycle_status)
        self.assertEqual(cycle_status.cycle_type, StudentCycleStatus.CycleType.LANGUAGE_TO_BACHELOR)
        self.assertEqual(cycle_status.source_program, self.language_major)
        self.assertEqual(cycle_status.target_program, self.bachelor_major)
        self.assertTrue(cycle_status.is_active)

    def test_detect_bachelor_to_master_transition(self):
        """Test detection of Bachelor to Master transition."""
        # Update student to bachelor program
        self.student.primary_major = self.bachelor_major
        self.student.save()

        # Create bachelor status
        StudentCycleStatus.objects.create(
            student=self.student,
            cycle_type=StudentCycleStatus.CycleType.LANGUAGE_TO_BACHELOR,
            source_program=self.language_major,
            target_program=self.bachelor_major,
            is_active=True,
        )

        # Update to master program
        self.student.primary_major = self.master_major
        self.student.save()

        # Detect cycle change
        cycle_status = CycleDetectionService.detect_cycle_change(self.student, self.master_major)

        self.assertIsNotNone(cycle_status)
        self.assertEqual(cycle_status.cycle_type, StudentCycleStatus.CycleType.BACHELOR_TO_MASTER)
        self.assertEqual(cycle_status.source_program, self.bachelor_major)
        self.assertEqual(cycle_status.target_program, self.master_major)
        self.assertTrue(cycle_status.is_active)

    def test_no_duplicate_detection(self):
        """Test that duplicate cycle statuses are not created."""
        # Create initial status
        CycleDetectionService.detect_cycle_change(self.student, self.language_major)

        # Try to detect again - should return None
        cycle_status = CycleDetectionService.detect_cycle_change(self.student, self.language_major)

        self.assertIsNone(cycle_status)

        # Verify only one status exists
        count = StudentCycleStatus.objects.filter(student=self.student, is_active=True).count()
        self.assertEqual(count, 1)

    def test_deactivate_previous_statuses(self):
        """Test that previous statuses are deactivated on transition."""
        # Create initial status
        initial_status = CycleDetectionService.detect_cycle_change(self.student, self.language_major)

        # Update to bachelor
        self.student.primary_major = self.bachelor_major
        self.student.save()

        # Detect new cycle
        new_status = CycleDetectionService.detect_cycle_change(self.student, self.bachelor_major)

        # Refresh initial status
        initial_status.refresh_from_db()

        # Verify initial status is deactivated
        self.assertFalse(initial_status.is_active)
        self.assertIsNotNone(initial_status.deactivated_date)
        self.assertEqual(initial_status.deactivation_reason, "Transitioned to new cycle")

        # Verify new status is active
        self.assertTrue(new_status.is_active)

    def test_get_current_cycle_status(self):
        """Test getting current active cycle status."""
        # No status initially
        status = CycleDetectionService.get_current_cycle_status(self.student)
        self.assertIsNone(status)

        # Create status
        created_status = CycleDetectionService.detect_cycle_change(self.student, self.language_major)

        # Get current status
        status = CycleDetectionService.get_current_cycle_status(self.student)
        self.assertEqual(status, created_status)

    def test_invalid_transitions_not_detected(self):
        """Test that invalid transitions are not detected."""
        # Create master status first
        self.student.primary_major = self.master_major
        self.student.save()

        StudentCycleStatus.objects.create(
            student=self.student,
            cycle_type=StudentCycleStatus.CycleType.BACHELOR_TO_MASTER,
            source_program=self.bachelor_major,
            target_program=self.master_major,
            is_active=True,
        )

        # Try to go back to language - should not detect
        cycle_status = CycleDetectionService.detect_cycle_change(self.student, self.language_major)

        self.assertIsNone(cycle_status)

    def test_same_level_transitions_not_detected(self):
        """Test that transitions within same level are not detected."""
        # Create another bachelor major
        another_bachelor = Major.objects.create(
            code="IT", name="Information Technology", major_type="BACHELOR", is_active=True
        )

        # Set initial bachelor major
        self.student.primary_major = self.bachelor_major
        self.student.save()

        # Create status
        CycleDetectionService.detect_cycle_change(self.student, self.bachelor_major)

        # Try to detect change to another bachelor major
        cycle_status = CycleDetectionService.detect_cycle_change(self.student, another_bachelor)

        # Should not detect as a cycle change
        self.assertIsNone(cycle_status)
