"""Unit tests for Grading app models.

This module tests the critical business logic of grading models including:
- Multiple grading scales (Language Standard, IEAP, Academic)
- Grade conversion mappings and GPA calculations
- ClassPartGrade with grade validation and status management
- Grade change history and audit trail
- Academic standing determination logic
- Grade entry workflow and permissions

Focus on testing the "why" - the actual grading rules and GPA calculations.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.grading.models import (
    ClassPartGrade,
    GradeConversion,
    GradingScale,
)

# Get user model for testing
User = get_user_model()


@pytest.fixture
def admin_user():
    """Create admin user for tests."""
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="testpass123",
    )


@pytest.fixture
def teacher_user():
    """Create teacher user for tests."""
    return User.objects.create_user(
        username="teacher",
        email="teacher@example.com",
        password="testpass123",
    )


@pytest.fixture
def language_standard_scale(admin_user):
    """Create Language Standard grading scale."""
    return GradingScale.objects.create(
        name="Language Standard Scale",
        scale_type=GradingScale.ScaleType.LANGUAGE_STANDARD,
        description="A-F scale with F<50%",
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def language_ieap_scale(admin_user):
    """Create Language IEAP grading scale."""
    return GradingScale.objects.create(
        name="Language IEAP Scale",
        scale_type=GradingScale.ScaleType.LANGUAGE_IEAP,
        description="A-F scale with F<60%",
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def academic_scale(admin_user):
    """Create Academic grading scale."""
    return GradingScale.objects.create(
        name="Academic Scale",
        scale_type=GradingScale.ScaleType.ACADEMIC,
        description="A+ to F scale with F<60%",
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def language_standard_conversions(language_standard_scale, admin_user):
    """Create grade conversions for Language Standard scale."""
    conversions = [
        ("A", Decimal("80.00"), Decimal("100.00"), Decimal("4.00")),
        ("B", Decimal("70.00"), Decimal("79.99"), Decimal("3.00")),
        ("C", Decimal("60.00"), Decimal("69.99"), Decimal("2.00")),
        ("D", Decimal("50.00"), Decimal("59.99"), Decimal("1.00")),
        ("F", Decimal("0.00"), Decimal("49.99"), Decimal("0.00")),
    ]

    created_conversions = []
    for i, (letter, min_pct, max_pct, gpa) in enumerate(conversions):
        conversion = GradeConversion.objects.create(
            grading_scale=language_standard_scale,
            letter_grade=letter,
            min_percentage=min_pct,
            max_percentage=max_pct,
            gpa_points=gpa,
            display_order=i,
            created_by=admin_user,
            updated_by=admin_user,
        )
        created_conversions.append(conversion)

    return created_conversions


@pytest.fixture
def academic_conversions(academic_scale, admin_user):
    """Create grade conversions for Academic scale with plus/minus grades."""
    conversions = [
        ("A+", Decimal("97.00"), Decimal("100.00"), Decimal("4.00")),
        ("A", Decimal("93.00"), Decimal("96.99"), Decimal("4.00")),
        ("A-", Decimal("90.00"), Decimal("92.99"), Decimal("3.70")),
        ("B+", Decimal("87.00"), Decimal("89.99"), Decimal("3.30")),
        ("B", Decimal("83.00"), Decimal("86.99"), Decimal("3.00")),
        ("B-", Decimal("80.00"), Decimal("82.99"), Decimal("2.70")),
        ("C+", Decimal("77.00"), Decimal("79.99"), Decimal("2.30")),
        ("C", Decimal("73.00"), Decimal("76.99"), Decimal("2.00")),
        ("C-", Decimal("70.00"), Decimal("72.99"), Decimal("1.70")),
        ("D+", Decimal("67.00"), Decimal("69.99"), Decimal("1.30")),
        ("D", Decimal("63.00"), Decimal("66.99"), Decimal("1.00")),
        ("D-", Decimal("60.00"), Decimal("62.99"), Decimal("0.70")),
        ("F", Decimal("0.00"), Decimal("59.99"), Decimal("0.00")),
    ]

    created_conversions = []
    for i, (letter, min_pct, max_pct, gpa) in enumerate(conversions):
        conversion = GradeConversion.objects.create(
            grading_scale=academic_scale,
            letter_grade=letter,
            min_percentage=min_pct,
            max_percentage=max_pct,
            gpa_points=gpa,
            display_order=i,
            created_by=admin_user,
            updated_by=admin_user,
        )
        created_conversions.append(conversion)

    return created_conversions


@pytest.fixture
def student_enrollment(db):
    """Create student enrollment for grade testing."""
    from apps.curriculum.models import Term
    from apps.enrollment.models import ClassHeaderEnrollment
    from apps.people.models import Person, StudentProfile
    from apps.scheduling.models import ClassHeader

    # Create person and student
    person = Person.objects.create(first_name="Jane", last_name="Student", email="jane.student@example.com")

    student = StudentProfile.objects.create(person=person, student_id="STU002")

    # Create term
    term = Term.objects.create(code="2024-1", name="Spring 2024", start_date="2024-01-15", end_date="2024-05-15")

    # Create class header (minimal for testing)
    class_header = ClassHeader.objects.create(class_code="ENG101-A", term=term, max_students=25)

    # Create enrollment
    enrollment = ClassHeaderEnrollment.objects.create(student=student, class_header=class_header)

    return enrollment


@pytest.fixture
def class_part(db):
    """Create class part for grade testing."""
    from apps.curriculum.models import Course, Term
    from apps.scheduling.models import ClassPart, ClassSession

    # Get or create term
    term, _ = Term.objects.get_or_create(
        code="2024-1", defaults={"name": "Spring 2024", "start_date": "2024-01-15", "end_date": "2024-05-15"}
    )

    # Create course for testing
    Course.objects.create(code="ENG101", title="English 101", credits=3)

    # Create class header
    from apps.scheduling.models import ClassHeader

    class_header = ClassHeader.objects.create(class_code="ENG101-A", term=term, max_students=25)

    # Create class session
    class_session = ClassSession.objects.create(
        class_header=class_header, session_number=1, weight_percentage=Decimal("100.00")
    )

    # Create class part
    class_part = ClassPart.objects.create(
        class_session=class_session, part_name="Grammar", weight_percentage=Decimal("50.00")
    )

    return class_part


@pytest.mark.django_db
class TestGradingScale:
    """Test GradingScale model business logic."""

    def test_grading_scale_creation(self, admin_user):
        """Test grading scale creation with all fields."""
        scale = GradingScale.objects.create(
            name="Test Scale",
            scale_type=GradingScale.ScaleType.LANGUAGE_STANDARD,
            description="Test description",
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert scale.name == "Test Scale"
        assert scale.scale_type == GradingScale.ScaleType.LANGUAGE_STANDARD
        assert scale.is_active is True
        assert "Language Standard" in str(scale)

    def test_scale_type_uniqueness(self, admin_user):
        """Test that scale types are unique."""
        # Create first scale
        GradingScale.objects.create(
            name="First Scale",
            scale_type=GradingScale.ScaleType.ACADEMIC,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Try to create duplicate scale type
        with pytest.raises(Exception):  # IntegrityError
            GradingScale.objects.create(
                name="Duplicate Scale",
                scale_type=GradingScale.ScaleType.ACADEMIC,
                created_by=admin_user,
                updated_by=admin_user,
            )

    @pytest.mark.parametrize(
        "scale_type",
        [
            GradingScale.ScaleType.LANGUAGE_STANDARD,
            GradingScale.ScaleType.LANGUAGE_IEAP,
            GradingScale.ScaleType.ACADEMIC,
        ],
    )
    def test_all_scale_types_supported(self, admin_user, scale_type):
        """Test all scale types can be created."""
        scale = GradingScale.objects.create(
            name=f"Test {scale_type} Scale",
            scale_type=scale_type,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert scale.scale_type == scale_type


@pytest.mark.django_db
class TestGradeConversion:
    """Test GradeConversion model business logic."""

    def test_grade_conversion_creation(self, language_standard_scale, admin_user):
        """Test grade conversion creation."""
        conversion = GradeConversion.objects.create(
            grading_scale=language_standard_scale,
            letter_grade="A",
            min_percentage=Decimal("80.00"),
            max_percentage=Decimal("100.00"),
            gpa_points=Decimal("4.00"),
            display_order=0,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert conversion.letter_grade == "A"
        assert conversion.min_percentage == Decimal("80.00")
        assert conversion.max_percentage == Decimal("100.00")
        assert conversion.gpa_points == Decimal("4.00")
        assert "A (80.00-100.00%)" in str(conversion)

    def test_percentage_range_validation(self, language_standard_scale, admin_user):
        """Test validation of percentage ranges."""
        # Test invalid range where min >= max
        with pytest.raises(ValidationError):
            conversion = GradeConversion(
                grading_scale=language_standard_scale,
                letter_grade="Invalid",
                min_percentage=Decimal("80.00"),
                max_percentage=Decimal("70.00"),  # Less than min
                gpa_points=Decimal("3.00"),
                created_by=admin_user,
                updated_by=admin_user,
            )
            conversion.full_clean()

        # Test equal min and max (should fail)
        with pytest.raises(ValidationError):
            conversion = GradeConversion(
                grading_scale=language_standard_scale,
                letter_grade="Equal",
                min_percentage=Decimal("80.00"),
                max_percentage=Decimal("80.00"),  # Equal to min
                gpa_points=Decimal("3.00"),
                created_by=admin_user,
                updated_by=admin_user,
            )
            conversion.full_clean()

    def test_unique_constraints(self, language_standard_scale, admin_user):
        """Test unique constraints on grade conversions."""
        # Create first conversion
        GradeConversion.objects.create(
            grading_scale=language_standard_scale,
            letter_grade="A",
            min_percentage=Decimal("80.00"),
            max_percentage=Decimal("100.00"),
            gpa_points=Decimal("4.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Try to create duplicate letter grade
        with pytest.raises(Exception):  # IntegrityError
            GradeConversion.objects.create(
                grading_scale=language_standard_scale,
                letter_grade="A",  # Duplicate letter grade
                min_percentage=Decimal("70.00"),
                max_percentage=Decimal("79.99"),
                gpa_points=Decimal("3.00"),
                created_by=admin_user,
                updated_by=admin_user,
            )

    def test_gpa_points_range_validation(self, language_standard_scale, admin_user):
        """Test GPA points validation (0.0 to 4.0)."""
        # Test negative GPA points
        with pytest.raises(ValidationError):
            conversion = GradeConversion(
                grading_scale=language_standard_scale,
                letter_grade="Invalid",
                min_percentage=Decimal("70.00"),
                max_percentage=Decimal("79.99"),
                gpa_points=Decimal("-1.00"),  # Negative
                created_by=admin_user,
                updated_by=admin_user,
            )
            conversion.full_clean()

        # Test GPA points over 4.0
        with pytest.raises(ValidationError):
            conversion = GradeConversion(
                grading_scale=language_standard_scale,
                letter_grade="Invalid",
                min_percentage=Decimal("70.00"),
                max_percentage=Decimal("79.99"),
                gpa_points=Decimal("5.00"),  # Over 4.0
                created_by=admin_user,
                updated_by=admin_user,
            )
            conversion.full_clean()

    def test_academic_scale_plus_minus_grades(self, academic_conversions):
        """Test academic scale supports plus/minus grades."""
        # Verify all plus/minus grades were created
        letters = [conv.letter_grade for conv in academic_conversions]

        assert "A+" in letters
        assert "A" in letters
        assert "A-" in letters
        assert "B+" in letters
        assert "C-" in letters
        assert "D+" in letters
        assert "F" in letters

        # Test GPA point differences
        a_plus = next(conv for conv in academic_conversions if conv.letter_grade == "A+")
        a_minus = next(conv for conv in academic_conversions if conv.letter_grade == "A-")

        assert a_plus.gpa_points == Decimal("4.00")
        assert a_minus.gpa_points == Decimal("3.70")

    @pytest.mark.parametrize(
        "percentage, expected_letter",
        [
            (Decimal("95.00"), "A"),
            (Decimal("85.00"), "B"),
            (Decimal("75.00"), "C"),
            (Decimal("55.00"), "D"),
            (Decimal("45.00"), "F"),
        ],
    )
    def test_percentage_to_letter_grade_mapping(self, language_standard_conversions, percentage, expected_letter):
        """Test percentage to letter grade mapping logic."""
        # Find the conversion that contains this percentage
        for conversion in language_standard_conversions:
            if conversion.min_percentage <= percentage <= conversion.max_percentage:
                assert conversion.letter_grade == expected_letter
                break
        else:
            pytest.fail(f"No grade conversion found for percentage {percentage}")


@pytest.mark.django_db
class TestClassPartGrade:
    """Test ClassPartGrade model business logic."""

    def test_class_part_grade_creation_numeric(self, student_enrollment, class_part, teacher_user):
        """Test grade creation with numeric score."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("85.50"),
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert grade.numeric_score == Decimal("85.50")
        assert grade.letter_grade == ""
        assert grade.grade_source == ClassPartGrade.GradeSource.MANUAL_TEACHER
        assert grade.grade_status == ClassPartGrade.GradeStatus.DRAFT
        assert grade.student_notified is False

    def test_class_part_grade_creation_letter(self, student_enrollment, class_part, teacher_user):
        """Test grade creation with letter grade."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            letter_grade="A",
            gpa_points=Decimal("4.00"),
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert grade.letter_grade == "A"
        assert grade.gpa_points == Decimal("4.00")
        assert grade.numeric_score is None

    def test_grade_validation_requires_score_or_letter(self, student_enrollment, class_part, teacher_user):
        """Test validation requires either numeric score or letter grade."""
        with pytest.raises(ValidationError):
            grade = ClassPartGrade(
                enrollment=student_enrollment,
                class_part=class_part,
                # No numeric_score or letter_grade
                entered_by=teacher_user,
                created_by=teacher_user,
                updated_by=teacher_user,
            )
            grade.full_clean()

    @pytest.mark.parametrize(
        "grade_source",
        [
            ClassPartGrade.GradeSource.MANUAL_TEACHER,
            ClassPartGrade.GradeSource.MANUAL_CLERK,
            ClassPartGrade.GradeSource.MOODLE_IMPORT,
            ClassPartGrade.GradeSource.CALCULATED,
            ClassPartGrade.GradeSource.MIGRATED,
        ],
    )
    def test_grade_source_options(self, student_enrollment, class_part, teacher_user, grade_source):
        """Test all grade source options are supported."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("80.00"),
            grade_source=grade_source,
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert grade.grade_source == grade_source

    @pytest.mark.parametrize(
        "grade_status",
        [
            ClassPartGrade.GradeStatus.DRAFT,
            ClassPartGrade.GradeStatus.SUBMITTED,
            ClassPartGrade.GradeStatus.APPROVED,
            ClassPartGrade.GradeStatus.FINALIZED,
        ],
    )
    def test_grade_status_workflow(self, student_enrollment, class_part, teacher_user, grade_status):
        """Test grade status workflow options."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("90.00"),
            grade_status=grade_status,
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert grade.grade_status == grade_status

    @pytest.mark.parametrize(
        "gpa_points, expected_passing",
        [
            (Decimal("4.00"), True),  # A
            (Decimal("3.00"), True),  # B
            (Decimal("2.00"), True),  # C
            (Decimal("1.00"), True),  # D
            (Decimal("0.70"), False),  # D- (below 1.0)
            (Decimal("0.00"), False),  # F
            (None, False),  # No GPA points
        ],
    )
    def test_is_passing_grade_logic(self, student_enrollment, class_part, teacher_user, gpa_points, expected_passing):
        """Test passing grade determination logic."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("75.00"),
            gpa_points=gpa_points,
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert grade.is_passing_grade() == expected_passing

    def test_is_passing_grade_with_letter_fallback(self, student_enrollment, class_part, teacher_user):
        """Test passing grade fallback to letter grade check."""
        # Test failing letter grade without GPA points
        failing_grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            letter_grade="F",
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert failing_grade.is_passing_grade() is False

        # Test passing letter grade without GPA points
        passing_grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            letter_grade="B",
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert passing_grade.is_passing_grade() is True

    def test_grade_modification_permissions(self, student_enrollment, class_part, teacher_user):
        """Test grade modification permission logic."""
        # Draft grade can be modified
        draft_grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("80.00"),
            grade_status=ClassPartGrade.GradeStatus.DRAFT,
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert draft_grade.can_be_modified() is True
        assert draft_grade.is_finalized() is False

        # Finalized grade cannot be modified
        draft_grade.grade_status = ClassPartGrade.GradeStatus.FINALIZED
        draft_grade.save()

        assert draft_grade.can_be_modified() is False
        assert draft_grade.is_finalized() is True

    def test_grade_display_formatting(self, student_enrollment, class_part, teacher_user):
        """Test grade display formatting logic."""
        # Numeric score only
        numeric_grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("87.50"),
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert numeric_grade.get_grade_display() == "87.50%"

        # Letter grade only
        letter_grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            letter_grade="A",
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert letter_grade.get_grade_display() == "A"

        # Both letter and numeric
        combined_grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            letter_grade="B+",
            numeric_score=Decimal("87.00"),
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        assert combined_grade.get_grade_display() == "B+ (87.00%)"

    def test_grade_approval_workflow(self, student_enrollment, class_part, teacher_user, admin_user):
        """Test grade approval workflow."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("92.00"),
            grade_status=ClassPartGrade.GradeStatus.SUBMITTED,
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        # Initially not approved
        assert grade.approved_by is None
        assert grade.approved_at is None

        # Approve grade
        grade.grade_status = ClassPartGrade.GradeStatus.APPROVED
        grade.approved_by = admin_user
        grade.approved_at = timezone.now()
        grade.save()

        assert grade.approved_by == admin_user
        assert grade.approved_at is not None

    def test_student_notification_tracking(self, student_enrollment, class_part, teacher_user):
        """Test student notification tracking."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("88.00"),
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        # Initially not notified
        assert grade.student_notified is False
        assert grade.notification_date is None

        # Mark as notified
        grade.student_notified = True
        grade.notification_date = timezone.now()
        grade.save()

        assert grade.student_notified is True
        assert grade.notification_date is not None

    def test_unique_enrollment_class_part_constraint(self, student_enrollment, class_part, teacher_user):
        """Test unique constraint on enrollment-class part combination."""
        # Create first grade
        ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("85.00"),
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        # Try to create duplicate
        with pytest.raises(Exception):  # IntegrityError
            ClassPartGrade.objects.create(
                enrollment=student_enrollment,
                class_part=class_part,
                numeric_score=Decimal("90.00"),
                entered_by=teacher_user,
                created_by=teacher_user,
                updated_by=teacher_user,
            )

    def test_numeric_score_validation(self, student_enrollment, class_part, teacher_user):
        """Test numeric score validation (0-100)."""
        # Test negative score
        with pytest.raises(ValidationError):
            grade = ClassPartGrade(
                enrollment=student_enrollment,
                class_part=class_part,
                numeric_score=Decimal("-5.00"),
                entered_by=teacher_user,
                created_by=teacher_user,
                updated_by=teacher_user,
            )
            grade.full_clean()

        # Test score over 100
        with pytest.raises(ValidationError):
            grade = ClassPartGrade(
                enrollment=student_enrollment,
                class_part=class_part,
                numeric_score=Decimal("105.00"),
                entered_by=teacher_user,
                created_by=teacher_user,
                updated_by=teacher_user,
            )
            grade.full_clean()

    def test_grade_change_audit_trail(self, student_enrollment, class_part, teacher_user):
        """Test grade change audit trail through timestamps."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("80.00"),
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        original_entered_at = grade.entered_at
        original_created = grade.created

        # Update grade
        grade.numeric_score = Decimal("85.00")
        grade.save()

        # Audit fields should be preserved/updated appropriately
        assert grade.entered_at == original_entered_at  # Should not change
        assert grade.created == original_created  # Should not change
        assert grade.updated >= original_created  # Should be updated


# Integration and business logic tests
@pytest.mark.django_db
class TestGradingBusinessLogic:
    """Test complex grading business logic scenarios."""

    def test_gpa_calculation_with_different_scales(
        self, language_standard_conversions, academic_conversions, admin_user
    ):
        """Test GPA calculation across different grading scales."""
        # Language Standard: A=4.0, B=3.0, C=2.0, D=1.0, F=0.0
        lang_a = next(conv for conv in language_standard_conversions if conv.letter_grade == "A")
        lang_b = next(conv for conv in language_standard_conversions if conv.letter_grade == "B")

        assert lang_a.gpa_points == Decimal("4.00")
        assert lang_b.gpa_points == Decimal("3.00")

        # Academic: A+=4.0, A=4.0, A-=3.70, B+=3.30, etc.
        acad_a_plus = next(conv for conv in academic_conversions if conv.letter_grade == "A+")
        acad_a_minus = next(conv for conv in academic_conversions if conv.letter_grade == "A-")
        acad_b_plus = next(conv for conv in academic_conversions if conv.letter_grade == "B+")

        assert acad_a_plus.gpa_points == Decimal("4.00")
        assert acad_a_minus.gpa_points == Decimal("3.70")
        assert acad_b_plus.gpa_points == Decimal("3.30")

    def test_grade_boundary_conditions(self, language_standard_conversions):
        """Test grade boundaries are correctly defined."""
        # Find A and B grades
        a_grade = next(conv for conv in language_standard_conversions if conv.letter_grade == "A")
        b_grade = next(conv for conv in language_standard_conversions if conv.letter_grade == "B")

        # A: 80.00 - 100.00
        # B: 70.00 - 79.99

        # Test boundary conditions
        assert a_grade.min_percentage == Decimal("80.00")
        assert a_grade.max_percentage == Decimal("100.00")
        assert b_grade.min_percentage == Decimal("70.00")
        assert b_grade.max_percentage == Decimal("79.99")

        # Ensure no gaps or overlaps
        assert b_grade.max_percentage < a_grade.min_percentage

    def test_failing_grade_thresholds_by_scale(self, language_standard_conversions, academic_conversions):
        """Test different failing grade thresholds by scale type."""
        # Language Standard: F < 50%
        lang_f = next(conv for conv in language_standard_conversions if conv.letter_grade == "F")
        lang_d = next(conv for conv in language_standard_conversions if conv.letter_grade == "D")

        assert lang_f.max_percentage == Decimal("49.99")
        assert lang_d.min_percentage == Decimal("50.00")

        # Academic: F < 60% (stricter)
        acad_f = next(conv for conv in academic_conversions if conv.letter_grade == "F")
        acad_d_minus = next(conv for conv in academic_conversions if conv.letter_grade == "D-")

        assert acad_f.max_percentage == Decimal("59.99")
        assert acad_d_minus.min_percentage == Decimal("60.00")

    def test_grade_workflow_state_transitions(self, student_enrollment, class_part, teacher_user, admin_user):
        """Test valid grade workflow state transitions."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("88.00"),
            grade_status=ClassPartGrade.GradeStatus.DRAFT,
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        # Draft -> Submitted
        grade.grade_status = ClassPartGrade.GradeStatus.SUBMITTED
        grade.save()
        assert grade.can_be_modified() is True

        # Submitted -> Approved
        grade.grade_status = ClassPartGrade.GradeStatus.APPROVED
        grade.approved_by = admin_user
        grade.approved_at = timezone.now()
        grade.save()
        assert grade.can_be_modified() is True

        # Approved -> Finalized
        grade.grade_status = ClassPartGrade.GradeStatus.FINALIZED
        grade.save()
        assert grade.can_be_modified() is False
        assert grade.is_finalized() is True

    def test_precision_handling_in_calculations(self, student_enrollment, class_part, teacher_user):
        """Test decimal precision in grade calculations."""
        # Test precise decimal calculations
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("87.333"),  # More than 2 decimal places
            gpa_points=Decimal("3.333"),  # More than 2 decimal places
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        # Should handle precision according to field definitions
        # Model should truncate/round to defined decimal places
        with pytest.raises(Exception):  # ValidationError for invalid precision
            grade.full_clean()

    def test_grade_relationships_and_properties(self, student_enrollment, class_part, teacher_user):
        """Test grade model relationships and derived properties."""
        grade = ClassPartGrade.objects.create(
            enrollment=student_enrollment,
            class_part=class_part,
            numeric_score=Decimal("91.00"),
            entered_by=teacher_user,
            created_by=teacher_user,
            updated_by=teacher_user,
        )

        # Test derived properties
        assert grade.student == student_enrollment.student
        assert grade.class_header == student_enrollment.class_header
        assert grade.class_session == class_part.class_session

        # Test relationships are properly established
        assert grade in student_enrollment.class_part_grades.all()
        assert grade in class_part.class_part_grades.all()
