"""Accounts app models for authorization and role-based access control.

This module contains models for managing advanced authorization features including
departments, roles, permissions, and user-role assignments. All models are designed
to avoid circular dependencies while providing comprehensive RBAC functionality.

Key architectural decisions:
- Clean dependencies: accounts → users (no circular dependencies)
- Hierarchical role system with permission inheritance
- Department-scoped permissions for multi-tenant scenarios
- Object-level permissions for fine-grained access control
- Performance optimized with caching and efficient queries

Models:
- Department: Organizational units for scoping permissions
- Role: Hierarchical roles with permission inheritance
- UserRole: Links users to roles with department context
- Permission: Custom permissions beyond Django's built-in system
- RolePermission: Links roles to permissions with context
"""

from datetime import date
from typing import Any, ClassVar

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    ForeignKey,
    JSONField,
    PositiveSmallIntegerField,
    TextField,
)
from django.utils.translation import gettext_lazy as _

try:
    import jsonschema
except ImportError:
    jsonschema = None

from apps.common.models import AuditModel

# JSON schema definitions for security validation
OVERRIDE_POLICIES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "string",
        "enum": [
            "ENROLLMENT_CAPACITY",
            "ENROLLMENT_DEADLINE",
            "PREREQUISITE_WAIVER",
            "GRADE_CHANGE",
            "ATTENDANCE_EXCUSE",
            "FEE_WAIVER",
            "LATE_REGISTRATION",
            "ACADEMIC_PROBATION",
            "GRADUATION_REQUIREMENT",
            "CREDIT_TRANSFER",
        ],
    },
    "maxItems": 20,
}

APPROVAL_LIMITS_SCHEMA = {
    "type": "object",
    "properties": {
        "financial": {
            "type": "object",
            "properties": {
                "max_amount": {"type": "number", "minimum": 0, "maximum": 1000000},
                "currency": {"type": "string", "enum": ["USD", "KHR"]},
                "requires_second_approval": {"type": "boolean"},
            },
            "required": ["max_amount", "currency"],
            "additionalProperties": False,
        },
        "enrollment": {
            "type": "object",
            "properties": {
                "max_students": {"type": "integer", "minimum": 1, "maximum": 1000},
                "can_override_capacity": {"type": "boolean"},
                "can_waive_prerequisites": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "academic": {
            "type": "object",
            "properties": {
                "can_change_grades": {"type": "boolean"},
                "grade_change_deadline_days": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 365,
                },
                "can_grant_extensions": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


class Department(AuditModel):
    """Organizational units for scoping permissions and roles.

    Departments provide organizational context for roles and permissions,
    enabling multi-tenant functionality within the SIS. Each department
    can have its own role hierarchy and permission assignments.

    Key features:
    - Unique department codes for system integration
    - Active/inactive status for department lifecycle management
    - Notice sending capabilities for department-wide communications
    - Historical tracking via AuditModel base
    - Clean validation and business logic
    """

    name: CharField = models.CharField(
        _("Department Name"),
        max_length=100,
        unique=True,
        help_text=_("Full name of the department"),
    )
    code: CharField = models.CharField(
        _("Department Code"),
        max_length=20,
        unique=True,
        help_text=_("Short code for the department (e.g., 'CS', 'MATH', 'ADMIN')"),
    )
    description: TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of the department's purpose and scope"),
    )
    is_active: BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this department is currently active"),
    )
    display_order: PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Display Order"),
        default=100,
        help_text=_("Order for displaying departments in lists"),
    )

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        ordering = ["display_order", "name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def clean(self) -> None:
        """Validate department data."""
        super().clean()
        if self.code:
            self.code = self.code.upper()


class Position(AuditModel):
    """Formal institutional positions with clear authority levels and hierarchy.

    Positions define institutional roles like Department Chair, Academic Director,
    Dean, etc. with explicit authority levels for decision-making and override
    permissions. This enables proper institutional governance and escalation
    workflows.

    Key features:
    - Clear authority hierarchy with numeric levels (1=highest)
    - Department-specific or institutional positions
    - Reporting structure for organizational clarity
    - Override permissions for policy exceptions
    - Approval limits for financial and policy decisions
    """

    title: CharField = models.CharField(
        _("Position Title"),
        max_length=100,
        help_text=_("Official title of the position (e.g., 'Department Chair', 'Academic Director')"),
    )
    department: ForeignKey = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="positions",
        verbose_name=_("Department"),
        help_text=_("Department this position belongs to (leave blank for institutional positions)"),
    )
    reports_to: ForeignKey = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
        verbose_name=_("Reports To"),
        help_text=_("Position this role reports to in organizational hierarchy"),
    )

    # Authority and decision-making
    authority_level: PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Authority Level"),
        help_text=_("Authority level (1=highest like Dean, 2=Dept Chair, 3=Supervisor, etc.)"),
    )
    can_override_policies: JSONField = models.JSONField(
        _("Override Policies"),
        default=list,
        blank=True,
        help_text=_("List of policy types this position can override (e.g., ['ENROLLMENT', 'ACADEMIC'])"),
    )
    approval_limits: JSONField = models.JSONField(
        _("Approval Limits"),
        default=dict,
        blank=True,
        help_text=_("Financial and other approval limits (e.g., {'financial': 5000, 'enrollment': 'unlimited'})"),
    )

    # Administrative fields
    is_active: BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this position is currently active"),
    )
    description: TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of this position's responsibilities"),
    )

    class Meta:
        verbose_name = _("Position")
        verbose_name_plural = _("Positions")
        unique_together = [["title", "department"]]
        ordering = ["authority_level", "department", "title"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["authority_level", "is_active"]),
            models.Index(fields=["department", "is_active"]),
            models.Index(fields=["reports_to"]),
        ]

    def __str__(self) -> str:
        if self.department:
            return f"{self.title} ({self.department.code})"
        return f"{self.title} (Institutional)"

    @property
    def is_institutional_position(self) -> bool:
        """Check if this is an institutional position (not department-specific)."""
        return self.department is None

    def get_all_subordinates(self) -> set["Position"]:
        """Get all positions that report to this position, directly or indirectly.

        Returns:
            Set of Position objects in the reporting hierarchy below this position
        """
        subordinates: set[Position] = set()

        # Get direct reports
        direct_reports = self.direct_reports.filter(is_active=True)
        subordinates.update(direct_reports)

        # Get indirect reports recursively
        for direct_report in direct_reports:
            indirect_reports = direct_report.get_all_subordinates()
            subordinates.update(indirect_reports)

        return subordinates

    def can_override_policy(self, policy_type: str) -> bool:
        """Check if this position can override a specific policy type.

        Args:
            policy_type: Type of policy to check (e.g., 'ENROLLMENT', 'ACADEMIC')

        Returns:
            True if position has override authority for this policy type
        """
        return policy_type in self.can_override_policies

    def clean(self) -> None:
        """Validate position data."""
        super().clean()

        # Prevent circular reporting relationships
        if self.reports_to:
            current: Position | None = self.reports_to
            while current:
                if current == self:
                    raise ValidationError(
                        {"reports_to": _("Circular reporting relationship detected.")},
                    )
                current = current.reports_to

        # Authority level validation
        if self.authority_level < 1:
            raise ValidationError(
                {"authority_level": _("Authority level must be 1 or higher.")},
            )

        # JSON field validation for security
        if jsonschema:
            try:
                if self.can_override_policies:
                    jsonschema.validate(self.can_override_policies, OVERRIDE_POLICIES_SCHEMA)
                if self.approval_limits:
                    jsonschema.validate(self.approval_limits, APPROVAL_LIMITS_SCHEMA)
            except jsonschema.ValidationError as e:
                raise ValidationError(
                    {
                        (
                            "can_override_policies"
                            if "can_override_policies" in str(e.absolute_path)
                            else "approval_limits"
                        ): _("Invalid JSON structure: %(error)s") % {"error": e.message},
                    },
                ) from e
        elif self.can_override_policies or self.approval_limits:
            # Fallback validation when jsonschema not available
            if self.can_override_policies and not isinstance(self.can_override_policies, list):
                raise ValidationError({"can_override_policies": _("Must be a list of policy types.")})
            if self.approval_limits and not isinstance(self.approval_limits, dict):
                raise ValidationError({"approval_limits": _("Must be a dictionary of approval limits.")})

    def save(self, *args, **kwargs):
        """Ensure validation runs on save."""
        self.full_clean()
        super().save(*args, **kwargs)


class PositionAssignment(AuditModel):
    """Links people to institutional positions with temporal tracking.

    Manages the assignment of people to formal institutional positions,
    tracking current and historical assignments, acting roles, and
    delegation relationships for leave coverage.

    Key features:
    - Links people/ app Person model to accounts/ Position model
    - Temporal tracking with start/end dates
    - Acting position support for temporary assignments
    - Delegation system for leave coverage
    - Historical assignment tracking
    """

    person: ForeignKey = models.ForeignKey(
        "people.Person",
        on_delete=models.PROTECT,
        related_name="position_assignments",
        verbose_name=_("Person"),
    )
    position: ForeignKey = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name=_("Position"),
    )

    start_date: DateField = models.DateField(
        _("Start Date"),
        help_text=_("Date when this position assignment began"),
    )
    end_date: DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Date when this position assignment ended (leave blank for current)"),
    )

    # Assignment type
    is_acting: BooleanField = models.BooleanField(
        _("Is Acting"),
        default=False,
        help_text=_("Whether this is an acting position assignment"),
    )
    is_primary: BooleanField = models.BooleanField(
        _("Is Primary"),
        default=True,
        help_text=_("Whether this is the person's primary position"),
    )

    # Delegation support
    delegates_to: ForeignKey = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_from",
        verbose_name=_("Delegates To"),
        help_text=_("Position assignment that has been delegated authority"),
    )
    delegation_start: DateField = models.DateField(
        _("Delegation Start"),
        null=True,
        blank=True,
        help_text=_("Start date of delegation"),
    )
    delegation_end: DateField = models.DateField(
        _("Delegation End"),
        null=True,
        blank=True,
        help_text=_("End date of delegation"),
    )

    # Administrative fields
    notes: TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this position assignment"),
    )

    class Meta:
        verbose_name = _("Position Assignment")
        verbose_name_plural = _("Position Assignments")
        ordering = ["-start_date", "position__authority_level"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["person", "start_date", "end_date"]),
            models.Index(fields=["position", "start_date", "end_date"]),
            models.Index(fields=["is_primary", "end_date"]),
            models.Index(fields=["delegates_to"]),
        ]

    def __str__(self) -> str:
        acting = " (Acting)" if self.is_acting else ""
        current = " (Current)" if self.is_current else ""
        return f"{self.person.full_name} - {self.position.title}{acting}{current}"

    @property
    def is_current(self) -> bool:
        """Check if this is a current position assignment."""
        today = date.today()
        if self.end_date and self.end_date < today:
            return False
        return self.start_date <= today

    @property
    def has_active_delegation(self) -> bool:
        """Check if this position currently has active delegation."""
        if not self.delegation_start:
            return False

        today = date.today()
        if self.delegation_end and self.delegation_end < today:
            return False
        return self.delegation_start <= today

    def get_effective_authority(self) -> "PositionAssignment":
        """Get the position assignment with effective authority.

        If delegation is active, returns the delegated assignment.
        Otherwise returns self.

        Returns:
            PositionAssignment with current effective authority
        """
        if self.has_active_delegation and self.delegates_to:
            return self.delegates_to
        return self

    def clean(self) -> None:
        """Validate position assignment data."""
        super().clean()

        # End date must be after start date
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": _("End date must be after start date.")},
            )

        # Delegation dates validation
        if self.delegation_start and not self.delegates_to:
            raise ValidationError(
                {"delegates_to": _("Delegation target is required when delegation start date is set.")},
            )

        if self.delegation_end and not self.delegation_start:
            raise ValidationError(
                {"delegation_start": _("Delegation start date is required when end date is set.")},
            )

        if self.delegation_start and self.delegation_end and self.delegation_end < self.delegation_start:
            raise ValidationError(
                {"delegation_end": _("Delegation end date must be after start date.")},
            )


class TeachingAssignment(AuditModel):
    """Links teachers to departments with teaching qualifications and restrictions.

    Manages which teachers can teach in which departments with specific
    qualification requirements and authority levels. Implements business
    rules like requiring Master's degree for BA classes (except native
    English speakers for certain English courses).

    Key features:
    - Links people.TeacherProfile to accounts.Department
    - Degree requirement validation
    - Subject-specific teaching authorization
    - Native speaker exceptions for language courses
    - Teaching level restrictions (undergraduate, graduate)
    """

    class DegreeLevel(models.TextChoices):
        """Degree levels for teaching qualification."""

        BACHELORS = "BACHELORS", _("Bachelor's Degree")
        MASTERS = "MASTERS", _("Master's Degree")
        DOCTORATE = "DOCTORATE", _("Doctorate Degree")

    class TeachingLevel(models.TextChoices):
        """Teaching level authorization."""

        UNDERGRADUATE = "UNDERGRADUATE", _("Undergraduate")
        GRADUATE = "GRADUATE", _("Graduate")
        BOTH = "BOTH", _("Both Undergraduate and Graduate")

    teacher: ForeignKey = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.PROTECT,
        related_name="teaching_assignments",
        verbose_name=_("Teacher"),
    )
    department: ForeignKey = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
        verbose_name=_("Department"),
    )

    # Teaching qualifications
    minimum_degree: CharField = models.CharField(
        _("Minimum Degree Required"),
        max_length=20,
        choices=DegreeLevel.choices,
        default=DegreeLevel.MASTERS,
        help_text=_("Minimum degree level required for teaching in this assignment"),
    )
    authorized_levels: CharField = models.CharField(
        _("Authorized Teaching Levels"),
        max_length=20,
        choices=TeachingLevel.choices,
        default=TeachingLevel.UNDERGRADUATE,
        help_text=_("Which academic levels this teacher can teach"),
    )

    # Subject specializations - TODO: Enable when curriculum.Subject model exists
    # authorized_subjects = models.ManyToManyField(
    #     "curriculum.Subject",
    #     blank=True,
    #     related_name="teaching_assignments",
    #     verbose_name=_("Authorized Subjects"),
    #     help_text=_("Specific subjects this teacher is authorized to teach"),
    # )

    # Special qualifications
    is_native_english_speaker: BooleanField = models.BooleanField(
        _("Native English Speaker"),
        default=False,
        help_text=_("Allows teaching English courses with Bachelor's degree"),
    )
    has_special_qualification: BooleanField = models.BooleanField(
        _("Has Special Qualification"),
        default=False,
        help_text=_("Has special qualifications that override standard degree requirements"),
    )
    special_qualification_notes: TextField = models.TextField(
        _("Special Qualification Notes"),
        blank=True,
        help_text=_("Details about special qualifications"),
    )

    # Administrative authority
    can_approve_course_changes: BooleanField = models.BooleanField(
        _("Can Approve Course Changes"),
        default=False,
        help_text=_("Whether teacher can approve course modifications"),
    )
    is_department_coordinator: BooleanField = models.BooleanField(
        _("Is Department Coordinator"),
        default=False,
        help_text=_("Whether teacher serves as coordinator for this department"),
    )

    start_date: DateField = models.DateField(
        _("Start Date"),
        help_text=_("Date when this teaching assignment began"),
    )
    end_date: DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Date when this teaching assignment ended (leave blank for current)"),
    )

    # Administrative fields
    is_active: BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this teaching assignment is currently active"),
    )
    notes: TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this teaching assignment"),
    )

    class Meta:
        verbose_name = _("Teaching Assignment")
        verbose_name_plural = _("Teaching Assignments")
        unique_together = [["teacher", "department"]]
        ordering = ["department", "teacher"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["teacher", "is_active"]),
            models.Index(fields=["department", "is_active"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["authorized_levels", "minimum_degree"]),
        ]

    def __str__(self) -> str:
        return f"{self.teacher.person.full_name} - {self.department.name}"

    @property
    def is_current(self) -> bool:
        """Check if this is a current teaching assignment."""
        today = date.today()
        if self.end_date and self.end_date < today:
            return False
        return self.start_date <= today

    def can_teach_ba_courses(self) -> bool:
        """Check if teacher can teach Bachelor's level courses.

        Business rule: Requires Master's degree except for native English
        speakers teaching English courses.

        Returns:
            True if teacher meets qualification requirements for BA courses
        """
        # Master's or higher degree always qualifies
        if self.minimum_degree in [
            self.DegreeLevel.MASTERS,
            self.DegreeLevel.DOCTORATE,
        ]:
            return True

        # Native English speaker exception for English courses
        if (
            self.is_native_english_speaker
            and self.department.code in ["ENG", "ENGLISH"]
            and self.minimum_degree == self.DegreeLevel.BACHELORS
        ):
            return True

        # Special qualifications override
        return bool(self.has_special_qualification)

    def can_teach_graduate_courses(self) -> bool:
        """Check if teacher can teach graduate level courses.

        Business rule: Requires Master's degree minimum, Doctorate preferred.

        Returns:
            True if teacher meets qualification requirements for graduate courses
        """
        # Graduate teaching requires Master's minimum
        if self.minimum_degree in [
            self.DegreeLevel.MASTERS,
            self.DegreeLevel.DOCTORATE,
        ]:
            return self.authorized_levels in [
                self.TeachingLevel.GRADUATE,
                self.TeachingLevel.BOTH,
            ]

        # Special qualifications may override
        if self.has_special_qualification:
            return self.authorized_levels in [
                self.TeachingLevel.GRADUATE,
                self.TeachingLevel.BOTH,
            ]

        return False

    def clean(self) -> None:
        """Validate teaching assignment data."""
        super().clean()

        # End date must be after start date
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": _("End date must be after start date.")},
            )

        # Native English speaker only applies to English departments
        if self.is_native_english_speaker and self.department.code not in [
            "ENG",
            "ENGLISH",
        ]:
            raise ValidationError(
                {
                    "is_native_english_speaker": _(
                        "Native English speaker qualification only applies to English departments.",
                    ),
                },
            )

        # Special qualification requires notes
        if self.has_special_qualification and not self.special_qualification_notes:
            raise ValidationError(
                {
                    "special_qualification_notes": _(
                        "Special qualification notes are required when special qualification is checked.",
                    ),
                },
            )


class Role(AuditModel):
    """Hierarchical roles with permission inheritance and department context.

    Roles define what users can do within the system, with support for
    hierarchical inheritance and department-specific scoping. This enables
    flexible role-based access control that can adapt to different
    organizational structures.

    Key features:
    - Predefined role types for common SIS roles
    - Hierarchical structure with parent-child relationships
    - Department-specific or global roles
    - Permission flags for common operations
    - Historical tracking and validation
    """

    class RoleType(models.TextChoices):
        """Standard role types for SIS functionality."""

        DIRECTOR = "DIRECTOR", _("Director")
        HEAD = "HEAD", _("Department Head")
        SUPERVISOR = "SUPERVISOR", _("Supervisor")
        TEACHER = "TEACHER", _("Teacher")
        STAFF = "STAFF", _("Staff")
        STUDENT = "STUDENT", _("Student")
        PARENT = "PARENT", _("Parent")
        EXTERNAL = "EXTERNAL", _("External User")

    name: CharField = models.CharField(
        _("Role Name"),
        max_length=100,
        help_text=_("Descriptive name of the role"),
    )
    role_type: CharField = models.CharField(
        _("Role Type"),
        max_length=20,
        choices=RoleType.choices,
        help_text=_("Standard role type classification"),
    )
    department: ForeignKey = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="roles",
        verbose_name=_("Department"),
        help_text=_("Department this role belongs to (leave blank for global roles)"),
    )
    parent_role: ForeignKey = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="child_roles",
        verbose_name=_("Parent Role"),
        help_text=_("Parent role for permission inheritance"),
    )

    # Permission flags for common operations
    can_approve: BooleanField = models.BooleanField(
        _("Can Approve"),
        default=False,
        help_text=_("Whether this role can approve requests/changes"),
    )
    can_edit: BooleanField = models.BooleanField(
        _("Can Edit"),
        default=False,
        help_text=_("Whether this role can edit data"),
    )
    can_view: BooleanField = models.BooleanField(
        _("Can View"),
        default=True,
        help_text=_("Whether this role can view data"),
    )

    # Administrative fields
    is_active: BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this role is currently active"),
    )
    description: TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of this role's responsibilities"),
    )

    class Meta:
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        unique_together = [["name", "department"]]
        ordering = ["department", "role_type", "name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["role_type", "is_active"]),
            models.Index(fields=["department", "is_active"]),
            models.Index(fields=["parent_role"]),
        ]

    def __str__(self) -> str:
        if self.department:
            return f"{self.name} ({self.department.code})"
        return f"{self.name} (Global)"

    @property
    def is_global_role(self) -> bool:
        """Check if this is a global role (not department-specific)."""
        return self.department is None

    def get_all_permissions(self) -> set[str]:
        """Get all permissions for this role, including inherited permissions.

        Returns:
            Set of permission codenames this role has access to
        """
        permissions: set[str] = set()

        # Get direct permissions
        direct_permissions = self.role_permissions.values_list(
            "permission__codename",
            flat=True,
        )
        permissions.update(direct_permissions)

        # Get inherited permissions from parent roles
        if self.parent_role:
            parent_permissions = self.parent_role.get_all_permissions()
            permissions.update(parent_permissions)

        return permissions

    def clean(self) -> None:
        """Validate role data."""
        super().clean()

        # Prevent circular parent relationships
        if self.parent_role:
            current: Role | None = self.parent_role
            while current:
                if current == self:
                    raise ValidationError(
                        {"parent_role": _("Circular parent relationship detected.")},
                    )
                current = current.parent_role


class UserRole(AuditModel):
    """Links users to roles with department context and status tracking.

    This through model connects users to their assigned roles while
    maintaining department context and enabling role activation/deactivation.
    Supports multiple roles per user and role switching functionality.

    Key features:
    - Many-to-many relationship between users and roles
    - Department context for role assignments
    - Active/inactive status for role lifecycle management
    - Assignment date tracking for audit purposes
    """

    user: ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name=_("User"),
    )
    role: ForeignKey = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_assignments",
        verbose_name=_("Role"),
    )
    department: ForeignKey = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_roles",
        verbose_name=_("Department"),
        help_text=_("Department context for this role assignment"),
    )
    is_active: BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this role assignment is currently active"),
    )
    assigned_date: DateField | models.DateTimeField = models.DateTimeField(
        _("Assigned Date"),
        auto_now_add=True,
        help_text=_("Date when this role was assigned"),
    )
    notes: TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this role assignment"),
    )

    class Meta:
        verbose_name = _("User Role")
        verbose_name_plural = _("User Roles")
        unique_together = [["user", "role", "department"]]
        ordering = ["user", "role"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["department", "is_active"]),
        ]

    def __str__(self) -> str:
        dept_str = f" in {self.department.code}" if self.department else ""
        return f"{self.user.email} - {self.role.name}{dept_str}"

    def clean(self) -> None:
        """Validate user role assignment."""
        super().clean()

        if not self.role.is_global_role and not self.department:
            raise ValidationError(
                {
                    "department": _(
                        "Department is required for department-specific roles.",
                    ),
                },
            )

        if self.role.is_global_role and self.department:
            raise ValidationError(
                {
                    "department": _(
                        "Department should not be specified for global roles.",
                    ),
                },
            )


class Permission(AuditModel):
    """Custom permissions beyond Django's built-in permission system.

    Extends Django's permission system with additional context and
    flexibility for SIS-specific authorization needs. Supports both
    model-level and custom action permissions.

    Key features:
    - Content type associations for model-specific permissions
    - Codename-based identification for programmatic access
    - Extensible description system for documentation
    - Support for custom actions beyond CRUD operations
    """

    name: CharField = models.CharField(
        _("Permission Name"),
        max_length=100,
        help_text=_("Human-readable name of the permission"),
    )
    codename: CharField = models.CharField(
        _("Codename"),
        max_length=100,
        unique=True,
        help_text=_("Unique codename for programmatic access"),
    )
    content_type: ForeignKey = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="custom_permissions",
        verbose_name=_("Content Type"),
        help_text=_("Model this permission applies to (optional)"),
    )
    description: TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of what this permission allows"),
    )
    is_active: BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this permission is currently active"),
    )

    class Meta:
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")
        ordering = ["content_type", "name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["codename"]),
            models.Index(fields=["content_type", "is_active"]),
        ]

    def __str__(self) -> str:
        if self.content_type:
            return f"{self.name} ({self.content_type.model})"
        return self.name

    def clean(self) -> None:
        """Validate permission data."""
        super().clean()
        if self.codename:
            # Ensure codename follows Django conventions
            self.codename = self.codename.lower().replace(" ", "_")


class RolePermission(AuditModel):
    """Links roles to permissions with department and object context.

    This through model connects roles to their assigned permissions while
    supporting department-scoped permissions and object-level access control.
    Enables fine-grained permission management for complex authorization scenarios.

    Key features:
    - Many-to-many relationship between roles and permissions
    - Department-scoped permission assignments
    - Object-level permissions via Generic Foreign Keys
    - Flexible permission assignment system
    """

    role: ForeignKey = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions",
        verbose_name=_("Role"),
    )
    permission: ForeignKey = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_assignments",
        verbose_name=_("Permission"),
    )
    department: ForeignKey = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="role_permissions",
        verbose_name=_("Department"),
        help_text=_("Department scope for this permission (optional)"),
    )

    # Object-level permissions
    content_type: ForeignKey = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Content Type"),
        help_text=_("Content type for object-level permissions"),
    )
    object_id: models.PositiveIntegerField = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Object ID"),
        help_text=_("Object ID for object-level permissions"),
    )
    content_object = GenericForeignKey("content_type", "object_id")

    # Security: Restrict which models can have object-level permissions
    ALLOWED_MODELS = [
        "people.studentprofile",
        "people.teacherprofile",
        "accounts.department",
        "curriculum.course",
        "curriculum.major",
        "scheduling.classheader",
        "finance.invoice",
        "enrollment.classheaderenrollment",
    ]

    # Administrative fields
    is_active: BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this permission assignment is active"),
    )
    notes: TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this permission assignment"),
    )

    class Meta:
        verbose_name = _("Role Permission")
        verbose_name_plural = _("Role Permissions")
        unique_together = [
            ["role", "permission", "department", "content_type", "object_id"],
        ]
        ordering = ["role", "permission"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["permission", "is_active"]),
            models.Index(fields=["department", "is_active"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        constraints: list[Any] = [
            # Security constraint removed - validation is handled in clean() method
            # Django doesn't support cross-table lookups in CheckConstraints
        ]

    def save(self, *args, **kwargs):
        """Ensure validation runs on save."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        parts = [str(self.role), str(self.permission)]
        if self.department:
            parts.append(f"in {self.department.code}")
        if self.content_object:
            parts.append(f"for {self.content_object}")
        return " - ".join(parts)

    @property
    def is_object_level(self) -> bool:
        """Check if this is an object-level permission."""
        return self.content_type is not None and self.object_id is not None

    def clean(self) -> None:
        """Validate role permission assignment."""
        super().clean()

        # Object-level permissions require both content_type and object_id
        if bool(self.content_type) != bool(self.object_id):
            raise ValidationError(
                _("Object-level permissions require both content type and object ID."),
            )

        # Validate that object-level permissions are only granted on allowed models
        if self.content_type:
            model_label = f"{self.content_type.app_label}.{self.content_type.model}"
            if model_label not in self.ALLOWED_MODELS:
                raise ValidationError(
                    f"Permissions cannot be granted on {model_label}. "
                    f"Allowed models: {', '.join(self.ALLOWED_MODELS)}",
                )
