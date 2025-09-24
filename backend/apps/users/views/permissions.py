"""Role-based access control interface.

This module provides comprehensive user role and permission management including:
- Role creation, modification, and deletion
- Permission assignment and revocation
- User role assignments with HTMX real-time updates
- Permission matrix for visual management
- Audit logging for all permission changes
"""

import json
import logging

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group, Permission
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from users.models import User

logger = logging.getLogger(__name__)


class PermissionDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Main permission management dashboard."""

    template_name = "users/permission_dashboard.html"
    permission_required = "auth.view_group"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all roles with their permissions and user counts
        roles = Group.objects.prefetch_related(
            "permissions", "user_set__studentprofile", "user_set__teacherprofile"
        ).annotate(user_count=Count("user"))

        # Get users with their profiles and groups
        users = (
            User.objects.select_related()
            .prefetch_related("groups", "user_permissions", "studentprofile", "teacherprofile")
            .order_by("email")
        )

        # Calculate role statistics
        role_stats = {}
        for role in roles:
            role_stats[role.name] = {"users": role.user_count, "permissions": role.permissions.count()}

        # Get available permissions organized by content type
        available_permissions = Permission.objects.select_related("content_type").order_by(
            "content_type__app_label", "content_type__model", "codename"
        )

        # Organize permissions by app and model
        permissions_by_app = {}
        for perm in available_permissions:
            app_label = perm.content_type.app_label
            model_name = perm.content_type.model

            if app_label not in permissions_by_app:
                permissions_by_app[app_label] = {}
            if model_name not in permissions_by_app[app_label]:
                permissions_by_app[app_label][model_name] = []

            permissions_by_app[app_label][model_name].append(perm)

        # Get permission audit log (recent changes)
        # TODO: Implement permission audit model
        recent_changes = []

        context.update(
            {
                "roles": roles,
                "users": users[:100],  # Limit for performance
                "role_stats": role_stats,
                "permissions_by_app": permissions_by_app,
                "recent_changes": recent_changes,
            }
        )

        return context


@login_required
@permission_required("auth.view_group")
def role_details(request, role_id):
    """HTMX endpoint for role detail view."""
    role = get_object_or_404(Group, id=role_id)

    # Get role permissions
    role_permissions = role.permissions.select_related("content_type").order_by(
        "content_type__app_label", "content_type__model", "codename"
    )

    # Get users with this role
    role_users = (
        User.objects.filter(groups=role)
        .select_related()
        .prefetch_related("studentprofile", "teacherprofile")
        .order_by("email")
    )

    # Organize permissions by app
    permissions_by_app = {}
    for perm in role_permissions:
        app_label = perm.content_type.app_label
        if app_label not in permissions_by_app:
            permissions_by_app[app_label] = []
        permissions_by_app[app_label].append(perm)

    context = {
        "role": role,
        "role_permissions": role_permissions,
        "permissions_by_app": permissions_by_app,
        "role_users": role_users,
    }

    return render(request, "users/partials/role_details.html", context)


@login_required
@permission_required("auth.change_group")
@require_http_methods(["POST"])
def toggle_permission(request):
    """HTMX endpoint for toggling role permissions."""
    try:
        data = json.loads(request.body)
        role_id = data.get("role_id")
        permission_codename = data.get("permission")

        if not role_id or not permission_codename:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        role = get_object_or_404(Group, id=role_id)
        permission = get_object_or_404(Permission, codename=permission_codename)

        # Toggle permission
        if permission in role.permissions.all():
            role.permissions.remove(permission)
            action = "removed"
        else:
            role.permissions.add(permission)
            action = "added"

        logger.info(f"Permission {permission.codename} {action} for role {role.name} by {request.user.email}")

        return JsonResponse(
            {
                "success": True,
                "action": action,
                "message": f"Permission {permission.name} {action} for {role.name}",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        logger.error(f"Error toggling permission: {e}")
        return JsonResponse({"error": "Failed to update permission"}, status=500)


@login_required
@permission_required("auth.view_user")
def search_users(request):
    """HTMX endpoint for user search."""
    query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "")

    if not query or len(query) < 2:
        users = User.objects.none()
    else:
        users = (
            User.objects.filter(
                Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
            )
            .select_related()
            .prefetch_related("groups", "studentprofile", "teacherprofile")
        )

    # Filter by role if specified
    if role_filter:
        try:
            role = Group.objects.get(id=role_filter)
            users = users.filter(groups=role)
        except Group.DoesNotExist:
            pass

    users = users.order_by("email")[:20]  # Limit results

    context = {
        "users": users,
        "query": query,
    }

    return render(request, "users/partials/user_list.html", context)


@login_required
@permission_required("auth.change_user")
@require_http_methods(["POST"])
def assign_user_role(request, user_id):
    """HTMX endpoint for assigning/removing user roles."""
    user = get_object_or_404(User, id=user_id)
    role_id = request.POST.get("role_id")
    action = request.POST.get("action")  # 'add' or 'remove'

    if not role_id or action not in ["add", "remove"]:
        return JsonResponse({"error": "Invalid request parameters"}, status=400)

    try:
        role = Group.objects.get(id=role_id)

        if action == "add":
            user.groups.add(role)
            message = f"Added {role.name} role to {user.get_full_name() or user.email}"
        else:
            user.groups.remove(role)
            message = f"Removed {role.name} role from {user.get_full_name() or user.email}"

        logger.info(f"Role {role.name} {action}ed for user {user.email} by {request.user.email}")

        return JsonResponse(
            {
                "success": True,
                "message": message,
            }
        )

    except Group.DoesNotExist:
        return JsonResponse({"error": "Role not found"}, status=404)
    except Exception as e:
        logger.error(f"Error assigning user role: {e}")
        return JsonResponse({"error": "Failed to update user role"}, status=500)


@login_required
@permission_required("auth.add_group")
def create_role_form(request):
    """HTMX endpoint for role creation form."""
    if request.method == "POST":
        role_name = request.POST.get("role_name", "").strip()
        request.POST.get("role_description", "").strip()
        permissions = request.POST.getlist("permissions")

        if not role_name:
            return JsonResponse({"error": "Role name is required"}, status=400)

        # Check if role already exists
        if Group.objects.filter(name=role_name).exists():
            return JsonResponse({"error": "Role with this name already exists"}, status=400)

        try:
            role = Group.objects.create(name=role_name)

            if permissions:
                permission_objects = Permission.objects.filter(id__in=permissions)
                role.permissions.set(permission_objects)

            logger.info(f"Role {role_name} created by {request.user.email}")

            return JsonResponse(
                {
                    "success": True,
                    "message": f'Role "{role_name}" created successfully',
                    "role_id": role.id,
                }
            )

        except Exception as e:
            logger.error(f"Error creating role: {e}")
            return JsonResponse({"error": "Failed to create role"}, status=500)

    # GET request - show form
    available_permissions = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label", "content_type__model", "codename"
    )

    # Group permissions by app for better organization
    permissions_by_app = {}
    for perm in available_permissions:
        app_label = perm.content_type.app_label
        if app_label not in permissions_by_app:
            permissions_by_app[app_label] = []
        permissions_by_app[app_label].append(perm)

    context = {
        "permissions_by_app": permissions_by_app,
    }

    return render(request, "users/partials/create_role_form.html", context)


@login_required
@permission_required("auth.view_group")
def audit_log(request):
    """HTMX endpoint for permission audit log."""
    # TODO: Implement proper audit logging model
    # For now, return empty log

    audit_entries = []

    context = {
        "audit_entries": audit_entries,
    }

    return render(request, "users/partials/audit_log.html", context)


@login_required
@permission_required("auth.delete_group")
@require_http_methods(["POST"])
def delete_role(request, role_id):
    """Delete a role with confirmation."""
    role = get_object_or_404(Group, id=role_id)

    # Prevent deletion of system roles
    system_roles = ["Admin", "Staff", "Teacher", "Student"]
    if role.name in system_roles:
        return JsonResponse({"error": "Cannot delete system roles"}, status=400)

    # Check if role has users
    user_count = role.user_set.count()
    if user_count > 0:
        return JsonResponse({"error": f"Cannot delete role with {user_count} assigned users"}, status=400)

    try:
        role_name = role.name
        role.delete()

        logger.info(f"Role {role_name} deleted by {request.user.email}")

        return JsonResponse(
            {
                "success": True,
                "message": f'Role "{role_name}" deleted successfully',
            }
        )

    except Exception as e:
        logger.error(f"Error deleting role: {e}")
        return JsonResponse({"error": "Failed to delete role"}, status=500)


@login_required
@permission_required("auth.view_user")
def user_profile_modal(request, user_id):
    """HTMX endpoint for user profile modal."""
    user = get_object_or_404(
        User.objects.select_related().prefetch_related(
            "groups", "user_permissions", "studentprofile", "teacherprofile"
        ),
        id=user_id,
    )

    # Get all available roles for assignment
    available_roles = Group.objects.all().order_by("name")
    user_roles = user.groups.all()

    context = {
        "profile_user": user,  # Named differently to avoid conflict with request.user
        "available_roles": available_roles,
        "user_roles": user_roles,
    }

    return render(request, "users/partials/user_profile_modal.html", context)
