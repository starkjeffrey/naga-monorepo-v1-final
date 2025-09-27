"""People App Audit Integration Examples

This module shows how to replace StudentAuditLog with the new
StudentActivityLog system in the people app views.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.common.audit.decorators import audit_action
from apps.common.audit.helpers import log_activity
from apps.common.audit.models import ActivityCategory, ActivityVisibility
from apps.people.models import EmergencyContact, Student


# Before: Using old StudentAuditLog
def old_update_student_status(request, student_id):
    """OLD METHOD - DO NOT USE"""
    from apps.people.models import StudentAuditLog

    student = get_object_or_404(Student, id=student_id)
    old_status = student.status
    new_status = request.POST.get("status")

    student.status = new_status
    student.save()

    # Old way - limited functionality
    StudentAuditLog.objects.create(
        student=student,
        user=request.user,
        action="status_change",
        details=f"Changed from {old_status} to {new_status}",
    )

    return redirect("student_detail", student_id=student.id)


# After: Using new StudentActivityLog with decorator
@login_required
@require_http_methods(["POST"])
@audit_action(
    category=ActivityCategory.STATUS_CHANGE,
    description="Update student status",
    visibility=ActivityVisibility.DEPARTMENT,
)
def update_student_status(request, student_id):
    """NEW METHOD - Update student status with comprehensive audit logging.

    Benefits:
    - Automatic exception handling
    - Request context captured
    - Standardized categories
    - Configurable visibility
    """
    student = get_object_or_404(Student, id=student_id)
    old_status = student.status
    new_status = request.POST.get("status")
    reason = request.POST.get("reason", "")

    # Validate status transition
    valid_transitions = {
        "ACTIVE": ["INACTIVE", "SUSPENDED", "GRADUATED"],
        "INACTIVE": ["ACTIVE", "WITHDRAWN"],
        "SUSPENDED": ["ACTIVE", "WITHDRAWN"],
        "GRADUATED": [],  # No transitions from graduated
        "WITHDRAWN": ["ACTIVE"],  # Can re-enroll
    }

    if new_status not in valid_transitions.get(old_status, []):
        messages.error(request, f"Invalid status transition from {old_status} to {new_status}")
        return redirect("student_detail", student_id=student.id)

    # Update status
    with transaction.atomic():
        student.status = new_status
        student.save()

        # The decorator handles basic logging, but we can add more detail
        # by accessing the student's activity log
        from apps.people.models import StudentActivityLog

        StudentActivityLog.objects.create(
            student=student,
            user=request.user,
            category=ActivityCategory.STATUS_CHANGE,
            description=f"Status changed from {old_status} to {new_status}",
            metadata={
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
            visibility=ActivityVisibility.DEPARTMENT,
        )

    messages.success(request, f"Student status updated to {new_status}")
    return redirect("student_detail", student_id=student.id)


# Profile update with manual logging for more control
@login_required
@require_http_methods(["POST"])
def update_student_profile(request, student_id):
    """Update student profile with detailed change tracking.

    Shows:
    - Manual logging for fine control
    - Tracking specific field changes
    - Different visibility for different updates
    """
    student = get_object_or_404(Student, id=student_id)
    person = student.person

    # Track what fields are changing
    changes = {}
    sensitive_changes = {}

    # Personal information
    if request.POST.get("first_name") != person.first_name:
        changes["first_name"] = {
            "old": person.first_name,
            "new": request.POST.get("first_name"),
        }
        person.first_name = request.POST.get("first_name")

    if request.POST.get("last_name") != person.last_name:
        changes["last_name"] = {
            "old": person.last_name,
            "new": request.POST.get("last_name"),
        }
        person.last_name = request.POST.get("last_name")

    # Contact information (more sensitive)
    if request.POST.get("email") != person.email:
        sensitive_changes["email"] = {
            "old": person.email,
            "new": request.POST.get("email"),
        }
        person.email = request.POST.get("email")

    if request.POST.get("phone") != person.phone:
        sensitive_changes["phone"] = {
            "old": person.phone,
            "new": request.POST.get("phone"),
        }
        person.phone = request.POST.get("phone")

    # Student-specific fields
    if request.POST.get("major_id") and request.POST.get("major_id") != str(student.major_id):
        changes["major"] = {
            "old": student.major.name if student.major else None,
            "new_id": request.POST.get("major_id"),
        }
        student.major_id = request.POST.get("major_id")

    # Save changes
    with transaction.atomic():
        if changes or sensitive_changes:
            person.save()
            student.save()

            # Log personal information changes (internal visibility)
            if changes:
                log_activity(
                    user=request.user,
                    category=ActivityCategory.UPDATE,
                    description="Updated student profile information",
                    target_object=student,
                    metadata={"changes": changes, "update_type": "profile"},
                    visibility=ActivityVisibility.INTERNAL,
                )

            # Log sensitive changes (admin only)
            if sensitive_changes:
                log_activity(
                    user=request.user,
                    category=ActivityCategory.UPDATE,
                    description="Updated student contact information",
                    target_object=student,
                    metadata={
                        "changes": sensitive_changes,
                        "update_type": "contact",
                        "requires_verification": True,
                    },
                    visibility=ActivityVisibility.ADMIN,
                )

            messages.success(request, "Student profile updated successfully")
        else:
            messages.info(request, "No changes detected")

    return redirect("student_detail", student_id=student.id)


# Emergency contact update with related object logging
@login_required
def update_emergency_contacts(request, student_id):
    """Update emergency contacts with audit trail.

    Shows:
    - Logging related object changes
    - Batch operations
    - Parent-child relationships in logs
    """
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        # Get existing contacts
        existing_contacts = {str(ec.id): ec for ec in student.person.emergency_contacts.all()}

        updated_contacts = []
        new_contacts = []
        deleted_ids = []

        # Process form data
        contact_count = int(request.POST.get("contact_count", 0))

        with transaction.atomic():
            for i in range(contact_count):
                contact_id = request.POST.get(f"contact_{i}_id")
                name = request.POST.get(f"contact_{i}_name")
                relationship = request.POST.get(f"contact_{i}_relationship")
                phone = request.POST.get(f"contact_{i}_phone")
                delete = request.POST.get(f"contact_{i}_delete") == "true"

                if contact_id and contact_id in existing_contacts:
                    # Update existing
                    contact = existing_contacts[contact_id]

                    if delete:
                        deleted_ids.append(contact_id)
                        contact.delete()
                    else:
                        # Track changes
                        changes = {}
                        if contact.name != name:
                            changes["name"] = {"old": contact.name, "new": name}
                        if contact.relationship != relationship:
                            changes["relationship"] = {
                                "old": contact.relationship,
                                "new": relationship,
                            }
                        if contact.phone != phone:
                            changes["phone"] = {"old": contact.phone, "new": phone}

                        if changes:
                            contact.name = name
                            contact.relationship = relationship
                            contact.phone = phone
                            contact.save()
                            updated_contacts.append((contact, changes))

                elif name and not delete:
                    # Create new
                    contact = EmergencyContact.objects.create(
                        person=student.person,
                        name=name,
                        relationship=relationship,
                        phone=phone,
                    )
                    new_contacts.append(contact)

            # Log all changes in one comprehensive entry
            metadata = {
                "student_code": student.student_code,
                "total_contacts": student.person.emergency_contacts.count(),
                "created": len(new_contacts),
                "updated": len(updated_contacts),
                "deleted": len(deleted_ids),
            }

            if new_contacts:
                metadata["new_contacts"] = [{"name": c.name, "relationship": c.relationship} for c in new_contacts]

            if updated_contacts:
                metadata["updated_contacts"] = [
                    {"name": c.name, "changes": changes} for c, changes in updated_contacts
                ]

            if deleted_ids:
                metadata["deleted_contact_ids"] = deleted_ids

            log_activity(
                user=request.user,
                category=ActivityCategory.UPDATE,
                description="Updated emergency contacts",
                target_object=student,
                metadata=metadata,
                visibility=ActivityVisibility.INTERNAL,
            )

        messages.success(request, "Emergency contacts updated successfully")
        return redirect("student_detail", student_id=student.id)

    # GET request - show form
    return render(
        request,
        "people/emergency_contacts_form.html",
        {"student": student, "contacts": student.person.emergency_contacts.all()},
    )


# API endpoint with audit logging
@login_required
@require_http_methods(["GET"])
def student_activity_history_api(request, student_id):
    """API endpoint to retrieve student activity history.

    Shows:
    - Querying activity logs
    - Filtering by visibility
    - Returning audit trail via API
    """
    student = get_object_or_404(Student, id=student_id)

    # Check permissions
    user = request.user
    if user.is_superuser:
        visibility_filter = None  # See all
    elif user.groups.filter(name="Department Staff").exists():
        visibility_filter = [
            ActivityVisibility.PUBLIC,
            ActivityVisibility.STUDENT,
            ActivityVisibility.DEPARTMENT,
        ]
    elif student.person.user == user:
        visibility_filter = [ActivityVisibility.PUBLIC, ActivityVisibility.STUDENT]
    else:
        visibility_filter = [ActivityVisibility.PUBLIC]

    # Get activities
    from apps.people.models import StudentActivityLog

    activities = StudentActivityLog.objects.filter(student=student)

    if visibility_filter:
        activities = activities.filter(visibility__in=visibility_filter)

    # Pagination
    page = int(request.GET.get("page", 1))
    per_page = int(request.GET.get("per_page", 20))
    offset = (page - 1) * per_page

    activities = activities.order_by("-created_at")[offset : offset + per_page]

    # Format response
    activity_data = [
        {
            "id": activity.id,
            "category": activity.category,
            "description": activity.description,
            "created_at": activity.created_at.isoformat(),
            "user": activity.user.get_full_name() if activity.user else "System",
            "metadata": activity.metadata,
            "visibility": activity.visibility,
        }
        for activity in activities
    ]

    # Log API access
    log_activity(
        user=request.user,
        category=ActivityCategory.VIEW,
        description=f"Accessed activity history for student {student.student_code}",
        target_object=student,
        metadata={
            "api_endpoint": "student_activity_history",
            "page": page,
            "per_page": per_page,
            "results_count": len(activity_data),
        },
        visibility=ActivityVisibility.INTERNAL,
    )

    return JsonResponse(
        {
            "student_id": student.id,
            "student_code": student.student_code,
            "activities": activity_data,
            "page": page,
            "per_page": per_page,
            "has_more": len(activity_data) == per_page,
        },
    )
