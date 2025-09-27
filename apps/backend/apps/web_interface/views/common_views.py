"""
Common views for the web interface.

This module contains shared views and utilities used across the web interface.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from ..permissions import RoleBasedPermissionMixin


class AboutView(LoginRequiredMixin, TemplateView):
    """About page for the web interface."""

    template_name = "web_interface/pages/common/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": _("About Naga SIS"),
                "system_info": {
                    "name": "Naga Student Information System",
                    "version": "1.0",
                    "university": "Pannasastra University of Cambodia",
                    "campus": "Siem Reap Campus",
                },
            }
        )
        return context


class HelpView(LoginRequiredMixin, TemplateView):
    """Help page for the web interface."""

    template_name = "web_interface/pages/common/help.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": _("Help & Support"),
                "help_sections": [
                    {
                        "title": _("Getting Started"),
                        "items": [_("How to log in"), _("Navigating the dashboard"), _("Switching roles")],
                    },
                    {
                        "title": _("Student Management"),
                        "items": [
                            _("Adding new students"),
                            _("Updating student information"),
                            _("Managing enrollment"),
                        ],
                    },
                    {
                        "title": _("Academic Records"),
                        "items": [_("Viewing grades"), _("Managing transcripts"), _("Course enrollment")],
                    },
                    {
                        "title": _("Finance"),
                        "items": [_("Creating invoices"), _("Processing payments"), _("Financial reports")],
                    },
                ],
            }
        )
        return context


class SettingsView(RoleBasedPermissionMixin, LoginRequiredMixin, TemplateView):
    """Settings page for the web interface."""

    template_name = "web_interface/pages/common/settings.html"
    required_role = "staff"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": _("Settings"),
                "user_preferences": {"language": "en", "timezone": "Asia/Phnom_Penh", "dashboard_layout": "default"},
            }
        )
        return context
