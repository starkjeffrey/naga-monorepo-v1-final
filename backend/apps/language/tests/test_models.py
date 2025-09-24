"""Test cases for language app models.

Tests the language promotion and level skip models including
validation, status transitions, and audit trail functionality.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.curriculum.models import Course, Cycle, Division, Major, Term
from apps.language.models import (
    LanguageLevelSkipRequest,
    LanguageProgramPromotion,
    LanguageStudentPromotion,
)
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


@pytest.mark.django_db
class TestLanguageProgramPromotion:
    """Test LanguageProgramPromotion model."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data."""
        # Create user
        user = User.objects.create_user(email="test@example.com", name="Test User")

        # Create division and cycle
        division = Division.objects.create(name="Language Division", short_name="LANG")
        cycle = Cycle.objects.create(division=division, name="Language Programs", short_name="LANG")

        # Create terms
        source_term = Term.objects.create(
            name="ENG A 2024-1",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-01-01",
            end_date="2024-03-31",
        )
        target_term = Term.objects.create(
            name="ENG A 2024-2",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-04-01",
            end_date="2024-06-30",
        )

        return {
            "user": user,
            "division": division,
            "cycle": cycle,
            "source_term": source_term,
            "target_term": target_term,
        }

    def test_create_promotion_batch(self, setup_data):
        """Test creating a promotion batch."""
        promotion = LanguageProgramPromotion.objects.create(
            source_term=setup_data["source_term"],
            target_term=setup_data["target_term"],
            program="EHSS",
            initiated_by=setup_data["user"],
            notes="Test promotion batch",
        )

        assert promotion.source_term == setup_data["source_term"]
        assert promotion.target_term == setup_data["target_term"]
        assert promotion.program == "EHSS"
        assert promotion.status == LanguageProgramPromotion.PromotionStatus.INITIATED
        assert promotion.students_promoted_count == 0
        assert promotion.classes_cloned_count == 0

    def test_promotion_status_transitions(self, setup_data):
        """Test status transitions for promotion batch."""
        promotion = LanguageProgramPromotion.objects.create(
            source_term=setup_data["source_term"],
            target_term=setup_data["target_term"],
            program="EHSS",
            initiated_by=setup_data["user"],
        )

        # Test mark_completed
        promotion.mark_completed(students_count=25, classes_count=5)
        promotion.refresh_from_db()

        assert promotion.status == LanguageProgramPromotion.PromotionStatus.COMPLETED
        assert promotion.students_promoted_count == 25
        assert promotion.classes_cloned_count == 5
        assert promotion.completed_at is not None

        # Test mark_failed
        promotion.mark_failed("Test failure reason")
        promotion.refresh_from_db()

        assert promotion.status == LanguageProgramPromotion.PromotionStatus.FAILED
        assert "Test failure reason" in promotion.notes

    def test_unique_constraint(self, setup_data):
        """Test unique constraint on source_term, target_term, program."""
        LanguageProgramPromotion.objects.create(
            source_term=setup_data["source_term"],
            target_term=setup_data["target_term"],
            program="EHSS",
            initiated_by=setup_data["user"],
        )

        # Should raise integrity error for duplicate
        with pytest.raises(Exception):  # IntegrityError
            LanguageProgramPromotion.objects.create(
                source_term=setup_data["source_term"],
                target_term=setup_data["target_term"],
                program="EHSS",
                initiated_by=setup_data["user"],
            )

    def test_string_representation(self, setup_data):
        """Test string representation of promotion batch."""
        promotion = LanguageProgramPromotion.objects.create(
            source_term=setup_data["source_term"],
            target_term=setup_data["target_term"],
            program="EHSS",
            initiated_by=setup_data["user"],
        )

        expected = f"EHSS promotion: {setup_data['source_term']} → {setup_data['target_term']}"
        assert str(promotion) == expected


@pytest.mark.django_db
class TestLanguageStudentPromotion:
    """Test LanguageStudentPromotion model."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data."""
        # Create user and student
        User.objects.create_user(email="student@example.com", name="Test Student")
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff Member")

        person = Person.objects.create(family_name="Test", personal_name="Student", date_of_birth="2000-01-01")
        student = StudentProfile.objects.create(person=person, student_id=1)

        # Create division, cycle, and major
        division = Division.objects.create(name="Language Division", short_name="LANG")
        cycle = Cycle.objects.create(division=division, name="Language Programs", short_name="LANG")
        Major.objects.create(
            cycle=cycle,
            name="English for High School Students",
            code="EHSS",
            program_type=Major.ProgramType.LANGUAGE,
        )

        # Create course
        course = Course.objects.create(
            code="EHSS-05",
            title="English for High School Level 5",
            short_title="EHSS L5",
            division=division,
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        # Create terms
        source_term = Term.objects.create(
            name="ENG A 2024-1",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-01-01",
            end_date="2024-03-31",
        )
        target_term = Term.objects.create(
            name="ENG A 2024-2",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-04-01",
            end_date="2024-06-30",
        )

        # Create class headers
        source_class = ClassHeader.objects.create(course=course, term=source_term, section_id="A")
        target_class = ClassHeader.objects.create(course=course, term=target_term, section_id="A")

        # Create promotion batch
        promotion_batch = LanguageProgramPromotion.objects.create(
            source_term=source_term,
            target_term=target_term,
            program="EHSS",
            initiated_by=staff_user,
        )

        return {
            "student": student,
            "staff_user": staff_user,
            "source_class": source_class,
            "target_class": target_class,
            "promotion_batch": promotion_batch,
        }

    def test_create_student_promotion(self, setup_data):
        """Test creating a student promotion record."""
        promotion = LanguageStudentPromotion.objects.create(
            promotion_batch=setup_data["promotion_batch"],
            student=setup_data["student"],
            from_level="EHSS-05",
            to_level="EHSS-06",
            source_class=setup_data["source_class"],
            target_class=setup_data["target_class"],
            result=LanguageStudentPromotion.PromotionResult.PROMOTED,
            final_grade="B+",
        )

        assert promotion.student == setup_data["student"]
        assert promotion.from_level == "EHSS-05"
        assert promotion.to_level == "EHSS-06"
        assert promotion.result == LanguageStudentPromotion.PromotionResult.PROMOTED
        assert not promotion.has_level_skip_override

    def test_level_skip_promotion(self, setup_data):
        """Test promotion with level skip override."""
        promotion = LanguageStudentPromotion.objects.create(
            promotion_batch=setup_data["promotion_batch"],
            student=setup_data["student"],
            from_level="EHSS-05",
            to_level="EHSS-07",  # Skipping level 6
            source_class=setup_data["source_class"],
            target_class=setup_data["target_class"],
            result=LanguageStudentPromotion.PromotionResult.LEVEL_SKIPPED,
            has_level_skip_override=True,
            skip_reason="Re-test showed higher competency",
            skip_approved_by=setup_data["staff_user"],
        )

        assert promotion.has_level_skip_override
        assert promotion.skip_reason == "Re-test showed higher competency"
        assert promotion.skip_approved_by == setup_data["staff_user"]
        assert "(SKIP)" in str(promotion)

    def test_unique_constraint(self, setup_data):
        """Test unique constraint on promotion_batch and student."""
        LanguageStudentPromotion.objects.create(
            promotion_batch=setup_data["promotion_batch"],
            student=setup_data["student"],
            from_level="EHSS-05",
            to_level="EHSS-06",
            source_class=setup_data["source_class"],
            result=LanguageStudentPromotion.PromotionResult.PROMOTED,
        )

        # Should raise integrity error for duplicate
        with pytest.raises(Exception):  # IntegrityError
            LanguageStudentPromotion.objects.create(
                promotion_batch=setup_data["promotion_batch"],
                student=setup_data["student"],
                from_level="EHSS-05",
                to_level="EHSS-06",
                source_class=setup_data["source_class"],
                result=LanguageStudentPromotion.PromotionResult.PROMOTED,
            )


@pytest.mark.django_db
class TestLanguageLevelSkipRequest:
    """Test LanguageLevelSkipRequest model."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data."""
        # Create users
        student_user = User.objects.create_user(email="student@example.com", name="Test Student")
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff Member")
        manager_user = User.objects.create_user(email="manager@example.com", name="Manager User")

        student = StudentProfile.objects.create(user=student_user, student_number="S001", date_of_birth="2000-01-01")

        return {
            "student": student,
            "staff_user": staff_user,
            "manager_user": manager_user,
        }

    def test_create_skip_request(self, setup_data):
        """Test creating a level skip request."""
        skip_request = LanguageLevelSkipRequest.objects.create(
            student=setup_data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="Student scored 85% on EHSS-07 placement test",
            supporting_evidence="Placement test score: 85/100",
            requested_by=setup_data["staff_user"],
        )

        assert skip_request.student == setup_data["student"]
        assert skip_request.current_level == "EHSS-05"
        assert skip_request.target_level == "EHSS-07"
        assert skip_request.levels_skipped == 2
        assert skip_request.status == LanguageLevelSkipRequest.RequestStatus.PENDING

    def test_approve_skip_request(self, setup_data):
        """Test approving a skip request."""
        skip_request = LanguageLevelSkipRequest.objects.create(
            student=setup_data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="Student scored 85% on EHSS-07 placement test",
            requested_by=setup_data["staff_user"],
        )

        # Test approval
        review_notes = "Approved based on strong test performance"
        skip_request.approve(setup_data["manager_user"], review_notes)
        skip_request.refresh_from_db()

        assert skip_request.status == LanguageLevelSkipRequest.RequestStatus.APPROVED
        assert skip_request.reviewed_by == setup_data["manager_user"]
        assert skip_request.review_notes == review_notes
        assert skip_request.reviewed_at is not None

    def test_deny_skip_request(self, setup_data):
        """Test denying a skip request."""
        skip_request = LanguageLevelSkipRequest.objects.create(
            student=setup_data["student"],
            current_level="EHSS-05",
            target_level="EHSS-08",  # Too many levels
            program="EHSS",
            levels_skipped=3,
            reason_category=LanguageLevelSkipRequest.SkipReason.MISEVALUATION,
            detailed_reason="Claims initial placement was wrong",
            requested_by=setup_data["staff_user"],
        )

        # Test denial
        review_notes = "Insufficient evidence for 3-level skip"
        skip_request.deny(setup_data["manager_user"], review_notes)
        skip_request.refresh_from_db()

        assert skip_request.status == LanguageLevelSkipRequest.RequestStatus.DENIED
        assert skip_request.reviewed_by == setup_data["manager_user"]
        assert skip_request.review_notes == review_notes

    def test_mark_implemented(self, setup_data):
        """Test marking skip request as implemented."""
        skip_request = LanguageLevelSkipRequest.objects.create(
            student=setup_data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="Test reason",
            requested_by=setup_data["staff_user"],
        )

        # First approve it
        skip_request.approve(setup_data["manager_user"])

        # Then mark as implemented
        skip_request.mark_implemented(setup_data["staff_user"])
        skip_request.refresh_from_db()

        assert skip_request.status == LanguageLevelSkipRequest.RequestStatus.IMPLEMENTED
        assert skip_request.implemented_by == setup_data["staff_user"]
        assert skip_request.implemented_at is not None

    def test_string_representation(self, setup_data):
        """Test string representation of skip request."""
        skip_request = LanguageLevelSkipRequest.objects.create(
            student=setup_data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="Test reason",
            requested_by=setup_data["staff_user"],
        )

        expected = f"{setup_data['student']}: EHSS-05 → EHSS-07 (PENDING)"
        assert str(skip_request) == expected

    def test_skip_reason_choices(self):
        """Test that all skip reason choices are valid."""
        choices = LanguageLevelSkipRequest.SkipReason.choices
        assert len(choices) >= 6  # Should have at least 6 reason types

        # Check specific important reasons exist
        reason_values = [choice[0] for choice in choices]
        assert "RETEST_HIGHER" in reason_values
        assert "MISEVALUATION" in reason_values
        assert "TRANSFER_CREDIT" in reason_values

    def test_request_status_choices(self):
        """Test that all request status choices are valid."""
        choices = LanguageLevelSkipRequest.RequestStatus.choices
        assert len(choices) == 4  # PENDING, APPROVED, DENIED, IMPLEMENTED

        status_values = [choice[0] for choice in choices]
        assert "PENDING" in status_values
        assert "APPROVED" in status_values
        assert "DENIED" in status_values
        assert "IMPLEMENTED" in status_values
