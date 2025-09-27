"""Legacy Class Headers Migration Script

To run a migration of a very large dataset (e.g., 250,000 records), you can use:

1. Batch processing to avoid memory issues
2. Progress tracking for monitoring
3. Error handling and recovery mechanisms
"""

import csv
import gc
import os
import re
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.models import Course, Room, TeacherProfile, Term

# Assuming TimeOfDay enum exists here
from apps.scheduling.models import ClassHeader, ClassPart, TimeOfDay

# Simple mapping for program codes.

PROGRAM_MAPPING = {
    "87": "BA",
    "147": "MA",
    "688": "EHSS",
    "582": "IEAP",
    "632": "GESL",
    "1187": "Weekend Express",
}


# Mapping time_slot abbreviations to TimeOfDay enum members.

TIME_MAP = {
    "E": TimeOfDay.EVE,
    "M": TimeOfDay.MORN,
    "W": TimeOfDay.WKEND,
    "A": TimeOfDay.AFT,
    # Add more mappings as needed, ensure they match TimeOfDay enum members
}


def parse_class_header(
    header: str,
) -> tuple[str | None, str | None, str | None]:
    """Parse the class_header field for language courses.

    Expected pattern: a base code optionally ending with a letter (A-E)

    and an optional time-of-day marker following a slash.



    For example:

      "EHSS-9B" => base: "EHSS-9", section: "B", timeofday: None

      "IEAP-1/M" => base: "IEAP-1", section: None, timeofday: "M"
    """
    # Regex to split header into base, optional section (A-E), optional /TIME

    m = re.match(r"^(?P<base>[\w\-]+?)(?P<section>[A-E])?(?:/(?P<timeofday>[A-Z]))?$", header)

    if m:
        return m.group("base"), m.group("section"), m.group("timeofday")

    return header, None, None


class Command(BaseCommand):
    help = "Import ClassHeader and ClassPart records from a legacy CSV file."

    # --- Argument Handling ---

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            default="data/migration/all_classheaders.csv",  # Adjusted default path
            help="Path to the CSV file containing class header data.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the import process without saving changes to the database.",
        )

        parser.add_argument(
            "--skip",
            nargs="+",
            type=str,
            default=[],
            help="List of legacy class IDs to skip during import.",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of rows to process.",
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing ClassHeader records if found based on legacy_classid.",
        )

        parser.add_argument(
            "--default-teacher-email",
            type=str,
            default=None,  # Require explicit default if needed
            help="Email of the default teacher to use if the instructor is not found.",
        )

        parser.add_argument(
            "--default-room-name",
            type=str,
            default=None,  # Require explicit default if needed
            help="Name of the default room to use if needed.",
        )

        # New arguments for batch processing

        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of records to process in a single batch before committing to the database.",
        )

        parser.add_argument(
            "--progress-every",
            type=int,
            default=1000,
            help="Show progress message after processing this many records.",
        )

        parser.add_argument(
            "--start-from",
            type=int,
            default=0,
            help="Start processing from this row number (0-based, not including header row).",
        )

    # --- Main Handler ---

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]

        self.skip_ids = set(options["skip"])

        self.limit = options["limit"]

        self.overwrite = options["overwrite"]

        csv_path = options["csv"]

        self.default_teacher = self._get_default_teacher(options["default_teacher_email"])

        self.default_room = self._get_default_room(options["default_room_name"])

        # Batch processing parameters

        self.batch_size = options["batch_size"]

        self.progress_every = options["progress_every"]

        self.start_from = options["start_from"]

        # Track missing course codes for reporting

        self.missing_courses = {}

        if not Path(csv_path).exists():
            cmd_error = f"CSV file not found: {csv_path}"

            raise CommandError(cmd_error)

        self.stdout.write(f"Starting import from {csv_path}...")

        self.stdout.write(f"Processing in batches of {self.batch_size}, starting from row {self.start_from}")

        if self.dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ---"))

        processed_count = 0

        skipped_count = 0

        error_count = 0

        created_count = 0

        updated_count = 0

        batch_count = 0

        current_batch = []

        try:
            # First, count total rows to show progress percentage

            with Path(csv_path).open(encoding="utf-8") as csvfile:
                total_rows = sum(1 for _ in csv.reader(csvfile)) - 1  # Subtract header row

            if self.limit is not None:
                total_to_process = min(total_rows - self.start_from, self.limit)

            else:
                total_to_process = total_rows - self.start_from

            self.stdout.write(f"Total rows to process: {total_to_process}")

            # Now process the file

            with Path(csv_path).open(encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                # Skip rows if needed

                for _ in range(self.start_from):
                    next(reader, None)

                for i, row in enumerate(reader, start=self.start_from):
                    # Display progress periodically

                    if processed_count > 0 and processed_count % self.progress_every == 0:
                        progress_pct = (processed_count / total_to_process) * 100 if total_to_process > 0 else 0

                        self.stdout.write(
                            f"Progress: {processed_count}/{total_to_process} rows ({progress_pct:.1f}%) - "
                            f"Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}, Errors: {error_count}",
                        )

                    # Check if we've reached the limit

                    if self.limit is not None and processed_count >= self.limit:
                        self.stdout.write(f"Reached processing limit of {self.limit}.")

                        break

                    legacy_classid = row.get("classid")

                    if not legacy_classid:
                        self.stderr.write(f"Skipping row {i + 1}: Missing 'classid'.")

                        skipped_count += 1

                        continue

                    if legacy_classid in self.skip_ids:
                        self.stdout.write(f"Skipping row {i + 1}: classid {legacy_classid} is in skip list.")

                        skipped_count += 1

                        continue

                    try:
                        if self.dry_run:
                            # In dry-run mode, process each row individually with rollback

                            with transaction.atomic():
                                status, message = self._process_row(row, i + 1)

                                if status == "created":
                                    created_count += 1

                                    self.stdout.write(self.style.SUCCESS(message))

                                elif status == "updated":
                                    updated_count += 1

                                    self.stdout.write(self.style.SUCCESS(message))

                                elif status == "skipped":
                                    skipped_count += 1

                                    self.stdout.write(self.style.WARNING(message))

                                elif status == "dryrun":
                                    self.stdout.write(message)  # No style for dry run info

                                transaction.set_rollback(True)

                        else:
                            # For normal processing, add to batch

                            current_batch.append((row, i + 1))

                            batch_count += 1

                            # Process the batch if it reaches the batch size

                            if batch_count >= self.batch_size:
                                batch_results = self._process_batch(current_batch)

                                created_count += batch_results["created"]

                                updated_count += batch_results["updated"]

                                skipped_count += batch_results["skipped"]

                                error_count += batch_results["errors"]

                                # Reset the batch

                                current_batch = []

                                batch_count = 0

                                # Force garbage collection to reduce memory usage

                                gc.collect()

                        processed_count += 1

                    except Exception as e:
                        self.stderr.write(
                            self.style.ERROR(f"Error processing row {i + 1} (classid {legacy_classid}): {e}"),
                        )

                        error_count += 1

                # Process any remaining batch items

                if not self.dry_run and current_batch:
                    batch_results = self._process_batch(current_batch)

                    created_count += batch_results["created"]

                    updated_count += batch_results["updated"]

                    skipped_count += batch_results["skipped"]

                    error_count += batch_results["errors"]

        except FileNotFoundError:
            cmd_error = f"CSV file not found: {csv_path}"

            raise CommandError(cmd_error) from None

        except Exception as e:
            cmd_error = f"An unexpected error occurred: {e}"

            raise CommandError(cmd_error) from e

        self.stdout.write("\n--- Import Summary ---")

        self.stdout.write(f"Total rows processed: {processed_count}")

        self.stdout.write(f"Rows created: {created_count}")

        self.stdout.write(f"Rows updated: {updated_count}")

        self.stdout.write(f"Rows skipped: {skipped_count}")

        self.stdout.write(f"Rows with errors: {error_count}")

        # Write missing courses to CSV

        if self.missing_courses:
            self._write_missing_courses_report(csv_path)

            self.stdout.write(f"Found {len(self.missing_courses)} missing course codes. See report for details.")

        if self.dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN COMPLETE: No changes were saved. ---"))

        else:
            self.stdout.write(self.style.SUCCESS("--- Import complete. ---"))

    def _write_missing_courses_report(self, import_csv_path):
        """Write the missing courses to a CSV file for later reference."""
        import csv
        from datetime import datetime
        from pathlib import Path

        # Generate output filename based on input CSV name

        base_path = Path(import_csv_path).parent

        base_name = Path(import_csv_path).name.split(".")[0]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        output_path = os.path.join(base_path, f"{base_name}_missing_courses_{timestamp}.csv")

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow(
                [
                    "Course Code",
                    "Row Count",
                    "Sample Row #",
                    "Sample Legacy ID",
                    "Sample Class Header",
                ],
            )

            for code, instances in sorted(self.missing_courses.items(), key=lambda x: len(x[1]), reverse=True):
                row_count = len(instances)

                sample_row_num, sample_legacy_id, sample_header = instances[0]

                writer.writerow([code, row_count, sample_row_num, sample_legacy_id, sample_header])

        self.stdout.write(self.style.SUCCESS(f"Missing courses report written to: {output_path}"))

    def _process_batch(self, batch):
        """Process a batch of rows in a single transaction."""
        results = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

        with transaction.atomic():
            for row, row_num in batch:
                try:
                    status, message = self._process_row(row, row_num)

                    if status == "created":
                        results["created"] += 1

                        self.stdout.write(self.style.SUCCESS(message))

                    elif status == "updated":
                        results["updated"] += 1

                        self.stdout.write(self.style.SUCCESS(message))

                    elif status == "skipped":
                        results["skipped"] += 1

                        self.stdout.write(self.style.WARNING(message))

                except Exception as e:
                    legacy_classid = row.get("classid", "unknown")

                    self.stderr.write(
                        self.style.ERROR(f"Error in batch processing row {row_num} (classid {legacy_classid}): {e}"),
                    )

                    results["errors"] += 1

        return results

    # --- Helper Methods ---

    def _get_default_teacher(self, email: str | None) -> TeacherProfile | None:
        """Gets a default teacher profile (ignores email for now)."""
        # Simplified to just get the first active teacher

        try:
            teacher = TeacherProfile.objects.filter(role__is_active=True).first()

            if teacher:
                self.stdout.write(f"Using default teacher: {teacher}")

                return teacher

            self.stderr.write(self.style.ERROR("No active teachers found in the system."))

            return None

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error finding default teacher: {e}"))

            return None

    def _get_default_room(self, name: str | None) -> Room | None:
        """Gets a default room (ignores name for now)."""
        # Simplified to just get the first room

        try:
            room = Room.objects.first()

            if room:
                self.stdout.write(f"Using default room: {room}")

                return room

            self.stderr.write(self.style.ERROR("No rooms found in the system."))

            return None

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error finding default room: {e}"))

            return None

    def _process_row(self, row: dict, row_num: int) -> tuple[str, str]:
        """Processes a single row from the CSV file."""
        # --- 1. Extract and Validate Data ---

        legacy_classid = row.get("classid")

        course_term = row.get("course_term")

        program_code = row.get("program")

        time_slot = row.get("time_slot")

        class_header_field = row.get("class_header", "")

        course_code_csv = row.get("course_code", "")

        # instructor_email = row.get("instructor") # Ignoring instructor email from CSV as requested

        csv_section = row.get("section")  # May be 'NULL' or a valid value

        # Basic validation

        if not all([legacy_classid, course_term, program_code, time_slot]):
            return (
                "skipped",
                f"Skipping row {row_num}: Missing required fields (classid, course_term, program, time_slot).",
            )

        # Find the corresponding term in the database

        try:
            term_obj = Term.objects.get(name=course_term)

            self.stdout.write(f"Found term: {term_obj}")

        except Term.DoesNotExist:
            return (
                "skipped",
                f"Skipping row {row_num}: Term with name '{course_term}' not found in database.",
            )

        except Term.MultipleObjectsReturned:
            self.stderr.write(
                self.style.ERROR(f"Multiple terms found with name '{course_term}'. Using the first one."),
            )

            term_obj = Term.objects.filter(name=course_term).first()

        # --- 2. Determine Course Type and Program ---

        is_ba_or_ma = program_code in ["87", "147"]

        program_display = PROGRAM_MAPPING.get(program_code, "OTHER")  # Not used directly yet, but good for context

        # --- 3. Determine TimeOfDay ---

        time_of_day_enum = TIME_MAP.get(time_slot)

        if not time_of_day_enum:
            # Try to find a match ignoring case or handle unknown values

            found = False

            for key, value in TIME_MAP.items():
                if key.upper() == time_slot.upper():
                    time_of_day_enum = value

                    found = True

                    break

            if not found:
                return (
                    "skipped",
                    f"Skipping row {row_num} (classid {legacy_classid}): Unknown time_slot '{time_slot}'. Add it to TIME_MAP.",
                )

        # --- 4. Look up Related Objects ---

        # Determine and validate appropriate course code based on program type

        course_code_to_use = None

        course_obj = None

        if is_ba_or_ma:
            # For BA or MA programs, use the course_code from CSV directly

            course_code_to_use = course_code_csv

        else:
            # For language programs, extract the base code from class_header_field

            base_code, _, _ = parse_class_header(class_header_field)

            # Apply substitutions for special course codes

            if base_code == "BEGINNER":
                base_code = "IEAP-BEG"

                self.stdout.write("Substituting BEGINNER with IEAP-BEG")

            elif base_code == "IEAP-BEGINNER":
                base_code = "IEAP-BEG"

                self.stdout.write("Substituting IEAP-BEGINNER with IEAP-BEG")

            elif base_code == "PRE-BEGINNER":
                base_code = "IEAP-PRE"

                self.stdout.write("Substituting PRE-BEGINNER with IEAP-PRE")

            elif base_code == "PRE-B1":
                base_code = "PT-BEG-1"

                self.stdout.write("Substituting PRE-B1 with PT-BEG-1")

            elif base_code == "PRE-B2" or base_code.startswith("PRE-B2/"):
                base_code = "PT-BEG-2"

                self.stdout.write(f"Substituting {base_code} with PT-BEG-2")

            elif base_code == "FREE/COMPUTER":
                base_code = "COMP-LAB"  # Assuming this is a good substitute

                self.stdout.write("Substituting FREE/COMPUTER with COMP-LAB")

            elif base_code.startswith("XPRESS-LEVEL-"):
                level = base_code[-1]  # Extract the last character (level number)

                base_code = f"XPRESS-{level}"

                self.stdout.write(f"Substituting {base_code} with XPRESS-{level}")

            elif base_code == "XPRESS-BEGINNER":
                base_code = "XPRESS-BEG"

                self.stdout.write("Substituting XPRESS-BEGINNER with XPRESS-BEG")

            # Map IEAP level codes (M-1, E-1, A-1, etc.)

            elif base_code in ["M-1", "M1", "E-1", "E1-", "A-1"]:
                base_code = "IEAP-1"

                self.stdout.write(f"Substituting {base_code} with IEAP-1")

            elif base_code in ["M-2", "M2", "E-2", "E2-", "A-2"]:
                base_code = "IEAP-2"

                self.stdout.write(f"Substituting {base_code} with IEAP-2")

            elif base_code in ["M-3", "M3", "E-3", "E3-", "A-3"]:
                base_code = "IEAP-3"

                self.stdout.write(f"Substituting {base_code} with IEAP-3")

            elif base_code in ["M-4", "M4", "E-4", "E4-", "A-4"]:
                base_code = "IEAP-4"

                self.stdout.write(f"Substituting {base_code} with IEAP-4")

            # Map beginner variants

            elif base_code in ["M/BEGINNER", "E/BEGINNER", "A/BEGINNER"]:
                base_code = "IEAP-BEG"

                self.stdout.write(f"Substituting {base_code} with IEAP-BEG")

            elif base_code == "BEGINNER-1M":
                base_code = "BEGINNER-1"

                self.stdout.write("Substituting BEGINNER-1M with BEGINNER-1")

            course_code_to_use = base_code

        # Validate that the course code exists in the database

        if course_code_to_use:
            if Course.objects.filter(code=course_code_to_use).exists():
                try:
                    course_obj = Course.objects.filter(code=course_code_to_use).first()

                    self.stdout.write(f"Found course: {course_obj}")

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error looking up course with code {course_code_to_use}: {e}"))

                    return (
                        "skipped",
                        f"Skipping row {row_num}: Error looking up course with code {course_code_to_use}: {e}",
                    )

            else:
                self.stdout.write(self.style.WARNING(f"No course found with code {course_code_to_use}"))

                # Save missing course info

                if course_code_to_use not in self.missing_courses:
                    self.missing_courses[course_code_to_use] = []

                self.missing_courses[course_code_to_use].append((row_num, legacy_classid, class_header_field))

                return (
                    "skipped",
                    f"Skipping row {row_num}: Course with code '{course_code_to_use}' does not exist in Core.course.",
                )

        # Term lookup is already done above, no need to override term_obj here

        teacher = None  # For now, allow None for teacher

        room = self._get_room()  # Using default room for now

        # --- 5. Determine Section ID for Language Courses ---

        extracted_section = None

        header_section_id = None  # Initialize

        # We've already parsed the class_header above for language courses

        if not is_ba_or_ma:
            # We already have base_code from above, just need to extract the section if we didn't already

            if "base_code" not in locals() or base_code is None:
                base_code, extracted_section, _tod_from_header = parse_class_header(class_header_field)

            else:
                # Re-extract just to get the section part if we didn't capture it earlier

                _, extracted_section, _tod_from_header = parse_class_header(class_header_field)

            # Determine section_id for ClassHeader: Use parsed section or default to 'A'

            header_section_id = extracted_section if extracted_section else "A"

            # Note: _tod_from_header is parsed but not used, time_slot from CSV takes precedence

        # Determine final section identifier

        final_section = csv_section if csv_section and csv_section.upper() != "NULL" else extracted_section

        # --- 6. Prepare ClassHeader Data ---

        header_data = {
            "course": course_obj,
            "term": term_obj,  # Now this will be correctly set from course_term
            "time_of_day": time_of_day_enum,
            "section_id": (
                course_code_csv if is_ba_or_ma else header_section_id
            ),  # Use determined section_id for language courses
            "class_type": "STANDARD",  # Default
            "max_enrollment": 20,  # Default
            "legacy_classid": legacy_classid,
            "is_paired": False,  # Default
            # Add other fields as necessary
        }

        # --- 7. Create or Update ClassHeader ---

        header, created, updated = self._create_or_update_class_header(legacy_classid, header_data)

        if not header:  # Skipped due to overwrite=False or error
            return (
                "skipped",
                f"Skipping row {row_num} (classid {legacy_classid}): Header already exists and overwrite is False.",
            )

        status_prefix = "Created" if created else "Updated"

        dry_run_prefix = "[DRY RUN] Would have" if self.dry_run else ""

        header_message = f"{dry_run_prefix} {status_prefix} ClassHeader for legacy_classid {legacy_classid} (ID: {header.id if header else 'N/A'})"

        # --- 8. Create ClassPart (for Language Courses) ---

        part_message = ""

        if not is_ba_or_ma:
            part_data = {
                "class_header": header,
                "class_part_type": "LECTURE",  # Default
                "class_part_code": course_code_to_use,  # Use the validated course code
                "name": base_code or class_header_field,  # Use parsed base or full header
                "room": room,
                "days": "MWF",  # Placeholder
                "start_time": timezone.now().replace(hour=9, minute=0).time(),  # Placeholder
                "end_time": (timezone.now() + timedelta(hours=1)).time(),  # Placeholder
                "grade_weight": 1.0,  # Default
                # Add other fields as necessary
            }

            # Only add teacher if we have one

            if teacher:
                part_data["teacher"] = teacher

            part = self._create_class_part(part_data)

            if part:
                part_message = f" and {dry_run_prefix} created ClassPart (ID: {part.id if part else 'N/A'})"

        final_status = "created" if created else "updated"

        if self.dry_run:
            final_status = "dryrun"

        return final_status, f"Row {row_num}: {header_message}{part_message}."

    def _get_room(self) -> Room | None:
        """Gets the room (currently just returns the default)."""
        # Placeholder: Implement actual room lookup if needed based on CSV data

        # For now, always use the default room if available

        if not self.default_room:
            self.stdout.write(self.style.WARNING("No default room available. ClassPart room will be None."))

        return self.default_room

    def _create_or_update_class_header(self, legacy_classid: str, data: dict) -> tuple[ClassHeader | None, bool, bool]:
        """Creates or updates a ClassHeader based on legacy_classid."""
        try:
            header = ClassHeader.objects.get(legacy_classid=legacy_classid)

            if not self.overwrite:
                return None, False, False  # Skip if exists and overwrite is False

            # Update existing header

            if not self.dry_run:
                for key, value in data.items():
                    setattr(header, key, value)

                header.save()

            return header, False, True  # Existing, updated

        except ClassHeader.DoesNotExist:
            # Create new header

            if not self.dry_run:
                header = ClassHeader.objects.create(**data)

            else:
                # Simulate creation for dry run message (no actual ID)

                header = ClassHeader(**data)  # Unsaved instance

            return header, True, False  # New, created

    def _create_class_part(self, data: dict) -> ClassPart | None:
        """Creates a ClassPart."""
        # Potentially check for existing parts if needed, though less common for this script

        if not self.dry_run:
            part = ClassPart.objects.create(**data)

        else:
            # Simulate creation for dry run message

            part = ClassPart(**data)  # Unsaved instance

        return part
