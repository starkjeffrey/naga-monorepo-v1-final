#!/usr/bin/env python3
"""Import new legacy data from the 20250612 CSV files.
Uses the existing import command DDLs to reimport the fresh data.
"""

import importlib.util
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()

from django.db import connection


def import_new_legacy_data():
    """Import all new legacy CSV files from 20250612."""
    # Map of new files to their corresponding import commands
    import_configs = [
        {
            "file": "data/legacy/all_students_20250612.csv",
            "command_path": "apps/core/management/commands/one-shot/import_legacy_students.py",
            "description": "Legacy Students",
        },
        {
            "file": "data/legacy/all_academiccoursetakers_20250612.csv",
            "command_path": "apps/core/management/commands/one-shot/import_legacy_academiccoursetakers.py",
            "description": "Legacy Academic Course Takers",
        },
        {
            "file": "data/legacy/all_receipt_headers_20250612.csv",
            "command_path": "apps/core/management/commands/one-shot/import_legacy_receipt_headers.py",
            "description": "Legacy Receipt Headers",
        },
        {
            "file": "data/legacy/all_receipt_items_20250612.csv",
            "command_path": "apps/core/management/commands/one-shot/import_legacy_receipt_items.py",
            "description": "Legacy Receipt Items",
        },
    ]

    # Note: We'll need to handle courses and terms separately as they may not have direct import commands

    for config in import_configs:
        # Check if file exists
        if not Path(config["file"]).exists():
            continue

        try:
            # Import the specific command file
            spec = importlib.util.spec_from_file_location(
                "command",
                config["command_path"],
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Create and run the command
            command_instance = module.Command()
            command_instance.handle(
                file=config["file"],
                drop_table=True,  # Use drop table to ensure clean import
                dry_run=False,
            )

        except Exception:
            continue

    # Handle courses separately - check if we have course data in leg_courses.csv
    courses_file = "data/legacy/leg_courses.csv"

    if Path(courses_file).exists():
        try:
            spec = importlib.util.spec_from_file_location(
                "command",
                "apps/core/management/commands/one-shot/import_legacy_courses.py",
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            command_instance = module.Command()
            command_instance.handle(file=courses_file, drop_table=True, dry_run=False)

        except Exception:
            pass

    # Handle terms data - create a simple import for the terms CSV
    terms_file = "data/legacy/all_terms_20250612.csv"

    if Path(terms_file).exists():
        try:
            import csv

            # Create terms table if it doesn't exist
            with connection.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS legacy_terms")

                create_terms_sql = """
                CREATE TABLE legacy_terms (
                    term_id VARCHAR(50) PRIMARY KEY,
                    term_name VARCHAR(200),
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    academic_year VARCHAR(20),
                    term_type VARCHAR(50),
                    is_active INTEGER,
                    created_date TIMESTAMP,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX idx_legacy_terms_year ON legacy_terms(academic_year);
                CREATE INDEX idx_legacy_terms_type ON legacy_terms(term_type);
                """

                cursor.execute(create_terms_sql)

            # Import terms data
            with Path(terms_file).open(encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                imported_count = 0

                with connection.cursor() as cursor:
                    for row in reader:
                        # Clean up the row data
                        term_data = {}
                        for key, value in row.items():
                            if value in ("NULL", "", None, "null"):
                                term_data[key] = None
                            else:
                                term_data[key] = value.strip() if isinstance(value, str) else value

                        # Insert the term record - adjust field names based on actual CSV structure
                        insert_sql = """
                        INSERT INTO legacy_terms (
                            term_id, term_name, start_date, end_date,
                            academic_year, term_type, is_active, created_date
                        ) VALUES (
                            %(term_id)s, %(term_name)s, %(start_date)s, %(end_date)s,
                            %(academic_year)s, %(term_type)s, %(is_active)s, %(created_date)s
                        )
                        """

                        # Map CSV columns to database columns (adjust as needed based on actual CSV structure)
                        mapped_data = {
                            "term_id": term_data.get("id") or term_data.get("term_id"),
                            "term_name": term_data.get("name") or term_data.get("term_name"),
                            "start_date": term_data.get("start_date"),
                            "end_date": term_data.get("end_date"),
                            "academic_year": term_data.get("academic_year"),
                            "term_type": term_data.get("term_type"),
                            "is_active": term_data.get("is_active"),
                            "created_date": term_data.get("created_date"),
                        }

                        cursor.execute(insert_sql, mapped_data)
                        imported_count += 1

        except Exception:
            pass

    # Check what tables were created
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name,
                   (SELECT COUNT(*) FROM information_schema.tables t2
                    WHERE t2.table_name = t1.table_name) as record_count
            FROM information_schema.tables t1
            WHERE table_schema = 'public'
            AND table_name LIKE 'legacy_%'
            ORDER BY table_name
        """
        )

        legacy_tables = cursor.fetchall()
        if legacy_tables:
            for table_name, _ in legacy_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                cursor.fetchone()[0]
        else:
            pass


if __name__ == "__main__":
    import_new_legacy_data()
