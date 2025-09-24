"""Django management command for idempotent student migration.

This command provides a Django management interface to the idempotent
student migration script that supports:
- CREATE or UPDATE operations (upsert)
- IPK-based change detection for efficiency
- Incremental processing by student ID range or modification date
- No duplicate creation - safe to run multiple times

Usage Examples:
    # Full sync (first time or complete refresh)
    python manage.py migrate_students_idempotent --mode upsert

    # Daily incremental sync (only changed records)
    python manage.py migrate_students_idempotent --mode upsert --modified-since yesterday

    # Process specific student ID range (useful for batching)
    python manage.py migrate_students_idempotent --mode upsert --student-id-range 18000:19000

    # Force update all records (ignore IPK comparison)
    python manage.py migrate_students_idempotent --mode upsert --force-update

    # Test with dry run
    python manage.py migrate_students_idempotent --dry-run --limit 100
"""

import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the idempotent student migration script with IPK-based change detection"

    def add_arguments(self, parser):
        """Add all arguments from the idempotent migration script."""
        parser.add_argument(
            "--dry-run", action="store_true", help="Show what would be migrated without making changes"
        )
        parser.add_argument("--batch-size", type=int, default=100, help="Number of records to process in each batch")
        parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")

        # Idempotent-specific options
        parser.add_argument(
            "--mode",
            choices=["create-only", "update-only", "upsert"],
            default="upsert",
            help="Processing mode: create-only (original), update-only, or upsert (default)",
        )
        parser.add_argument(
            "--student-id-range",
            type=str,
            help="Process specific student ID range, format: START:END (e.g., 18000:19000)",
        )
        parser.add_argument(
            "--modified-since",
            type=str,
            help="Only process records modified since date (YYYY-MM-DD) or 'yesterday'",
        )
        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Force update all records even if IPK unchanged",
        )

    def handle(self, *args, **options):
        """Execute the idempotent migration script with provided options."""

        # Get the script path
        script_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "scripts"
            / "migration_environment"
            / "production-ready"
            / "migrate_legacy_students_idempotent.py"
        )

        # Build command arguments
        cmd_args = ["python", str(script_path)]

        # Map all options to script arguments
        option_mapping = {
            "dry_run": "--dry-run",
            "batch_size": "--batch-size",
            "limit": "--limit",
            "mode": "--mode",
            "student_id_range": "--student-id-range",
            "modified_since": "--modified-since",
            "force_update": "--force-update",
        }

        for option_name, script_arg in option_mapping.items():
            value = options.get(option_name)
            if value is not None:
                if isinstance(value, bool):
                    if value:  # Only add flag if True
                        cmd_args.append(script_arg)
                else:
                    cmd_args.extend([script_arg, str(value)])

        # Print command for transparency
        self.stdout.write(f"🚀 Executing: {' '.join(cmd_args)}")

        # Execute the script
        try:
            result = subprocess.run(cmd_args, check=True, text=True, capture_output=True)

            # Print output
            if result.stdout:
                self.stdout.write(result.stdout)
            if result.stderr:
                self.stderr.write(result.stderr)

            self.stdout.write(self.style.SUCCESS("✅ Migration completed successfully"))

        except subprocess.CalledProcessError as e:
            # Print any captured output
            if e.stdout:
                self.stdout.write(e.stdout)
            if e.stderr:
                self.stderr.write(e.stderr)

            self.stderr.write(self.style.ERROR(f"❌ Migration failed with return code {e.returncode}"))
            sys.exit(e.returncode)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to execute migration script: {e}"))
            sys.exit(1)
