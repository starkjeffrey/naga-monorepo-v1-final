"""Edge case and error handling tests for language promotion system.

Tests unusual scenarios, error conditions, data corruption recovery,
and boundary conditions to ensure robust system behavior.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.common.models import StudentActivityLog
from apps.curriculum.models import Course, Division, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.language.enums import LanguageLevel
from apps.language.models import LanguageLevelSkipRequest, LanguageProgramPromotion
from apps.language.services import LanguageLevelSkipService, LanguagePromotionService
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


@pytest.mark.django_db
class TestLanguagePromotionEdgeCases:
    """Test edge cases in language promotion system."""

    @pytest.fixture
    def setup_edge_case_data(self):
        """Set up test data for edge case testing."""
        # Create minimal required data
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff User")

        division = Division.objects.create(name="Language Division", short_name="LANG")

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
            "staff_user": staff_user,
            "division": division,
            "source_term": source_term,
            "target_term": target_term,
        }

    def test_promotion_with_no_eligible_students(self, setup_edge_case_data):
        """Test promotion analysis when no students are eligible."""
        data = setup_edge_case_data

        # Create a class with no students
        course = Course.objects.create(
            code="EHSS-05",
            title="Empty Class",
            short_title="Empty",
            division=data["division"],
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        ClassHeader.objects.create(course=course, term=data["source_term"], section_id="A")

        # Analyze promotion
        plan = LanguagePromotionService.analyze_promotion_eligibility(
            source_term=data["source_term"],
            target_term=data["target_term"],
            program="EHSS",
        )

        assert plan.estimated_student_count == 0
        assert plan.estimated_class_count == 0
        assert len(plan.eligible_students) == 0
        assert len(plan.classes_to_clone) == 0

    def test_promotion_with_all_failing_students(self, setup_edge_case_data):
        """Test promotion with students who all failed."""
        data = setup_edge_case_data

        # Create student and course
        User.objects.create_user(email="student@example.com", name="Student User")
        person = Person.objects.create(family_name="Test", personal_name="Student", date_of_birth="2000-01-01")
        student = StudentProfile.objects.create(person=person, student_id=1)

        course = Course.objects.create(
            code="EHSS-05",
            title="Test Class",
            short_title="Test",
            division=data["division"],
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        class_header = ClassHeader.objects.create(course=course, term=data["source_term"], section_id="A")

        # Create enrollment with failing grade
        ClassHeaderEnrollment.objects.create(
            student=student,
            class_header=class_header,
            enrolled_by=data["staff_user"],
            status=ClassHeaderEnrollment.EnrollmentStatus.FAILED,
            final_grade="F",
        )

        # Analyze promotion
        plan = LanguagePromotionService.analyze_promotion_eligibility(
            source_term=data["source_term"],
            target_term=data["target_term"],
            program="EHSS",
        )

        assert plan.estimated_student_count == 0
        assert len(plan.eligible_students) == 0

    def test_promotion_with_invalid_course_codes(self, setup_edge_case_data):
        """Test promotion with malformed course codes."""
        data = setup_edge_case_data

        # Create course with invalid code format
        course = Course.objects.create(
            code="INVALID_CODE",  # No level number
            title="Invalid Course",
            short_title="Invalid",
            division=data["division"],
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        ClassHeader.objects.create(course=course, term=data["source_term"], section_id="A")

        # Should handle gracefully
        plan = LanguagePromotionService.analyze_promotion_eligibility(
            source_term=data["source_term"],
            target_term=data["target_term"],
            program="EHSS",
        )

        # Should skip classes with invalid codes
        assert plan.estimated_student_count == 0
        assert plan.estimated_class_count == 0

    def test_promotion_execution_with_database_error(self, setup_edge_case_data):
        """Test promotion execution when database errors occur."""
        data = setup_edge_case_data

        # Create basic setup
        User.objects.create_user(email="student@example.com", name="Student User")
        person = Person.objects.create(family_name="Test", personal_name="Student", date_of_birth="2000-01-01")
        student = StudentProfile.objects.create(person=person, student_id=1)

        plan = LanguagePromotionService.PromotionPlan(
            source_term=data["source_term"],
            target_term=data["target_term"],
            program="EHSS",
            eligible_students=[(student, "EHSS-05", "EHSS-06")],
            classes_to_clone=[],
            estimated_student_count=1,
            estimated_class_count=0,
        )

        # Mock a database error during execution
        with patch("apps.enrollment.models.ClassHeaderEnrollment.objects.create") as mock_create:
            mock_create.side_effect = IntegrityError("Database constraint violation")

            result = LanguagePromotionService.execute_promotion(promotion_plan=plan, initiated_by=data["staff_user"])

            assert not result.success
            assert len(result.errors) > 0
            assert "Failed to promote student" in result.errors[0]

    def test_duplicate_promotion_batch_prevention(self, setup_edge_case_data):
        """Test prevention of duplicate promotion batches."""
        data = setup_edge_case_data

        # Create first promotion batch
        LanguageProgramPromotion.objects.create(
            source_term=data["source_term"],
            target_term=data["target_term"],
            program="EHSS",
            initiated_by=data["staff_user"],
        )

        with pytest.raises(IntegrityError):
            LanguageProgramPromotion.objects.create(
                source_term=data["source_term"],
                target_term=data["target_term"],
                program="EHSS",
                initiated_by=data["staff_user"],
            )

    def test_promotion_with_missing_next_level_course(self, setup_edge_case_data):
        """Test promotion when next level course doesn't exist."""
        data = setup_edge_case_data

        # Create student
        User.objects.create_user(email="student@example.com", name="Student User")
        person = Person.objects.create(family_name="Test", personal_name="Student", date_of_birth="2000-01-01")
        student = StudentProfile.objects.create(person=person, student_id=1)

        # Create EHSS-12 course (highest level, no next course)
        course = Course.objects.create(
            code="EHSS-12",
            title="EHSS Level 12",
            short_title="EHSS L12",
            division=data["division"],
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        class_header = ClassHeader.objects.create(course=course, term=data["source_term"], section_id="A")

        ClassHeaderEnrollment.objects.create(
            student=student,
            class_header=class_header,
            enrolled_by=data["staff_user"],
            status=ClassHeaderEnrollment.EnrollmentStatus.COMPLETED,
            final_grade="B",
        )

        # Should handle gracefully when next course doesn't exist
        cloned_class = LanguagePromotionService._clone_class_for_next_level(
            source_class=class_header,
            target_term=data["target_term"],
            program="EHSS",
        )

        assert cloned_class is None  # Should return None gracefully


@pytest.mark.django_db
class TestLanguageLevelSkipEdgeCases:
    """Test edge cases in language level skip system."""

    @pytest.fixture
    def setup_skip_edge_data(self):
        """Set up test data for skip edge case testing."""
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff User")
        manager_user = User.objects.create_user(email="manager@example.com", name="Manager User")

        User.objects.create_user(email="student@example.com", name="Student User")
        person = Person.objects.create(family_name="Test", personal_name="Student", date_of_birth="2000-01-01")
        student = StudentProfile.objects.create(person=person, student_id=1)

        return {
            "staff_user": staff_user,
            "manager_user": manager_user,
            "student": student,
        }

    def test_skip_request_with_extreme_level_jump(self, setup_skip_edge_data):
        """Test skip request validation with extreme level jumps."""
        # Test validation of 5-level skip (should fail)
        validation = LanguageLevelSkipService.validate_level_skip("EHSS-01", "EHSS-06", "EHSS")

        assert not validation["valid"]
        assert "Cannot skip more than 3 levels" in validation["message"]

    def test_skip_request_with_invalid_level_formats(self, setup_skip_edge_data):
        """Test skip request with malformed level strings."""
        # Test with invalid level formats
        test_cases = [
            ("INVALID", "EHSS-05", "Invalid current level"),
            ("EHSS-05", "INVALID", "Invalid target level"),
            ("", "EHSS-05", "Invalid current level"),
            ("EHSS-05", "", "Invalid target level"),
        ]

        for current, target, expected_error in test_cases:
            validation = LanguageLevelSkipService.validate_level_skip(current, target, "EHSS")
            assert not validation["valid"]
            assert expected_error in validation["message"]

    def test_skip_request_with_backwards_progression(self, setup_skip_edge_data):
        """Test skip request going backwards (should fail)."""
        validation = LanguageLevelSkipService.validate_level_skip("EHSS-07", "EHSS-05", "EHSS")

        assert not validation["valid"]
        assert "must be higher than current level" in validation["message"]

    def test_skip_request_approval_transaction_rollback(self, setup_skip_edge_data):
        """Test that skip request approval rolls back on audit log failure."""
        data = setup_skip_edge_data

        skip_request = LanguageLevelSkipRequest.objects.create(
            student=data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="Test",
            requested_by=data["staff_user"],
        )

        # Mock audit log to fail
        with patch("apps.language.services.SystemAuditLog.log_override") as mock_log:
            mock_log.side_effect = Exception("Audit log failed")

            result = LanguageLevelSkipService.approve_skip_request(
                skip_request=skip_request,
                approved_by=data["manager_user"],
            )

            assert not result
            skip_request.refresh_from_db()
            # Should still be pending due to transaction rollback
            assert skip_request.status == LanguageLevelSkipRequest.RequestStatus.PENDING

    def test_implement_skip_with_enrollment_failure(self, setup_skip_edge_data):
        """Test implementing skip when enrollment creation fails."""
        data = setup_skip_edge_data

        # Create approved skip request
        skip_request = LanguageLevelSkipRequest.objects.create(
            student=data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="Test",
            requested_by=data["staff_user"],
            status=LanguageLevelSkipRequest.RequestStatus.APPROVED,
        )

        # Create mock class that will cause enrollment to fail
        mock_class = MagicMock()
        mock_class.id = 999

        # Mock enrollment creation to fail
        with patch("apps.enrollment.models.ClassHeaderEnrollment.objects.create") as mock_create:
            mock_create.side_effect = IntegrityError("Enrollment failed")

            enrollment = LanguageLevelSkipService.implement_level_skip(
                skip_request=skip_request,
                target_class=mock_class,
                implemented_by=data["staff_user"],
            )

            assert enrollment is None
            skip_request.refresh_from_db()
            # Status should remain approved, not implemented
            assert skip_request.status == LanguageLevelSkipRequest.RequestStatus.APPROVED

    def test_multiple_skip_requests_for_same_student(self, setup_skip_edge_data):
        """Test handling multiple skip requests for the same student."""
        data = setup_skip_edge_data

        # Create multiple skip requests for same student
        skip1 = LanguageLevelSkipRequest.objects.create(
            student=data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="First request",
            requested_by=data["staff_user"],
        )

        skip2 = LanguageLevelSkipRequest.objects.create(
            student=data["student"],
            current_level="EHSS-07",
            target_level="EHSS-09",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.DEMONSTRATED_COMPETENCY,
            detailed_reason="Second request",
            requested_by=data["staff_user"],
        )

        # Both should be allowed (different levels)
        assert skip1.id != skip2.id

        # Get student history
        history = LanguageLevelSkipService.get_student_skip_history(data["student"])
        assert len(history) == 2


@pytest.mark.django_db
class TestLanguageLevelEnumEdgeCases:
    """Test edge cases in language level enumeration."""

    def test_equivalency_with_non_existent_program(self):
        """Test equivalency checking with invalid programs."""
        ehss_5 = LanguageLevel.EHSS_5

        # Should return empty list for non-existent program
        equivalents = LanguageLevel.get_equivalent_levels(ehss_5, "NONEXISTENT")
        assert len(equivalents) == 0

    def test_level_progression_at_boundaries(self):
        """Test level progression at program boundaries."""
        # Test highest EHSS level
        ehss_12 = LanguageLevel.EHSS_12
        next_level = LanguageLevel.get_next_level(ehss_12)
        assert next_level is None

        # Test lowest IEAP level
        ieap_pre = LanguageLevel.IEAP_PRE
        next_level = LanguageLevel.get_next_level(ieap_pre)
        assert next_level == LanguageLevel.IEAP_BEG

    def test_transfer_with_boundary_conditions(self):
        """Test transfer capabilities at program boundaries."""
        # Test transfer from highest IEAP to EHSS
        ieap_4 = LanguageLevel.IEAP_4

        # Should be able to transfer to EHSS 11-12
        assert LanguageLevel.can_transfer_to(ieap_4, "EHSS", 11)
        assert LanguageLevel.can_transfer_to(ieap_4, "EHSS", 12)

        # Should not be able to transfer beyond program bounds
        assert not LanguageLevel.can_transfer_to(ieap_4, "EHSS", 13)

    def test_course_code_generation_edge_cases(self):
        """Test course code generation for edge cases."""
        # Test negative level numbers
        ieap_pre = LanguageLevel.IEAP_PRE
        code = LanguageLevel.get_course_code_for_level(ieap_pre)
        assert code == "IEAP-PRE"

        ieap_beg = LanguageLevel.IEAP_BEG
        code = LanguageLevel.get_course_code_for_level(ieap_beg)
        assert code == "IEAP-PRE"  # Both negative levels become "PRE"

    def test_equivalency_rules_completeness(self):
        """Test that equivalency rules are comprehensive and symmetric."""
        # Test that EHSS-GESL equivalency is complete
        for level_num in range(1, 13):
            ehss_level = LanguageLevel.get_level_by_program_and_num("EHSS", level_num)
            gesl_level = LanguageLevel.get_level_by_program_and_num("GESL", level_num)

            # Should be equivalent both ways
            ehss_to_gesl = LanguageLevel.get_equivalent_levels(ehss_level, "GESL")
            gesl_to_ehss = LanguageLevel.get_equivalent_levels(gesl_level, "EHSS")

            assert len(ehss_to_gesl) == 1
            assert len(gesl_to_ehss) == 1
            assert ehss_to_gesl[0].level_num == level_num
            assert gesl_to_ehss[0].level_num == level_num


@pytest.mark.django_db
class TestSystemRecoveryScenarios:
    """Test system recovery from various failure scenarios."""

    def test_audit_log_recovery_from_missing_references(self):
        """Test audit log behavior when referenced objects are deleted."""
        # Create user and student
        user = User.objects.create_user(email="test@example.com", name="Test User")
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff User")

        student = StudentProfile.objects.create(user=user, student_number="S001", date_of_birth="2000-01-01")

        # Create audit log entry
        log_entry = StudentActivityLog.log_student_activity(
            student=student,
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="Test enrollment",
            performed_by=staff_user,
            student_number="S001",
            student_name="Test Student",
        )

        # Delete the student (simulating data corruption or deletion)
        student.delete()

        # Audit log should still be accessible with preserved data
        log_entry.refresh_from_db()
        assert log_entry.student is None  # FK is gone
        assert log_entry.student_number == "S001"  # But data is preserved
        assert log_entry.student_name == "Test Student"

        # Search should still work
        results = StudentActivityLog.search_student_activities(student_number="S001")
        assert len(results) == 1

    def test_promotion_batch_recovery_from_partial_failure(self):
        """Test recovery when promotion batch partially completes."""
        # Create test data
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff User")

        source_term = Term.objects.create(
            name="Source Term",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        target_term = Term.objects.create(
            name="Target Term",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-04-01",
            end_date="2024-06-30",
        )

        # Create promotion batch that fails partway through
        promotion_batch = LanguageProgramPromotion.objects.create(
            source_term=source_term,
            target_term=target_term,
            program="EHSS",
            initiated_by=staff_user,
            status=LanguageProgramPromotion.PromotionStatus.IN_PROGRESS,
        )

        # Simulate partial completion then failure
        promotion_batch.students_promoted_count = 5
        promotion_batch.classes_cloned_count = 2
        promotion_batch.mark_failed("System error during batch processing")

        promotion_batch.refresh_from_db()
        assert promotion_batch.status == LanguageProgramPromotion.PromotionStatus.FAILED
        assert promotion_batch.students_promoted_count == 5  # Preserved
        assert promotion_batch.classes_cloned_count == 2  # Preserved
        assert "System error" in promotion_batch.notes

    def test_concurrent_promotion_prevention(self):
        """Test prevention of concurrent promotions for same term/program."""
        # For now, test the database constraint

        staff_user = User.objects.create_user(email="staff@example.com", name="Staff User")

        source_term = Term.objects.create(
            name="Source Term",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        target_term = Term.objects.create(
            name="Target Term",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-04-01",
            end_date="2024-06-30",
        )

        # First promotion should succeed
        LanguageProgramPromotion.objects.create(
            source_term=source_term,
            target_term=target_term,
            program="EHSS",
            initiated_by=staff_user,
        )

        # Second concurrent promotion should fail
        with pytest.raises(IntegrityError):
            LanguageProgramPromotion.objects.create(
                source_term=source_term,
                target_term=target_term,
                program="EHSS",
                initiated_by=staff_user,
            )
