"""Factory-boy factories for accounts models.

This module provides factory classes for generating realistic test data
for role-based access control (RBAC) models including:
- Departments and organizational units
- Hierarchical roles with permission inheritance
- User role assignments and permissions
- Custom permissions and role-permission mappings

Following clean architecture principles with realistic data generation
that supports comprehensive testing of RBAC workflows.
"""

import factory
from django.contrib.contenttypes.models import ContentType
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from apps.accounts.models import Department, Permission, Role, RolePermission, UserRole


class DepartmentFactory(DjangoModelFactory):
    """Factory for creating departments."""

    class Meta:
        model = Department
        django_get_or_create = ("code",)

    name = Faker(
        "random_element",
        elements=[
            "Computer Science Department",
            "English Language Department",
            "Mathematics Department",
            "Business Administration Department",
            "Student Affairs Department",
            "Academic Affairs Department",
            "Finance Department",
            "Human Resources Department",
            "Library Services Department",
            "Information Technology Department",
        ],
    )

    code = factory.LazyAttribute(
        lambda obj: (obj.name.split()[0].upper()[:4] if len(obj.name.split()) > 0 else "DEPT")
    )

    description = factory.LazyAttribute(
        lambda obj: f"The {obj.name} is responsible for managing academic and administrative functions "
        f"related to {obj.name.lower().replace('department', '').strip()}.",
    )

    is_active = Faker("boolean", chance_of_getting_true=90)

    display_order = Faker("random_int", min=1, max=100)


class RoleFactory(DjangoModelFactory):
    """Factory for creating roles."""

    class Meta:
        model = Role

    name = factory.LazyAttribute(
        lambda obj: (
            f"{obj.role_type.replace('_', ' ').title()}"
            if not obj.department
            else f"{obj.department.name} {obj.role_type.replace('_', ' ').title()}"
        ),
    )

    role_type = Faker(
        "random_element",
        elements=[
            Role.RoleType.DIRECTOR,
            Role.RoleType.HEAD,
            Role.RoleType.SUPERVISOR,
            Role.RoleType.TEACHER,
            Role.RoleType.STAFF,
            Role.RoleType.STUDENT,
            Role.RoleType.PARENT,
            Role.RoleType.EXTERNAL,
        ],
    )

    department = SubFactory(DepartmentFactory)

    # parent_role will be set separately to avoid circular dependencies
    parent_role = None

    can_approve = factory.LazyAttribute(
        lambda obj: obj.role_type in [Role.RoleType.DIRECTOR, Role.RoleType.HEAD, Role.RoleType.SUPERVISOR],
    )

    can_edit = factory.LazyAttribute(
        lambda obj: obj.role_type
        in [
            Role.RoleType.DIRECTOR,
            Role.RoleType.HEAD,
            Role.RoleType.SUPERVISOR,
            Role.RoleType.TEACHER,
            Role.RoleType.STAFF,
        ],
    )

    can_view = Faker("boolean", chance_of_getting_true=95)

    is_active = Faker("boolean", chance_of_getting_true=85)

    description = factory.LazyAttribute(
        lambda obj: f"Role for {obj.role_type.replace('_', ' ').lower()} level access"
        f"{' within ' + obj.department.name if obj.department else ' across the institution'}",
    )


class GlobalRoleFactory(RoleFactory):
    """Factory for creating global roles (not department-specific)."""

    department = None

    name = factory.LazyAttribute(lambda obj: f"Global {obj.role_type.replace('_', ' ').title()}")


class PermissionFactory(DjangoModelFactory):
    """Factory for creating custom permissions."""

    class Meta:
        model = Permission
        django_get_or_create = ("codename",)

    name = Faker(
        "random_element",
        elements=[
            "Can View Student Records",
            "Can Edit Student Records",
            "Can Delete Student Records",
            "Can Approve Enrollments",
            "Can Generate Reports",
            "Can Access Financial Data",
            "Can Modify Course Content",
            "Can Assign Grades",
            "Can View Attendance",
            "Can Manage Schedules",
            "Can Access Admin Panel",
            "Can Export Data",
            "Can Import Data",
            "Can Manage User Accounts",
            "Can View Audit Logs",
        ],
    )

    codename = factory.LazyAttribute(lambda obj: obj.name.lower().replace("can ", "").replace(" ", "_"))

    content_type = factory.LazyFunction(lambda: ContentType.objects.first() if ContentType.objects.exists() else None)

    description = factory.LazyAttribute(
        lambda obj: f"Permission that allows users to {obj.name.lower().replace('can ', '')}",
    )

    is_active = Faker("boolean", chance_of_getting_true=90)


class UserRoleFactory(DjangoModelFactory):
    """Factory for creating user role assignments."""

    class Meta:
        model = UserRole

    role = SubFactory(RoleFactory)
    department = factory.SelfAttribute("role.department")

    is_active = Faker("boolean", chance_of_getting_true=85)

    notes = factory.LazyAttribute(
        lambda obj: (
            f"Assigned {obj.role.name} role{' in ' + obj.department.name if obj.department else ''}"
            if Faker("boolean", chance_of_getting_true=30)
            else ""
        ),
    )


class RolePermissionFactory(DjangoModelFactory):
    """Factory for creating role permission assignments."""

    class Meta:
        model = RolePermission

    role = SubFactory(RoleFactory)
    permission = SubFactory(PermissionFactory)
    department = factory.SelfAttribute("role.department")

    # Object-level permissions (optional)
    content_type = None
    object_id = None

    is_active = Faker("boolean", chance_of_getting_true=90)

    notes = factory.LazyAttribute(
        lambda obj: (
            f"Grants {obj.permission.name.lower()} to {obj.role.name}"
            if Faker("boolean", chance_of_getting_true=25)
            else ""
        ),
    )


# Utility factory for creating complete RBAC scenarios
class RBACScenarioFactory:
    """Factory for creating complete RBAC scenarios with related data."""

    @classmethod
    def create_academic_department_hierarchy(cls, department_name="Computer Science Department"):
        """Create a complete academic department with role hierarchy."""
        # Create department
        department = DepartmentFactory(name=department_name)

        # Create hierarchical roles
        director_role = RoleFactory(
            name=f"{department.name} Director",
            role_type=Role.RoleType.DIRECTOR,
            department=department,
            can_approve=True,
            can_edit=True,
            can_view=True,
        )

        head_role = RoleFactory(
            name=f"{department.name} Head",
            role_type=Role.RoleType.HEAD,
            department=department,
            parent_role=director_role,
            can_approve=True,
            can_edit=True,
            can_view=True,
        )

        supervisor_role = RoleFactory(
            name=f"{department.name} Supervisor",
            role_type=Role.RoleType.SUPERVISOR,
            department=department,
            parent_role=head_role,
            can_approve=False,
            can_edit=True,
            can_view=True,
        )

        teacher_role = RoleFactory(
            name=f"{department.name} Teacher",
            role_type=Role.RoleType.TEACHER,
            department=department,
            parent_role=supervisor_role,
            can_approve=False,
            can_edit=True,
            can_view=True,
        )

        staff_role = RoleFactory(
            name=f"{department.name} Staff",
            role_type=Role.RoleType.STAFF,
            department=department,
            can_approve=False,
            can_edit=False,
            can_view=True,
        )

        return {
            "department": department,
            "roles": {
                "director": director_role,
                "head": head_role,
                "supervisor": supervisor_role,
                "teacher": teacher_role,
                "staff": staff_role,
            },
        }

    @classmethod
    def create_standard_permissions_set(cls):
        """Create a standard set of permissions for SIS functionality."""
        permissions = []

        # Academic permissions
        academic_permissions = [
            ("Can View Student Records", "view_student_records"),
            ("Can Edit Student Records", "edit_student_records"),
            ("Can Delete Student Records", "delete_student_records"),
            ("Can Approve Enrollments", "approve_enrollments"),
            ("Can Assign Grades", "assign_grades"),
            ("Can View Grades", "view_grades"),
            ("Can Modify Course Content", "modify_course_content"),
            ("Can View Attendance", "view_attendance"),
            ("Can Mark Attendance", "mark_attendance"),
        ]

        # Administrative permissions
        admin_permissions = [
            ("Can Generate Reports", "generate_reports"),
            ("Can Access Financial Data", "access_financial_data"),
            ("Can Manage Schedules", "manage_schedules"),
            ("Can Access Admin Panel", "access_admin_panel"),
            ("Can Export Data", "export_data"),
            ("Can Import Data", "import_data"),
            ("Can Manage User Accounts", "manage_user_accounts"),
            ("Can View Audit Logs", "view_audit_logs"),
        ]

        for name, codename in academic_permissions + admin_permissions:
            permission = PermissionFactory(name=name, codename=codename)
            permissions.append(permission)

        return permissions

    @classmethod
    def create_role_permissions_for_hierarchy(cls, roles_dict, permissions_list):
        """Assign appropriate permissions to roles based on hierarchy."""
        role_permissions = []

        # Director gets all permissions
        if "director" in roles_dict:
            for permission in permissions_list:
                rp = RolePermissionFactory(role=roles_dict["director"], permission=permission, is_active=True)
                role_permissions.append(rp)

        # Head gets most permissions except user management
        if "head" in roles_dict:
            excluded_codenames = {"manage_user_accounts", "access_admin_panel"}
            for permission in permissions_list:
                if permission.codename not in excluded_codenames:
                    rp = RolePermissionFactory(role=roles_dict["head"], permission=permission, is_active=True)
                    role_permissions.append(rp)

        # Teacher gets academic permissions
        if "teacher" in roles_dict:
            academic_codenames = {
                "view_student_records",
                "view_grades",
                "assign_grades",
                "view_attendance",
                "mark_attendance",
                "modify_course_content",
            }
            for permission in permissions_list:
                if permission.codename in academic_codenames:
                    rp = RolePermissionFactory(
                        role=roles_dict["teacher"],
                        permission=permission,
                        is_active=True,
                    )
                    role_permissions.append(rp)

        # Staff gets basic view permissions
        if "staff" in roles_dict:
            view_codenames = {"view_student_records", "view_grades", "view_attendance"}
            for permission in permissions_list:
                if permission.codename in view_codenames:
                    rp = RolePermissionFactory(role=roles_dict["staff"], permission=permission, is_active=True)
                    role_permissions.append(rp)

        return role_permissions

    @classmethod
    def create_complete_rbac_system(cls):
        """Create a complete RBAC system with departments, roles, and permissions."""
        # Create multiple departments
        cs_system = cls.create_academic_department_hierarchy("Computer Science Department")
        eng_system = cls.create_academic_department_hierarchy("English Language Department")
        math_system = cls.create_academic_department_hierarchy("Mathematics Department")

        # Create global roles
        global_admin = GlobalRoleFactory(
            name="System Administrator",
            role_type=Role.RoleType.DIRECTOR,
            can_approve=True,
            can_edit=True,
            can_view=True,
        )

        global_student = GlobalRoleFactory(
            name="Student",
            role_type=Role.RoleType.STUDENT,
            can_approve=False,
            can_edit=False,
            can_view=True,
        )

        # Create standard permissions
        permissions = cls.create_standard_permissions_set()

        # Assign permissions to each department's roles
        cs_role_permissions = cls.create_role_permissions_for_hierarchy(cs_system["roles"], permissions)
        eng_role_permissions = cls.create_role_permissions_for_hierarchy(eng_system["roles"], permissions)
        math_role_permissions = cls.create_role_permissions_for_hierarchy(math_system["roles"], permissions)

        # Global admin gets all permissions
        global_admin_permissions = []
        for permission in permissions:
            rp = RolePermissionFactory(
                role=global_admin,
                permission=permission,
                department=None,
                is_active=True,
            )
            global_admin_permissions.append(rp)

        return {
            "departments": [
                cs_system["department"],
                eng_system["department"],
                math_system["department"],
            ],
            "department_systems": {
                "cs": cs_system,
                "eng": eng_system,
                "math": math_system,
            },
            "global_roles": [global_admin, global_student],
            "permissions": permissions,
            "role_permissions": (
                cs_role_permissions + eng_role_permissions + math_role_permissions + global_admin_permissions
            ),
        }


class TeacherRoleScenarioFactory:
    """Factory for creating teacher-specific role scenarios."""

    @classmethod
    def create_teacher_with_course_permissions(cls, department=None):
        """Create a teacher role with typical course management permissions."""
        if not department:
            department = DepartmentFactory()

        teacher_role = RoleFactory(
            name=f"{department.name} Teacher",
            role_type=Role.RoleType.TEACHER,
            department=department,
            can_edit=True,
            can_view=True,
        )

        # Create course-related permissions
        course_permissions = [
            PermissionFactory(name="Can View Course Content", codename="view_course_content"),
            PermissionFactory(name="Can Edit Course Content", codename="edit_course_content"),
            PermissionFactory(name="Can Assign Grades", codename="assign_grades"),
            PermissionFactory(name="Can View Student Progress", codename="view_student_progress"),
            PermissionFactory(name="Can Mark Attendance", codename="mark_attendance"),
        ]

        # Assign permissions to teacher role
        role_permissions = []
        for permission in course_permissions:
            rp = RolePermissionFactory(role=teacher_role, permission=permission, department=department)
            role_permissions.append(rp)

        return {
            "role": teacher_role,
            "permissions": course_permissions,
            "role_permissions": role_permissions,
        }


class StudentRoleScenarioFactory:
    """Factory for creating student-specific role scenarios."""

    @classmethod
    def create_student_with_basic_permissions(cls):
        """Create a student role with basic view permissions."""
        student_role = GlobalRoleFactory(
            name="Student",
            role_type=Role.RoleType.STUDENT,
            can_approve=False,
            can_edit=False,
            can_view=True,
        )

        # Create student-specific permissions
        student_permissions = [
            PermissionFactory(name="Can View Own Records", codename="view_own_records"),
            PermissionFactory(name="Can View Own Grades", codename="view_own_grades"),
            PermissionFactory(name="Can View Own Schedule", codename="view_own_schedule"),
            PermissionFactory(name="Can Submit Assignments", codename="submit_assignments"),
        ]

        # Assign permissions to student role
        role_permissions = []
        for permission in student_permissions:
            rp = RolePermissionFactory(
                role=student_role,
                permission=permission,
                department=None,  # Global permissions
            )
            role_permissions.append(rp)

        return {
            "role": student_role,
            "permissions": student_permissions,
            "role_permissions": role_permissions,
        }
