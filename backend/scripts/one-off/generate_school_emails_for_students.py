#!/usr/bin/env python3
"""
Generate school emails for students based on their names.

Creates school emails in the format firstname.lastname@pucsr.edu.kh for all students
who don't already have school emails. Uses the Person.full_name field to generate
appropriate email addresses.

Usage:
    # Dry run to see what would be generated
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/one-off/generate_school_emails_for_students.py --dry-run

    # Generate for first 100 students (testing)
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/one-off/generate_school_emails_for_students.py --limit 100 --dry-run

    # Execute the generation
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/one-off/generate_school_emails_for_students.py
"""

import os
import re
import sys
from pathlib import Path

import django

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import transaction

from apps.people.models import StudentProfile


def clean_name_for_email(name):
    """Convert a name to email-safe format."""
    if not name:
        return ""

    # Remove common titles and parenthetical content
    name = re.sub(r"\(.*?\)", "", name)  # Remove (content)
    name = re.sub(r"\bMR\.?\b|\bMRS\.?\b|\bMS\.?\b|\bDR\.?\b|\bPROF\.?\b", "", name, flags=re.IGNORECASE)

    # Split into parts and clean
    parts = name.strip().split()
    clean_parts = []

    for part in parts:
        # Remove special characters and keep only letters
        clean_part = re.sub(r"[^a-zA-Z]", "", part).lower()
        if clean_part and len(clean_part) > 1:  # Skip single letters
            clean_parts.append(clean_part)

    return clean_parts


def generate_email_from_name(full_name):
    """Generate email address from full name."""
    clean_parts = clean_name_for_email(full_name)

    if len(clean_parts) >= 2:
        # Use first and last name
        return f"{clean_parts[0]}.{clean_parts[-1]}@pucsr.edu.kh"
    elif len(clean_parts) == 1:
        # Single name - use it twice or add number
        return f"{clean_parts[0]}.{clean_parts[0]}@pucsr.edu.kh"
    else:
        # Fallback
        return None


def find_students_needing_emails(limit=None):
    """Find students who need school emails generated."""
    students = []

    # Get students whose Person record has no school_email
    query = (
        StudentProfile.objects.select_related("person")
        .filter(person__school_email__isnull=True)
        .order_by("student_id")
    )

    if limit:
        query = query[:limit]

    for student_profile in query:
        person = student_profile.person

        # Skip if already has school email
        if person.school_email:
            continue

        # Generate proposed email
        proposed_email = generate_email_from_name(person.full_name)

        if proposed_email:
            students.append(
                {
                    "student_profile": student_profile,
                    "person": person,
                    "proposed_email": proposed_email,
                    "current_school_email": person.school_email,
                }
            )

    return students


def check_for_duplicates(students):
    """Check for duplicate email addresses in proposed list."""
    email_counts = {}
    duplicates = []

    for student in students:
        email = student["proposed_email"]
        if email in email_counts:
            email_counts[email] += 1
            if email_counts[email] == 2:  # First duplicate
                duplicates.append(email)
        else:
            email_counts[email] = 1

    return duplicates, email_counts


def resolve_duplicates(students):
    """Resolve duplicate emails by adding numbers."""
    email_counts = {}

    for student in students:
        base_email = student["proposed_email"]

        if base_email in email_counts:
            # This is a duplicate, add number
            email_counts[base_email] += 1
            # Change from user@domain to user2@domain, user3@domain, etc.
            user_part, domain_part = base_email.split("@")
            numbered_email = f"{user_part}{email_counts[base_email]}@{domain_part}"
            student["proposed_email"] = numbered_email
        else:
            email_counts[base_email] = 1

    return students


def update_school_emails(students, dry_run=True):
    """Update Person records with generated school emails."""
    updated_count = 0
    errors = []

    print(f"📧 {'DRY RUN: Would generate' if dry_run else 'Generating'} {len(students)} school emails...")

    if not dry_run:
        with transaction.atomic():
            for student in students:
                try:
                    person = student["person"]
                    school_email = student["proposed_email"]

                    # Update the person's school_email field
                    person.school_email = school_email
                    person.save(update_fields=["school_email"])

                    updated_count += 1

                    if updated_count % 100 == 0:
                        print(f"   ✅ Generated {updated_count} school emails...")

                except Exception as e:
                    error_msg = f"Failed to update Person {person.id}: {e}"
                    errors.append(error_msg)
                    print(f"   ❌ {error_msg}")
    else:
        # Dry run - show examples
        for i, student in enumerate(students[:10], 1):
            person = student["person"]
            proposed = student["proposed_email"]

            print(f"   {i}. Student {student['student_profile'].student_id} ({person.full_name})")
            print(f"      Generated: '{proposed}'")

        if len(students) > 10:
            print(f"   ... and {len(students) - 10} more emails")

    return updated_count, errors


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate school emails for students")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated without making changes")
    parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")

    args = parser.parse_args()

    print("📬 Student School Email Generation Script")
    print("=" * 60)

    try:
        # Find students needing emails
        print("🔍 Finding students who need school emails...")
        students = find_students_needing_emails(limit=args.limit)
        print(f"   Found {len(students)} students needing school emails")

        if not students:
            print("✅ No students need school emails generated!")
            return

        # Check for duplicates before resolving
        duplicates, email_counts = check_for_duplicates(students)
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} duplicate email patterns:")
            for dup in duplicates[:5]:  # Show first 5
                print(f"   {dup} ({email_counts[dup]} occurrences)")
            if len(duplicates) > 5:
                print(f"   ... and {len(duplicates) - 5} more duplicates")

            print("🔧 Resolving duplicates by adding numbers...")
            students = resolve_duplicates(students)

        # Show statistics
        unique_domains = {s["proposed_email"].split("@")[1] for s in students if "@" in s["proposed_email"]}
        print(f"   Email domains: {', '.join(sorted(unique_domains))}")

        # Sample of proposed emails
        sample_emails = [s["proposed_email"] for s in students[:5]]
        print(f"   Sample emails: {', '.join(sample_emails)}")

        # Generate emails
        updated_count, errors = update_school_emails(students, dry_run=args.dry_run)

        # Print results
        print("\n📊 RESULTS")
        print("=" * 60)

        if args.dry_run:
            print(f"🔍 DRY RUN - Would generate {len(students)} school emails")
            print("   Run without --dry-run to execute the generation")
        else:
            print(f"✅ Successfully generated {updated_count} school emails")

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
