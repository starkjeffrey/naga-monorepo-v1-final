"""StudentProfile CRUD views using the CRUD framework."""

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.utils.html import format_html

from apps.common.crud import (
    CRUDCreateView,
    CRUDDeleteView,
    CRUDDetailView,
    CRUDListView,
    CRUDUpdateView,
)
from apps.common.crud.config import CRUDConfig, FieldConfig
from apps.enrollment.models import ClassHeaderEnrollment
from apps.enrollment.services import MajorDeclarationService
from apps.people.forms import StudentProfileForm
from apps.people.models import StudentProfile


def render_student_status(value, field_config):
    """Custom renderer for student status with color coding."""
    status_styles = {
        StudentProfile.Status.ACTIVE: ("Active", "green"),
        StudentProfile.Status.INACTIVE: ("Inactive", "gray"),
        StudentProfile.Status.GRADUATED: ("Graduated", "blue"),
        StudentProfile.Status.DROPPED: ("Dropped", "red"),
        StudentProfile.Status.SUSPENDED: ("Suspended", "yellow"),
        StudentProfile.Status.TRANSFERRED: ("Transferred", "purple"),
        StudentProfile.Status.FROZEN: ("Frozen", "indigo"),
        StudentProfile.Status.UNKNOWN: ("Unknown", "gray"),
    }

    label, color = status_styles.get(value, ("Unknown", "gray"))

    return format_html(
        (
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium '
            'bg-{}-100 text-{}-800 dark:bg-{}-900 dark:text-{}-200">'
            '<i class="fas fa-circle text-{}-400 mr-1.5 text-xs"></i>'
            "{}</span>"
        ),
        color,
        color,
        color,
        color,
        color,
        label,
    )


def render_student_id(value, field_config):
    """Custom renderer for student ID with formatting."""
    if value:
        # Convert to int if it's not already
        try:
            student_id = int(value)
            return format_html('<span class="font-mono text-sm">{:05d}</span>', student_id)
        except (ValueError, TypeError):
            # If conversion fails, just display as is
            return format_html('<span class="font-mono text-sm">{}</span>', value)
    return "-"


def render_monk_status(value, field_config):
    """Custom renderer for monk status."""
    if value:
        return format_html(
            '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium '
            'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200">'
            '<i class="fas fa-dharmachakra mr-1"></i>'
            "Monk"
            "</span>"
        )
    return ""


def render_study_time(value, field_config):
    """Custom renderer for study time preference."""
    icons = {
        "morning": "fa-sun",
        "afternoon": "fa-cloud-sun",
        "evening": "fa-moon",
    }

    colors = {
        "morning": "yellow",
        "afternoon": "orange",
        "evening": "indigo",
    }

    icon = icons.get(value, "fa-clock")
    color = colors.get(value, "gray")
    label = dict(StudentProfile.STUDY_TIME_CHOICES).get(value, value)

    return format_html(
        '<span class="inline-flex items-center text-{}-600 dark:text-{}-400"><i class="fas {} mr-1"></i>{}</span>',
        color,
        color,
        icon,
        label,
    )


def get_effective_major_name(student_profile):
    """Get the student's effective major name using the service."""
    major = MajorDeclarationService.get_effective_major(student_profile)
    return major.name if major else ""


def get_effective_major(student_profile):
    """Get the student's effective major using the service."""
    return MajorDeclarationService.get_effective_major(student_profile)


class StudentProfileListView(CRUDListView):
    """List view for student profiles with comprehensive features."""

    model = StudentProfile
    template_name = "people/student_profile_list.html"

    def get_effective_major_name(self, obj):
        """Get the student's effective major name using the service."""
        return get_effective_major_name(obj)

    def get_academic_journey_status(self, obj):
        """Get the student's current status from their active academic journey."""
        from apps.enrollment.models_progression import AcademicJourney

        # Use prefetched data if available
        if hasattr(obj, "active_journey_list") and obj.active_journey_list:
            active_journey = obj.active_journey_list[0]
        else:
            # Fallback query if not prefetched
            active_journey = AcademicJourney.objects.filter(
                student=obj, transition_status=AcademicJourney.TransitionStatus.ACTIVE
            ).first()

        if active_journey:
            # Map AcademicJourney TransitionStatus to StudentProfile Status
            status_mapping = {
                AcademicJourney.TransitionStatus.ACTIVE: StudentProfile.Status.ACTIVE,
                AcademicJourney.TransitionStatus.GRADUATED: StudentProfile.Status.GRADUATED,
                AcademicJourney.TransitionStatus.DROPPED_OUT: StudentProfile.Status.DROPPED,
                AcademicJourney.TransitionStatus.SUSPENDED: StudentProfile.Status.SUSPENDED,
                AcademicJourney.TransitionStatus.TRANSFERRED: StudentProfile.Status.TRANSFERRED,
            }
            mapped_status = status_mapping.get(active_journey.transition_status, StudentProfile.Status.UNKNOWN)
            return mapped_status

        # Fall back to the student's current_status field
        return obj.current_status

    crud_config = CRUDConfig(
        page_title="Student Profiles",
        page_subtitle="Comprehensive student profile management",
        page_icon="fas fa-users-cog",
        # Field configuration
        fields=[
            FieldConfig(
                name="formatted_student_id",
                verbose_name="Student ID",
                renderer=render_student_id,
                searchable=True,
                link_url="people:student-profile-detail",
            ),
            FieldConfig(
                name="person.full_name",
                verbose_name="Full Name",
                searchable=True,
                sortable=True,
                link_url="people:student-profile-detail",
            ),
            FieldConfig(
                name="person.khmer_name",
                verbose_name="Khmer Name",
                searchable=True,
                sortable=True,
            ),
            FieldConfig(
                name="person.school_email",
                verbose_name="School Email",
                searchable=True,
                truncate=30,
            ),
            FieldConfig(
                name="get_academic_journey_status",
                verbose_name="Status",
                field_type="method",
                renderer=render_student_status,
                sortable=False,  # Can't sort on computed field
            ),
            FieldConfig(
                name="get_effective_major_name",
                verbose_name="Major",
                field_type="method",
                searchable=False,  # Can't search on computed fields
            ),
            FieldConfig(
                name="study_time_preference",
                verbose_name="Study Time",
                renderer=render_study_time,
            ),
            FieldConfig(
                name="last_enrollment_date",
                verbose_name="Last Enrolled",
                field_type="date",
                sortable=True,
            ),
            FieldConfig(
                name="person.citizenship",
                verbose_name="Citizenship",
                hidden=True,
            ),
            FieldConfig(
                name="created_at",
                verbose_name="Created",
                field_type="datetime",
                hidden=True,
                sortable=True,
            ),
        ],
        # Features
        enable_search=True,
        enable_export=True,
        enable_column_toggle=True,
        enable_column_reorder=True,
        default_sort_field="-created_at",
        paginate_by=25,
        paginate_choices=[10, 25, 50, 100],
        # URLs
        list_url_name="people:student-profile-list",
        create_url_name="people:student-profile-create",
        update_url_name="people:student-profile-update",
        delete_url_name="people:student-profile-deactivate",
        detail_url_name="people:student-profile-detail",
        # Row actions
        row_actions=[
            {"type": "view"},
            {"type": "edit"},
            # Note: Replace these hardcoded URLs with reverse() once the views are implemented
            # {
            #     "type": "custom",
            #     "icon": "fas fa-exchange-alt",
            #     "title": "Change Status",
            #     "url": "/people/students/{pk}/status/",
            #     "css_class": "text-yellow-600 hover:text-yellow-900 dark:text-yellow-400",
            # },
            # {
            #     "type": "custom",
            #     "icon": "fas fa-graduation-cap",
            #     "title": "Academic Record",
            #     "url": "/academic/student-record/?student={pk}",
            #     "css_class": "text-purple-600 hover:text-purple-900 dark:text-purple-400",
            # },
            {"type": "delete"},
        ],
        # Export settings
        export_filename_prefix="student_profiles",
        export_formats=["csv", "xlsx"],
        # Extra context
        extra_context={
            "help_text": "Use filters to find specific student groups. Click column headers to sort.",
        },
    )

    def get_queryset(self):
        """Optimize queryset with related data."""
        from django.db.models import Prefetch

        from apps.enrollment.models_progression import AcademicJourney

        queryset = super().get_queryset()

        # Prefetch only active academic journeys for efficiency
        active_journeys = Prefetch(
            "academic_journeys",
            queryset=AcademicJourney.objects.filter(transition_status=AcademicJourney.TransitionStatus.ACTIVE),
            to_attr="active_journey_list",
        )

        queryset = queryset.select_related("person").prefetch_related(
            "major_declarations",
            "person__emergency_contacts",
            active_journeys,
        )

        # Apply filters
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(current_status=status)

        study_time = self.request.GET.get("study_time")
        if study_time:
            queryset = queryset.filter(study_time_preference=study_time)

        monk_filter = self.request.GET.get("is_monk")
        if monk_filter == "yes":
            queryset = queryset.filter(is_monk=True)
        elif monk_filter == "no":
            queryset = queryset.filter(is_monk=False)

        transfer_filter = self.request.GET.get("is_transfer")
        if transfer_filter == "yes":
            queryset = queryset.filter(is_transfer_student=True)
        elif transfer_filter == "no":
            queryset = queryset.filter(is_transfer_student=False)

        # Major conflict filter
        conflict_filter = self.request.GET.get("major_conflict")
        if conflict_filter == "yes":
            # This would need a custom annotation
            pass

        return queryset

    def get_context_data(self, **kwargs):
        """Add filter options and statistics."""
        context = super().get_context_data(**kwargs)

        # Add filter options
        context["status_choices"] = StudentProfile.Status.choices
        context["study_time_choices"] = StudentProfile.STUDY_TIME_CHOICES

        # Add statistics
        stats = StudentProfile.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(current_status=StudentProfile.Status.ACTIVE)),
            graduated=Count("id", filter=Q(current_status=StudentProfile.Status.GRADUATED)),
            monks=Count("id", filter=Q(is_monk=True)),
            transfers=Count("id", filter=Q(is_transfer_student=True)),
        )
        context["stats"] = stats

        # Status distribution
        status_dist = (
            StudentProfile.objects.values("current_status").annotate(count=Count("id")).order_by("current_status")
        )
        context["status_distribution"] = {item["current_status"]: item["count"] for item in status_dist}

        return context


class StudentProfileCreateView(CRUDCreateView):
    """Create view for student profiles."""

    model = StudentProfile
    form_class = StudentProfileForm

    crud_config = CRUDConfig(
        page_icon="fas fa-user-plus",
        page_title="Create Student Profile",
        page_subtitle="Register a new student in the system",
        list_url_name="people:student-profile-list",
    )

    def get_initial(self):
        """Set initial values."""
        initial = super().get_initial()

        # Use StudentNumberService to generate next student ID
        from apps.people.services import StudentNumberService

        initial["student_id"] = StudentNumberService.generate_next_student_number()

        return initial

    def get_form_kwargs(self):
        """Pass request user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Handle form submission."""
        # Set the user on the form for the service to use
        form.user = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            f"Student profile created successfully. ID: {self.object.formatted_student_id}",
        )

        return response


class StudentProfileUpdateView(CRUDUpdateView):
    """Update view for student profiles."""

    model = StudentProfile
    form_class = StudentProfileForm

    crud_config = CRUDConfig(
        page_icon="fas fa-user-edit",
        page_title="Edit Student Profile",
        list_url_name="people:student-profile-list",
    )

    def get_page_title(self):
        """Dynamic page title."""
        return f"Edit Student: {self.object.formatted_student_id}"

    def form_valid(self, form):
        """Track changes and log them."""
        # Track what changed
        changed_fields = []
        for field in form.changed_data:
            old_value = form.initial.get(field)
            new_value = form.cleaned_data.get(field)
            if old_value != new_value:
                changed_fields.append(f"{field}: {old_value} → {new_value}")

        form.instance.updated_by = self.request.user
        response = super().form_valid(form)

        # Log the update
        if changed_fields:
            from apps.people.models import StudentAuditLog

            StudentAuditLog.objects.create(
                student=self.object,
                action=StudentAuditLog.ActionType.UPDATE,
                changed_by=self.request.user,
                changes={
                    field: {
                        "old": form.initial.get(field),
                        "new": form.cleaned_data.get(field),
                    }
                    for field in form.changed_data
                },
                notes=f"Updated fields: {', '.join(changed_fields)}",
            )

        return response


class StudentProfileDetailView(CRUDDetailView):
    """Detail view for student profiles."""

    model = StudentProfile

    def get_effective_major(self, obj):
        """Get the student's effective major using the service."""
        return get_effective_major(obj)

    crud_config = CRUDConfig(
        page_icon="fas fa-id-card",
        fields=[
            # Basic Information Section
            FieldConfig(
                name="formatted_student_id",
                verbose_name="Student ID",
                renderer=render_student_id,
            ),
            FieldConfig(name="person.full_name", verbose_name="Full Name"),
            FieldConfig(name="person.display_name", verbose_name="Display Name"),
            FieldConfig(
                name="current_status",
                verbose_name="Status",
                renderer=render_student_status,
            ),
            # Contact Information
            FieldConfig(name="person.email", verbose_name="Email"),
            FieldConfig(name="person.phone", verbose_name="Phone"),
            FieldConfig(name="person.address", verbose_name="Address"),
            # Academic Information
            FieldConfig(
                name="get_effective_major",
                verbose_name="Current Major",
                field_type="method",
            ),
            FieldConfig(
                name="has_major_conflict",
                verbose_name="Major Conflict",
                field_type="boolean",
            ),
            FieldConfig(
                name="study_time_preference",
                verbose_name="Study Time",
                renderer=render_study_time,
            ),
            # Personal Information
            FieldConfig(
                name="person.date_of_birth",
                verbose_name="Date of Birth",
                field_type="date",
            ),
            FieldConfig(name="person.age", verbose_name="Age"),
            FieldConfig(name="person.gender", verbose_name="Gender"),
            FieldConfig(name="person.citizenship", verbose_name="Citizenship"),
            FieldConfig(name="person.birth_province", verbose_name="Birth Province"),
            # Special Status
            FieldConfig(
                name="is_monk",
                verbose_name="Monk Status",
                field_type="boolean",
                renderer=render_monk_status,
            ),
            FieldConfig(
                name="is_transfer_student",
                verbose_name="Transfer Student",
                field_type="boolean",
            ),
            # Dates
            FieldConfig(
                name="last_enrollment_date",
                verbose_name="Last Enrollment",
                field_type="date",
            ),
            FieldConfig(name="created_at", verbose_name="Profile Created", field_type="datetime"),
            # System Information
            FieldConfig(name="created_by", verbose_name="Created By"),
            FieldConfig(name="updated_by", verbose_name="Updated By"),
        ],
        list_url_name="people:student-profile-list",
        update_url_name="people:student-profile-update",
        delete_url_name="people:student-profile-deactivate",
    )

    def get_context_data(self, **kwargs):
        """Add additional context for detail view."""
        context = super().get_context_data(**kwargs)

        # Add audit log
        from apps.people.models import StudentAuditLog

        context["audit_logs"] = (
            StudentAuditLog.objects.filter(student=self.object)
            .select_related("changed_by")
            .order_by("-timestamp")[:10]
        )

        # Add emergency contacts
        context["emergency_contacts"] = self.object.person.emergency_contacts.all()

        # Add major declaration history
        context["major_declarations"] = self.object.major_declarations.select_related("major", "declared_by").order_by(
            "-declaration_date",
        )

        # Add enrollment summary

        enrollments = ClassHeaderEnrollment.objects.filter(student=self.object).select_related("class_header__course")

        context["enrollment_summary"] = {
            "total_courses": enrollments.count(),
            "completed_courses": enrollments.filter(status="COMPLETED").count(),
            "current_courses": enrollments.filter(status="ENROLLED").count(),
            "recent_enrollments": enrollments.order_by("-created_at")[:5],
        }

        return context


class StudentProfileDeactivateView(CRUDDeleteView):
    """Deactivate view for student profiles."""

    model = StudentProfile

    crud_config = CRUDConfig(
        page_title="Deactivate Student Profile",
        page_subtitle="This will mark the student as inactive, not delete the record.",
        list_url_name="people:student-profile-list",
    )

    def delete(self, request, *args, **kwargs):
        """Soft delete by changing status to INACTIVE."""
        self.object = self.get_object()

        # Don't actually delete, just deactivate
        old_status = self.object.current_status
        self.object.change_status(
            StudentProfile.Status.INACTIVE,
            user=request.user,
            notes="Deactivated via admin interface",
        )

        messages.warning(
            request,
            f"Student {self.object.formatted_student_id} has been deactivated. "
            f"Status changed from {old_status} to {self.object.current_status}.",
        )

        return HttpResponseRedirect(self.get_success_url())
