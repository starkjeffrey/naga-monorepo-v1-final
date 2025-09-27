"""Tests for the people app admin interfaces.

This test module validates admin functionality including:
- Permission-based admin actions
- N+1 query optimization
- Admin interface security
- Custom admin methods and displays
"""

from unittest.mock import Mock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase

from apps.people.admin import StudentProfileAdmin
from apps.people.models import Person, StudentProfile

User = get_user_model()


class AdminPermissionTest(TestCase):
    """Test admin permission functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = StudentProfileAdmin(StudentProfile, self.site)

        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
            is_staff=True,
            is_superuser=True,
        )

        self.regular_user = User.objects.create_user(
            email="regular@test.com",
            password="testpass",
            is_staff=True,
        )

        self.limited_user = User.objects.create_user(
            email="limited@test.com",
            password="testpass",
            is_staff=True,
        )

        # Create person and student
        self.person = Person.objects.create(
            family_name="Test",
            personal_name="Student",
        )
        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=12345,
            current_status=StudentProfile.Status.INACTIVE,
        )

        # Add specific permissions to limited user
        content_type = ContentType.objects.get_for_model(StudentProfile)
        activate_permission = Permission.objects.get(
            codename="can_activate_student",
            content_type=content_type,
        )
        self.limited_user.user_permissions.add(activate_permission)

    def test_admin_user_has_all_permissions(self):
        """Test that admin users have all permissions."""
        request = self.factory.get("/")
        request.user = self.admin_user

        assert self.admin.has_activate_student_permission(request)
        assert self.admin.has_deactivate_student_permission(request)

    def test_regular_user_has_no_special_permissions(self):
        """Test that regular users have no special permissions."""
        request = self.factory.get("/")
        request.user = self.regular_user

        assert not self.admin.has_activate_student_permission(request)
        assert not self.admin.has_deactivate_student_permission(request)

    def test_limited_user_has_specific_permissions(self):
        """Test that users with specific permissions can perform specific actions."""
        request = self.factory.get("/")
        request.user = self.limited_user

        assert self.admin.has_activate_student_permission(request)
        assert not self.admin.has_deactivate_student_permission(request)

    def test_get_actions_filters_by_permissions(self):
        """Test that admin actions are filtered based on user permissions."""
        # Admin user should see all actions
        request = self.factory.get("/")
        request.user = self.admin_user
        actions = self.admin.get_actions(request)
        assert "activate_students" in actions
        assert "deactivate_students" in actions

        # Regular user should see no special actions
        request.user = self.regular_user
        actions = self.admin.get_actions(request)
        assert "activate_students" not in actions
        assert "deactivate_students" not in actions

        # Limited user should see only activate action
        request.user = self.limited_user
        actions = self.admin.get_actions(request)
        assert "activate_students" in actions
        assert "deactivate_students" not in actions

    def test_activate_students_action_with_permission(self):
        """Test activate students action with proper permissions."""
        request = self.factory.post("/")
        request.user = self.admin_user
        request._messages = Mock()  # Mock messages framework

        queryset = StudentProfile.objects.filter(pk=self.student.pk)

        # Mock SystemAuditLog to avoid dependency
        with patch("apps.people.admin.SystemAuditLog") as mock_audit:
            self.admin.activate_students(request, queryset)

        # Verify student was activated
        self.student.refresh_from_db()
        assert self.student.current_status == StudentProfile.Status.ACTIVE

        # Verify audit log was called
        mock_audit.log_override.assert_called_once()

    def test_activate_students_action_without_permission(self):
        """Test activate students action without proper permissions."""
        request = self.factory.post("/")
        request.user = self.regular_user
        request._messages = Mock()  # Mock messages framework

        queryset = StudentProfile.objects.filter(pk=self.student.pk)

        self.admin.activate_students(request, queryset)

        # Verify student was NOT activated
        self.student.refresh_from_db()
        assert self.student.current_status == StudentProfile.Status.INACTIVE

        # Verify error message was sent
        request._messages.add.assert_called_with(
            request._messages.ERROR,
            "You do not have permission to activate students.",
            "",
        )

    def test_deactivate_students_action_with_permission(self):
        """Test deactivate students action with proper permissions."""
        # Set student to active first
        self.student.current_status = StudentProfile.Status.ACTIVE
        self.student.save()

        request = self.factory.post("/")
        request.user = self.admin_user
        request._messages = Mock()  # Mock messages framework

        queryset = StudentProfile.objects.filter(pk=self.student.pk)

        # Mock SystemAuditLog to avoid dependency
        with patch("apps.people.admin.SystemAuditLog") as mock_audit:
            self.admin.deactivate_students(request, queryset)

        # Verify student was deactivated
        self.student.refresh_from_db()
        assert self.student.current_status == StudentProfile.Status.INACTIVE

        # Verify audit log was called
        mock_audit.log_override.assert_called_once()

    def test_deactivate_students_action_without_permission(self):
        """Test deactivate students action without proper permissions."""
        # Set student to active first
        self.student.current_status = StudentProfile.Status.ACTIVE
        self.student.save()

        request = self.factory.post("/")
        request.user = self.regular_user
        request._messages = Mock()  # Mock messages framework

        queryset = StudentProfile.objects.filter(pk=self.student.pk)

        self.admin.deactivate_students(request, queryset)

        # Verify student was NOT deactivated
        self.student.refresh_from_db()
        assert self.student.current_status == StudentProfile.Status.ACTIVE

        # Verify error message was sent
        request._messages.add.assert_called_with(
            request._messages.ERROR,
            "You do not have permission to deactivate students.",
            "",
        )


class AdminQueryOptimizationTest(TestCase):
    """Test admin query optimization."""

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = StudentProfileAdmin(StudentProfile, self.site)

        # Create test data
        for i in range(5):
            person = Person.objects.create(
                family_name=f"Family{i}",
                personal_name=f"Person{i}",
            )
            StudentProfile.objects.create(
                person=person,
                student_id=10000 + i,
            )

    def test_get_queryset_uses_select_related(self):
        """Test that get_queryset uses select_related to prevent N+1 queries."""
        request = Mock()
        queryset = self.admin.get_queryset(request)

        # Check that select_related was applied
        assert "person" in queryset.query.select_related

    def test_admin_list_display_avoids_n_plus_one(self):
        """Test that admin list display methods don't cause N+1 queries."""
        request = Mock()
        queryset = self.admin.get_queryset(request)

        # Get all students
        students = list(queryset)

        # Reset queries
        with self.assertNumQueries(0):
            # These should not cause additional queries due to select_related
            for student in students:
                # This accesses person.full_name, which should be prefetched
                self.admin.person_name(student)


class AdminDisplayMethodTest(TestCase):
    """Test admin display methods."""

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = StudentProfileAdmin(StudentProfile, self.site)

        self.person = Person.objects.create(
            family_name="Test",
            personal_name="Person",
        )
        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=12345,
        )

    def test_person_name_display(self):
        """Test person_name display method."""
        result = self.admin.person_name(self.student)
        assert result == "TEST PERSON"

    def test_program_display_placeholder(self):
        """Test program_display placeholder method."""
        result = self.admin.program_display(self.student)
        assert result == "Multiple Programs"

    def test_gpa_display_placeholder(self):
        """Test gpa_display placeholder method."""
        result = self.admin.gpa_display(self.student)
        assert result == "N/A"
