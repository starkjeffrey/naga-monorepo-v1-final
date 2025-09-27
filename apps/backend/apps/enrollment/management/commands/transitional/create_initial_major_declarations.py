"""Management command to create initial MajorDeclaration records from ProgramEnrollment data.

This command analyzes existing ProgramEnrollment records and creates corresponding
MajorDeclaration records for students who don't have explicit declarations yet.
It follows the BaseMigrationCommand pattern for comprehensive audit reporting.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.enrollment.models import MajorDeclaration, ProgramEnrollment


class Command(BaseMigrationCommand):
    help = "Create initial MajorDeclaration records from existing ProgramEnrollment data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without making changes",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing declarations (use with caution)",
        )
        parser.add_argument(
            "--effective-date-offset",
            type=int,
            default=0,
            help="Days to offset effective date from enrollment start date",
        )

    def get_rejection_categories(self):
        return [
            "no_program_enrollment",
            "existing_declaration",
            "invalid_major",
            "missing_student",
            "validation_error",
            "duplicate_effective_date",
        ]

    def execute_migration(self, *args, **options):
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]
        date_offset = options["effective_date_offset"]

        self.stdout.write(self.style.SUCCESS("Creating initial MajorDeclaration records from ProgramEnrollment data"))

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Get all program enrollments
        program_enrollments = ProgramEnrollment.objects.select_related("student", "program").order_by(
            "student",
            "-start_date",
        )

        self.record_input_stats(
            total_records=program_enrollments.count(),
            source_description="ProgramEnrollment records",
        )

        # Track students we've processed to avoid duplicates
        processed_students = set()
        created_count = 0
        skipped_count = 0

        for enrollment in program_enrollments:
            try:
                # Skip if we've already processed this student
                if enrollment.student.id in processed_students:
                    continue

                # Check if student already has a declaration
                existing_declaration = MajorDeclaration.objects.filter(student=enrollment.student).first()

                if existing_declaration and not overwrite:
                    self.record_rejection(
                        "existing_declaration",
                        record_id=enrollment.id,
                        reason=(
                            f"Student {enrollment.student.student_id} already has declaration "
                            f"for {existing_declaration.major.name}"
                        ),
                    )
                    skipped_count += 1
                    continue

                # Validate enrollment data
                if not enrollment.student:
                    self.record_rejection(
                        "missing_student",
                        record_id=enrollment.id,
                        reason="Enrollment has no associated student",
                    )
                    continue

                if not enrollment.program:
                    self.record_rejection(
                        "invalid_major",
                        record_id=enrollment.id,
                        reason="Enrollment has no associated program/major",
                    )
                    continue

                # Calculate effective date
                effective_date = enrollment.start_date
                if date_offset:
                    effective_date = effective_date + timedelta(days=date_offset)

                # Check for duplicate effective dates if overwriting
                if overwrite:
                    duplicate = MajorDeclaration.objects.filter(
                        student=enrollment.student,
                        effective_date=effective_date,
                        is_active=True,
                    ).first()

                    if duplicate:
                        self.record_rejection(
                            "duplicate_effective_date",
                            record_id=enrollment.id,
                            reason=f"Student already has active declaration for {effective_date}",
                        )
                        continue

                if not dry_run:
                    with transaction.atomic():
                        # Deactivate existing declaration if overwriting
                        if existing_declaration and overwrite:
                            existing_declaration.is_active = False
                            existing_declaration.save(update_fields=["is_active"])

                        # Create new declaration
                        declaration = MajorDeclaration.objects.create(
                            student=enrollment.student,
                            major=enrollment.program,
                            effective_date=effective_date,
                            declared_date=enrollment.created_at or timezone.now(),
                            is_self_declared=False,  # System generated
                            declared_by=None,  # System user would be set in service
                            notes=f"Auto-generated from ProgramEnrollment ID: {enrollment.id}",
                            requires_approval=False,  # System migration doesn't require approval
                        )

                        created_count += 1
                        self.record_success("declarations_created", 1)

                        self.stdout.write(f"Created declaration: {declaration}")
                else:
                    # Dry run - just log what would be created
                    self.stdout.write(
                        f"Would create: {enrollment.student.student_id} → "
                        f"{enrollment.program.name} (effective {effective_date})",
                    )
                    created_count += 1

                # Mark student as processed
                processed_students.add(enrollment.student.id)

            except Exception as e:
                self.record_rejection(
                    "validation_error",
                    record_id=enrollment.id,
                    reason=f"Error creating declaration: {e!s}",
                )
                continue

        # Record final statistics
        self.record_success("total_processed", len(processed_students))
        self.record_success("declarations_created", created_count)
        self.record_success("records_skipped", skipped_count)

        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN: Would create {created_count} declarations, skip {skipped_count} existing",
                ),
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully created {created_count} major declarations"))

            if skipped_count:
                self.stdout.write(self.style.WARNING(f"Skipped {skipped_count} students with existing declarations"))

        # Suggest next steps
        self.stdout.write(
            self.style.SUCCESS(
                "\nNext steps:"
                "\n1. Review created declarations in admin"
                "\n2. Run consistency checks: python manage.py check_major_consistency"
                "\n3. Train staff on declaration approval workflow",
            ),
        )
