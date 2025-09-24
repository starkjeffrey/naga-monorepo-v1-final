"""Audit Integration Examples

This module demonstrates how to integrate the new audit logging system
into existing views, services, and signal handlers.
"""

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.common.audit.decorators import audit_action
from apps.common.audit.helpers import log_activity, log_bulk_activity
from apps.common.audit.models import ActivityCategory, ActivityVisibility
from apps.people.models import Person, Student


# Example 1: View using the decorator
@login_required
@require_http_methods(["POST"])
@audit_action(
    category=ActivityCategory.UPDATE,
    description="Update user profile",
    visibility=ActivityVisibility.INTERNAL,
)
def update_profile_view(request, person_id):
    """Example view showing decorator usage for audit logging.

    The decorator automatically:
    - Logs the action
    - Captures request context
    - Records success/failure
    - Handles exceptions
    """
    person = get_object_or_404(Person, id=person_id)

    # Update logic
    person.first_name = request.POST.get("first_name", person.first_name)
    person.last_name = request.POST.get("last_name", person.last_name)
    person.email_address = request.POST.get("email", person.email_address)
    person.save()

    return JsonResponse({"status": "success", "message": "Profile updated successfully"})


# Example 2: Service method using helper functions
class StudentService:
    """Example service showing direct helper function usage."""

    @staticmethod
    def change_student_status(student_id: int, new_status: str, reason: str, user):
        """Change student status with audit logging.

        This example shows:
        - Direct log_activity usage
        - Recording old and new values
        - Adding metadata
        - Error handling
        """
        try:
            with transaction.atomic():
                student = Student.objects.select_for_update().get(id=student_id)
                old_status = student.status

                # Perform the status change
                student.status = new_status
                student.save()

                # Log the activity
                log_activity(
                    user=user,
                    category=ActivityCategory.STATUS_CHANGE,
                    description=f"Changed student status from {old_status} to {new_status}",
                    target_object=student,
                    metadata={
                        "old_status": old_status,
                        "new_status": new_status,
                        "reason": reason,
                        "student_code": student.student_code,
                    },
                    visibility=ActivityVisibility.DEPARTMENT,  # Visible to department staff
                )

                return student

        except Student.DoesNotExist:
            log_activity(
                user=user,
                category=ActivityCategory.STATUS_CHANGE,
                description=f"Failed to change status - student {student_id} not found",
                metadata={
                    "student_id": student_id,
                    "attempted_status": new_status,
                    "error": "Student not found",
                },
                visibility=ActivityVisibility.ADMIN,  # Only admins see errors
            )
            raise

    @staticmethod
    def enroll_multiple_students(course_id: int, student_ids: list, user):
        """Example of batch operation with bulk logging.

        Shows:
        - Bulk activity logging
        - Transaction handling
        - Success/failure tracking
        """
        from apps.enrollment.models import Course, Enrollment

        course = Course.objects.get(id=course_id)
        successful_enrollments = []
        failed_enrollments = []

        with transaction.atomic():
            for student_id in student_ids:
                try:
                    student = Student.objects.get(id=student_id)
                    enrollment = Enrollment.objects.create(student=student, course=course, status="ENROLLED")
                    successful_enrollments.append(
                        {
                            "student_id": student_id,
                            "student_code": student.student_code,
                            "enrollment_id": enrollment.id,
                        },
                    )
                except Exception as e:
                    failed_enrollments.append({"student_id": student_id, "error": str(e)})

            # Log bulk activity
            log_bulk_activity(
                user=user,
                category=ActivityCategory.ENROLLMENT,
                base_description=f"Bulk enrollment in {course.code}",
                objects=[
                    {
                        "model": "enrollment.Enrollment",
                        "id": item["enrollment_id"],
                        "description": f"Enrolled student {item['student_code']}",
                    }
                    for item in successful_enrollments
                ],
                metadata={
                    "course_code": course.code,
                    "course_name": course.title,
                    "total_attempted": len(student_ids),
                    "successful": len(successful_enrollments),
                    "failed": len(failed_enrollments),
                    "failed_details": failed_enrollments,
                },
                visibility=ActivityVisibility.DEPARTMENT,
            )

        return successful_enrollments, failed_enrollments


# Example 3: Signal handler for automatic logging
@receiver(post_save, sender=Person)
def log_person_changes(sender, instance, created, **kwargs):
    """Automatically log person creation or updates.

    Shows:
    - Signal-based automatic logging
    - Handling created vs updated
    - System-initiated logging
    """
    # Skip if this is a system update (to avoid infinite loops)
    if getattr(instance, "_skip_audit_log", False):
        return

    # Get the user from the current request if available
    from apps.common.middleware import get_current_user

    user = get_current_user()

    if created:
        log_activity(
            user=user,  # Will be None for system actions
            category=ActivityCategory.CREATE,
            description=f"Created person profile: {instance.get_full_name()}",
            target_object=instance,
            metadata={
                "person_type": instance.person_type,
                "email": instance.email_address,
                "created_via": "signal_handler",
            },
            visibility=ActivityVisibility.INTERNAL,
        )
    else:
        # For updates, track what changed
        if instance.tracker.changed():
            changes = {
                field: {
                    "old": instance.tracker.previous(field),
                    "new": getattr(instance, field),
                }
                for field in instance.tracker.changed()
            }

            log_activity(
                user=user,
                category=ActivityCategory.UPDATE,
                description=f"Updated person profile: {instance.get_full_name()}",
                target_object=instance,
                metadata={"changes": changes, "updated_via": "signal_handler"},
                visibility=ActivityVisibility.INTERNAL,
            )


# Example 4: Complex operation with nested logging
class GradeService:
    """Example showing complex operations with multiple log points."""

    @staticmethod
    @audit_action(
        category=ActivityCategory.GRADE_CHANGE,
        description="Process final grades",
        visibility=ActivityVisibility.DEPARTMENT,
    )
    def process_final_grades(course_id: int, grades_data: dict, user):
        """Process final grades with comprehensive logging.

        Shows:
        - Decorator combined with manual logging
        - Nested operations
        - Detailed metadata
        """
        from apps.enrollment.models import Course, Enrollment
        from apps.grading.models import Grade

        course = Course.objects.get(id=course_id)
        processed_grades = []

        with transaction.atomic():
            for student_id, grade_info in grades_data.items():
                enrollment = Enrollment.objects.get(course=course, student_id=student_id)

                # Get or create grade
                grade, created = Grade.objects.get_or_create(
                    enrollment=enrollment,
                    defaults={"grade": grade_info["grade"]},
                )

                if not created:
                    old_grade = grade.grade
                    grade.grade = grade_info["grade"]
                    grade.save()

                    # Log individual grade change
                    log_activity(
                        user=user,
                        category=ActivityCategory.GRADE_CHANGE,
                        description=f"Changed grade from {old_grade} to {grade.grade}",
                        target_object=grade,
                        metadata={
                            "student_code": enrollment.student.student_code,
                            "course_code": course.code,
                            "old_grade": old_grade,
                            "new_grade": grade.grade,
                            "reason": grade_info.get("reason", "Final grade entry"),
                        },
                        visibility=ActivityVisibility.STUDENT,  # Students can see their own grades
                    )

                processed_grades.append({"student_id": student_id, "grade": grade.grade, "created": created})

        # The decorator will automatically log the overall operation
        # We can access the created log entry if needed
        return processed_grades


# Example 5: Error handling and recovery
def safe_operation_with_logging(operation_func, *args, **kwargs):
    """Wrapper showing error handling with audit logging.

    Shows:
    - Logging both success and failure
    - Error details in metadata
    - Appropriate visibility for errors
    """
    from apps.common.middleware import get_current_user

    user = get_current_user()

    try:
        result = operation_func(*args, **kwargs)

        log_activity(
            user=user,
            category=ActivityCategory.SYSTEM,
            description=f"Successfully completed {operation_func.__name__}",
            metadata={
                "function": operation_func.__name__,
                "args": str(args)[:100],  # Truncate for safety
                "success": True,
            },
            visibility=ActivityVisibility.INTERNAL,
        )

        return result

    except Exception as e:
        log_activity(
            user=user,
            category=ActivityCategory.ERROR,
            description=f"Error in {operation_func.__name__}: {e!s}",
            metadata={
                "function": operation_func.__name__,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "args": str(args)[:100],
            },
            visibility=ActivityVisibility.ADMIN,  # Only admins see error details
        )
        raise


# Example 6: Custom visibility rules
def log_sensitive_operation(user, action: str, target, details: dict):
    """Example of custom visibility rules for sensitive operations.

    Shows:
    - Conditional visibility
    - Redacting sensitive data
    - Role-based visibility
    """
    # Determine visibility based on the operation
    if "financial" in action.lower():
        visibility = ActivityVisibility.ADMIN
        # Redact sensitive financial data
        safe_details = {k: "***" if k in ["account_number", "amount"] else v for k, v in details.items()}
    elif "grade" in action.lower():
        visibility = ActivityVisibility.DEPARTMENT
        safe_details = details
    else:
        visibility = ActivityVisibility.INTERNAL
        safe_details = details

    log_activity(
        user=user,
        category=ActivityCategory.UPDATE,
        description=action,
        target_object=target,
        metadata=safe_details,
        visibility=visibility,
    )
