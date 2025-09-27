"""
Management command to populate the AcademicProgression denormalized view.

This command creates summary records from AcademicJourney data for performance
optimization. The AcademicProgression model provides fast queries for reporting
and analytics without the need to join multiple tables.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.enrollment.models_progression import AcademicJourney, AcademicProgression


class Command(BaseCommand):
    """Populate AcademicProgression view from AcademicJourney data."""

    help = "Populate the AcademicProgression denormalized view from AcademicJourney data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing AcademicProgression records before populating",
        )
        parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing (default: 100)")

    def handle(self, *args, **options):
        """Main command handler."""
        clear_existing = options["clear_existing"]
        batch_size = options["batch_size"]

        if clear_existing:
            self.stdout.write("🗑️  Clearing existing AcademicProgression records...")
            count = AcademicProgression.objects.all().delete()[0]
            self.stdout.write(self.style.SUCCESS(f"Cleared {count} existing records"))

        # Get all academic journeys
        journeys = AcademicJourney.objects.select_related("student__person", "current_program").prefetch_related(
            "milestones__program"
        )

        total_journeys = journeys.count()
        self.stdout.write(f"📊 Processing {total_journeys} academic journeys...")

        created_count = 0
        processed_count = 0

        # Process in batches
        for i in range(0, total_journeys, batch_size):
            batch = journeys[i : i + batch_size]
            progression_records = []

            for journey in batch:
                progression_data = self.build_progression_from_journey(journey)
                if progression_data:
                    progression_records.append(AcademicProgression(**progression_data))
                processed_count += 1

            # Bulk create the batch
            if progression_records:
                with transaction.atomic():
                    AcademicProgression.objects.bulk_create(progression_records)
                    created_count += len(progression_records)

            # Progress indicator
            if (i + batch_size) % 500 == 0 or (i + batch_size) >= total_journeys:
                self.stdout.write(f"  Processed {min(i + batch_size, total_journeys)}/{total_journeys} journeys...")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Successfully created {created_count} AcademicProgression records from {processed_count} journeys"
            )
        )

    def build_progression_from_journey(self, journey):
        """Build AcademicProgression data from an AcademicJourney."""
        try:
            # Basic student information
            data = {
                "student_name": journey.student.person.full_name,
                "student_id_number": journey.student.student_id,
                "entry_term": "",  # Will be determined from milestones
                "entry_program": "",  # Will be determined from milestones
                "current_status": journey.journey_status,
                "last_enrollment_term": "",  # Will be determined from milestones
                "last_updated": journey.updated_at,
            }

            # Get milestones for detailed analysis
            milestones = list(journey.milestones.order_by("milestone_date"))

            if not milestones:
                # No milestones, use basic journey data
                data.update(
                    {
                        "entry_term": "",
                        "entry_program": journey.current_program.name if journey.current_program else "",
                        "last_enrollment_term": "",
                    }
                )
                return data

            # Analyze milestones to populate detailed fields
            first_milestone = milestones[0]
            last_milestone = milestones[-1]

            # Entry information
            data["entry_term"] = (
                getattr(first_milestone.academic_term, "code", "") if first_milestone.academic_term else ""
            )
            data["entry_program"] = first_milestone.program.name if first_milestone.program else ""
            data["last_enrollment_term"] = (
                getattr(last_milestone.academic_term, "code", "") if last_milestone.academic_term else ""
            )

            # Language program analysis
            language_milestones = [m for m in milestones if m.program and m.program.program_type == "LANGUAGE"]
            if language_milestones:
                data["language_start_date"] = language_milestones[0].milestone_date
                data["language_final_level"] = language_milestones[-1].level or ""
                data["language_terms"] = len({m.academic_term for m in language_milestones if m.academic_term})

                # Determine completion status
                completed_milestone = next(
                    (m for m in language_milestones if m.milestone_type == "PROGRAM_COMPLETION"), None
                )
                if completed_milestone:
                    data["language_completion_status"] = "GRADUATED"
                    data["language_completion_date"] = completed_milestone.milestone_date
                else:
                    data["language_completion_status"] = "ACTIVE" if journey.journey_status == "ACTIVE" else "DROPPED"

            # BA program analysis
            ba_milestones = [m for m in milestones if m.program and m.program.program_type == "UNDERGRADUATE"]
            if ba_milestones:
                data["ba_start_date"] = ba_milestones[0].milestone_date
                data["ba_major"] = ba_milestones[0].program.name if ba_milestones[0].program else ""
                data["ba_terms"] = len({m.academic_term for m in ba_milestones if m.academic_term})

                # Determine completion status
                completed_milestone = next(
                    (m for m in ba_milestones if m.milestone_type == "PROGRAM_COMPLETION"), None
                )
                if completed_milestone:
                    data["ba_completion_status"] = "GRADUATED"
                    data["ba_completion_date"] = completed_milestone.milestone_date

                    # Calculate time to BA
                    if data.get("language_start_date") or data.get("ba_start_date"):
                        start_date = data.get("language_start_date") or data["ba_start_date"]
                        data["time_to_ba_days"] = (completed_milestone.milestone_date - start_date).days
                else:
                    data["ba_completion_status"] = "ACTIVE" if journey.journey_status == "ACTIVE" else "DROPPED"

            # MA program analysis
            ma_milestones = [m for m in milestones if m.program and m.program.program_type == "GRADUATE"]
            if ma_milestones:
                data["ma_start_date"] = ma_milestones[0].milestone_date
                data["ma_program"] = ma_milestones[0].program.name if ma_milestones[0].program else ""
                data["ma_terms"] = len({m.academic_term for m in ma_milestones if m.academic_term})

                # Determine completion status
                completed_milestone = next(
                    (m for m in ma_milestones if m.milestone_type == "PROGRAM_COMPLETION"), None
                )
                if completed_milestone:
                    data["ma_completion_status"] = "GRADUATED"
                    data["ma_completion_date"] = completed_milestone.milestone_date

                    # Calculate time to MA
                    if data.get("ba_completion_date"):
                        data["time_to_ma_days"] = (
                            completed_milestone.milestone_date - data["ba_completion_date"]
                        ).days
                else:
                    data["ma_completion_status"] = "ACTIVE" if journey.journey_status == "ACTIVE" else "DROPPED"

            # Set default values for missing fields
            default_values = {
                "language_start_date": None,
                "language_final_level": "",
                "language_terms": 0,
                "language_credits": 0,
                "language_completion_status": "",
                "language_completion_date": None,
                "ba_start_date": None,
                "ba_major": "",
                "ba_terms": 0,
                "ba_credits": 0,
                "ba_gpa": None,
                "ba_completion_date": None,
                "ba_completion_status": "",
                "ma_start_date": None,
                "ma_program": "",
                "ma_terms": 0,
                "ma_credits": 0,
                "ma_gpa": None,
                "ma_completion_date": None,
                "ma_completion_status": "",
                "time_to_ba_days": None,
                "time_to_ma_days": None,
            }

            for key, default_value in default_values.items():
                if key not in data:
                    data[key] = default_value

            return data

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Warning: Could not process journey for student {journey.student.student_id}: {e}")
            )
            return None
