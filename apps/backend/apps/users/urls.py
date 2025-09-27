"""URL configuration for the users app."""

from django.urls import path

from .views import permissions

app_name = "users"

urlpatterns = [
    # Main permission dashboard
    path("permissions/", permissions.PermissionDashboardView.as_view(), name="permission_dashboard"),
    # Role management
    path("role/<int:role_id>/details/", permissions.role_details, name="role_details"),
    path("create-role/", permissions.create_role_form, name="create_role"),
    path("role/<int:role_id>/delete/", permissions.delete_role, name="delete_role"),
    # Permission management
    path("toggle-permission/", permissions.toggle_permission, name="toggle_permission"),
    # User management
    path("search/", permissions.search_users, name="search_users"),
    path("user/<int:user_id>/assign-role/", permissions.assign_user_role, name="assign_user_role"),
    path("user/<int:user_id>/profile/", permissions.user_profile_modal, name="user_profile"),
    # Audit and reporting
    path("audit-log/", permissions.audit_log, name="audit_log"),
]
