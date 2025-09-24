# views.py
import csv
from io import BytesIO

import xlsxwriter
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render

from .models import Student


def student_search(request):
    """Main search page view"""
    context = {
        "total_students": Student.objects.count(),
        "active_students": Student.objects.filter(status="active").count(),
        "term_students": Student.objects.filter(enrolled_date__gte="2025-01-01").count(),  # Current term
    }
    return render(request, "students/search.html", context)


def student_search_results(request):
    """HTMX endpoint for search results"""
    # Start with all students
    queryset = Student.objects.all()

    # Apply filters
    if student_id := request.GET.get("student_id"):
        queryset = queryset.filter(student_id__icontains=student_id)

    if name := request.GET.get("name"):
        queryset = queryset.filter(
            Q(first_name__icontains=name) | Q(last_name__icontains=name) | Q(full_name__icontains=name)
        )

    if email := request.GET.get("email"):
        queryset = queryset.filter(email__icontains=email)

    if program := request.GET.get("program"):
        queryset = queryset.filter(program=program)

    if status := request.GET.get("status"):
        queryset = queryset.filter(status=status)

    if study_time := request.GET.get("study_time"):
        queryset = queryset.filter(study_time=study_time)

    if gender := request.GET.get("gender"):
        queryset = queryset.filter(gender=gender)

    if citizenship := request.GET.get("citizenship"):
        queryset = queryset.filter(citizenship=citizenship)

    # Age range
    if age_min := request.GET.get("age_min"):
        queryset = queryset.filter(age__gte=age_min)

    if age_max := request.GET.get("age_max"):
        queryset = queryset.filter(age__lte=age_max)

    # Balance range
    if balance_min := request.GET.get("balance_min"):
        queryset = queryset.filter(balance__gte=balance_min)

    if balance_max := request.GET.get("balance_max"):
        queryset = queryset.filter(balance__lte=balance_max)

    # Enrollment date range
    if enrolled_from := request.GET.get("enrolled_from"):
        queryset = queryset.filter(enrolled_date__gte=enrolled_from)

    if enrolled_to := request.GET.get("enrolled_to"):
        queryset = queryset.filter(enrolled_date__lte=enrolled_to)

    # Payment status
    if payment_status := request.GET.get("payment_status"):
        queryset = queryset.filter(payment_status=payment_status)

    # Checkbox filters
    if request.GET.get("missing_email"):
        # TODO: After data migration, this can be simplified to just Q(email__isnull=True)
        # Current complex filter handles legacy data inconsistencies
        queryset = queryset.filter(Q(email__isnull=True) | Q(email="") | Q(email="NULL") | Q(email="No email"))

    if request.GET.get("missing_phone"):
        queryset = queryset.filter(Q(phone__isnull=True) | Q(phone=""))

    if request.GET.get("has_invoices"):
        queryset = queryset.filter(invoices__isnull=False).distinct()

    # Order by most recent first
    queryset = queryset.order_by("-enrolled_date", "last_name", "first_name")

    # Pagination
    paginator = Paginator(queryset, 25)  # 25 students per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "students": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "result_count": page_obj.paginator.count,  # Optimized: use paginator count instead of redundant query
    }

    return render(request, "students/partials/search_results.html", context)


def student_export(request):
    """Export search results to CSV or Excel"""
    # Apply same filters as search (reuse the filtering logic)
    # ... (same filtering code as above)
    # Example: queryset = Student.objects.filter(...) should be defined here
    queryset = []  # Placeholder - should be replaced with actual filtering logic

    export_format = request.GET.get("export", "csv")

    if export_format == "excel":
        # Create Excel file
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        # Headers
        headers = ["Student ID", "Name", "Email", "Program", "Status", "Balance", "Enrolled Date"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # Data
        for row, student in enumerate(queryset, start=1):
            worksheet.write(row, 0, student.student_id)
            worksheet.write(row, 1, student.get_full_name())
            worksheet.write(row, 2, student.email or "")  # Clean: use empty string instead of "No email"
            worksheet.write(row, 3, student.program)
            worksheet.write(row, 4, student.status)
            worksheet.write(row, 5, float(student.balance))
            worksheet.write(row, 6, student.enrolled_date.strftime("%Y-%m-%d"))

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=students.xlsx"
        return response

    else:  # CSV
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=students.csv"

        writer = csv.writer(response)
        writer.writerow(["Student ID", "Name", "Email", "Program", "Status", "Balance", "Enrolled Date"])

        for student in queryset:
            writer.writerow(
                [
                    student.student_id,
                    student.get_full_name(),
                    student.email or "No email",
                    student.program,
                    student.status,
                    student.balance,
                    student.enrolled_date,
                ]
            )

        return response


def student_detail(request, pk):
    """View individual student details"""
    student = Student.objects.get(pk=pk)
    return render(request, "students/detail.html", {"student": student})


def student_edit(request, pk):
    """Edit student information"""
    # Your edit logic here
    pass


def student_send_message(request, pk):
    """Send message to student via HTMX"""
    if request.method == "POST":
        Student.objects.get(pk=pk)
        # Your messaging logic here
        return HttpResponse("Message sent!")


# urls.py
# from django.urls import path
#
# from . import views

urlpatterns = [
    path("students/", views.student_search, name="student_search"),
    path("students/results/", views.student_search_results, name="student_search_results"),
    path("students/export/", views.student_export, name="student_export"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:pk>/message/", views.student_send_message, name="student_send_message"),
]

# models.py (example)
# from django.db import models


# Example Student model class (commented out to avoid redefinition with imported Student)
# class Student(models.Model):
#     student_id = models.CharField(max_length=20, unique=True)
#     first_name = models.CharField(max_length=100)
#     last_name = models.CharField(max_length=100)
#     full_name = models.CharField(max_length=200)  # For combined names
#     email = models.EmailField(blank=True, null=True)
#     phone = models.CharField(max_length=20, blank=True, null=True)
#     program = models.CharField(max_length=100)
#     status = models.CharField(
#         max_length=20,
#         choices=[
#             ("active", "Active"),
#             ("inactive", "Inactive"),
#             ("graduated", "Graduated"),
#             ("suspended", "Suspended"),
#         ],
#     )
#     study_time = models.CharField(max_length=20, blank=True)
#     gender = models.CharField(
#         max_length=1,
#         choices=[
#             ("M", "Male"),
#             ("F", "Female"),
#             ("O", "Other"),
#         ],
#         blank=True,
#     )
#     age = models.IntegerField(blank=True, null=True)
#     citizenship = models.CharField(max_length=20, blank=True)
#     balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     payment_status = models.CharField(max_length=20, blank=True)
#     enrolled_date = models.DateField()
#
#     def get_full_name(self):
#         return f"{self.first_name} {self.last_name}"
#
#     def __str__(self):
#         return f"{self.student_id} - {self.get_full_name()}"
