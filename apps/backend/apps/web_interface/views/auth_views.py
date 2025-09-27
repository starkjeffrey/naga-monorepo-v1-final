"""
Authentication views for the web interface.

This module contains views for login, logout, role switching, and other
authentication-related functionality in the user-facing web interface.
"""

import logging

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, View

from ..forms.auth_forms import LoginForm, ProfileUpdateForm, RoleSwitchForm
from ..permissions import RoleBasedPermissionMixin
from ..utils import get_user_navigation, is_htmx_request

logger = logging.getLogger(__name__)


@method_decorator(never_cache, name="dispatch")
class LoginCenteredView(FormView):
    """
    Center-aligned login view with modern design.

    Beautiful centered login page with gradient background and modern styling.
    Maintains all functionality of the regular login view.
    """

    template_name = "web_interface/base/login_centered.html"
    form_class = LoginForm
    success_url = reverse_lazy("web_interface:dashboard")

    def dispatch(self, request, *args, **kwargs):
        """Redirect authenticated users to dashboard."""
        # Only redirect if user is authenticated
        if request.user.is_authenticated:
            return redirect("web_interface:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Add request to form kwargs for HTMX support."""
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        """Process successful login."""
        user = form.get_user()
        selected_role = form.cleaned_data["role"]

        # Log the user in
        auth_login(self.request, user)

        # Store the selected role in session
        self.request.session["user_role"] = selected_role
        self.request.session["role_permissions"] = get_user_navigation(user)

        logger.info(
            "User %s logged in successfully with role %s",
            user.email,
            selected_role,
        )

        # Handle HTMX requests with JSON response
        if is_htmx_request(self.request):
            return JsonResponse(
                {
                    "success": True,
                    "message": _("Login successful"),
                    "redirect_url": str(self.get_success_url()),
                }
            )

        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle form validation errors."""
        logger.warning("Login attempt failed: %s", form.errors)

        # For HTMX requests, return the form with errors
        if is_htmx_request(self.request):
            return self.render_to_response(self.get_context_data(form=form))

        return super().form_invalid(form)

    def get_client_ip(self):
        """Get client IP address from request."""
        x_forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = self.request.META.get("REMOTE_ADDR")
        return ip

    def get_context_data(self, **kwargs):
        """Add additional context for template."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": _("Login"),
                "hide_navigation": True,
            }
        )
        return context


class LogoutView(LoginRequiredMixin, View):
    """
    Logout view that clears session and redirects to login.

    Handles both regular requests and HTMX requests.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request for logout."""
        return self.logout_user()

    def post(self, request, *args, **kwargs):
        """Handle POST request for logout."""
        return self.logout_user()

    def logout_user(self):
        """
        Log out the user and clear session data.

        Returns appropriate response based on request type.
        """
        user_identifier = self.request.user.email if self.request.user.is_authenticated else "unknown"

        logger.info("User %s logged out from IP %s", user_identifier, self.get_client_ip())

        # Clear session data
        if "current_role" in self.request.session:
            del self.request.session["current_role"]

        # Log out user
        auth_logout(self.request)

        messages.info(self.request, _("You have been logged out successfully."))

        # Handle HTMX requests
        if is_htmx_request(self.request):
            return JsonResponse({"success": True, "redirect_url": reverse("web_interface:login")})

        return redirect("web_interface:login")

    def get_client_ip(self):
        """Get client IP address from request."""
        x_forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = self.request.META.get("REMOTE_ADDR")
        return ip


class RoleSwitchView(LoginRequiredMixin, FormView):
    """
    View for switching user roles during active session.

    Allows users with multiple roles to switch between them
    without re-authentication.
    """

    form_class = RoleSwitchForm
    template_name = "web_interface/auth/role_switch.html"

    def get_form_kwargs(self):
        """Add user to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Handle successful role switch."""
        new_role = form.cleaned_data["role"]
        old_role = self.request.session.get("current_role", "unknown")

        # Update role in session
        self.request.session["current_role"] = new_role

        logger.info("User %s switched role from %s to %s", self.request.user.email, old_role, new_role)

        messages.success(
            self.request, _("Role switched to {}.").format(dict(LoginForm.ROLE_CHOICES).get(new_role, new_role))
        )

        # Handle HTMX requests
        if is_htmx_request(self.request):
            return JsonResponse(
                {
                    "success": True,
                    "redirect_url": reverse("web_interface:dashboard"),
                    "message": _("Role switched successfully"),
                }
            )

        return redirect("web_interface:dashboard")

    def form_invalid(self, form):
        """Handle invalid role switch."""
        if is_htmx_request(self.request):
            return JsonResponse(
                {"success": False, "form_errors": form.errors, "error": _("Unable to switch to selected role.")},
                status=400,
            )

        return super().form_invalid(form)

    def get(self, request, *args, **kwargs):
        """Handle GET request - switch role if provided in query params."""
        role = request.GET.get("role")

        if role:
            # Create form with POST data to validate and switch role
            form = self.get_form_class()(user=request.user, data={"role": role})
            if form.is_valid():
                return self.form_valid(form)
            else:
                messages.error(request, _("Invalid role selection."))

        return super().get(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, FormView):
    """
    View for updating user profile information.

    Allows users to update their basic profile information.
    """

    template_name = "web_interface/auth/profile.html"
    form_class = ProfileUpdateForm
    success_url = reverse_lazy("web_interface:profile")

    def get_form_kwargs(self):
        """Add user instance to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Handle successful profile update."""
        user = form.save()

        logger.info("User %s updated their profile", user.email)

        messages.success(self.request, _("Your profile has been updated successfully."))

        if is_htmx_request(self.request):
            return JsonResponse({"success": True, "message": _("Profile updated successfully")})

        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle invalid profile update."""
        if is_htmx_request(self.request):
            return JsonResponse(
                {"success": False, "form_errors": form.errors, "error": _("Please correct the errors below.")},
                status=400,
            )

        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add additional context for template."""
        context = super().get_context_data(**kwargs)

        # Get user roles for display
        permission_mixin = RoleBasedPermissionMixin()
        user_roles = permission_mixin.get_user_roles(self.request.user)
        current_role = self.request.session.get("current_role")

        context.update(
            {
                "page_title": _("My Profile"),
                "user_roles": user_roles,
                "current_role": current_role,
                "navigation_data": get_user_navigation(self.request.user),
            }
        )
        return context


class SessionInfoView(LoginRequiredMixin, View):
    """
    API view to get current session information.

    Returns user info, current role, and navigation data as JSON.
    Used by JavaScript for dynamic UI updates.
    """

    def get(self, request, *args, **kwargs):
        """Return current session information as JSON."""
        permission_mixin = RoleBasedPermissionMixin()
        user_roles = permission_mixin.get_user_roles(request.user)
        current_role = request.session.get("current_role")

        data = {
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "full_name": request.user.get_full_name(),
                "is_superuser": request.user.is_superuser,
            },
            "roles": user_roles,
            "current_role": current_role,
            "navigation": get_user_navigation(request.user),
            "session": {
                "session_key": request.session.session_key,
                "expires": (
                    request.session.get_expiry_date().isoformat() if request.session.get_expiry_date() else None
                ),
            },
        }

        return JsonResponse(data)


# Utility functions for context processors
def auth_context_processor(request):
    """
    Context processor to add authentication-related context to all templates.

    Args:
        request: Django request object

    Returns:
        Dict with authentication context
    """
    context = {
        "current_role": None,
        "user_roles": [],
        "navigation_data": [],
    }

    if request.user.is_authenticated:
        permission_mixin = RoleBasedPermissionMixin()
        user_roles = permission_mixin.get_user_roles(request.user)
        current_role = request.session.get("current_role")

        context.update(
            {
                "current_role": current_role,
                "user_roles": user_roles,
                "navigation_data": get_user_navigation(request.user),
            }
        )

    return context
