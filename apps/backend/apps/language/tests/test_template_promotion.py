"""Tests for template-based language promotion system.

Tests the updated language promotion service that requires curriculum templates
instead of cloning previous classes.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.curriculum.models import Course, CoursePartTemplate, Division, Term, Textbook
from apps.language.services import LanguagePromotionService
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


@pytest.mark.django_db
class TestTemplateBasedPromotion:
    """Test language promotion using curriculum templates."""

    @pytest.fixture
    def setup_promotion_data(self):
        """Set up comprehensive test data for template-based promotion."""
        # Create users
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff User")

        # Create students
        students = []
        for i in range(3):
            User.objects.create_user(email=f"student{i}@example.com", name=f"Student{i} Test")
            person = Person.objects.create(
                family_name=f"Student{i}",
                personal_name="Test",
                date_of_birth="2000-01-01",
            )
            student = StudentProfile.objects.create(person=person, student_id=i + 1)
            students.append(student)

        # Create division
        division = Division.objects.create(name="Language Division", short_name="LANG")

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

        # Create courses
        ehss_05 = Course.objects.create(
            code="EHSS-05",
            title="English for High School Level 5",
            short_title="EHSS L5",
            division=division,
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        ehss_06 = Course.objects.create(
            code="EHSS-06",
            title="English for High School Level 6",
            short_title="EHSS L6",
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

        ieap_2 = Course.objects.create(
            code="IEAP-02",
            title="IEAP Level 2",
            short_title="IEAP L2",
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
        ventures_5 = Textbook.objects.create(
            title="Ventures 5 Student Book",
            author="Gretchen Bitterlin",
            isbn="978-1-108-45670-5",
        )

        ventures_6 = Textbook.objects.create(
            title="Ventures 6 Student Book",
            author="Gretchen Bitterlin",
            isbn="978-1-108-45671-6",
        )

        ventures_7_student = Textbook.objects.create(
            title="Ventures 7 Student Book",
            author="Gretchen Bitterlin",
            isbn="978-1-108-45672-7",
        )

        ventures_7_workbook = Textbook.objects.create(
            title="Ventures 7 Workbook",
            author="Gretchen Bitterlin",
            isbn="978-1-108-45673-8",
        )

        return {
            "staff_user": staff_user,
            "students": students,
            "division": division,
            "source_term": source_term,
            "target_term": target_term,
            "ehss_05": ehss_05,
            "ehss_06": ehss_06,
            "ehss_07": ehss_07,
            "ieap_2": ieap_2,
            "ieap_3": ieap_3,
            "ventures_5": ventures_5,
            "ventures_6": ventures_6,
            "ventures_7_student": ventures_7_student,
            "ventures_7_workbook": ventures_7_workbook,
        }

    def test_create_class_from_simple_template(self, setup_promotion_data):
        """Test creating a class from a simple single-session template."""
        data = setup_promotion_data

        CoursePartTemplate.objects.create(
            course=data["ehss_06"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("0.800"),
        ).textbooks.set([data["ventures_6"]])

        CoursePartTemplate.objects.create(
            course=data["ehss_06"],
            part_type="COMPUTER",
            part_code="B",
            name="Computer Lab",
            session_number=1,
            meeting_days="TUE,THU",
            grade_weight=Decimal("0.200"),
        ).textbooks.set([data["ventures_6"]])

        class_header = LanguagePromotionService._create_class_from_template(data["ehss_06"], data["target_term"], "A")

        # Verify class header created correctly
        assert class_header.course == data["ehss_06"]
        assert class_header.term == data["target_term"]
        assert class_header.section_id == "A"
        assert class_header.status == ClassHeader.ClassStatus.DRAFT

        # Verify single session created
        sessions = class_header.class_sessions.all()
        assert sessions.count() == 1
        session = sessions.first()
        assert session.session_number == 1
        assert session.grade_weight == Decimal("1.000")

        parts = session.class_parts.all()
        assert parts.count() == 2

        grammar_part = parts.get(class_part_type="GRAMMAR")
        assert grammar_part.class_part_code == "A"
        assert grammar_part.name == "Grammar"
        assert grammar_part.meeting_days == "MON,WED,FRI"
        assert grammar_part.grade_weight == Decimal("0.800")
        assert grammar_part.textbooks.count() == 1
        assert grammar_part.textbooks.first() == data["ventures_6"]

        computer_part = parts.get(class_part_type="COMPUTER")
        assert computer_part.class_part_code == "B"
        assert computer_part.name == "Computer Lab"
        assert computer_part.meeting_days == "TUE,THU"
        assert computer_part.grade_weight == Decimal("0.200")

    def test_create_class_from_multi_part_template(self, setup_promotion_data):
        """Test creating a class from EHSS-07 template with 3 parts."""
        data = setup_promotion_data

        CoursePartTemplate.objects.create(
            course=data["ehss_07"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED",
            grade_weight=Decimal("0.500"),
        ).textbooks.set([data["ventures_7_student"], data["ventures_7_workbook"]])

        CoursePartTemplate.objects.create(
            course=data["ehss_07"],
            part_type="COMPUTER",
            part_code="B",
            name="Computer Lab",
            session_number=1,
            meeting_days="TUE,THU",
            grade_weight=Decimal("0.300"),
        ).textbooks.set([data["ventures_7_student"]])

        CoursePartTemplate.objects.create(
            course=data["ehss_07"],
            part_type="CONVERSATION",
            part_code="C",
            name="Conversation",
            session_number=1,
            meeting_days="FRI",
            grade_weight=Decimal("0.200"),
        ).textbooks.set([data["ventures_7_workbook"]])

        class_header = LanguagePromotionService._create_class_from_template(data["ehss_07"], data["target_term"], "A")

        # Verify all parts created correctly
        session = class_header.class_sessions.first()
        parts = session.class_parts.all()
        assert parts.count() == 3

        # Check specific part configurations
        grammar_part = parts.get(class_part_type="GRAMMAR")
        assert grammar_part.meeting_days == "MON,WED"
        assert grammar_part.textbooks.count() == 2

        conversation_part = parts.get(class_part_type="CONVERSATION")
        assert conversation_part.meeting_days == "FRI"
        assert conversation_part.textbooks.count() == 1
        assert conversation_part.textbooks.first() == data["ventures_7_workbook"]

        # Verify weights sum to 1.0
        total_weight = sum(part.grade_weight for part in parts)
        assert abs(total_weight - Decimal("1.000")) < Decimal("0.001")

    def test_create_ieap_class_from_template(self, setup_promotion_data):
        """Test creating IEAP class with 2 sessions from template."""
        data = setup_promotion_data

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

        class_header = LanguagePromotionService._create_class_from_template(data["ieap_3"], data["target_term"], "A")

        # Verify 2 sessions created
        sessions = class_header.class_sessions.all()
        assert sessions.count() == 2

        # Verify each session has correct weight and structure
        for session in sessions:
            assert session.grade_weight == Decimal("0.500")  # IEAP sessions are 50% each
            assert session.class_parts.count() == 1

        # Verify session-specific parts
        session_1 = sessions.get(session_number=1)
        session_2 = sessions.get(session_number=2)

        part_1 = session_1.class_parts.first()
        part_2 = session_2.class_parts.first()

        assert part_1.class_part_code == "A"
        assert part_1.name == "Session A"
        assert part_2.class_part_code == "B"
        assert part_2.name == "Session B"

    def test_template_missing_fails_hard(self, setup_promotion_data):
        """Test that missing template causes hard failure, no fallback cloning."""
        data = setup_promotion_data

        with pytest.raises(ValidationError) as exc_info:
            LanguagePromotionService._create_class_from_template(data["ehss_06"], data["target_term"], "A")

        assert "missing required part template" in str(exc_info.value)
        assert "Cannot create class without curriculum definition" in str(exc_info.value)

    def test_incomplete_template_fails_hard(self, setup_promotion_data):
        """Test that incomplete template (weights don't sum to 1.0) fails."""
        data = setup_promotion_data

        # Create incomplete template (weights sum to 0.7, not 1.0)
        CoursePartTemplate.objects.create(
            course=data["ehss_06"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("0.400"),
        )

        CoursePartTemplate.objects.create(
            course=data["ehss_06"],
            part_type="COMPUTER",
            part_code="B",
            name="Computer Lab",
            session_number=1,
            meeting_days="TUE,THU",
            grade_weight=Decimal("0.300"),  # Total = 0.7, not 1.0
        )

        # Should fail validation
        with pytest.raises(ValidationError) as exc_info:
            LanguagePromotionService._create_class_from_template(data["ehss_06"], data["target_term"], "A")

        assert "incomplete templates" in str(exc_info.value)

    def test_ieap_missing_session_fails(self, setup_promotion_data):
        """Test that IEAP course missing session 2 template fails."""
        data = setup_promotion_data

        CoursePartTemplate.objects.create(
            course=data["ieap_3"],
            part_type="MAIN",
            part_code="A",
            name="Session A",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )

        with pytest.raises(ValidationError) as exc_info:
            LanguagePromotionService._create_class_from_template(data["ieap_3"], data["target_term"], "A")

        assert "should have exactly 2 sessions" in str(exc_info.value)

    def test_promotion_with_template_success(self, setup_promotion_data):
        """Test full promotion flow using templates."""
        data = setup_promotion_data

        # Create source class (EHSS-05)
        source_class = ClassHeader.objects.create(course=data["ehss_05"], term=data["source_term"], section_id="A")

        CoursePartTemplate.objects.create(
            course=data["ehss_06"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("0.800"),
        )

        CoursePartTemplate.objects.create(
            course=data["ehss_06"],
            part_type="COMPUTER",
            part_code="B",
            name="Computer Lab",
            session_number=1,
            meeting_days="TUE,THU",
            grade_weight=Decimal("0.200"),
        )

        # Test promotion cloning
        cloned_class = LanguagePromotionService._clone_class_for_next_level(source_class, data["target_term"], "EHSS")

        # Verify class created successfully
        assert cloned_class is not None
        assert cloned_class.course.code == "EHSS-06"
        assert cloned_class.term == data["target_term"]
        assert cloned_class.section_id == "A"

        session = cloned_class.class_sessions.first()
        parts = session.class_parts.all()
        assert parts.count() == 2
        assert parts.filter(class_part_type="GRAMMAR").exists()
        assert parts.filter(class_part_type="COMPUTER").exists()

    def test_promotion_without_template_fails(self, setup_promotion_data):
        """Test that promotion fails without target course template."""
        data = setup_promotion_data

        # Create source class (EHSS-05)
        source_class = ClassHeader.objects.create(course=data["ehss_05"], term=data["source_term"], section_id="A")

        with pytest.raises(ValidationError):
            LanguagePromotionService._clone_class_for_next_level(source_class, data["target_term"], "EHSS")

    def test_different_textbooks_per_level(self, setup_promotion_data):
        """Test that different levels use different textbooks as specified in templates."""
        data = setup_promotion_data

        CoursePartTemplate.objects.create(
            course=data["ehss_06"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        ).textbooks.set([data["ventures_6"]])

        CoursePartTemplate.objects.create(
            course=data["ehss_07"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        ).textbooks.set([data["ventures_7_student"], data["ventures_7_workbook"]])

        ehss_06_class = LanguagePromotionService._create_class_from_template(data["ehss_06"], data["target_term"], "A")

        ehss_07_class = LanguagePromotionService._create_class_from_template(data["ehss_07"], data["target_term"], "A")

        # Verify different textbooks assigned
        ehss_06_part = ehss_06_class.class_sessions.first().class_parts.first()
        ehss_07_part = ehss_07_class.class_sessions.first().class_parts.first()

        assert ehss_06_part.textbooks.count() == 1
        assert ehss_06_part.textbooks.first() == data["ventures_6"]

        assert ehss_07_part.textbooks.count() == 2
        textbook_titles = {tb.title for tb in ehss_07_part.textbooks.all()}
        assert "Ventures 7 Student Book" in textbook_titles
        assert "Ventures 7 Workbook" in textbook_titles

    def test_schedule_details_left_blank_for_scheduler(self, setup_promotion_data):
        """Test that scheduling details are left blank for manual assignment."""
        data = setup_promotion_data

        CoursePartTemplate.objects.create(
            course=data["ehss_06"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED,FRI",
            grade_weight=Decimal("1.000"),
        )

        # Create class
        class_header = LanguagePromotionService._create_class_from_template(data["ehss_06"], data["target_term"], "A")

        # Verify scheduling details are blank
        part = class_header.class_sessions.first().class_parts.first()
        assert part.meeting_days == "MON,WED,FRI"
        assert part.start_time is None  # Left for scheduler
        assert part.end_time is None  # Left for scheduler
        assert part.teacher is None  # Left for scheduler
        assert part.room is None  # Left for scheduler

    def test_template_preserves_curriculum_weights(self, setup_promotion_data):
        """Test that curriculum-defined weights are preserved in created classes."""
        data = setup_promotion_data

        CoursePartTemplate.objects.create(
            course=data["ehss_07"],
            part_type="GRAMMAR",
            part_code="A",
            name="Grammar",
            session_number=1,
            meeting_days="MON,WED",
            grade_weight=Decimal("0.600"),  # Curriculum decision
        )

        CoursePartTemplate.objects.create(
            course=data["ehss_07"],
            part_type="CONVERSATION",
            part_code="B",
            name="Conversation",
            session_number=1,
            meeting_days="FRI",
            grade_weight=Decimal("0.400"),  # Curriculum decision
        )

        # Create class
        class_header = LanguagePromotionService._create_class_from_template(data["ehss_07"], data["target_term"], "A")

        # Verify weights preserved exactly
        parts = class_header.class_sessions.first().class_parts.all()
        grammar_part = parts.get(class_part_type="GRAMMAR")
        conversation_part = parts.get(class_part_type="CONVERSATION")

        assert grammar_part.grade_weight == Decimal("0.600")
        assert conversation_part.grade_weight == Decimal("0.400")

        # Verify total still equals 1.0
        total_weight = sum(part.grade_weight for part in parts)
        assert abs(total_weight - Decimal("1.000")) < Decimal("0.001")
