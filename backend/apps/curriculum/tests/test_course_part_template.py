"""Tests for CoursePartTemplate model and functionality.

Tests the curriculum template system including validation, template creation,
and integration with the language promotion system.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.curriculum.models import Course, CoursePartTemplate, Division, Textbook

User = get_user_model()


@pytest.mark.django_db
class TestCoursePartTemplate:
    """Test CoursePartTemplate model and validation."""

    @pytest.fixture
    def setup_curriculum_data(self):
        """Set up test data for curriculum template testing."""
        # Create division
        division = Division.objects.create(name="Language Division", short_name="LANG")

        # Create courses
        ehss_05 = Course.objects.create(
            code="EHSS-05",
            title="English for High School Level 5",
            short_title="EHSS L5",
            division=division,
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        ehss_07 = Course.objects.create(
            code="EHSS-07",
            title="English for High School Level 7",
            short_title="EHSS L7",
            division=division,
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        ieap_3 = Course.objects.create(
            code="IEAP-03",
            title="IEAP Level 3",
            short_title="IEAP L3",
            division=division,
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        # Create textbooks
        ventures_4_student = Textbook.objects.create(
            title="Ventures 4 Student Book",
            author="Gretchen Bitterlin",
            isbn="978-1-108-45678-9",
        )

        ventures_4_workbook = Textbook.objects.create(
            title="Ventures 4 Workbook",
            author="Gretchen Bitterlin",
            isbn="978-1-108-45679-6",
        )

        return {
            "division": division,
            "ehss_05": ehss_05,
            "ehss_07": ehss_07,
            "ieap_3": ieap_3,
            "ventures_4_student": ventures_4_student,
            "ventures_4_workbook": ventures_4_workbook,
        }

    def test_create_simple_course_template(self, setup_curriculum_data):
        """Test creating a simple single-session course template."""
        data = setup_curriculum_data

        grammar_template = CoursePartTemplate.objects.create(
            course=data["ehss_05"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("0.800"),
        )
        grammar_template.textbooks.set([data["ventures_4_student"]])

        computer_template = CoursePartTemplate.objects.create(
            course=data["ehss_05"],
            part_type="COMPUTER",
            part_code="B",
            name="Computer Lab",
            session_number=1,
            meeting_days="TUE,THU",
            grade_weight=Decimal("0.200"),
        )
        computer_template.textbooks.set([data["ventures_4_student"]])

        templates = CoursePartTemplate.get_templates_for_course(data["ehss_05"])
        assert templates.count() == 2
        assert templates.filter(part_type="GRAMMAR").exists()
        assert templates.filter(part_type="COMPUTER").exists()

        # Verify weights sum to 1.0
        total_weight = sum(t.grade_weight for t in templates)
        assert abs(total_weight - Decimal("1.000")) < Decimal("0.001")

    def test_create_multi_part_course_template(self, setup_curriculum_data):
        """Test creating EHSS-07 template with 3 parts."""
        data = setup_curriculum_data

        templates_data = [
            {
                "part_type": "GRAMMAR",
                "part_code": "A",
                "name": "Grammar",
                "meeting_days": "MON,WED",
                "grade_weight": Decimal("0.500"),
                "textbooks": [data["ventures_4_student"], data["ventures_4_workbook"]],
            },
            {
                "part_type": "COMPUTER",
                "part_code": "B",
                "name": "Computer Lab",
                "meeting_days": "TUE,THU",
                "grade_weight": Decimal("0.300"),
                "textbooks": [data["ventures_4_student"]],
            },
            {
                "part_type": "CONVERSATION",
                "part_code": "C",
                "name": "Conversation",
                "meeting_days": "FRI",
                "grade_weight": Decimal("0.200"),
                "textbooks": [data["ventures_4_workbook"]],
            },
        ]

        for template_data in templates_data:
            template = CoursePartTemplate.objects.create(
                course=data["ehss_07"],
                part_type=template_data["part_type"],
                part_code=template_data["part_code"],
                name=template_data["name"],
                session_number=1,
                meeting_days=template_data["meeting_days"],
                grade_weight=template_data["grade_weight"],
            )
            template.textbooks.set(template_data["textbooks"])

        # Verify all parts created
        templates = CoursePartTemplate.get_templates_for_course(data["ehss_07"])
        assert templates.count() == 3

        # Verify specific parts exist
        grammar = templates.get(part_type="GRAMMAR")
        assert grammar.meeting_days == "MON,WED"
        assert grammar.textbooks.count() == 2

        conversation = templates.get(part_type="CONVERSATION")
        assert conversation.meeting_days == "FRI"
        assert conversation.textbooks.count() == 1

    def test_create_ieap_two_session_template(self, setup_curriculum_data):
        """Test creating IEAP template with 2 sessions."""
        data = setup_curriculum_data

        CoursePartTemplate.objects.create(
            course=data["ieap_3"],
            part_type="MAIN",
            part_code="A",
            name="Session A",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),  # Full weight within session
        )

        CoursePartTemplate.objects.create(
            course=data["ieap_3"],
            part_type="MAIN",
            part_code="B",
            name="Session B",
            session_number=2,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),  # Full weight within session
        )

        templates = CoursePartTemplate.get_templates_for_course(data["ieap_3"])
        assert templates.count() == 2

        # Verify session separation
        session_1_templates = templates.filter(session_number=1)
        session_2_templates = templates.filter(session_number=2)
        assert session_1_templates.count() == 1
        assert session_2_templates.count() == 1

    def test_weight_validation_within_session(self, setup_curriculum_data):
        """Test that weights within a session must sum to 1.0."""
        data = setup_curriculum_data

        # Create first part with 0.6 weight
        CoursePartTemplate.objects.create(
            course=data["ehss_05"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("0.600"),
        )

        # Try to create second part that would make total > 1.0
        with pytest.raises(ValidationError) as exc_info:
            template = CoursePartTemplate(
                course=data["ehss_05"],
                part_type="COMPUTER",
                part_code="B",
                name="Computer Lab",
                session_number=1,
                meeting_days="TUE,THU",
                grade_weight=Decimal("0.500"),  # 0.6 + 0.5 = 1.1 > 1.0
            )
            template.clean()

        assert "must sum to 1.000" in str(exc_info.value)

    def test_weight_validation_allows_valid_total(self, setup_curriculum_data):
        """Test that weights summing to exactly 1.0 are valid."""
        data = setup_curriculum_data

        # Create first part
        CoursePartTemplate.objects.create(
            course=data["ehss_05"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("0.700"),
        )

        # Create second part that makes total exactly 1.0
        template = CoursePartTemplate(
            course=data["ehss_05"],
            part_type="COMPUTER",
            part_code="B",
            name="Computer Lab",
            session_number=1,
            meeting_days="TUE,THU",
            grade_weight=Decimal("0.300"),  # 0.7 + 0.3 = 1.0
        )

        # Should not raise validation error
        template.clean()
        template.save()

        templates = CoursePartTemplate.get_templates_for_course(data["ehss_05"])
        assert templates.count() == 2

    def test_meeting_days_validation(self, setup_curriculum_data):
        """Test validation of meeting days format."""
        data = setup_curriculum_data

        # Valid meeting days should work
        template = CoursePartTemplate(
            course=data["ehss_05"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )
        template.clean()  # Should not raise

        # Invalid meeting days should fail
        invalid_template = CoursePartTemplate(
            course=data["ehss_05"],
            part_type="COMPUTER",
            part_code="B",
            name="Computer Lab",
            session_number=1,
            meeting_days="MONDAY,TUESDAY",  # Invalid format
            grade_weight=Decimal("1.000"),
        )

        with pytest.raises(ValidationError) as exc_info:
            invalid_template.clean()

        assert "Invalid days" in str(exc_info.value)

    def test_course_template_completeness_validation(self, setup_curriculum_data):
        """Test validation of complete course templates."""
        data = setup_curriculum_data

        validation = CoursePartTemplate.validate_course_template_completeness(data["ehss_05"])
        assert not validation["valid"]
        assert "no part templates defined" in validation["errors"][0]

        CoursePartTemplate.objects.create(
            course=data["ehss_05"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )

        validation = CoursePartTemplate.validate_course_template_completeness(data["ehss_05"])
        assert validation["valid"]
        assert len(validation["errors"]) == 0

    def test_ieap_course_template_validation(self, setup_curriculum_data):
        """Test validation specific to IEAP courses."""
        data = setup_curriculum_data

        # IEAP course with only 1 session should be invalid
        CoursePartTemplate.objects.create(
            course=data["ieap_3"],
            part_type="MAIN",
            part_code="A",
            name="Session A",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )

        validation = CoursePartTemplate.validate_course_template_completeness(data["ieap_3"])
        assert not validation["valid"]
        assert "should have exactly 2 sessions" in validation["errors"][0]

        # Add second session
        CoursePartTemplate.objects.create(
            course=data["ieap_3"],
            part_type="MAIN",
            part_code="B",
            name="Session B",
            session_number=2,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )

        # Now should be valid
        validation = CoursePartTemplate.validate_course_template_completeness(data["ieap_3"])
        assert validation["valid"]

    def test_template_string_representation(self, setup_curriculum_data):
        """Test string representation of templates."""
        data = setup_curriculum_data

        template = CoursePartTemplate.objects.create(
            course=data["ehss_05"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )

        assert str(template) == "EHSS-05 - Grammar (A)"
        assert template.full_name == "EHSS-05: Grammar"

        ieap_template = CoursePartTemplate.objects.create(
            course=data["ieap_3"],
            part_type="MAIN",
            part_code="B",
            name="Session B",
            session_number=2,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )

        assert str(ieap_template) == "IEAP-03 - Session B (B) (Session 2)"

    def test_get_templates_for_course_with_session_filter(self, setup_curriculum_data):
        """Test getting templates filtered by session."""
        data = setup_curriculum_data

        CoursePartTemplate.objects.create(
            course=data["ieap_3"],
            part_type="MAIN",
            part_code="A",
            name="Session A",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )

        CoursePartTemplate.objects.create(
            course=data["ieap_3"],
            part_type="MAIN",
            part_code="B",
            name="Session B",
            session_number=2,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )

        # Test filtering by session
        session_1_templates = CoursePartTemplate.get_templates_for_course(data["ieap_3"], session_number=1)
        session_2_templates = CoursePartTemplate.get_templates_for_course(data["ieap_3"], session_number=2)
        all_templates = CoursePartTemplate.get_templates_for_course(data["ieap_3"])

        assert session_1_templates.count() == 1
        assert session_2_templates.count() == 1
        assert all_templates.count() == 2

        assert session_1_templates.first().session_number == 1
        assert session_2_templates.first().session_number == 2

    def test_template_ordering(self, setup_curriculum_data):
        """Test that templates are ordered correctly."""
        data = setup_curriculum_data

        CoursePartTemplate.objects.create(
            course=data["ehss_07"],
            part_type="CONVERSATION",
            part_code="C",
            name="Conversation",
            session_number=1,
            meeting_days="FRI",
            grade_weight=Decimal("0.200"),
            display_order=300,
        )

        CoursePartTemplate.objects.create(
            course=data["ehss_07"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED",
            grade_weight=Decimal("0.500"),
            display_order=100,
        )

        CoursePartTemplate.objects.create(
            course=data["ehss_07"],
            part_type="COMPUTER",
            part_code="B",
            name="Computer Lab",
            session_number=1,
            meeting_days="TUE,THU",
            grade_weight=Decimal("0.300"),
            display_order=200,
        )

        # Verify correct ordering
        templates = CoursePartTemplate.get_templates_for_course(data["ehss_07"])
        template_list = list(templates)

        assert template_list[0].part_type == "GRAMMAR"  # display_order 100
        assert template_list[1].part_type == "COMPUTER"  # display_order 200
        assert template_list[2].part_type == "CONVERSATION"  # display_order 300
