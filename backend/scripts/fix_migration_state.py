#!/usr/bin/env python
"""
Fix Django migration state after migration reset.

This script resolves the issue where Django thinks it needs to apply initial
migrations but the database tables already exist.
"""

import os
import sys

import django
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()


def fix_migration_state():
    """Fix migration state by faking initial migrations for existing tables."""

    print("🔧 Fixing Django migration state...")

    # Apps that have existing tables but need initial migrations marked as applied
    apps_with_existing_tables = [
        "academic",
        "academic_records",
        "accounts",
        "attendance",
        "common",
        "curriculum",
        "enrollment",
        "finance",
        "grading",
        "language",
        "people",
        "scheduling",
        "scholarships",
        "web_interface",
    ]

    # First, fake the initial migrations for apps with existing tables
    print("\n📋 Step 1: Fake-applying initial migrations for existing tables...")
    for app in apps_with_existing_tables:
        try:
            print(f"   🔄 Faking {app}.0001_initial...")
            execute_from_command_line(["manage.py", "migrate", app, "0001", "--fake"])
        except Exception as e:
            print(f"   ⚠️  {app}: {e}")
            # Continue with other apps even if one fails
            continue

    # Second, fake the 0002_initial migrations where they exist
    print("\n📋 Step 2: Fake-applying 0002_initial migrations...")
    apps_with_0002 = [
        "academic",
        "academic_records",
        "attendance",
        "curriculum",
        "enrollment",
        "finance",
        "grading",
        "language",
        "people",
        "scheduling",
    ]
    for app in apps_with_0002:
        try:
            print(f"   🔄 Faking {app}.0002_initial...")
            execute_from_command_line(["manage.py", "migrate", app, "0002", "--fake"])
        except Exception as e:
            print(f"   ⚠️  {app}: {e}")
            # Continue with other apps
            continue

    # Third, apply any remaining migrations normally
    print("\n📋 Step 3: Applying remaining migrations...")
    try:
        execute_from_command_line(["manage.py", "migrate"])
        print("   ✅ All remaining migrations applied successfully!")
    except Exception as e:
        print(f"   ❌ Error applying remaining migrations: {e}")
        return False

    print("\n✅ Migration state fixed successfully!")
    return True


if __name__ == "__main__":
    success = fix_migration_state()
    sys.exit(0 if success else 1)
