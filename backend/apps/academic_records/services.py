"""Academic Records services for transcript generation and document management.

This module provides services for:
- Official transcript PDF generation using reportlab
- Academic history compilation and formatting
- Document verification and security features
- Degree audit reports and graduation tracking
- Document quota management for administrative fees

Key architectural decisions:
- Clean dependencies: academic_records → grading + enrollment + curriculum + people
- Professional PDF formatting for official documents
- Comprehensive academic data aggregation
- Security features for document verification
- Integration with administrative fee quotas
"""

import hashlib
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.academic.models import TransferCredit
from apps.enrollment.models import ClassHeaderEnrollment, StudentCycleStatus
from apps.grading.models import GPARecord
from apps.people.models import StudentProfile

from .constants import (
    COURSE_TITLE_TRUNCATE_LENGTH,
    CRYPTOGRAPHIC_HASH_ALGORITHM,
    PDF_CONTENT_WIDTH_REDUCTION,
    PDF_MARGIN_INCHES,
)
from .models import (
    DocumentQuota,
    DocumentQuotaUsage,
    DocumentRequest,
    DocumentTypeConfig,
    GeneratedDocument,
)


class TranscriptGenerationError(Exception):
    """Custom exception for transcript generation errors."""


class DocumentGenerationService:
    """Service for generating academic documents using the flexible document system.

    Provides comprehensive document generation with professional formatting,
    security features, and integration with all academic systems.
    Updated to use the new flexible DocumentRequest/GeneratedDocument models.
    """

    # PDF formatting constants
    PAGE_WIDTH, PAGE_HEIGHT = letter
    MARGIN = PDF_MARGIN_INCHES * inch
    CONTENT_WIDTH = PAGE_WIDTH - (PDF_CONTENT_WIDTH_REDUCTION * MARGIN)

    @classmethod
    def generate_document(
        cls,
        document_request: DocumentRequest,
        generated_by=None,
    ) -> GeneratedDocument:
        """Generate a document based on a document request.

        Args:
            document_request: DocumentRequest to generate document for
            generated_by: User generating the document

        Returns:
            GeneratedDocument with generated content

        Raises:
            TranscriptGenerationError: If document generation fails
        """
        try:
            # Type annotations to help mypy understand the concrete types
            student: StudentProfile = cast("StudentProfile", document_request.student)
            document_type: DocumentTypeConfig = cast("DocumentTypeConfig", document_request.document_type)

            # Set as_of_date from request or current date
            as_of_date = timezone.now()

            # Determine if transfer credits should be included based on document type
            include_transfer_credits = document_type.requires_grade_data

            # Compile academic data
            academic_data = cls._compile_academic_data(
                student,
                include_transfer_credits,
                as_of_date,
            )

            # Generate PDF content based on document type
            if document_type.category in ["academic_transcript", "grade_report"]:
                pdf_content = cls._generate_pdf_transcript(student, academic_data, document_type)
            elif document_type.category == "enrollment_verification":
                pdf_content = cls._generate_pdf_enrollment_verification(student, academic_data, document_type)
            else:
                # Generic document generation
                pdf_content = cls._generate_pdf_generic_document(student, academic_data, document_type)

            # Calculate content hash for verification using configured algorithm
            hash_algo = getattr(hashlib, CRYPTOGRAPHIC_HASH_ALGORITHM)
            content_hash = hash_algo(pdf_content).hexdigest()

            # Create generated document record using new flexible model
            document = GeneratedDocument.objects.create(
                document_request=document_request,
                student=student,
                file_size=len(pdf_content),
                content_hash=content_hash,
                generated_by=generated_by,
            )

            # Save PDF file to storage
            file_path = cls._save_pdf_to_storage(
                pdf_content,
                student,
                document.document_id,
            )
            document.file_path = file_path
            document.save(update_fields=["file_path"])

            return document

        except Exception as e:
            msg = f"Failed to generate document: {e!s}"
            raise TranscriptGenerationError(msg) from e

    @classmethod
    def _compile_academic_data(
        cls,
        student: StudentProfile,
        include_transfer_credits: bool | None = True,
        as_of_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Compile comprehensive academic data for transcript generation.

        Args:
            student: Student to compile data for
            include_transfer_credits: Whether to include transfer credits
            as_of_date: Compile data as of this date

        Returns:
            Dictionary with comprehensive academic information
        """
        # Filter enrollments by as_of_date if provided
        enrollment_filter = Q(student=student)
        if as_of_date:
            enrollment_filter &= Q(enrollment_date__lte=as_of_date)

        # Get all enrollments
        enrollments = (
            ClassHeaderEnrollment.objects.filter(enrollment_filter)
            .select_related("class_header__course", "class_header__term")
            .order_by("class_header__term__start_date", "class_header__course__code")
        )

        # Group enrollments by term
        enrollments_by_term: dict[Any, list] = {}
        for enrollment in enrollments:
            term = enrollment.class_header.term
            if term not in enrollments_by_term:
                enrollments_by_term[term] = []
            enrollments_by_term[term].append(enrollment)

        # Get GPA records
        gpa_filter = Q(student=student)
        if as_of_date:
            gpa_filter &= Q(calculated_at__lte=as_of_date)

        gpa_records = GPARecord.objects.filter(gpa_filter).order_by("term__start_date")

        # Calculate overall statistics
        total_credits_attempted = enrollments.aggregate(total=Sum("class_header__course__credits"))["total"] or 0

        total_credits_earned = (
            enrollments.filter(status__in=["COMPLETED", "PASSED"]).aggregate(
                total=Sum("class_header__course__credits"),
            )["total"]
            or 0
        )

        # Get latest cumulative GPA
        latest_gpa = gpa_records.filter(gpa_type="CUMULATIVE").order_by("-calculated_at").first()

        cumulative_gpa = latest_gpa.gpa_value if latest_gpa else None

        # Include transfer credits if requested
        transfer_credits = []
        if include_transfer_credits:
            transfer_credits = list(
                TransferCredit.objects.filter(
                    student=student,
                    approval_status=TransferCredit.ApprovalStatus.APPROVED,
                )
                .select_related(
                    "internal_equivalent_course",
                )
                .order_by("approved_at"),
            )

        return {
            "student": student,
            "enrollments_by_term": enrollments_by_term,
            "gpa_records": gpa_records,
            "total_credits_attempted": total_credits_attempted,
            "total_credits_earned": total_credits_earned,
            "cumulative_gpa": cumulative_gpa,
            "transfer_credits": transfer_credits,
            "generation_date": timezone.now(),
            "as_of_date": as_of_date or timezone.now(),
        }

    @classmethod
    def _generate_pdf_transcript(
        cls,
        student: StudentProfile,
        academic_data: dict[str, Any],
        document_type: DocumentTypeConfig,
    ) -> bytes:
        """Generate PDF transcript using reportlab.

        Args:
            student: Student for the transcript
            academic_data: Compiled academic data
            document_type: Document type configuration

        Returns:
            PDF content as bytes
        """
        # Create PDF buffer
        buffer = io.BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=cls.MARGIN,
            leftMargin=cls.MARGIN,
            topMargin=cls.MARGIN,
            bottomMargin=cls.MARGIN,
        )

        # Build PDF content
        story = []

        # Add header
        story.extend(cls._build_transcript_header(student, academic_data, document_type))

        # Add student information
        story.extend(cls._build_student_section(student, academic_data))

        # Add academic history by term
        story.extend(cls._build_academic_history(academic_data))

        # Add transfer credits section if available
        if academic_data["transfer_credits"]:
            story.extend(cls._build_transfer_credits_section(academic_data))

        # Add summary section
        story.extend(cls._build_summary_section(academic_data))

        # Add footer with verification info
        story.extend(cls._build_transcript_footer(academic_data))

        # Build PDF
        doc.build(story)

        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    @classmethod
    def _generate_pdf_enrollment_verification(
        cls,
        student: StudentProfile,
        academic_data: dict[str, Any],
        document_type: DocumentTypeConfig,
    ) -> bytes:
        """Generate PDF enrollment verification letter.

        Args:
            student: Student for the verification
            academic_data: Compiled academic data
            document_type: Document type configuration

        Returns:
            PDF content as bytes
        """
        # Create PDF buffer
        buffer = io.BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=cls.MARGIN,
            leftMargin=cls.MARGIN,
            topMargin=cls.MARGIN,
            bottomMargin=cls.MARGIN,
        )

        # Build PDF content
        story = []
        getSampleStyleSheet()

        # Add header
        story.extend(cls._build_transcript_header(student, academic_data, document_type))

        # Add enrollment verification content
        story.extend(cls._build_enrollment_verification_content(student, academic_data))

        # Add footer
        story.extend(cls._build_transcript_footer(academic_data))

        # Build PDF
        doc.build(story)

        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    @classmethod
    def _generate_pdf_generic_document(
        cls,
        student: StudentProfile,
        academic_data: dict[str, Any],
        document_type: DocumentTypeConfig,
    ) -> bytes:
        """Generate generic PDF document for other document types.

        Args:
            student: Student for the document
            academic_data: Compiled academic data
            document_type: Document type configuration

        Returns:
            PDF content as bytes
        """
        # Create PDF buffer
        buffer = io.BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=cls.MARGIN,
            leftMargin=cls.MARGIN,
            topMargin=cls.MARGIN,
            bottomMargin=cls.MARGIN,
        )

        # Build PDF content
        story = []

        # Add header
        story.extend(cls._build_transcript_header(student, academic_data, document_type))

        # Add student information
        story.extend(cls._build_student_section(student, academic_data))

        # Add generic content based on document type
        story.extend(cls._build_generic_document_content(student, academic_data, document_type))

        # Add footer
        story.extend(cls._build_transcript_footer(academic_data))

        # Build PDF
        doc.build(story)

        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    @classmethod
    def _build_enrollment_verification_content(
        cls,
        student: StudentProfile,
        academic_data: dict[str, Any],
    ) -> list:
        """Build enrollment verification letter content."""
        styles = getSampleStyleSheet()
        story = []

        # Verification letter text
        letter_style = ParagraphStyle(
            "LetterStyle",
            parent=styles["Normal"],
            fontSize=12,
            spaceAfter=15,
            spaceBefore=10,
        )

        story.append(Paragraph("TO WHOM IT MAY CONCERN:", letter_style))
        story.append(Spacer(1, 20))

        story.append(
            Paragraph(
                f"This letter certifies that {student.person.full_name} "
                f"(Student ID: {student.student_id}) is currently enrolled as a student "
                f"at Naga University.",
                letter_style,
            ),
        )

        if hasattr(student, "current_program") and student.current_program:
            story.append(
                Paragraph(
                    f"The student is enrolled in the {student.current_program.name} program.",
                    letter_style,
                ),
            )

        story.append(
            Paragraph(
                "This verification is issued upon request for official purposes.",
                letter_style,
            ),
        )

        story.append(Spacer(1, 40))

        # Signature section
        signature_style = ParagraphStyle(
            "SignatureStyle",
            parent=styles["Normal"],
            fontSize=11,
            spaceBefore=30,
        )

        story.append(Paragraph("_" * 40, signature_style))
        story.append(Paragraph("Registrar", signature_style))
        story.append(Paragraph("Naga University", signature_style))

        return story

    @classmethod
    def _build_generic_document_content(
        cls,
        student: StudentProfile,
        academic_data: dict[str, Any],
        document_type: DocumentTypeConfig,
    ) -> list:
        """Build generic document content based on document type."""
        styles = getSampleStyleSheet()
        story = []

        content_style = ParagraphStyle(
            "ContentStyle",
            parent=styles["Normal"],
            fontSize=12,
            spaceAfter=15,
            spaceBefore=10,
        )

        # Add document description
        if document_type.description:
            story.append(Paragraph(document_type.description, content_style))
            story.append(Spacer(1, 20))

        # Add basic academic information if needed
        if document_type.requires_grade_data:
            story.extend(cls._build_summary_section(academic_data))

        return story

    @classmethod
    def _build_transcript_header(
        cls,
        student: StudentProfile,
        academic_data: dict[str, Any],
        document_type: DocumentTypeConfig,
    ) -> list:
        """Build the transcript header section."""
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.black,
        )

        subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=styles["Normal"],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.black,
        )

        story = []

        # Institution header
        story.append(Paragraph("NAGA UNIVERSITY", title_style))
        story.append(Paragraph(document_type.name.upper(), subtitle_style))
        story.append(Spacer(1, 20))

        # Transcript metadata
        metadata_style = ParagraphStyle(
            "Metadata",
            parent=styles["Normal"],
            fontSize=10,
            alignment=TA_RIGHT,
        )

        story.append(
            Paragraph(
                f"Generated: {academic_data['generation_date'].strftime('%B %d, %Y')}",
                metadata_style,
            ),
        )
        story.append(
            Paragraph(
                f"Records as of: {academic_data['as_of_date'].strftime('%B %d, %Y')}",
                metadata_style,
            ),
        )
        story.append(Spacer(1, 30))

        return story

    @classmethod
    def _build_student_section(
        cls,
        student: StudentProfile,
        academic_data: dict[str, Any],
    ) -> list:
        """Build the student information section."""
        getSampleStyleSheet()

        story = []

        # Student information table
        student_data = [
            ["Student Name:", student.person.full_name],
            ["Student ID:", student.student_id],
            [
                "Date of Birth:",
                (student.person.date_of_birth.strftime("%B %d, %Y") if student.person.date_of_birth else "N/A"),
            ],
            [
                "Current Program:",
                getattr(getattr(student, "current_program", None), "name", "Not enrolled"),
            ],
        ]

        student_table = Table(student_data, colWidths=[2 * inch, 4 * inch])
        student_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ],
            ),
        )

        story.append(student_table)
        story.append(Spacer(1, 30))

        return story

    @classmethod
    def _build_academic_history(cls, academic_data: dict[str, Any]) -> list:
        """Build the academic history section."""
        styles = getSampleStyleSheet()
        story = []

        # Academic history header
        history_header = ParagraphStyle(
            "HistoryHeader",
            parent=styles["Heading2"],
            fontSize=14,
            spaceAfter=15,
            textColor=colors.black,
        )

        story.append(Paragraph("ACADEMIC HISTORY", history_header))

        # Process each term
        for term, enrollments in academic_data["enrollments_by_term"].items():
            # Term header
            term_style = ParagraphStyle(
                "TermHeader",
                parent=styles["Heading3"],
                fontSize=12,
                spaceBefore=15,
                spaceAfter=10,
                textColor=colors.black,
            )

            story.append(Paragraph(f"{term.code}", term_style))

            # Course table headers
            course_data = [["Course", "Title", "Credits", "Grade", "Points"]]

            term_credits = 0
            term_points = 0

            # Add courses for this term
            for enrollment in enrollments:
                course = enrollment.class_header.course
                course_credits = course.credits

                # Get final grade (simplified - would use actual grade calculation)
                grade = getattr(
                    enrollment,
                    "final_grade",
                    "IP",
                )  # In Progress if no grade

                # Calculate quality points (simplified)
                quality_points = 0
                if grade and grade != "IP":
                    # This would use the actual grade conversion service
                    grade_point_map = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
                    grade_points = grade_point_map.get(grade, 0)
                    quality_points = course_credits * grade_points

                course_data.append(
                    [
                        course.code,
                        course.title[:COURSE_TITLE_TRUNCATE_LENGTH]
                        + ("..." if len(course.title) > COURSE_TITLE_TRUNCATE_LENGTH else ""),
                        str(course_credits),
                        grade or "IP",
                        f"{quality_points:.1f}" if quality_points else "",
                    ],
                )

                term_credits += course_credits
                term_points += quality_points

            # Add term summary
            term_gpa = (term_points / term_credits) if term_credits > 0 else 0.0
            course_data.append(
                ["", "Term Totals:", f"{term_credits}", "", f"{term_points:.1f}"],
            )
            course_data.append(["", "Term GPA:", "", "", f"{term_gpa:.2f}"])

            # Create course table
            course_table = Table(
                course_data,
                colWidths=[1 * inch, 2.5 * inch, 0.8 * inch, 0.8 * inch, 0.9 * inch],
            )
            course_table.setStyle(
                TableStyle(
                    [
                        # Header row
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        (
                            "ALIGN",
                            (2, 0),
                            (-1, -1),
                            "CENTER",
                        ),  # Credits, Grade, Points columns
                        # Data rows
                        ("FONTNAME", (0, 1), (-1, -3), "Helvetica"),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -3),
                            [colors.white, colors.lightgrey],
                        ),
                        # Summary rows
                        ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"),
                        ("LINEABOVE", (0, -2), (-1, -2), 1, colors.black),
                        # Borders
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ],
                ),
            )

            story.append(course_table)
            story.append(Spacer(1, 15))

        return story

    @classmethod
    def _build_transfer_credits_section(cls, academic_data: dict[str, Any]) -> list:
        """Build the transfer credits section."""
        styles = getSampleStyleSheet()
        story = []

        # Transfer credits header
        header_style = ParagraphStyle(
            "TransferHeader",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=12,
            spaceBefore=20,
        )

        story.append(Paragraph("Transfer Credits", header_style))

        # Build transfer credits table
        transfer_data = [
            [
                "Institution",
                "Course",
                "Title",
                "Grade",
                "Credits",
                "Internal Equivalent",
            ]
        ]

        for credit in academic_data["transfer_credits"]:
            equivalent_course = (
                f"{credit.internal_equivalent_course.code} - {credit.internal_equivalent_course.title}"
                if credit.internal_equivalent_course
                else "Elective Credit"
            )

            transfer_data.append(
                [
                    credit.external_institution[:25],  # Truncate long names
                    credit.external_course_code,
                    credit.external_course_title[:30],  # Truncate long titles
                    credit.external_grade,
                    str(credit.internal_credits),
                    equivalent_course[:30],  # Truncate long equivalent names
                ],
            )

        # Create and style the transfer credits table
        transfer_table = Table(
            transfer_data,
            colWidths=[
                1.2 * inch,
                0.8 * inch,
                1.5 * inch,
                0.6 * inch,
                0.7 * inch,
                1.5 * inch,
            ],
            repeatRows=1,
        )

        transfer_table.setStyle(
            TableStyle(
                [
                    # Header row styling
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    # Data rows styling
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("ALIGN", (0, 1), (3, -1), "LEFT"),  # Left align text columns
                    ("ALIGN", (4, 1), (4, -1), "CENTER"),  # Center align credits
                    ("ALIGN", (5, 1), (5, -1), "LEFT"),  # Left align equivalent course
                    # Grid and borders
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # Alternating row colors for readability
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.lightgrey],
                    ),
                ],
            ),
        )

        story.append(transfer_table)
        story.append(Spacer(1, 15))

        # Add transfer credits summary
        total_transfer_credits = sum(credit.internal_credits for credit in academic_data["transfer_credits"])
        summary_text = f"Total Transfer Credits Accepted: {total_transfer_credits}"

        summary_style = ParagraphStyle(
            "TransferSummary",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_RIGHT,
            spaceBefore=5,
        )

        story.append(Paragraph(summary_text, summary_style))
        story.append(Spacer(1, 10))

        return story

    @classmethod
    def _build_summary_section(cls, academic_data: dict[str, Any]) -> list:
        """Build the academic summary section."""
        styles = getSampleStyleSheet()
        story = []

        # Summary header
        summary_header = ParagraphStyle(
            "SummaryHeader",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=15,
            textColor=colors.black,
        )

        story.append(Paragraph("ACADEMIC SUMMARY", summary_header))

        # Summary data
        summary_data = [
            ["Total Credits Attempted:", f"{academic_data['total_credits_attempted']}"],
            ["Total Credits Earned:", f"{academic_data['total_credits_earned']}"],
            [
                "Cumulative GPA:",
                (f"{academic_data['cumulative_gpa']:.3f}" if academic_data["cumulative_gpa"] else "N/A"),
            ],
        ]

        summary_table = Table(summary_data, colWidths=[2.5 * inch, 1.5 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ],
            ),
        )

        story.append(summary_table)
        story.append(Spacer(1, 30))

        return story

    @classmethod
    def _build_transcript_footer(cls, academic_data: dict[str, Any]) -> list:
        """Build the transcript footer with verification information."""
        styles = getSampleStyleSheet()
        story = []

        # Footer text
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey,
        )

        story.append(Spacer(1, 40))
        story.append(Paragraph("*** END OF TRANSCRIPT ***", footer_style))
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                "This is an official academic transcript. Any alteration or unauthorized reproduction is prohibited.",
                footer_style,
            ),
        )
        story.append(
            Paragraph(
                f"Document generated on {academic_data['generation_date'].strftime('%B %d, %Y at %I:%M %p')}",
                footer_style,
            ),
        )

        return story

    @staticmethod
    def _generate_verification_qr(student: StudentProfile, content_hash: str) -> str:
        """Generate QR code data for document verification.

        Args:
            student: Student for the document
            content_hash: Hash of the document content

        Returns:
            QR code data string
        """
        # In production, this would be a secure verification URL
        return f"VERIFY:{student.student_id}:{content_hash[:16]}"

    @classmethod
    def _save_pdf_to_storage(
        cls,
        pdf_content: bytes,
        student: StudentProfile,
        document_id: str,
    ) -> str:
        """Save PDF content to storage and return the file path.

        Args:
            pdf_content: PDF content as bytes
            student: Student profile for organization
            document_id: Unique document identifier

        Returns:
            File path where the PDF was saved
        """
        # Create directory structure: transcripts/student_id/year/
        current_year = timezone.now().year
        directory = f"transcripts/{student.student_id}/{current_year}"

        # Create filename with timestamp for uniqueness
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{document_id}_{timestamp}.pdf"
        file_path = f"{directory}/{filename}"

        try:
            # Ensure directory exists (for local storage)
            if hasattr(settings, "MEDIA_ROOT"):
                full_directory = Path(settings.MEDIA_ROOT) / directory
                full_directory.mkdir(parents=True, exist_ok=True)

            # Save file using Django's storage system
            # This works with both local storage and cloud storage (S3, etc.)
            content_file = ContentFile(pdf_content, name=filename)
            return default_storage.save(file_path, content_file)

        except (ValueError, TypeError, AttributeError):
            # Log the error and fall back to a simple path
            # In production, you'd want proper logging here
            return f"transcripts/{student.student_id}/{document_id}.pdf"

    @classmethod
    def get_document_file_url(cls, document: GeneratedDocument) -> str | None:
        """Get the URL for accessing a document PDF file.

        Args:
            document: GeneratedDocument instance

        Returns:
            URL to access the file, or None if file doesn't exist
        """
        if not document.file_path:
            return None

        try:
            # Check if file exists
            if default_storage.exists(document.file_path):
                return default_storage.url(document.file_path)
            return None
        except (ValueError, TypeError, AttributeError):
            # Handle storage errors gracefully
            return None


class DocumentQuotaService:
    """Service for managing document quotas and usage."""

    @staticmethod
    def get_active_quota(student: StudentProfile, term) -> DocumentQuota | None:
        """Get active document quota for a student in a term.

        Args:
            student: The student to check
            term: The term to check

        Returns:
            Active DocumentQuota or None if not found
        """
        from django.utils import timezone

        return DocumentQuota.objects.filter(
            student=student, term=term, is_active=True, expires_date__gte=timezone.now().date()
        ).first()

    @staticmethod
    @transaction.atomic
    def create_quota_for_term(
        student: StudentProfile, term, cycle_status: StudentCycleStatus, total_units: int, admin_fee_line_item=None
    ) -> DocumentQuota:
        """Create document quota for a student for a term.

        Args:
            student: The student to create quota for
            term: The term to create quota for
            cycle_status: The student's cycle status
            total_units: Total units to allocate
            admin_fee_line_item: Optional invoice line item that included this quota

        Returns:
            Created DocumentQuota
        """
        # Calculate expiration date (end of term + 30 days grace period)
        expires_date = term.end_date + timedelta(days=30)

        # Check if quota already exists
        existing = DocumentQuota.objects.filter(student=student, term=term).first()

        if existing:
            # Update existing quota
            existing.total_units = total_units
            existing.is_active = True
            existing.expires_date = expires_date
            existing.cycle_status = cycle_status
            if admin_fee_line_item:
                existing.admin_fee_line_item = admin_fee_line_item
            existing.save()
            return existing

        # Create new quota
        return DocumentQuota.objects.create(
            student=student,
            term=term,
            cycle_status=cycle_status,
            total_units=total_units,
            used_units=0,
            is_active=True,
            expires_date=expires_date,
            admin_fee_line_item=admin_fee_line_item,
        )

    @staticmethod
    @transaction.atomic
    def check_and_consume_quota(
        student: StudentProfile, document_type: DocumentTypeConfig, term
    ) -> tuple[bool, DocumentQuota | None, int]:
        """Check if student has quota and consume if available.

        Args:
            student: The student requesting document
            document_type: The type of document requested
            term: The current term

        Returns:
            Tuple of (quota_used, quota_object, excess_units)
            - quota_used: True if quota was used, False if no quota or insufficient
            - quota_object: The DocumentQuota object if found
            - excess_units: Number of units that exceed quota (0 if within quota)
        """
        quota = DocumentQuotaService.get_active_quota(student, term)

        if not quota:
            return False, None, document_type.unit_cost

        units_needed = document_type.unit_cost

        # Check if sufficient units available
        if quota.remaining_units >= units_needed:
            # Consume units
            quota.consume_units(units_needed)
            return True, quota, 0
        else:
            # Calculate excess
            excess = units_needed - quota.remaining_units
            return False, quota, excess

    @staticmethod
    @transaction.atomic
    def process_document_request(
        document_request: DocumentRequest,
    ) -> tuple[bool, DocumentQuotaUsage | None, Any | None]:
        """Process a document request against quotas.

        Args:
            document_request: The document request to process

        Returns:
            Tuple of (success, quota_usage, excess_charge)
            - success: True if request was processed successfully
            - quota_usage: DocumentQuotaUsage if quota was used
            - excess_charge: InvoiceLineItem if excess charge was applied
        """
        # Type annotations to help mypy understand the concrete types
        student: StudentProfile = cast("StudentProfile", document_request.student)
        document_type: DocumentTypeConfig = cast("DocumentTypeConfig", document_request.document_type)

        # Get current term (you may need to adjust this based on your term selection logic)
        from apps.curriculum.models import Term

        current_term = Term.get_current_term()

        # Check and consume quota
        quota_used, quota, excess_units = DocumentQuotaService.check_and_consume_quota(
            student, document_type, current_term
        )

        quota_usage = None
        excess_charge = None

        # Record quota usage if any units were consumed from quota
        if quota and quota_used:
            quota_usage = DocumentQuotaUsage.objects.create(
                quota=quota,
                document_request=document_request,
                units_consumed=document_type.unit_cost,
            )
        elif quota and excess_units > 0:
            # Partial quota usage
            if quota.remaining_units > 0:
                quota_usage = DocumentQuotaUsage.objects.create(
                    quota=quota, document_request=document_request, units_consumed=quota.remaining_units
                )
                # Consume remaining units
                quota.consume_units(quota.remaining_units)

            # Apply excess charge
            from apps.finance.models.administrative import AdministrativeFeeConfig
            from apps.finance.services.administrative import AdministrativeFeeService

            # Get excess fee configuration
            excess_config = AdministrativeFeeConfig.objects.filter(
                cycle_type=quota.cycle_status.cycle_type, is_active=True
            ).first()

            if excess_config:
                excess_charge = AdministrativeFeeService.apply_document_excess_charge(
                    student=student,
                    document_request=document_request,
                    excess_units=excess_units,
                    fee_per_unit=excess_config.fee_per_unit,
                )

        return True, quota_usage, excess_charge

    @staticmethod
    def get_quota_summary(student: StudentProfile, term):
        """Get quota usage summary for a student in a term.

        Args:
            student: The student to check
            term: The term to check

        Returns:
            Dictionary with quota summary information
        """
        quota = DocumentQuotaService.get_active_quota(student, term)

        if not quota:
            return {
                "has_quota": False,
                "total_units": 0,
                "used_units": 0,
                "remaining_units": 0,
                "usage_percentage": 0.0,
                "is_expired": False,
                "expires_date": None,
                "cycle_type": None,
            }

        return {
            "has_quota": True,
            "total_units": quota.total_units,
            "used_units": quota.used_units,
            "remaining_units": quota.remaining_units,
            "usage_percentage": quota.usage_percentage,
            "is_expired": quota.is_expired,
            "expires_date": quota.expires_date,
            "cycle_type": getattr(quota.cycle_status, "cycle_type", None),
        }

    @staticmethod
    def expire_old_quotas():
        """Expire quotas that have passed their expiration date.

        Returns:
            Number of quotas expired
        """
        from django.utils import timezone

        today = timezone.now().date()
        expired_count = DocumentQuota.objects.filter(is_active=True, expires_date__lt=today).update(is_active=False)

        return expired_count
