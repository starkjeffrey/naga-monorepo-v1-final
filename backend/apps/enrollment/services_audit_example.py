"""Enrollment App Audit Integration Examples

This module demonstrates audit logging integration for enrollment
and grading operations, including batch operations.

Note: This is an example/template file with placeholder models.
"""

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.db import transaction

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    User = AbstractUser

    # Placeholder models for template/example purposes
    class Grade:
        pass

    class GradeType:
        pass
else:
    User = get_user_model()

from apps.attendance.models import AttendanceRecord
from apps.common.audit.decorators import audit_action
from apps.common.audit.helpers import log_activity, log_bulk_activity
from apps.common.audit.models import ActivityCategory, ActivityVisibility
from apps.curriculum.models import Course
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader


# Example/placeholder types for audit documentation
class EnrollmentStatus:
    ENROLLED = "enrolled"
    DROPPED = "dropped"
    COMPLETED = "completed"


class MockManager:
    """Mock manager for placeholder classes."""

    def create(self, **kwargs):
        """Mock create method."""
        return None

    def filter(self, **kwargs):
        """Mock filter method."""
        return self

    def count(self):
        """Mock count method."""
        return 0

    def get(self, **kwargs):
        """Mock get method."""
        return None


class Section:
    """Placeholder for audit example."""

    objects = MockManager()

    def __init__(self):
        self.course = None
        self.section_id = None
        self.term = None
        self.class_header_enrollments = MockManager()


class Enrollment:
    """Placeholder for audit example."""

    class DoesNotExist(Exception):
        """Mock DoesNotExist exception."""

        pass

    objects = MockManager()

    def __init__(self):
        self.id = 1
        self.student = None
        self.section = None
        self.status = None
        self.dropped_date = None
        self.drop_reason = None

    def save(self):
        """Placeholder save method."""
        pass


class EnrollmentService:
    """Service for handling enrollment operations with audit logging."""

    @staticmethod
    def enroll_student(
        student: StudentProfile,
        class_header: ClassHeader,
        user: User,
        override_capacity: bool = False,
        notes: str = "",
    ) -> ClassHeaderEnrollment:
        """Enroll a single student in a course section.

        Shows:
        - Pre-enrollment validation logging
        - Success logging with metadata
        - Error handling with audit trail
        """
        # Check prerequisites
        prerequisites_met = EnrollmentService._check_prerequisites(student, class_header.course)

        # Check section capacity
        current_enrollment = class_header.class_header_enrollments.filter(status=EnrollmentStatus.ENROLLED).count()

        at_capacity = current_enrollment >= class_header.max_enrollment

        try:
            with transaction.atomic():
                # Create enrollment
                enrollment = Enrollment.objects.create(
                    student=student,
                    section=class_header,
                    status=EnrollmentStatus.ENROLLED,
                    enrolled_by=user,
                    override_capacity=override_capacity and at_capacity,
                    notes=notes,
                )

                # Log successful enrollment
                metadata = {
                    "student_id": student.student_id,
                    "course_code": class_header.course.code,
                    "section_id": class_header.section_id,
                    "term": class_header.term.code,
                    "prerequisites_met": prerequisites_met,
                    "at_capacity": at_capacity,
                    "override_capacity": override_capacity and at_capacity,
                    "current_enrollment": current_enrollment + 1,
                    "section_capacity": class_header.max_enrollment,
                }

                if notes:
                    metadata["notes"] = notes

                log_activity(
                    user=user,
                    category=ActivityCategory.ENROLLMENT,
                    description=(
                        f"Enrolled {student.student_id} in {class_header.course.code} "
                        f"section {class_header.section_id}"
                    ),
                    target_object=enrollment,
                    metadata=metadata,
                    visibility=ActivityVisibility.DEPARTMENT,
                )

                # Also log to student's activity
                from apps.common.models import StudentActivityLog

                StudentActivityLog.objects.create(
                    student_number=student.student_id if hasattr(student, "student_id") else str(student.id),
                    student_name=str(student),
                    activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
                    description=f"Enrolled in {class_header.course.code} - {class_header.course.title}",
                    activity_details={
                        "enrollment_id": enrollment.id,
                        "section": class_header.section_id,
                        "instructor": (
                            class_header.primary_teacher.get_full_name() if class_header.primary_teacher else None
                        ),
                    },
                    class_code=class_header.course.code,
                    term_name=class_header.term.name,
                    performed_by=user,
                )

                return enrollment

        except Exception as e:
            # Log failed enrollment
            log_activity(
                user=user,
                category=ActivityCategory.ERROR,
                description=f"Failed to enroll {student.student_id} in {class_header.course.code}",
                metadata={
                    "student_id": student.student_id,
                    "course_code": class_header.course.code,
                    "section_id": class_header.section_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "at_capacity": at_capacity,
                    "prerequisites_met": prerequisites_met,
                },
                visibility=ActivityVisibility.ADMIN,
            )
            raise

    @staticmethod
    def drop_enrollment(enrollment: Enrollment, user: User, reason: str = "StudentProfile requested") -> None:
        """Drop a student from a course.

        Shows:
        - Recording drop reasons
        - Calculating refunds
        - Notification metadata
        """
        student = enrollment.student
        section = enrollment.section
        old_status = enrollment.status

        # Calculate refund percentage based on drop date
        term_start = section.term.start_date
        days_since_start = (datetime.now().date() - term_start).days

        refund_percentage = 100
        if days_since_start > 7:
            refund_percentage = 50
        if days_since_start > 14:
            refund_percentage = 0

        with transaction.atomic():
            # Update enrollment status
            enrollment.status = EnrollmentStatus.DROPPED
            enrollment.dropped_date = datetime.now()
            enrollment.drop_reason = reason
            enrollment.save()

            # Log the drop
            log_activity(
                user=user,
                category=ActivityCategory.ENROLLMENT,
                description=f"Dropped {student.student_id} from {section.course.code}",
                target_object=enrollment,
                metadata={
                    "student_id": student.student_id,
                    "course_code": section.course.code,
                    "section_id": section.section_id,
                    "old_status": old_status,
                    "drop_reason": reason,
                    "days_since_start": days_since_start,
                    "refund_percentage": refund_percentage,
                    "initiated_by": ("student" if user == student.person.user else "staff"),
                },
                visibility=ActivityVisibility.DEPARTMENT,
            )

            # StudentProfile-visible log
            from apps.common.models import StudentActivityLog

            StudentActivityLog.objects.create(
                student_number=student.student_id if hasattr(student, "student_id") else str(student.id),
                student_name=str(student),
                activity_type=StudentActivityLog.ActivityType.CLASS_WITHDRAWAL,
                description=f"Dropped from {section.course.code} - {section.course.title}",
                activity_details={"reason": reason, "refund_percentage": refund_percentage},
                class_code=section.course.code,
                performed_by=user,
            )

    @staticmethod
    @audit_action(
        category=ActivityCategory.ENROLLMENT,
        description="Batch enrollment operation",
        visibility=ActivityVisibility.DEPARTMENT,
    )
    def batch_enroll_students(
        student_ids: list[int],
        section_id: int,
        user: User,
        override_capacity: bool = False,
    ) -> tuple[list[Enrollment], list[dict]]:
        """Enroll multiple students in a section.

        Shows:
        - Batch operation logging
        - Success/failure tracking
        - Comprehensive metadata
        """
        section = Section.objects.get(id=section_id)
        successful_enrollments = []
        failed_enrollments = []

        # Check section capacity
        current_enrollment = section.class_header_enrollments.filter(status=EnrollmentStatus.ENROLLED).count()
        available_spots = max(0, section.max_enrollment - current_enrollment)

        with transaction.atomic():
            for idx, student_id in enumerate(student_ids):
                try:
                    student = StudentProfile.objects.get(id=student_id)

                    # Check if already enrolled
                    if Enrollment.objects.filter(
                        student=student,
                        section=section,
                        status=EnrollmentStatus.ENROLLED,
                    ).exists():
                        failed_enrollments.append(
                            {
                                "student_id": student.student_id,
                                "reason": "Already enrolled",
                            },
                        )
                        continue

                    # Check capacity (unless overriding)
                    if not override_capacity and idx >= available_spots:
                        failed_enrollments.append(
                            {
                                "student_id": student.student_id,
                                "reason": "Section at capacity",
                            },
                        )
                        continue

                    # Create enrollment
                    enrollment = Enrollment.objects.create(
                        student=student,
                        section=section,
                        status=EnrollmentStatus.ENROLLED,
                        enrolled_by=user,
                        override_capacity=override_capacity and idx >= available_spots,
                    )

                    successful_enrollments.append(enrollment)

                except StudentProfile.DoesNotExist:
                    failed_enrollments.append(
                        {
                            "student_id": student_id,
                            "reason": "StudentProfile not found",
                        },
                    )
                except Exception as e:
                    failed_enrollments.append(
                        {
                            "student_id": getattr(student, "student_id", student_id),
                            "reason": str(e),
                        },
                    )

            # Log bulk operation
            if successful_enrollments:
                log_bulk_activity(
                    user=user,
                    category=ActivityCategory.ENROLLMENT,
                    base_description=f"Batch enrolled students in {section.course.code}",
                    objects=[
                        {
                            "model": "enrollment.Enrollment",
                            "id": enrollment.id,
                            "description": f"Enrolled {enrollment.student.student_id}",
                        }
                        for enrollment in successful_enrollments
                    ],
                    metadata={
                        "course_code": section.course.code,
                        "section_id": section.section_id,
                        "term": section.term.code,
                        "total_requested": len(student_ids),
                        "successful": len(successful_enrollments),
                        "failed": len(failed_enrollments),
                        "override_capacity": override_capacity,
                        "initial_enrollment": current_enrollment,
                        "final_enrollment": current_enrollment + len(successful_enrollments),
                        "section_capacity": section.max_enrollment,
                        "failed_details": failed_enrollments,
                    },
                    visibility=ActivityVisibility.DEPARTMENT,
                )

        return successful_enrollments, failed_enrollments

    @staticmethod
    def _check_prerequisites(student: StudentProfile, course: Course) -> bool:
        """Check if student meets course prerequisites."""
        # Simplified example - real implementation would be more complex
        if not course.required_prerequisites.exists():
            return True

        completed_courses = Enrollment.objects.filter(
            student=student,
            status=EnrollmentStatus.COMPLETED,
            grade__grade__in=["A", "B", "C"],  # Passing grades
        ).values_list("section__course_id", flat=True)

        prerequisite_ids = course.required_prerequisites.values_list("id", flat=True)
        return all(prereq_id in completed_courses for prereq_id in prerequisite_ids)


class GradeService:
    """Service for handling grade operations with audit logging."""

    @staticmethod
    def update_grade(
        enrollment: Enrollment,
        grade_value: str,
        grade_type: GradeType,
        user: User,
        notes: str = "",
    ) -> Grade:
        """Update or create a grade for an enrollment.

        Shows:
        - Grade change tracking
        - GPA impact calculation
        - Visibility rules for grades
        """
        student = enrollment.student
        old_grade = None
        old_gpa_impact = 0.0

        try:
            # Get or create grade record
            grade, created = Grade.objects.get_or_create(
                enrollment=enrollment,
                grade_type=grade_type,
                defaults={"grade": grade_value, "graded_by": user, "notes": notes},
            )

            if not created:
                old_grade = grade.grade
                old_gpa_impact = GradeService._calculate_gpa_points(old_grade, enrollment.section.course.credits)
                grade.grade = grade_value
                grade.graded_by = user
                grade.graded_date = datetime.now()
                if notes:
                    grade.notes = notes
                grade.save()

            # Calculate new GPA impact
            new_gpa_impact = GradeService._calculate_gpa_points(grade_value, enrollment.section.course.credits)

            # Log grade change
            metadata = {
                "student_id": student.student_id,
                "course_code": enrollment.section.course.code,
                "section_id": enrollment.section.section_id,
                "grade_type": grade_type,
                "credits": enrollment.section.course.credits,
                "new_gpa_points": new_gpa_impact,
            }

            if old_grade:
                metadata["old_grade"] = old_grade
                metadata["old_gpa_points"] = old_gpa_impact
                metadata["gpa_change"] = new_gpa_impact - old_gpa_impact
                description = f"Updated grade from {old_grade} to {grade_value}"
            else:
                description = f"Assigned grade {grade_value}"

            if notes:
                metadata["notes"] = notes

            # Department-visible log
            log_activity(
                user=user,
                category=ActivityCategory.GRADE_CHANGE,
                description=f"{description} for {student.student_id} in {enrollment.section.course.code}",
                target_object=grade,
                metadata=metadata,
                visibility=ActivityVisibility.DEPARTMENT,
            )

            # StudentProfile-visible log (less detail)
            from apps.common.models import StudentActivityLog

            StudentActivityLog.objects.create(
                student_number=student.student_id if hasattr(student, "student_id") else str(student.id),
                student_name=str(student),
                activity_type=StudentActivityLog.ActivityType.GRADE_ASSIGNMENT,
                description=f"Grade {grade_type} posted for {enrollment.section.course.code}",
                activity_details={
                    "course_name": enrollment.section.course.title,
                    "grade": grade_value,
                    "credits": enrollment.section.course.credits,
                },
                class_code=enrollment.section.course.code,
                performed_by=user,
            )

            return grade

        except Exception as e:
            log_activity(
                user=user,
                category=ActivityCategory.ERROR,
                description=f"Failed to update grade for {student.student_id}",
                metadata={
                    "error": str(e),
                    "enrollment_id": enrollment.id,
                    "attempted_grade": grade_value,
                },
                visibility=ActivityVisibility.ADMIN,
            )
            raise

    @staticmethod
    def batch_grade_update(
        section: Section,
        grades_data: list[dict[str, Any]],
        user: User,
    ) -> tuple[list[Grade], list[dict]]:
        """Update grades for multiple students in a section.

        Example grades_data:
        [
            {'student_id': 1, 'grade': 'A', 'notes': 'Excellent work'},
            {'student_id': 2, 'grade': 'B+', 'notes': ''},
            ...
        ]

        Shows:
        - Batch grade processing
        - Transaction management
        - Comprehensive error tracking
        """
        successful_grades = []
        failed_grades = []
        grade_changes = []

        with transaction.atomic():
            for grade_data in grades_data:
                try:
                    enrollment = Enrollment.objects.get(
                        student_id=grade_data["student_id"],
                        section=section,
                        status=EnrollmentStatus.ENROLLED,
                    )

                    # Track old grade if exists
                    old_grade = None
                    try:
                        existing = Grade.objects.get(enrollment=enrollment, grade_type=GradeType.FINAL)
                        old_grade = existing.grade
                    except Grade.DoesNotExist:
                        pass

                    # Update grade
                    grade = GradeService.update_grade(
                        enrollment=enrollment,
                        grade_value=grade_data["grade"],
                        grade_type=GradeType.FINAL,
                        user=user,
                        notes=grade_data.get("notes", ""),
                    )

                    successful_grades.append(grade)
                    grade_changes.append(
                        {
                            "student_id": enrollment.student.student_id,
                            "old_grade": old_grade,
                            "new_grade": grade_data["grade"],
                        },
                    )

                except Enrollment.DoesNotExist:
                    failed_grades.append(
                        {
                            "student_id": grade_data["student_id"],
                            "reason": "StudentProfile not enrolled in section",
                            "attempted_grade": grade_data["grade"],
                        },
                    )
                except Exception as e:
                    failed_grades.append(
                        {
                            "student_id": grade_data["student_id"],
                            "reason": str(e),
                            "attempted_grade": grade_data["grade"],
                        },
                    )

            # Log batch operation summary
            if successful_grades or failed_grades:
                log_activity(
                    user=user,
                    category=ActivityCategory.GRADE_CHANGE,
                    description=f"Batch grade update for {section.course.code} section {section.section_id}",
                    metadata={
                        "course_code": section.course.code,
                        "section_id": section.section_id,
                        "term": section.term.code,
                        "total_processed": len(grades_data),
                        "successful": len(successful_grades),
                        "failed": len(failed_grades),
                        "grade_distribution": GradeService._calculate_grade_distribution(successful_grades),
                        "changes_summary": grade_changes,
                        "failures": failed_grades,
                    },
                    visibility=ActivityVisibility.DEPARTMENT,
                )

        return successful_grades, failed_grades

    @staticmethod
    def _calculate_gpa_points(grade: str, credits: int) -> float:
        """Calculate GPA points for a grade."""
        grade_points = {
            "A": 4.0,
            "A-": 3.7,
            "B+": 3.3,
            "B": 3.0,
            "B-": 2.7,
            "C+": 2.3,
            "C": 2.0,
            "C-": 1.7,
            "D+": 1.3,
            "D": 1.0,
            "F": 0.0,
        }
        return grade_points.get(grade, 0.0) * credits

    @staticmethod
    def _calculate_grade_distribution(grades: list[Grade]) -> dict[str, int]:
        """Calculate distribution of grades."""
        distribution: dict[str, int] = {}
        for grade in grades:
            distribution[grade.grade] = distribution.get(grade.grade, 0) + 1
        return distribution


class AttendanceService:
    """Service for handling attendance with audit logging."""

    @staticmethod
    @audit_action(
        category=ActivityCategory.ATTENDANCE,
        description="Record class attendance",
        visibility=ActivityVisibility.DEPARTMENT,
    )
    def record_attendance(section: Section, date: date, attendance_data: list[dict], user: User) -> dict:
        """Record attendance for a class session.

        Shows:
        - Batch attendance recording
        - Pattern detection (chronic absences)
        - Automatic notifications
        """
        # AttendanceRecord already imported at top

        present_count = 0
        absent_count = 0
        late_count = 0
        excused_count = 0

        with transaction.atomic():
            for record in attendance_data:
                enrollment = Enrollment.objects.get(id=record["enrollment_id"], section=section)

                # Create or update attendance record
                attendance, created = AttendanceRecord.objects.update_or_create(
                    enrollment=enrollment,
                    date=date,
                    defaults={
                        "status": record["status"],
                        "notes": record.get("notes", ""),
                        "recorded_by": user,
                    },
                )

                # Count by status
                if record["status"] == AttendanceRecord.AttendanceStatus.PRESENT:
                    present_count += 1
                elif record["status"] == AttendanceRecord.AttendanceStatus.ABSENT:
                    absent_count += 1

                    # Check for chronic absences
                    recent_absences = AttendanceRecord.objects.filter(
                        student=enrollment.student,
                        status=AttendanceRecord.AttendanceStatus.ABSENT,
                        created_at__gte=date - timedelta(days=30),
                    ).count()

                    if recent_absences >= 3:
                        # Log chronic absence alert
                        log_activity(
                            user=user,
                            category=ActivityCategory.ALERT,
                            description=f"Chronic absence alert for {enrollment.student.student_id}",
                            target_object=enrollment.student,
                            metadata={
                                "course_code": section.course.code,
                                "recent_absences": recent_absences,
                                "threshold": 3,
                                "alert_type": "chronic_absence",
                            },
                            visibility=ActivityVisibility.DEPARTMENT,
                        )

                elif record["status"] == AttendanceRecord.AttendanceStatus.LATE:
                    late_count += 1
                elif record["status"] == AttendanceRecord.AttendanceStatus.PERMISSION:
                    excused_count += 1

        # Summary metadata (automatically logged by decorator)
        return {
            "date": date.isoformat(),
            "section": f"{section.course.code} - {section.section_id}",
            "total_enrolled": section.class_header_enrollments.filter(status=EnrollmentStatus.ENROLLED).count(),
            "recorded": len(attendance_data),
            "present": present_count,
            "absent": absent_count,
            "late": late_count,
            "excused": excused_count,
            "attendance_rate": (
                round((present_count + late_count) / len(attendance_data) * 100, 1) if attendance_data else 0
            ),
        }
