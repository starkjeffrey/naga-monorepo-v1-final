"""Management command to set up initial class part templates for language programs."""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.scheduling.services.template_service import ClassTemplateService


class Command(BaseCommand):
    """Set up initial class part templates for all language programs."""

    help = "Create initial class part templates for EHSS, GESL, IEAP, and EXPRESS programs"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--program",
            type=str,
            choices=["EHSS", "GESL", "IEAP", "EXPRESS"],
            help="Specific program to set up templates for",
        )
        parser.add_argument(
            "--level",
            type=int,
            help="Specific level to set up templates for",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without creating",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        program = options.get("program")
        level = options.get("level")
        dry_run = options.get("dry_run")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        service = ClassTemplateService()

        # Define template configurations for each program
        templates = self.get_template_configurations()

        # Filter by program/level if specified
        if program:
            templates = {k: v for k, v in templates.items() if k[0] == program}
        if level is not None:
            templates = {k: v for k, v in templates.items() if k[1] == level}

        # Create templates
        created_count = 0
        for (prog_code, level_num), parts_config in templates.items():
            self.stdout.write(f"Creating template for {prog_code}-{level_num:02d}...")

            if not dry_run:
                try:
                    template_set = service.create_template_set(
                        program_code=prog_code,
                        level_number=level_num,
                        parts_config=parts_config,
                        effective_date=timezone.now().date(),
                        name=f"{prog_code} Level {level_num} Template",
                    )
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Created {template_set}"))
                    created_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Failed: {e!s}"))
            else:
                self.stdout.write(f"  Would create template with {len(parts_config)} parts")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully created {created_count} template sets"))

    def get_template_configurations(self) -> dict:
        """Get template configurations for all programs and levels.

        Returns:
            Dictionary mapping (program, level) to parts configuration
        """
        templates = {}

        # EHSS Templates (example for levels 1-12)
        for level in range(1, 13):
            if level <= 6:
                # Lower levels: Grammar focus
                parts = [
                    {
                        "name": "Grammar & Vocabulary",
                        "class_part_type": "GRAMMAR",
                        "class_part_code": "A",
                        "meeting_days_pattern": "MON,WED",
                        "grade_weight": Decimal("0.4"),
                        "sequence_order": 1,
                    },
                    {
                        "name": "Conversation Practice",
                        "class_part_type": "CONVERSATION",
                        "class_part_code": "B",
                        "meeting_days_pattern": "TUE,THU",
                        "grade_weight": Decimal("0.4"),
                        "sequence_order": 2,
                    },
                    {
                        "name": "Computer Lab",
                        "class_part_type": "COMPUTER",
                        "class_part_code": "C",
                        "meeting_days_pattern": "FRI",
                        "grade_weight": Decimal("0.2"),
                        "sequence_order": 3,
                    },
                ]
            elif level == 7:
                # Level 7: Special Ventures structure
                parts = [
                    {
                        "name": "Ventures",
                        "class_part_type": "MAIN",
                        "class_part_code": "A",
                        "meeting_days_pattern": "MON,WED",
                        "grade_weight": Decimal("0.4"),
                        "sequence_order": 1,
                    },
                    {
                        "name": "Reading",
                        "class_part_type": "READING",
                        "class_part_code": "B",
                        "meeting_days_pattern": "TUE,THU",
                        "grade_weight": Decimal("0.4"),
                        "sequence_order": 2,
                    },
                    {
                        "name": "Computer Training",
                        "class_part_type": "COMPUTER",
                        "class_part_code": "C",
                        "meeting_days_pattern": "FRI",
                        "grade_weight": Decimal("0.2"),
                        "sequence_order": 3,
                    },
                ]
            else:
                # Upper levels: Advanced skills
                parts = [
                    {
                        "name": "Academic Writing",
                        "class_part_type": "WRITING",
                        "class_part_code": "A",
                        "meeting_days_pattern": "MON,WED",
                        "grade_weight": Decimal("0.35"),
                        "sequence_order": 1,
                    },
                    {
                        "name": "Reading & Discussion",
                        "class_part_type": "READING",
                        "class_part_code": "B",
                        "meeting_days_pattern": "TUE,THU",
                        "grade_weight": Decimal("0.35"),
                        "sequence_order": 2,
                    },
                    {
                        "name": "Speaking & Presentation",
                        "class_part_type": "SPEAKING",
                        "class_part_code": "C",
                        "meeting_days_pattern": "FRI",
                        "grade_weight": Decimal("0.3"),
                        "sequence_order": 3,
                    },
                ]

            templates[("EHSS", level)] = parts

        # GESL Templates (similar structure to EHSS)
        for level in range(1, 13):
            # GESL follows similar pattern to EHSS
            templates[("GESL", level)] = templates[("EHSS", level)].copy()

        # IEAP Templates (intensive program with different structure)
        ieap_parts = [
            {
                "name": "Core Language Skills",
                "class_part_type": "MAIN",
                "class_part_code": "A",
                "meeting_days_pattern": "MON,WED,FRI",
                "grade_weight": Decimal("0.5"),
                "sequence_order": 1,
            },
            {
                "name": "Academic Skills",
                "class_part_type": "WRITING",
                "class_part_code": "B",
                "meeting_days_pattern": "TUE,THU",
                "grade_weight": Decimal("0.3"),
                "sequence_order": 2,
            },
            {
                "name": "Lab & Practice",
                "class_part_type": "LAB",
                "class_part_code": "C",
                "meeting_days_pattern": "MON,WED",
                "grade_weight": Decimal("0.2"),
                "sequence_order": 3,
            },
        ]

        for level in [-2, -1, 1, 2, 3, 4]:  # IEAP levels
            templates[("IEAP", level)] = ieap_parts.copy()

        # EXPRESS (Weekend) Templates
        express_parts = [
            {
                "name": "Integrated Skills",
                "class_part_type": "MAIN",
                "class_part_code": "A",
                "meeting_days_pattern": "SAT",
                "grade_weight": Decimal("0.5"),
                "sequence_order": 1,
            },
            {
                "name": "Communication Practice",
                "class_part_type": "CONVERSATION",
                "class_part_code": "B",
                "meeting_days_pattern": "SUN",
                "grade_weight": Decimal("0.5"),
                "sequence_order": 2,
            },
        ]

        for level in [-1, 1, 2, 3, 4]:  # EXPRESS levels
            templates[("EXPRESS", level)] = express_parts.copy()

        return templates
