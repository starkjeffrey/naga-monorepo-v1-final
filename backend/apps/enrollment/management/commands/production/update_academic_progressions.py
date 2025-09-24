"""Update AcademicProgression records based on ProgramPeriod data."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.enrollment.models_progression import AcademicProgression, ProgramPeriod
from apps.people.models import StudentProfile


class Command(BaseCommand):
    """Update academic progression records from program periods."""

    help = "Update AcademicProgression records based on ProgramPeriod data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--student-id",
            type=str,
            help="Process specific student ID",
        )

    def handle(self, *args, **options):
        student_id = options.get("student_id")

        if student_id:
            students = StudentProfile.objects.filter(student_id=student_id)
        else:
            students = StudentProfile.objects.all()

        self.stdout.write(f"Updating {students.count()} students...")

        for student in students:
            with transaction.atomic():
                self.update_student_progression(student)

        self.stdout.write(self.style.SUCCESS("Successfully updated progressions"))

    def update_student_progression(self, student: StudentProfile):
        """Update progression for a single student."""
        # Get or create progression record
        progression, created = AcademicProgression.objects.get_or_create(
            student=student,
            defaults={
                "student_name": student.person.full_name,
                "student_id_number": student.student_id,
            },
        )

        # Get program periods
        try:
            journey = student.academic_journey
            periods = ProgramPeriod.objects.filter(journey=journey).order_by("sequence_number")
        except Exception:
            return

        # Update from program periods
        for period in periods:
            if period.to_program_type == "BA":
                progression.ba_start_date = period.transition_date
                progression.ba_credits = period.completed_credits
                progression.ba_gpa = period.gpa
                progression.ba_terms = period.term_count

                if period.completion_status == "GRADUATED":
                    progression.ba_completion_status = "completed"
                    progression.ba_completion_date = period.transition_date + timedelta(days=int(period.duration_days))
                    progression.current_status = "BA_COMPLETED"
                elif period.completion_status == "ACTIVE":
                    progression.current_status = "ACTIVE_BA"
                else:
                    progression.ba_completion_status = "incomplete"

            elif period.to_program_type in ["IEAP", "GESL", "EHSS"]:
                if not progression.language_start_date or period.transition_date < progression.language_start_date:
                    progression.language_start_date = period.transition_date

                progression.language_terms = (progression.language_terms or 0) + period.term_count
                progression.language_final_level = period.language_level

                if period.completion_status == "COMPLETED":
                    progression.language_completion_status = "completed"
                    progression.language_end_date = period.transition_date + timedelta(days=int(period.duration_days))

        # Update total terms
        progression.total_terms = sum(p.term_count for p in periods)

        # Save
        progression.save()

        self.stdout.write(f"Updated progression for {student.student_id}")
