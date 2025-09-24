"""Audit logging utilities for the Naga SIS project.

This module provides helper functions for common audit scenarios, batch logging,
and migration utilities for transitioning from StudentAuditLog to StudentActivityLog.

USAGE PATTERNS:

1. Batch logging student activities:
   batch_log_student_activities([
       {
           'student': student1,
           'activity_type': StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
           'description': 'Enrolled in CS101',
           'user': request.user,
       },
       # ... more activities
   ])

2. Migrate existing audit logs:
   migrate_student_audit_logs(
       source_queryset=StudentAuditLog.objects.filter(student__student_id='12345'),
       dry_run=True
   )

3. Bulk status changes:
   log_bulk_status_change(
       students=[student1, student2],
       old_status='active',
       new_status='graduated',
       user=request.user,
       reason='End of program'
   )
"""

import logging
from datetime import datetime
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


def batch_log_student_activities(activities: list[dict[str, Any]], batch_size: int = 100) -> int:
    """Create multiple student activity logs in batches for efficiency.

    Args:
        activities: List of dictionaries containing activity data
        batch_size: Number of records to create per batch

    Returns:
        Number of activities logged

    Example:
        batch_log_student_activities([
            {
                'student': student_obj,  # or student_number string
                'activity_type': StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
                'description': 'Enrolled in Math 101',
                'user': request.user,
                'term': term_obj,  # optional
                'class_header': class_obj,  # optional
                'visibility': 'STUDENT_VISIBLE',  # optional
            },
            # ... more activities
        ])
    """
    from apps.common.models import StudentActivityLog

    created_count = 0

    # Process in batches
    for i in range(0, len(activities), batch_size):
        batch = activities[i : i + batch_size]
        objects_to_create = []

        for activity_data in batch:
            try:
                # Extract student information
                student = activity_data.get("student")
                student_number = None
                student_name = ""

                if student is not None and hasattr(student, "student_id"):
                    student_number = str(student.student_id)
                    if hasattr(student, "person"):
                        student_name = student.person.full_name
                elif isinstance(student, str):
                    student_number = student
                elif "student_number" in activity_data:
                    student_number = activity_data["student_number"]
                    student_name = activity_data.get("student_name", "")

                if not student_number:
                    logger.warning(
                        "Skipping activity log - no student number found: %s",
                        activity_data,
                    )
                    continue

                # Build the log entry
                log_entry = StudentActivityLog(
                    student_number=student_number,
                    student_name=student_name,
                    activity_type=activity_data["activity_type"],
                    description=activity_data["description"],
                    performed_by=activity_data.get("user") or User.objects.get(username="system"),
                    is_system_generated=activity_data.get("is_system_generated", False),
                    visibility=activity_data.get("visibility", StudentActivityLog.VisibilityLevel.STAFF_ONLY),
                    activity_details=activity_data.get("activity_details", {}),
                )

                # Add optional context
                if activity_data.get("term"):
                    log_entry.term_name = activity_data["term"].code

                if activity_data.get("class_header"):
                    class_header = activity_data["class_header"]
                    if hasattr(class_header, "course"):
                        log_entry.class_code = class_header.course.code
                    if hasattr(class_header, "section_id"):
                        log_entry.class_section = class_header.section_id

                if "program_name" in activity_data:
                    log_entry.program_name = activity_data["program_name"]

                objects_to_create.append(log_entry)

            except Exception as e:
                logger.error("Error preparing activity log: %s", e, exc_info=True)

        # Bulk create the batch
        if objects_to_create:
            with transaction.atomic():
                StudentActivityLog.objects.bulk_create(objects_to_create)
                created_count += len(objects_to_create)

    return created_count


def migrate_student_audit_logs(
    source_queryset=None,
    dry_run: bool = True,
    batch_size: int = 100,
    visibility_mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Migrate records from people.StudentAuditLog to common.StudentActivityLog.

    Args:
        source_queryset: QuerySet of StudentAuditLog records to migrate
        dry_run: If True, don't actually create records, just report what would happen
        batch_size: Number of records to process at a time
        visibility_mapping: Custom mapping of action types to visibility levels

    Returns:
        Dictionary with migration statistics

    Example:
        result = migrate_student_audit_logs(
            source_queryset=StudentAuditLog.objects.filter(timestamp__gte='2024-01-01'),
            dry_run=False
        )
        print(f"Migrated {result['migrated']} records")
    """
    from apps.common.models import StudentActivityLog

    # Import StudentAuditLog dynamically to avoid circular imports
    try:
        from apps.people.models import StudentAuditLog as SourceModel
    except ImportError:
        logger.error("Cannot import StudentAuditLog from apps.people.models")
        return {"error": "Import failed", "migrated": 0}

    # Default visibility mapping
    default_visibility = {
        "CREATE": StudentActivityLog.VisibilityLevel.STAFF_ONLY,
        "UPDATE": StudentActivityLog.VisibilityLevel.STAFF_ONLY,
        "MERGE": StudentActivityLog.VisibilityLevel.STAFF_ONLY,
        "STATUS": StudentActivityLog.VisibilityLevel.STUDENT_VISIBLE,
        "MONK_STATUS": StudentActivityLog.VisibilityLevel.STUDENT_VISIBLE,
        "ENROLLMENT": StudentActivityLog.VisibilityLevel.STUDENT_VISIBLE,
        "GRADUATION": StudentActivityLog.VisibilityLevel.PUBLIC,
        "ACADEMIC": StudentActivityLog.VisibilityLevel.STUDENT_VISIBLE,
        "OTHER": StudentActivityLog.VisibilityLevel.STAFF_ONLY,
    }

    if visibility_mapping:
        # Convert string values to VisibilityLevel enum values
        enum_mapping = {
            key: getattr(StudentActivityLog.VisibilityLevel, value)
            for key, value in visibility_mapping.items()
            if hasattr(StudentActivityLog.VisibilityLevel, value)
        }
        default_visibility.update(enum_mapping)

    # Activity type mapping from old to new
    activity_type_map = {
        "CREATE": StudentActivityLog.ActivityType.PROFILE_CREATE,
        "UPDATE": StudentActivityLog.ActivityType.PROFILE_UPDATE,
        "MERGE": StudentActivityLog.ActivityType.PROFILE_MERGE,
        "STATUS": StudentActivityLog.ActivityType.STUDENT_STATUS_CHANGE,
        "MONK_STATUS": StudentActivityLog.ActivityType.MONK_STATUS_CHANGE,
        "ENROLLMENT": StudentActivityLog.ActivityType.PROGRAM_ENROLLMENT,
        "GRADUATION": StudentActivityLog.ActivityType.GRADUATION,
        "ACADEMIC": StudentActivityLog.ActivityType.PROGRAM_ENROLLMENT,
        "OTHER": StudentActivityLog.ActivityType.PROFILE_UPDATE,
    }

    if source_queryset is None:
        source_queryset = SourceModel.objects.all()

    stats = {
        "total": source_queryset.count(),
        "migrated": 0,
        "skipped": 0,
        "errors": 0,
        "dry_run": dry_run,
    }

    # Process in batches
    for offset in range(0, stats["total"], batch_size):
        batch = source_queryset[offset : offset + batch_size]
        objects_to_create = []

        for old_log in batch:
            try:
                # Map activity type
                new_activity_type = activity_type_map.get(
                    old_log.action,
                    StudentActivityLog.ActivityType.PROFILE_UPDATE,
                )

                # Build description
                description = old_log.notes or f"{old_log.get_action_display()}"
                if old_log.changes:
                    if "field" in old_log.changes:
                        field = old_log.changes["field"]
                        old_val = old_log.changes.get("old_value", "N/A")
                        new_val = old_log.changes.get("new_value", "N/A")
                        description = f"{field} changed from {old_val} to {new_val}"

                # Extract student info
                student_number = str(old_log.student.student_id)
                student_name = old_log.student.person.full_name if hasattr(old_log.student, "person") else ""

                # Build activity details
                activity_details = {
                    "migrated_from": "StudentAuditLog",
                    "original_id": old_log.id,
                    "original_action": old_log.action,
                }
                if old_log.changes:
                    activity_details["changes"] = old_log.changes

                # Handle related object
                if old_log.content_type and old_log.object_id:
                    activity_details["related_content_type"] = old_log.content_type.model
                    activity_details["related_object_id"] = old_log.object_id

                new_log = StudentActivityLog(
                    student_number=student_number,
                    student_name=student_name,
                    activity_type=new_activity_type,
                    description=description,
                    performed_by=old_log.changed_by,
                    is_system_generated=False,
                    visibility=default_visibility.get(old_log.action, StudentActivityLog.VisibilityLevel.STAFF_ONLY),
                    activity_details=activity_details,
                    created_at=old_log.timestamp,  # Preserve original timestamp
                )

                objects_to_create.append(new_log)

            except Exception as e:
                logger.error("Error migrating audit log %s: %s", old_log.id, e, exc_info=True)
                stats["errors"] += 1

        # Create records if not dry run
        if objects_to_create and not dry_run:
            with transaction.atomic():
                StudentActivityLog.objects.bulk_create(objects_to_create)
                stats["migrated"] += len(objects_to_create)
        elif objects_to_create and dry_run:
            stats["migrated"] += len(objects_to_create)
            logger.info("Would migrate %d records (dry run)", len(objects_to_create))

    stats["skipped"] = stats["total"] - stats["migrated"] - stats["errors"]
    return stats


def log_bulk_status_change(
    students: list[Any],
    old_status: str,
    new_status: str,
    user,
    reason: str = "",
    visibility: str = "STUDENT_VISIBLE",
) -> int:
    """Log status changes for multiple students at once.

    Args:
        students: List of StudentProfile objects or student numbers
        old_status: Previous status
        new_status: New status
        user: User performing the change
        reason: Reason for the status change
        visibility: Visibility level for the logs

    Returns:
        Number of logs created
    """
    activities = []

    for student in students:
        activities.append(
            {
                "student": student,
                "activity_type": "STUDENT_STATUS_CHANGE",
                "description": f"Status changed from {old_status} to {new_status}" + (f": {reason}" if reason else ""),
                "user": user,
                "visibility": visibility,
                "activity_details": {
                    "old_status": old_status,
                    "new_status": new_status,
                    "reason": reason,
                    "bulk_change": True,
                },
            },
        )

    return batch_log_student_activities(activities)


def get_student_activity_summary(
    student_number: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    """Get a summary of a student's activities within a date range.

    Args:
        student_number: Student number to look up
        start_date: Start of date range (optional)
        end_date: End of date range (optional)

    Returns:
        Dictionary with activity summary and statistics
    """
    from apps.common.models import StudentActivityLog

    queryset = StudentActivityLog.objects.filter(student_number=student_number)

    if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__lte=end_date)

    # Get activity counts by type
    activity_counts: dict[str, int] = {}
    for activity in queryset:
        activity_type = activity.get_activity_type_display()
        activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1

    # Get recent activities
    recent_activities = list(
        queryset.order_by("-created_at")[:10].values(
            "activity_type",
            "description",
            "created_at",
            "performed_by__username",
        ),
    )

    return {
        "student_number": student_number,
        "total_activities": queryset.count(),
        "activity_counts": activity_counts,
        "recent_activities": recent_activities,
        "date_range": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        },
    }


def archive_old_activities(days_old: int = 365, batch_size: int = 1000) -> dict[str, int]:
    """Archive old student activities by moving them to a separate table or marking them.

    Args:
        days_old: Activities older than this many days will be archived
        batch_size: Number of records to process at a time

    Returns:
        Dictionary with archive statistics
    """
    from datetime import timedelta

    from apps.common.models import StudentActivityLog

    cutoff_date = timezone.now() - timedelta(days=days_old)

    old_activities = StudentActivityLog.objects.filter(created_at__lt=cutoff_date)
    total_count = old_activities.count()

    # For now, just add an "archived" flag to activity_details
    # In production, you might want to move to a separate table
    archived_count = 0

    for offset in range(0, total_count, batch_size):
        batch = old_activities[offset : offset + batch_size]

        with transaction.atomic():
            for activity in batch:
                if "archived" not in activity.activity_details:
                    activity.activity_details["archived"] = True
                    activity.activity_details["archived_date"] = timezone.now().isoformat()
                    activity.save(update_fields=["activity_details"])
                    archived_count += 1

    return {
        "total_old_activities": total_count,
        "archived": archived_count,
        "cutoff_date": cutoff_date.isoformat(),
    }
