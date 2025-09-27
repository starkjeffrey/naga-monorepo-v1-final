"""Management command to add missing language courses: IEAP-BEG and PRE-B2.

These courses are referenced in legacy data but were missing from the Course table.
They correspond to existing language level enums but need Course records for enrollment import.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.curriculum.models import Course, Division


class Command(BaseCommand):
    """Add missing language courses IEAP-BEG and PRE-B2."""

    help = "Add missing language courses IEAP-BEG and PRE-B2 to support legacy data import"

    def handle(self, *args, **options):
        """Add the missing courses."""
        with transaction.atomic():
            # Get or create Language Division
            language_division, created = Division.objects.get_or_create(
                name="Language Division",
                defaults={
                    "short_name": "LANG",
                    "description": "Language instruction programs",
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(f"Created Language Division: {language_division}")

            courses_added = 0

            # Add IEAP-BEG course
            ieap_beg, created = Course.objects.get_or_create(
                code="IEAP-BEG",
                defaults={
                    "title": "IEAP Beginner Level",
                    "short_title": "IEAP BEG",
                    "description": "Intensive English for Academic Purposes - Beginner Level",
                    "credits": 1,
                    "is_language": True,
                    "is_foundation_year": False,
                    "division": language_division,
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Added course: {ieap_beg.code} - {ieap_beg.title}"))
                courses_added += 1
            else:
                self.stdout.write(f"⚠️  Course already exists: {ieap_beg.code}")

            # Add PRE-B2 course
            pre_b2, created = Course.objects.get_or_create(
                code="PRE-B2",
                defaults={
                    "title": "Part-Time Pre-Beginner Level 2",
                    "short_title": "PRE-B2",
                    "description": "Part-Time English Program - Pre-Beginner Level 2",
                    "credits": 1,
                    "is_language": True,
                    "is_foundation_year": False,
                    "division": language_division,
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Added course: {pre_b2.code} - {pre_b2.title}"))
                courses_added += 1
            else:
                self.stdout.write(f"⚠️  Course already exists: {pre_b2.code}")

            # Summary
            self.stdout.write("\n📊 Summary:")
            self.stdout.write(f"   Courses added: {courses_added}")
            self.stdout.write("   Total courses checked: 2")

            if courses_added > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✅ Successfully added {courses_added} missing language courses!"),
                )
            else:
                self.stdout.write("\n💡 All courses already exist - no changes made.")
