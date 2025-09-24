#!/usr/bin/env python3
"""Import all legacy tables from CSV files into PostgreSQL database.
This script creates the 5 legacy tables needed for term count calculations.
"""

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


def import_legacy_tables():
    """Import all legacy CSV files into database tables."""
    # Legacy files to import
    legacy_imports = [
        {
            "command": "apps.core.management.commands.one-shot.import_legacy_students",
            "file": "data/legacy/leg_students.csv",
            "description": "Legacy Students",
        },
        {
            "command": "apps.core.management.commands.one-shot.import_legacy_courses",
            "file": "data/legacy/leg_courses.csv",
            "description": "Legacy Courses",
        },
        {
            "command": "apps.core.management.commands.one-shot.import_legacy_academiccoursetakers",
            "file": "data/legacy/leg_academiccoursetakers.csv",
            "description": "Legacy Academic Course Takers",
        },
        {
            "command": "apps.core.management.commands.one-shot.import_legacy_fees",
            "file": "data/legacy/leg_fees.csv",
            "description": "Legacy Fees",
        },
        {
            "command": "apps.core.management.commands.one-shot.import_legacy_receipt_headers",
            "file": "data/legacy/leg_receipt_headers.csv",
            "description": "Legacy Receipt Headers",
        },
    ]

    for import_config in legacy_imports:
        # Check if file exists
        if not Path(import_config["file"]).exists():
            continue

        try:
            # Run each command directly
            if "students" in import_config["command"]:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "command",
                    "apps/core/management/commands/one-shot/import_legacy_students.py",
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                command_instance = module.Command()
            elif "courses" in import_config["command"] and "takers" not in import_config["command"]:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "command",
                    "apps/core/management/commands/one-shot/import_legacy_courses.py",
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                command_instance = module.Command()
            elif "academiccoursetakers" in import_config["command"]:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "command",
                    "apps/core/management/commands/one-shot/import_legacy_academiccoursetakers.py",
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                command_instance = module.Command()
            elif "fees" in import_config["command"]:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "command",
                    "apps/core/management/commands/one-shot/import_legacy_fees.py",
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                command_instance = module.Command()
            elif "receipt_headers" in import_config["command"]:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "command",
                    "apps/core/management/commands/one-shot/import_legacy_receipt_headers.py",
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                command_instance = module.Command()
            else:
                continue

            # Run the command
            command_instance.handle(
                file=import_config["file"],
                drop_table=True,
                dry_run=False,
            )

        except Exception:
            continue

    # Check what tables were created
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'legacy_%'
            ORDER BY table_name
        """
        )

        legacy_tables = cursor.fetchall()
        if legacy_tables:
            for table in legacy_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                cursor.fetchone()[0]
        else:
            pass


if __name__ == "__main__":
    import_legacy_tables()
