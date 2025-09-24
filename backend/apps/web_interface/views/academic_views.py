"""
Academic management views for the web interface.

This module contains views for courses, enrollment, grades, and academic records.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView, TemplateView

from apps.curriculum.models import Course
from apps.enrollment.models import ClassHeaderEnrollment
from apps.grading.models import ClassPartGrade, GradingScale
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader, ClassSession

from ..permissions import StaffRequiredMixin, TeacherRequiredMixin
from ..utils import is_htmx_request


class CourseListView(StaffRequiredMixin, ListView):
    """List view for courses with search and filtering."""

    model = Course
    template_name = "web_interface/pages/academic/course_list.html"
    context_object_name = "courses"
    paginate_by = 20

    def get_queryset(self):
        """Filter courses based on search parameters."""
        queryset = Course.objects.select_related("division", "major").annotate(
            enrollment_count=Count("classheader__enrollments")
        )

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(title_khmer__icontains=search) | Q(course_code__icontains=search)
            )

        # Division filtering
        division = self.request.GET.get("division")
        if division:
            queryset = queryset.filter(division_id=division)

        # Active/inactive filtering
        status = self.request.GET.get("status")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        return queryset.order_by("course_code")

    def get_template_names(self):
        """Return appropriate template for HTMX requests."""
        if is_htmx_request(self.request):
            return ["web_interface/pages/academic/course_list_content.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "page_title": _("Course Management"),
                "current_page": "courses",
                "search_query": self.request.GET.get("search", ""),
                "selected_division": self.request.GET.get("division", ""),
                "selected_status": self.request.GET.get("status", ""),
                "total_courses": len(context["courses"]),  # Use already-evaluated queryset
            }
        )
        return context


class EnrollmentManagementView(StaffRequiredMixin, TemplateView):
    """Enhanced enrollment dashboard with class cards and quick enrollment."""

    template_name = "web_interface/pages/academic/enrollment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current term or default term
        from apps.curriculum.models import Term

        current_term = Term.objects.filter(is_active=True).first()
        if not current_term:
            current_term = Term.objects.order_by("-start_date").first()

        # Get available terms for filter
        available_terms = Term.objects.order_by("-start_date")[:10]

        # Get classes for the current term with enrollment data and calculated statistics
        from django.db.models import Case, Count, F, IntegerField, Q, Sum, When

        classes_queryset = (
            ClassHeader.objects.filter(term=current_term if current_term else None)
            .select_related("course")
            .annotate(
                enrolled_count=Count(
                    "class_header_enrollments", filter=Q(class_header_enrollments__status="ENROLLED")
                ),
                seats_available=Case(
                    When(max_enrollment__gt=F("enrolled_count"), then=F("max_enrollment") - F("enrolled_count")),
                    default=0,
                    output_field=IntegerField(),
                ),
            )
            .order_by("course__code")
        )

        # Calculate all statistics in a single aggregate query
        stats = classes_queryset.aggregate(
            available_seats=Sum("seats_available"),
            nearly_full=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment") * 0.8)),
            full_classes=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment"))),
            total_enrolled=Sum("enrolled_count"),
        )

        # Convert None values to 0 for display
        stats = {key: value or 0 for key, value in stats.items()}

        # Cache the queryset by evaluating it once for display
        classes = list(classes_queryset)

        # Get recent enrollments
        recent_enrollments = ClassHeaderEnrollment.objects.select_related(
            "student__person", "class_header__course"
        ).order_by("-created_at")[:20]

        # Get pending enrollments
        pending_enrollments = (
            ClassHeaderEnrollment.objects.filter(status="ENROLLED")
            .select_related("student__person", "class_header__course")
            .order_by("-created_at")
        )

        context.update(
            {
                "page_title": _("Enrollment Management"),
                "current_page": "enrollment",
                "term": current_term,
                "available_terms": available_terms,
                "classes": classes,
                "stats": stats,
                "recent_enrollments": recent_enrollments,
                "pending_enrollments": pending_enrollments,
            }
        )
        return context


class EnrollmentWizardView(StaffRequiredMixin, TemplateView):
    """Multi-step enrollment wizard for guided enrollment process."""

    template_name = "web_interface/pages/enrollment/enrollment_wizard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from apps.curriculum.models import Term
        from apps.people.models import StudentProfile

        # Get active terms
        active_terms = Term.objects.filter(is_active=True).order_by("-start_date")
        if not active_terms:
            active_terms = Term.objects.order_by("-start_date")[:5]

        # Get recent students for quick selection
        recent_students = StudentProfile.objects.select_related("person").order_by("-created_at")[:20]

        context.update(
            {
                "page_title": _("Enrollment Wizard"),
                "active_terms": active_terms,
                "recent_students": recent_students,
            }
        )
        return context


class QuickEnrollmentModalView(StaffRequiredMixin, TemplateView):
    """Quick enrollment form modal."""

    template_name = "web_interface/pages/enrollment/quick_enrollment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from apps.curriculum.models import Term

        # Get current term
        current_term = Term.objects.filter(is_active=True).first()
        if not current_term:
            current_term = Term.objects.order_by("-start_date").first()

        # Get classes for current term
        if current_term:
            classes = (
                ClassHeader.objects.filter(term=current_term)
                .select_related("course")
                .annotate(
                    enrolled_count=Count(
                        "class_header_enrollments", filter=Q(class_header_enrollments__status="ENROLLED")
                    ),
                    seats_available=F("max_enrollment") - F("enrolled_count"),
                )
                .order_by("course__code")
            )
        else:
            classes = ClassHeader.objects.none()

        context.update(
            {
                "page_title": _("Quick Enrollment"),
                "current_term": current_term,
                "classes": classes,
            }
        )
        return context


class EnhancedClassCardsView(StaffRequiredMixin, TemplateView):
    """Enhanced class cards view for visual enrollment management."""

    template_name = "web_interface/pages/enrollment/enhanced_class_cards.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from apps.curriculum.models import Term

        # Get current term or default term
        current_term = Term.objects.filter(is_active=True).first()
        if not current_term:
            current_term = Term.objects.order_by("-start_date").first()

        # Get available terms for filter
        available_terms = Term.objects.order_by("-start_date")[:10]

        # Get classes for the current term with enrollment data
        if current_term:
            classes = (
                ClassHeader.objects.filter(term=current_term)
                .select_related("course")
                .annotate(
                    enrolled_count=Count(
                        "class_header_enrollments", filter=Q(class_header_enrollments__status="ENROLLED")
                    ),
                    seats_available=F("max_enrollment") - F("enrolled_count"),
                )
                .order_by("course__code")
            )
        else:
            classes = ClassHeader.objects.none()

        context.update(
            {
                "page_title": _("Enhanced Class Cards"),
                "current_term": current_term,
                "available_terms": available_terms,
                "classes": classes,
            }
        )
        return context


class GradeManagementView(TeacherRequiredMixin, TemplateView):
    """View for grade management by teachers."""

    template_name = "web_interface/pages/academic/grades.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get teacher's classes
        teacher_profile = None
        if hasattr(self.request.user, "person") and hasattr(self.request.user.person, "teacherprofile"):
            teacher_profile = self.request.user.person.teacherprofile

        if teacher_profile:
            # Get active classes for this teacher
            teacher_classes = (
                ClassHeader.objects.filter(teacher=teacher_profile, is_active=True)
                .select_related("course")
                .prefetch_related("enrollments__student__person")
            )

            # Get pending grades
            pending_grades = ClassPartGrade.objects.filter(
                enrollment__class_header__teacher=teacher_profile, final_grade__isnull=True
            ).select_related(
                "enrollment__student__person", "enrollment__class_header__course", "enrollment__class_header__term"
            )

            # Get grade statistics
            grade_stats = {
                "classes_taught": teacher_classes.count(),
                "total_students": ClassHeaderEnrollment.objects.filter(
                    class_header__teacher=teacher_profile, status="ENROLLED"
                ).count(),
                "pending_grades": pending_grades.count(),
                "graded_students": ClassPartGrade.objects.filter(
                    enrollment__class_header__teacher=teacher_profile, final_grade__isnull=False
                ).count(),
            }
        else:
            teacher_classes = ClassHeader.objects.none()
            pending_grades = ClassPartGrade.objects.none()
            grade_stats = {
                "classes_taught": 0,
                "total_students": 0,
                "pending_grades": 0,
                "graded_students": 0,
            }

        context.update(
            {
                "page_title": _("Grade Management"),
                "current_page": "grades",
                "teacher_classes": teacher_classes,
                "pending_grades": pending_grades[:10],  # Limit for display
                "grade_stats": grade_stats,
            }
        )
        return context


class GradeEntryView(TeacherRequiredMixin, DetailView):
    """View for entering grades for a specific class."""

    model = ClassHeader
    template_name = "web_interface/pages/academic/grade_entry.html"
    context_object_name = "class_header"

    def get_queryset(self):
        """Only allow teacher to access their own classes."""
        teacher_profile = None
        if hasattr(self.request.user, "person") and hasattr(self.request.user.person, "teacherprofile"):
            teacher_profile = self.request.user.person.teacherprofile

        if teacher_profile:
            return ClassHeader.objects.filter(teacher=teacher_profile).select_related(
                "course", "term", "teacher__person"
            )
        return ClassHeader.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_header = self.get_object()

        # Get enrolled students with their grades
        enrolled_students = (
            ClassHeaderEnrollment.objects.filter(class_header=class_header, status="ENROLLED")
            .select_related("student__person")
            .prefetch_related("classpartgrade_set")
        )

        # Get grading scale
        grading_scale = GradingScale.objects.first()  # Simplified - should be more specific

        context.update(
            {
                "page_title": _("Grade Entry - {}").format(class_header.course.title),
                "current_page": "grades",
                "enrolled_students": enrolled_students,
                "grading_scale": grading_scale,
            }
        )
        return context

    def get_enrollments(self):
        """Get enrollments for the current class."""
        class_header = self.get_object()
        return (
            ClassHeaderEnrollment.objects.filter(class_header=class_header, status="ENROLLED")
            .select_related("student__person")
            .order_by("student__person__last_name")
        )

    def post(self, request, *args, **kwargs):
        """Handle grade submission securely."""
        from ..forms.academic_forms import GradeEntryForm

        class_header = self.get_object()
        enrollments = self.get_enrollments()
        form = GradeEntryForm(request.POST, enrollments=enrollments)

        if form.is_valid():
            with transaction.atomic():
                enrollment_grades = form.get_enrollment_grades()

                for enrollment_id, grade_data in enrollment_grades.items():
                    try:
                        enrollment = ClassHeaderEnrollment.objects.get(id=enrollment_id, class_header=class_header)

                        # Create or update grade
                        grade, created = ClassPartGrade.objects.get_or_create(
                            enrollment=enrollment,
                            defaults={"final_grade": grade_data["grade"], "comments": grade_data["comment"]},
                        )
                        if not created:
                            grade.final_grade = grade_data["grade"]
                            grade.comments = grade_data["comment"]
                            grade.save()

                    except ClassHeaderEnrollment.DoesNotExist:
                        # Invalid enrollment ID - ignore (security protection)
                        continue

            messages.success(request, _("Grades have been saved successfully."))

            if is_htmx_request(request):
                return JsonResponse({"success": True, "message": _("Grades saved successfully")})

            return redirect("web_interface:grade-entry", pk=class_header.pk)
        else:
            # Form validation failed
            messages.error(request, _("Please correct the errors below."))

            # Re-render with form errors
            context = self.get_context_data()
            context["form_errors"] = form.errors
            return self.render_to_response(context)


class ScheduleView(LoginRequiredMixin, TemplateView):
    """View for class schedules."""

    template_name = "web_interface/pages/academic/schedules.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_role = self.request.session.get("current_role", "student")

        if current_role == "teacher":
            # Get teacher's schedule
            teacher_profile = None
            if hasattr(self.request.user, "person") and hasattr(self.request.user.person, "teacherprofile"):
                teacher_profile = self.request.user.person.teacherprofile

            if teacher_profile:
                class_sessions = (
                    ClassSession.objects.filter(class_header__teacher=teacher_profile)
                    .select_related("class_header__course", "room")
                    .order_by("day_of_week", "start_time")
                )
            else:
                class_sessions = ClassSession.objects.none()

        elif current_role == "student":
            # Get student's schedule
            student_profile = None
            if hasattr(self.request.user, "person") and hasattr(self.request.user.person, "studentprofile"):
                student_profile = self.request.user.person.studentprofile

            if student_profile:
                class_sessions = (
                    ClassSession.objects.filter(
                        class_header__class_header_enrollments__student=student_profile,
                        class_header__class_header_enrollments__status="ENROLLED",
                    )
                    .select_related("class_header__course", "room")
                    .distinct()
                    .order_by("day_of_week", "start_time")
                )
            else:
                class_sessions = ClassSession.objects.none()
        else:
            # Staff/Admin - show all schedules
            class_sessions = ClassSession.objects.select_related(
                "class_header__course", "class_header__teacher__person", "room"
            ).order_by("day_of_week", "start_time")

        context.update(
            {
                "page_title": _("Schedules"),
                "current_page": "schedules",
                "class_sessions": class_sessions,
                "current_role": current_role,
            }
        )
        return context


class TranscriptView(StaffRequiredMixin, TemplateView):
    """View for transcript management."""

    template_name = "web_interface/pages/academic/transcripts_fixed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get students eligible for transcripts
        eligible_students = (
            StudentProfile.objects.filter(current_status__in=["GRADUATED", "ACTIVE"])
            .select_related("person")
            .annotate(
                completed_courses=Count(
                    "class_header_enrollments", filter=Q(class_header_enrollments__status="COMPLETED")
                )
            )
            .order_by("-created_at")
        )

        # Get recent transcript requests (simplified - would need a proper transcript request model)
        recent_requests = eligible_students.filter(current_status="GRADUATED")[:10]

        # Transcript statistics
        transcript_stats = {
            "eligible_students": eligible_students.count(),
            "graduated_students": eligible_students.filter(current_status="GRADUATED").count(),
            "pending_requests": recent_requests.count(),
        }

        context.update(
            {
                "page_title": _("Transcript Management"),
                "current_page": "transcripts",
                "eligible_students": eligible_students[:20],
                "recent_requests": recent_requests,
                "transcript_stats": transcript_stats,
            }
        )
        return context


class StudentGradeView(TeacherRequiredMixin, DetailView):
    """View individual student grades in a class."""

    model = StudentProfile
    template_name = "web_interface/pages/academic/student_grades.html"
    context_object_name = "student"

    def get_queryset(self):
        """Optimize student queryset with related person data."""
        return StudentProfile.objects.select_related("person")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.get_object()

        # Get class header from URL parameter if provided
        class_header_id = self.kwargs.get("class_header_id")
        if class_header_id:
            try:
                class_header = ClassHeader.objects.get(id=class_header_id)
                # Get enrollment and grades for specific class
                enrollment = ClassHeaderEnrollment.objects.get(student=student, class_header=class_header)
                grades = ClassPartGrade.objects.filter(enrollment=enrollment)

                context.update(
                    {
                        "class_header": class_header,
                        "enrollment": enrollment,
                        "grades": grades,
                    }
                )
            except (ClassHeader.DoesNotExist, ClassHeaderEnrollment.DoesNotExist):
                messages.error(self.request, _("Class or enrollment not found."))

        # Get all student enrollments
        all_enrollments = (
            ClassHeaderEnrollment.objects.filter(student=student)
            .select_related("class_header__course")
            .prefetch_related("classpartgrade_set")
            .order_by("-created_at")
        )

        context.update(
            {
                "page_title": _("Student Grades - {}").format(student.person.full_name),
                "current_page": "grades",
                "all_enrollments": all_enrollments,
            }
        )
        return context


class EnrollmentApprovalView(StaffRequiredMixin, TemplateView):
    """View for approving/rejecting enrollment requests."""

    template_name = "web_interface/pages/academic/enrollment_approval.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get pending enrollments
        pending_enrollments = (
            ClassHeaderEnrollment.objects.filter(status="ENROLLED")
            .select_related("student__person", "class_header__course")
            .order_by("-created_at")
        )

        context.update(
            {
                "page_title": _("Enrollment Approval"),
                "current_page": "enrollment",
                "pending_enrollments": pending_enrollments,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        """Handle enrollment approval/rejection."""
        enrollment_id = request.POST.get("enrollment_id")
        action = request.POST.get("action")

        if enrollment_id and action in ["approve", "reject"]:
            try:
                enrollment = ClassHeaderEnrollment.objects.get(id=enrollment_id)

                if action == "approve":
                    enrollment.status = "ENROLLED"
                    message = _("Enrollment approved for {}").format(enrollment.student.person.full_name)
                else:
                    enrollment.status = "DROPPED"
                    message = _("Enrollment rejected for {}").format(enrollment.student.person.full_name)

                enrollment.save()
                messages.success(request, message)

            except ClassHeaderEnrollment.DoesNotExist:
                messages.error(request, _("Enrollment not found."))

        if is_htmx_request(request):
            return JsonResponse({"success": True, "message": _("Enrollment status updated")})

        return redirect("web_interface:enrollment-approval")


# Additional views for enhanced enrollment dashboard


def class_card_status(request, class_id):
    """HTMX endpoint to refresh class card status"""
    from django.shortcuts import get_object_or_404, render

    class_header = get_object_or_404(
        ClassHeader.objects.select_related("course", "teacher__person", "room").annotate(
            enrolled_count=Count("enrollments", filter=Q(enrollments__status="ENROLLED")),
            seats_available=F("max_enrollment") - F("enrolled_count"),
        ),
        id=class_id,
    )

    return render(request, "web_interface/partials/class_card_enhanced.html", {"class": class_header})


def class_roster_modal(request, class_id):
    """HTMX endpoint for class roster modal"""
    from django.shortcuts import get_object_or_404, render

    class_header = get_object_or_404(ClassHeader, id=class_id)
    enrolled_students = (
        ClassHeaderEnrollment.objects.filter(class_header=class_header, status="ENROLLED")
        .select_related("student__person")
        .order_by("student__person__full_name")
    )

    return render(
        request,
        "web_interface/modals/class_roster_modal.html",
        {"class": class_header, "enrolled_students": enrolled_students},
    )


def quick_enrollment_form(request, class_id):
    """HTMX endpoint for quick enrollment form"""
    from django.shortcuts import get_object_or_404, render

    class_header = get_object_or_404(ClassHeader, id=class_id)

    return render(request, "web_interface/modals/quick_enrollment_form.html", {"class": class_header})


@transaction.atomic
def process_quick_enrollment(request, class_id):
    """HTMX endpoint to process quick enrollment"""
    from django.http import HttpResponse, JsonResponse
    from django.shortcuts import get_object_or_404, render

    from apps.people.models import StudentProfile

    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests allowed"}, status=405)

    # Use select_for_update to lock the class record during enrollment
    class_header = get_object_or_404(ClassHeader.objects.select_for_update(), id=class_id)
    student_id = request.POST.get("student_id")
    notes = request.POST.get("notes", "")

    if not student_id:
        return render(
            request,
            "web_interface/partials/enrollment_message.html",
            {"message": _("Please select a student"), "type": "error"},
        )

    try:
        student = StudentProfile.objects.get(id=student_id)

        # Check if student is already enrolled
        existing_enrollment = ClassHeaderEnrollment.objects.filter(student=student, class_header=class_header).first()

        if existing_enrollment:
            return render(
                request,
                "web_interface/partials/enrollment_message.html",
                {"message": _("Student is already enrolled in this class"), "type": "warning"},
            )

        # Check class capacity with atomic count to prevent race conditions
        enrolled_count = ClassHeaderEnrollment.objects.filter(class_header=class_header, status="ENROLLED").count()

        if enrolled_count >= class_header.max_enrollment:
            return HttpResponse(
                '<div class="alert alert-danger">Class is full</div>',
                status=409,  # Conflict status
            )

        # Create enrollment (now safe from race conditions)
        enrollment = ClassHeaderEnrollment.objects.create(
            student=student, class_header=class_header, status="ENROLLED", notes=notes
        )

        # Track user for audit logging
        enrollment._current_user = request.user
        enrollment.save()

        messages.success(request, _("Student enrolled successfully"))

        return render(
            request,
            "web_interface/partials/enrollment_message.html",
            {
                "message": _(
                    "Successfully enrolled {} in {}".format(student.person.full_name, class_header.course.code)
                ),
                "type": "success",
            },
        )

    except StudentProfile.DoesNotExist:
        return render(
            request,
            "web_interface/partials/enrollment_message.html",
            {"message": _("Student not found"), "type": "error"},
        )
    except Exception as e:
        return render(
            request,
            "web_interface/partials/enrollment_message.html",
            {"message": _("Error enrolling student: {}").format(str(e)), "type": "error"},
        )
