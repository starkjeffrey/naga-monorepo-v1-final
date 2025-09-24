import os
import sys

import django
from django.apps import apps
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()


def verify_complete_sync():
    """Verify models and database are perfectly synchronized.

    This script checks for:
    1. Missing tables (models without database tables)
    2. Nullable constraint mismatches between models and database
    3. Missing columns in database tables

    Excludes:
    - Legacy import tables (legacy_*)
    - Backup tables (*_backup)
    - Many-to-many relationship tables (handled automatically by Django)
    - Django system tables (normal and expected)
    """

    issues = []
    warnings = []

    try:
        with connection.cursor() as cursor:
            # Get all database tables (no filtering - we'll categorize them)
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            all_db_tables = {row[0] for row in cursor.fetchall()}

            # Get all model tables from Django
            all_model_tables = {model._meta.db_table for model in apps.get_models()}

            # Define tables to ignore in sync verification
            ignored_table_patterns = [
                "legacy_",  # Legacy import tables
                "_backup",  # Backup tables
                "django_migrations",  # Django's migration tracking table
            ]

            # Filter database tables to only those we care about for sync verification
            relevant_db_tables = set()
            ignored_db_tables = set()

            for table in all_db_tables:
                should_ignore = any(
                    table.startswith(pattern) or table.endswith(pattern.lstrip("_"))
                    for pattern in ignored_table_patterns
                )

                if should_ignore:
                    ignored_db_tables.add(table)
                else:
                    relevant_db_tables.add(table)

            # Check for table mismatches
            extra_in_db = relevant_db_tables - all_model_tables
            missing_in_db = all_model_tables - all_db_tables

            # Categorize extra tables in DB
            if extra_in_db:
                # Separate many-to-many tables from other extra tables
                m2m_tables = set()
                unknown_tables = set()

                for table in extra_in_db:
                    # Many-to-many tables typically have exactly 3 columns: id, model1_id, model2_id
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM information_schema.columns
                        WHERE table_name = %s
                    """,
                        [table],
                    )
                    column_count = cursor.fetchone()[0]

                    # Check if it follows M2M naming pattern and has 3 columns
                    if column_count == 3 and table.count("_") >= 2:
                        m2m_tables.add(table)
                    else:
                        unknown_tables.add(table)

                if m2m_tables:
                    warnings.append(f"Many-to-many relationship tables in DB (normal): {len(m2m_tables)} tables")

                if unknown_tables:
                    issues.append(f"Unknown extra tables in DB: {unknown_tables}")

            if missing_in_db:
                issues.append(f"Model tables missing from DB: {missing_in_db}")

            # Check columns for each model
            for model in apps.get_models():
                table = model._meta.db_table

                # Skip if table doesn't exist in DB (already reported above)
                if table not in all_db_tables:
                    continue

                # Get database column information (use parameterized query for security)
                cursor.execute(
                    """
                    SELECT column_name, is_nullable, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """,
                    [table],
                )
                db_columns = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

                # Check each model field
                for field in model._meta.fields:
                    if field.column not in db_columns:
                        issues.append(f"Missing column: {table}.{field.column}")
                    else:
                        db_nullable = db_columns[field.column][0] == "YES"
                        model_nullable = field.null

                        if db_nullable != model_nullable:
                            issues.append(
                                f"Nullable mismatch: {table}.{field.column} "
                                f"(DB: {'NULL' if db_nullable else 'NOT NULL'}, "
                                f"Model: {'null=True' if model_nullable else 'null=False'})"
                            )

    except Exception as e:
        print(f"❌ Sync verification ERROR: {e}")
        return False

    # Report results
    print("🔍 Database-Model Sync Verification")
    print(f"📊 Checked {len(all_model_tables)} Django models against database")
    print(f"🗃️  Found {len(all_db_tables)} total tables in database")
    print(f"🚫 Ignored {len(ignored_db_tables)} legacy/backup tables")

    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")

    if issues:
        print("\n❌ SYNC VERIFICATION FAILED:")
        for issue in issues:
            print(f"  - {issue}")
        print(f"\n💡 Found {len(issues)} integrity issues that need attention")
        return False
    else:
        print("\n✅ PERFECT SYNC ACHIEVED!")
        print("🎉 All Django models are perfectly synchronized with the database")
        return True


if __name__ == "__main__":
    success = verify_complete_sync()
    sys.exit(0 if success else 1)
