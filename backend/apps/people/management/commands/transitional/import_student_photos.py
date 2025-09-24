"""Management command to import historical student photos.

This command imports legacy student photos from a directory, matching them
to students by ID in the filename, and creates StudentPhoto records with
proper versioning and metadata.
"""

import os
import re
from datetime import datetime
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from apps.common.management.base_migration import BaseMigrationCommand
from apps.people.models import StudentPhoto, StudentProfile
from apps.people.utils import PhotoProcessor


class Command(BaseMigrationCommand):
    """Import historical student photos from legacy system."""

    help = "Import student photos from a directory, matching by student ID in filename"

    def add_arguments(self, parser):
        """Add command arguments."""
        super().add_arguments(parser)
        parser.add_argument("photo_directory", type=str, help="Directory containing photos to import")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of photos to process per batch (default: 100)",
        )
        parser.add_argument(
            "--start-id",
            type=int,
            default=0,
            help="Start importing from this student ID (default: 0)",
        )
        parser.add_argument(
            "--end-id",
            type=int,
            default=999999,
            help="Stop importing at this student ID (default: 999999)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without actually creating records",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            default=True,
            help="Skip students who already have photos (default: True)",
        )

    def get_rejection_categories(self) -> list[str]:
        """Return list of possible rejection categories for this migration."""
        return [
            "student_not_found",
            "duplicate_photo",
            "invalid_image",
            "processing_error",
            "already_has_photo",
        ]

    def get_report_name(self) -> str:
        """Generate report filename."""
        return f"student_photo_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def execute_migration(self, *args, **options):
        """Main command handler."""
        photo_dir = Path(options["photo_directory"])

        if not photo_dir.exists() or not photo_dir.is_dir():
            self.stdout.write(self.style.ERROR(f"Directory not found: {photo_dir}"))
            return

        self.batch_size = options["batch_size"]
        self.start_id = options["start_id"]
        self.end_id = options["end_id"]
        self.dry_run = options["dry_run"]
        self.skip_existing = options["skip_existing"]

        self.stdout.write(f"Starting photo import from: {photo_dir}")
        self.stdout.write(f"ID range: {self.start_id} to {self.end_id}")
        self.stdout.write(f"Batch size: {self.batch_size}")
        self.stdout.write(f"Dry run: {self.dry_run}")

        # Get list of photo files
        photo_files = self._get_photo_files(photo_dir)
        self.stdout.write(f"Found {len(photo_files)} photo files to process")

        # Record input stats
        self.record_input_stats(
            total_files=len(photo_files),
            photo_directory=str(photo_dir),
            id_range=f"{self.start_id}-{self.end_id}",
            dry_run=self.dry_run,
        )

        # Process in batches
        processed = 0
        for i in range(0, len(photo_files), self.batch_size):
            batch = photo_files[i : i + self.batch_size]
            self._process_batch(batch, photo_dir)
            processed += len(batch)
            self.stdout.write(f"Processed {processed}/{len(photo_files)} photos")

    def _get_photo_files(self, photo_dir: Path) -> list[tuple[str, int]]:
        """Get list of photo files with extracted student IDs.

        Returns:
            List of (filename, student_id) tuples sorted by student ID
        """
        photo_files = []

        # Pattern to extract student ID from filename
        # Matches: 00583.jpg, 18000.jpg, 18001.JPG, etc.
        # Handles zero-padded IDs by converting to int
        id_pattern = re.compile(r"^(\d+)\.(jpg|jpeg|png)$", re.IGNORECASE)

        for filename in os.listdir(photo_dir):
            match = id_pattern.match(filename)
            if match:
                # Convert to int, which removes leading zeros
                student_id = int(match.group(1))
                if self.start_id <= student_id <= self.end_id:
                    photo_files.append((filename, student_id))

        # Log some examples to verify parsing
        if photo_files:
            self.stdout.write("Sample photo mappings:")
            for filename, sid in photo_files[:5]:
                self.stdout.write(f"  {filename} -> Student ID {sid}")

        # Sort by student ID
        photo_files.sort(key=lambda x: x[1])

        return photo_files

    def _process_batch(self, batch: list[tuple[str, int]], photo_dir: Path):
        """Process a batch of photos."""
        for filename, student_id in batch:
            try:
                self._import_photo(filename, student_id, photo_dir)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to import {filename} for student {student_id}: {e!s}"))
                self.record_rejection(
                    "processing_error",
                    str(student_id),
                    f"Failed to import {filename}",
                    error_details=str(e),
                )

    def _import_photo(self, filename: str, student_id: int, photo_dir: Path):
        """Import a single photo."""
        file_path = photo_dir / filename

        # Find the person by student ID
        try:
            student_profile = StudentProfile.objects.select_related("person").get(student_id=student_id)
            person = student_profile.person
        except StudentProfile.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"Student not found: {student_id}"))
            self.record_rejection(
                "student_not_found",
                str(student_id),
                f"No student profile found for ID {student_id}",
                raw_data={"filename": filename},
            )
            return

        # Check if student already has a photo
        if self.skip_existing and StudentPhoto.objects.filter(person=person).exists():
            self.stdout.write(f"Skipping student {student_id} - already has photo")
            self.record_rejection(
                "already_has_photo",
                str(student_id),
                f"Student {person.full_name} already has a photo",
                raw_data={"filename": filename},
            )
            return

        # Read and process the photo
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Calculate file hash to check for duplicates
            file_hash = PhotoProcessor.calculate_file_hash(file_content)

            # Check if this exact photo already exists
            if StudentPhoto.objects.filter(file_hash=file_hash).exists():
                self.stdout.write(f"Duplicate photo detected for student {student_id}")
                self.record_rejection(
                    "duplicate_photo",
                    str(student_id),
                    f"Photo with hash {file_hash} already exists",
                    raw_data={"filename": filename},
                )
                return

            if not self.dry_run:
                # Create file objects for Django
                photo_file = ContentFile(file_content, name=filename)

                # Process the photo (resize, thumbnail, etc.)
                processed_photo, thumbnail, _, metadata = PhotoProcessor.process_photo(
                    photo_file,
                    generate_thumbnail=True,
                )

                # Create StudentPhoto record
                with transaction.atomic():
                    student_photo = StudentPhoto.objects.create(
                        person=person,
                        photo_file=processed_photo,
                        thumbnail=thumbnail,
                        upload_source=StudentPhoto.UploadSource.LEGACY_IMPORT,
                        file_hash=file_hash,
                        file_size=metadata["file_size"],
                        width=metadata["width"],
                        height=metadata["height"],
                        original_filename=filename,
                        notes=f"Imported from legacy system on {timezone.now().date()}",
                    )

                    # Also update the Person.photo field for backward compatibility
                    if not person.photo:
                        person.photo = processed_photo
                        person.save(update_fields=["photo"])

                self.stdout.write(self.style.SUCCESS(f"Imported photo for student {student_id}: {person.full_name}"))
                self.record_success("photos_imported", 1)
                self.record_sample_data(
                    "imported_photos",
                    [
                        {
                            "filename": filename,
                            "student_id": student_id,
                            "person_name": person.full_name,
                            "file_size": metadata["file_size"],
                            "photo_id": student_photo.id,
                        },
                    ],
                )
            else:
                # Dry run
                self.stdout.write(f"[DRY RUN] Would import photo for student {student_id}: {person.full_name}")
                self.record_success("dry_run_imports", 1)

        except Image.UnidentifiedImageError:
            self.stdout.write(self.style.ERROR(f"Invalid image file: {filename}"))
            self.record_rejection(
                "invalid_image",
                str(student_id),
                "Cannot open image file",
                raw_data={"filename": filename},
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing photo {filename}: {e!s}"))
            self.record_rejection(
                "processing_error",
                str(student_id),
                f"Error processing photo: {e!s}",
                error_details=str(e),
                raw_data={"filename": filename},
            )
