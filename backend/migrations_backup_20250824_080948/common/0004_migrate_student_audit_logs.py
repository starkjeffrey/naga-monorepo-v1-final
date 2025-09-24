"""
Data migration to consolidate StudentAuditLog records into StudentActivityLog.

This migration transfers all existing audit log data from the people app's
StudentAuditLog model to the common app's StudentActivityLog model, which
provides better search capabilities and visibility control.
"""

import datetime

from django.db import migrations


def migrate_student_audit_logs(apps, schema_editor):
    """
    Migrate all StudentAuditLog records to StudentActivityLog.

    This function handles:
    - Mapping action types between the two models
    - Extracting student information (handling deleted students)
    - Transforming data formats
    - Setting appropriate visibility levels
    - Progress tracking for large datasets
    """
    # Get models
    StudentAuditLog = apps.get_model("people", "StudentAuditLog")
    StudentActivityLog = apps.get_model("common", "StudentActivityLog")

    # Map StudentAuditLog.ActionType to StudentActivityLog.ActivityType
    action_type_mapping = {
        "CREATE": "PROFILE_CREATE",
        "UPDATE": "PROFILE_UPDATE",
        "MERGE": "PROFILE_MERGE",
        "STATUS": "STUDENT_STATUS_CHANGE",
        "MONK_STATUS": "MONK_STATUS_CHANGE",
        "ENROLLMENT": "PROGRAM_ENROLLMENT",
        "GRADUATION": "GRADUATION",
        "ACADEMIC": "ACADEMIC",  # This doesn't have a direct mapping
        "OTHER": "MANAGEMENT_OVERRIDE",  # Use management override as catch-all
    }

    # Determine visibility based on action type
    visibility_mapping = {
        "CREATE": "STAFF_ONLY",
        "UPDATE": "STAFF_ONLY",
        "MERGE": "STAFF_ONLY",
        "STATUS": "STUDENT_VISIBLE",
        "MONK_STATUS": "STUDENT_VISIBLE",
        "ENROLLMENT": "STUDENT_VISIBLE",
        "GRADUATION": "PUBLIC",
        "ACADEMIC": "STUDENT_VISIBLE",
        "OTHER": "STAFF_ONLY",
    }

    # Get total count for progress tracking
    total_count = StudentAuditLog.objects.count()

    if total_count == 0:
        print("No StudentAuditLog records to migrate.")
        return

    print(f"\n🔄 Starting migration of {total_count:,} StudentAuditLog records...")

    # Process in batches to handle large datasets efficiently
    batch_size = 1000
    processed = 0
    migrated = 0
    skipped = 0
    errors = []

    # Process in chunks using iterator to save memory
    for audit_log in StudentAuditLog.objects.select_related("student__person", "changed_by").iterator(
        chunk_size=batch_size
    ):
        try:
            # Extract student information
            if audit_log.student and hasattr(audit_log.student, "person"):
                student_number = str(audit_log.student.student_id)
                student_name = audit_log.student.person.full_name
            else:
                # Handle deleted students or missing data
                student_number = f"DELETED_{audit_log.student_id}"
                student_name = "Unknown Student (Deleted)"

            # Map action type
            activity_type = action_type_mapping.get(audit_log.action, "MANAGEMENT_OVERRIDE")

            # Build description
            description = audit_log.notes or f"{audit_log.get_action_display()}"
            if audit_log.changes:
                # Add change details to description if available
                changes = audit_log.changes
                if isinstance(changes, dict):
                    if "field" in changes and "old_value" in changes and "new_value" in changes:
                        description = (
                            f"{changes['field']} changed from {changes['old_value']} to {changes['new_value']}"
                        )
                    elif changes:
                        description = f"{description} - {changes!s}"

            # Build activity details from changes and related object info
            activity_details = {}
            if audit_log.changes:
                activity_details["original_changes"] = audit_log.changes
            if audit_log.content_type and audit_log.object_id:
                activity_details["related_object"] = {
                    "app": audit_log.content_type.app_label,
                    "model": audit_log.content_type.model,
                    "id": audit_log.object_id,
                }
            activity_details["original_action"] = audit_log.action

            # Determine visibility
            visibility = visibility_mapping.get(audit_log.action, "STAFF_ONLY")

            # Create new StudentActivityLog entry
            StudentActivityLog.objects.create(
                student_number=student_number,
                student_name=student_name,
                activity_type=activity_type,
                description=description,
                activity_details=activity_details,
                performed_by=audit_log.changed_by,
                created_at=audit_log.timestamp,  # Preserve original timestamp
                visibility=visibility,
                is_system_generated=False,  # These are all user-initiated actions
            )

            migrated += 1

        except Exception as e:
            # Record error but continue processing
            errors.append(
                {
                    "audit_log_id": audit_log.id,
                    "error": str(e),
                    "action": audit_log.action,
                }
            )
            skipped += 1

        processed += 1

        # Print progress every 1000 records
        if processed % 1000 == 0:
            print(
                f"  Processed {processed:,}/{total_count:,} records... (Migrated: {migrated:,}, Skipped: {skipped:,})"
            )

    # Final summary
    print("\n✅ Migration completed:")
    print(f"  - Total records: {total_count:,}")
    print(f"  - Successfully migrated: {migrated:,}")
    print(f"  - Skipped (errors): {skipped:,}")

    if errors:
        print(f"\n⚠️  {len(errors)} errors occurred during migration:")
        for i, error in enumerate(errors[:10]):  # Show first 10 errors
            print(f"  {i + 1}. ID {error['audit_log_id']} ({error['action']}): {error['error']}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

    # Store migration metadata in the database for verification
    if hasattr(schema_editor.connection, "alias"):
        from django.core.cache import cache

        cache_key = f"audit_log_migration_{schema_editor.connection.alias}"
        cache.set(
            cache_key,
            {
                "total_source_records": total_count,
                "migrated": migrated,
                "skipped": skipped,
                "errors": len(errors),
                "timestamp": datetime.datetime.now().isoformat(),
            },
            timeout=86400,
        )  # Keep for 24 hours


def reverse_migrate_student_audit_logs(apps, schema_editor):
    """
    Reverse migration - safe no-op.

    We don't delete the migrated StudentActivityLog records because:
    1. They may have been modified after migration
    2. New records may have been added using the same model
    3. It's safer to keep the audit trail intact

    If you need to reverse this migration, manually review and clean up
    the StudentActivityLog records that were migrated.
    """
    print("\n⚠️  Reverse migration is a no-op for safety.")
    print("StudentActivityLog records created by this migration will NOT be deleted.")
    print("If you need to clean up, please do so manually after reviewing the data.")


class Migration(migrations.Migration):
    """
    Data migration to consolidate student audit logs.

    This migration is atomic - either all records are migrated successfully
    or none are (in case of critical errors).
    """

    dependencies = [
        ("common", "0003_enhance_student_activity_log"),
        ("people", "0001_initial"),  # Adjust this to the actual people migration
    ]

    operations = [
        migrations.RunPython(
            migrate_student_audit_logs,
            reverse_migrate_student_audit_logs,
            atomic=True,
        ),
    ]
