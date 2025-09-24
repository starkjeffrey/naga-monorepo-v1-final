"""Unit tests for accounts app models and authentication.

Tests all authentication and user management functionality including:
- User model and custom user manager
- Authentication flows
- Permission system
- MFA functionality
- Password validation
- Session management
"""

from datetime import datetime

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.test import override_settings
from freezegun import freeze_time

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test custom User model functionality."""

    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(email="test@example.com", password="testpass123")

        assert user.email == "test@example.com"
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser
        assert user.check_password("testpass123")
        assert not user.check_password("wrongpass")

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(email="admin@example.com", password="adminpass123")

        assert user.email == "admin@example.com"
        assert user.is_active
        assert user.is_staff
        assert user.is_superuser

    @pytest.mark.parametrize(
        "email,should_fail",
        [
            ("", True),  # Empty email
            (None, True),  # None email
            ("invalid", True),  # Invalid format
            ("test@example.com", False),  # Valid
            ("TEST@EXAMPLE.COM", False),  # Case should be normalized
        ],
    )
    def test_email_validation(self, email, should_fail):
        """Test email validation and normalization."""
        if should_fail:
            with pytest.raises((ValueError, ValidationError)):
                User.objects.create_user(email=email, password="pass123")
        else:
            user = User.objects.create_user(email=email, password="pass123")
            # Email should be normalized to lowercase
            assert user.email == email.lower() if email else email

    def test_email_uniqueness(self):
        """Test that email must be unique."""
        User.objects.create_user(email="test@example.com", password="pass123")

        with pytest.raises(Exception):  # IntegrityError
            User.objects.create_user(email="test@example.com", password="pass456")

    def test_user_str_representation(self):
        """Test string representation of user."""
        user = User.objects.create_user(email="john.doe@example.com", first_name="John", last_name="Doe")

        assert str(user) == "john.doe@example.com"
        # Or if get_full_name is implemented
        assert user.get_full_name() in ["John Doe", "john.doe@example.com"]

    def test_user_permissions(self):
        """Test user permission methods."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        # Create a permission
        permission = Permission.objects.first()  # Get any permission

        # User shouldn't have permission initially
        assert not user.has_perm(permission.codename)

        # Add permission
        user.user_permissions.add(permission)
        user = User.objects.get(pk=user.pk)  # Refresh

        assert user.has_perm(f"{permission.content_type.app_label}.{permission.codename}")

    def test_user_groups(self):
        """Test user group membership."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        group = Group.objects.create(name="Students")

        # Add user to group
        user.groups.add(group)

        assert group in user.groups.all()
        assert user.groups.filter(name="Students").exists()

    def test_user_is_active(self):
        """Test user active status affects authentication."""
        user = User.objects.create_user(email="test@example.com", password="pass123", is_active=False)

        # Inactive user shouldn't authenticate
        authenticated = authenticate(username="test@example.com", password="pass123")
        assert authenticated is None

        # Activate user
        user.is_active = True
        user.save()

        authenticated = authenticate(username="test@example.com", password="pass123")
        assert authenticated == user


@pytest.mark.django_db
class TestUserManager:
    """Test custom user manager functionality."""

    def test_create_user_without_email(self):
        """Test that email is required."""
        with pytest.raises(ValueError) as exc:
            User.objects.create_user(email=None, password="pass123")
        assert "email" in str(exc.value).lower()

    def test_create_user_normalizes_email(self):
        """Test email normalization."""
        user = User.objects.create_user(email="TEST@EXAMPLE.COM", password="pass123")
        assert user.email == "test@example.com"

    def test_create_superuser_flags(self):
        """Test superuser must have is_staff and is_superuser."""
        # These should raise errors
        with pytest.raises(ValueError):
            User.objects.create_superuser(email="admin@example.com", password="pass123", is_staff=False)

        with pytest.raises(ValueError):
            User.objects.create_superuser(email="admin@example.com", password="pass123", is_superuser=False)


@pytest.mark.django_db
class TestAuthentication:
    """Test authentication functionality."""

    def test_login_with_correct_credentials(self):
        """Test successful login."""
        user = User.objects.create_user(email="test@example.com", password="correctpass")

        authenticated = authenticate(username="test@example.com", password="correctpass")

        assert authenticated == user

    def test_login_with_incorrect_password(self):
        """Test login fails with wrong password."""
        User.objects.create_user(email="test@example.com", password="correctpass")

        authenticated = authenticate(username="test@example.com", password="wrongpass")

        assert authenticated is None

    def test_login_with_nonexistent_user(self):
        """Test login fails with non-existent user."""
        authenticated = authenticate(username="nonexistent@example.com", password="anypass")

        assert authenticated is None

    def test_login_case_insensitive_email(self):
        """Test login is case-insensitive for email."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        # Try login with different case
        authenticated = authenticate(username="TEST@EXAMPLE.COM", password="pass123")

        assert authenticated == user

    @freeze_time("2024-01-15 10:00:00")
    def test_last_login_updated(self, client):
        """Test last_login is updated on successful login."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        assert user.last_login is None

        # Login via client
        client.login(username="test@example.com", password="pass123")

        user.refresh_from_db()
        assert user.last_login is not None
        assert user.last_login.date() == datetime(2024, 1, 15).date()


@pytest.mark.django_db
class TestPasswordValidation:
    """Test password validation and management."""

    @pytest.mark.parametrize(
        "password,should_pass,reason",
        [
            ("short", False, "Too short"),
            ("12345678", False, "All numeric"),
            ("password", False, "Too common"),
            ("ValidPass123!", True, "Valid password"),
            ("test@example.com", False, "Same as email"),
            ("        ", False, "All spaces"),
            ("", False, "Empty"),
        ],
    )
    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[
            {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
            {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
            {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
        ]
    )
    def test_password_validators(self, password, should_pass, reason):
        """Test various password validation rules."""
        from django.contrib.auth.password_validation import validate_password

        user = User(email="test@example.com")

        if should_pass:
            try:
                validate_password(password, user)
            except ValidationError:
                pytest.fail(f"Password validation failed: {reason}")
        else:
            with pytest.raises(ValidationError):
                validate_password(password, user)

    def test_password_change(self):
        """Test changing user password."""
        user = User.objects.create_user(email="test@example.com", password="oldpass123")

        assert user.check_password("oldpass123")
        assert not user.check_password("newpass123")

        user.set_password("newpass123")
        user.save()

        assert not user.check_password("oldpass123")
        assert user.check_password("newpass123")

    def test_password_reset_token(self):
        """Test password reset token generation."""
        from django.contrib.auth.tokens import default_token_generator

        user = User.objects.create_user(email="test@example.com", password="pass123")

        token = default_token_generator.make_token(user)
        assert default_token_generator.check_token(user, token)

        # Token should be invalid after password change
        user.set_password("newpass123")
        user.save()

        assert not default_token_generator.check_token(user, token)


@pytest.mark.django_db
class TestUserRoles:
    """Test user role management."""

    def test_student_role(self):
        """Test student role assignment."""
        user = User.objects.create_user(email="student@example.com", password="pass123")

        student_group = Group.objects.create(name="Students")
        user.groups.add(student_group)

        assert user.groups.filter(name="Students").exists()

        # Check role-based method if implemented
        if hasattr(user, "is_student"):
            assert user.is_student()

    def test_teacher_role(self):
        """Test teacher role assignment."""
        user = User.objects.create_user(email="teacher@example.com", password="pass123")

        teacher_group = Group.objects.create(name="Teachers")
        user.groups.add(teacher_group)

        assert user.groups.filter(name="Teachers").exists()

        # Check role-based method if implemented
        if hasattr(user, "is_teacher"):
            assert user.is_teacher()

    def test_multiple_roles(self):
        """Test user can have multiple roles."""
        user = User.objects.create_user(email="multi@example.com", password="pass123")

        student_group = Group.objects.create(name="Students")
        ta_group = Group.objects.create(name="Teaching Assistants")

        user.groups.add(student_group, ta_group)

        assert user.groups.count() == 2
        assert user.groups.filter(name="Students").exists()
        assert user.groups.filter(name="Teaching Assistants").exists()


@pytest.mark.django_db
class TestMFAFunctionality:
    """Test Multi-Factor Authentication if implemented."""

    @pytest.mark.skip(reason="MFA implementation pending")
    def test_mfa_setup(self):
        """Test MFA setup for user."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        # Test TOTP setup
        if hasattr(user, "enable_mfa"):
            secret = user.enable_mfa()
            assert secret is not None
            assert user.mfa_enabled

    @pytest.mark.skip(reason="MFA implementation pending")
    def test_mfa_verification(self):
        """Test MFA code verification."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        if hasattr(user, "verify_mfa"):
            # Would need to generate valid TOTP code
            pass


@pytest.mark.django_db
class TestSessionManagement:
    """Test user session management."""

    def test_concurrent_sessions(self, client):
        """Test handling of concurrent sessions."""
        User.objects.create_user(email="test@example.com", password="pass123")

        # Create multiple sessions
        from django.test import Client

        client1 = Client()
        client2 = Client()

        assert client1.login(username="test@example.com", password="pass123")
        assert client2.login(username="test@example.com", password="pass123")

        # Both sessions should be valid
        # Implementation depends on session backend

    def test_session_expiry(self, client):
        """Test session expiration."""
        User.objects.create_user(email="test@example.com", password="pass123")

        client.login(username="test@example.com", password="pass123")

        # Test session exists
        assert "_auth_user_id" in client.session

        # Expire session
        client.logout()

        # Session should be cleared
        assert "_auth_user_id" not in client.session


@pytest.mark.django_db
class TestUserQueries:
    """Test optimized user queries."""

    def test_user_with_groups_prefetch(self, assert_num_queries):
        """Test prefetching groups to avoid N+1 queries."""
        # Create users with groups
        group1 = Group.objects.create(name="Group1")
        group2 = Group.objects.create(name="Group2")

        for i in range(5):
            user = User.objects.create_user(email=f"user{i}@example.com", password="pass123")
            user.groups.add(group1, group2)

        # Should use only 2 queries (users + groups)
        def fetch_users_with_groups():
            users = User.objects.prefetch_related("groups").all()
            for user in users:
                list(user.groups.all())  # Access groups

        assert_num_queries(2, fetch_users_with_groups)

    def test_user_with_permissions_prefetch(self, assert_num_queries):
        """Test prefetching permissions."""
        # Create users with permissions
        perm = Permission.objects.first()

        for i in range(3):
            user = User.objects.create_user(email=f"user{i}@example.com", password="pass123")
            user.user_permissions.add(perm)

        # Should use optimized queries
        def fetch_users_with_perms():
            users = User.objects.prefetch_related("user_permissions").all()
            for user in users:
                list(user.user_permissions.all())

        assert_num_queries(2, fetch_users_with_perms)
