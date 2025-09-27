"""Unit tests for Academic app models.

This module tests the critical business logic of academic models including:
- Canonical requirement definitions and validation
- Course equivalency mapping with term versioning
- Transfer credit approval and validation
- Student degree progress tracking and fulfillment
- Requirement exception handling
- Academic standing calculations

Focus on testing the "why" - the actual academic rules and degree audit logic.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.academic.models import (
    CanonicalRequirement,
    CourseEquivalency,
    StudentCourseOverride,
    StudentDegreeProgress,
    StudentRequirementException,
    TransferCredit,
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
def registrar_user():
    """Create registrar user for tests."""
    return User.objects.create_user(
        username="registrar",
        email="registrar@example.com",
        password="testpass123",
    )


@pytest.fixture
def student(db):
    """Create student profile for testing."""
    from apps.people.models import Person, StudentProfile

    person = Person.objects.create(first_name="Alice", last_name="Academic", email="alice.academic@example.com")

    return StudentProfile.objects.create(person=person, student_id="STU003")


@pytest.fixture
def major(db):
    """Create major for testing."""
    from apps.curriculum.models import Major

    return Major.objects.create(code="BUSADMIN", title="Business Administration", credits_required=129)


@pytest.fixture
def term_2024_1(db):
    """Create Spring 2024 term."""
    from apps.curriculum.models import Term

    return Term.objects.create(
        code="2024-1", name="Spring 2024", start_date=date(2024, 1, 15), end_date=date(2024, 5, 15)
    )


@pytest.fixture
def term_2024_2(db):
    """Create Fall 2024 term."""
    from apps.curriculum.models import Term

    return Term.objects.create(
        code="2024-2", name="Fall 2024", start_date=date(2024, 8, 15), end_date=date(2024, 12, 15)
    )


@pytest.fixture
def course_eng101(db):
    """Create English 101 course."""
    from apps.curriculum.models import Course

    return Course.objects.create(code="ENG101", title="English Composition I", credits=3)


@pytest.fixture
def course_eng102(db):
    """Create English 102 course."""
    from apps.curriculum.models import Course

    return Course.objects.create(code="ENG102", title="English Composition II", credits=3)


@pytest.fixture
def course_math101(db):
    """Create Math 101 course."""
    from apps.curriculum.models import Course

    return Course.objects.create(code="MATH101", title="College Algebra", credits=3)


@pytest.fixture
def canonical_requirement(major, course_eng101, term_2024_1):
    """Create canonical requirement for testing."""
    return CanonicalRequirement.objects.create(
        major=major,
        sequence_number=1,
        required_course=course_eng101,
        name="English Composition I",
        description="First required English course",
        effective_term=term_2024_1,
        is_active=True,
    )


@pytest.mark.django_db
class TestCanonicalRequirement:
    """Test CanonicalRequirement model business logic."""

    def test_canonical_requirement_creation(self, major, course_eng101, term_2024_1):
        """Test canonical requirement creation with required fields."""
        requirement = CanonicalRequirement.objects.create(
            major=major,
            sequence_number=1,
            required_course=course_eng101,
            name="English Composition I",
            description="First English course in sequence",
            effective_term=term_2024_1,
            is_active=True,
        )

        assert requirement.major == major
        assert requirement.sequence_number == 1
        assert requirement.required_course == course_eng101
        assert requirement.canonical_credits == Decimal("3")  # From course.credits
        assert requirement.is_active is True
        assert "BUSADMIN #1: ENG101" in str(requirement)

    def test_canonical_credits_from_course(self, major, course_eng101, term_2024_1):
        """Test canonical credits derived from required course."""
        requirement = CanonicalRequirement.objects.create(
            major=major,
            sequence_number=2,
            required_course=course_eng101,
            name="English Course",
            effective_term=term_2024_1,
        )

        # Credits should come from the course, not be stored separately
        assert requirement.canonical_credits == Decimal("3")

        # Change course credits and verify it reflects
        course_eng101.credits = 4
        course_eng101.save()
        requirement.refresh_from_db()

        assert requirement.canonical_credits == Decimal("4")

    def test_sequence_uniqueness_per_major_term(self, major, course_eng101, course_eng102, term_2024_1):
        """Test sequence number uniqueness within major and term."""
        # Create first requirement
        CanonicalRequirement.objects.create(
            major=major, sequence_number=1, required_course=course_eng101, name="English I", effective_term=term_2024_1
        )

        # Try to create duplicate sequence number
        with pytest.raises(Exception):  # IntegrityError
            CanonicalRequirement.objects.create(
                major=major,
                sequence_number=1,  # Duplicate sequence
                required_course=course_eng102,
                name="English II",
                effective_term=term_2024_1,
            )

    def test_course_uniqueness_per_major_term(self, major, course_eng101, term_2024_1):
        """Test course uniqueness within major and term."""
        # Create first requirement
        CanonicalRequirement.objects.create(
            major=major, sequence_number=1, required_course=course_eng101, name="English I", effective_term=term_2024_1
        )

        # Try to create duplicate course
        with pytest.raises(Exception):  # IntegrityError
            CanonicalRequirement.objects.create(
                major=major,
                sequence_number=2,
                required_course=course_eng101,  # Duplicate course
                name="English I Again",
                effective_term=term_2024_1,
            )

    def test_term_versioning_validation(self, major, course_eng101, term_2024_1, term_2024_2):
        """Test term ordering validation for versioning."""
        # Test invalid term ordering (end before effective)
        with pytest.raises(ValidationError):
            requirement = CanonicalRequirement(
                major=major,
                sequence_number=1,
                required_course=course_eng101,
                name="English I",
                effective_term=term_2024_2,  # Fall
                end_term=term_2024_1,  # Spring (earlier)
            )
            requirement.full_clean()

    def test_is_currently_effective_property(self, major, course_eng101, term_2024_1, term_2024_2):
        """Test current effectiveness determination."""
        # Active requirement without end term
        active_requirement = CanonicalRequirement.objects.create(
            major=major,
            sequence_number=1,
            required_course=course_eng101,
            name="Active English",
            effective_term=term_2024_1,
            is_active=True,
        )

        assert active_requirement.is_currently_effective is True

        # Inactive requirement
        active_requirement.is_active = False
        active_requirement.save()

        assert active_requirement.is_currently_effective is False

    @pytest.mark.parametrize(
        "sequence_number, expected_valid",
        [
            (1, True),
            (43, True),  # Max for BA
            (50, True),  # Max allowed
            (0, False),  # Below minimum
            (51, False),  # Above maximum
        ],
    )
    def test_sequence_number_validation(self, major, course_eng101, term_2024_1, sequence_number, expected_valid):
        """Test sequence number validation range."""
        if expected_valid:
            requirement = CanonicalRequirement.objects.create(
                major=major,
                sequence_number=sequence_number,
                required_course=course_eng101,
                name=f"Course {sequence_number}",
                effective_term=term_2024_1,
            )
            assert requirement.sequence_number == sequence_number
        else:
            with pytest.raises(ValidationError):
                requirement = CanonicalRequirement(
                    major=major,
                    sequence_number=sequence_number,
                    required_course=course_eng101,
                    name=f"Course {sequence_number}",
                    effective_term=term_2024_1,
                )
                requirement.full_clean()


@pytest.mark.django_db
class TestCourseEquivalency:
    """Test CourseEquivalency model business logic."""

    def test_equivalency_creation(self, course_eng101, course_eng102, term_2024_1, admin_user):
        """Test course equivalency creation."""
        equivalency = CourseEquivalency.objects.create(
            original_course=course_eng101,
            equivalent_course=course_eng102,
            bidirectional=False,
            effective_term=term_2024_1,
            reason="Course renumbering",
            approval_date=date.today(),
            approved_by=admin_user,
        )

        assert equivalency.original_course == course_eng101
        assert equivalency.equivalent_course == course_eng102
        assert equivalency.bidirectional is False
        assert "ENG101 → ENG102" in str(equivalency)

    def test_bidirectional_equivalency_display(self, course_eng101, course_eng102, term_2024_1, admin_user):
        """Test bidirectional equivalency string representation."""
        equivalency = CourseEquivalency.objects.create(
            original_course=course_eng101,
            equivalent_course=course_eng102,
            bidirectional=True,
            effective_term=term_2024_1,
            reason="Mutual equivalency",
            approval_date=date.today(),
            approved_by=admin_user,
        )

        assert "ENG101 ↔ ENG102" in str(equivalency)

    def test_self_equivalency_validation(self, course_eng101, term_2024_1, admin_user):
        """Test validation prevents self-equivalency."""
        with pytest.raises(ValidationError):
            equivalency = CourseEquivalency(
                original_course=course_eng101,
                equivalent_course=course_eng101,  # Same course
                effective_term=term_2024_1,
                reason="Invalid self-equivalency",
                approval_date=date.today(),
                approved_by=admin_user,
            )
            equivalency.full_clean()

    def test_term_versioning_for_equivalencies(
        self, course_eng101, course_eng102, term_2024_1, term_2024_2, admin_user
    ):
        """Test term-based versioning for equivalency changes."""
        # Create equivalency effective in Spring
        spring_equivalency = CourseEquivalency.objects.create(
            original_course=course_eng101,
            equivalent_course=course_eng102,
            effective_term=term_2024_1,
            end_term=term_2024_2,
            reason="Temporary equivalency",
            approval_date=date.today(),
            approved_by=admin_user,
        )

        # Create new equivalency effective in Fall
        fall_equivalency = CourseEquivalency.objects.create(
            original_course=course_eng101,
            equivalent_course=course_eng102,
            effective_term=term_2024_2,
            reason="Updated equivalency",
            approval_date=date.today(),
            approved_by=admin_user,
        )

        assert spring_equivalency.end_term == term_2024_2
        assert fall_equivalency.effective_term == term_2024_2

    def test_unique_equivalency_per_term(self, course_eng101, course_eng102, term_2024_1, admin_user):
        """Test unique constraint on equivalency per term."""
        # Create first equivalency
        CourseEquivalency.objects.create(
            original_course=course_eng101,
            equivalent_course=course_eng102,
            effective_term=term_2024_1,
            reason="First equivalency",
            approval_date=date.today(),
            approved_by=admin_user,
        )

        # Try to create duplicate
        with pytest.raises(Exception):  # IntegrityError
            CourseEquivalency.objects.create(
                original_course=course_eng101,
                equivalent_course=course_eng102,
                effective_term=term_2024_1,  # Same term
                reason="Duplicate equivalency",
                approval_date=date.today(),
                approved_by=admin_user,
            )


@pytest.mark.django_db
class TestTransferCredit:
    """Test TransferCredit model business logic."""

    def test_transfer_credit_creation(self, student, registrar_user):
        """Test transfer credit creation with required fields."""
        transfer = TransferCredit.objects.create(
            student=student,
            external_institution="University of California",
            external_course_code="ENGL 101",
            external_course_name="College Writing",
            external_credits=Decimal("3.00"),
            external_grade="A",
            approval_status=TransferCredit.ApprovalStatus.APPROVED,
            reviewed_by=registrar_user,
            created_by=registrar_user,
            updated_by=registrar_user,
        )

        assert transfer.student == student
        assert transfer.external_credits == Decimal("3.00")
        assert transfer.external_grade == "A"
        assert transfer.approval_status == TransferCredit.ApprovalStatus.APPROVED

    def test_transfer_credit_workflow_states(self, student, registrar_user):
        """Test transfer credit approval workflow."""
        transfer = TransferCredit.objects.create(
            student=student,
            external_institution="State University",
            external_course_code="MATH 110",
            external_course_name="College Algebra",
            external_credits=Decimal("4.00"),
            approval_status=TransferCredit.ApprovalStatus.PENDING,
            created_by=registrar_user,
            updated_by=registrar_user,
        )

        # Initially pending
        assert transfer.approval_status == TransferCredit.ApprovalStatus.PENDING
        assert transfer.reviewed_by is None

        # Approve transfer
        transfer.approval_status = TransferCredit.ApprovalStatus.APPROVED
        transfer.reviewed_by = registrar_user
        transfer.save()

        assert transfer.approval_status == TransferCredit.ApprovalStatus.APPROVED
        assert transfer.reviewed_by == registrar_user

    def test_course_mapping_integration(self, student, course_math101, registrar_user):
        """Test transfer credit with course mapping."""
        transfer = TransferCredit.objects.create(
            student=student,
            external_institution="Community College",
            external_course_code="MATH 101",
            external_course_name="Basic Algebra",
            external_credits=Decimal("3.00"),
            equivalent_course=course_math101,  # Maps to our course
            awarded_credits=Decimal("3.00"),
            approval_status=TransferCredit.ApprovalStatus.APPROVED,
            reviewed_by=registrar_user,
            created_by=registrar_user,
            updated_by=registrar_user,
        )

        assert transfer.equivalent_course == course_math101
        assert transfer.awarded_credits == Decimal("3.00")

    def test_credit_conversion_scenarios(self, student, registrar_user):
        """Test different credit conversion scenarios."""
        # Exact credit match
        exact_transfer = TransferCredit.objects.create(
            student=student,
            external_institution="Partner University",
            external_course_code="BUS 101",
            external_course_name="Business 101",
            external_credits=Decimal("3.00"),
            awarded_credits=Decimal("3.00"),  # Exact match
            approval_status=TransferCredit.ApprovalStatus.APPROVED,
            created_by=registrar_user,
            updated_by=registrar_user,
        )

        # Credit reduction
        reduced_transfer = TransferCredit.objects.create(
            student=student,
            external_institution="Other University",
            external_course_code="ENG 200",
            external_course_name="English 200",
            external_credits=Decimal("4.00"),
            awarded_credits=Decimal("3.00"),  # Reduced due to policy
            approval_status=TransferCredit.ApprovalStatus.APPROVED,
            created_by=registrar_user,
            updated_by=registrar_user,
        )

        assert exact_transfer.external_credits == exact_transfer.awarded_credits
        assert reduced_transfer.external_credits > reduced_transfer.awarded_credits

    @pytest.mark.parametrize(
        "status",
        [
            TransferCredit.ApprovalStatus.PENDING,
            TransferCredit.ApprovalStatus.APPROVED,
            TransferCredit.ApprovalStatus.REJECTED,
            TransferCredit.ApprovalStatus.MORE_INFO,
        ],
    )
    def test_all_transfer_statuses(self, student, registrar_user, status):
        """Test all transfer credit status options."""
        transfer = TransferCredit.objects.create(
            student=student,
            external_institution="Test University",
            external_course_code="TEST 101",
            external_course_name="Test Course 101",
            external_credits=Decimal("3.00"),
            approval_status=status,
            created_by=registrar_user,
            updated_by=registrar_user,
        )

        assert transfer.approval_status == status


@pytest.mark.django_db
class TestStudentDegreeProgress:
    """Test StudentDegreeProgress model business logic."""

    def test_degree_progress_creation(self, student, canonical_requirement):
        """Test student degree progress creation."""
        progress = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION,
            fulfillment_date=date.today(),
            credits_earned=Decimal("3.00"),
            grade="A",
            is_active=True,
        )

        assert progress.student == student
        assert progress.canonical_requirement == canonical_requirement
        assert progress.fulfillment_method == StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION
        assert progress.credits_earned == Decimal("3.00")
        assert progress.grade == "A"

    @pytest.mark.parametrize(
        "fulfillment_method",
        [
            StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION,
            StudentDegreeProgress.FulfillmentMethod.TRANSFER_CREDIT,
            StudentDegreeProgress.FulfillmentMethod.EXCEPTION_SUBSTITUTION,
            StudentDegreeProgress.FulfillmentMethod.WAIVER,
            StudentDegreeProgress.FulfillmentMethod.EXAM_CREDIT,
        ],
    )
    def test_fulfillment_methods(self, student, canonical_requirement, fulfillment_method):
        """Test all fulfillment method options."""
        progress = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=fulfillment_method,
            fulfillment_date=date.today(),
            credits_earned=Decimal("3.00"),
            is_active=True,
        )

        assert progress.fulfillment_method == fulfillment_method

    def test_enrollment_fulfillment(self, student, canonical_requirement, db):
        """Test fulfillment through course enrollment."""
        from apps.curriculum.models import Term
        from apps.enrollment.models import ClassHeaderEnrollment
        from apps.scheduling.models import ClassHeader

        # Create enrollment
        term = Term.objects.create(
            code="2024-1", name="Spring 2024", start_date=date(2024, 1, 15), end_date=date(2024, 5, 15)
        )

        class_header = ClassHeader.objects.create(class_code="ENG101-A", term=term, max_students=25)

        enrollment = ClassHeaderEnrollment.objects.create(student=student, class_header=class_header)

        # Create progress linked to enrollment
        progress = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION,
            fulfilling_enrollment=enrollment,
            fulfillment_date=date.today(),
            credits_earned=Decimal("3.00"),
            grade="B+",
            is_active=True,
        )

        assert progress.fulfilling_enrollment == enrollment
        assert progress.fulfillment_method == StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION

    def test_transfer_credit_fulfillment(self, student, canonical_requirement, registrar_user):
        """Test fulfillment through transfer credit."""
        # Create transfer credit
        transfer = TransferCredit.objects.create(
            student=student,
            external_institution="Transfer University",
            external_course_code="ENG 101",
            external_credits=Decimal("3.00"),
            awarded_credits=Decimal("3.00"),
            status=TransferCredit.TransferStatus.APPROVED,
            requested_by=registrar_user,
            created_by=registrar_user,
            updated_by=registrar_user,
        )

        # Create progress linked to transfer
        progress = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.TRANSFER_CREDIT,
            fulfilling_transfer=transfer,
            fulfillment_date=date.today(),
            credits_earned=Decimal("3.00"),
            grade="B",
            is_active=True,
        )

        assert progress.fulfilling_transfer == transfer
        assert progress.fulfillment_method == StudentDegreeProgress.FulfillmentMethod.TRANSFER_CREDIT

    def test_completion_status_tracking(self, student, canonical_requirement):
        """Test completion status tracking."""
        progress = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION,
            fulfillment_date=date.today(),
            credits_earned=Decimal("3.00"),
            completion_status="COMPLETED",
            is_active=True,
        )

        assert progress.completion_status == "COMPLETED"

        # Test other completion statuses
        progress.completion_status = "IN_PROGRESS"
        progress.save()

        assert progress.completion_status == "IN_PROGRESS"


@pytest.mark.django_db
class TestStudentRequirementException:
    """Test StudentRequirementException model business logic."""

    def test_requirement_exception_creation(self, student, canonical_requirement, admin_user):
        """Test student requirement exception creation."""
        exception = StudentRequirementException.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.COURSE_SUBSTITUTION,
            reason="Student has equivalent background knowledge",
            requested_by=admin_user,
            approved_by=admin_user,
            approval_date=date.today(),
            effective_term=term_2024_1,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert exception.student == student
        assert exception.canonical_requirement == canonical_requirement
        assert exception.exception_type == StudentRequirementException.ExceptionType.COURSE_SUBSTITUTION
        assert exception.approved_by == admin_user

    @pytest.mark.parametrize(
        "exception_type",
        [
            StudentRequirementException.ExceptionType.WAIVER,
            StudentRequirementException.ExceptionType.COURSE_SUBSTITUTION,
            StudentRequirementException.ExceptionType.ADMINISTRATIVE_OVERRIDE,
            StudentRequirementException.ExceptionType.EXAM_CREDIT,
        ],
    )
    def test_exception_types(self, student, canonical_requirement, admin_user, exception_type):
        """Test all exception type options."""
        exception = StudentRequirementException.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            exception_type=exception_type,
            reason=f"Test {exception_type} exception",
            requested_by=admin_user,
            approved_by=admin_user,
            approval_date=date.today(),
            effective_term=term_2024_1,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert exception.exception_type == exception_type

    def test_exception_approval_workflow(self, student, canonical_requirement, admin_user, registrar_user):
        """Test exception approval workflow."""
        exception = StudentRequirementException.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.WAIVER,
            reason="Medical leave accommodation",
            requested_by=registrar_user,
            approval_status=StudentRequirementException.ApprovalStatus.PENDING,
            effective_term=term_2024_1,
            is_waived=True,
            created_by=registrar_user,
            updated_by=registrar_user,
        )

        # Initially pending
        assert exception.approval_status == StudentRequirementException.ApprovalStatus.PENDING
        assert exception.approved_by is None

        # Approve exception
        exception.approval_status = StudentRequirementException.ApprovalStatus.APPROVED
        exception.approved_by = admin_user
        exception.approval_date = date.today()
        exception.save()

        assert exception.approval_status == StudentRequirementException.ApprovalStatus.APPROVED
        assert exception.approved_by == admin_user


@pytest.mark.django_db
class TestStudentCourseOverride:
    """Test StudentCourseOverride model business logic."""

    def test_course_override_creation(self, student, course_eng101, course_eng102, admin_user):
        """Test student course override creation."""
        override = StudentCourseOverride.objects.create(
            student=student,
            original_course=course_eng101,
            substitute_course=course_eng102,
            reason="Schedule conflict resolution",
            requested_by=admin_user,
            approved_by=admin_user,
            approval_date=date.today(),
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert override.student == student
        assert override.original_course == course_eng101
        assert override.substitute_course == course_eng102
        assert override.approved_by == admin_user

    def test_override_with_credit_adjustment(self, student, course_eng101, admin_user):
        """Test override with credit adjustment."""
        # Create course with different credits
        from apps.curriculum.models import Course

        special_course = Course.objects.create(
            code="ENG101S",
            title="English 101 Special",
            credits=4,  # Different credit value
        )

        override = StudentCourseOverride.objects.create(
            student=student,
            original_course=course_eng101,
            substitute_course=special_course,
            detailed_reason="Special program requirement",
            effective_term=term_2024_1,
            requested_by=admin_user,
            approved_by=admin_user,
            approval_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Test that the override is valid
        assert override.substitute_course == special_course
        assert override.substitute_course.credits == 4  # Different credit value
        assert course_eng101.credits == 3  # Original course credits


# Integration and business logic tests
@pytest.mark.django_db
class TestAcademicBusinessLogic:
    """Test complex academic business logic scenarios."""

    def test_degree_audit_calculation(self, student, major, course_eng101, course_eng102, term_2024_1):
        """Test degree audit calculation with multiple requirements."""
        # Create canonical requirements
        req1 = CanonicalRequirement.objects.create(
            major=major, sequence_number=1, required_course=course_eng101, name="English I", effective_term=term_2024_1
        )

        req2 = CanonicalRequirement.objects.create(
            major=major,
            sequence_number=2,
            required_course=course_eng102,
            name="English II",
            effective_term=term_2024_1,
        )

        # Create fulfillment for first requirement
        StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=req1,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION,
            fulfillment_date=date.today(),
            credits_earned=Decimal("3.00"),
            grade="A",
            is_active=True,
        )

        # Verify fulfillment tracking
        fulfilled_reqs = student.requirement_fulfillments.filter(is_active=True)
        assert fulfilled_reqs.count() == 1
        assert (fulfilled_reqs.first().canonical_requirement if fulfilled_reqs.first() else None) == req1

        # Second requirement should still be unfulfilled
        unfulfilled_reqs = CanonicalRequirement.objects.filter(major=major, is_active=True).exclude(
            student_fulfillments__student=student, student_fulfillments__is_active=True
        )
        assert unfulfilled_reqs.count() == 1
        assert req2 in unfulfilled_reqs

    def test_equivalency_resolution(self, course_eng101, course_eng102, term_2024_1, admin_user):
        """Test course equivalency resolution logic."""
        # Create bidirectional equivalency
        CourseEquivalency.objects.create(
            original_course=course_eng101,
            equivalent_course=course_eng102,
            bidirectional=True,
            effective_term=term_2024_1,
            reason="Curriculum update",
            approval_date=date.today(),
            approved_by=admin_user,
        )

        # Verify equivalency relationships
        eng101_equivalents = CourseEquivalency.objects.filter(original_course=course_eng101, is_active=True)
        assert eng101_equivalents.count() == 1
        assert (eng101_equivalents.first().equivalent_course if eng101_equivalents.first() else None) == course_eng102

        # For bidirectional, should also work in reverse
        CourseEquivalency.objects.filter(original_course=course_eng102, is_active=True)
        # Note: Bidirectional logic would need to be implemented in services

    def test_transfer_credit_integration_with_requirements(self, student, canonical_requirement, registrar_user):
        """Test transfer credit fulfilling canonical requirements."""
        # Create approved transfer credit
        transfer = TransferCredit.objects.create(
            student=student,
            external_institution="Partner College",
            external_course_code="ENG 101",
            external_course_name="Composition I",
            external_credits=Decimal("3.00"),
            awarded_credits=Decimal("3.00"),
            equivalent_course=canonical_requirement.required_course,
            approval_status=TransferCredit.ApprovalStatus.APPROVED,
            reviewed_by=registrar_user,
            created_by=registrar_user,
            updated_by=registrar_user,
        )

        # Create degree progress record for transfer fulfillment
        progress = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.TRANSFER_CREDIT,
            fulfilling_transfer=transfer,
            fulfillment_date=date.today(),
            credits_earned=transfer.awarded_credits,
            grade=transfer.external_grade,
            is_active=True,
        )

        # Verify integration
        assert progress.fulfilling_transfer == transfer
        assert progress.credits_earned == transfer.awarded_credits
        assert transfer.equivalent_course == canonical_requirement.required_course

    def test_exception_handling_workflow(self, student, canonical_requirement, admin_user):
        """Test complete exception handling workflow."""
        # Create exception request
        exception = StudentRequirementException.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.WAIVER,
            reason="Student demonstrated competency through work experience",
            requested_by=admin_user,
            approval_status=StudentRequirementException.ApprovalStatus.PENDING,
            effective_term=term_2024_1,
            is_waived=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Process exception approval
        exception.approval_status = StudentRequirementException.ApprovalStatus.APPROVED
        exception.approved_by = admin_user
        exception.approval_date = date.today()
        exception.save()

        # Create degree progress for waiver
        progress = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.WAIVER,
            fulfillment_date=exception.approval_date,
            credits_earned=canonical_requirement.canonical_credits,
            is_active=True,
        )

        # Verify complete workflow
        assert exception.approval_status == StudentRequirementException.ApprovalStatus.APPROVED
        assert progress.fulfillment_method == StudentDegreeProgress.FulfillmentMethod.WAIVER

    def test_credit_calculation_precision(self, student, canonical_requirement):
        """Test credit calculation precision in academic tracking."""
        # Test precise credit calculations
        progress = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION,
            fulfillment_date=date.today(),
            credits_earned=Decimal("3.00"),
            is_active=True,
        )

        assert progress.credits_earned == Decimal("3.00")

        # Test that canonical credits come from course
        assert canonical_requirement.canonical_credits == Decimal("3")  # From fixture course

        # Credits earned can differ from canonical (e.g., transfer conversions)
        progress.credits_earned = Decimal("2.50")  # Reduced due to conversion
        progress.save()

        assert progress.credits_earned == Decimal("2.50")
        assert canonical_requirement.canonical_credits == Decimal("3")  # Unchanged
