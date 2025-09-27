"""Test utilities and helper functions for SQLite-based testing.

This module provides convenient functions for creating test data scenarios
using the factory_boy factories.
"""

from apps.common.factories import SuperUserFactory
from apps.curriculum.factories import (
    AcademicCourseFactory,
    AcademicDivisionFactory,
    LanguageCourseFactory,
    LanguageDivisionFactory,
    TermFactory,
)
from apps.enrollment.factories import (
    ActiveEnrollmentFactory,
    CompletedEnrollmentFactory,
)
from apps.people.factories import StudentProfileFactory, TeacherProfileFactory
from apps.scheduling.factories import (
    AcademicClassHeaderFactory,
    ClassSessionFactory,
    LanguageClassHeaderFactory,
    LanguageClassPartFactory,
)


def create_basic_test_environment():
    """Create a basic test environment with essential data.

    Returns:
        dict: Contains created objects for easy access in tests
    """
    # Create admin user
    admin = SuperUserFactory()

    # Create divisions
    lang_division = LanguageDivisionFactory()
    acad_division = AcademicDivisionFactory()

    # Create terms
    current_term = TermFactory(name="2024T1")
    next_term = TermFactory(name="2024T2")

    # Create some courses
    eng_course = LanguageCourseFactory(code="ENG-01", title="English Level 1")
    math_course = AcademicCourseFactory(code="MATH-101", title="College Mathematics")

    # Create teacher
    teacher = TeacherProfileFactory()

    return {
        "admin": admin,
        "lang_division": lang_division,
        "acad_division": acad_division,
        "current_term": current_term,
        "next_term": next_term,
        "eng_course": eng_course,
        "math_course": math_course,
        "teacher": teacher,
    }


def create_student_enrollment_scenario():
    """Create a realistic student enrollment scenario.

    Returns:
        dict: Contains student with multiple enrollments
    """
    env = create_basic_test_environment()

    # Create student
    student = StudentProfileFactory()

    # Create class headers
    eng_class = LanguageClassHeaderFactory(course=env["eng_course"], term=env["current_term"], section_id="A")
    math_class = AcademicClassHeaderFactory(course=env["math_course"], term=env["current_term"], section_id="A")

    # Create enrollments
    active_enrollment = ActiveEnrollmentFactory(student=student, class_header=eng_class, enrolled_by=env["admin"])
    completed_enrollment = CompletedEnrollmentFactory(
        student=student,
        class_header=math_class,
        enrolled_by=env["admin"],
        final_grade="B",
    )

    return {
        **env,
        "student": student,
        "eng_class": eng_class,
        "math_class": math_class,
        "active_enrollment": active_enrollment,
        "completed_enrollment": completed_enrollment,
    }


def create_ieap_class_scenario():
    """Create an IEAP class with multiple sessions and parts.

    Returns:
        dict: Contains IEAP class structure
    """
    env = create_basic_test_environment()

    # Create IEAP course
    ieap_course = LanguageCourseFactory(code="IEAP-01", title="IEAP Level 1")

    # Create class header
    ieap_class = LanguageClassHeaderFactory(course=ieap_course, term=env["current_term"], section_id="A")

    # Create two sessions (IEAP has 2 sessions per class)
    session1 = ClassSessionFactory(class_header=ieap_class, session_number=1, session_name="Session 1")
    session2 = ClassSessionFactory(class_header=ieap_class, session_number=2, session_name="Session 2")

    # Create class parts for each session
    grammar_part1 = LanguageClassPartFactory(class_session=session1, class_part_code="A", name="Grammar Part 1")
    writing_part1 = LanguageClassPartFactory(class_session=session1, class_part_code="B", name="Writing Part 1")

    grammar_part2 = LanguageClassPartFactory(class_session=session2, class_part_code="A", name="Grammar Part 2")
    writing_part2 = LanguageClassPartFactory(class_session=session2, class_part_code="B", name="Writing Part 2")

    return {
        **env,
        "ieap_course": ieap_course,
        "ieap_class": ieap_class,
        "session1": session1,
        "session2": session2,
        "grammar_part1": grammar_part1,
        "writing_part1": writing_part1,
        "grammar_part2": grammar_part2,
        "writing_part2": writing_part2,
    }


def create_bulk_students(count=50):
    """Create multiple students for performance testing.

    Args:
        count (int): Number of students to create

    Returns:
        list: List of created StudentProfile objects
    """
    return StudentProfileFactory.create_batch(count)


def create_full_class_enrollment(class_size=15):
    """Create a fully enrolled class with realistic data.

    Args:
        class_size (int): Number of students to enroll

    Returns:
        dict: Contains class and all enrollments
    """
    env = create_basic_test_environment()

    # Create class
    lang_class = LanguageClassHeaderFactory(
        course=env["eng_course"],
        term=env["current_term"],
        section_id="A",
        max_enrollment=class_size,
    )

    # Create students and enroll them
    students = []
    enrollments = []

    for _i in range(class_size):
        student = StudentProfileFactory()
        enrollment = ActiveEnrollmentFactory(student=student, class_header=lang_class, enrolled_by=env["admin"])
        students.append(student)
        enrollments.append(enrollment)

    return {
        **env,
        "class_header": lang_class,
        "students": students,
        "enrollments": enrollments,
    }
