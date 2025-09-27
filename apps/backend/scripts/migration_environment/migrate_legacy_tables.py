"""Django management command to migrate legacy tables to the migration database.

Moves legacy_* tables from default database to migration database.
"""

import subprocess
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connections

# Constants
DOCKER_COMPOSE_FILE = "docker-compose.local.yml"


class Command(BaseCommand):
    """Migrate legacy tables to migration database."""

    help = "Migrate legacy tables from default to migration database"

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without making changes",
        )

    def handle(self, *args, **options):
        """Migrate legacy tables to migration database."""
        dry_run = options["dry_run"]

        if dry_run:
            dry_run_msg = "🔍 DRY RUN MODE - No changes will be made"
            self.stdout.write(self.style.WARNING(dry_run_msg))

        # Get database connections
        default_db = connections["default"]
        migration_db = connections["migration"]

        # Find legacy tables in default database
        with default_db.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema='public' AND table_name LIKE 'legacy_%'
            """
            )
            legacy_tables = [row[0] for row in cursor.fetchall()]

        if not legacy_tables:
            self.stdout.write("📭 No legacy tables found in default database")
            return

        self.stdout.write(f"📋 Found {len(legacy_tables)} legacy tables to migrate:")
        for table in legacy_tables:
            self.stdout.write(f"  - {table}")

        if dry_run:
            self.stdout.write("\\n✅ Dry run completed - ready for migration!")
            return

        # Migrate each table
        migrated_count = 0
        for table_name in legacy_tables:
            try:
                self.stdout.write(f"🔄 Migrating {table_name}...")

                # Get table structure
                with default_db.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}'
                        ORDER BY ordinal_position
                    """
                    )
                    columns = cursor.fetchall()

                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]

                self.stdout.write(f"  📊 {row_count:,} records, {len(columns)} columns")

                if row_count > 0:
                    # Use PostgreSQL pg_dump and pg_restore for efficient migration
                    # This is simpler and more reliable than manual copying

                    # Create temporary dump file
                    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".sql", delete=False) as dump_file:
                        dump_filename = dump_file.name

                    try:
                        # Dump table from default database
                        dump_cmd = [
                            "docker",
                            "compose",
                            "-f",
                            DOCKER_COMPOSE_FILE,
                            "exec",
                            "-T",
                            "postgres",
                            "pg_dump",
                            "-U",
                            "debug",
                            "-d",
                            "naga_backend_v1",
                            "--table",
                            table_name,
                            "--data-only",
                            "--no-owner",
                        ]

                        with Path(dump_filename).open("w") as f:
                            subprocess.run(dump_cmd, stdout=f, check=True)

                        # Create table structure in migration database
                        structure_cmd = [
                            "docker",
                            "compose",
                            "-f",
                            DOCKER_COMPOSE_FILE,
                            "exec",
                            "-T",
                            "postgres",
                            "pg_dump",
                            "-U",
                            "debug",
                            "-d",
                            "naga_backend_v1",
                            "--table",
                            table_name,
                            "--schema-only",
                            "--no-owner",
                        ]

                        create_result = subprocess.run(structure_cmd, check=False, capture_output=True, text=True)

                        # Apply structure to migration database
                        with migration_db.cursor() as cursor:
                            # Drop table if exists to recreate
                            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                            cursor.execute(create_result.stdout)

                        # Load data into migration database
                        load_cmd = [
                            "docker",
                            "compose",
                            "-f",
                            DOCKER_COMPOSE_FILE,
                            "exec",
                            "-i",
                            "postgres",
                            "psql",
                            "-U",
                            "debug",
                            "-d",
                            "naga_migration_v1",
                        ]

                        dump_path = Path(dump_filename)
                        with dump_path.open() as f:
                            subprocess.run(load_cmd, stdin=f, check=True)

                    finally:
                        # Clean up temp file
                        dump_path = Path(dump_filename)
                        if dump_path.exists():
                            dump_path.unlink()

                    # Verify migration
                    with migration_db.cursor() as cursor:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        migrated_rows = cursor.fetchone()[0]

                    if migrated_rows == row_count:
                        msg = f"  ✅ Successfully migrated {migrated_rows:,} records"
                        self.stdout.write(msg)
                        migrated_count += 1
                    else:
                        error_msg = f"  ❌ Migration mismatch: {row_count} -> {migrated_rows}"
                        self.stdout.write(self.style.ERROR(error_msg))
                else:
                    # Just create empty table structure
                    with migration_db.cursor() as cursor:
                        sql = f"CREATE TABLE IF NOT EXISTS {table_name} "
                        sql += f"(LIKE {table_name} INCLUDING ALL)"
                        cursor.execute(sql)
                    self.stdout.write("  ✅ Created empty table structure")
                    migrated_count += 1

            except Exception as e:
                error_msg = f"  ❌ Error migrating {table_name}: {e}"
                self.stdout.write(self.style.ERROR(error_msg))

        self.stdout.write("\\n📊 Migration Results:")
        self.stdout.write(f"  Tables processed: {len(legacy_tables)}")
        self.stdout.write(f"  Successfully migrated: {migrated_count}")

        if migrated_count == len(legacy_tables):
            success_msg = "\\n✅ All legacy tables migrated successfully!"
            self.stdout.write(self.style.SUCCESS(success_msg))
            self.stdout.write("\\n🔄 Next steps:")
            self.stdout.write("  1. Verify data in migration database")
            migration_msg = "  2. Update ProgramEnrollment status logic to use migration DB"
            self.stdout.write(migration_msg)
            self.stdout.write("  3. Consider dropping legacy tables from default DB")
        else:
            self.stdout.write(self.style.ERROR("\\n❌ Some tables failed to migrate"))

    def _find_legacy_tables(self, default_db):
        """Find legacy tables in default database."""
        with default_db.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema='public' AND table_name LIKE 'legacy_%'
            """
            )
            return [row[0] for row in cursor.fetchall()]

    def _display_tables_to_migrate(self, legacy_tables):
        """Display list of tables to migrate."""
        self.stdout.write(f"📋 Found {len(legacy_tables)} legacy tables to migrate:")
        for table in legacy_tables:
            self.stdout.write(f"  - {table}")
        self.stdout.write("")

    def _display_migration_results(self, migrated_count, total_tables):
        """Display final migration results."""
        self.stdout.write("\\n📊 Migration Results:")
        self.stdout.write(f"  Tables processed: {total_tables}")
        self.stdout.write(f"  Successfully migrated: {migrated_count}")

        if migrated_count == total_tables:
            success_msg = "\\n✅ All legacy tables migrated successfully!"
            self.stdout.write(self.style.SUCCESS(success_msg))
            self.stdout.write("\\n🔄 Next steps:")
            self.stdout.write("  1. Verify data in migration database")
            migration_msg = "  2. Update ProgramEnrollment status logic to use migration DB"
            self.stdout.write(migration_msg)
            self.stdout.write("  3. Consider dropping legacy tables from default DB")
        else:
            self.stdout.write(self.style.ERROR("\\n❌ Some tables failed to migrate"))
