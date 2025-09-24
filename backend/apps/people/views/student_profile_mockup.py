"""Student Profile Mockup Views."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import DetailView

from apps.people.models import StudentProfile


class StudentProfileByStudentIdMixin:
    """Mixin to lookup students by student_id instead of pk."""

    def get_object(self, queryset=None):
        """Override to use student_id from URL."""
        if queryset is None:
            queryset = self.get_queryset()

        student_id = self.kwargs.get("student_id")
        return get_object_or_404(queryset, student_id=student_id)


class StudentProfileMockupView(LoginRequiredMixin, DetailView):
    """Display the student profile mockup with vertical tabs."""

    model = StudentProfile
    template_name = "people/student_profile_mockup.html"
    context_object_name = "student"

    def get_context_data(self, **kwargs):
        """Add additional context for the mockup."""
        context = super().get_context_data(**kwargs)
        student = self.object

        # Add any additional context needed for the mockup
        context.update(
            {
                "page_title": f"Student Profile - {student.person.full_name}",
                "breadcrumbs": [
                    {"name": "Home", "url": "/"},
                    {"name": "Students", "url": "/people/students/"},
                    {"name": student.person.full_name, "active": True},
                ],
            },
        )

        return context


class StudentProfileTabView(LoginRequiredMixin, DetailView):
    """Handle HTMX tab content loading."""

    model = StudentProfile
    context_object_name = "student"

    def get_template_names(self):
        """Return the template for the requested tab."""
        tab = self.kwargs.get("tab", "overview")
        valid_tabs = [
            "overview",
            "demographics",
            "academic",
            "enrollment",
            "grades",
            "attendance",
            "finance",
            "documents",
            "activity",
        ]

        if tab not in valid_tabs:
            tab = "overview"

        return [f"people/partials/tab_{tab}.html"]

    def get_context_data(self, **kwargs):
        """Add tab-specific context."""
        context = super().get_context_data(**kwargs)
        tab = self.kwargs.get("tab", "overview")
        student = self.object

        # Common context for all tabs
        context["current_term"] = {"name": "Spring 2024", "id": 1}

        # Add tab-specific data based on the tab being loaded
        if tab == "overview":
            # Mock data for overview
            context.update(
                {
                    "current_enrollments": self._get_mock_current_enrollments(),
                    "degree_credits_required": 120,
                    "degree_progress_percentage": 62.5,
                    "current_term_gpa": Decimal("3.90"),
                    "current_term_credits": 15,
                    "expected_graduation_year": 2025,
                    "current_balance": Decimal("1250.00"),
                    "term_charges": Decimal("5500.00"),
                    "financial_aid_total": Decimal("4250.00"),
                    "payment_due_date": timezone.now() + timedelta(days=30),
                    "overall_attendance_rate": 94.5,
                    "classes_attended": 42,
                    "total_absences": 3,
                    "attendance_warnings": 1,
                    "recent_activities": self._get_mock_recent_activities(),
                    "upcoming_events": self._get_mock_upcoming_events(),
                },
            )

        elif tab == "demographics":
            context["emergency_contacts"] = student.person.emergency_contacts.all()
            context["phone_numbers"] = student.person.phone_numbers.all()

        elif tab == "academic":
            # Mock academic data
            context.update(
                {
                    "degree_requirements": self._get_mock_degree_requirements(),
                    "academic_history": self._get_mock_academic_history(),
                    "transfer_credits": (self._get_mock_transfer_credits() if student.is_transfer_student else None),
                    "total_transfer_credits": 24 if student.is_transfer_student else 0,
                },
            )

        elif tab == "enrollment":
            # Mock enrollment data
            context.update(
                {
                    "current_enrollments": self._get_mock_current_enrollments(),
                    "total_current_credits": 15,
                    "enrollment_history": self._get_mock_enrollment_history(),
                    "available_terms": [
                        {"id": 1, "name": "Spring 2024"},
                        {"id": 2, "name": "Fall 2023"},
                        {"id": 3, "name": "Spring 2023"},
                    ],
                    "registration_holds": [],  # Empty for now
                    "add_drop_history": self._get_mock_add_drop_history(),
                },
            )

        elif tab == "grades":
            # Mock grades data
            context.update(
                {
                    "total_credits_attempted": 90,
                    "current_term_gpa": Decimal("3.90"),
                    "current_term_credits": 15,
                    "major_gpa": Decimal("3.95"),
                    "major_credits": 45,
                    "quality_points": Decimal("346.5"),
                    "current_term_grades": self._get_mock_current_grades(),
                    "grade_history": self._get_mock_grade_history(),
                    "grade_distribution": {
                        "A": 18,
                        "A-": 12,
                        "B+": 8,
                        "B": 5,
                        "B-": 2,
                        "C+": 1,
                        "C": 0,
                    },
                    "total_courses": 46,
                    "repeated_courses": [],
                },
            )

        elif tab == "attendance":
            # Mock attendance data
            context.update(
                {
                    "overall_attendance_rate": 94.5,
                    "total_classes_attended": 42,
                    "total_absences": 3,
                    "total_tardies": 2,
                    "attendance_alerts": self._get_mock_attendance_alerts(),
                    "course_attendance": self._get_mock_course_attendance(),
                    "recent_attendance": self._get_mock_recent_attendance(),
                    "current_month": timezone.now(),
                    "total_attendance_records": 150,
                },
            )

        elif tab == "finance":
            # Mock financial data
            context.update(
                {
                    "current_balance": Decimal("1250.00"),
                    "total_charges": Decimal("25500.00"),
                    "total_payments": Decimal("24250.00"),
                    "financial_aid": Decimal("12000.00"),
                    "has_balance_due": True,
                    "payment_due_date": timezone.now() + timedelta(days=30),
                    "pending_charges_count": 2,
                    "total_payments_count": 8,
                    "active_aid_count": 3,
                    "active_payment_plan": False,
                    "tax_documents_count": 2,
                    "pending_refunds": 0,
                    "recent_transactions": self._get_mock_transactions(),
                    "term_charges": self._get_mock_term_charges(),
                    "term_total": Decimal("5500.00"),
                },
            )

        elif tab == "documents":
            # Mock document data
            context.update(
                {
                    "academic_docs_count": 12,
                    "financial_docs_count": 8,
                    "personal_docs_count": 5,
                    "application_docs_count": 7,
                    "forms_count": 4,
                    "other_docs_count": 2,
                    "recent_documents": self._get_mock_documents(),
                    "document_requirements": self._get_mock_document_requirements(),
                },
            )

        elif tab == "activity":
            # Mock activity log data
            context.update(
                {
                    "total_activities": 256,
                    "activities_this_month": 23,
                    "unique_users": 5,
                    "last_activity_days": 0,
                    "activity_timeline": self._get_mock_activity_timeline(),
                    "activity_categories": self._get_mock_activity_categories(),
                    "has_more_activities": True,
                },
            )

        return context

    # Mock data generation methods
    def _get_mock_current_enrollments(self):
        """Generate mock current enrollment data."""
        return [
            {
                "class_section": {
                    "course": {
                        "course_code": "CS101",
                        "title": "Introduction to Computer Science",
                    },
                    "meeting_pattern": "MWF 10:00-11:00 AM",
                    "room": {"full_name": "A-201"},
                    "primary_instructor": {"person": {"full_name": "Dr. Sarah Smith"}},
                    "current_enrollment": 25,
                    "capacity": 30,
                    "credits": 3,
                },
                "enrollment_status": "ENROLLED",
                "current_grade": "A-",
            },
            {
                "class_section": {
                    "course": {
                        "course_code": "MATH201",
                        "title": "Calculus II",
                    },
                    "meeting_pattern": "TTh 2:00-3:30 PM",
                    "room": {"full_name": "B-105"},
                    "primary_instructor": {"person": {"full_name": "Prof. John Davis"}},
                    "current_enrollment": 20,
                    "capacity": 25,
                    "credits": 4,
                },
                "enrollment_status": "ENROLLED",
                "current_grade": "B+",
            },
            {
                "class_section": {
                    "course": {
                        "course_code": "ENG102",
                        "title": "Academic Writing",
                    },
                    "meeting_pattern": "MWF 1:00-2:00 PM",
                    "room": {"full_name": "C-302"},
                    "primary_instructor": {"person": {"full_name": "Dr. Emily Johnson"}},
                    "current_enrollment": 18,
                    "capacity": 20,
                    "credits": 3,
                },
                "enrollment_status": "ENROLLED",
                "current_grade": "A",
            },
        ]

    def _get_mock_recent_activities(self):
        """Generate mock recent activity data."""
        return [
            {
                "description": "Grade posted for CS101 Midterm: A-",
                "timestamp": timezone.now() - timedelta(hours=2),
                "color": "blue",
            },
            {
                "description": "Payment received: $500.00",
                "timestamp": timezone.now() - timedelta(days=1, hours=8),
                "color": "green",
            },
            {
                "description": "Enrolled in MATH201 for Spring 2024",
                "timestamp": timezone.now() - timedelta(days=3),
                "color": "purple",
            },
        ]

    def _get_mock_upcoming_events(self):
        """Generate mock upcoming events."""
        return [
            {
                "title": "CS101 Project Due",
                "description": "Final project submission",
                "date": timezone.now() + timedelta(days=5),
                "icon": "fa-code",
                "color": "blue",
            },
            {
                "title": "Registration Opens",
                "description": "Fall 2024 course registration",
                "date": timezone.now() + timedelta(days=14),
                "icon": "fa-calendar-plus",
                "color": "green",
            },
            {
                "title": "Payment Due",
                "description": "Spring 2024 balance",
                "date": timezone.now() + timedelta(days=30),
                "icon": "fa-dollar-sign",
                "color": "red",
            },
        ]

    def _get_mock_degree_requirements(self):
        """Generate mock degree requirements."""
        return [
            {
                "category_name": "General Education",
                "description": "Core liberal arts requirements",
                "credits_required": 45,
                "credits_completed": 42,
                "progress_percentage": 93.3,
                "remaining_courses": ["PHIL 101"],
            },
            {
                "category_name": "Major Requirements",
                "description": "Computer Science major courses",
                "credits_required": 60,
                "credits_completed": 30,
                "progress_percentage": 50.0,
                "remaining_courses": ["CS301", "CS302", "CS401"],
            },
            {
                "category_name": "Electives",
                "description": "Free elective courses",
                "credits_required": 15,
                "credits_completed": 3,
                "progress_percentage": 20.0,
                "remaining_courses": [],
            },
        ]

    def _get_mock_academic_history(self):
        """Generate mock academic history."""
        return [
            {
                "term_name": "Fall 2023",
                "term_gpa": Decimal("3.85"),
                "credits_attempted": 16,
                "courses_count": 5,
                "honors": "Dean's List",
            },
            {
                "term_name": "Spring 2023",
                "term_gpa": Decimal("3.75"),
                "credits_attempted": 15,
                "courses_count": 5,
                "honors": None,
            },
            {
                "term_name": "Fall 2022",
                "term_gpa": Decimal("3.90"),
                "credits_attempted": 15,
                "courses_count": 5,
                "honors": "Dean's List",
            },
        ]

    def _get_mock_transfer_credits(self):
        """Generate mock transfer credits."""
        return [
            {
                "institution_name": "Community College",
                "original_course_code": "CIS 101",
                "credits": 3,
                "equivalent_course_code": "CS 101",
            },
            {
                "institution_name": "Community College",
                "original_course_code": "MAT 151",
                "credits": 4,
                "equivalent_course_code": "MATH 151",
            },
        ]

    def _get_mock_enrollment_history(self):
        """Generate mock enrollment history."""
        return [
            {
                "term": {"name": "Fall 2023"},
                "total_credits": 16,
                "term_gpa": Decimal("3.85"),
                "enrollments": [
                    {
                        "class_section": {
                            "course": {
                                "course_code": "CS201",
                                "title": "Data Structures",
                            },
                            "credits": 3,
                        },
                        "final_grade": "A",
                    },
                    {
                        "class_section": {
                            "course": {
                                "course_code": "MATH151",
                                "title": "Calculus I",
                            },
                            "credits": 4,
                        },
                        "final_grade": "A-",
                    },
                ],
            },
        ]

    def _get_mock_add_drop_history(self):
        """Generate mock add/drop history."""
        return [
            {
                "action_date": timezone.now() - timedelta(days=45),
                "action_type": "DROP",
                "course_code": "PHYS201",
                "course_title": "Physics I",
                "reason": "Schedule conflict",
            },
            {
                "action_date": timezone.now() - timedelta(days=44),
                "action_type": "ADD",
                "course_code": "CS210",
                "course_title": "Web Development",
                "reason": "Better fit for major",
            },
        ]

    def _get_mock_current_grades(self):
        """Generate mock current grades."""
        return [
            {
                "course_code": "CS101",
                "course_title": "Introduction to Computer Science",
                "credits": 3,
                "midterm_grade": "A-",
                "current_grade": "A-",
                "final_grade": None,
                "quality_points": None,
            },
            {
                "course_code": "MATH201",
                "course_title": "Calculus II",
                "credits": 4,
                "midterm_grade": "B",
                "current_grade": "B+",
                "final_grade": None,
                "quality_points": None,
            },
            {
                "course_code": "ENG102",
                "course_title": "Academic Writing",
                "credits": 3,
                "midterm_grade": "A",
                "current_grade": "A",
                "final_grade": None,
                "quality_points": None,
            },
        ]

    def _get_mock_grade_history(self):
        """Generate mock grade history."""
        return [
            {
                "term": {"id": 2, "name": "Fall 2023"},
                "credits": 16,
                "term_gpa": Decimal("3.85"),
                "courses": [
                    {
                        "course_code": "CS201",
                        "course_title": "Data Structures",
                        "credits": 3,
                        "final_grade": "A",
                        "quality_points": Decimal("12.0"),
                    },
                    {
                        "course_code": "MATH151",
                        "course_title": "Calculus I",
                        "credits": 4,
                        "final_grade": "A-",
                        "quality_points": Decimal("14.8"),
                    },
                ],
            },
        ]

    def _get_mock_attendance_alerts(self):
        """Generate mock attendance alerts."""
        return [
            {
                "course_code": "PHYS101",
                "message": "Attendance below 80%",
                "absences": 4,
            },
        ]

    def _get_mock_course_attendance(self):
        """Generate mock course attendance."""
        return [
            {
                "course_code": "CS101",
                "course_title": "Introduction to Computer Science",
                "instructor": "Dr. Sarah Smith",
                "meeting_pattern": "MWF 10:00-11:00 AM",
                "attendance_rate": 95.0,
                "present_count": 38,
                "absent_count": 2,
                "tardy_count": 0,
                "excused_count": 1,
                "recent_attendance": [
                    {"date": timezone.now() - timedelta(days=1), "status": "PRESENT"},
                    {"date": timezone.now() - timedelta(days=3), "status": "PRESENT"},
                    {"date": timezone.now() - timedelta(days=5), "status": "ABSENT"},
                ],
                "next_class": timezone.now() + timedelta(days=2, hours=10),
            },
        ]

    def _get_mock_recent_attendance(self):
        """Generate mock recent attendance records."""
        return [
            {
                "date": timezone.now() - timedelta(days=1),
                "course_code": "CS101",
                "course_title": "Introduction to Computer Science",
                "class_time": "10:00 AM",
                "status": "PRESENT",
                "notes": None,
            },
            {
                "date": timezone.now() - timedelta(days=1),
                "course_code": "MATH201",
                "course_title": "Calculus II",
                "class_time": "2:00 PM",
                "status": "PRESENT",
                "notes": None,
            },
        ]

    def _get_mock_transactions(self):
        """Generate mock financial transactions."""
        return [
            {
                "date": timezone.now() - timedelta(days=2),
                "description": "Online Payment - Credit Card",
                "type": "PAYMENT",
                "amount": Decimal("500.00"),
                "balance": Decimal("1250.00"),
            },
            {
                "date": timezone.now() - timedelta(days=10),
                "description": "Spring 2024 Tuition",
                "type": "CHARGE",
                "amount": Decimal("4500.00"),
                "balance": Decimal("1750.00"),
            },
            {
                "date": timezone.now() - timedelta(days=12),
                "description": "Merit Scholarship",
                "type": "AID",
                "amount": Decimal("2000.00"),
                "balance": Decimal("-2750.00"),
            },
        ]

    def _get_mock_term_charges(self):
        """Generate mock term charges."""
        return [
            {
                "description": "Tuition - Full Time",
                "category": "Tuition",
                "amount": Decimal("4500.00"),
            },
            {
                "description": "Student Activity Fee",
                "category": "Fees",
                "amount": Decimal("250.00"),
            },
            {
                "description": "Technology Fee",
                "category": "Fees",
                "amount": Decimal("150.00"),
            },
            {
                "description": "Health Services Fee",
                "category": "Fees",
                "amount": Decimal("200.00"),
            },
            {
                "description": "Lab Fee - CS101",
                "category": "Course Fees",
                "amount": Decimal("100.00"),
            },
            {
                "description": "Parking Permit",
                "category": "Other",
                "amount": Decimal("300.00"),
            },
        ]

    def _get_mock_documents(self):
        """Generate mock document data."""
        return [
            {
                "name": "Spring 2024 Schedule.pdf",
                "category": "Academic",
                "file_size": "245 KB",
                "uploaded_date": timezone.now() - timedelta(days=5),
                "status": "VERIFIED",
                "download_url": "#",
            },
            {
                "name": "Unofficial Transcript.pdf",
                "category": "Academic",
                "file_size": "512 KB",
                "uploaded_date": timezone.now() - timedelta(days=30),
                "status": "VERIFIED",
                "download_url": "#",
            },
            {
                "name": "2023 Tax Form 1098-T.pdf",
                "category": "Financial",
                "file_size": "189 KB",
                "uploaded_date": timezone.now() - timedelta(days=60),
                "status": "VERIFIED",
                "download_url": "#",
            },
        ]

    def _get_mock_document_requirements(self):
        """Generate mock document requirements."""
        return [
            {
                "document_type": "Health Insurance Verification",
                "due_date": timezone.now() + timedelta(days=15),
            },
            {
                "document_type": "FERPA Release Form",
                "due_date": timezone.now() + timedelta(days=30),
            },
        ]

    def _get_mock_activity_timeline(self):
        """Generate mock activity timeline."""
        today = timezone.now()
        return [
            {
                "date": today,
                "activities": [
                    {
                        "type": "academic",
                        "icon": "fa-graduation-cap",
                        "color": "blue",
                        "title": "Grade Posted",
                        "description": "CS101 Midterm grade posted: A-",
                        "time": today.replace(hour=14, minute=30),
                        "performed_by": "Dr. Sarah Smith",
                        "details": {"Course": "CS101", "Grade": "A-"},
                    },
                    {
                        "type": "financial",
                        "icon": "fa-dollar-sign",
                        "color": "green",
                        "title": "Payment Received",
                        "description": "Online payment processed successfully",
                        "time": today.replace(hour=10, minute=15),
                        "performed_by": "System",
                        "details": {"Amount": "$500.00", "Method": "Credit Card"},
                    },
                ],
            },
            {
                "date": today - timedelta(days=1),
                "activities": [
                    {
                        "type": "enrollment",
                        "icon": "fa-book",
                        "color": "purple",
                        "title": "Course Enrolled",
                        "description": "Successfully enrolled in MATH201",
                        "time": (today - timedelta(days=1)).replace(hour=16, minute=45),
                        "performed_by": "Student",
                        "details": {"Course": "MATH201", "Credits": "4"},
                    },
                ],
            },
        ]

    def _get_mock_activity_categories(self):
        """Generate mock activity category breakdown."""
        return [
            {
                "name": "Academic",
                "icon": "fa-graduation-cap",
                "color": "blue",
                "count": 85,
                "percentage": 33,
            },
            {
                "name": "Financial",
                "icon": "fa-dollar-sign",
                "color": "green",
                "count": 65,
                "percentage": 25,
            },
            {
                "name": "Enrollment",
                "icon": "fa-book",
                "color": "purple",
                "count": 52,
                "percentage": 20,
            },
            {
                "name": "Profile Updates",
                "icon": "fa-user",
                "color": "orange",
                "count": 31,
                "percentage": 12,
            },
            {
                "name": "System",
                "icon": "fa-cog",
                "color": "gray",
                "count": 23,
                "percentage": 10,
            },
        ]


class StudentProfileByStudentIdView(StudentProfileByStudentIdMixin, StudentProfileMockupView):
    """Student profile mockup accessed by student_id - TEST ONLY."""

    def get_context_data(self, **kwargs):
        """Override to set student_id context."""
        context = super().get_context_data(**kwargs)
        context["use_student_id_urls"] = True
        context["student_id"] = self.object.student_id
        return context


class StudentProfileTabByStudentIdView(StudentProfileByStudentIdMixin, StudentProfileTabView):
    """Student profile tab content accessed by student_id - TEST ONLY."""

    pass
