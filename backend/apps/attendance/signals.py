"""Attendance app signals for automated workflows.

This module provides signal handlers for:
- Automatic attendance statistics updates
- Permission request notifications
- Roster sync triggers
- External system integrations
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import AttendanceRecord, AttendanceSession, PermissionRequest


@receiver(post_save, sender=AttendanceRecord)
def update_session_statistics(sender, instance, created, **kwargs):
    """Update attendance session statistics when attendance records change.

    This ensures session totals are always accurate in real-time.
    """
    if instance.attendance_session:
        instance.attendance_session.update_statistics()


@receiver(post_save, sender=PermissionRequest)
def handle_permission_request_approval(sender, instance, created, **kwargs):
    """Handle permission request approvals and create attendance records.

    When permission requests are approved, create corresponding
    attendance records with PERMISSION status.
    """
    if not created and instance.request_status == PermissionRequest.RequestStatus.APPROVED:
        # Check if attendance session exists for this date
        try:
            session = AttendanceSession.objects.get(
                class_part=instance.class_part,
                session_date=instance.session_date,
            )

            # Create or update attendance record
            record, created = AttendanceRecord.objects.get_or_create(
                attendance_session=session,
                student=instance.student,
                defaults={
                    "status": AttendanceRecord.AttendanceStatus.PERMISSION,
                    "data_source": AttendanceRecord.DataSource.PERMISSION_REQUEST,
                    "permission_reason": instance.reason,
                    "permission_approved": True,
                    "permission_approved_by": instance.approved_by,
                    "permission_notes": instance.approval_notes,
                },
            )

            if not created:
                # Update existing record
                record.status = AttendanceRecord.AttendanceStatus.PERMISSION
                record.permission_approved = True
                record.permission_approved_by = instance.approved_by
                record.permission_reason = instance.reason
                record.permission_notes = instance.approval_notes
                record.save()

        except AttendanceSession.DoesNotExist:
            # Session doesn't exist yet - the record will be created
            # when the teacher starts the session
            pass


@receiver(pre_delete, sender=AttendanceSession)
def archive_attendance_before_deletion(sender, instance, **kwargs):
    """Archive attendance data before session deletion.

    Prevents data loss by creating archive records.
    """
    from .models import AttendanceArchive

    # Get all attendance records for this session
    records = instance.attendance_records.select_related("student")

    # Group by student to create archive entries
    for record in records:
        # Check if archive already exists for this student/class/term
        AttendanceArchive.objects.update_or_create(
            student=record.student,
            class_part=instance.class_part,
            term=instance.class_part.class_session.class_header.term,
            defaults={
                "total_sessions": 1,
                "present_sessions": 1 if record.is_present else 0,
                "absent_sessions": 1 if record.status == AttendanceRecord.AttendanceStatus.ABSENT else 0,
                "late_sessions": 1 if record.status == AttendanceRecord.AttendanceStatus.LATE else 0,
                "excused_sessions": 1 if record.status == AttendanceRecord.AttendanceStatus.PERMISSION else 0,
                "attendance_percentage": 100.0 if record.is_present else 0.0,
                "punctuality_percentage": 100.0 if record.status == AttendanceRecord.AttendanceStatus.PRESENT else 0.0,
                "archived_by": instance.created_by,
                "session_details": {
                    "sessions": [
                        {"date": instance.session_date.isoformat(), "status": record.status, "notes": record.notes}
                    ]
                },
            },
        )
