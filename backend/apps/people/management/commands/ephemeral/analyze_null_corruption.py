"""Analyze data corruption where NULL was partially imported."""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from apps.people.models import Person


class Command(BaseCommand):
    """Analyze NULL corruption in Person records."""

    help = "Analyze how NULL values were corrupted during import"

    def handle(self, *args, **options):
        """Execute the analysis."""
        self.stdout.write("=" * 80)
        self.stdout.write("NULL CORRUPTION ANALYSIS")
        self.stdout.write("=" * 80)

        # Check citizenship field for "NU"
        self.stdout.write("\nCitizenship Analysis:")
        nu_citizenship = Person.objects.filter(citizenship="NU").count()
        self.stdout.write(f"  - Records with citizenship='NU': {nu_citizenship:,}")

        if nu_citizenship > 0:
            # Show examples
            examples = Person.objects.filter(citizenship="NU")[:5]
            self.stdout.write("\n  Examples:")
            for p in examples:
                self.stdout.write(
                    f"    ID {p.id}: {p.personal_name} {p.family_name}, "
                    f"Citizenship: '{p.citizenship}', Khmer: '{p.khmer_name}'"
                )

        # Check for other truncated NULL patterns
        self.stdout.write("\nChecking for other NULL patterns in citizenship:")
        null_patterns = ["N", "NU", "NUL", "NULL", "Null", "null"]
        for pattern in null_patterns:
            count = Person.objects.filter(citizenship=pattern).count()
            if count > 0:
                self.stdout.write(f"  - citizenship='{pattern}': {count:,} records")

        # Analyze Khmer names more thoroughly
        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Khmer Name Analysis (showing first 50 chars):")

        # Get a sample of unique khmer names to see patterns
        khmer_samples = (
            Person.objects.exclude(Q(khmer_name="") | Q(khmer_name__isnull=True))
            .values_list("khmer_name", flat=True)
            .distinct()[:100]
        )

        # Look for patterns
        null_like_patterns = []
        for sample in khmer_samples:
            # Check if it might be NULL-related
            if any(char in sample for char in ["ណ", "ន", "ុ", "ូ", "ល"]):
                # Check if it's short (likely to be NULL translation)
                if len(sample.strip()) <= 5:
                    null_like_patterns.append(sample)

        if null_like_patterns:
            self.stdout.write("\nShort Khmer names that might be NULL translations:")
            # Count occurrences
            pattern_counts = {}
            for pattern in set(null_like_patterns):
                count = Person.objects.filter(khmer_name=pattern).count()
                pattern_counts[pattern] = count

            # Sort by count
            for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
                self.stdout.write(f"  '{pattern}' : {count:,} records")
                # Show hex representation to see exact characters
                hex_repr = " ".join(f"{ord(c):04X}" for c in pattern)
                self.stdout.write(f"     (Unicode: {hex_repr})")

        # Check for records where citizenship="NU" AND khmer_name looks like NULL
        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Records with BOTH citizenship='NU' AND suspicious Khmer names:")

        suspicious_combo = Person.objects.filter(citizenship="NU").exclude(
            Q(khmer_name="") | Q(khmer_name__isnull=True)
        )[:20]

        for p in suspicious_combo:
            self.stdout.write(f"  ID {p.id}: {p.personal_name} {p.family_name}")
            self.stdout.write(
                f"    Citizenship: '{p.citizenship}', Khmer: '{p.khmer_name}' (len: {len(p.khmer_name.strip())})"
            )

        # Pattern detection
        self.stdout.write("\n" + "=" * 40)
        self.stdout.write("PATTERN DETECTION")
        self.stdout.write("=" * 40)

        # Find the most common short Khmer values
        short_khmer = (
            Person.objects.exclude(Q(khmer_name="") | Q(khmer_name__isnull=True))
            .extra(where=["LENGTH(TRIM(khmer_name)) <= 5"])
            .values("khmer_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        self.stdout.write("\nMost common short Khmer names (likely NULL):")
        for item in short_khmer:
            self.stdout.write(f"  '{item['khmer_name']}': {item['count']:,} records")

        # Summary and recommendations
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 80)

        total_persons = Person.objects.count()
        self.stdout.write(f"\nTotal Person records: {total_persons:,}")
        self.stdout.write(f"Records with citizenship='NU': {nu_citizenship:,}")

        if nu_citizenship > 0:
            percentage = (nu_citizenship / total_persons) * 100
            self.stdout.write(f"Percentage affected: {percentage:.1f}%")

            self.stdout.write("\nLikely import error pattern:")
            self.stdout.write("  - Original data had NULL values")
            self.stdout.write("  - Import process took LEFT(NULL, 2) → 'NU' for citizenship")
            self.stdout.write("  - Import process translated 'NULL' to Khmer script")

            self.stdout.write("\nRecommended fix:")
            self.stdout.write("  1. Set citizenship='KH' for records with citizenship='NU' (if they're Cambodian)")
            self.stdout.write("  2. Clear khmer_name for affected records")
            self.stdout.write("  3. Re-import from original source if available")
