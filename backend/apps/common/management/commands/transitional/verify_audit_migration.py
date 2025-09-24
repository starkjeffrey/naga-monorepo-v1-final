"""Verify the successful migration of StudentAuditLog to StudentActivityLog.

This command provides comprehensive verification of the audit log migration,
including record counts, data integrity checks, and sample comparisons.
"""

from typing import Any

from django.core.cache import cache
from django.db.models import Count

from apps.common.management.base_migration import BaseMigrationCommand


class Command(BaseMigrationCommand):
    """Verify StudentAuditLog to StudentActivityLog migration.

    This command:
    - Compares record counts between source and target
    - Verifies data mapping accuracy
    - Checks for missing or corrupted data
    - Generates a comprehensive verification report
    """

    help = "Verify the migration of StudentAuditLog records to StudentActivityLog"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--detailed",
            action="store_true",
            help="Include detailed record-by-record verification",
        )
        parser.add_argument(
            "--sample-size",
            type=int,
            default=100,
            help="Number of records to sample for detailed verification (default: 100)",
        )

    def get_rejection_categories(self) -> list[str]:
        """Define rejection categories for verification failures."""
        return [
            "missing_in_target",
            "data_mismatch",
            "timestamp_mismatch",
            "user_mismatch",
            "unmapped_action_type",
        ]

    def execute_migration(self, *args, **options) -> Any:
        """Execute the verification process."""
        from apps.common.models import StudentActivityLog
        from apps.people.models import StudentAuditLog

        self.stdout.write("\n🔍 Starting StudentAuditLog migration verification...")

        # Get basic counts
        source_count = StudentAuditLog.objects.count()
        self.record_input_stats(
            total_source_records=source_count,
            source_model="people.StudentAuditLog",
        )

        # Count migrated records by checking for original_action in activity_details
        migrated_count = StudentActivityLog.objects.filter(activity_details__has_key="original_action").count()

        self.record_input_stats(
            migrated_records_found=migrated_count,
            target_model="common.StudentActivityLog",
        )

        # Check cache for migration metadata
        cache_key = f"audit_log_migration_{self.style.WARNING('default')}"
        migration_metadata = cache.get(cache_key)

        if migration_metadata:
            self.stdout.write(self.style.SUCCESS("✅ Found migration metadata in cache"))
            self.record_data_integrity("migration_metadata", migration_metadata)

        # Verify counts
        self.stdout.write("\n📊 Verifying record counts...")
        self._verify_counts(source_count, migrated_count, migration_metadata)

        # Verify action type mapping
        self.stdout.write("\n🔄 Verifying action type mappings...")
        self._verify_action_mappings()

        # Verify data integrity with sampling
        if options["detailed"]:
            self.stdout.write("\n🔬 Performing detailed verification...")
            self._verify_detailed_data(options["sample_size"])

        # Check for orphaned records
        self.stdout.write("\n👤 Checking for orphaned student records...")
        self._check_orphaned_records()

        # Generate summary
        self._generate_verification_summary(source_count, migrated_count)

        return "Verification completed"

    def _verify_counts(self, source_count: int, migrated_count: int, migration_metadata: dict | None):
        """Verify record counts match expectations."""
        expected_migrated = source_count

        if migration_metadata:
            # Use metadata if available
            expected_migrated = migration_metadata.get("migrated", source_count)
            expected_skipped = migration_metadata.get("skipped", 0)

            self.record_data_integrity(
                "count_verification",
                {
                    "source_count": source_count,
                    "expected_migrated": expected_migrated,
                    "actual_migrated": migrated_count,
                    "expected_skipped": expected_skipped,
                    "count_matches": migrated_count == expected_migrated,
                },
            )

            if migrated_count == expected_migrated:
                self.stdout.write(self.style.SUCCESS(f"  ✅ Count verification passed: {migrated_count:,} records"))
            else:
                diff = expected_migrated - migrated_count
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ Count mismatch: Expected {expected_migrated:,}, "
                        f"found {migrated_count:,} (difference: {diff:,})",
                    ),
                )
                self.record_rejection(
                    "missing_in_target",
                    "count_mismatch",
                    f"Missing {diff:,} records in target",
                )
        else:
            # No metadata, just compare counts
            self.record_data_integrity(
                "count_verification",
                {
                    "source_count": source_count,
                    "migrated_count": migrated_count,
                    "metadata_available": False,
                },
            )

            self.stdout.write(f"  Source records: {source_count:,}")
            self.stdout.write(f"  Migrated records: {migrated_count:,}")

            if migrated_count < source_count:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  {source_count - migrated_count:,} records may not have been migrated"),
                )

    def _verify_action_mappings(self):
        """Verify action types were mapped correctly."""
        from apps.common.models import StudentActivityLog
        from apps.people.models import StudentAuditLog

        # Expected mappings
        action_type_mapping = {
            "CREATE": "PROFILE_CREATE",
            "UPDATE": "PROFILE_UPDATE",
            "MERGE": "PROFILE_MERGE",
            "STATUS": "STUDENT_STATUS_CHANGE",
            "MONK_STATUS": "MONK_STATUS_CHANGE",
            "ENROLLMENT": "PROGRAM_ENROLLMENT",
            "GRADUATION": "GRADUATION",
            "ACADEMIC": "ACADEMIC",
            "OTHER": "MANAGEMENT_OVERRIDE",
        }

        # Count source actions
        source_action_counts = dict(StudentAuditLog.objects.values_list("action").annotate(count=Count("id")))

        # Count migrated actions by original_action in activity_details
        migrated_actions = {}
        for activity in StudentActivityLog.objects.filter(activity_details__has_key="original_action").values(
            "activity_type",
            "activity_details",
        ):
            original_action = activity["activity_details"].get("original_action")
            if original_action:
                if original_action not in migrated_actions:
                    migrated_actions[original_action] = {}
                activity_type = activity["activity_type"]
                migrated_actions[original_action][activity_type] = (
                    migrated_actions[original_action].get(activity_type, 0) + 1
                )

        # Verify mappings
        mapping_results = {}
        for source_action, expected_target in action_type_mapping.items():
            source_count = source_action_counts.get(source_action, 0)

            if source_action in migrated_actions:
                target_counts = migrated_actions[source_action]
                expected_count = target_counts.get(expected_target, 0)
                other_counts = {k: v for k, v in target_counts.items() if k != expected_target}

                mapping_results[source_action] = {
                    "source_count": source_count,
                    "expected_target": expected_target,
                    "expected_count": expected_count,
                    "other_mappings": other_counts,
                    "correctly_mapped": expected_count == source_count and not other_counts,
                }

                if mapping_results[source_action]["correctly_mapped"]:
                    self.stdout.write(f"  ✅ {source_action} → {expected_target}: {source_count:,} records")
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  {source_action} → {expected_target}: {expected_count:,}/{source_count:,} records",
                        ),
                    )
                    if other_counts:
                        for other_type, count in other_counts.items():
                            self.stdout.write(f"      Also mapped to {other_type}: {count:,}")
            else:
                mapping_results[source_action] = {
                    "source_count": source_count,
                    "expected_target": expected_target,
                    "expected_count": 0,
                    "correctly_mapped": source_count == 0,
                }

                if source_count > 0:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ❌ {source_action}: No migrated records found (source has {source_count:,})",
                        ),
                    )
                    self.record_rejection(
                        "unmapped_action_type",
                        source_action,
                        f"No records migrated for action type {source_action}",
                    )

        self.record_data_integrity("action_type_mappings", mapping_results)

    def _verify_detailed_data(self, sample_size: int):
        """Perform detailed verification on a sample of records."""
        from apps.common.models import StudentActivityLog
        from apps.people.models import StudentAuditLog

        # Get sample of source records
        source_samples = list(
            StudentAuditLog.objects.select_related("student__person", "changed_by").order_by("?")[:sample_size],
        )

        verified = 0
        mismatches = []

        for source in source_samples:
            # Find corresponding migrated record
            filters = {
                "activity_details__original_action": source.action,
                "performed_by": source.changed_by,
                "created_at": source.timestamp,
            }

            # Handle student number
            if source.student and hasattr(source.student, "student_id"):
                filters["student_number"] = str(source.student.student_id)
            else:
                filters["student_number__startswith"] = "DELETED_"

            migrated = StudentActivityLog.objects.filter(**filters).first()

            if migrated:
                # Verify data matches
                issues = []

                # Check timestamp
                if migrated.created_at != source.timestamp:
                    issues.append(f"Timestamp mismatch: {migrated.created_at} vs {source.timestamp}")

                # Check user
                if migrated.performed_by != source.changed_by:
                    issues.append(f"User mismatch: {migrated.performed_by} vs {source.changed_by}")

                # Check original data preserved
                if "original_changes" in migrated.activity_details:
                    if migrated.activity_details["original_changes"] != source.changes:
                        issues.append("Original changes data mismatch")

                if issues:
                    mismatches.append(
                        {
                            "source_id": source.id,
                            "migrated_id": migrated.id,
                            "issues": issues,
                        },
                    )
                else:
                    verified += 1
            else:
                self.record_rejection(
                    "missing_in_target",
                    f"source_{source.id}",
                    "Could not find migrated record for source",
                    raw_data={
                        "action": source.action,
                        "timestamp": str(source.timestamp),
                        "student_id": source.student_id if source.student_id else None,
                    },
                )

        self.record_data_integrity(
            "detailed_verification",
            {
                "sample_size": len(source_samples),
                "verified": verified,
                "mismatches": len(mismatches),
                "verification_rate": ((verified / len(source_samples) * 100) if source_samples else 0),
            },
        )

        self.stdout.write(f"  Verified {verified}/{len(source_samples)} records successfully")

        if mismatches:
            self.stdout.write(self.style.WARNING(f"  Found {len(mismatches)} mismatches"))
            self.record_sample_data("verification_mismatches", mismatches[:10])

    def _check_orphaned_records(self):
        """Check for records with deleted students."""
        from apps.common.models import StudentActivityLog

        orphaned_count = StudentActivityLog.objects.filter(student_number__startswith="DELETED_").count()

        self.record_data_integrity(
            "orphaned_records",
            {
                "count": orphaned_count,
                "description": "Records for deleted students",
            },
        )

        if orphaned_count > 0:
            self.stdout.write(f"  Found {orphaned_count:,} records for deleted students")

            # Get sample
            orphaned_samples = list(
                StudentActivityLog.objects.filter(student_number__startswith="DELETED_").values(
                    "student_number",
                    "student_name",
                    "activity_type",
                    "created_at",
                )[:5],
            )

            self.record_sample_data("orphaned_student_records", orphaned_samples)
        else:
            self.stdout.write(self.style.SUCCESS("  ✅ No orphaned student records found"))

    def _generate_verification_summary(self, source_count: int, migrated_count: int):
        """Generate final verification summary."""
        success_rate = (migrated_count / source_count * 100) if source_count > 0 else 0

        self.record_performance_metric("verification_success_rate", success_rate)
        self.record_success("records_verified", migrated_count)

        # Summary statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📋 VERIFICATION SUMMARY"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Source records: {source_count:,}")
        self.stdout.write(f"Migrated records: {migrated_count:,}")
        self.stdout.write(f"Success rate: {success_rate:.2f}%")

        if success_rate < 100:
            self.stdout.write(
                self.style.WARNING("\n⚠️  Migration may be incomplete. Please review the detailed report."),
            )
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ All records appear to have been migrated successfully!"))

        self.stdout.write("=" * 60)
