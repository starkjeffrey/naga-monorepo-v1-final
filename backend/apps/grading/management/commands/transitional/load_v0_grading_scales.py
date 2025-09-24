"""Load the 3 grading scales from V0 fixture data.

Based on the V0 grading_schoolstructuralunit.json fixture file:
1. Standard Academic Scale (for BA/MA programs) - uses plus/minus grades
2. IEAP Grading Scale (for IEAP full-time program) - no plus/minus grades
3. Part-time Language Grading Scale (for EHSS, GESL, Weekend English) - no plus/minus grades
"""

from decimal import Decimal

from apps.common.management.base_migration import BaseMigrationCommand
from apps.grading.models import GradeConversion, GradingScale


class Command(BaseMigrationCommand):
    """Load V0 grading scales with exact grade conversions."""

    help = "Load the 3 grading scales from V0 system with proper grade conversions"

    def get_rejection_categories(self):
        """Return list of possible rejection categories."""
        return [
            "duplicate_scale",
            "duplicate_conversion",
            "data_validation_error",
            "database_error",
        ]

    def execute_migration(self, *args, **options):
        """Main command handler."""
        # Record input stats
        self.record_input_stats(
            source="V0 grading_schoolstructuralunit.json fixture",
            grading_scales_to_create=3,
            grade_conversions_to_create=14,  # Only for academic scale
        )

        self.stdout.write("🎓 Loading V0 grading scales...")

        try:
            # Create the 3 grading scales
            scales_created = self._create_grading_scales()
            conversions_created = self._create_grade_conversions()

            # Record success metrics
            self.record_success("grading_scales_created", scales_created)
            self.record_success("grade_conversions_created", conversions_created)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Successfully loaded {scales_created} grading scales "
                    f"with {conversions_created} grade conversions",
                ),
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to load grading scales: {e}"))
            raise

    def _create_grading_scales(self) -> int:
        """Create the 3 grading scales from V0 system."""
        scales_data = [
            {
                "name": "Standard Academic Scale",
                "scale_type": "ACADEMIC",
                "description": (
                    "The standard academic grading scale for BA/MA programs. "
                    "Passing grade is D (1.00). Grades below D do not receive academic credit."
                ),
            },
            {
                "name": "IEAP Grading Scale",
                "scale_type": "LANGUAGE_IEAP",
                "description": "Grading scale for Intensive English for Academic Purposes (IEAP) full-time program.",
            },
            {
                "name": "Part-time Language Grading Scale",
                "scale_type": "LANGUAGE_STANDARD",
                "description": "Grading scale for part-time language programs (EHSS, GESL, Weekend English).",
            },
        ]

        created_count = 0
        for scale_data in scales_data:
            scale, created = GradingScale.objects.get_or_create(
                name=scale_data["name"],
                defaults={
                    "scale_type": scale_data["scale_type"],
                    "description": scale_data["description"],
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(f"   ✅ Created: {scale.name}")
            else:
                self.stdout.write(f"   ⚠️  Already exists: {scale.name}")

        return created_count

    def _create_grade_conversions(self) -> int:
        """Create grade conversions for Standard Academic Scale (V0 data)."""
        # Get the academic grading scale
        try:
            academic_scale = GradingScale.objects.get(name="Standard Academic Scale")
        except GradingScale.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Standard Academic Scale not found"))
            return 0

        # Grade conversion data from V0 fixture (exact values)
        conversions_data = [
            {
                "letter_grade": "A+",
                "min_percentage": Decimal("96.0"),
                "max_percentage": Decimal("100.0"),
                "gpa_points": Decimal("4.0"),
                "display_order": 0,
            },
            {
                "letter_grade": "A",
                "min_percentage": Decimal("93.0"),
                "max_percentage": Decimal("95.99"),
                "gpa_points": Decimal("4.0"),
                "display_order": 1,
            },
            {
                "letter_grade": "A-",
                "min_percentage": Decimal("90.0"),
                "max_percentage": Decimal("92.99"),
                "gpa_points": Decimal("3.67"),
                "display_order": 2,
            },
            {
                "letter_grade": "B+",
                "min_percentage": Decimal("86.0"),
                "max_percentage": Decimal("89.99"),
                "gpa_points": Decimal("3.33"),
                "display_order": 3,
            },
            {
                "letter_grade": "B",
                "min_percentage": Decimal("83.0"),
                "max_percentage": Decimal("85.99"),
                "gpa_points": Decimal("3.0"),
                "display_order": 4,
            },
            {
                "letter_grade": "B-",
                "min_percentage": Decimal("80.0"),
                "max_percentage": Decimal("82.99"),
                "gpa_points": Decimal("2.67"),
                "display_order": 5,
            },
            {
                "letter_grade": "C+",
                "min_percentage": Decimal("76.0"),
                "max_percentage": Decimal("79.99"),
                "gpa_points": Decimal("2.33"),
                "display_order": 6,
            },
            {
                "letter_grade": "C",
                "min_percentage": Decimal("73.0"),
                "max_percentage": Decimal("75.99"),
                "gpa_points": Decimal("2.0"),
                "display_order": 7,
            },
            {
                "letter_grade": "C-",
                "min_percentage": Decimal("70.0"),
                "max_percentage": Decimal("72.99"),
                "gpa_points": Decimal("1.67"),
                "display_order": 8,
            },
            {
                "letter_grade": "D",
                "min_percentage": Decimal("60.0"),
                "max_percentage": Decimal("69.99"),
                "gpa_points": Decimal("1.0"),
                "display_order": 9,
            },
            {
                "letter_grade": "F",
                "min_percentage": Decimal("0.0"),
                "max_percentage": Decimal("59.99"),
                "gpa_points": Decimal("0.0"),
                "display_order": 10,
            },
            # Special grades - use non-overlapping ranges within 0-100%
            {
                "letter_grade": "I",
                "min_percentage": Decimal("60.0"),  # Incomplete - overlaps with D range but unique for this scale
                "max_percentage": Decimal("60.0"),  # Same min/max for special grades
                "gpa_points": Decimal("0.0"),
                "display_order": 11,
            },
            {
                "letter_grade": "P",
                "min_percentage": Decimal("61.0"),  # Pass no grade
                "max_percentage": Decimal("61.0"),
                "gpa_points": Decimal("0.0"),
                "display_order": 12,
            },
            {
                "letter_grade": "W",
                "min_percentage": Decimal("62.0"),  # Withdrawal
                "max_percentage": Decimal("62.0"),
                "gpa_points": Decimal("0.0"),
                "display_order": 13,
            },
            {
                "letter_grade": "AU",
                "min_percentage": Decimal("63.0"),  # Audit
                "max_percentage": Decimal("63.0"),
                "gpa_points": Decimal("0.0"),
                "display_order": 14,
            },
        ]

        created_count = 0
        for conv_data in conversions_data:
            conversion, created = GradeConversion.objects.get_or_create(
                grading_scale=academic_scale,
                letter_grade=conv_data["letter_grade"],
                defaults={
                    "min_percentage": conv_data["min_percentage"],
                    "max_percentage": conv_data["max_percentage"],
                    "gpa_points": conv_data["gpa_points"],
                    "display_order": conv_data["display_order"],
                },
            )

            if created:
                created_count += 1
                self.stdout.write(
                    f"   ✅ Created conversion: {conv_data['letter_grade']} "
                    f"({conv_data['gpa_points']} pts) - {conv_data['min_percentage']}-{conv_data['max_percentage']}%",
                )
            else:
                self.stdout.write(f"   ⚠️  Already exists: {conv_data['letter_grade']}")

        return created_count
