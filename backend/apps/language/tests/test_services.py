"""Test cases for language promotion and level skip services.

Tests the business logic for automatic promotions, class cloning,
and level skip request processing with comprehensive edge cases.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.common.models import StudentActivityLog
from apps.curriculum.models import Course, Cycle, Division, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.language.models import (
    LanguageLevelSkipRequest,
    LanguageProgramPromotion,
    LanguageStudentPromotion,
)
from apps.language.services import (
    LanguageLevelSkipService,
    LanguagePromotionService,
    PromotionPlan,
    PromotionResult,
)
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


@pytest.mark.django_db
class TestLanguagePromotionService:
    """Test LanguagePromotionService business logic."""

    @pytest.fixture
    def setup_promotion_data(self):
        """Set up comprehensive test data for promotion testing."""
        # Create users
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff Member")

        # Create students
        students = []
        for i in range(5):
            User.objects.create_user(email=f"student{i}@example.com", name=f"Student{i} Test")
            person = Person.objects.create(
                family_name=f"Student{i}",
                personal_name="Test",
                date_of_birth="2000-01-01",
            )
            student = StudentProfile.objects.create(person=person, student_id=i + 1)
            students.append(student)

        # Create division, cycle, and major
        division = Division.objects.create(name="Language Division", short_name="LANG")
        Cycle.objects.create(division=division, name="Language Programs", short_name="LANG")

        # Create courses for EHSS levels 5 and 6
        course_l5 = Course.objects.create(
            code="EHSS-05",
            title="English for High School Level 5",
            short_title="EHSS L5",
            division=division,
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )
        course_l6 = Course.objects.create(
            code="EHSS-06",
            title="English for High School Level 6",
            short_title="EHSS L6",
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

        # Create class in source term
        source_class = ClassHeader.objects.create(course=course_l5, term=source_term, section_id="A")

        # Create enrollments for students
        enrollments = []
        passing_grades = ["B+", "A-", "B", "C+", "D+"]
        for i, student in enumerate(students):
            enrollment = ClassHeaderEnrollment.objects.create(
                student=student,
                class_header=source_class,
                enrolled_by=staff_user,
                status=ClassHeaderEnrollment.EnrollmentStatus.COMPLETED,
                final_grade=passing_grades[i],
            )
            enrollments.append(enrollment)

        return {
            "staff_user": staff_user,
            "students": students,
            "source_term": source_term,
            "target_term": target_term,
            "source_class": source_class,
            "course_l5": course_l5,
            "course_l6": course_l6,
            "enrollments": enrollments,
        }

    def test_analyze_promotion_eligibility(self, setup_promotion_data):
        """Test analyzing which students are eligible for promotion."""
        data = setup_promotion_data

        # Analyze promotion eligibility
        plan = LanguagePromotionService.analyze_promotion_eligibility(
            source_term=data["source_term"],
            target_term=data["target_term"],
            program="EHSS",
        )

        assert isinstance(plan, PromotionPlan)
        assert plan.source_term == data["source_term"]
        assert plan.target_term == data["target_term"]
        assert plan.program == "EHSS"
        assert plan.estimated_student_count == 5  # All 5 students have passing grades
        assert plan.estimated_class_count == 1  # One class to clone
        assert len(plan.eligible_students) == 5
        assert len(plan.classes_to_clone) == 1

        # Check student promotion details
        for student, from_level, to_level in plan.eligible_students:
            assert from_level == "EHSS-05"
            assert to_level == "EHSS-06"
            assert student in data["students"]

    def test_analyze_promotion_with_failing_students(self, setup_promotion_data):
        """Test promotion analysis with some failing students."""
        data = setup_promotion_data

        # Mark one student as failed
        failing_enrollment = data["enrollments"][0]
        failing_enrollment.final_grade = "F"
        failing_enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.FAILED
        failing_enrollment.save()

        # Mark one student as withdrawn
        withdrawn_enrollment = data["enrollments"][1]
        withdrawn_enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN
        withdrawn_enrollment.save()

        plan = LanguagePromotionService.analyze_promotion_eligibility(
            source_term=data["source_term"],
            target_term=data["target_term"],
            program="EHSS",
        )

        # Should only have 3 eligible students (5 - 1 failed - 1 withdrawn)
        assert plan.estimated_student_count == 3
        assert len(plan.eligible_students) == 3

    @patch("apps.language.services.LanguagePromotionService._clone_class_for_next_level")
    def test_execute_promotion_success(self, mock_clone_class, setup_promotion_data):
        """Test successful execution of promotion."""
        data = setup_promotion_data

        # Mock the class cloning to return a new class
        mock_target_class = MagicMock()
        mock_target_class.id = 999
        mock_clone_class.return_value = mock_target_class

        # Create promotion plan
        plan = LanguagePromotionService.analyze_promotion_eligibility(
            source_term=data["source_term"],
            target_term=data["target_term"],
            program="EHSS",
        )

        # Execute promotion
        result = LanguagePromotionService.execute_promotion(
            promotion_plan=plan,
            initiated_by=data["staff_user"],
            notes="Test promotion execution",
        )

        assert isinstance(result, PromotionResult)
        assert result.success
        assert result.students_promoted == 5
        assert result.classes_cloned == 1
        assert result.promotion_batch is not None

        # Check promotion batch was created
        promotion_batch = result.promotion_batch
        assert promotion_batch.source_term == data["source_term"]
        assert promotion_batch.target_term == data["target_term"]
        assert promotion_batch.program == "EHSS"
        assert promotion_batch.status == LanguageProgramPromotion.PromotionStatus.COMPLETED

        # Check student promotion records
        student_promotions = LanguageStudentPromotion.objects.filter(promotion_batch=promotion_batch)
        assert student_promotions.count() == 5

        # Check audit logs were created
        audit_logs = StudentActivityLog.objects.filter(
            activity_type=StudentActivityLog.ActivityType.LANGUAGE_PROMOTION,
        )
        assert audit_logs.count() == 5

    def test_extract_level_from_course_code(self):
        """Test level extraction from course codes."""
        service = LanguagePromotionService

        assert service._extract_level_from_course_code("EHSS-05") == 5
        assert service._extract_level_from_course_code("GESL-12") == 12
        assert service._extract_level_from_course_code("IEAP-01") == 1

        # Invalid formats
        assert service._extract_level_from_course_code("EHSS05") is None
        assert service._extract_level_from_course_code("INVALID") is None
        assert service._extract_level_from_course_code("") is None

    def test_is_student_eligible_for_promotion(self, setup_promotion_data):
        """Test student eligibility checking."""
        data = setup_promotion_data
        service = LanguagePromotionService

        # Test completed with passing grade
        passing_enrollment = data["enrollments"][0]
        assert service._is_student_eligible_for_promotion(passing_enrollment)

        # Test still enrolled (assumed passing)
        passing_enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        passing_enrollment.save()
        assert service._is_student_eligible_for_promotion(passing_enrollment)

        # Test failed
        passing_enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.FAILED
        passing_enrollment.final_grade = "F"
        passing_enrollment.save()
        assert not service._is_student_eligible_for_promotion(passing_enrollment)

        # Test withdrawn
        passing_enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN
        passing_enrollment.save()
        assert not service._is_student_eligible_for_promotion(passing_enrollment)

    def test_clone_class_for_next_level(self, setup_promotion_data):
        """Test class cloning for next level."""
        data = setup_promotion_data

        # This will fail because EHSS-06 course doesn't exist in our test data
        # but we can test the logic handles it gracefully
        cloned_class = LanguagePromotionService._clone_class_for_next_level(
            source_class=data["source_class"],
            target_term=data["target_term"],
            program="EHSS",
        )

        # Should return None because EHSS-06 course doesn't exist
        assert cloned_class is None

    def test_clone_class_with_existing_next_course(self, setup_promotion_data):
        """Test class cloning when next level course exists."""
        data = setup_promotion_data

        # Now test with existing next course
        cloned_class = LanguagePromotionService._clone_class_for_next_level(
            source_class=data["source_class"],
            target_term=data["target_term"],
            program="EHSS",
        )

        # Should succeed because EHSS-06 exists
        assert cloned_class is not None
        assert cloned_class.course == data["course_l6"]
        assert cloned_class.term == data["target_term"]
        assert cloned_class.section == data["source_class"].section

    def test_get_promotion_history(self, setup_promotion_data):
        """Test getting promotion history."""
        data = setup_promotion_data

        # Create some promotion batches
        for _i in range(3):
            LanguageProgramPromotion.objects.create(
                source_term=data["source_term"],
                target_term=data["target_term"],
                program="EHSS",
                initiated_by=data["staff_user"],
                status=LanguageProgramPromotion.PromotionStatus.COMPLETED,
            )

        history = LanguagePromotionService.get_promotion_history("EHSS", limit=5)
        assert len(history) == 3
        assert all(promo.program == "EHSS" for promo in history)

    def test_get_failed_students_for_workflow(self, setup_promotion_data):
        """Test getting failed students for workflow follow-up."""
        data = setup_promotion_data

        # Create promotion batch
        promotion_batch = LanguageProgramPromotion.objects.create(
            source_term=data["source_term"],
            target_term=data["target_term"],
            program="EHSS",
            initiated_by=data["staff_user"],
        )

        # Create some failed student promotions
        for i, student in enumerate(data["students"][:2]):
            result = (
                LanguageStudentPromotion.PromotionResult.FAILED_COURSE
                if i == 0
                else LanguageStudentPromotion.PromotionResult.NO_SHOW
            )
            LanguageStudentPromotion.objects.create(
                promotion_batch=promotion_batch,
                student=student,
                from_level="EHSS-05",
                to_level="EHSS-06",
                source_class=data["source_class"],
                result=result,
            )

        failed_students = LanguagePromotionService.get_failed_students_for_workflow(promotion_batch)
        assert len(failed_students) == 2
        assert all(
            sp.result
            in [
                LanguageStudentPromotion.PromotionResult.FAILED_COURSE,
                LanguageStudentPromotion.PromotionResult.NO_SHOW,
            ]
            for sp in failed_students
        )


@pytest.mark.django_db
class TestLanguageLevelSkipService:
    """Test LanguageLevelSkipService business logic."""

    @pytest.fixture
    def setup_skip_data(self):
        """Set up test data for level skip testing."""
        # Create users
        User.objects.create_user(email="student@example.com", name="Test Student")
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff Member")
        manager_user = User.objects.create_user(email="manager@example.com", name="Manager User")

        person = Person.objects.create(family_name="Test", personal_name="Student", date_of_birth="2000-01-01")
        student = StudentProfile.objects.create(person=person, student_id=1)

        # Create division and course
        division = Division.objects.create(name="Language Division", short_name="LANG")

        target_course = Course.objects.create(
            code="EHSS-07",
            title="English for High School Level 7",
            short_title="EHSS L7",
            division=division,
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        # Create term and class
        term = Term.objects.create(
            name="ENG A 2024-2",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-04-01",
            end_date="2024-06-30",
        )

        target_class = ClassHeader.objects.create(course=target_course, term=term, section_id="A")

        return {
            "student": student,
            "staff_user": staff_user,
            "manager_user": manager_user,
            "target_class": target_class,
        }

    def test_create_skip_request(self, setup_skip_data):
        """Test creating a level skip request."""
        data = setup_skip_data

        skip_request = LanguageLevelSkipService.create_skip_request(
            student=data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="Student scored 90% on EHSS-07 placement test",
            supporting_evidence="Placement test results attached",
            requested_by=data["staff_user"],
        )

        assert skip_request.student == data["student"]
        assert skip_request.current_level == "EHSS-05"
        assert skip_request.target_level == "EHSS-07"
        assert skip_request.levels_skipped == 2
        assert skip_request.status == LanguageLevelSkipRequest.RequestStatus.PENDING

    def test_extract_level_num(self):
        """Test level number extraction."""
        service = LanguageLevelSkipService

        assert service._extract_level_num("EHSS-05") == 5
        assert service._extract_level_num("GESL-12") == 12
        assert service._extract_level_num("INVALID") is None
        assert service._extract_level_num("") is None

    @patch("apps.language.services.SystemAuditLog.log_override")
    def test_approve_skip_request(self, mock_log_override, setup_skip_data):
        """Test approving a skip request with audit logging."""
        data = setup_skip_data

        # Create skip request
        skip_request = LanguageLevelSkipRequest.objects.create(
            student=data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="High test scores",
            requested_by=data["staff_user"],
        )

        # Approve the request
        result = LanguageLevelSkipService.approve_skip_request(
            skip_request=skip_request,
            approved_by=data["manager_user"],
            review_notes="Strong test performance justifies skip",
        )

        assert result is True
        skip_request.refresh_from_db()
        assert skip_request.status == LanguageLevelSkipRequest.RequestStatus.APPROVED
        assert skip_request.reviewed_by == data["manager_user"]
        assert skip_request.review_notes == "Strong test performance justifies skip"

        # Check audit log was called
        mock_log_override.assert_called_once()

    @patch("apps.language.services.StudentActivityLog.log_student_activity")
    @patch("apps.language.services.SystemAuditLog.log_override")
    def test_implement_level_skip(self, mock_sys_log, mock_student_log, setup_skip_data):
        """Test implementing an approved level skip."""
        data = setup_skip_data

        # Create and approve skip request
        skip_request = LanguageLevelSkipRequest.objects.create(
            student=data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="High test scores",
            requested_by=data["staff_user"],
            status=LanguageLevelSkipRequest.RequestStatus.APPROVED,
        )

        # Implement the skip
        enrollment = LanguageLevelSkipService.implement_level_skip(
            skip_request=skip_request,
            target_class=data["target_class"],
            implemented_by=data["staff_user"],
        )

        assert enrollment is not None
        assert enrollment.student == data["student"]
        assert enrollment.class_header == data["target_class"]
        assert enrollment.status == ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        assert "Level skip implementation" in enrollment.notes

        # Check skip request was marked as implemented
        skip_request.refresh_from_db()
        assert skip_request.status == LanguageLevelSkipRequest.RequestStatus.IMPLEMENTED
        assert skip_request.implemented_by == data["staff_user"]
        assert skip_request.new_enrollment == enrollment

        # Check audit logs were called
        mock_sys_log.assert_called_once()

    def test_implement_unapproved_skip_request(self, setup_skip_data):
        """Test that unapproved skip requests cannot be implemented."""
        data = setup_skip_data

        # Create pending skip request
        skip_request = LanguageLevelSkipRequest.objects.create(
            student=data["student"],
            current_level="EHSS-05",
            target_level="EHSS-07",
            program="EHSS",
            levels_skipped=2,
            reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
            detailed_reason="High test scores",
            requested_by=data["staff_user"],
            status=LanguageLevelSkipRequest.RequestStatus.PENDING,
        )

        # Should return None for unapproved request
        enrollment = LanguageLevelSkipService.implement_level_skip(
            skip_request=skip_request,
            target_class=data["target_class"],
            implemented_by=data["staff_user"],
        )

        assert enrollment is None

    def test_validate_level_skip(self):
        """Test level skip validation logic."""
        service = LanguageLevelSkipService

        # Valid skip
        result = service.validate_level_skip("EHSS-05", "EHSS-07", "EHSS")
        assert result["valid"] is True
        assert result["levels_skipped"] == 2

        # Invalid current level
        result = service.validate_level_skip("EHSS-99", "EHSS-07", "EHSS")
        assert result["valid"] is False
        assert "Invalid current level" in result["message"]

        # Invalid target level
        result = service.validate_level_skip("EHSS-05", "EHSS-99", "EHSS")
        assert result["valid"] is False
        assert "Invalid target level" in result["message"]

        # Target level not higher than current
        result = service.validate_level_skip("EHSS-07", "EHSS-05", "EHSS")
        assert result["valid"] is False
        assert "must be higher than current level" in result["message"]

        # Too many levels skipped (max 3)
        result = service.validate_level_skip("EHSS-01", "EHSS-05", "EHSS")
        assert result["valid"] is False
        assert "Cannot skip more than 3 levels" in result["message"]

    def test_get_pending_skip_requests(self, setup_skip_data):
        """Test getting pending skip requests."""
        data = setup_skip_data

        # Create some skip requests
        for i in range(3):
            LanguageLevelSkipRequest.objects.create(
                student=data["student"],
                current_level=f"EHSS-0{i + 1}",
                target_level=f"EHSS-0{i + 3}",
                program="EHSS",
                levels_skipped=2,
                reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
                detailed_reason=f"Test reason {i}",
                requested_by=data["staff_user"],
            )

        pending_requests = LanguageLevelSkipService.get_pending_skip_requests("EHSS")
        assert len(pending_requests) == 3
        assert all(req.status == LanguageLevelSkipRequest.RequestStatus.PENDING for req in pending_requests)

    def test_get_student_skip_history(self, setup_skip_data):
        """Test getting student skip history."""
        data = setup_skip_data

        # Create skip requests with different statuses
        statuses = [
            LanguageLevelSkipRequest.RequestStatus.PENDING,
            LanguageLevelSkipRequest.RequestStatus.APPROVED,
            LanguageLevelSkipRequest.RequestStatus.IMPLEMENTED,
        ]

        for i, status in enumerate(statuses):
            LanguageLevelSkipRequest.objects.create(
                student=data["student"],
                current_level=f"EHSS-0{i + 1}",
                target_level=f"EHSS-0{i + 3}",
                program="EHSS",
                levels_skipped=2,
                reason_category=LanguageLevelSkipRequest.SkipReason.RETEST_HIGHER,
                detailed_reason=f"Test reason {i}",
                requested_by=data["staff_user"],
                status=status,
            )

        history = LanguageLevelSkipService.get_student_skip_history(data["student"])
        assert len(history) == 3
        assert all(req.student == data["student"] for req in history)
