#!/usr/bin/env python3
"""
Update unparsed legacy course taker records with automated ClassID parsing.

Finds records with empty NormalizedCourse and updates them with parser results.
"""

import os
import sys
from pathlib import Path

import django

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection, transaction

from scripts.legacy_imports.classid_parser import parse_full_classid


def update_unparsed_records():
    """Find and update unparsed records with automated parsing."""

    print("🔍 Finding unparsed records...")

    # Find unparsed records
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                "IPK",
                "ClassID"
            FROM legacy_course_takers
            WHERE ("NormalizedCourse" = '' OR "NormalizedCourse" IS NULL)
                AND "ClassID" IS NOT NULL
                AND "ClassID" != ''
                AND "parsed_termid" >= '21'
            ORDER BY CAST("IPK" AS INTEGER)
        """)

        unparsed_records = cursor.fetchall()

    print(f"📄 Found {len(unparsed_records)} unparsed records")

    if not unparsed_records:
        print("✅ No unparsed records found!")
        return

    # Process each record
    updated_count = 0
    failed_count = 0

    with transaction.atomic():
        for ipk, classid in unparsed_records:
            try:
                # Parse the ClassID
                course, part, section = parse_full_classid(classid)

                # Update the record
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE legacy_course_takers
                        SET
                            "NormalizedCourse" = %s,
                            "NormalizedPart" = %s,
                            "NormalizedSection" = %s
                        WHERE "IPK" = %s
                    """,
                        [course or "", part or "", section or "", ipk],
                    )

                updated_count += 1
                print(f"✅ IPK {ipk}: {classid}")
                print(f"   → Course: {course}, Part: {part}, Section: {section}")

            except Exception as e:
                failed_count += 1
                print(f"❌ IPK {ipk}: {classid} - Error: {e}")

    print("\n📊 RESULTS")
    print("=" * 40)
    print(f"✅ Successfully updated: {updated_count}")
    print(f"❌ Failed to update: {failed_count}")
    print(f"📄 Total processed: {len(unparsed_records)}")

    if updated_count > 0:
        print(f"\n🎉 Updated {updated_count} records with automated ClassID parsing!")


if __name__ == "__main__":
    update_unparsed_records()
