#!/usr/bin/env python3
"""Copy essential legacy data from MIGRATION to TEST environment.
This allows us to test import scripts in the TEST environment safely.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django with local settings for TEST environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()

from django.db import connections


def copy_legacy_tables():
    """Copy legacy tables from MIGRATION to TEST environment."""
    # Get connections
    test_db = connections["default"]  # Local/TEST database

    # Tables to copy
    legacy_tables = [
        "legacy_terms",
        "legacy_students",
        "legacy_academiccoursetakers",
    ]

    with test_db.cursor() as cursor:
        for table in legacy_tables:
            # Drop table if exists
            cursor.execute(f"DROP TABLE IF EXISTS {table}")

            # Get table structure from MIGRATION database


if __name__ == "__main__":
    copy_legacy_tables()
