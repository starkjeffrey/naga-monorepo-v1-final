"""Comprehensive tests for scheduling app models.

Tests all scheduling models following clean architecture principles:
- CombinedClassGroup: Administrative grouping functionality
- ClassHeader: Core class instance functionality
- ClassSession: Session grouping for IEAP support
- ClassPart: Class component functionality
- ReadingClass: Specialized tiered class functionality

Key testing areas:
- Model validation and business logic
- Property methods and calculated fields
- Clean methods and constraint validation
- Status transitions and workflow management
- Relationships and dependency management
- IEAP session management and exemptions
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.common.models import Room
from apps.curriculum.models import Course, Cycle, Division, Term, Textbook
from apps.people.models import Person, TeacherProfile
from apps.scheduling.class_part_types import ClassPartType
from apps.scheduling.models import (
    ClassHeader,
    ClassPart,
    ClassSession,
    CombinedClassGroup,
    ReadingClass,
)

User = get_user_model()

# Test constants for magic value elimination
MAX_CLASS_CAPACITY = 20
STANDARD_LESSON_DURATION_MINUTES = 90
READING_CLASS_TARGET_ENROLLMENT = 3
EXPECTED_CLASS_PARTS_COUNT = 2
EXPECTED_MEMBER_CLASS_HEADERS_COUNT = 2
EXPECTED_MEMBER_COUNT = 2


class CombinedClassGroupModelTest(TestCase):
    """Test CombinedClassGroup model functionality."""

    def setUp(self):
        """Set up test data."""
        self.term = Term.objects.create(
            code="2025F",
            start_date="2025-09-01",
            end_date="2025-12-15",
        )

    def test_create_combined_class_group(self):
        """Test creating a combined class group."""
        group = CombinedClassGroup.objects.create(
            name="ESL Level 1 Combined",
            term=self.term,
            description="Combined sections for ESL Level 1",
        )

        assert group.name == "ESL Level 1 Combined"
        assert group.term == self.term
        assert str(group) == f"{self.term} - ESL Level 1 Combined"

    def test_unique_together_constraint(self):
        """Test unique constraint on term and name."""
        CombinedClassGroup.objects.create(name="Test Group", term=self.term)

        with pytest.raises(IntegrityError):
            CombinedClassGroup.objects.create(name="Test Group", term=self.term)

    def test_member_count_property(self):
        """Test member_count property."""
        group = CombinedClassGroup.objects.create(name="Test Group", term=self.term)

        assert group.member_count == 0


class ClassHeaderModelTest(TestCase):
    """Test ClassHeader model functionality."""

    def setUp(self):
        """Set up test data."""
        self.term = Term.objects.create(
            code="2025F",
            start_date="2025-09-01",
            end_date="2025-12-15",
        )

        self.division = Division.objects.create(
            name="General English as Second Language",
            short_name="GESL",
        )

        self.cycle = Cycle.objects.create(
            name="Language Program Cycle",
            division=self.division,
        )

        self.course = Course.objects.create(
            code="GESL-01",
            title="General English Level 1",
            short_title="GESL Level 1",
            cycle=self.cycle,
            credits=3,
        )

    def test_create_class_header(self):
        """Test creating a class header."""
        class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            time_of_day=ClassHeader.TimeOfDay.MORNING,
            class_type=ClassHeader.ClassType.STANDARD,
            max_enrollment=15,
        )

        assert class_header.course == self.course
        assert class_header.section_id == "A"
        assert str(class_header) == f"{self.course.code} A ({self.term})"

    def test_unique_together_constraint(self):
        """Test unique constraint on course, term, and section_id."""
        ClassHeader.objects.create(course=self.course, term=self.term, section_id="A")

        with pytest.raises(IntegrityError):
            ClassHeader.objects.create(
                course=self.course,
                term=self.term,
                section_id="A",
            )

    def test_section_id_validation(self):
        """Test section ID validation."""
        class_header = ClassHeader(
            course=self.course,
            term=self.term,
            section_id="AB",  # Invalid - should be single letter
            time_of_day=ClassHeader.TimeOfDay.MORNING,
        )

        with pytest.raises(ValidationError):
            class_header.full_clean()

    def test_pairing_validation(self):
        """Test class pairing validation."""
        class_header = ClassHeader(
            course=self.course,
            term=self.term,
            section_id="A",
            is_paired=True,
            paired_with=None,
        )

        with pytest.raises(ValidationError):
            class_header.clean()

    def test_pairing_symmetry(self):
        """Test that pairing is symmetric."""
        class_header_1 = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            time_of_day=ClassHeader.TimeOfDay.MORNING,
        )

        class_header_2 = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="B",
            time_of_day=ClassHeader.TimeOfDay.MORNING,
        )

        # Pair them
        class_header_1.is_paired = True
        class_header_1.paired_with = class_header_2
        class_header_1.save()

        # Refresh from database
        class_header_2.refresh_from_db()

        assert class_header_2.is_paired
        assert class_header_2.paired_with == class_header_1

    def test_properties(self):
        """Test class header properties."""
        class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            max_enrollment=MAX_CLASS_CAPACITY,
        )

        assert class_header.full_name == f"{self.course.title} - Section A"
        assert class_header.enrollment_count == 0
        assert not class_header.is_full
        assert class_header.available_spots == MAX_CLASS_CAPACITY


class ClassPartModelTest(TestCase):
    """Test ClassPart model functionality."""

    def setUp(self):
        """Set up test data."""
        self.term = Term.objects.create(
            code="2025F",
            start_date="2025-09-01",
            end_date="2025-12-15",
        )

        self.division = Division.objects.create(
            name="General English as Second Language",
            short_name="GESL",
        )

        self.cycle = Cycle.objects.create(
            name="Language Program Cycle",
            division=self.division,
        )

        self.course = Course.objects.create(
            code="GESL-01",
            title="General English Level 1",
            short_title="GESL Level 1",
            cycle=self.cycle,
            credits=3,
        )

        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
        )

        # Create default class session
        self.class_session = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
        )

        self.person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth="1980-01-01",
        )

        self.teacher = TeacherProfile.objects.create(
            person=self.person,
        )

        self.room = Room.objects.create(
            name="Classroom 101",
            building="MAIN",
        )

        self.textbook = Textbook.objects.create(
            title="English Grammar Basics",
            isbn="978-0123456789",
            publisher="Test Publisher",
        )

    def test_create_class_part(self):
        """Test creating a class part."""
        class_part = ClassPart.objects.create(
            class_session=self.class_session,
            class_part_type=ClassPartType.GRAMMAR,
            class_part_code="A",
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:00",
            teacher=self.teacher,
            room=self.room,
            grade_weight=Decimal("0.500"),
        )

        assert class_part.class_session == self.class_session
        assert class_part.class_header == self.class_header  # Through session
        assert class_part.class_part_type == ClassPartType.GRAMMAR
        assert class_part.teacher == self.teacher
        assert class_part.room == self.room

    def test_unique_together_constraint(self):
        """Test unique constraint on class_session and class_part_code."""
        ClassPart.objects.create(
            class_session=self.class_session,
            class_part_code="A",
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:00",
        )

        with pytest.raises(IntegrityError):
            ClassPart.objects.create(
                class_session=self.class_session,
                class_part_code="A",  # Same code for same session
                meeting_days="TUE,THU",
                start_time="10:00",
                end_time="11:00",
            )

    def test_time_validation(self):
        """Test time validation."""
        class_part = ClassPart(
            class_session=self.class_session,
            meeting_days="MON,WED,FRI",
            start_time="10:00",
            end_time="09:00",  # End before start - invalid
            grade_weight=Decimal("1.000"),
        )

        with pytest.raises(ValidationError):
            class_part.clean()

    def test_grade_weight_validation(self):
        """Test grade weight validation."""
        class_part = ClassPart(
            class_session=self.class_session,
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:00",
            grade_weight=Decimal("1.500"),  # Invalid - above 1.0
        )

        with pytest.raises(ValidationError):
            class_part.clean()

    def test_meeting_days_validation(self):
        """Test meeting days validation."""
        class_part = ClassPart(
            class_session=self.class_session,
            meeting_days="MON,INVALID,FRI",  # Invalid day
            start_time="09:00",
            end_time="10:00",
        )

        with pytest.raises(ValidationError):
            class_part.clean()

    def test_properties(self):
        """Test class part properties."""
        class_part = ClassPart.objects.create(
            class_session=self.class_session,
            class_part_type=ClassPartType.GRAMMAR,
            name="Grammar Fundamentals",
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:30",
        )

        assert class_part.duration_minutes == STANDARD_LESSON_DURATION_MINUTES
        assert class_part.meeting_days_list == ["MON", "WED", "FRI"]
        assert "Grammar Fundamentals" in class_part.full_name
        assert class_part.enrollment_count == 0

    def test_textbook_assignment(self):
        """Test textbook assignment to class part."""
        class_part = ClassPart.objects.create(
            class_session=self.class_session,
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:00",
        )

        class_part.textbooks.add(self.textbook)

        assert self.textbook in class_part.textbooks.all()


class ClassSessionModelTest(TestCase):
    """Test ClassSession model functionality."""

    def setUp(self):
        """Set up test data."""
        self.term = Term.objects.create(
            code="2025F",
            start_date="2025-09-01",
            end_date="2025-12-15",
        )

        self.division = Division.objects.create(
            name="Intensive English Academic Program",
            short_name="IEAP",
        )

        self.cycle = Cycle.objects.create(
            name="IEAP Program Cycle",
            division=self.division,
        )

        self.course = Course.objects.create(
            code="IEAP-01",
            title="IEAP Level 1",
            short_title="IEAP Level 1",
            cycle=self.cycle,
            credits=6,
        )

        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
        )

    def test_create_single_session(self):
        """Test creating a single session for regular classes."""
        session = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
            grade_weight=Decimal("1.000"),
        )

        assert session.class_header == self.class_header
        assert session.session_number == 1
        assert session.grade_weight == Decimal("1.000")
        assert not session.is_ieap_session  # Single session

    def test_create_ieap_sessions(self):
        """Test creating dual sessions for IEAP classes."""
        session1 = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
            session_name="Session 1",
            grade_weight=Decimal("0.500"),
        )

        session2 = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=2,
            session_name="Session 2",
            grade_weight=Decimal("0.500"),
        )

        assert session1.is_ieap_session  # Multiple sessions
        assert session2.is_ieap_session
        assert session1.grade_weight + session2.grade_weight == Decimal("1.000")

    def test_unique_together_constraint(self):
        """Test unique constraint on class_header and session_number."""
        ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
        )

        with pytest.raises(IntegrityError):
            ClassSession.objects.create(
                class_header=self.class_header,
                session_number=1,  # Same session number
            )

    def test_session_validation(self):
        """Test session number validation."""
        session = ClassSession(
            class_header=self.class_header,
            session_number=0,  # Invalid - below minimum
        )

        with pytest.raises(ValidationError):
            session.full_clean()

    def test_grade_weight_validation(self):
        """Test grade weight validation."""
        session = ClassSession(
            class_header=self.class_header,
            session_number=1,
            grade_weight=Decimal("1.500"),  # Invalid - above 1.0
        )

        with pytest.raises(ValidationError):
            session.full_clean()

    def test_str_representation(self):
        """Test string representation logic."""
        # Regular class (single session)
        regular_session = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
        )
        assert str(regular_session) == str(self.class_header)

        # IEAP class (multiple sessions)
        ieap_session = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=2,
            session_name="Session 2",
        )
        assert "Session 2" in str(ieap_session)

    def test_part_count_property(self):
        """Test part_count property."""
        session = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
        )

        assert session.part_count == 0

        # Add a class part
        ClassPart.objects.create(
            class_session=session,
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:00",
        )

        assert session.part_count == 1

    def test_room_conflict_validation(self):
        """Test room conflict validation in ClassPart."""
        room = Room.objects.create(
            name="Room 101",
            building="MAIN",
        )

        session1 = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
        )

        # Create first class part
        ClassPart.objects.create(
            class_session=session1,
            room=room,
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:00",
        )

        # Try to create conflicting class part
        session2 = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=2,
        )

        conflicting_part = ClassPart(
            class_session=session2,
            room=room,  # Same room
            meeting_days="MON,TUE,WED",  # Overlapping days (MON, WED)
            start_time="09:30",  # Overlapping time
            end_time="10:30",
        )

        with pytest.raises(ValidationError):
            conflicting_part.clean()


class ReadingClassModelTest(TestCase):
    """Test ReadingClass model functionality."""

    def setUp(self):
        """Set up test data."""
        self.term = Term.objects.create(
            code="2025F",
            start_date="2025-09-01",
            end_date="2025-12-15",
        )

        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )

        self.course = Course.objects.create(
            code="ENGL-101",
            title="Introduction to Literature",
            short_title="Intro Literature",
            cycle=self.cycle,
            credits=3,
        )

        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            class_type=ClassHeader.ClassType.READING,
        )

    def test_create_reading_class(self):
        """Test creating a reading class."""
        reading_class = ReadingClass.objects.create(
            class_header=self.class_header,
            tier=ReadingClass.Tier.TIER_1,
            target_enrollment=READING_CLASS_TARGET_ENROLLMENT,
            enrollment_status=ReadingClass.EnrollmentStatus.PLANNING,
        )

        assert reading_class.class_header == self.class_header
        assert reading_class.tier == ReadingClass.Tier.TIER_1
        assert reading_class.target_enrollment == READING_CLASS_TARGET_ENROLLMENT

    def test_class_type_validation(self):
        """Test that reading class must be READING type."""
        # Create a non-reading class header
        standard_class = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="B",
            class_type=ClassHeader.ClassType.STANDARD,
        )

        reading_class = ReadingClass(
            class_header=standard_class,
            tier=ReadingClass.Tier.TIER_1,
        )

        with pytest.raises(ValidationError):
            reading_class.clean()

    def test_target_enrollment_validation(self):
        """Test target enrollment validation."""
        reading_class = ReadingClass(
            class_header=self.class_header,
            target_enrollment=20,  # Above 15 - invalid for reading class
        )

        with pytest.raises(ValidationError):
            reading_class.clean()

    def test_tier_calculation(self):
        """Test tier calculation logic."""
        reading_class = ReadingClass.objects.create(
            class_header=self.class_header,
            tier=ReadingClass.Tier.TIER_1,
        )

        # Test tier calculation for different enrollment counts
        # Mock enrollment count = 0 (TIER_1)
        assert reading_class.calculate_tier() == ReadingClass.Tier.TIER_1

        # The actual tier calculation would need enrollment data

    def test_conversion_check(self):
        """Test conversion to standard class check."""
        reading_class = ReadingClass.objects.create(
            class_header=self.class_header,
            tier=ReadingClass.Tier.TIER_3,
        )

        # With no enrollment, should not be convertible
        assert not reading_class.can_convert_to_standard

    def test_properties(self):
        """Test reading class properties."""
        reading_class = ReadingClass.objects.create(
            class_header=self.class_header,
            tier=ReadingClass.Tier.TIER_2,
            description="Advanced reading comprehension",
        )

        assert reading_class.enrollment_count == 0
        assert "Reading:" in str(reading_class)
        assert "Tier 2" in str(reading_class)


class SchedulingIntegrityTest(TestCase):
    """Test scheduling integrity enforcement and validation."""

    def setUp(self):
        """Set up test data for integrity tests."""
        self.term = Term.objects.create(
            code="2025F",
            start_date="2025-09-01",
            end_date="2025-12-15",
        )

        self.division = Division.objects.create(
            name="General English as Second Language",
            short_name="GESL",
        )

        self.regular_course = Course.objects.create(
            code="GESL-01",
            title="General English Level 1",
            cycle=self.cycle,
            credits=3,
        )

        self.ieap_course = Course.objects.create(
            code="IEAP-01",
            title="IEAP Level 1",
            cycle=self.cycle,
            credits=6,
        )

    def test_regular_class_integrity_structure(self):
        """Test that regular classes maintain proper structure integrity."""
        # Create class header - signals should create proper structure
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        # Verify structure was created properly
        self.assertEqual(class_header.class_sessions.count(), 1)

        session = class_header.class_sessions.first()
        self.assertEqual(session.session_number, 1)
        self.assertEqual(session.grade_weight, Decimal("1.0"))

        # Signal should have also created a default part
        self.assertEqual(session.class_parts.count(), 1)

        part = session.class_parts.first()
        self.assertEqual(part.class_part_code, "A")
        self.assertEqual(part.class_part_type, ClassPartType.MAIN)

    def test_ieap_class_integrity_structure(self):
        """Test that IEAP classes maintain proper dual-session structure."""
        # Create IEAP class header
        class_header = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")

        # Verify IEAP structure
        self.assertTrue(class_header.is_ieap_class())
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

    def test_integrity_validation_methods(self):
        """Test integrity validation methods detect and report issues."""
        # Create class with proper structure
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        # Should validate as correct
        validation = class_header.validate_session_structure()
        self.assertTrue(validation["valid"])
        self.assertEqual(len(validation["errors"]), 0)

        # Break the structure by deleting sessions
        class_header.class_sessions.all().delete()

        # Should now detect the problem
        validation = class_header.validate_session_structure()
        self.assertFalse(validation["valid"])
        self.assertGreater(len(validation["errors"]), 0)
        self.assertIn("no sessions", validation["errors"][0])

    def test_orphaned_parts_prevention(self):
        """Test that orphaned parts (without sessions) are prevented."""
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        session = class_header.class_sessions.first()

        # This should work fine
        part = ClassPart.objects.create(
            class_session=session, class_part_code="B", class_part_type=ClassPartType.CONVERSATION
        )

        self.assertEqual(part.class_session, session)
        self.assertEqual(part.class_header, class_header)

    def test_session_deletion_prevention(self):
        """Test that deletion of required sessions is prevented."""
        # Regular class - cannot delete the only session
        regular_class = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        session = regular_class.class_sessions.first()

        with pytest.raises(ValidationError):
            session.delete()

        # IEAP class - cannot delete any session
        ieap_class = ClassHeader.objects.create(course=self.ieap_course, term=self.term, section_id="A")

        sessions = list(ieap_class.class_sessions.all())

        for session in sessions:
            with pytest.raises(ValidationError):
                session.delete()

    def test_ensure_methods_idempotency(self):
        """Test that ensure methods are idempotent."""
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        # Multiple calls should not create additional sessions
        original_count = class_header.class_sessions.count()

        created1, _sessions1 = class_header.ensure_sessions_exist()
        self.assertEqual(created1, 0)  # No new sessions created
        self.assertEqual(class_header.class_sessions.count(), original_count)

        created2, _sessions2 = class_header.ensure_sessions_exist()
        self.assertEqual(created2, 0)  # Still no new sessions
        self.assertEqual(class_header.class_sessions.count(), original_count)

    def test_grade_weight_validation_integrity(self):
        """Test grade weight validation maintains integrity."""
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        session = class_header.class_sessions.first()

        # Clear the auto-created part to test validation
        session.class_parts.all().delete()

        # Create parts with incorrect weights
        ClassPart.objects.create(class_session=session, class_part_code="A", grade_weight=Decimal("0.6"))
        ClassPart.objects.create(class_session=session, class_part_code="B", grade_weight=Decimal("0.3"))

        # Validation should warn about weight issues
        validation = session.validate_parts_structure()
        self.assertTrue(validation["valid"])  # Still valid but has warnings
        self.assertGreater(len(validation["warnings"]), 0)
        self.assertIn("total weight", validation["warnings"][0])

    def test_architectural_rule_enforcement(self):
        """Test that the core architectural rule is enforced: ALL parts go through sessions."""
        class_header = ClassHeader.objects.create(course=self.regular_course, term=self.term, section_id="A")

        session = class_header.class_sessions.first()

        # This should work - part through session
        part = ClassPart.objects.create(class_session=session, class_part_code="A")

        # Verify the relationship chain
        self.assertEqual(part.class_session, session)
        self.assertEqual(part.class_header, class_header)
        self.assertEqual(session.class_header, class_header)

        # Verify there's no way to create orphaned parts
        # (ClassPart model requires class_session, so this is enforced at DB level)
        with pytest.raises(IntegrityError):
            ClassPart.objects.create(
                class_session=None,  # This should fail
                class_part_code="B",
            )


class SchedulingIntegrationTest(TestCase):
    """Test integration between scheduling models."""

    def setUp(self):
        """Set up test data for integration tests."""
        # Create user for enrolled_by fields
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create term
        self.term = Term.objects.create(
            code="2025F",
            start_date="2025-09-01",
            end_date="2025-12-15",
        )

        # Create subject and course
        self.division = Division.objects.create(
            name="General English as Second Language",
            short_name="GESL",
        )

        self.cycle = Cycle.objects.create(
            name="Language Program Cycle",
            division=self.division,
        )

        self.course = Course.objects.create(
            code="GESL-01",
            title="General English Level 1",
            short_title="GESL Level 1",
            cycle=self.cycle,
            credits=3,
        )

        # Create facilities
        self.room = Room.objects.create(
            building="MAIN",
            name="Classroom 101",
        )

        # Create person and profiles
        self.person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth="1980-01-01",
        )

        self.teacher = TeacherProfile.objects.create(
            person=self.person,
        )

    def test_complete_class_creation_workflow_with_integrity(self):
        """Test complete workflow of creating a class with integrity enforcement."""
        # 1. Create class header - signals should auto-create structure
        class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            time_of_day=ClassHeader.TimeOfDay.MORNING,
            class_type=ClassHeader.ClassType.STANDARD,
            max_enrollment=20,
        )

        # 2. Verify structure was auto-created by signals
        self.assertEqual(class_header.class_sessions.count(), 1)
        session = class_header.class_sessions.first()
        self.assertEqual(session.class_parts.count(), 1)  # Default part created

        # 3. Replace default part with custom parts
        session.class_parts.all().delete()

        grammar_part = ClassPart.objects.create(
            class_session=session,
            class_part_type=ClassPartType.GRAMMAR,
            class_part_code="G",
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:00",
            teacher=self.teacher,
            room=self.room,
            grade_weight=Decimal("0.400"),
        )

        conversation_part = ClassPart.objects.create(
            class_session=session,
            class_part_type=ClassPartType.CONVERSATION,
            class_part_code="C",
            meeting_days="TUE,THU",
            start_time="10:00",
            end_time="11:00",
            teacher=self.teacher,
            room=self.room,
            grade_weight=Decimal("0.600"),
        )

        # 4. Verify relationships and integrity
        assert session.class_parts.count() == EXPECTED_CLASS_PARTS_COUNT
        assert grammar_part in session.class_parts.all()
        assert conversation_part in session.class_parts.all()

        # 5. Verify total grade weight
        total_weight = sum(part.grade_weight for part in session.class_parts.all())
        assert total_weight == Decimal("1.000")

        # 6. Test integrity validation
        header_validation = class_header.validate_session_structure()
        self.assertTrue(header_validation["valid"])

        session_validation = session.validate_parts_structure()
        self.assertTrue(session_validation["valid"])

    def test_room_assignment_integration(self):
        """Test simple room assignment with class parts."""
        # Create class using the room
        class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
        )

        # Create session for this class
        session = ClassSession.objects.create(
            class_header=class_header,
            session_number=1,
        )

        class_part = ClassPart.objects.create(
            class_session=session,
            meeting_days="MON",
            start_time="09:30",
            end_time="10:30",
            room=self.room,
        )

        # Verify room assignment
        assert class_part.room == self.room
        assert self.room.class_parts.first() == class_part

    def test_combined_class_group_workflow(self):
        """Test combined class group functionality."""
        # Create combined class group
        group = CombinedClassGroup.objects.create(
            name="ESL Combined Sections",
            term=self.term,
            description="Combined sections for scheduling efficiency",
        )

        # Create multiple class headers in the group
        class_a = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            combined_class_group=group,
        )

        class_b = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="B",
            combined_class_group=group,
        )

        # Verify group relationships
        assert group.member_class_headers.count() == EXPECTED_MEMBER_CLASS_HEADERS_COUNT
        assert group.member_count == EXPECTED_MEMBER_COUNT
        assert class_a in group.member_class_headers.all()
        assert class_b in group.member_class_headers.all()
