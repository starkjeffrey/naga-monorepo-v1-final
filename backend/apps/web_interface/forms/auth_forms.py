"""
Authentication forms for the web interface.

This module contains forms for login, role selection, and authentication
functionality in the user-facing web interface.
"""

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..permissions import RoleBasedPermissionMixin

User = get_user_model()


class LoginForm(AuthenticationForm):
    """
    Custom login form with role selection.

    Extends Django's AuthenticationForm to include role selection
    and enhanced validation for the web interface.
    """

    ROLE_CHOICES = [
        ("student", _("Student")),
        ("teacher", _("Teacher")),
        ("staff", _("Academic Staff")),
        ("finance", _("Financial Staff")),
        ("admin", _("Administrator")),
    ]

    username = forms.CharField(
        label=_("Email"),
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your PUCSR email address"),
                "autocomplete": "email",
                "autofocus": True,
            }
        ),
    )

    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your password"),
                "autocomplete": "current-password",
            }
        ),
    )

    role = forms.ChoiceField(
        label=_("Login As"),
        choices=ROLE_CHOICES,
        initial="student",
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    remember_me = forms.BooleanField(
        label=_("Remember me"),
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )

    def __init__(self, request=None, *args, **kwargs):
        """Initialize form with request context."""
        super().__init__(request, *args, **kwargs)
        self.user_cache = None
        self.selected_role = None

        # Remove default error messages to customize them
        self.error_messages = {
            "invalid_login": _(
                "The email and password you entered do not match. Please check your credentials and try again."
            ),
            "inactive": _("This account is inactive."),
            "invalid_role": _("You do not have permission to login with this role."),
            "email_not_found": _("No account found with this email address."),
            "incorrect_password": _("The password you entered is incorrect."),
        }

    def clean_username(self):
        """Clean and validate username field."""
        username = self.cleaned_data.get("username")
        if username:
            username = username.strip().lower()
        return username

    def clean_role(self):
        """Clean and validate role field."""
        role = self.cleaned_data.get("role")
        if role not in dict(self.ROLE_CHOICES):
            raise ValidationError(_("Invalid role selected."))
        return role

    def clean(self):
        """
        Validate login credentials and role permissions.

        This method performs authentication and verifies that the user
        has permission to login with the selected role.
        """
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        role = self.cleaned_data.get("role")

        if username is not None and password:
            # Since the User model uses email as the identifier, try email auth directly
            # The user can enter their email in the username field
            self.user_cache = authenticate(self.request, email=username, password=password)

            if self.user_cache is None:
                # Check if the email exists to provide a more specific error
                from django.contrib.auth import get_user_model

                User = get_user_model()
                try:
                    User.objects.get(email=username)
                    # Email exists but password is wrong
                    raise ValidationError(
                        self.error_messages["invalid_login"],
                        code="invalid_login",
                    )
                except User.DoesNotExist:
                    # Email doesn't exist
                    raise ValidationError(
                        self.error_messages["invalid_login"],
                        code="invalid_login",
                    ) from None
            else:
                self.confirm_login_allowed(self.user_cache)

                # Validate role permissions
                if role:
                    if not self.validate_user_role(self.user_cache, role):
                        raise ValidationError(self.error_messages["invalid_role"], code="invalid_role")
                    self.selected_role = role

        return self.cleaned_data

    def validate_user_role(self, user, role):
        """
        Validate that the user has permission to login with the selected role.

        Args:
            user: User instance
            role: Selected role

        Returns:
            bool: True if user can use this role
        """
        permission_mixin = RoleBasedPermissionMixin()
        user_roles = permission_mixin.get_user_roles(user)

        # Admin can login as any role
        if "admin" in user_roles:
            return True

        # Check if user has the selected role
        return role in user_roles

    def get_user(self):
        """Return authenticated user."""
        return self.user_cache

    def get_selected_role(self):
        """Return selected role."""
        return self.selected_role


class RoleSwitchForm(forms.Form):
    """
    Form for switching user roles during an active session.

    Allows users with multiple roles to switch between them
    without re-authenticating.
    """

    role = forms.ChoiceField(
        label=_("Switch to Role"),
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    def __init__(self, user=None, *args, **kwargs):
        """
        Initialize form with user's available roles.

        Args:
            user: User instance to get roles for
        """
        super().__init__(*args, **kwargs)
        self.user = user

        if user and user.is_authenticated:
            permission_mixin = RoleBasedPermissionMixin()
            user_roles = permission_mixin.get_user_roles(user)

            # Create choices from user's available roles
            role_choices = []
            role_labels = dict(LoginForm.ROLE_CHOICES)

            for role in user_roles:
                if role in role_labels:
                    role_choices.append((role, role_labels[role]))

            self.fields["role"].choices = role_choices
        else:
            self.fields["role"].choices = []

    def clean_role(self):
        """Validate that the user can switch to the selected role."""
        role = self.cleaned_data.get("role")

        if not self.user or not self.user.is_authenticated:
            raise ValidationError(_("User must be authenticated to switch roles."))

        permission_mixin = RoleBasedPermissionMixin()
        user_roles = permission_mixin.get_user_roles(self.user)

        if role not in user_roles:
            raise ValidationError(_("You do not have permission to use this role."))

        return role


class PasswordResetRequestForm(forms.Form):
    """
    Form for requesting password reset.

    Allows users to request password reset using email address.
    """

    email = forms.EmailField(
        label=_("Email Address"),
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your email address"),
                "autocomplete": "email",
            }
        ),
    )

    def clean_email(self):
        """Validate that the email exists in the system."""
        email = self.cleaned_data.get("email")

        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                raise ValidationError(_("This account is inactive."))
        except User.DoesNotExist:
            # Don't reveal whether email exists for security
            # But still validate the form
            pass

        return email


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile information.

    Allows users to update their basic profile information
    through the web interface.
    """

    first_name = forms.CharField(
        label=_("First Name"),
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    last_name = forms.CharField(
        label=_("Last Name"),
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    email = forms.EmailField(
        label=_("Email Address"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        """Validate email uniqueness."""
        email = self.cleaned_data.get("email")

        if email:
            # Check if email is already used by another user
            qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_("This email address is already in use."))

        return email
