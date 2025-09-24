"""Load only the percentage-based grade conversions from V0.

Special grades (I, IP, AU, CR, NC, P, W) are handled as letter grades
in application logic, not through percentage conversions.
"""

from decimal import Decimal

from apps.common.management.base_migration import BaseMigrationCommand
from apps.grading.models import GradeConversion, GradingScale


class Command(BaseMigrationCommand):
    """Load percentage-based grade conversions for Academic scale."""

    help = "Load percentage-based grade conversions (A+ through F) for Standard Academic Scale"

    def get_rejection_categories(self):
        return ["scale_not_found", "duplicate_conversion", "validation_error"]

    def execute_migration(self, *args, **options):
        """Main command handler."""
        self.record_input_stats(
            source="V0 grading_schoolstructuralunit.json fixture",
            percentage_based_grades=11,  # A+ through F
            special_grades_excluded=4,  # I, P, W, AU (handled in app logic)
        )

        self.stdout.write("📊 Loading percentage-based grade conversions...")

        try:
            conversions_created = self._create_academic_conversions()
            self.record_success("grade_conversions_created", conversions_created)

            self.stdout.write(
                self.style.SUCCESS(f"✅ Successfully loaded {conversions_created} percentage-based grade conversions"),
            )

            self._show_special_grades_info()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to load conversions: {e}"))
            raise

    def _create_academic_conversions(self) -> int:
        """Create percentage-based conversions for Standard Academic Scale."""
        try:
            academic_scale = GradingScale.objects.get(name="Standard Academic Scale")
        except GradingScale.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("❌ Standard Academic Scale not found. Run load_v0_grading_scales_simple first."),
            )
            return 0

        # Only percentage-based grades from V0 fixture
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
                    (
                        f"   ✅ {conv_data['letter_grade']}: {conv_data['min_percentage']}"
                        f"-{conv_data['max_percentage']}% = {conv_data['gpa_points']} GPA"
                    ),
                )
            else:
                self.stdout.write(f"   ⚠️  Already exists: {conv_data['letter_grade']}")

        return created_count

    def _show_special_grades_info(self):
        """Show information about special grades."""
        self.stdout.write("\n📋 Special grades (handled in application logic, not percentage conversions):")

        special_grades = [
            ("I", "Incomplete - Student did not complete course requirements"),
            ("IP", "In Progress - Course still in session"),
            ("AU", "Audit - Student audited course for no credit"),
            ("P", "Pass - Passing grade with no numeric value"),
            ("W", "Withdrawal - Student withdrew from course"),
            ("CR", "Credit - Credit awarded (transfer/equivalency)"),
            ("NC", "No Credit - No credit awarded"),
        ]

        for grade, description in special_grades:
            self.stdout.write(f"   {grade}: {description} (0.0 GPA points)")

        self.stdout.write("\n✅ Passing grades: D and above (D, C-, C, C+, B-, B, B+, A-, A, A+)")
        self.stdout.write("❌ Non-passing: F")
        self.stdout.write("⚠️  Special grades: Handled case-by-case in enrollment status logic")
