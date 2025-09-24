"""Scheduling app views with real-time data integration and HTMX support.

This module provides web views for the scheduling system including:
- Interactive scheduling dashboard with term-based statistics
- Class management with filtering, search, and detail views
- Term selection and session management
- Real-time updates via HTMX endpoints
- Permission-based access control for scheduling operations

Key features:
- Term-aware context management with intelligent defaults
- Real-time statistics and capacity utilization tracking
- Advanced filtering and search capabilities
- Responsive design with mobile-first approach
- Integration with curriculum, enrollment, and grading systems
"""

import json
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Count, F, Prefetch, Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.curriculum.models import Term

from .models import ClassHeader


class SchedulingBaseMixin(LoginRequiredMixin):
    """Base mixin for scheduling views providing common context and permissions."""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Add common scheduling context to all views."""
        context = super().get_context_data(**kwargs)

        # Get current term (either from session, URL param, or latest active term)
        current_term = self.get_current_term()
        context["current_term"] = current_term

        context.update(self.get_term_selector_context(current_term))

        return context

    def get_current_term(self) -> Term:
        """Get the current term for the scheduling context."""
        # Check if term is specified in the request
        term_id = self.request.GET.get("term") or self.request.session.get("current_term_id")

        if term_id:
            try:
                term = Term.objects.get(id=term_id, is_deleted=False)
                # Ensure the selected term is appropriate for scheduling (not too old)
                today = timezone.now().date()
                if term.end_date >= today - timezone.timedelta(days=7):  # Allow recently ended terms
                    return term
            except (Term.DoesNotExist, ValueError):
                pass

        # Fall back to most appropriate term for scheduling
        today = timezone.now().date()

        # First priority: Currently active terms
        active_term = (
            Term.objects.filter(
                is_deleted=False,
                start_date__lte=today,
                end_date__gte=today,
            )
            .order_by("start_date")
            .first()
        )

        if active_term:
            return active_term

        # Second priority: Terms starting soon (next 2 months)
        upcoming_term = (
            Term.objects.filter(
                is_deleted=False,
                start_date__gt=today,
                start_date__lte=today + timezone.timedelta(days=60),
            )
            .order_by("start_date")
            .first()
        )

        if upcoming_term:
            return upcoming_term

        # Last resort: Most recent term (for initial setup scenarios)
        return list(Term.objects.filter(is_deleted=False)).order_by("-start_date").first()

    def get_term_selector_context(self, current_term: Term) -> dict[str, Any]:
        """Get context data for the term selector component - focused on scheduling-relevant terms."""
        today = timezone.now().date()

        # Current terms: Active now or starting very soon (within 2 weeks)
        # These are terms where scheduling work is most relevant
        current_terms = Term.objects.filter(
            is_deleted=False,
            start_date__lte=today + timezone.timedelta(days=14),  # Started or starting very soon
            end_date__gte=today - timezone.timedelta(days=3),  # Recently ended (grace period)
        ).order_by("start_date")

        # Future terms: Starting in the near future (next 6 months)
        # These are terms that need scheduling preparation
        future_terms = Term.objects.filter(
            is_deleted=False,
            start_date__gt=today + timezone.timedelta(days=14),  # Starting after the "current" window
            start_date__lte=today + timezone.timedelta(days=180),  # Within 6 months
        ).order_by("start_date")[:8]  # Limit to next 8 future terms

        return {
            "current_terms": current_terms,
            "future_terms": future_terms,
        }

    def _calculate_term_stats(self, term) -> dict[str, Any]:
        """Shared utility method to calculate dashboard statistics for a term."""
        classes_qs = ClassHeader.objects.filter(term=term, is_deleted=False)
        total_classes = classes_qs.count()
        active_classes = classes_qs.filter(status=ClassHeader.ClassStatus.ACTIVE).count()

        # Calculate active percentage
        active_percentage = round((active_classes / total_classes * 100) if total_classes > 0 else 0)

        # Get enrollment statistics (once enrollment integration is complete)
        total_enrollments = 0
        capacity_utilization = 0

        # For now, calculate basic capacity utilization from class headers
        if total_classes > 0:
            total_capacity = sum(cls.max_enrollment for cls in classes_qs)
            # Calculate actual enrollment from enrollment models
            try:
                from apps.enrollment.models import ClassHeaderEnrollment

                total_enrolled = ClassHeaderEnrollment.objects.filter(
                    class_header__in=classes_qs, status="ENROLLED"
                ).count()
            except ImportError:
                # Fallback if enrollment models not available
                total_enrolled = 0
            capacity_utilization = round((total_enrolled / total_capacity * 100) if total_capacity > 0 else 0)
            total_enrollments = total_enrolled

        return {
            "total_classes": total_classes,
            "active_classes": active_classes,
            "active_percentage": active_percentage,
            "total_enrollments": total_enrollments,
            "avg_capacity_utilization": capacity_utilization,
        }


class SchedulingDashboardView(SchedulingBaseMixin, TemplateView):
    """Dashboard view for scheduling with real statistics and data."""

    template_name = "scheduling/dashboard.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        current_term = context["current_term"]

        if current_term:
            # Get real statistics for the current term
            context["stats"] = self.get_dashboard_stats(current_term)
            context["recent_classes"] = self.get_recent_classes(current_term)
            context["alerts"] = self.get_dashboard_alerts(current_term)
        else:
            # Fallback if no term available
            context["stats"] = {
                "total_classes": 0,
                "active_classes": 0,
                "active_percentage": 0,
                "total_enrollments": 0,
                "avg_capacity_utilization": 0,
            }
            context["recent_classes"] = []
            context["alerts"] = []

        return context

    def get_dashboard_stats(self, term: Term) -> dict[str, Any]:
        """Calculate real dashboard statistics for the term."""
        return self._calculate_term_stats(term)

    def get_recent_classes(self, term: Term) -> QuerySet[ClassHeader]:
        """Get recently updated classes for the dashboard."""
        return (
            ClassHeader.objects.filter(term=term, is_deleted=False)
            .select_related("course", "term")
            .order_by("-updated_at")[:6]
        )

    def get_dashboard_alerts(self, term: Term) -> list[dict[str, str]]:
        """Generate dashboard alerts and notifications."""
        alerts = []

        # Check for classes at capacity
        try:
            from django.db.models import Count, F

            full_classes = (
                ClassHeader.objects.filter(term=term, is_deleted=False)
                .annotate(
                    enrollment_count=Count(
                        "class_header_enrollments", filter=models.Q(class_header_enrollments__status="ENROLLED")
                    )
                )
                .filter(max_enrollment__lte=F("enrollment_count"))
            )
        except ImportError:
            # Fallback if enrollment models not available
            full_classes = ClassHeader.objects.none()

        if full_classes.exists():
            alerts.append(
                {
                    "type": "warning",
                    "title": "Classes at Capacity",
                    "message": f"{full_classes.count()} classes are at or near capacity.",
                },
            )

        # Check for classes without teachers
        unassigned_classes = ClassHeader.objects.filter(
            term=term,
            is_deleted=False,
            status=ClassHeader.ClassStatus.SCHEDULED,
            class_sessions__class_parts__teacher__isnull=True,
        ).distinct()

        if unassigned_classes.exists():
            alerts.append(
                {
                    "type": "error",
                    "title": "Unassigned Teachers",
                    "message": f"{unassigned_classes.count()} classes need teacher assignments.",
                },
            )

        return alerts


class SchedulingClassListView(SchedulingBaseMixin, ListView):
    """List view for classes with filtering and search capabilities."""

    model = ClassHeader
    template_name = "scheduling/class_list.html"
    context_object_name = "classes"
    paginate_by = 20

    def get_queryset(self) -> QuerySet[ClassHeader]:
        """Get filtered list of classes for the current term."""
        current_term = self.get_current_term()
        if not current_term:
            return ClassHeader.objects.none()

        qs = (
            ClassHeader.objects.filter(term=current_term, is_deleted=False)
            .select_related("course", "term", "combined_class_instance")
            .prefetch_related("class_sessions__class_parts")
            .order_by("course__code", "section_id")
        )

        # Apply filters from request parameters
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        time_of_day = self.request.GET.get("time")
        if time_of_day:
            qs = qs.filter(time_of_day=time_of_day)

        class_type = self.request.GET.get("type")
        if class_type:
            qs = qs.filter(class_type=class_type)

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(
                Q(course__code__icontains=search)
                | Q(course__title__icontains=search)
                | Q(section_id__icontains=search),
            )

        return qs

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "view_mode": self.request.GET.get("view", "grid"),
                "status_choices": ClassHeader.ClassStatus.choices,
                "time_choices": ClassHeader.TimeOfDay.choices,
                "type_choices": ClassHeader.ClassType.choices,
                "current_filters": {
                    "status": self.request.GET.get("status", ""),
                    "time": self.request.GET.get("time", ""),
                    "type": self.request.GET.get("type", ""),
                    "search": self.request.GET.get("search", ""),
                },
            },
        )

        return context


class SchedulingClassDetailView(SchedulingBaseMixin, DetailView):
    """Detail view for individual classes."""

    model = ClassHeader
    template_name = "scheduling/class_detail.html"
    context_object_name = "class"

    def get_queryset(self) -> QuerySet[ClassHeader]:
        """Get class with related data."""
        return (
            ClassHeader.objects.filter(is_deleted=False)
            .select_related("course", "term", "combined_class_instance")
            .prefetch_related(
                "class_sessions__class_parts__teacher",
                "class_sessions__class_parts__room",
                "class_sessions__class_parts__textbooks",
            )
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Add enrollment and performance statistics
        context.update(
            {
                "waitlist_count": 0,  # Will be updated when enrollment integration is complete
                "attendance_rate": 0,  # Will be updated when attendance integration is complete
                "avg_grade": None,  # Will be updated when grading integration is complete
            },
        )

        return context


class SetTermView(SchedulingBaseMixin, TemplateView):
    """HTMX endpoint to set the current term and refresh content."""

    def get(self, request: HttpRequest, term_id: int) -> HttpResponse:
        """Set the current term in session and redirect to dashboard."""
        try:
            get_object_or_404(Term, id=term_id, is_deleted=False)
            request.session["current_term_id"] = term_id

            # If this is an HTMX request, return updated content
            if request.headers.get("HX-Request"):
                return redirect("scheduling:dashboard")

            # Regular request, redirect to dashboard
            return redirect("scheduling:dashboard")

        except Term.DoesNotExist:
            if request.headers.get("HX-Request"):
                return HttpResponse("Term not found", status=404)
            return redirect("scheduling:dashboard")


class DashboardStatsView(SchedulingBaseMixin, TemplateView):
    """HTMX endpoint for refreshing dashboard statistics."""

    template_name = "scheduling/components/dashboard_stats.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        current_term = context["current_term"]

        if current_term:
            # Reuse the stats logic without creating a new view instance
            context["stats"] = self._get_dashboard_stats(current_term)

        return context

    def _get_dashboard_stats(self, term) -> dict[str, Any]:
        """Calculate dashboard statistics for the term (extracted from SchedulingDashboardView)."""
        return self._calculate_term_stats(term)


# Base placeholder view for routes that need implementation
class SchedulingPlaceholderView(SchedulingBaseMixin, TemplateView):
    """Base placeholder view that redirects to dashboard with a message."""

    template_name = "scheduling/dashboard.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["placeholder_message"] = getattr(self, "placeholder_message", "This feature is coming soon!")
        return context


class SchedulingEnrollmentsView(SchedulingPlaceholderView):
    """Placeholder view for enrollment management."""

    placeholder_message = "Enrollment management feature is coming soon!"


class SchedulingScheduleView(SchedulingPlaceholderView):
    """Placeholder view for schedule grid/calendar."""

    placeholder_message = "Schedule grid/calendar view is coming soon!"


class SchedulingReportsView(SchedulingPlaceholderView):
    """Placeholder view for reporting."""

    placeholder_message = "Reporting features are coming soon!"


class SchedulingArchiveView(SchedulingPlaceholderView):
    """Placeholder view for archived terms."""

    placeholder_message = "Term archive view is coming soon!"


# ========== CLASS ENROLLMENT DISPLAY SYSTEM ==========


class ClassScheduleView(LoginRequiredMixin, TemplateView):
    """Main view for the class schedule page."""

    template_name = "scheduling/class_schedule.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Import ClassHeader at method level

        # Get term ID parameter or use most recent active term with classes
        term_id = self.request.GET.get("term_id")

        if term_id:
            try:
                active_term = Term.objects.get(id=term_id, is_active=True)
            except (Term.DoesNotExist, ValueError):
                active_term = None
        else:
            active_term = None

        # If no specific term or term not found, find most recent term with classes
        if not active_term:
            # Find terms that have classes scheduled
            terms_with_classes = (
                Term.objects.filter(is_active=True, class_headers__isnull=False, class_headers__is_deleted=False)
                .distinct()
                .order_by("-start_date")[:10]
            )

            active_term = terms_with_classes.first() if terms_with_classes else None

        context["active_term"] = active_term
        context["user"] = self.request.user

        # Get available terms with classes for selection
        available_terms = (
            Term.objects.filter(is_active=True, class_headers__isnull=False, class_headers__is_deleted=False)
            .distinct()
            .order_by("-start_date")[:20]
        )  # Most recent 20 terms with classes

        context["available_terms"] = available_terms

        return context


class ClassDataAPIView(View):
    """API endpoint for fetching class data with proper session structure."""

    def get(self, request):
        # Import ClassHeader at the method level
        from apps.scheduling.models import ClassHeader

        # Get parameters
        term_id = request.GET.get("term_id")
        prefix = request.GET.get("prefix", "all")
        view_filter = request.GET.get("filter", "all")
        search = request.GET.get("search", "")

        # Get the specific term
        try:
            if term_id:
                term = Term.objects.get(id=term_id, is_active=True)
            else:
                # If no term specified, get most recent term with classes
                terms_with_classes = (
                    Term.objects.filter(is_active=True, class_headers__isnull=False, class_headers__is_deleted=False)
                    .distinct()
                    .order_by("-start_date")
                )

                term = terms_with_classes.first()
                if not term:
                    return JsonResponse({"error": "No terms with classes found"}, status=404)

        except (Term.DoesNotExist, ValueError):
            return JsonResponse({"error": "Term not found"}, status=404)

        # Build queryset with optimized prefetching
        queryset = (
            ClassHeader.objects.filter(term=term, status__in=["ACTIVE", "SCHEDULED", "DRAFT"], is_deleted=False)
            .select_related("course", "term", "combined_class_instance", "paired_with")
            .prefetch_related(
                Prefetch("class_sessions", queryset=self.get_class_sessions_queryset().order_by("session_number")),
                "combined_class_instance__class_headers__course",
            )
        )

        # Apply prefix filter
        if prefix != "all":
            queryset = queryset.filter(course__code__istartswith=prefix)

        # Apply view filter
        if view_filter == "available":
            # Use annotation for current enrollment
            queryset = queryset.annotate(
                current_enrollment=Count(
                    "class_header_enrollments", filter=Q(class_header_enrollments__status="ENROLLED")
                )
            ).filter(current_enrollment__lt=F("max_enrollment"))
        elif view_filter == "full":
            queryset = queryset.annotate(
                current_enrollment=Count(
                    "class_header_enrollments", filter=Q(class_header_enrollments__status="ENROLLED")
                )
            ).filter(current_enrollment__gte=F("max_enrollment"))

        # Apply search filter
        if search:
            search_query = Q()

            # Search in course fields
            search_query |= Q(course__code__icontains=search)
            search_query |= Q(course__title__icontains=search)
            search_query |= Q(course__short_name__icontains=search)

            # Search in teacher names through sessions
            search_query |= Q(class_sessions__class_parts__teacher__user__first_name__icontains=search)
            search_query |= Q(class_sessions__class_parts__teacher__user__last_name__icontains=search)

            # Search in room codes
            search_query |= Q(class_sessions__class_parts__room__code__icontains=search)

            queryset = queryset.filter(search_query).distinct()

        # Serialize classes
        classes_data = []
        for cls in queryset:
            classes_data.append(self.serialize_class(cls))

        # Calculate statistics
        stats = self.calculate_stats(classes_data)

        return JsonResponse(
            {
                "classes": classes_data,
                "stats": stats,
                "term": {
                    "id": term.id,
                    "name": str(term),
                    "type": term.term_type,
                },
            }
        )

    def get_class_sessions_queryset(self):
        """Get optimized queryset for class sessions."""
        from .models import ClassSession

        return ClassSession.objects.prefetch_related(Prefetch("class_parts", queryset=self.get_class_parts_queryset()))

    def get_class_parts_queryset(self):
        """Get optimized queryset for class parts."""
        from .models import ClassPart

        return ClassPart.objects.select_related("teacher", "room")

    def serialize_class(self, cls):
        """Serialize ClassHeader with session-based structure."""
        # Get current enrollment count
        current_enrollment = cls.enrollment_count if hasattr(cls, "enrollment_count") else 0

        # If annotated, use that instead
        if hasattr(cls, "current_enrollment"):
            current_enrollment = cls.current_enrollment

        data = {
            "id": cls.id,
            "course_code": cls.course.code,
            "course_title": cls.course.title,
            "short_name": getattr(cls.course, "short_name", ""),
            "section_id": cls.section_id,
            "time_of_day": cls.time_of_day,
            "class_type": cls.class_type,
            "status": cls.status,
            "max_enrollment": cls.max_enrollment,
            "current_enrollment": current_enrollment,
            "is_extended": self.is_extended_class(cls),
        }

        # Add tier for reading classes
        if cls.class_type == "READING" and hasattr(cls, "reading_class"):
            data["tier"] = cls.reading_class.get_tier_display()

        # Handle combined classes
        if cls.combined_class_instance:
            # Get all course codes in the combination
            combined_courses = []
            for header in cls.combined_class_instance.class_headers.all():
                combined_courses.append(header.course.code)
            data["combined_courses"] = sorted(combined_courses)

        # Determine if this is an IEAP class
        is_ieap = self.is_ieap_class(cls)

        if is_ieap:
            # IEAP: Serialize sessions with their parts
            data["sessions"] = []
            for session in cls.class_sessions.all():
                session_data = {
                    "session_number": session.session_number,
                    "session_name": session.session_name or f"Session {session.session_number}",
                    "parts": [],
                }

                # For IEAP, use proper session names
                if session.session_number == 1:
                    session_data["session_name"] = "First Session"
                elif session.session_number == 2:
                    session_data["session_name"] = "Second Session"

                for part in session.class_parts.all():
                    session_data["parts"].append(self.serialize_part(part))

                data["sessions"].append(session_data)
        else:
            # Non-IEAP: Get the single session
            session = cls.class_sessions.first()
            if session:
                parts = list(session.class_parts.all())

                # Multi-part language programs (EHSS, GESL, EXPRESS)
                if len(parts) > 1 or self.is_language_program(cls):
                    data["parts"] = [self.serialize_part(p) for p in parts]

                # For all non-IEAP classes, also provide flattened info
                # This helps with display in collapsed view
                if parts:
                    # Collect info from all parts
                    all_teachers = []
                    all_rooms = []
                    all_days = set()
                    all_times = set()

                    for part in parts:
                        if part.teacher:
                            teacher_name = f"{part.teacher.user.first_name} {part.teacher.user.last_name}".strip()
                            if not teacher_name:
                                teacher_name = part.teacher.user.email
                            all_teachers.append(teacher_name)

                        if part.room:
                            all_rooms.append(part.room.code)

                        if part.meeting_days:
                            days = [d.strip() for d in part.meeting_days.split(",")]
                            all_days.update(days)

                        if part.start_time and part.end_time:
                            time_str = f"{part.start_time.strftime('%H:%M')}-{part.end_time.strftime('%H:%M')}"
                            all_times.add(time_str)

                    # For single-part classes, flatten completely
                    if len(parts) == 1:
                        part = parts[0]
                        data["teacher"] = all_teachers[0] if all_teachers else None
                        data["room"] = all_rooms[0] if all_rooms else None
                        data["meeting_days"] = sorted(all_days)
                        if part.start_time:
                            data["start_time"] = part.start_time.strftime("%H:%M")
                        if part.end_time:
                            data["end_time"] = part.end_time.strftime("%H:%M")

        return data

    def serialize_part(self, part):
        """Serialize a ClassPart."""
        teacher_name = None
        if part.teacher:
            teacher_name = f"{part.teacher.user.first_name} {part.teacher.user.last_name}".strip()
            if not teacher_name:
                teacher_name = part.teacher.user.email

        return {
            "part_code": part.class_part_code,
            "part_type": part.class_part_type,
            "teacher": teacher_name,
            "room": part.room.code if part.room else None,
            "meeting_days": [d.strip() for d in part.meeting_days.split(",")] if part.meeting_days else [],
            "start_time": part.start_time.strftime("%H:%M") if part.start_time else None,
            "end_time": part.end_time.strftime("%H:%M") if part.end_time else None,
        }

    def is_ieap_class(self, cls):
        """Check if this is an IEAP class."""
        return cls.course.code.startswith("IEAP") or cls.class_sessions.count() > 1

    def is_language_program(self, cls):
        """Check if this is a language program class."""
        code = cls.course.code
        return any(code.startswith(prefix) for prefix in ["EHSS", "GESL", "EXPRESS"])

    def is_extended_class(self, cls):
        """Check if any part is 3+ hours."""
        for session in cls.class_sessions.all():
            for part in session.class_parts.all():
                if part.start_time and part.end_time:
                    duration = part.duration_minutes
                    if duration >= 180:  # 3 hours
                        return True
        return False

    def calculate_stats(self, classes_data):
        """Calculate statistics for the classes."""
        total_classes = len(classes_data)
        total_enrolled = sum(c.get("current_enrollment", 0) for c in classes_data)
        total_capacity = sum(c.get("max_enrollment", 0) for c in classes_data)
        available_seats = total_capacity - total_enrolled

        return {
            "total_classes": total_classes,
            "total_enrolled": total_enrolled,
            "total_capacity": total_capacity,
            "available_seats": available_seats,
        }


class ClassDetailView(View):
    """Get detailed information about a specific class."""

    def get(self, request, class_id):
        try:
            class_header = ClassHeader.objects.prefetch_related(
                "class_sessions__class_parts__teacher",
                "class_sessions__class_parts__room",
                "combined_class_instance__class_headers",
            ).get(id=class_id)

            serializer = ClassDataAPIView()
            data = serializer.serialize_class(class_header)

            # Add additional detail info
            all_teachers = set()
            all_days = set()

            for session in class_header.class_sessions.all():
                for part in session.class_parts.all():
                    if part.teacher:
                        teacher_name = f"{part.teacher.user.first_name} {part.teacher.user.last_name}".strip()
                        all_teachers.add(teacher_name)
                    if part.meeting_days:
                        days = [d.strip() for d in part.meeting_days.split(",")]
                        all_days.update(days)

            data["all_teachers"] = sorted(all_teachers)
            data["all_meeting_days"] = sorted(all_days)

            return JsonResponse(data)

        except ClassHeader.DoesNotExist:
            return JsonResponse({"error": "Class not found"}, status=404)


class EnrollStudentView(LoginRequiredMixin, View):
    """Handle student enrollment actions."""

    def post(self, request):
        """Enroll or drop a student from a class."""
        import json

        try:
            data = json.loads(request.body)
            class_id = data.get("class_id")
            action = data.get("action", "enroll")
        except (json.JSONDecodeError, AttributeError):
            class_id = request.POST.get("class_id")
            action = request.POST.get("action", "enroll")

        if not class_id:
            return JsonResponse({"error": "Class ID required"}, status=400)

        try:
            class_header = ClassHeader.objects.get(id=class_id)
        except ClassHeader.DoesNotExist:
            return JsonResponse({"error": "Class not found"}, status=404)

        # Import enrollment model (adjust path as needed)
        try:
            from apps.enrollment.models import ClassHeaderEnrollment
        except ImportError:
            return JsonResponse({"error": "Enrollment system not available"}, status=503)

        if action == "enroll":
            # Check if class is full
            current_enrollment = ClassHeaderEnrollment.objects.filter(
                class_header=class_header, status="ENROLLED"
            ).count()

            if current_enrollment >= class_header.max_enrollment:
                return JsonResponse({"error": "Class is full"}, status=400)

            # Create enrollment
            enrollment, created = ClassHeaderEnrollment.objects.get_or_create(
                student=request.user, class_header=class_header, defaults={"status": "ENROLLED"}
            )

            if created:
                return JsonResponse(
                    {"success": True, "message": "Enrolled successfully", "current_enrollment": current_enrollment + 1}
                )
            else:
                return JsonResponse({"error": "Already enrolled"}, status=400)

        elif action == "drop":
            try:
                enrollment = ClassHeaderEnrollment.objects.get(
                    student=request.user, class_header=class_header, status="ENROLLED"
                )
                enrollment.status = "DROPPED"
                enrollment.save()

                new_enrollment = ClassHeaderEnrollment.objects.filter(
                    class_header=class_header, status="ENROLLED"
                ).count()

                return JsonResponse(
                    {"success": True, "message": "Dropped successfully", "current_enrollment": new_enrollment}
                )
            except ClassHeaderEnrollment.DoesNotExist:
                return JsonResponse({"error": "Not enrolled in this class"}, status=400)

        return JsonResponse({"error": "Invalid action"}, status=400)


class ExportScheduleView(LoginRequiredMixin, View):
    """Export class schedule to CSV."""

    def get(self, request):
        import csv

        # Get parameters
        term_type = request.GET.get("term", "language")

        # Get classes using same logic as API
        api_view = ClassDataAPIView()
        response = api_view.get(request)
        data = json.loads(response.content)

        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="class_schedule_{term_type}.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Course Code",
                "Course Title",
                "Section",
                "Time of Day",
                "Teacher(s)",
                "Room(s)",
                "Days",
                "Time",
                "Current Enrollment",
                "Max Enrollment",
                "Available Seats",
            ]
        )

        for cls in data.get("classes", []):
            # Collect all teachers
            teachers = []
            rooms = []
            days = set()
            times = set()

            if cls.get("sessions"):
                for session in cls["sessions"]:
                    for part in session.get("parts", []):
                        if part.get("teacher"):
                            teachers.append(part["teacher"])
                        if part.get("room"):
                            rooms.append(part["room"])
                        if part.get("meeting_days"):
                            days.update(part["meeting_days"])
                        if part.get("start_time") and part.get("end_time"):
                            times.add(f"{part['start_time']}-{part['end_time']}")
            elif cls.get("parts"):
                for part in cls["parts"]:
                    if part.get("teacher"):
                        teachers.append(part["teacher"])
                    if part.get("room"):
                        rooms.append(part["room"])
                    if part.get("meeting_days"):
                        days.update(part["meeting_days"])
                    if part.get("start_time") and part.get("end_time"):
                        times.add(f"{part['start_time']}-{part['end_time']}")
            else:
                if cls.get("teacher"):
                    teachers.append(cls["teacher"])
                if cls.get("room"):
                    rooms.append(cls["room"])
                if cls.get("meeting_days"):
                    days.update(cls["meeting_days"])
                if cls.get("start_time") and cls.get("end_time"):
                    times.add(f"{cls['start_time']}-{cls['end_time']}")

            writer.writerow(
                [
                    cls.get("course_code", ""),
                    cls.get("course_title", ""),
                    cls.get("section_id", ""),
                    cls.get("time_of_day", ""),
                    ", ".join(teachers) or "TBA",
                    ", ".join(rooms) or "TBA",
                    "".join(sorted(days)),
                    ", ".join(times) or "TBA",
                    cls.get("current_enrollment", 0),
                    cls.get("max_enrollment", 0),
                    cls.get("max_enrollment", 0) - cls.get("current_enrollment", 0),
                ]
            )

        return response
