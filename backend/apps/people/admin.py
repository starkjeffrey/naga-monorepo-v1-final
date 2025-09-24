"""People app admin interfaces.

Provides comprehensive admin interfaces for managing people and their profiles,
including students, teachers, staff, and their related information following
clean architecture principles.

Key features:
- Person profile management with photo display
- Student profile with academic status tracking
- Teacher and staff profile management
- Phone number and emergency contact management
- Audit log tracking for person events
- Enhanced search and filtering capabilities
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from apps.common.utils import format_student_id

from .models import (
    EmergencyContact,
    Person,
    PersonEventLog,
    PhoneNumber,
    StaffProfile,
    StudentAuditLog,
    StudentPhoto,
    StudentProfile,
    TeacherProfile,
)


class PhoneNumberInline(admin.TabularInline):
    """Inline for managing person's phone numbers."""

    model = PhoneNumber
    extra = 1
    fields = [
        "number",
        "comment",
        "is_preferred",
        "is_telegram",
        "is_verified",
    ]
    ordering = ["-is_preferred", "number"]


class EmergencyContactInline(admin.TabularInline):
    """Inline for managing person's emergency contacts."""

    model = EmergencyContact
    extra = 1
    fields = [
        "name",
        "relationship",
        "primary_phone",
        "email",
        "is_primary",
    ]
    ordering = ["-is_primary", "name"]


class StudentPhotoInline(admin.TabularInline):
    """Inline for viewing student photos in Person admin."""

    model = StudentPhoto
    extra = 0
    fields = [
        "thumbnail_preview",
        "upload_timestamp",
        "upload_source",
        "is_current",
        "verified_by",
        "age_in_months_display",
        "needs_update",
    ]
    readonly_fields = [
        "thumbnail_preview",
        "upload_timestamp",
        "age_in_months_display",
        "needs_update",
    ]
    ordering = ["-upload_timestamp"]

    @admin.display(description="Photo")
    def thumbnail_preview(self, obj):
        """Display thumbnail preview."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 80px; max-height: 80px;" />',
                obj.thumbnail.url,
            )
        elif obj.photo_file:
            return format_html(
                '<img src="{}" style="max-width: 80px; max-height: 80px;" />',
                obj.photo_file.url,
            )
        return "No photo"

    @admin.display(description="Age (months)")
    def age_in_months_display(self, obj):
        """Display photo age in months."""
        return f"{obj.age_in_months:.1f}"


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """Admin interface for Person records."""

    list_display = [
        "full_name",
        "preferred_gender",
        "date_of_birth",
        "age_display",
        "birth_province",
        "citizenship",
        "has_photo",
        "phone_count",
        "created_at",
    ]
    list_filter = [
        "preferred_gender",
        "birth_province",
        "citizenship",
        "use_legal_name_for_documents",
        "created_at",
    ]
    search_fields = [
        "family_name",
        "personal_name",
        "full_name",
        "khmer_name",
        "alternate_family_name",
        "alternate_personal_name",
        "school_email",
        "personal_email",
        "unique_id",
    ]
    ordering = ["family_name", "personal_name"]
    readonly_fields = [
        "unique_id",
        "created_at",
        "updated_at",
        "age_display",
        "display_name",
        "photo_preview",
    ]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "unique_id",
                    "family_name",
                    "personal_name",
                    "full_name",
                    "khmer_name",
                ),
            },
        ),
        (
            "Legal Name (for Official Documents)",
            {
                "fields": (
                    "use_legal_name_for_documents",
                    "alternate_family_name",
                    "alternate_personal_name",
                    "alternate_khmer_name",
                    "alternate_gender",
                    "display_name",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Personal Details",
            {
                "fields": (
                    "preferred_gender",
                    "date_of_birth",
                    "age_display",
                    "birth_province",
                    "citizenship",
                ),
            },
        ),
        (
            "Contact Information",
            {
                "fields": (
                    "school_email",
                    "personal_email",
                ),
            },
        ),
        (
            "Photo",
            {
                "fields": (
                    "photo",
                    "photo_preview",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [PhoneNumberInline, EmergencyContactInline, StudentPhotoInline]

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for phone count."""
        from django.db.models import Count

        return super().get_queryset(request).annotate(phone_number_count=Count("phone_numbers"))

    @admin.display(description="Age")
    def age_display(self, obj):
        """Display calculated age."""
        return f"{obj.age} years old" if obj.age is not None else "Unknown"

    @admin.display(description="Photo")
    def has_photo(self, obj):
        """Display whether person has a photo."""
        if obj.photo:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: red;">✗ No</span>')

    @admin.display(description="Phone Numbers")
    def phone_count(self, obj):
        """Display number of phone numbers."""
        return obj.phone_number_count

    @admin.display(description="Photo Preview")
    def photo_preview(self, obj):
        """Display photo preview in admin."""
        # First try to get current photo from StudentPhoto
        current_photo = obj.get_current_photo()
        if current_photo and current_photo.photo_file:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px;" /><br/><small>Uploaded: {}</small>',
                current_photo.photo_file.url,
                current_photo.upload_timestamp.strftime("%Y-%m-%d"),
            )
        # Fallback to legacy photo field
        elif obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px;" /><br/><small>Legacy photo</small>',
                obj.photo.url,
            )
        return "No photo"


class EmergencyContactInlineForStudent(admin.TabularInline):
    """Inline for managing student's emergency contacts through their Person."""

    model = EmergencyContact
    extra = 0
    fields = [
        "name",
        "relationship",
        "primary_phone",
        "secondary_phone",
        "email",
        "is_primary",
    ]
    ordering = ["-is_primary", "name"]
    verbose_name = "Emergency Contact"
    verbose_name_plural = "Emergency Contacts"

    def get_queryset(self, request):
        """Filter emergency contacts to only show those for the student's person."""
        qs = super().get_queryset(request)
        if hasattr(request, "_obj_") and request._obj_ is not None:
            return qs.filter(person=request._obj_.person)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Set the person field to the current student's person."""
        if db_field.name == "person" and hasattr(request, "_obj_") and request._obj_ is not None:
            kwargs["initial"] = request._obj_.person
            kwargs["queryset"] = Person.objects.filter(id=request._obj_.person_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Ensure emergency contact is linked to the student's person."""
        if hasattr(request, "_obj_") and request._obj_ is not None:
            obj.person = request._obj_.person
        super().save_model(request, obj, form, change)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin interface for Student profiles."""

    list_display = [
        "person_name",
        "person_name_khmer",
        "formatted_student_id_display",
        "current_status",
        "person_gender",
        "person_age",
        "study_time_preference",
        "person_birth_province",
        "is_sponsored",
        "last_enrollment_date",
    ]
    list_filter = [
        "current_status",
        "study_time_preference",
        "person__preferred_gender",
        "person__birth_province",
        "person__citizenship",
        "last_enrollment_date",
        "created_at",
    ]
    search_fields = [
        "person__family_name",
        "person__personal_name",
        "person__full_name",
        "student_id",
    ]
    ordering = ["person__family_name", "person__personal_name"]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["person"]
    date_hierarchy = "last_enrollment_date"
    # inlines = [EmergencyContactInlineForStudent]  # Emergency contacts are on Person, not StudentProfile

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for person access."""
        return super().get_queryset(request).select_related("person")

    def get_form(self, request, obj=None, change=False, **kwargs):
        """Pass the current object to the request for use in inlines."""
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

    def get_inline_instances(self, request, obj=None):
        """Only show emergency contacts inline when editing existing student."""
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    fieldsets = (
        ("Person Information", {"fields": ("person",)}),
        (
            "Student Details",
            {
                "fields": (
                    "student_id",
                    "current_status",
                    "is_monk",
                    "is_transfer_student",
                    "study_time_preference",
                ),
            },
        ),
        (
            "Enrollment Information",
            {
                "fields": ("last_enrollment_date",),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["activate_students", "deactivate_students"]

    @admin.display(
        description="Name",
        ordering="person__full_name",
    )
    def person_name(self, obj):
        """Display person's full name."""
        return obj.person.full_name

    @admin.display(description="Programs")
    def program_display(self, obj):
        """Display current program information."""
        # This would need enrollment information
        return "Multiple Programs"  # Placeholder

    @admin.display(description="GPA")
    def gpa_display(self, obj):
        """Display current GPA."""
        # This would calculate from grades
        return "N/A"  # Placeholder until grade integration

    @admin.display(
        description="Student ID",
        ordering="student_id",
    )
    def formatted_student_id_display(self, obj):
        """Display student ID with leading zeros (5 digits)."""
        return format_student_id(obj.student_id)

    @admin.display(
        description="Gender",
        ordering="person__preferred_gender",
    )
    def person_gender(self, obj):
        """Display person's preferred gender."""
        return obj.person.get_preferred_gender_display()

    @admin.display(
        description="Age",
        ordering="person__date_of_birth",
    )
    def person_age(self, obj):
        """Display person's age."""
        return f"{obj.person.age}" if obj.person.age is not None else "Unknown"

    @admin.display(
        description="Birth Province",
        ordering="person__birth_province",
    )
    def person_birth_province(self, obj):
        """Display person's birth province."""
        return obj.person.get_birth_province_display() if obj.person.birth_province else "Not specified"

    @admin.display(
        description="Khmer Name",
        ordering="person__khmer_name",
    )
    def person_name_khmer(self, obj):
        """Display person's Khmer name."""
        return obj.person.khmer_name or "—"

    @admin.display(
        description="Sponsored",
        boolean=True,
    )
    def is_sponsored(self, obj):
        """Check if student has active sponsorship."""
        from apps.scholarships.models import SponsoredStudent

        return SponsoredStudent.objects.get_active_for_student(obj).exists()

    def has_activate_student_permission(self, request):
        """Check if user has permission to activate students."""
        return request.user.has_perm("people.can_activate_student")

    def has_deactivate_student_permission(self, request):
        """Check if user has permission to deactivate students."""
        return request.user.has_perm("people.can_deactivate_student")

    def get_actions(self, request):
        """Filter actions based on user permissions."""
        actions = super().get_actions(request)

        # Remove activate action if user doesn't have permission
        if not self.has_activate_student_permission(request) and "activate_students" in actions:
            del actions["activate_students"]

        # Remove deactivate action if user doesn't have permission
        if not self.has_deactivate_student_permission(request) and "deactivate_students" in actions:
            del actions["deactivate_students"]

        return actions

    @admin.action(description="Activate selected students")
    def activate_students(self, request, queryset):
        """Activate selected student accounts with permission check."""
        # Double-check permissions
        if not self.has_activate_student_permission(request):
            self.message_user(
                request,
                "You do not have permission to activate students.",
                level="error",
            )
            return

        # Filter only students that need activation
        students_to_activate = queryset.exclude(current_status=StudentProfile.Status.ACTIVE)

        if not students_to_activate.exists():
            self.message_user(request, "All selected students are already active.", level="info")
            return

        # Store old statuses for logging
        student_status_map = {student.pk: student.current_status for student in students_to_activate}

        # Bulk update all students to ACTIVE status
        updated_count = students_to_activate.update(
            current_status=StudentProfile.Status.ACTIVE,
            updated_at=timezone.now(),
        )

        # Bulk create audit logs
        from apps.common.models import SystemAuditLog

        audit_logs = []
        for student_id, old_status in student_status_map.items():
            audit_logs.append(
                SystemAuditLog(
                    action_type=SystemAuditLog.ActionType.REGISTRATION_POLICY_OVERRIDE,
                    performed_by=request.user,
                    target_app="people",
                    target_model="StudentProfile",
                    target_object_id=str(student_id),
                    override_reason=f"Admin activation: {old_status} -> ACTIVE",
                    original_restriction=f"Student status was {old_status}",
                    override_details={"old_status": old_status, "new_status": "ACTIVE"},
                    ip_address=request.META.get("REMOTE_ADDR"),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                ),
            )

        SystemAuditLog.objects.bulk_create(audit_logs)

        self.message_user(
            request,
            f"Successfully activated {updated_count} student(s).",
            level="success",
        )

    @admin.action(description="Deactivate selected students")
    def deactivate_students(self, request, queryset):
        """Deactivate selected student accounts with permission check."""
        # Double-check permissions
        if not self.has_deactivate_student_permission(request):
            self.message_user(
                request,
                "You do not have permission to deactivate students.",
                level="error",
            )
            return

        # Filter only students that need deactivation
        students_to_deactivate = queryset.exclude(current_status=StudentProfile.Status.INACTIVE)

        if not students_to_deactivate.exists():
            self.message_user(request, "All selected students are already inactive.", level="info")
            return

        # Store old statuses for logging
        student_status_map = {student.pk: student.current_status for student in students_to_deactivate}

        # Bulk update all students to INACTIVE status
        updated_count = students_to_deactivate.update(
            current_status=StudentProfile.Status.INACTIVE,
            updated_at=timezone.now(),
        )

        # Bulk create audit logs
        from apps.common.models import SystemAuditLog

        audit_logs = []
        for student_id, old_status in student_status_map.items():
            audit_logs.append(
                SystemAuditLog(
                    action_type=SystemAuditLog.ActionType.REGISTRATION_POLICY_OVERRIDE,
                    performed_by=request.user,
                    target_app="people",
                    target_model="StudentProfile",
                    target_object_id=str(student_id),
                    override_reason=f"Admin deactivation: {old_status} -> INACTIVE",
                    original_restriction=f"Student status was {old_status}",
                    override_details={
                        "old_status": old_status,
                        "new_status": "INACTIVE",
                    },
                    ip_address=request.META.get("REMOTE_ADDR"),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                ),
            )

        SystemAuditLog.objects.bulk_create(audit_logs)

        self.message_user(
            request,
            f"Successfully deactivated {updated_count} student(s).",
            level="success",
        )


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    """Admin interface for Teacher profiles."""

    list_display = [
        "person_name",
        "terminal_degree",
        "status",
        "start_date",
        "end_date",
        "is_teacher_active",
    ]
    list_filter = [
        "terminal_degree",
        "status",
        "start_date",
        "created_at",
    ]
    search_fields = [
        "person__family_name",
        "person__personal_name",
        "person__full_name",
    ]
    ordering = ["person__family_name", "person__personal_name"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["person"]
    date_hierarchy = "start_date"

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for person access."""
        return super().get_queryset(request).select_related("person")

    fieldsets = (
        ("Person Information", {"fields": ("person",)}),
        (
            "Employment Details",
            {
                "fields": (
                    "terminal_degree",
                    "status",
                ),
            },
        ),
        (
            "Employment Period",
            {
                "fields": (
                    "start_date",
                    "end_date",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="Name",
        ordering="person__full_name",
    )
    def person_name(self, obj):
        """Display person's full name."""
        return obj.person.full_name


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    """Admin interface for Staff profiles."""

    list_display = [
        "person_name",
        "position",
        "status",
        "start_date",
        "end_date",
    ]
    list_filter = [
        "position",
        "status",
        "start_date",
        "created_at",
    ]
    search_fields = [
        "person__family_name",
        "person__personal_name",
        "person__full_name",
        "position",
    ]
    ordering = ["person__family_name", "person__personal_name"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["person"]
    date_hierarchy = "start_date"

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for person access."""
        return super().get_queryset(request).select_related("person")

    fieldsets = (
        ("Person Information", {"fields": ("person",)}),
        (
            "Employment Details",
            {
                "fields": (
                    "position",
                    "status",
                ),
            },
        ),
        (
            "Employment Period",
            {
                "fields": (
                    "start_date",
                    "end_date",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="Name",
        ordering="person__full_name",
    )
    def person_name(self, obj):
        """Display person's full name."""
        return obj.person.full_name


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    """Admin interface for phone numbers."""

    list_display = [
        "person_name",
        "number",
        "comment",
        "is_preferred",
        "is_telegram",
        "is_verified",
        "created_at",
    ]
    list_filter = [
        "is_preferred",
        "is_telegram",
        "is_verified",
        "created_at",
    ]
    search_fields = [
        "person__family_name",
        "person__personal_name",
        "number",
    ]
    ordering = ["person", "-is_preferred", "number"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["person"]

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for person access."""
        return super().get_queryset(request).select_related("person")

    fieldsets = (
        ("Person Information", {"fields": ("person",)}),
        (
            "Phone Details",
            {
                "fields": (
                    "number",
                    "comment",
                ),
            },
        ),
        (
            "Configuration",
            {
                "fields": (
                    "is_preferred",
                    "is_telegram",
                    "is_verified",
                    "last_verification",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="Person",
        ordering="person__full_name",
    )
    def person_name(self, obj):
        """Display person's name."""
        return obj.person.full_name


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    """Admin interface for emergency contacts."""

    list_display = [
        "person_name",
        "name",
        "relationship",
        "primary_phone",
        "email",
        "is_primary",
        "created_at",
    ]
    list_filter = [
        "relationship",
        "is_primary",
        "created_at",
    ]
    search_fields = [
        "person__family_name",
        "person__personal_name",
        "name",
        "primary_phone",
        "email",
    ]
    ordering = ["person", "-is_primary", "name"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["person"]

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for person access."""
        return super().get_queryset(request).select_related("person")

    fieldsets = (
        ("Person Information", {"fields": ("person",)}),
        (
            "Contact Details",
            {
                "fields": (
                    "name",
                    "relationship",
                    "primary_phone",
                    "secondary_phone",
                    "email",
                    "address",
                ),
            },
        ),
        ("Configuration", {"fields": ("is_primary",)}),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="Person",
        ordering="person__full_name",
    )
    def person_name(self, obj):
        """Display person's name."""
        return obj.person.full_name


@admin.register(PersonEventLog)
class PersonEventLogAdmin(admin.ModelAdmin):
    """Admin interface for person event logs."""

    list_display = [
        "person_name",
        "action",
        "changed_by",
        "timestamp",
    ]
    list_filter = [
        "action",
        "timestamp",
        "changed_by",
    ]
    search_fields = [
        "person__family_name",
        "person__personal_name",
        "notes",
    ]
    ordering = ["-timestamp"]
    readonly_fields = [
        "person",
        "action",
        "changed_by",
        "timestamp",
        "details",
        "notes",
    ]

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for person access."""
        return super().get_queryset(request).select_related("person", "changed_by")

    fieldsets = (
        (
            "Event Information",
            {
                "fields": (
                    "person",
                    "action",
                    "changed_by",
                    "timestamp",
                    "details",
                    "notes",
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(
        description="Person",
        ordering="person__full_name",
    )
    def person_name(self, obj):
        """Display person's name."""
        return obj.person.full_name


@admin.register(StudentAuditLog)
class StudentAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for student audit logs."""

    list_display = [
        "student_name",
        "action",
        "changed_by",
        "timestamp",
    ]
    list_filter = [
        "action",
        "content_type",
        "timestamp",
        "changed_by",
    ]
    search_fields = [
        "student__person__family_name",
        "student__person__personal_name",
        "notes",
    ]
    ordering = ["-timestamp"]
    readonly_fields = [
        "student",
        "action",
        "content_type",
        "object_id",
        "changes",
        "changed_by",
        "timestamp",
        "notes",
    ]

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for student and person access."""
        return super().get_queryset(request).select_related("student__person", "changed_by", "content_type")

    fieldsets = (
        (
            "Change Information",
            {
                "fields": (
                    "student",
                    "action",
                    "content_type",
                    "object_id",
                ),
            },
        ),
        (
            "Changes",
            {
                "fields": (
                    "changes",
                    "notes",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "changed_by",
                    "timestamp",
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(
        description="Student",
        ordering="student__person__full_name",
    )
    def student_name(self, obj):
        """Display student's name."""
        return obj.student.person.full_name


@admin.register(StudentPhoto)
class StudentPhotoAdmin(admin.ModelAdmin):
    """Admin interface for student photos with versioning."""

    list_display = [
        "person_name",
        "student_id_display",
        "thumbnail_preview",
        "upload_timestamp",
        "upload_source",
        "is_current",
        "age_display",
        "needs_update_display",
        "verified_status",
        "file_size_display",
    ]

    list_filter = [
        "is_current",
        "upload_source",
        "skip_reminder",
        ("verified_by", admin.EmptyFieldListFilter),
        "upload_timestamp",
    ]

    search_fields = [
        "person__family_name",
        "person__personal_name",
        "person__full_name",
        "person__student_profile__student_id",
        "file_hash",
    ]

    ordering = ["-upload_timestamp"]

    readonly_fields = [
        "person",
        "photo_preview",
        "thumbnail_preview_large",
        "upload_timestamp",
        "file_hash",
        "file_size",
        "width",
        "height",
        "age_in_days",
        "age_in_months",
        "needs_update",
        "needs_reminder",
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = ["person"]
    date_hierarchy = "upload_timestamp"

    fieldsets = (
        (
            "Person Information",
            {
                "fields": ("person",),
            },
        ),
        (
            "Photo Details",
            {
                "fields": (
                    "photo_file",
                    "photo_preview",
                    "thumbnail",
                    "thumbnail_preview_large",
                    "upload_source",
                    "is_current",
                ),
            },
        ),
        (
            "Technical Information",
            {
                "fields": (
                    "file_hash",
                    "file_size",
                    "width",
                    "height",
                    "original_filename",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Verification",
            {
                "fields": (
                    "verified_by",
                    "verified_at",
                ),
            },
        ),
        (
            "Reminder Settings",
            {
                "fields": (
                    "age_in_days",
                    "age_in_months",
                    "needs_update",
                    "needs_reminder",
                    "reminder_sent_at",
                    "reminder_count",
                    "skip_reminder",
                ),
            },
        ),
        (
            "Administrative",
            {
                "fields": (
                    "notes",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["verify_photos", "send_reminders", "mark_as_current"]

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "person",
                "person__student_profile",
                "verified_by",
            )
        )

    @admin.display(description="Person", ordering="person__full_name")
    def person_name(self, obj):
        """Display person's name."""
        return obj.person.full_name

    @admin.display(description="Student ID", ordering="person__student_profile__student_id")
    def student_id_display(self, obj):
        """Display student ID if available."""
        if hasattr(obj.person, "student_profile"):
            return format_student_id(obj.person.student_profile.student_id)
        return "—"

    @admin.display(description="Photo")
    def thumbnail_preview(self, obj):
        """Display small thumbnail in list."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px;" />',
                obj.thumbnail.url,
            )
        elif obj.photo_file:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px;" />',
                obj.photo_file.url,
            )
        return "No photo"

    @admin.display(description="Photo Preview")
    def photo_preview(self, obj):
        """Display larger photo preview in detail view."""
        if obj.photo_file:
            return format_html(
                '<img src="{}" style="max-width: 320px; max-height: 360px;" />',
                obj.photo_file.url,
            )
        return "No photo"

    @admin.display(description="Thumbnail Preview")
    def thumbnail_preview_large(self, obj):
        """Display thumbnail preview in detail view."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 80px; max-height: 90px;" />',
                obj.thumbnail.url,
            )
        return "No thumbnail"

    @admin.display(description="Age")
    def age_display(self, obj):
        """Display photo age."""
        days = obj.age_in_days
        if days < 30:
            return f"{days} days"
        elif days < 365:
            return f"{obj.age_in_months:.1f} months"
        else:
            return f"{days // 365} years"

    @admin.display(description="Needs Update", boolean=True)
    def needs_update_display(self, obj):
        """Display whether photo needs update."""
        return obj.needs_update

    @admin.display(description="Verified")
    def verified_status(self, obj):
        """Display verification status."""
        if obj.verified_by:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                obj.verified_by.get_full_name() or obj.verified_by.email,
            )
        return format_html('<span style="color: gray;">—</span>')

    @admin.display(description="Size")
    def file_size_display(self, obj):
        """Display file size in human-readable format."""
        size = obj.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    @admin.action(description="Verify selected photos")
    def verify_photos(self, request, queryset):
        """Verify selected photos."""
        count = 0
        for photo in queryset.filter(verified_by__isnull=True):
            photo.verify(request.user)
            count += 1

        self.message_user(
            request,
            f"Successfully verified {count} photo(s).",
            level="success" if count > 0 else "info",
        )

    @admin.action(description="Send reminder for selected photos")
    def send_reminders(self, request, queryset):
        """Send reminders for selected photos."""
        count = 0
        for photo in queryset.filter(needs_reminder=True):
            photo.send_reminder()
            count += 1
            # Here you would also trigger the actual reminder notification

        self.message_user(
            request,
            f"Successfully sent reminders for {count} photo(s).",
            level="success" if count > 0 else "info",
        )

    @admin.action(description="Mark as current photo")
    def mark_as_current(self, request, queryset):
        """Mark selected photo as current (only one per person)."""
        if queryset.count() != 1:
            self.message_user(
                request,
                "Please select exactly one photo to mark as current.",
                level="error",
            )
            return

        photo = queryset.first()
        photo.is_current = True
        photo.save()

        self.message_user(
            request,
            f"Successfully marked photo as current for {photo.person.full_name}.",
            level="success",
        )
