#!/usr/bin/env python
"""Demo script for language program automatic promotion system.

This script creates a complete test scenario:
1. Creates 10 test students
2. Creates 2 consecutive ENG_A terms
3. Creates EHSS-05 and EHSS-06 courses
4. Enrolls students in EHSS-05 for term 1
5. Runs automatic promotion to term 2
6. Verifies students were promoted correctly
"""

import os
import sys
from datetime import date

import django

# Add the project root to Python path
sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# Initialize Django
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.common.models import StudentActivityLog
from apps.curriculum.models import Course, Division, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.language.services import LanguagePromotionService
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


def create_test_data():
    """Create all test data needed for the promotion demo."""
    # Create staff user
    staff_user, created = User.objects.get_or_create(
        email="promotion_test_staff@test.com",
        defaults={"name": "Test Staff", "is_staff": True},
    )
    if created:
        staff_user.set_password("test123")
        staff_user.save()

    # Create 10 test students
    students = []
    for i in range(1, 11):
        user, created = User.objects.get_or_create(
            email=f"student{i:02d}@test.com",
            defaults={"name": f"Student {i:02d} Test"},
        )

        student, created = StudentProfile.objects.get_or_create(
            user=user,
            defaults={"student_number": f"S{i:03d}", "date_of_birth": date(2000, 1, 1)},
        )
        students.append(student)

    # Create Language Division
    division, created = Division.objects.get_or_create(name="Language Division", defaults={"short_name": "LANG"})

    # Create two consecutive ENG_A terms
    term1, created = Term.objects.get_or_create(
        name="ENG A 2024-1",
        defaults={
            "term_type": Term.TermType.ENGLISH_A,
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
        },
    )

    term2, created = Term.objects.get_or_create(
        name="ENG A 2024-2",
        defaults={
            "term_type": Term.TermType.ENGLISH_A,
            "start_date": "2024-04-01",
            "end_date": "2024-06-30",
        },
    )

    # Create EHSS courses (levels 5 and 6)
    course_l5, created = Course.objects.get_or_create(
        code="EHSS-05",
        defaults={
            "title": "English for High School Level 5",
            "short_title": "EHSS L5",
            "division": division,
            "cycle": Course.CourseLevel.LANGUAGE,
            "is_language": True,
        },
    )

    course_l6, created = Course.objects.get_or_create(
        code="EHSS-06",
        defaults={
            "title": "English for High School Level 6",
            "short_title": "EHSS L6",
            "division": division,
            "cycle": Course.CourseLevel.LANGUAGE,
            "is_language": True,
        },
    )

    # Create class in term 1 (EHSS-05)
    class_t1, created = ClassHeader.objects.get_or_create(
        course=course_l5,
        term=term1,
        section="A",
        defaults={"max_enrollment": 25, "created_by": staff_user},
    )

    return {
        "staff_user": staff_user,
        "students": students,
        "term1": term1,
        "term2": term2,
        "course_l5": course_l5,
        "course_l6": course_l6,
        "class_t1": class_t1,
    }


def enroll_students(data):
    """Enroll all students in the EHSS-05 class for term 1."""
    enrollments = []
    grades = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D"]

    for i, student in enumerate(data["students"]):
        enrollment, created = ClassHeaderEnrollment.objects.get_or_create(
            student=student,
            class_header=data["class_t1"],
            defaults={
                "enrolled_by": data["staff_user"],
                "status": ClassHeaderEnrollment.EnrollmentStatus.COMPLETED,
                "final_grade": grades[i],  # Assign different passing grades
            },
        )
        enrollments.append(enrollment)

        # Log the enrollment
        StudentActivityLog.log_student_activity(
            student=student,
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description=f"Enrolled in {data['class_t1'].course.code} Section {data['class_t1'].section}",
            performed_by=data["staff_user"],
            term=data["term1"],
            class_header=data["class_t1"],
            program_name="EHSS",
        )

    return enrollments


def analyze_promotion(data):
    """Analyze promotion eligibility for students."""
    plan = LanguagePromotionService.analyze_promotion_eligibility(
        source_term=data["term1"],
        target_term=data["term2"],
        program="EHSS",
    )

    for _i, (_student, _from_level, _to_level) in enumerate(plan.eligible_students, 1):
        pass

    for _i, _class_header in enumerate(plan.classes_to_clone, 1):
        pass

    return plan


def execute_promotion(data, plan):
    """Execute the automatic promotion."""
    with transaction.atomic():
        result = LanguagePromotionService.execute_promotion(
            promotion_plan=plan,
            initiated_by=data["staff_user"],
            notes="Demo promotion test - automatic progression from EHSS-05 to EHSS-06",
        )

    if result.errors:
        for _error in result.errors:
            pass

    return result


def verify_promotion(data, result):
    """Verify that the promotion was successful."""
    # Check promotion batch
    promotion_batch = result.promotion_batch
    if promotion_batch:
        pass

    # Check if EHSS-06 class was created in term 2
    try:
        ehss_06_class = ClassHeader.objects.get(course=data["course_l6"], term=data["term2"], section="A")
    except ClassHeader.DoesNotExist:
        return False

    # Check student enrollments in new class
    new_enrollments = ClassHeaderEnrollment.objects.filter(class_header=ehss_06_class).select_related("student__user")

    for _i, _enrollment in enumerate(new_enrollments, 1):
        pass

    # Check audit logs
    promotion_logs = StudentActivityLog.objects.filter(
        activity_type=StudentActivityLog.ActivityType.LANGUAGE_PROMOTION,
        term_name=data["term2"].name,
    ).select_related("student__user")

    for _i, _log in enumerate(promotion_logs, 1):
        pass

    # Summary

    return new_enrollments.count() == len(data["students"])


def demonstrate_search_capabilities(data):
    """Demonstrate the audit log search capabilities."""
    # Search by student number
    student = data["students"][0]
    student_logs = StudentActivityLog.search_student_activities(student_number=student.student_number)
    for _log in student_logs:
        pass

    # Search by activity type
    promotion_logs = StudentActivityLog.search_student_activities(
        activity_type=StudentActivityLog.ActivityType.LANGUAGE_PROMOTION,
    )
    for _log in promotion_logs[:3]:  # Show first 3
        pass

    # Search by term
    term_logs = StudentActivityLog.search_student_activities(term_name=data["term2"].name)
    for _log in term_logs[:3]:  # Show first 3
        pass


def main():
    """Run the complete promotion demonstration."""
    try:
        # Step 1: Create test data
        data = create_test_data()

        # Step 2: Enroll students
        enroll_students(data)

        # Step 3: Analyze promotion eligibility
        plan = analyze_promotion(data)

        # Step 4: Execute promotion
        result = execute_promotion(data, plan)

        # Step 5: Verify results
        success = verify_promotion(data, result)

        # Step 6: Demonstrate search capabilities
        demonstrate_search_capabilities(data)

        # Final summary
        if success:
            pass
        else:
            pass

    except Exception:
        import traceback

        traceback.print_exc()
        return False

    return success


if __name__ == "__main__":
    main()
