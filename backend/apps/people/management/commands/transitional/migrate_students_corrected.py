"""Wrapper for the corrected student migration script.

Technical debt: This is an anti-pattern - remove subprocess.run and import the actual migration command directly.
Instead of subprocess.run, import and call the migration command function directly within Django context.
"""

import subprocess

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the corrected student migration script"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        # Build command arguments
        cmd_args = [
            "python",
            "scripts/migration_environment/production-ready/migrate_legacy_students_250708.py",
        ]

        if options.get("dry_run"):
            cmd_args.append("--dry-run")
        if options.get("limit"):
            cmd_args.extend(["--limit", str(options["limit"])])
        if options.get("batch_size"):
            cmd_args.extend(["--batch-size", str(options["batch_size"])])

        # Run the script
        result = subprocess.run(cmd_args, check=False, capture_output=True, text=True)

        # Print output
        if result.stdout:
            self.stdout.write(result.stdout)
        if result.stderr:
            self.stderr.write(result.stderr)

        if result.returncode != 0:
            self.stderr.write(f"Script failed with return code {result.returncode}")
