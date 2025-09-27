"""Analyze Khmer names in the Person model to identify issues."""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from apps.people.models import Person


class Command(BaseCommand):
    """Analyze Khmer names to identify data quality issues."""

    help = "Analyze Khmer names in Person records"

    def handle(self, *args, **options):
        """Execute the analysis."""
        self.stdout.write("=" * 80)
        self.stdout.write("KHMER NAME ANALYSIS")
        self.stdout.write("=" * 80)

        # Total persons
        total_persons = Person.objects.count()
        self.stdout.write(f"\nTotal Person records: {total_persons:,}")

        # Khmer name statistics
        with_khmer = Person.objects.exclude(khmer_name="").exclude(khmer_name__isnull=True).count()
        empty_khmer = Person.objects.filter(Q(khmer_name="") | Q(khmer_name__isnull=True)).count()

        self.stdout.write("\nKhmer Name Statistics:")
        self.stdout.write(f"  - With Khmer names: {with_khmer:,} ({with_khmer / total_persons * 100:.1f}%)")
        self.stdout.write(f"  - Empty/NULL: {empty_khmer:,} ({empty_khmer / total_persons * 100:.1f}%)")

        # Check for various NULL representations
        self.stdout.write("\nChecking for NULL-like values:")
        null_variations = ["NULL", "null", "Null", "NONE", "None", "none", "នូល", "ណូល", "N/A", "n/a", "-", "--"]

        for variant in null_variations:
            count = Person.objects.filter(khmer_name=variant).count()
            if count > 0:
                self.stdout.write(f"  - '{variant}': {count} records")
                # Show examples
                examples = Person.objects.filter(khmer_name=variant)[:3]
                for p in examples:
                    self.stdout.write(f"      ID {p.id}: {p.personal_name} {p.family_name}")

        # Check for actual Khmer script
        self.stdout.write("\nKhmer Script Analysis:")

        # Has Khmer Unicode characters
        khmer_script = Person.objects.filter(khmer_name__regex=r"[\u1780-\u17FF]+").count()
        self.stdout.write(f"  - Contains Khmer script: {khmer_script:,}")

        # Check for mixed content (English + Khmer)
        mixed = (
            Person.objects.filter(khmer_name__regex=r"[a-zA-Z]").filter(khmer_name__regex=r"[\u1780-\u17FF]").count()
        )
        self.stdout.write(f"  - Mixed English/Khmer: {mixed:,}")

        # Check for only English characters
        only_english = Person.objects.filter(khmer_name__regex=r"^[a-zA-Z\s\-\.]+$").exclude(khmer_name="").count()
        self.stdout.write(f"  - Only English characters: {only_english:,}")

        # Length analysis
        self.stdout.write("\nLength Analysis:")

        # Very short (might be invalid)
        very_short = Person.objects.filter(khmer_name__regex=r"^.{1,2}$").exclude(khmer_name="").count()
        self.stdout.write(f"  - Very short (1-2 chars): {very_short:,}")

        # Show some examples of actual Khmer names
        self.stdout.write("\nExamples of valid Khmer names:")
        valid_khmer = Person.objects.filter(
            khmer_name__regex=r"[\u1780-\u17FF]+"
        ).exclude(
            khmer_name__regex=r"[a-zA-Z]"  # Exclude mixed
        )[:5]

        for p in valid_khmer:
            self.stdout.write(f"  - {p.personal_name} {p.family_name}: '{p.khmer_name.strip()}'")

        # Students specifically
        self.stdout.write("\n" + "=" * 40)
        self.stdout.write("STUDENT-SPECIFIC ANALYSIS")
        self.stdout.write("=" * 40)

        from apps.people.models import StudentProfile

        total_students = StudentProfile.objects.count()
        students_with_khmer = StudentProfile.objects.filter(person__khmer_name__regex=r"[\u1780-\u17FF]+").count()
        students_no_khmer = total_students - students_with_khmer

        self.stdout.write("\nStudent Statistics:")
        self.stdout.write(f"  - Total students: {total_students:,}")
        self.stdout.write(
            f"  - With Khmer names: {students_with_khmer:,} ({students_with_khmer / total_students * 100:.1f}%)"
        )
        self.stdout.write(
            f"  - Without Khmer names: {students_no_khmer:,} ({students_no_khmer / total_students * 100:.1f}%)"
        )

        # Check for patterns in missing Khmer names
        self.stdout.write("\nMissing Khmer Names by Citizenship:")

        # Group by citizenship
        citizenship_stats = (
            Person.objects.filter(Q(khmer_name="") | Q(khmer_name__isnull=True))
            .values("citizenship")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        for stat in citizenship_stats:
            self.stdout.write(f"  - {stat['citizenship'] or 'Unknown'}: {stat['count']:,}")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("RECOMMENDATIONS:")
        self.stdout.write("=" * 80)

        if empty_khmer > 0:
            self.stdout.write(f"\n1. {empty_khmer:,} records have no Khmer name")
            self.stdout.write("   Consider importing from original source or using transliteration")

        if only_english > 0:
            self.stdout.write(f"\n2. {only_english:,} records have English text in Khmer name field")
            self.stdout.write("   These may need to be converted to Khmer script")

        self.stdout.write("\nRun 'python manage.py fix_khmer_names --dry-run' to preview fixes")
