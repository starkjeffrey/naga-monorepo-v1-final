"""Photo processing utilities for the people app.

This module provides utilities for processing student photos including:
- Image resizing and thumbnail generation
- EXIF data handling and rotation
- File hash calculation for deduplication
- Image validation and optimization
"""

import hashlib
import io

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import ExifTags, Image, ImageOps


class PhotoProcessor:
    """Handle photo processing operations for student photos."""

    # Standard dimensions
    PHOTO_SIZE = (320, 360)  # Standard ID photo size
    THUMBNAIL_SIZE = (80, 90)  # Thumbnail for lists
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    JPEG_QUALITY = 85  # JPEG compression quality

    @classmethod
    def process_photo(
        cls,
        uploaded_file: InMemoryUploadedFile,
        generate_thumbnail: bool = True,
    ) -> tuple[ContentFile, ContentFile | None, str, dict]:
        """Process an uploaded photo file.

        Args:
            uploaded_file: The uploaded file from Django
            generate_thumbnail: Whether to generate a thumbnail

        Returns:
            Tuple of (processed_photo, thumbnail, file_hash, metadata)
            where metadata contains width, height, file_size
        """
        # Read the uploaded file
        uploaded_file.seek(0)
        image_data = uploaded_file.read()
        uploaded_file.seek(0)

        # Calculate file hash for deduplication
        file_hash = hashlib.sha256(image_data).hexdigest()

        # Open image with Pillow
        image = Image.open(io.BytesIO(image_data))

        # Convert RGBA to RGB if necessary
        if image.mode in ("RGBA", "P"):
            # Create a white background
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Handle EXIF orientation
        image = cls._handle_exif_rotation(image)

        # Get original dimensions
        original_width, original_height = image.size

        # Resize to standard size
        processed_image = cls._resize_image(image, cls.PHOTO_SIZE)

        # Save processed image to bytes
        output = io.BytesIO()
        processed_image.save(output, format="JPEG", quality=cls.JPEG_QUALITY, optimize=True)
        output.seek(0)
        processed_content = ContentFile(output.read(), name=f"photo_{file_hash[:8]}.jpg")

        # Generate thumbnail if requested
        thumbnail_content = None
        if generate_thumbnail:
            thumbnail = cls._resize_image(image, cls.THUMBNAIL_SIZE)
            thumb_output = io.BytesIO()
            thumbnail.save(thumb_output, format="JPEG", quality=cls.JPEG_QUALITY, optimize=True)
            thumb_output.seek(0)
            thumbnail_content = ContentFile(thumb_output.read(), name=f"thumb_{file_hash[:8]}.jpg")

        # Prepare metadata
        metadata = {
            "width": cls.PHOTO_SIZE[0],
            "height": cls.PHOTO_SIZE[1],
            "original_width": original_width,
            "original_height": original_height,
            "file_size": len(processed_content),
        }

        return processed_content, thumbnail_content, file_hash, metadata

    @classmethod
    def _handle_exif_rotation(cls, image: Image.Image) -> Image.Image:
        """Handle EXIF orientation to ensure photos are upright."""
        try:
            # Get EXIF data
            exif = image._getexif()
            if exif:
                # Find orientation tag
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == "Orientation":
                        break

                orientation_value = exif.get(orientation)
                if orientation_value:
                    # Apply rotation based on EXIF orientation
                    rotations = {3: 180, 6: 270, 8: 90}
                    if orientation_value in rotations:
                        image = image.rotate(rotations[orientation_value], expand=True)
        except (AttributeError, KeyError, IndexError):
            # No EXIF data or orientation info
            pass

        return image

    @classmethod
    def _resize_image(cls, image: Image.Image, size: tuple[int, int]) -> Image.Image:
        """Resize image to fit within specified dimensions while maintaining aspect ratio.

        Uses ImageOps.fit for smart cropping to maintain the most important parts
        of the image (typically the center for portraits).
        """
        # Use LANCZOS resampling for best quality
        return ImageOps.fit(
            image,
            size,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),  # Center the crop
        )

    @classmethod
    def validate_image(cls, uploaded_file: InMemoryUploadedFile) -> tuple[bool, str]:
        """Validate an uploaded image file.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        if uploaded_file.size > cls.MAX_FILE_SIZE:
            return (
                False,
                f"File size exceeds {cls.MAX_FILE_SIZE // (1024 * 1024)}MB limit",
            )

        # Check file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg"]
        if uploaded_file.content_type not in allowed_types:
            return False, "Only JPEG and PNG images are allowed"

        # Try to open the image
        try:
            image = Image.open(uploaded_file)
            image.verify()  # Verify it's a valid image

            # Check minimum dimensions (at least 160x180 for reasonable quality)
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
            if image.width < 160 or image.height < 180:
                return (
                    False,
                    "Image dimensions too small. Minimum 160x180 pixels required",
                )

            uploaded_file.seek(0)  # Reset for further processing
            return True, ""

        except Exception as e:
            return False, f"Invalid image file: {e!s}"

    @classmethod
    def calculate_file_hash(cls, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()


class PhotoReminder:
    """Handle photo reminder logic and scheduling."""

    @classmethod
    def get_students_needing_reminders(cls):
        """Get queryset of students who need photo update reminders.

        Returns students with photos that are:
        - 5+ months old for regular students
        - 11+ months old for monks
        - Haven't been reminded in the last 7 days
        - Don't have skip_reminder flag set
        """
        from datetime import timedelta

        from django.utils import timezone

        from apps.people.models import StudentPhoto

        # Calculate cutoff dates
        five_months_ago = timezone.now() - timedelta(days=150)  # ~5 months
        eleven_months_ago = timezone.now() - timedelta(days=330)  # ~11 months
        seven_days_ago = timezone.now() - timedelta(days=7)

        # Get current photos needing reminders
        photos = StudentPhoto.objects.filter(is_current=True, skip_reminder=False).select_related(
            "person__student_profile",
        )

        # Filter by age and reminder status
        regular_students = photos.filter(
            person__student_profile__is_monk=False,
            upload_timestamp__lte=five_months_ago,
        ).exclude(reminder_sent_at__gte=seven_days_ago)

        monk_students = photos.filter(
            person__student_profile__is_monk=True,
            upload_timestamp__lte=eleven_months_ago,
        ).exclude(reminder_sent_at__gte=seven_days_ago)

        # Combine querysets
        return regular_students | monk_students

    @classmethod
    def get_overdue_students(cls):
        """Get students with photos that are overdue for update.

        Returns students with photos that are:
        - 6+ months old for regular students
        - 12+ months old for monks
        """
        from datetime import timedelta

        from django.utils import timezone

        from apps.people.models import StudentPhoto

        six_months_ago = timezone.now() - timedelta(days=180)
        twelve_months_ago = timezone.now() - timedelta(days=365)

        photos = StudentPhoto.objects.filter(is_current=True, skip_reminder=False).select_related(
            "person__student_profile",
        )

        regular_overdue = photos.filter(person__student_profile__is_monk=False, upload_timestamp__lte=six_months_ago)

        monk_overdue = photos.filter(
            person__student_profile__is_monk=True,
            upload_timestamp__lte=twelve_months_ago,
        )

        return regular_overdue | monk_overdue
