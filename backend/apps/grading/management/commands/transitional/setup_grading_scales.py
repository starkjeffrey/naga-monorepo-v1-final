"""Management command to set up initial grading scales and grade conversions.

This command creates the three primary grading scales used in Naga SIS:
- LANGUAGE_STANDARD: A-F with F<50% (EHSS, GESL, WKEND)
- LANGUAGE_IEAP: A-F with F<60% and different breakpoints
- ACADEMIC: A+ to F with F<60% (BA/MA programs)

Usage:
    python manage.py setup_grading_scales
    python manage.py setup_grading_scales --overwrite  # Replace existing scales
"""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.grading.models import GradeConversion, GradingScale


class Command(BaseCommand):
    help = "Set up initial grading scales and grade conversions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing grading scales",
        )

    def handle(self, *args, **options):
        """Execute the management command."""
        self.stdout.write("Setting up grading scales...")

        try:
            with transaction.atomic():
                # Check if scales already exist
                if GradingScale.objects.exists() and not options["overwrite"]:
                    self.stdout.write(
                        self.style.WARNING("Grading scales already exist. Use --overwrite to replace them."),
                    )
                    return

                if options["overwrite"]:
                    self.stdout.write("Removing existing grading scales...")
                    GradingScale.objects.all().delete()

                # Create the three grading scales
                self._create_language_standard_scale()
                self._create_language_ieap_scale()
                self._create_academic_scale()

                self.stdout.write(self.style.SUCCESS("Successfully set up all grading scales!"))

        except Exception as e:
            msg = f"Error setting up grading scales: {e}"
            raise CommandError(msg) from e

    def _create_language_standard_scale(self):
        """Create Language Standard grading scale (A-F, F<50%)."""
        self.stdout.write("Creating Language Standard scale...")

        scale = GradingScale.objects.create(
            name="Language Standard",
            scale_type=GradingScale.ScaleType.LANGUAGE_STANDARD,
            description=(
                "Standard language grading scale used for EHSS, GESL, and WKEND programs. "
                "F grade for scores below 50%."
            ),
            is_active=True,
        )

        # Grade conversions for Language Standard scale
        conversions = [
            # (letter, min_pct, max_pct, gpa_points)
            ("A", Decimal("90.0"), Decimal("100.0"), Decimal("4.0")),
            ("B", Decimal("80.0"), Decimal("89.99"), Decimal("3.0")),
            ("C", Decimal("70.0"), Decimal("79.99"), Decimal("2.0")),
            ("D", Decimal("50.0"), Decimal("69.99"), Decimal("1.0")),
            ("F", Decimal("0.0"), Decimal("49.99"), Decimal("0.0")),
        ]

        for letter, min_pct, max_pct, gpa_points in conversions:
            GradeConversion.objects.create(
                grading_scale=scale,
                letter_grade=letter,
                min_percentage=min_pct,
                max_percentage=max_pct,
                gpa_points=gpa_points,
            )

        self.stdout.write(f"  ✓ Created {len(conversions)} grade conversions")

    def _create_language_ieap_scale(self):
        """Create Language IEAP grading scale (A-F, F<60%)."""
        self.stdout.write("Creating Language IEAP scale...")

        scale = GradingScale.objects.create(
            name="Language IEAP",
            scale_type=GradingScale.ScaleType.LANGUAGE_IEAP,
            description="IEAP language grading scale with higher passing threshold. F grade for scores below 60%.",
            is_active=True,
        )

        # Grade conversions for Language IEAP scale
        conversions = [
            # (letter, min_pct, max_pct, gpa_points)
            ("A", Decimal("90.0"), Decimal("100.0"), Decimal("4.0")),
            ("B", Decimal("80.0"), Decimal("89.99"), Decimal("3.0")),
            ("C", Decimal("70.0"), Decimal("79.99"), Decimal("2.0")),
            ("D", Decimal("60.0"), Decimal("69.99"), Decimal("1.0")),
            ("F", Decimal("0.0"), Decimal("59.99"), Decimal("0.0")),
        ]

        for letter, min_pct, max_pct, gpa_points in conversions:
            GradeConversion.objects.create(
                grading_scale=scale,
                letter_grade=letter,
                min_percentage=min_pct,
                max_percentage=max_pct,
                gpa_points=gpa_points,
            )

        self.stdout.write(f"  ✓ Created {len(conversions)} grade conversions")

    def _create_academic_scale(self):
        """Create Academic grading scale (A+ to F, F<60%)."""
        self.stdout.write("Creating Academic scale...")

        scale = GradingScale.objects.create(
            name="Academic",
            scale_type=GradingScale.ScaleType.ACADEMIC,
            description=(
                "Academic grading scale for BA and MA programs with plus/minus grades. F grade for scores below 60%."
            ),
            is_active=True,
        )

        # Grade conversions for Academic scale
        conversions = [
            # (letter, min_pct, max_pct, gpa_points)
            ("A+", Decimal("97.0"), Decimal("100.0"), Decimal("4.0")),
            ("A", Decimal("93.0"), Decimal("96.99"), Decimal("4.0")),
            ("A-", Decimal("90.0"), Decimal("92.99"), Decimal("3.7")),
            ("B+", Decimal("87.0"), Decimal("89.99"), Decimal("3.3")),
            ("B", Decimal("83.0"), Decimal("86.99"), Decimal("3.0")),
            ("B-", Decimal("80.0"), Decimal("82.99"), Decimal("2.7")),
            ("C+", Decimal("77.0"), Decimal("79.99"), Decimal("2.3")),
            ("C", Decimal("73.0"), Decimal("76.99"), Decimal("2.0")),
            ("C-", Decimal("70.0"), Decimal("72.99"), Decimal("1.7")),
            ("D+", Decimal("67.0"), Decimal("69.99"), Decimal("1.3")),
            ("D", Decimal("63.0"), Decimal("66.99"), Decimal("1.0")),
            ("D-", Decimal("60.0"), Decimal("62.99"), Decimal("0.7")),
            ("F", Decimal("0.0"), Decimal("59.99"), Decimal("0.0")),
        ]

        for letter, min_pct, max_pct, gpa_points in conversions:
            GradeConversion.objects.create(
                grading_scale=scale,
                letter_grade=letter,
                min_percentage=min_pct,
                max_percentage=max_pct,
                gpa_points=gpa_points,
            )

        self.stdout.write(f"  ✓ Created {len(conversions)} grade conversions")
