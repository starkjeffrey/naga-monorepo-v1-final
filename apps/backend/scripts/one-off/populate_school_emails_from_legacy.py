#!/usr/bin/env python3
"""
Populate Person.school_email field with school_email from legacy_students table.

This script matches Person records with legacy_students using StudentProfile.student_id
and updates the Person.school_email field which is currently mostly blank.

Usage:
    # Dry run to see what would be updated
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/one-off/populate_school_emails_from_legacy.py --dry-run

    # Execute the updates
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/one-off/populate_school_emails_from_legacy.py

    # Limit for testing
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/one-off/populate_school_emails_from_legacy.py --limit 100
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

from django.db import connection

from apps.people.models import Person, StudentProfile


def get_legacy_school_emails():
    """Get school_email data from legacy_students table."""
    query = """
    SELECT id as legacy_id, schoolemail as school_email, name as name
    FROM legacy_students
    WHERE schoolemail IS NOT NULL
      AND schoolemail != ''
      AND schoolemail LIKE '%@pucsr.edu.kh'
    ORDER BY id
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def find_matching_persons(legacy_data, limit=None):
    """Find Person records that need school_email populated."""
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
            current_school_email = person.school_email or ""
            legacy_school_email = legacy_record["school_email"]

            # Only update if we have a legacy school email and current school_email is blank
            # Also check that the legacy school email doesn't already exist in the Person table
            if legacy_school_email and not current_school_email:
                # Check if this school email already exists for another person
                existing_person = Person.objects.filter(school_email=legacy_school_email).first()
                if existing_person:
                    # Skip this record to avoid duplicate constraint violation
                    continue
                matches.append(
                    {
                        "person": person,
                        "student_profile": student_profile,
                        "legacy_record": legacy_record,
                        "current_school_email": current_school_email,
                        "legacy_school_email": legacy_school_email,
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


def update_school_emails(matches, dry_run=True):
    """Update Person records with school_email from legacy data."""

    updated_count = 0
    errors = []

    print(f"📧 {'DRY RUN: Would update' if dry_run else 'Updating'} {len(matches)} Person.school_email fields...")

    if not dry_run:
        # Process each update individually to handle constraint violations gracefully
        for match in matches:
            try:
                person = match["person"]
                school_email = match["legacy_school_email"]

                # Double-check if this email is already in use by another person
                # (in case it was added since we did our initial check)
                if Person.objects.filter(school_email=school_email).exclude(id=person.id).exists():
                    # Skip this record to avoid duplicate constraint violation
                    continue

                # Update the person's school_email field
                person.school_email = school_email
                person.save(update_fields=["school_email"])

                updated_count += 1

                if updated_count % 100 == 0:
                    print(f"   ✅ Updated {updated_count} records...")

            except Exception as e:
                error_msg = f"Failed to update Person {person.id}: {e}"
                errors.append(error_msg)
                print(f"   ❌ {error_msg}")

                # Continue with other records even if one fails
    else:
        # Dry run - just show what would be updated
        for i, match in enumerate(matches[:10], 1):  # Show first 10 examples
            person = match["person"]
            current = match["current_school_email"]
            school = match["legacy_school_email"]

            print(f"   {i}. Student {match['student_profile'].student_id} ({person.full_name})")
            print(f"      Current school_email: '{current}' → Legacy school_email: '{school}'")

        if len(matches) > 10:
            print(f"   ... and {len(matches) - 10} more records")

    return updated_count, errors


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Populate Person.school_email from legacy_students")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")

    args = parser.parse_args()

    print("📬 Person School Email Population Script")
    print("=" * 60)

    try:
        # Get legacy school email data
        print("🔍 Fetching school emails from legacy_students table...")
        legacy_data = get_legacy_school_emails()
        print(f"   Found {len(legacy_data)} legacy records with school emails")

        # Find matching Person records that need school_email populated
        print("🔎 Finding Person records that need school_email populated...")
        matches = find_matching_persons(legacy_data, limit=args.limit)
        print(f"   Found {len(matches)} Person records to update")

        if not matches:
            print("✅ No records need updating!")
            return

        # Show some statistics
        school_emails = [m["legacy_school_email"] for m in matches]
        unique_domains = {email.split("@")[1] for email in school_emails if "@" in email}
        print(f"   Email domains: {', '.join(sorted(unique_domains))}")

        # Update records
        updated_count, errors = update_school_emails(matches, dry_run=args.dry_run)

        # Print results
        print("\n📊 RESULTS")
        print("=" * 60)

        if args.dry_run:
            print(f"🔍 DRY RUN - Would update {len(matches)} Person.school_email fields")
            print("   Run without --dry-run to execute the updates")
        else:
            print(f"✅ Successfully updated {updated_count} Person.school_email fields")

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
