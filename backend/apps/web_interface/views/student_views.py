"""
Simplified student management views for the web interface.

Focus on performance with minimal complexity.
"""

from django.contrib import messages
from django.db.models import Prefetch
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.common.services.student_search import StudentSearchService
from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment
from apps.people.forms import StudentProfileForm
from apps.people.models import StudentProfile

from ..performance import QueryOptimizer
from ..permissions import StaffRequiredMixin
from ..utils import is_htmx_request


class StudentListView(StaffRequiredMixin, ListView):
    """Simplified student list view with basic search."""

    model = StudentProfile
    template_name = "web_interface/pages/students/student_list.html"
    context_object_name = "students"
    paginate_by = 50  # Increased for better performance

    def get_queryset(self):
        """Get students with optimized queries using centralized search service."""
        # Use centralized search service for consistent search logic
        queryset = StudentSearchService.get_optimized_search_queryset(
            query_params=self.request.GET.dict(),
            for_list_view=True,
            limit=None,  # Pagination handles limiting
        )

        # Additional optimization for list view
        queryset = QueryOptimizer.optimize_student_queryset(queryset, for_list=True)

        # Order by most recently active
        return queryset.order_by("-last_enrollment_date", "-created_at")

    def get_template_names(self):
        """Return appropriate template for HTMX requests."""
        if is_htmx_request(self.request):
            return ["web_interface/pages/students/student_list_content.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add minimal context for rendering
        context.update(
            {
                "page_title": _("Students"),
                "current_page": "students",
                "search_query": self.request.GET.get("search", ""),
                "selected_status": self.request.GET.get("status", ""),
                "status_choices": StudentProfile.Status.choices,
            }
        )
        return context


class StudentDetailView(StaffRequiredMixin, DetailView):
    """Detail view for individual student."""

    model = StudentProfile
    template_name = "web_interface/pages/students/student_detail.html"
    context_object_name = "student"

    def get_queryset(self):
        """Optimize queries with related data."""
        return StudentProfile.objects.select_related("person")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get related objects with proper queries to avoid slice issues
        recent_enrollments = (
            ClassHeaderEnrollment.objects.filter(
                student=self.object, is_deleted=False
            )
            .select_related("class_header__course", "class_header__term")
            .order_by("-class_header__term__start_date")[:10]
        )

        recent_programs = (
            ProgramEnrollment.objects.filter(
                student=self.object, is_deleted=False
            )
            .select_related("program")
            .order_by("-created_at")[:5]
        )

        context.update(
            {
                "page_title": f"Student: {self.object.person.full_name}",
                "current_page": "students",
                "recent_enrollments": recent_enrollments,
                "recent_programs": recent_programs,
            }
        )
        return context


class StudentCreateView(StaffRequiredMixin, CreateView):
    """Create new student registration."""

    model = StudentProfile
    form_class = StudentProfileForm
    template_name = "web_interface/pages/students/student_form.html"
    success_url = reverse_lazy("web_interface:student-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": _("Register New Student"),
                "current_page": "students",
            }
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Student registered successfully."))
        return super().form_valid(form)


class StudentUpdateView(StaffRequiredMixin, UpdateView):
    """Update student information."""

    model = StudentProfile
    form_class = StudentProfileForm
    template_name = "web_interface/pages/students/student_form.html"

    def get_success_url(self):
        return reverse_lazy("web_interface:student-detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": f"Edit: {self.object.person.full_name}",
                "current_page": "students",
            }
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Student information updated successfully."))
        return super().form_valid(form)


class StudentEnrollmentView(StaffRequiredMixin, DetailView):
    """View for managing student enrollments."""

    model = StudentProfile
    template_name = "web_interface/pages/students/student_enrollment.html"
    context_object_name = "student"

    def get_queryset(self):
        """Get student with enrollment data."""
        return StudentProfile.objects.select_related("person").prefetch_related(
            "program_enrollments__program", "class_header_enrollments__class_header__course"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": f"Enrollments: {self.object.person.full_name}",
                "current_page": "students",
            }
        )
        return context


class StudentSearchView(StaffRequiredMixin, ListView):
    """HTMX-powered student search endpoint."""

    model = StudentProfile
    template_name = "web_interface/components/student_search_results.html"
    context_object_name = "students"
    paginate_by = 20

    def get_queryset(self):
        """Search students efficiently using centralized service."""
        query = self.request.GET.get("q", "").strip()

        if not query:
            return StudentProfile.objects.none()

        # Use centralized search service with query parameter mapping
        return StudentSearchService.quick_search(
            search_term=query,
            limit=20,
            active_only=False,  # Don't filter by active status for general search
        )

    def get(self, request, *args, **kwargs):
        """Return JSON for AJAX requests."""
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            students = self.get_queryset()
            data = [
                {
                    "id": s.id,
                    "student_id": s.student_id,
                    "name": s.person.full_name,
                    "email": s.person.school_email or s.person.personal_email,
                }
                for s in students
            ]
            return JsonResponse({"results": data})
        return super().get(request, *args, **kwargs)


def student_quick_search(request):
    """HTMX endpoint for student search with instant results"""
    from django.shortcuts import render

    query = request.GET.get("q", "")

    if len(query) < 2:
        return render(request, "web_interface/partials/search_empty.html")

    # Use centralized search service for consistent search logic
    students = StudentSearchService.quick_search(search_term=query, limit=10, active_only=False)

    return render(request, "web_interface/partials/student_results.html", {"students": students, "query": query})


def student_search_for_enrollment(request):
    """HTMX endpoint for student search in enrollment modal"""
    from django.shortcuts import render

    query = request.GET.get("student_search", "")

    if len(query) < 2:
        return render(
            request, "web_interface/partials/student_results_enrollment.html", {"students": [], "query": query}
        )

    # Use centralized search service for consistent search logic
    # Note: This search includes phone field which may need special handling in the service
    students = StudentSearchService.quick_search(
        search_term=query,
        limit=10,
        active_only=False,
        include_phone=True,  # Pass flag to include phone search if service supports it
    )

    return render(
        request, "web_interface/partials/student_results_enrollment.html", {"students": students, "query": query}
    )
