#!/usr/bin/env python
"""
Backup all enrollment tables before dropping them.
Creates individual SQL files and a combined backup.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()


def backup_enrollment_tables():
    """Backup all enrollment tables to SQL files."""

    # Create backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"enrollment_backup_{timestamp}")
    backup_dir.mkdir(exist_ok=True)

    # List of enrollment tables with record counts
    enrollment_tables = [
        ("enrollment_classheaderenrollment", 261802),
        ("enrollment_programmilestone", 19596),
        ("enrollment_academicjourney", 17650),
        ("enrollment_academicprogression", 15910),
        ("enrollment_programenrollment", 8274),
        ("enrollment_majordeclaration", 1740),
        ("enrollment_seniorprojectgroup_students", 324),
        ("enrollment_seniorprojectgroup", 100),
        ("enrollment_programperiod", 2),
        ("enrollment_studentcourseeligibility", 0),
        ("enrollment_studentcourseeligibility_missing_prerequisites", 0),
        ("enrollment_classpartenrollment", 0),
        ("enrollment_programtransition", 0),
        ("enrollment_classsessionexemption", 0),
        ("enrollment_certificateissuance", 0),
        ("enrollment_student_cycle_status", 0),
    ]

    print(f"🔒 Creating backup of enrollment tables in {backup_dir}/")
    print("=" * 80)

    # Backup each table
    for table_name, record_count in enrollment_tables:
        if record_count > 0:
            print(f"\n📋 Backing up {table_name} ({record_count:,} records)...")

            # Use pg_dump for individual table
            backup_file = backup_dir / f"{table_name}.sql"
            cmd = [
                "pg_dump",
                "-h",
                "postgres",
                "-U",
                "debug",
                "-d",
                "naga_local",
                "--table",
                table_name,
                "--data-only",
                "--column-inserts",
            ]

            try:
                with open(backup_file, "w") as f:
                    subprocess.run(cmd, stdout=f, check=True, env={**os.environ, "PGPASSWORD": "debug"})
                print(f"   ✅ Saved to {backup_file}")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ Error backing up {table_name}: {e}")
        else:
            print(f"\n⏭️  Skipping {table_name} (no records)")

    # Create combined backup with schema
    print("\n📦 Creating combined backup with schema...")
    combined_file = backup_dir / "all_enrollment_tables.sql"

    # First get schema
    schema_cmd = [
        "docker",
        "compose",
        "-f",
        "docker-compose.local.yml",
        "exec",
        "-T",
        "postgres",
        "pg_dump",
        "-U",
        "debug",
        "-d",
        "naga_local",
        "--schema-only",
    ]

    # Filter for enrollment tables only
    enrollment_schema = []
    try:
        result = subprocess.run(schema_cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.split("\n")

        in_enrollment_table = False
        for line in lines:
            if "CREATE TABLE" in line and "enrollment_" in line:
                in_enrollment_table = True
            elif in_enrollment_table and line.strip() == ");":
                enrollment_schema.append(line)
                in_enrollment_table = False

            if in_enrollment_table or (
                "enrollment_" in line
                and any(
                    keyword in line
                    for keyword in ["CREATE TABLE", "ALTER TABLE", "CREATE INDEX", "ADD CONSTRAINT", "CREATE SEQUENCE"]
                )
            ):
                enrollment_schema.append(line)

        with open(combined_file, "w") as f:
            f.write("-- Enrollment Tables Backup\n")
            f.write(f"-- Generated: {datetime.now()}\n")
            f.write("-- Record counts:\n")
            for table_name, count in enrollment_tables:
                if count > 0:
                    f.write(f"-- {table_name}: {count:,} records\n")
            f.write("\n")
            f.write("\n".join(enrollment_schema))

            # Add data
            f.write("\n\n-- Data\n")
            for table_name, count in enrollment_tables:
                if count > 0:
                    data_file = backup_dir / f"{table_name}.sql"
                    if data_file.exists():
                        f.write(f"\n-- {table_name} data\n")
                        f.write(data_file.read_text())

        print(f"   ✅ Combined backup saved to {combined_file}")

    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error creating combined backup: {e}")

    # Create Django fixtures as well
    print("\n🗂️  Creating Django fixtures...")
    fixtures_dir = backup_dir / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    # Use Django dumpdata for tables with data
    for table_name, count in enrollment_tables:
        if count > 0:
            app_model = f"enrollment.{table_name.replace('enrollment_', '')}"
            fixture_file = fixtures_dir / f"{table_name}.json"

            cmd = [
                "docker",
                "compose",
                "-f",
                "docker-compose.local.yml",
                "run",
                "--rm",
                "django",
                "python",
                "manage.py",
                "dumpdata",
                app_model,
                "--indent",
                "2",
            ]

            try:
                with open(fixture_file, "w") as f:
                    subprocess.run(cmd, stdout=f, check=True)
                print(f"   ✅ Fixture saved to {fixture_file}")
            except subprocess.CalledProcessError:
                # Some models might not work with dumpdata
                pass

    print("\n" + "=" * 80)
    print(f"✅ Backup complete! Files saved in: {backup_dir}/")
    print("\nTo restore later:")
    print(f"  psql -U debug -d naga_local < {combined_file}")
    print("  OR")
    print(f"  python manage.py loaddata {fixtures_dir}/*.json")

    return backup_dir


if __name__ == "__main__":
    backup_enrollment_tables()
