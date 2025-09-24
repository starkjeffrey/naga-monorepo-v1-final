"""
Student Locator views - Advanced search system for students.

Based on the attractive design by Claude Desktop Opus.
"""

import csv
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

try:
    import xlsxwriter

    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False

from django.db.models import F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import ListView, TemplateView

from apps.curriculum.models import Major
from apps.people.models import StudentProfile

from ..permissions import StaffRequiredMixin


class StudentLocatorView(StaffRequiredMixin, TemplateView):
    """Main student locator page with stats."""

    template_name = "web_interface/pages/students/student_locator.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate statistics
        total_students = StudentProfile.objects.filter(is_deleted=False).count()
        # Handle both 'ACTIVE' and 'Active' status values
        active_students = StudentProfile.objects.filter(is_deleted=False, current_status__iexact="active").count()

        # Students enrolled in current term (last 3 months)
        three_months_ago = timezone.now().date() - timedelta(days=90)
        term_students = StudentProfile.objects.filter(
            is_deleted=False, last_enrollment_date__gte=three_months_ago
        ).count()

        # Get all programs for dropdown
        programs = Major.objects.filter(is_active=True).order_by("name")

        context.update(
            {
                "page_title": _("Student Locator"),
                "current_page": "student-locator",
                "total_students": total_students,
                "active_students": active_students,
                "term_students": term_students,
                "programs": programs,
            }
        )

        return context


class StudentLocatorResultsView(StaffRequiredMixin, ListView):
    """HTMX endpoint for student search results."""

    model = StudentProfile
    template_name = "web_interface/pages/students/student_locator_results.html"
    context_object_name = "students"
    paginate_by = 50

    def get_queryset(self):
        """Apply filters to student queryset."""
        # Start with optimized base query
        # Note: Invoice and ProgramEnrollment use student_id foreign key, not direct relations
        queryset = (
            StudentProfile.objects.filter(is_deleted=False)
            .select_related("person")
            .prefetch_related(
                "program_enrollments__program",  # ProgramEnrollment has related_name='program_enrollments'
                "invoices",  # Invoice has related_name='invoices'
            )
            .annotate(
                current_balance=Coalesce(
                    Sum(F("invoices__total_amount") - F("invoices__paid_amount")), Value(Decimal("0.00"))
                )
            )
        )

        # Get filter parameters
        params = self.request.GET

        # Student ID search
        if student_id := params.get("student_id", "").strip():
            queryset = queryset.filter(student_id__startswith=student_id)  # Optimized: students search by ID prefix

        # Name search (handles both English and Khmer names)
        if name := params.get("name", "").strip():
            queryset = queryset.filter(
                Q(person__full_name__icontains=name)
                | Q(person__family_name__icontains=name)
                | Q(person__personal_name__icontains=name)
                | Q(person__khmer_name__icontains=name)
            )

        # Email search (check both school_email and personal_email)
        if email := params.get("email", "").strip():
            queryset = queryset.filter(
                Q(person__school_email__icontains=email) | Q(person__personal_email__icontains=email)
            )

        # Program filter
        if program_id := params.get("program"):
            queryset = queryset.filter(
                program_enrollments__program_id=program_id, program_enrollments__status="ACTIVE"
            ).distinct()

        # Status filter
        if status := params.get("status"):
            queryset = queryset.filter(current_status=status)

        # Study time preference
        if study_time := params.get("study_time"):
            queryset = queryset.filter(study_time_preference=study_time)

        # Gender filter
        if gender := params.get("gender"):
            queryset = queryset.filter(person__preferred_gender=gender)

        # Age range filter
        if age_min := params.get("age_min"):
            try:
                min_age = int(age_min)
                min_birthdate = date.today() - timedelta(days=min_age * 365)
                queryset = queryset.filter(person__date_of_birth__lte=min_birthdate)
            except (ValueError, TypeError):
                pass

        if age_max := params.get("age_max"):
            try:
                max_age = int(age_max)
                max_birthdate = date.today() - timedelta(days=max_age * 365)
                queryset = queryset.filter(person__date_of_birth__gte=max_birthdate)
            except (ValueError, TypeError):
                pass

        # Balance range filter
        if balance_min := params.get("balance_min"):
            try:
                min_balance = Decimal(balance_min)
                queryset = queryset.filter(current_balance__gte=min_balance)
            except (ValueError, TypeError):
                pass

        if balance_max := params.get("balance_max"):
            try:
                max_balance = Decimal(balance_max)
                queryset = queryset.filter(current_balance__lte=max_balance)
            except (ValueError, TypeError):
                pass

        # Enrollment date range
        if enrolled_from := params.get("enrolled_from"):
            queryset = queryset.filter(last_enrollment_date__gte=enrolled_from)

        if enrolled_to := params.get("enrolled_to"):
            queryset = queryset.filter(last_enrollment_date__lte=enrolled_to)

        # Citizenship filter
        if citizenship := params.get("citizenship"):
            if citizenship == "cambodian":
                queryset = queryset.filter(
                    Q(person__citizenship="KH")
                    | Q(person__citizenship="CA")  # CA seems to be used for Cambodia in data
                )
            elif citizenship == "international":
                queryset = queryset.exclude(Q(person__citizenship="KH") | Q(person__citizenship="CA"))

        # Has balance filter
        if has_balance := params.get("has_balance"):
            if has_balance == "yes":
                queryset = queryset.filter(current_balance__gt=0)
            elif has_balance == "no":
                queryset = queryset.filter(Q(current_balance__lte=0) | Q(current_balance__isnull=True))

        # Checkbox filters
        if params.get("missing_email"):
            queryset = queryset.filter(
                Q(person__school_email__isnull=True, person__personal_email__isnull=True)
                | Q(person__school_email="", person__personal_email="")
                | Q(person__school_email="", person__personal_email__isnull=True)
                | Q(person__school_email__isnull=True, person__personal_email="")
            )

        # Note: Person model doesn't have a phone field based on our inspection
        # This would need to be added to the model or removed from the filter

        if params.get("has_invoices"):
            queryset = queryset.filter(invoices__isnull=False).distinct()

        # Add current program annotation for display
        # Get the most recent active program enrollment
        queryset = queryset.annotate(current_program=F("program_enrollments__program__name"))

        # Order by most recent enrollment
        queryset = queryset.order_by("-last_enrollment_date", "-created_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Use paginator count instead of redundant database query
        if context.get("is_paginated") and context.get("page_obj"):
            context["result_count"] = context["page_obj"].paginator.count
        else:
            context["result_count"] = self.get_queryset().count()
        return context


class StudentLocatorExportView(StudentLocatorResultsView):
    """Export student search results to CSV or Excel."""

    paginate_by = None  # Export all results

    def render_to_response(self, context, **response_kwargs):
        """Generate CSV or Excel file."""
        export_format = self.request.GET.get("export", "csv")
        students = context["students"]

        if export_format == "excel":
            return self.export_excel(students)
        else:
            return self.export_csv(students)

    def export_csv(self, students):
        """Export to CSV format."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="students_export.csv"'

        writer = csv.writer(response)
        writer.writerow(
            ["Student ID", "Name", "Khmer Name", "Email", "Phone", "Program", "Status", "Balance", "Last Enrollment"]
        )

        for student in students:
            writer.writerow(
                [
                    student.student_id,
                    student.person.full_name,
                    student.person.khmer_name or "",
                    student.person.school_email
                    or student.person.personal_email
                    or "",  # Clean: use empty string instead of "No email"
                    "No phone",  # Person model doesn't have phone field
                    student.current_program or "TBD",
                    student.get_current_status_display(),
                    f"${float(student.current_balance or 0):.2f}",
                    student.last_enrollment_date.strftime("%Y-%m-%d") if student.last_enrollment_date else "",
                ]
            )

        return response

    def export_excel(self, students):
        """Export to Excel format."""
        if not HAS_XLSXWRITER:
            # Fall back to CSV if xlsxwriter is not available
            return self.export_csv(students)

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet("Students")

        # Define formats
        header_format = workbook.add_format({"bold": True, "bg_color": "#667eea", "font_color": "white", "border": 1})

        # Write headers
        headers = [
            "Student ID",
            "Name",
            "Khmer Name",
            "Email",
            "Phone",
            "Program",
            "Status",
            "Balance",
            "Last Enrollment",
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        for row, student in enumerate(students, start=1):
            worksheet.write(row, 0, student.student_id)
            worksheet.write(row, 1, student.person.full_name)
            worksheet.write(row, 2, student.person.khmer_name or "")
            worksheet.write(
                row, 3, student.person.school_email or student.person.personal_email or ""
            )  # Clean: use empty string instead of "No email"
            worksheet.write(row, 4, "No phone")  # Person model doesn't have phone field
            worksheet.write(row, 5, student.current_program or "TBD")
            worksheet.write(row, 6, student.get_current_status_display())
            worksheet.write(row, 7, float(student.current_balance or 0))
            worksheet.write(
                row, 8, student.last_enrollment_date.strftime("%Y-%m-%d") if student.last_enrollment_date else ""
            )

        # Adjust column widths
        worksheet.set_column(0, 0, 12)  # Student ID
        worksheet.set_column(1, 1, 25)  # Name
        worksheet.set_column(2, 2, 25)  # Khmer Name
        worksheet.set_column(3, 3, 30)  # Email
        worksheet.set_column(4, 4, 15)  # Phone
        worksheet.set_column(5, 5, 20)  # Program
        worksheet.set_column(6, 6, 10)  # Status
        worksheet.set_column(7, 7, 12)  # Balance
        worksheet.set_column(8, 8, 12)  # Enrollment

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="students_export.xlsx"'

        return response
