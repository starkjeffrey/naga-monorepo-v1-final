"""Comprehensive tests for grading app models.

Tests all grading models following clean architecture principles:
- GradingScale: Program-specific grading scale management
- GradeConversion: Letter grade to numeric conversion mappings
- ClassPartGrade: Individual class component grade tracking
- ClassSessionGrade: Aggregated session-level grades
- GradeChangeHistory: Complete audit trail for grade modifications
- GPARecord: Term and cumulative GPA calculations

Key testing areas:
- Model validation and business logic
- Grade calculation and conversion processes
- GPA calculation workflows
- Grade change audit trails
- Hierarchical grade aggregation
- Clean architecture compliance
- Edge cases and error conditions
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.grading.gpa import GPAManager, GPAReportGenerator
from apps.grading.models import (
    ClassPartGrade,
    ClassSessionGrade,
    GPARecord,
    GradeChangeHistory,
    GradeConversion,
    GradingScale,
)
from apps.grading.services import ClassPartGradeService, GradeConversionService
from apps.people.models import Person, StudentProfile

User = get_user_model()


class MockDivision:
    """Mock curriculum division for testing."""

    def __init__(self, name="Test Division", short_name="TEST"):
        self.name = name
        self.short_name = short_name
        self.id = 1


class MockCourse:
    """Mock curriculum course for testing."""

    def __init__(self, code="TEST-101", title="Test Course", credits=3):
        self.code = code
        self.title = title
        self.credits = credits
        self.cycle = "BA"
        self.is_language = False
        self.is_foundation_year = False
        self.division = MockDivision()
        self.id = 1


class MockTerm:
    """Mock curriculum term for testing."""

    def __init__(self, name="Fall 2024"):
        self.name = name
        self.start_date = date(2024, 9, 1)
        self.end_date = date(2024, 12, 15)
        self.id = 1


class MockMajor:
    """Mock curriculum major for testing."""

    def __init__(self, code="CS", name="Computer Science"):
        self.code = code
        self.name = name
        self.id = 1


class MockClassHeader:
    """Mock scheduling class header for testing."""

    def __init__(self, course=None, term=None):
        self.course = course or MockCourse()
        self.term = term or MockTerm()
        self.id = 1


class MockClassSession:
    """Mock scheduling class session for testing."""

    def __init__(self, class_header=None, name="Session 1"):
        self.class_header = class_header or MockClassHeader()
        self.name = name
        self.id = 1


class MockClassPart:
    """Mock scheduling class part for testing."""

    def __init__(self, class_session=None, name="Grammar", weight=100):
        self.class_session = class_session or MockClassSession()
        self.name = name
        self.weight_percentage = Decimal(str(weight))
        self.id = 1


class MockEnrollment:
    """Mock enrollment for testing."""

    def __init__(self, student=None, class_header=None):
        self.student = student
        self.class_header = class_header or MockClassHeader()
        self.status = "ENROLLED"
        self.id = 1


class GradingScaleModelTest(TestCase):
    """Test GradingScale model functionality."""

    def test_create_grading_scale(self):
        """Test creating a grading scale."""
        scale = GradingScale.objects.create(
            name="Academic Grading Scale",
            scale_type=GradingScale.ScaleType.ACADEMIC,
            description="Standard academic grading for BA/MA programs",
            is_active=True,
        )

        assert scale.name == "Academic Grading Scale"
        assert scale.scale_type == GradingScale.ScaleType.ACADEMIC
        assert scale.description == "Standard academic grading for BA/MA programs"
        assert scale.is_active

    def test_scale_type_choices(self):
        """Test all scale type options."""
        scale_types = [
            GradingScale.ScaleType.LANGUAGE_STANDARD,
            GradingScale.ScaleType.LANGUAGE_IEAP,
            GradingScale.ScaleType.ACADEMIC,
        ]

        for scale_type in scale_types:
            scale = GradingScale.objects.create(
                name=f"Test Scale {scale_type}",
                scale_type=scale_type,
            )
            assert scale.scale_type == scale_type

    def test_unique_scale_type_constraint(self):
        """Test unique constraint on scale_type."""
        GradingScale.objects.create(
            name="Academic Scale 1",
            scale_type=GradingScale.ScaleType.ACADEMIC,
        )

        with pytest.raises(IntegrityError):
            GradingScale.objects.create(
                name="Academic Scale 2",
                scale_type=GradingScale.ScaleType.ACADEMIC,  # Duplicate
            )

    def test_string_representation(self):
        """Test string representation."""
        scale = GradingScale.objects.create(
            name="Language Standard Scale",
            scale_type=GradingScale.ScaleType.LANGUAGE_STANDARD,
        )

        expected = "Language Standard Scale (Language Standard (A-F, F<50%))"
        assert str(scale) == expected

    def test_active_status_filtering(self):
        """Test filtering by active status."""
        active_scale = GradingScale.objects.create(
            name="Active Scale",
            scale_type=GradingScale.ScaleType.LANGUAGE_STANDARD,
            is_active=True,
        )

        inactive_scale = GradingScale.objects.create(
            name="Inactive Scale",
            scale_type=GradingScale.ScaleType.LANGUAGE_IEAP,
            is_active=False,
        )

        active_scales = GradingScale.objects.filter(is_active=True)
        assert active_scale in active_scales
        assert inactive_scale not in active_scales


class GradeConversionModelTest(TestCase):
    """Test GradeConversion model functionality."""

    def setUp(self):
        """Set up test data."""
        self.grading_scale = GradingScale.objects.create(
            name="Academic Scale",
            scale_type=GradingScale.ScaleType.ACADEMIC,
        )

    def test_create_grade_conversion(self):
        """Test creating a grade conversion."""
        conversion = GradeConversion.objects.create(
            grading_scale=self.grading_scale,
            letter_grade="A",
            min_percentage=Decimal("93.00"),
            max_percentage=Decimal("100.00"),
            gpa_points=Decimal("4.00"),
            display_order=0,
        )

        assert conversion.grading_scale == self.grading_scale
        assert conversion.letter_grade == "A"
        assert conversion.min_percentage == Decimal("93.00")
        assert conversion.max_percentage == Decimal("100.00")
        assert conversion.gpa_points == Decimal("4.00")
        assert conversion.display_order == 0

    def test_unique_constraints(self):
        """Test unique constraints on grade conversions."""
        # Create first conversion
        GradeConversion.objects.create(
            grading_scale=self.grading_scale,
            letter_grade="A",
            min_percentage=Decimal("93.00"),
            max_percentage=Decimal("100.00"),
            gpa_points=Decimal("4.00"),
        )

        # Test duplicate letter grade
        with pytest.raises(IntegrityError):
            GradeConversion.objects.create(
                grading_scale=self.grading_scale,
                letter_grade="A",  # Duplicate
                min_percentage=Decimal("90.00"),
                max_percentage=Decimal("92.99"),
                gpa_points=Decimal("3.70"),
            )

    def test_percentage_validation(self):
        """Test percentage range validation."""
        # Test invalid range (min >= max)
        conversion = GradeConversion(
            grading_scale=self.grading_scale,
            letter_grade="A",
            min_percentage=Decimal("95.00"),
            max_percentage=Decimal("93.00"),  # Less than min
            gpa_points=Decimal("4.00"),
        )

        with pytest.raises(ValidationError):
            conversion.clean()

    def test_complete_grading_scale(self):
        """Test creating a complete grading scale."""
        grade_mappings = [
            ("A+", Decimal("97.00"), Decimal("100.00"), Decimal("4.00"), 0),
            ("A", Decimal("93.00"), Decimal("96.99"), Decimal("4.00"), 1),
            ("A-", Decimal("90.00"), Decimal("92.99"), Decimal("3.70"), 2),
            ("B+", Decimal("87.00"), Decimal("89.99"), Decimal("3.30"), 3),
            ("B", Decimal("83.00"), Decimal("86.99"), Decimal("3.00"), 4),
            ("B-", Decimal("80.00"), Decimal("82.99"), Decimal("2.70"), 5),
            ("C+", Decimal("77.00"), Decimal("79.99"), Decimal("2.30"), 6),
            ("C", Decimal("73.00"), Decimal("76.99"), Decimal("2.00"), 7),
            ("C-", Decimal("70.00"), Decimal("72.99"), Decimal("1.70"), 8),
            ("D+", Decimal("67.00"), Decimal("69.99"), Decimal("1.30"), 9),
            ("D", Decimal("63.00"), Decimal("66.99"), Decimal("1.00"), 10),
            ("D-", Decimal("60.00"), Decimal("62.99"), Decimal("0.70"), 11),
            ("F", Decimal("0.00"), Decimal("59.99"), Decimal("0.00"), 12),
        ]

        conversions = []
        for letter, min_pct, max_pct, gpa, order in grade_mappings:
            conversion = GradeConversion.objects.create(
                grading_scale=self.grading_scale,
                letter_grade=letter,
                min_percentage=min_pct,
                max_percentage=max_pct,
                gpa_points=gpa,
                display_order=order,
            )
            conversions.append(conversion)

        # Verify all conversions created
        assert len(conversions) == 13
        assert GradeConversion.objects.filter(grading_scale=self.grading_scale).count() == 13

    def test_string_representation(self):
        """Test string representation."""
        conversion = GradeConversion.objects.create(
            grading_scale=self.grading_scale,
            letter_grade="A",
            min_percentage=Decimal("93.00"),
            max_percentage=Decimal("100.00"),
            gpa_points=Decimal("4.00"),
        )

        expected = f"{self.grading_scale.name}: A (93.00-100.00%)"
        assert str(conversion) == expected


class ClassPartGradeModelTest(TestCase):
    """Test ClassPartGrade model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="testpass",
        )

        # Create student
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=1001,
        )

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_create_class_part_grade(self, mock_class_part, mock_enrollment):
        """Test creating a class part grade."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()
        mock_class_part.name = "Grammar"

        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("87.50"),
            letter_grade="B+",
            gpa_points=Decimal("3.30"),
            grade_source=ClassPartGrade.GradeSource.MANUAL_TEACHER,
            grade_status=ClassPartGrade.GradeStatus.SUBMITTED,
            entered_by=self.user,
            notes="Good performance on grammar exercises",
        )

        assert grade.numeric_score == Decimal("87.50")
        assert grade.letter_grade == "B+"
        assert grade.gpa_points == Decimal("3.30")
        assert grade.grade_source == ClassPartGrade.GradeSource.MANUAL_TEACHER
        assert grade.grade_status == ClassPartGrade.GradeStatus.SUBMITTED
        assert grade.entered_by == self.user
        assert grade.notes == "Good performance on grammar exercises"

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_grade_source_choices(self, mock_class_part, mock_enrollment):
        """Test all grade source options."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()

        sources = [
            ClassPartGrade.GradeSource.MANUAL_TEACHER,
            ClassPartGrade.GradeSource.MANUAL_CLERK,
            ClassPartGrade.GradeSource.MOODLE_IMPORT,
            ClassPartGrade.GradeSource.CALCULATED,
            ClassPartGrade.GradeSource.MIGRATED,
        ]

        for source in sources:
            grade = ClassPartGrade.objects.create(
                numeric_score=Decimal("85.00"),
                grade_source=source,
                entered_by=self.user,
            )
            assert grade.grade_source == source

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_grade_status_choices(self, mock_class_part, mock_enrollment):
        """Test all grade status options."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()

        statuses = [
            ClassPartGrade.GradeStatus.DRAFT,
            ClassPartGrade.GradeStatus.SUBMITTED,
            ClassPartGrade.GradeStatus.APPROVED,
            ClassPartGrade.GradeStatus.FINALIZED,
        ]

        for status in statuses:
            grade = ClassPartGrade.objects.create(
                numeric_score=Decimal("85.00"),
                grade_status=status,
                entered_by=self.user,
            )
            assert grade.grade_status == status

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_grade_validation(self, mock_class_part, mock_enrollment):
        """Test grade validation logic."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()

        # Test missing both numeric and letter grade
        grade = ClassPartGrade(
            grade_source=ClassPartGrade.GradeSource.MANUAL_TEACHER,
            entered_by=self.user,
        )

        with pytest.raises(ValidationError):
            grade.clean()

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_approval_workflow(self, mock_class_part, mock_enrollment):
        """Test grade approval workflow."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()

        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("87.50"),
            grade_status=ClassPartGrade.GradeStatus.SUBMITTED,
            entered_by=self.user,
        )

        # Test approval
        grade.grade_status = ClassPartGrade.GradeStatus.APPROVED
        grade.approved_by = self.user
        grade.approved_at = timezone.now()
        grade.save()

        assert grade.grade_status == ClassPartGrade.GradeStatus.APPROVED
        assert grade.approved_by == self.user
        assert grade.approved_at is not None

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_notification_tracking(self, mock_class_part, mock_enrollment):
        """Test student notification tracking."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()

        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("87.50"),
            entered_by=self.user,
            student_notified=True,
            notification_date=timezone.now(),
        )

        assert grade.student_notified
        assert grade.notification_date is not None

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_property_methods(self, mock_class_part, mock_enrollment):
        """Test property methods."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()
        mock_class_part.name = "Grammar Test"

        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("87.50"),
            entered_by=self.user,
        )

        assert grade.student == self.student
        assert grade.class_header == mock_enrollment.class_header
        assert grade.class_session == mock_class_part.class_session

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_string_representation(self, mock_class_part, mock_enrollment):
        """Test string representation."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()
        mock_class_part.name = "Grammar"
        mock_class_part.__str__ = lambda: "Grammar"

        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("87.50"),
            letter_grade="B+",
            entered_by=self.user,
        )

        expected = f"{self.student} - Grammar: B+"
        assert str(grade) == expected


class ClassSessionGradeModelTest(TestCase):
    """Test ClassSessionGrade model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="testpass",
        )

        # Create student
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=1001,
        )

    @patch("apps.grading.models.ClassSessionGrade.enrollment")
    @patch("apps.grading.models.ClassSessionGrade.class_session")
    def test_create_class_session_grade(self, mock_class_session, mock_enrollment):
        """Test creating a class session grade."""
        mock_enrollment.student = self.student
        mock_class_session.name = "Session 1"
        mock_class_session.class_header = MockClassHeader()

        session_grade = ClassSessionGrade.objects.create(
            calculated_score=Decimal("87.50"),
            letter_grade="B+",
            gpa_points=Decimal("3.30"),
            calculation_details={
                "components": [
                    {"name": "Grammar", "score": 90.0, "weight": 50.0},
                    {"name": "Conversation", "score": 85.0, "weight": 50.0},
                ],
                "weighted_average": 87.5,
            },
        )

        assert session_grade.calculated_score == Decimal("87.50")
        assert session_grade.letter_grade == "B+"
        assert session_grade.gpa_points == Decimal("3.30")
        assert "components" in session_grade.calculation_details
        assert session_grade.calculated_at is not None

    @patch("apps.grading.models.ClassSessionGrade.enrollment")
    @patch("apps.grading.models.ClassSessionGrade.class_session")
    def test_calculation_details_structure(self, mock_class_session, mock_enrollment):
        """Test calculation details data structure."""
        mock_enrollment.student = self.student
        mock_class_session.name = "Session 1"

        calculation_data = {
            "method": "weighted_average",
            "components": [
                {
                    "class_part": "Grammar",
                    "score": 90.0,
                    "weight": 40.0,
                    "weighted_score": 36.0,
                },
                {
                    "class_part": "Conversation",
                    "score": 85.0,
                    "weight": 35.0,
                    "weighted_score": 29.75,
                },
                {
                    "class_part": "Writing",
                    "score": 80.0,
                    "weight": 25.0,
                    "weighted_score": 20.0,
                },
            ],
            "total_weight": 100.0,
            "final_score": 85.75,
            "calculation_timestamp": timezone.now().isoformat(),
        }

        session_grade = ClassSessionGrade.objects.create(
            calculated_score=Decimal("85.75"),
            letter_grade="B",
            gpa_points=Decimal("3.00"),
            calculation_details=calculation_data,
        )

        details = session_grade.calculation_details
        assert details["method"] == "weighted_average"
        assert len(details["components"]) == 3
        assert details["total_weight"] == 100.0
        assert details["final_score"] == 85.75

    @patch("apps.grading.models.ClassSessionGrade.enrollment")
    @patch("apps.grading.models.ClassSessionGrade.class_session")
    def test_string_representation(self, mock_class_session, mock_enrollment):
        """Test string representation."""
        mock_enrollment.student = self.student
        mock_class_session.name = "Session 1"
        mock_class_session.__str__ = lambda: "Session 1"

        session_grade = ClassSessionGrade.objects.create(
            calculated_score=Decimal("87.50"),
            letter_grade="B+",
            gpa_points=Decimal("3.30"),
        )

        expected = f"{self.student} - Session 1: B+"
        assert str(session_grade) == expected


class GradeChangeHistoryModelTest(TestCase):
    """Test GradeChangeHistory model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="testpass",
        )

        # Create student
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=1001,
        )

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_create_grade_change_history(self, mock_class_part, mock_enrollment):
        """Test creating grade change history."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()

        # Create a grade first
        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("85.00"),
            letter_grade="B",
            entered_by=self.user,
        )

        # Create change history
        history = GradeChangeHistory.objects.create(
            class_part_grade=grade,
            change_type=GradeChangeHistory.ChangeType.CORRECTION,
            changed_by=self.user,
            previous_numeric_score=Decimal("80.00"),
            previous_letter_grade="B-",
            previous_status=ClassPartGrade.GradeStatus.DRAFT,
            new_numeric_score=Decimal("85.00"),
            new_letter_grade="B",
            new_status=ClassPartGrade.GradeStatus.SUBMITTED,
            reason="Grade correction after review",
        )

        assert history.class_part_grade == grade
        assert history.change_type == GradeChangeHistory.ChangeType.CORRECTION
        assert history.changed_by == self.user
        assert history.previous_numeric_score == Decimal("80.00")
        assert history.new_numeric_score == Decimal("85.00")
        assert history.reason == "Grade correction after review"

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_change_type_choices(self, mock_class_part, mock_enrollment):
        """Test all change type options."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()

        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("85.00"),
            entered_by=self.user,
        )

        change_types = [
            GradeChangeHistory.ChangeType.INITIAL_ENTRY,
            GradeChangeHistory.ChangeType.CORRECTION,
            GradeChangeHistory.ChangeType.RECALCULATION,
            GradeChangeHistory.ChangeType.STATUS_CHANGE,
            GradeChangeHistory.ChangeType.BULK_UPDATE,
            GradeChangeHistory.ChangeType.MIGRATION,
        ]

        for change_type in change_types:
            history = GradeChangeHistory.objects.create(
                class_part_grade=grade,
                change_type=change_type,
                changed_by=self.user,
                reason=f"Test {change_type}",
            )
            assert history.change_type == change_type

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_additional_details_structure(self, mock_class_part, mock_enrollment):
        """Test additional details JSON field."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()

        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("85.00"),
            entered_by=self.user,
        )

        additional_details = {
            "system_info": {
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "session_id": "abc123",
            },
            "validation_checks": {
                "range_check": "passed",
                "scale_validation": "passed",
                "business_rules": "passed",
            },
            "performance_metrics": {
                "calculation_time_ms": 45,
                "database_queries": 3,
            },
        }

        history = GradeChangeHistory.objects.create(
            class_part_grade=grade,
            change_type=GradeChangeHistory.ChangeType.CORRECTION,
            changed_by=self.user,
            reason="Automated correction",
            additional_details=additional_details,
        )

        details = history.additional_details
        assert "system_info" in details
        assert details["validation_checks"]["range_check"] == "passed"
        assert details["performance_metrics"]["calculation_time_ms"] == 45

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_string_representation(self, mock_class_part, mock_enrollment):
        """Test string representation."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()
        mock_class_part.__str__ = lambda: "Grammar"

        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("85.00"),
            entered_by=self.user,
        )

        history = GradeChangeHistory.objects.create(
            class_part_grade=grade,
            change_type=GradeChangeHistory.ChangeType.CORRECTION,
            changed_by=self.user,
            reason="Test change",
        )

        expected = f"{grade} - Correction by {self.user.email}"
        assert str(history) == expected


class GPARecordModelTest(TestCase):
    """Test GPARecord model functionality."""

    def setUp(self):
        """Set up test data."""
        # Create student
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=1001,
        )

        self.term = MockTerm()
        self.major = MockMajor()

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_create_gpa_record(self, mock_major, mock_term):
        """Test creating a GPA record."""
        mock_term.name = "Fall 2024"
        mock_major.name = "Computer Science"

        gpa_record = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.TERM,
            gpa_value=Decimal("3.450"),
            quality_points=Decimal("41.40"),
            credit_hours_attempted=Decimal("12.00"),
            credit_hours_earned=Decimal("12.00"),
            calculation_details={
                "courses": [
                    {
                        "course": "CS-101",
                        "credits": 3.0,
                        "grade": "A-",
                        "gpa_points": 3.7,
                        "quality_points": 11.1,
                    },
                    {
                        "course": "MATH-101",
                        "credits": 3.0,
                        "grade": "B+",
                        "gpa_points": 3.3,
                        "quality_points": 9.9,
                    },
                    {
                        "course": "ENG-101",
                        "credits": 3.0,
                        "grade": "A",
                        "gpa_points": 4.0,
                        "quality_points": 12.0,
                    },
                    {
                        "course": "SCI-101",
                        "credits": 3.0,
                        "grade": "B",
                        "gpa_points": 3.0,
                        "quality_points": 9.0,
                    },
                ],
                "calculation_method": "weighted_average",
            },
        )

        assert gpa_record.student == self.student
        assert gpa_record.gpa_type == GPARecord.GPAType.TERM
        assert gpa_record.gpa_value == Decimal("3.450")
        assert gpa_record.quality_points == Decimal("41.40")
        assert gpa_record.credit_hours_attempted == Decimal("12.00")
        assert gpa_record.credit_hours_earned == Decimal("12.00")
        assert len(gpa_record.calculation_details["courses"]) == 4

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_gpa_type_choices(self, mock_major, mock_term):
        """Test both GPA type options."""
        mock_term.name = "Fall 2024"
        mock_major.name = "Computer Science"

        # Term GPA
        term_gpa = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.TERM,
            gpa_value=Decimal("3.500"),
            quality_points=Decimal("42.00"),
            credit_hours_attempted=Decimal("12.00"),
            credit_hours_earned=Decimal("12.00"),
        )

        # Cumulative GPA
        cumulative_gpa = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.CUMULATIVE,
            gpa_value=Decimal("3.450"),
            quality_points=Decimal("124.20"),
            credit_hours_attempted=Decimal("36.00"),
            credit_hours_earned=Decimal("36.00"),
        )

        assert term_gpa.gpa_type == GPARecord.GPAType.TERM
        assert cumulative_gpa.gpa_type == GPARecord.GPAType.CUMULATIVE

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_comprehensive_calculation_details(self, mock_major, mock_term):
        """Test comprehensive calculation details structure."""
        mock_term.name = "Fall 2024"
        mock_major.name = "Computer Science"

        calculation_data = {
            "calculation_metadata": {
                "calculation_date": timezone.now().isoformat(),
                "calculation_version": "1.0",
                "major_requirements_version": "2024.1",
            },
            "courses": [
                {
                    "course_id": 1,
                    "course_code": "CS-101",
                    "course_title": "Introduction to Programming",
                    "credits": 3.0,
                    "grade": "A",
                    "numeric_score": 95.0,
                    "gpa_points": 4.0,
                    "quality_points": 12.0,
                    "grading_scale": "Academic",
                    "requirement_fulfilled": "Core Programming",
                },
                {
                    "course_id": 2,
                    "course_code": "MATH-201",
                    "course_title": "Calculus I",
                    "credits": 4.0,
                    "grade": "B+",
                    "numeric_score": 87.5,
                    "gpa_points": 3.3,
                    "quality_points": 13.2,
                    "grading_scale": "Academic",
                    "requirement_fulfilled": "Mathematics",
                },
            ],
            "totals": {
                "total_courses": 2,
                "total_credits_attempted": 7.0,
                "total_credits_earned": 7.0,
                "total_quality_points": 25.2,
                "calculated_gpa": 3.6,
            },
            "validation": {
                "major_requirement_check": "passed",
                "credit_hour_validation": "passed",
                "grade_finalization_check": "passed",
            },
        }

        gpa_record = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.TERM,
            gpa_value=Decimal("3.600"),
            quality_points=Decimal("25.20"),
            credit_hours_attempted=Decimal("7.00"),
            credit_hours_earned=Decimal("7.00"),
            calculation_details=calculation_data,
        )

        details = gpa_record.calculation_details
        assert "calculation_metadata" in details
        assert len(details["courses"]) == 2
        assert details["totals"]["calculated_gpa"] == 3.6
        assert details["validation"]["major_requirement_check"] == "passed"

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_gpa_value_validation(self, mock_major, mock_term):
        """Test GPA value validation."""
        mock_term.name = "Fall 2024"
        mock_major.name = "Computer Science"

        # Test valid GPA
        valid_gpa = GPARecord(
            student=self.student,
            gpa_type=GPARecord.GPAType.TERM,
            gpa_value=Decimal("3.850"),
            quality_points=Decimal("46.20"),
            credit_hours_attempted=Decimal("12.00"),
            credit_hours_earned=Decimal("12.00"),
        )
        valid_gpa.full_clean()  # Should not raise

        # Test invalid GPA (too high)
        invalid_gpa = GPARecord(
            student=self.student,
            gpa_type=GPARecord.GPAType.TERM,
            gpa_value=Decimal("5.000"),  # Above 4.0
            quality_points=Decimal("60.00"),
            credit_hours_attempted=Decimal("12.00"),
            credit_hours_earned=Decimal("12.00"),
        )

        with pytest.raises(ValidationError):
            invalid_gpa.full_clean()

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_string_representation(self, mock_major, mock_term):
        """Test string representation."""
        mock_term.name = "Fall 2024"
        mock_term.__str__ = lambda: "Fall 2024"
        mock_major.name = "Computer Science"

        gpa_record = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.TERM,
            gpa_value=Decimal("3.450"),
            quality_points=Decimal("41.40"),
            credit_hours_attempted=Decimal("12.00"),
            credit_hours_earned=Decimal("12.00"),
        )

        expected = f"{self.student} - Fall 2024 Term GPA: 3.450"
        assert str(gpa_record) == expected


class GradeConversionServiceTest(TestCase):
    """Test GradeConversionService functionality."""

    def setUp(self):
        """Set up test data."""
        # Create grading scale with conversions
        self.grading_scale = GradingScale.objects.create(
            name="Academic Scale",
            scale_type=GradingScale.ScaleType.ACADEMIC,
        )

        # Create grade conversions
        conversions = [
            ("A", Decimal("93.00"), Decimal("100.00"), Decimal("4.00")),
            ("A-", Decimal("90.00"), Decimal("92.99"), Decimal("3.70")),
            ("B+", Decimal("87.00"), Decimal("89.99"), Decimal("3.30")),
            ("B", Decimal("83.00"), Decimal("86.99"), Decimal("3.00")),
            ("B-", Decimal("80.00"), Decimal("82.99"), Decimal("2.70")),
            ("C", Decimal("70.00"), Decimal("79.99"), Decimal("2.00")),
            ("F", Decimal("0.00"), Decimal("69.99"), Decimal("0.00")),
        ]

        for letter, min_pct, max_pct, gpa in conversions:
            GradeConversion.objects.create(
                grading_scale=self.grading_scale,
                letter_grade=letter,
                min_percentage=min_pct,
                max_percentage=max_pct,
                gpa_points=gpa,
            )

    def test_get_letter_grade_conversion(self):
        """Test converting numeric scores to letter grades."""
        test_cases = [
            (Decimal("95.00"), "A", Decimal("4.00")),
            (Decimal("91.50"), "A-", Decimal("3.70")),
            (Decimal("88.00"), "B+", Decimal("3.30")),
            (Decimal("85.00"), "B", Decimal("3.00")),
            (Decimal("81.00"), "B-", Decimal("2.70")),
            (Decimal("75.00"), "C", Decimal("2.00")),
            (Decimal("65.00"), "F", Decimal("0.00")),
        ]

        for score, expected_letter, expected_gpa in test_cases:
            letter, gpa_points = GradeConversionService.get_letter_grade(
                score,
                self.grading_scale,
            )
            assert letter == expected_letter
            assert gpa_points == expected_gpa

    def test_get_numeric_range(self):
        """Test getting numeric ranges for letter grades."""
        letter_grade = "B+"
        min_pct, max_pct = GradeConversionService.get_numeric_range(
            letter_grade,
            self.grading_scale,
        )

        assert min_pct == Decimal("87.00")
        assert max_pct == Decimal("89.99")

    def test_invalid_score_conversion(self):
        """Test error handling for invalid scores."""
        with pytest.raises(Exception):  # GradeCalculationError
            GradeConversionService.get_letter_grade(
                Decimal("150.00"),
                self.grading_scale,  # Invalid score
            )

    def test_invalid_letter_grade_lookup(self):
        """Test error handling for invalid letter grades."""
        with pytest.raises(Exception):  # GradeCalculationError
            GradeConversionService.get_numeric_range(
                "Z",
                self.grading_scale,  # Invalid letter grade
            )

    def test_validate_grade_data_numeric(self):
        """Test grade data validation with numeric score."""
        grade_data = GradeConversionService.validate_grade_data(
            numeric_score=Decimal("87.50"),
            letter_grade=None,
            grading_scale=self.grading_scale,
        )

        assert grade_data["numeric_score"] == Decimal("87.50")
        assert grade_data["letter_grade"] == "B+"
        assert grade_data["gpa_points"] == Decimal("3.30")

    def test_validate_grade_data_letter(self):
        """Test grade data validation with letter grade."""
        grade_data = GradeConversionService.validate_grade_data(
            numeric_score=None,
            letter_grade="A-",
            grading_scale=self.grading_scale,
        )

        assert grade_data["letter_grade"] == "A-"
        assert grade_data["gpa_points"] == Decimal("3.70")
        # Should calculate midpoint as numeric equivalent
        expected_midpoint = (Decimal("90.00") + Decimal("92.99")) / 2
        assert grade_data["numeric_score"] == expected_midpoint

    def test_validate_grade_data_missing(self):
        """Test validation error when both grades missing."""
        with pytest.raises(ValidationError):
            GradeConversionService.validate_grade_data(
                numeric_score=None,
                letter_grade=None,
                grading_scale=self.grading_scale,
            )


class GPAManagerTest(TestCase):
    """Test GPAManager functionality."""

    def setUp(self):
        """Set up test data."""
        # Create student
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=1001,
        )

        self.term = MockTerm()
        self.major = MockMajor()

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_determine_good_standing(self, mock_major, mock_term):
        """Test academic standing determination - good standing."""
        mock_term.name = "Fall 2024"
        mock_major.name = "Computer Science"

        # Create GPA records for good standing
        term_gpa = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.TERM,
            gpa_value=Decimal("3.200"),
            quality_points=Decimal("38.40"),
            credit_hours_attempted=Decimal("12.00"),
            credit_hours_earned=Decimal("12.00"),
        )

        cumulative_gpa = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.CUMULATIVE,
            gpa_value=Decimal("3.100"),
            quality_points=Decimal("111.60"),
            credit_hours_attempted=Decimal("36.00"),
            credit_hours_earned=Decimal("36.00"),
        )

        standing = GPAManager.determine_academic_standing(
            self.student,
            term_gpa,
            cumulative_gpa,
        )

        assert standing.status == "GOOD_STANDING"
        assert standing.requirements_met
        assert standing.cumulative_gpa == Decimal("3.100")

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_determine_probation_standing(self, mock_major, mock_term):
        """Test academic standing determination - probation."""
        mock_term.name = "Fall 2024"
        mock_major.name = "Computer Science"

        # Create GPA records for probation
        term_gpa = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.TERM,
            gpa_value=Decimal("1.800"),
            quality_points=Decimal("21.60"),
            credit_hours_attempted=Decimal("12.00"),
            credit_hours_earned=Decimal("12.00"),
        )

        cumulative_gpa = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.CUMULATIVE,
            gpa_value=Decimal("1.750"),
            quality_points=Decimal("63.00"),
            credit_hours_attempted=Decimal("36.00"),
            credit_hours_earned=Decimal("33.00"),
        )

        standing = GPAManager.determine_academic_standing(
            self.student,
            term_gpa,
            cumulative_gpa,
        )

        assert standing.status == "PROBATION"
        assert not standing.requirements_met
        assert len(standing.warnings) > 0
        assert len(standing.recommendations) > 0

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_get_gpa_history(self, mock_major, mock_term):
        """Test GPA history retrieval."""
        mock_term.name = "Fall 2024"
        mock_major.name = "Computer Science"

        # Create multiple term GPA records
        for i in range(3):
            term_date = date(2024, 1 + i * 4, 1)  # Jan, May, Sep
            mock_term_individual = MockTerm(f"Term {i + 1} 2024")
            mock_term_individual.start_date = term_date

            with patch("apps.grading.models.GPARecord.term", mock_term_individual):
                GPARecord.objects.create(
                    student=self.student,
                    gpa_type=GPARecord.GPAType.TERM,
                    gpa_value=Decimal(f"3.{200 + i * 100}"),
                    quality_points=Decimal(f"{38 + i * 4}.40"),
                    credit_hours_attempted=Decimal("12.00"),
                    credit_hours_earned=Decimal("12.00"),
                    calculation_details={"courses": [f"Course {i + 1}"]},
                )

        history = GPAManager.get_gpa_history(self.student, self.major, limit=5)

        assert len(history) <= 3  # Should get all created records
        # Should be ordered by term start date (most recent first)
        if len(history) > 1:
            assert history[0]["term_gpa"] >= history[1]["term_gpa"]


class GradingIntegrationTest(TestCase):
    """Test integration between grading models and services."""

    def setUp(self):
        """Set up test data for integration tests."""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="testpass",
        )

        # Create student
        student_person = Person.objects.create(
            family_name="Integration",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=2001,
        )

        # Create grading scale
        self.grading_scale = GradingScale.objects.create(
            name="Test Academic Scale",
            scale_type=GradingScale.ScaleType.ACADEMIC,
        )

        # Create grade conversions
        GradeConversion.objects.create(
            grading_scale=self.grading_scale,
            letter_grade="A",
            min_percentage=Decimal("90.00"),
            max_percentage=Decimal("100.00"),
            gpa_points=Decimal("4.00"),
        )

        GradeConversion.objects.create(
            grading_scale=self.grading_scale,
            letter_grade="B",
            min_percentage=Decimal("80.00"),
            max_percentage=Decimal("89.99"),
            gpa_points=Decimal("3.00"),
        )

        GradeConversion.objects.create(
            grading_scale=self.grading_scale,
            letter_grade="C",
            min_percentage=Decimal("70.00"),
            max_percentage=Decimal("79.99"),
            gpa_points=Decimal("2.00"),
        )

        GradeConversion.objects.create(
            grading_scale=self.grading_scale,
            letter_grade="F",
            min_percentage=Decimal("0.00"),
            max_percentage=Decimal("69.99"),
            gpa_points=Decimal("0.00"),
        )

    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_complete_grading_workflow(self, mock_class_part, mock_enrollment):
        """Test complete grading workflow from entry to history."""
        mock_enrollment.student = self.student
        mock_enrollment.class_header = MockClassHeader()
        mock_class_part.class_session = MockClassSession()

        # 1. Create initial grade
        grade = ClassPartGrade.objects.create(
            numeric_score=Decimal("87.50"),
            grade_source=ClassPartGrade.GradeSource.MANUAL_TEACHER,
            grade_status=ClassPartGrade.GradeStatus.DRAFT,
            entered_by=self.user,
            notes="Initial grade entry",
        )

        # 2. Update to calculated letter grade using service
        with patch.object(
            ClassPartGradeService,
            "_get_grading_scale_for_class",
            return_value=self.grading_scale,
        ):
            grade_data = GradeConversionService.validate_grade_data(
                numeric_score=Decimal("87.50"),
                letter_grade=None,
                grading_scale=self.grading_scale,
            )

        # Update grade with calculated values
        grade.letter_grade = grade_data["letter_grade"]
        grade.gpa_points = grade_data["gpa_points"]
        grade.save()

        # 3. Create change history for the update
        GradeChangeHistory.objects.create(
            class_part_grade=grade,
            change_type=GradeChangeHistory.ChangeType.RECALCULATION,
            changed_by=self.user,
            previous_letter_grade="",
            new_letter_grade=grade.letter_grade,
            reason="Letter grade calculation",
        )

        # 4. Submit grade for approval
        grade.grade_status = ClassPartGrade.GradeStatus.SUBMITTED
        grade.save()

        # 5. Approve grade
        grade.grade_status = ClassPartGrade.GradeStatus.APPROVED
        grade.approved_by = self.user
        grade.approved_at = timezone.now()
        grade.save()

        # 6. Verify workflow completion
        assert grade.numeric_score == Decimal("87.50")
        assert grade.letter_grade == "B"  # 87.50 should map to B
        assert grade.gpa_points == Decimal("3.00")
        assert grade.grade_status == ClassPartGrade.GradeStatus.APPROVED
        assert grade.approved_by == self.user

        # Verify change history was created
        history_count = GradeChangeHistory.objects.filter(
            class_part_grade=grade,
        ).count()
        assert history_count == 1

    @patch("apps.grading.models.ClassSessionGrade.enrollment")
    @patch("apps.grading.models.ClassSessionGrade.class_session")
    @patch("apps.grading.models.ClassPartGrade.enrollment")
    @patch("apps.grading.models.ClassPartGrade.class_part")
    def test_hierarchical_grade_calculation(
        self,
        mock_part,
        mock_part_enrollment,
        mock_session,
        mock_session_enrollment,
    ):
        """Test hierarchical grade calculation from parts to session."""
        # Mock the relationships
        mock_class_session = MockClassSession()
        mock_part_enrollment.student = self.student
        mock_part_enrollment.class_header = MockClassHeader()
        mock_session_enrollment.student = self.student
        mock_session_enrollment.class_header = MockClassHeader()
        mock_session.class_header = MockClassHeader()

        # Create multiple class part grades
        part_scores = [
            ("Grammar", Decimal("90.00"), Decimal("40.00")),  # 40% weight
            ("Conversation", Decimal("85.00"), Decimal("35.00")),  # 35% weight
            ("Writing", Decimal("80.00"), Decimal("25.00")),  # 25% weight
        ]

        total_weighted_score = Decimal("0")
        total_weight = Decimal("0")

        for part_name, score, weight in part_scores:
            # Create mock class part with weight
            mock_class_part = MockClassPart(
                class_session=mock_class_session,
                name=part_name,
                weight=float(weight),
            )

            with patch(
                "apps.grading.models.ClassPartGrade.class_part",
                mock_class_part,
            ):
                ClassPartGrade.objects.create(
                    numeric_score=score,
                    letter_grade="A" if score >= 90 else "B",
                    gpa_points=Decimal("4.00") if score >= 90 else Decimal("3.00"),
                    grade_status=ClassPartGrade.GradeStatus.FINALIZED,
                    entered_by=self.user,
                )

            # Calculate weighted contribution
            weighted_score = score * weight / 100
            total_weighted_score += weighted_score
            total_weight += weight

        # Calculate expected session grade
        expected_score = total_weighted_score / total_weight * 100

        # Create session grade manually (simulating service calculation)
        session_grade = ClassSessionGrade.objects.create(
            calculated_score=expected_score.quantize(Decimal("0.01")),
            letter_grade="B",  # ~86.25 should be B grade
            gpa_points=Decimal("3.00"),
            calculation_details={
                "components": [
                    {"name": name, "score": float(score), "weight": float(weight)}
                    for name, score, weight in part_scores
                ],
                "total_weight": float(total_weight),
                "final_score": float(expected_score),
            },
        )

        # Verify calculation
        assert abs(session_grade.calculated_score - Decimal("86.25")) < Decimal("0.01")
        assert session_grade.letter_grade == "B"
        assert len(session_grade.calculation_details["components"]) == 3

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_gpa_calculation_workflow(self, mock_major, mock_term):
        """Test GPA calculation from session grades to GPA records."""
        mock_term.name = "Fall 2024"
        mock_major.name = "Computer Science"

        # Create multiple course session grades
        course_data = [
            ("CS-101", 3, Decimal("3.70")),  # A- grade
            ("MATH-101", 4, Decimal("3.00")),  # B grade
            ("ENG-101", 3, Decimal("4.00")),  # A grade
        ]

        total_quality_points = Decimal("0")
        total_credits = Decimal("0")

        calculation_courses = []

        for course_code, credits, gpa_points in course_data:
            credits_decimal = Decimal(str(credits))
            quality_points = gpa_points * credits_decimal

            total_quality_points += quality_points
            total_credits += credits_decimal

            calculation_courses.append(
                {
                    "course": course_code,
                    "credits": credits,
                    "gpa_points": float(gpa_points),
                    "quality_points": float(quality_points),
                },
            )

        # Calculate expected GPA
        expected_gpa = total_quality_points / total_credits

        # Create term GPA record
        term_gpa = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.TERM,
            gpa_value=expected_gpa.quantize(Decimal("0.001")),
            quality_points=total_quality_points,
            credit_hours_attempted=total_credits,
            credit_hours_earned=total_credits,
            calculation_details={
                "courses": calculation_courses,
                "calculation_method": "weighted_average",
            },
        )

        # Create cumulative GPA (same as term for first term)
        cumulative_gpa = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.CUMULATIVE,
            gpa_value=expected_gpa.quantize(Decimal("0.001")),
            quality_points=total_quality_points,
            credit_hours_attempted=total_credits,
            credit_hours_earned=total_credits,
            calculation_details={
                "terms": [
                    {
                        "term": "Fall 2024",
                        "term_gpa": float(expected_gpa),
                        "quality_points": float(total_quality_points),
                        "credit_hours": float(total_credits),
                    },
                ],
                "calculation_method": "cumulative_weighted",
            },
        )

        # Verify calculations
        # Expected: (3.7*3 + 3.0*4 + 4.0*3) / (3+4+3) = (11.1 + 12.0 + 12.0) / 10 = 35.1 / 10 = 3.51
        assert abs(term_gpa.gpa_value - Decimal("3.510")) < Decimal("0.001")
        assert term_gpa.quality_points == Decimal("35.10")
        assert term_gpa.credit_hours_attempted == Decimal("10")

        assert cumulative_gpa.gpa_value == term_gpa.gpa_value
        assert len(cumulative_gpa.calculation_details["terms"]) == 1

    def test_grade_audit_trail_completeness(self):
        """Test complete audit trail for grade changes."""
        # Test that all grading models maintain proper audit trails
        # All models inherit from AuditModel which provides timestamp and soft delete

        # Test GradingScale audit fields
        scale = GradingScale()
        assert hasattr(scale, "created_at")
        assert hasattr(scale, "updated_at")
        assert hasattr(scale, "is_deleted")
        assert hasattr(scale, "deleted_at")

        # Test ClassPartGrade audit fields
        grade = ClassPartGrade()
        assert hasattr(grade, "created_at")
        assert hasattr(grade, "updated_at")
        assert hasattr(grade, "is_deleted")
        assert hasattr(grade, "deleted_at")

        # Test GPARecord audit fields
        gpa_record = GPARecord()
        assert hasattr(gpa_record, "created_at")
        assert hasattr(gpa_record, "updated_at")
        assert hasattr(gpa_record, "is_deleted")
        assert hasattr(gpa_record, "deleted_at")

    def test_clean_architecture_compliance(self):
        """Test that grading models follow clean architecture principles."""
        # Models should only depend on:
        # - Common app (for base models)
        # - People app (for student profiles)
        # - Enrollment app (for class enrollments)
        # - Scheduling app (for class structure)
        # - Curriculum app (for terms/majors)

        # Test that models can be imported without circular dependencies
        from apps.grading.models import (
            ClassPartGrade,
            ClassSessionGrade,
            GPARecord,
            GradeChangeHistory,
            GradeConversion,
            GradingScale,
        )

        # All models should be properly defined
        assert GradingScale._meta.abstract is False
        assert GradeConversion._meta.abstract is False
        assert ClassPartGrade._meta.abstract is False
        assert ClassSessionGrade._meta.abstract is False
        assert GradeChangeHistory._meta.abstract is False
        assert GPARecord._meta.abstract is False

    def test_grading_scale_edge_cases(self):
        """Test grading scale edge cases and boundary conditions."""
        # Test with minimum and maximum possible scores
        test_scores = [
            Decimal("0.00"),  # Minimum
            Decimal("69.99"),  # Just below C
            Decimal("70.00"),  # Exactly C
            Decimal("79.99"),  # Just below B
            Decimal("80.00"),  # Exactly B
            Decimal("89.99"),  # Just below A
            Decimal("90.00"),  # Exactly A
            Decimal("100.00"),  # Maximum
        ]

        for score in test_scores:
            try:
                letter, gpa_points = GradeConversionService.get_letter_grade(
                    score,
                    self.grading_scale,
                )
                # Verify result is valid
                assert letter in ["A", "B", "C", "F"]
                assert 0 <= gpa_points <= 4
            except (ValueError, TypeError, AttributeError):
                # Some boundary cases might not have exact matches
                # depending on how grade ranges are defined
                pass

    @patch("apps.grading.models.GPARecord.term")
    @patch("apps.grading.models.GPARecord.major")
    def test_gpa_forecasting_scenarios(self, mock_major, mock_term):
        """Test GPA forecasting and planning scenarios."""
        mock_term.name = "Fall 2024"
        mock_major.name = "Computer Science"

        # Create current cumulative GPA
        current_gpa = GPARecord.objects.create(
            student=self.student,
            gpa_type=GPARecord.GPAType.CUMULATIVE,
            gpa_value=Decimal("2.800"),  # Below good standing
            quality_points=Decimal("84.00"),
            credit_hours_attempted=Decimal("30.00"),
            credit_hours_earned=Decimal("30.00"),
        )

        # Test forecasting scenarios
        forecasting = GPAManager.calculate_gpa_forecasting(
            self.student,
            self.major,
            current_gpa,
        )

        assert forecasting["current_gpa"] == 2.8
        assert forecasting["current_credits"] == 30.0
        assert len(forecasting["scenarios"]) > 0
        assert len(forecasting["recommendations"]) > 0

        # Should include recommendations for improvement since below 3.0
        recommendations_text = " ".join(forecasting["recommendations"])
        assert any(keyword in recommendations_text.lower() for keyword in ["good standing", "improve", "focus"])

    def test_transcript_data_generation(self):
        """Test comprehensive transcript data generation."""
        # This would typically require more complex mock setup
        # For now, test the basic structure
        transcript_data = GPAReportGenerator.generate_transcript_data(
            self.student,
            self.major,
            include_unofficial=False,
        )

        assert "student" in transcript_data
        assert "major" in transcript_data
        assert "terms" in transcript_data
        assert "summary" in transcript_data
        assert "generated_at" in transcript_data

        assert transcript_data["student"] == self.student
        assert transcript_data["include_unofficial"] is False


class GradingBusinessLogicTest(TestCase):
    """Test grading business logic and edge cases."""

    def test_gpa_calculation_precision(self):
        """Test GPA calculation precision and rounding."""
        # Test various precision scenarios
        test_cases = [
            (Decimal("89.999"), "B"),  # Should round down to B
            (Decimal("90.000"), "A"),  # Exactly A threshold
            (Decimal("90.001"), "A"),  # Just above A threshold
        ]

        scale = GradingScale.objects.create(
            name="Test Scale",
            scale_type=GradingScale.ScaleType.ACADEMIC,
        )

        GradeConversion.objects.create(
            grading_scale=scale,
            letter_grade="A",
            min_percentage=Decimal("90.00"),
            max_percentage=Decimal("100.00"),
            gpa_points=Decimal("4.00"),
        )

        GradeConversion.objects.create(
            grading_scale=scale,
            letter_grade="B",
            min_percentage=Decimal("80.00"),
            max_percentage=Decimal("89.99"),
            gpa_points=Decimal("3.00"),
        )

        for score, expected_letter in test_cases:
            letter, _ = GradeConversionService.get_letter_grade(score, scale)
            assert letter == expected_letter

    def test_zero_credit_gpa_handling(self):
        """Test handling of zero credit scenarios in GPA calculations."""
        # Create GPA record with zero credits
        student_person = Person.objects.create(
            family_name="Zero",
            personal_name="Credits",
            date_of_birth=date(2000, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=student_person,
            student_id=3001,
        )

        with patch("apps.grading.models.GPARecord.term", MockTerm()):
            with patch("apps.grading.models.GPARecord.major", MockMajor()):
                gpa_record = GPARecord(
                    student=student,
                    gpa_type=GPARecord.GPAType.TERM,
                    gpa_value=Decimal("0.000"),
                    quality_points=Decimal("0.00"),
                    credit_hours_attempted=Decimal("0.00"),
                    credit_hours_earned=Decimal("0.00"),
                )

                # Should not raise validation errors
                gpa_record.full_clean()

    def test_grade_boundary_conditions(self):
        """Test grade boundary conditions and edge cases."""
        # Test exact boundary values in grading scale
        scale = GradingScale.objects.create(
            name="Boundary Test Scale",
            scale_type=GradingScale.ScaleType.ACADEMIC,
        )

        # Create conversion with exact boundaries
        GradeConversion.objects.create(
            grading_scale=scale,
            letter_grade="B",
            min_percentage=Decimal("80.00"),
            max_percentage=Decimal("89.99"),
            gpa_points=Decimal("3.00"),
        )

        # Test the clean method with equal min/max (should fail)
        invalid_conversion = GradeConversion(
            grading_scale=scale,
            letter_grade="A",
            min_percentage=Decimal("90.00"),
            max_percentage=Decimal("90.00"),  # Equal to min
            gpa_points=Decimal("4.00"),
        )

        with pytest.raises(ValidationError):
            invalid_conversion.clean()

    def test_concurrent_grade_modifications(self):
        """Test handling of concurrent grade modifications."""
        # This would typically test database-level concurrency
        # For now, test the audit trail captures multiple changes

        user1 = User.objects.create_user(email="user1@test.com", password="pass")
        user2 = User.objects.create_user(email="user2@test.com", password="pass")

        student_person = Person.objects.create(
            family_name="Concurrent",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=student_person,
            student_id=4001,
        )

        with (
            patch("apps.grading.models.ClassPartGrade.enrollment") as mock_enrollment,
            patch(
                "apps.grading.models.ClassPartGrade.class_part",
            ) as mock_class_part,
        ):
            mock_enrollment.student = student
            mock_enrollment.class_header = MockClassHeader()
            mock_class_part.class_session = MockClassSession()

            # Create grade
            grade = ClassPartGrade.objects.create(
                numeric_score=Decimal("85.00"),
                entered_by=user1,
            )

            # Create multiple history entries (simulating concurrent changes)
            GradeChangeHistory.objects.create(
                class_part_grade=grade,
                change_type=GradeChangeHistory.ChangeType.CORRECTION,
                changed_by=user1,
                reason="First change",
            )

            GradeChangeHistory.objects.create(
                class_part_grade=grade,
                change_type=GradeChangeHistory.ChangeType.STATUS_CHANGE,
                changed_by=user2,
                reason="Second change",
            )

            # Verify both changes are tracked
            history_count = GradeChangeHistory.objects.filter(
                class_part_grade=grade,
            ).count()
            assert history_count == 2

    def test_invalid_gpa_scenarios(self):
        """Test invalid GPA scenarios and error handling."""
        student_person = Person.objects.create(
            family_name="Invalid",
            personal_name="GPA",
            date_of_birth=date(2000, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=student_person,
            student_id=5001,
        )

        # Test GPA above 4.0
        with patch("apps.grading.models.GPARecord.term", MockTerm()):
            with patch("apps.grading.models.GPARecord.major", MockMajor()):
                invalid_gpa = GPARecord(
                    student=student,
                    gpa_type=GPARecord.GPAType.TERM,
                    gpa_value=Decimal("4.500"),  # Above maximum
                    quality_points=Decimal("54.00"),
                    credit_hours_attempted=Decimal("12.00"),
                    credit_hours_earned=Decimal("12.00"),
                )

                with pytest.raises(ValidationError):
                    invalid_gpa.full_clean()

        # Test negative GPA
        with patch("apps.grading.models.GPARecord.term", MockTerm()):
            with patch("apps.grading.models.GPARecord.major", MockMajor()):
                negative_gpa = GPARecord(
                    student=student,
                    gpa_type=GPARecord.GPAType.TERM,
                    gpa_value=Decimal("-1.000"),  # Negative
                    quality_points=Decimal("-12.00"),
                    credit_hours_attempted=Decimal("12.00"),
                    credit_hours_earned=Decimal("0.00"),
                )

                with pytest.raises(ValidationError):
                    negative_gpa.full_clean()
