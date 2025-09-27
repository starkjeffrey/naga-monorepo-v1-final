#!/usr/bin/env python3
"""
Kludge script to update Person.email field with school_email from legacy_students table.

This script matches Person records with legacy_students using legacy_id and updates
the Person.email field to use school_email (*@pucsr.edu.kh) instead of personal email.

Usage:
    # Dry run to see what would be updated
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/one-off/update_person_emails_from_legacy.py --dry-run

    # Execute the updates
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/one-off/update_person_emails_from_legacy.py

    # Limit for testing
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/one-off/update_person_emails_from_legacy.py --limit 100
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

from apps.people.models import StudentProfile


def get_legacy_school_emails():
    """Get school_email data from legacy_students table."""
    query = """
    SELECT "ID" as legacy_id, "SchoolEmail" as school_email, "Name" as name, "Email" as personal_email
    FROM legacy_students
    WHERE "SchoolEmail" IS NOT NULL
      AND "SchoolEmail" != ''
      AND "SchoolEmail" LIKE '%@pucsr.edu.kh'
    ORDER BY "ID"
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def find_matching_persons(legacy_data, limit=None):
    """Find Person records that match legacy_students by legacy_id via StudentProfile."""
    matches = []
    processed = 0

    for legacy_record in legacy_data:
        if limit and processed >= limit:
            break

        legacy_id = legacy_record["legacy_id"]

        # Find StudentProfile with matching student_id (which corresponds to legacy_id)
        try:
            student_profile = StudentProfile.objects.select_related("person").get(student_id=int(legacy_id))
            person = student_profile.person

            # Check if we should update this record
            current_email = person.personal_email or ""
            school_email = legacy_record["school_email"]

            # Update if we have a school email and the person doesn't already have a @pucsr.edu.kh email
            if school_email and not current_email.endswith("@pucsr.edu.kh"):
                matches.append(
                    {
                        "person": person,
                        "student_profile": student_profile,
                        "legacy_record": legacy_record,
                        "current_email": current_email,
                        "school_email": school_email,
                    }
                )

        except StudentProfile.DoesNotExist:
            # No matching student profile found
            pass
        except ValueError:
            # Invalid student_id format
            pass

        processed += 1

    return matches


def update_person_emails(matches, dry_run=True):
    """Update Person records with school_email from legacy data."""

    updated_count = 0
    errors = []

    print(f"📧 {'DRY RUN: Would update' if dry_run else 'Updating'} {len(matches)} Person records...")

    if not dry_run:
        with transaction.atomic():
            for match in matches:
                try:
                    person = match["person"]
                    school_email = match["school_email"]

                    # Update the person's email to use school email
                    person.personal_email = school_email
                    person.save(update_fields=["personal_email"])

                    updated_count += 1

                    if updated_count % 100 == 0:
                        print(f"   ✅ Updated {updated_count} records...")

                except Exception as e:
                    error_msg = f"Failed to update Person {person.id}: {e}"
                    errors.append(error_msg)
                    print(f"   ❌ {error_msg}")
    else:
        # Dry run - just show what would be updated
        for i, match in enumerate(matches[:10], 1):  # Show first 10 examples
            person = match["person"]
            current = match["current_email"]
            school = match["school_email"]

            print(f"   {i}. Student {match['student_profile'].student_id} ({person.full_name})")
            print(f"      Current: '{current}' → School: '{school}'")

        if len(matches) > 10:
            print(f"   ... and {len(matches) - 10} more records")

    return updated_count, errors


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Update Person emails with school_email from legacy_students")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")

    args = parser.parse_args()

    print("📬 Person Email Update Script")
    print("=" * 60)

    try:
        # Get legacy school email data
        print("🔍 Fetching school emails from legacy_students table...")
        legacy_data = get_legacy_school_emails()
        print(f"   Found {len(legacy_data)} legacy records with school emails")

        # Find matching Person records
        print("🔎 Finding matching Person records...")
        matches = find_matching_persons(legacy_data, limit=args.limit)
        print(f"   Found {len(matches)} Person records to update")

        if not matches:
            print("✅ No records need updating!")
            return

        # Show some statistics
        school_emails = [m["school_email"] for m in matches]
        unique_domains = {email.split("@")[1] for email in school_emails if "@" in email}
        print(f"   Email domains: {', '.join(sorted(unique_domains))}")

        # Update records
        updated_count, errors = update_person_emails(matches, dry_run=args.dry_run)

        # Print results
        print("\n📊 RESULTS")
        print("=" * 60)

        if args.dry_run:
            print(f"🔍 DRY RUN - Would update {len(matches)} Person records")
            print("   Run without --dry-run to execute the updates")
        else:
            print(f"✅ Successfully updated {updated_count} Person records")

            if errors:
                print(f"❌ {len(errors)} errors occurred:")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"   {error}")
                if len(errors) > 5:
                    print(f"   ... and {len(errors) - 5} more errors")

        print("=" * 60)

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
