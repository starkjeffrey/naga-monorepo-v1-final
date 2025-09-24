"""Load the 3 grading scales from V0 (without detailed conversions for now).

This creates the 3 grading scale structures to validate the correct grades are available.
"""

from apps.common.management.base_migration import BaseMigrationCommand
from apps.grading.models import GradingScale


class Command(BaseMigrationCommand):
    """Load V0 grading scales (structure only)."""

    help = "Load the 3 grading scales from V0 system"

    def get_rejection_categories(self):
        """Return list of possible rejection categories."""
        return ["duplicate_scale", "data_validation_error"]

    def execute_migration(self, *args, **options):
        """Main command handler."""
        # Record input stats
        self.record_input_stats(
            source="V0 grading_schoolstructuralunit.json fixture",
            grading_scales_to_create=3,
        )

        self.stdout.write("🎓 Loading V0 grading scales...")

        try:
            # Create the 3 grading scales
            scales_created = self._create_grading_scales()

            # Record success metrics
            self.record_success("grading_scales_created", scales_created)

            self.stdout.write(self.style.SUCCESS(f"✅ Successfully loaded {scales_created} grading scales"))

            # Show what grades are available
            self._show_available_grades()

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
                    "The standard academic grading scale for BA/MA programs. Passing grade is D (1.00). "
                    "Grades below D do not receive academic credit. Uses A+, A, A-, B+, B, B-, C+, C, C-, "
                    "D, F plus special grades I, P, W, AU."
                ),
            },
            {
                "name": "IEAP Grading Scale",
                "scale_type": "LANGUAGE_IEAP",
                "description": (
                    "Grading scale for Intensive English for Academic Purposes (IEAP) full-time program. "
                    "Uses A, B, C, D, F (no plus/minus grades)."
                ),
            },
            {
                "name": "Part-time Language Grading Scale",
                "scale_type": "LANGUAGE_STANDARD",
                "description": (
                    "Grading scale for part-time language programs (EHSS, GESL, Weekend English). "
                    "Uses A, B, C, D, F (no plus/minus grades)."
                ),
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

    def _show_available_grades(self):
        """Show what grades are available for each scale."""
        self.stdout.write("\n📋 Available grading scales:")

        for scale in GradingScale.objects.all():
            self.stdout.write(f"\n🎓 {scale.name} ({scale.get_scale_type_display()})")
            self.stdout.write(f"   {scale.description}")

            if scale.scale_type == "ACADEMIC":
                self.stdout.write("   Available grades: A+, A, A-, B+, B, B-, C+, C, C-, D, F, I, P, W, AU")
                self.stdout.write("   ✅ Passing: D and above (no D+/D- at this school)")
            else:
                self.stdout.write("   Available grades: A, B, C, D, F, I, P, W, AU")
                self.stdout.write("   ✅ Passing: D and above")
