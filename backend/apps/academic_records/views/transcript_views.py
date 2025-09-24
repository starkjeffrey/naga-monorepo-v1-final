"""Transcript generation views with PDF export and HTMX endpoints.

This module provides transcript management functionality including:
- Dashboard for viewing transcript requests
- PDF generation with academic data integration
- HTMX endpoints for real-time updates
- Bulk transcript generation capabilities
"""

import io
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.academic_records.models import DocumentFeeCalculator, DocumentRequest, DocumentTypeConfig
from apps.grading.models import ClassPartGrade
from apps.people.models import StudentProfile

# Import for PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)


class TranscriptDashboardView(LoginRequiredMixin, TemplateView):
    """Main transcript management dashboard."""

    template_name = "academic_records/transcript_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get transcript document type
        transcript_type = DocumentTypeConfig.objects.filter(code="OFFICIAL_TRANSCRIPT", is_active=True).first()

        if not transcript_type:
            # Create default transcript type if it doesn't exist
            transcript_type = DocumentTypeConfig.objects.create(
                code="OFFICIAL_TRANSCRIPT",
                name="Official Academic Transcript",
                category=DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
                description="Official academic transcript showing all completed courses and grades",
                requires_approval=True,
                auto_generate=False,
                processing_time_hours=24,
                requires_grade_data=True,
                has_fee=True,
                fee_amount=15.00,
                free_allowance_per_year=2,
            )

        # Get recent transcript requests
        transcript_requests = (
            DocumentRequest.objects.filter(document_type=transcript_type)
            .select_related("student__person", "requested_by", "assigned_to")
            .prefetch_related("generated_documents")[:50]
        )

        # Calculate statistics
        today = timezone.now().date()
        this_month = today.replace(day=1)

        pending_count = DocumentRequest.objects.filter(
            document_type=transcript_type, request_status=DocumentRequest.RequestStatus.PENDING
        ).count()

        today_count = DocumentRequest.objects.filter(document_type=transcript_type, requested_date__date=today).count()

        month_count = DocumentRequest.objects.filter(
            document_type=transcript_type, requested_date__date__gte=this_month
        ).count()

        # Calculate average GPA from grades
        avg_gpa = (
            ClassPartGrade.objects.filter(gpa_points__isnull=False).aggregate(avg_gpa=Avg("gpa_points"))["avg_gpa"]
            or 0
        )

        context.update(
            {
                "transcripts": transcript_requests,
                "pending_count": pending_count,
                "today_count": today_count,
                "month_count": month_count,
                "avg_gpa": avg_gpa,
                "transcript_type": transcript_type,
            }
        )

        return context


@login_required
def transcript_dashboard(request):
    """HTMX endpoint for transcript dashboard data."""
    search = request.GET.get("q", "")
    status = request.GET.get("status", "all")
    request.GET.get("type", "all")

    # Get transcript document type
    transcript_type = DocumentTypeConfig.objects.filter(code="OFFICIAL_TRANSCRIPT", is_active=True).first()

    if not transcript_type:
        return JsonResponse({"error": "Transcript document type not configured"}, status=400)

    # Build query
    transcripts = DocumentRequest.objects.filter(document_type=transcript_type).select_related(
        "student__person", "requested_by"
    )

    if search:
        transcripts = transcripts.filter(
            Q(student__student_id__icontains=search)
            | Q(student__person__name_en__icontains=search)
            | Q(student__person__name_km__icontains=search)
        )

    if status != "all":
        transcripts = transcripts.filter(request_status=status)

    transcripts = transcripts.order_by("-requested_date")[:50]

    return render(request, "academic_records/partials/transcript_list.html", {"transcripts": transcripts})


@login_required
def generate_transcript(request, student_id):
    """Generate official transcript for a student."""
    student = get_object_or_404(StudentProfile, id=student_id)

    # Get all grades for the student
    grades = (
        ClassPartGrade.objects.filter(enrollment__student=student, gpa_points__isnull=False)
        .select_related(
            "enrollment__class_header__course", "enrollment__class_header__term", "enrollment__class_header"
        )
        .order_by("enrollment__class_header__term__start_date", "enrollment__class_header__course__code")
    )

    # Calculate GPAs by term
    term_gpas = calculate_term_gpas(grades)
    cumulative_gpa = calculate_cumulative_gpa(grades)

    # Get transcript document type
    transcript_type = DocumentTypeConfig.objects.filter(code="OFFICIAL_TRANSCRIPT", is_active=True).first()

    if request.GET.get("format") == "pdf":
        return generate_transcript_pdf(student, grades, term_gpas, cumulative_gpa)

    return render(
        request,
        "academic_records/transcript_preview.html",
        {
            "student": student,
            "grades": grades,
            "term_gpas": term_gpas,
            "cumulative_gpa": cumulative_gpa,
            "transcript_type": transcript_type,
        },
    )


@login_required
def transcript_preview(request, request_id):
    """Preview transcript before final generation."""
    doc_request = get_object_or_404(DocumentRequest, id=request_id)
    student = doc_request.student

    # Get academic data
    grades = (
        ClassPartGrade.objects.filter(enrollment__student=student, gpa_points__isnull=False)
        .select_related("enrollment__class_header__course", "enrollment__class_header__term")
        .order_by("enrollment__class_header__term__start_date")
    )

    term_gpas = calculate_term_gpas(grades)
    cumulative_gpa = calculate_cumulative_gpa(grades)

    return render(
        request,
        "academic_records/transcript_preview.html",
        {
            "student": student,
            "grades": grades,
            "term_gpas": term_gpas,
            "cumulative_gpa": cumulative_gpa,
            "document_request": doc_request,
        },
    )


def calculate_term_gpas(grades) -> dict[str, float]:
    """Calculate GPA by term from grades."""
    term_gpas = {}
    term_grades = {}

    for grade in grades:
        term_key = str(grade.enrollment.class_header.term.id)
        if term_key not in term_grades:
            term_grades[term_key] = {"term": grade.enrollment.class_header.term, "grades": [], "credits": 0}

        if grade.gpa_points is not None:
            term_grades[term_key]["grades"].append(grade.gpa_points)
            # Assume 3 credits per course if not specified
            credits = getattr(grade.enrollment.class_header.course, "credits", 3)
            term_grades[term_key]["credits"] += credits

    for _term_key, data in term_grades.items():
        if data["grades"]:
            gpa = sum(data["grades"]) / len(data["grades"])
            term_gpas[f"{data['term'].name}"] = round(gpa, 2)

    return term_gpas


def calculate_cumulative_gpa(grades) -> float:
    """Calculate cumulative GPA from all grades."""
    if not grades:
        return 0.0

    total_points = 0
    total_credits = 0

    for grade in grades:
        if grade.gpa_points is not None:
            credits = getattr(grade.enrollment.class_header.course, "credits", 3)
            total_points += grade.gpa_points * credits
            total_credits += credits

    if total_credits == 0:
        return 0.0

    return round(total_points / total_credits, 2)


def generate_transcript_pdf(student, grades, term_gpas, cumulative_gpa) -> HttpResponse:
    """Generate PDF transcript document."""
    if not REPORTLAB_AVAILABLE:
        return HttpResponse("PDF generation not available. Please install reportlab.", status=500)

    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Build PDF content
    story = []
    styles = getSampleStyleSheet()

    # Header
    header_style = ParagraphStyle(
        "CustomHeader", parent=styles["Heading1"], fontSize=16, spaceAfter=30, alignment=TA_CENTER
    )

    story.append(Paragraph("OFFICIAL ACADEMIC TRANSCRIPT", header_style))
    story.append(Spacer(1, 12))

    # Institution info
    institution_style = ParagraphStyle(
        "Institution", parent=styles["Normal"], fontSize=12, alignment=TA_CENTER, spaceAfter=20
    )

    story.append(Paragraph("Naga University", institution_style))
    story.append(Paragraph("Academic Records Office", institution_style))
    story.append(Spacer(1, 20))

    # Student information
    student_info = [
        ["Student Name:", student.person.name_en],
        ["Student ID:", student.student_id],
        [
            "Date of Birth:",
            student.person.date_of_birth.strftime("%B %d, %Y") if student.person.date_of_birth else "N/A",
        ],
        ["Transcript Date:", timezone.now().strftime("%B %d, %Y")],
    ]

    student_table = Table(student_info, colWidths=[2 * inch, 4 * inch])
    student_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(student_table)
    story.append(Spacer(1, 20))

    # Academic record by term
    if grades:
        # Group grades by term
        from typing import Any

        terms_data: dict[Any, list[dict[str, Any]]] = {}
        for grade in grades:
            term = grade.enrollment.class_header.term
            if term not in terms_data:
                terms_data[term] = []

            course = grade.enrollment.class_header.course
            terms_data[term].append(
                {
                    "course_code": course.code,
                    "course_name": course.name,
                    "credits": getattr(course, "credits", 3),
                    "grade": grade.letter_grade or grade.gpa_points or "N/A",
                }
            )

        # Build course table for each term
        for term, courses in terms_data.items():
            # Term header
            term_header = Paragraph(f"<b>{term.name}</b>", styles["Heading2"])
            story.append(term_header)
            story.append(Spacer(1, 10))

            # Course table
            course_data = [["Course Code", "Course Title", "Credits", "Grade"]]

            for course in courses:
                course_data.append(
                    [
                        course["course_code"],
                        (
                            course["course_name"][:40] + "..."
                            if len(course["course_name"]) > 40
                            else course["course_name"]
                        ),
                        str(course["credits"]),
                        str(course["grade"]),
                    ]
                )

            # Add term GPA
            term_gpa = term_gpas.get(term.name, 0.0)
            course_data.append(["", f"<b>Term GPA: {term_gpa}</b>", "", ""])

            course_table = Table(course_data, colWidths=[1.5 * inch, 3 * inch, 0.8 * inch, 0.8 * inch])
            course_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -2), 1, colors.black),
                        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ]
                )
            )

            story.append(course_table)
            story.append(Spacer(1, 15))

    # Summary
    summary_data = [
        ["Cumulative GPA:", f"{cumulative_gpa}"],
        ["Total Credits:", str(len(grades) * 3)],  # Approximate
        ["Transcript Status:", "Official"],
    ]

    summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    story.append(Spacer(1, 20))
    story.append(summary_table)

    # Footer
    story.append(Spacer(1, 30))
    footer_text = f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}"
    footer = Paragraph(footer_text, styles["Normal"])
    story.append(footer)

    # Build PDF
    doc.build(story)

    # Create response
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="transcript_{student.student_id}.pdf"'

    return response


@login_required
@require_http_methods(["POST"])
def bulk_generate_transcripts(request):
    """HTMX endpoint for bulk transcript generation."""
    student_ids = request.POST.getlist("student_ids")

    if not student_ids:
        return JsonResponse({"error": "No students selected"}, status=400)

    # Get transcript document type
    transcript_type = DocumentTypeConfig.objects.filter(code="OFFICIAL_TRANSCRIPT", is_active=True).first()

    if not transcript_type:
        return JsonResponse({"error": "Transcript document type not configured"}, status=400)

    generated_count = 0
    errors = []

    for student_id in student_ids:
        try:
            student = StudentProfile.objects.get(id=student_id)

            # Create document request
            _request_obj, _fee_calc = DocumentFeeCalculator.create_request_with_fee_calculation(
                student=student,
                document_type=transcript_type,
                requested_by=request.user,
                delivery_method=DocumentRequest.DeliveryMethod.EMAIL,
                recipient_email=student.person.email,
                request_notes=f"Bulk generated by {request.user.get_full_name() or request.user.email}",
            )

            generated_count += 1

        except Exception as e:
            errors.append(f"Student {student_id}: {e!s}")
            logger.error(f"Error generating transcript for student {student_id}: {e}")

    return JsonResponse(
        {
            "success": True,
            "generated_count": generated_count,
            "errors": errors,
            "message": f"Generated {generated_count} transcript requests successfully.",
        }
    )


@login_required
def transcript_wizard(request):
    """HTMX endpoint for transcript generation wizard."""
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        delivery_method = request.POST.get("delivery_method")
        recipient_email = request.POST.get("recipient_email", "")
        recipient_address = request.POST.get("recipient_address", "")
        notes = request.POST.get("notes", "")

        try:
            student = StudentProfile.objects.get(id=student_id)

            # Get transcript document type
            transcript_type = DocumentTypeConfig.objects.filter(code="OFFICIAL_TRANSCRIPT", is_active=True).first()

            if not transcript_type:
                return JsonResponse({"error": "Transcript document type not configured"}, status=400)

            # Create the document request with fee calculation
            request_obj, fee_calc = DocumentFeeCalculator.create_request_with_fee_calculation(
                student=student,
                document_type=transcript_type,
                requested_by=request.user,
                delivery_method=delivery_method,
                recipient_email=recipient_email,
                recipient_address=recipient_address,
                request_notes=notes,
            )

            return JsonResponse(
                {
                    "success": True,
                    "request_id": str(request_obj.request_id),
                    "message": f"Transcript request created successfully for {student.person.name_en}",
                    "fee_info": fee_calc,
                }
            )

        except StudentProfile.DoesNotExist:
            return JsonResponse({"error": "Student not found"}, status=404)
        except Exception as e:
            logger.error(f"Error creating transcript request: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    # GET request - show wizard form
    students = StudentProfile.objects.select_related("person").order_by("student_id")[:100]

    return render(request, "academic_records/partials/transcript_wizard.html", {"students": students})
