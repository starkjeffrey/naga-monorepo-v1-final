"""
Dashboard views for the web interface.

This module contains views for role-specific dashboards and main content areas.
"""

from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment
from apps.finance.models import Invoice, Payment
from apps.grading.models import ClassPartGrade, GPARecord

# Import models for dashboard data
from apps.people.models import StudentProfile

from ..performance import CacheManager
from ..utils import is_htmx_request


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard view with role-specific content.

    Displays different dashboard content based on user's current role.
    """

    template_name = "web_interface/base/main_app_base.html"

    def get_template_names(self):
        """Return template based on request type."""
        if is_htmx_request(self.request):
            return ["web_interface/dashboards/dashboard_content.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        """Add dashboard-specific context."""
        context = super().get_context_data(**kwargs)

        # Get current role from session, with intelligent fallback
        current_role = self.request.session.get("current_role")

        # If no role is set, determine a default role based on user properties
        if not current_role:
            current_role = self.get_default_role()
            # Store the determined role in session for future requests
            self.request.session["current_role"] = current_role

        context.update(
            {
                "page_title": _("Dashboard"),
                "current_page": "dashboard",
                "current_role": current_role,
            }
        )

        # Add role-specific context
        if current_role == "admin":
            context.update(self.get_admin_context())
        elif current_role == "staff":
            context.update(self.get_staff_context())
        elif current_role == "teacher":
            context.update(self.get_teacher_context())
        elif current_role == "finance":
            context.update(self.get_finance_context())
        else:  # student
            context.update(self.get_student_context())

        return context

    def get_default_role(self):
        """Determine default role for user based on their profile and permissions."""
        user = self.request.user

        # Check if user is superuser or staff
        if user.is_superuser:
            return "admin"

        # Check if user has a Person record with specific profiles
        if hasattr(user, "person"):
            person = user.person

            # Check for specific profile types
            if hasattr(person, "staffprofile"):
                # Check if staff member has financial permissions
                if user.groups.filter(name__icontains="finance").exists():
                    return "finance"
                return "staff"

            if hasattr(person, "teacherprofile"):
                return "teacher"

            if hasattr(person, "studentprofile"):
                return "student"

        # Check Django permissions/groups
        if user.groups.filter(name__icontains="admin").exists():
            return "admin"
        elif user.groups.filter(name__icontains="finance").exists():
            return "finance"
        elif user.groups.filter(name__icontains="staff").exists():
            return "staff"
        elif user.groups.filter(name__icontains="teacher").exists():
            return "teacher"

        # Default to student role
        return "student"

    @CacheManager.cached_result(timeout=CacheManager.TIMEOUT_SHORT, key_prefix="admin_dashboard")
    def get_admin_context(self):
        """Get admin dashboard context with optimized queries and caching."""
        try:
            # Check cache first for expensive aggregations
            cache_key = f"admin_stats_{self.request.user.id}"
            cached_stats = cache.get(cache_key)

            if cached_stats:
                stats = cached_stats
            else:
                # Single query for student counts by status
                student_stats = StudentProfile.objects.values("current_status").annotate(count=models.Count("id"))

                total_students = sum(
                    stat["count"] for stat in student_stats if stat["current_status"] in ["ACTIVE", "ENROLLED"]
                )
                graduated_students = sum(
                    stat["count"] for stat in student_stats if stat["current_status"] == "GRADUATED"
                )

                # Optimize class enrollment count with single query
                active_classes = (
                    ClassHeaderEnrollment.objects.filter(status__in=["ENROLLED", "ACTIVE"])
                    .values("class_header")
                    .distinct()
                    .count()
                )

                # Optimize invoice aggregation
                invoice_stats = Invoice.objects.filter(status__in=["SENT", "PARTIALLY_PAID", "OVERDUE"]).aggregate(
                    pending_total=Sum("total_amount"), pending_count=models.Count("id")
                )
                pending_payments = invoice_stats["pending_total"] or Decimal("0")

                # Optimize enrollment count
                total_program_enrollments = ProgramEnrollment.objects.count()
                graduation_rate = (
                    (graduated_students / total_program_enrollments * 100) if total_program_enrollments > 0 else 0
                )

                stats = {
                    "total_students": total_students,
                    "active_classes": active_classes,
                    "pending_payments": float(pending_payments),
                    "graduation_rate": round(graduation_rate, 1),
                }

                # Cache for 1 minute
                cache.set(cache_key, stats, 60)

            # Get recent enrollments with optimized query (not cached as it changes frequently)
            recent_enrollments = (
                ClassHeaderEnrollment.objects.select_related(
                    "student__person", "class_header__course", "class_header__term"
                )
                .filter(status="ENROLLED")
                .order_by("-created_at")[:5]
            )

            return {
                "stats": stats,
                "recent_enrollments": recent_enrollments,
            }
        except Exception as e:
            # Log the exception for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error in get_admin_context: {e}", exc_info=True)

            # Fallback to placeholder data if queries fail
            return {
                "stats": {
                    "total_students": 0,
                    "active_classes": 0,
                    "pending_payments": 0,
                    "graduation_rate": 0,
                },
                "recent_enrollments": [],
            }

    def get_staff_context(self):
        """Get staff dashboard context with optimized queries."""
        try:
            # Single query for multiple student stats
            student_stats = StudentProfile.objects.aggregate(
                total_records=models.Count("id"),
                graduated_count=models.Count("id", filter=models.Q(current_status="GRADUATED")),
            )

            student_records = student_stats["total_records"]
            pending_transcripts = student_stats["graduated_count"]  # Simplified

            # Optimize enrollment query
            pending_enrollments = ClassHeaderEnrollment.objects.filter(status="PENDING").count()

            return {
                "stats": {
                    "student_records": student_records,
                    "pending_enrollments": pending_enrollments,
                    "pending_transcripts": pending_transcripts,
                }
            }
        except Exception:
            return {
                "stats": {
                    "student_records": 0,
                    "pending_enrollments": 0,
                    "pending_transcripts": 0,
                }
            }

    def get_teacher_context(self):
        """Get teacher dashboard context."""
        try:
            # Get teacher profile for current user
            teacher_profile = None
            if hasattr(self.request.user, "person") and hasattr(self.request.user.person, "teacherprofile"):
                teacher_profile = self.request.user.person.teacherprofile

            if teacher_profile:
                # Get classes taught by this teacher
                my_classes = (
                    ClassHeaderEnrollment.objects.filter(class_header__teacher=teacher_profile)
                    .values("class_header")
                    .distinct()
                    .count()
                )

                # Get total students in teacher's classes
                total_students = ClassHeaderEnrollment.objects.filter(
                    class_header__teacher=teacher_profile, status="ENROLLED"
                ).count()

                # Get pending grades for teacher's classes
                pending_grades = ClassPartGrade.objects.filter(
                    enrollment__class_header__teacher=teacher_profile, final_grade__isnull=True
                ).count()
            else:
                my_classes = total_students = pending_grades = 0

            return {
                "stats": {
                    "my_classes": my_classes,
                    "total_students": total_students,
                    "pending_grades": pending_grades,
                }
            }
        except Exception:
            return {
                "stats": {
                    "my_classes": 0,
                    "total_students": 0,
                    "pending_grades": 0,
                }
            }

    def get_finance_context(self):
        """Get finance dashboard context with optimized queries."""
        try:
            # Single query for invoice statistics
            invoice_stats = Invoice.objects.aggregate(
                pending_count=models.Count("id", filter=models.Q(status__in=["SENT", "PARTIALLY_PAID"])),
                overdue_count=models.Count("id", filter=models.Q(status="OVERDUE")),
            )

            pending_invoices = invoice_stats["pending_count"]
            overdue_payments = invoice_stats["overdue_count"]

            # Calculate total revenue from paid invoices
            total_revenue = Payment.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0")

            return {
                "stats": {
                    "pending_invoices": pending_invoices,
                    "total_revenue": float(total_revenue),
                    "overdue_payments": overdue_payments,
                }
            }
        except Exception:
            return {
                "stats": {
                    "pending_invoices": 0,
                    "total_revenue": 0,
                    "overdue_payments": 0,
                }
            }

    def get_student_context(self):
        """Get student dashboard context."""
        try:
            # Get student profile for current user
            student_profile = None
            if hasattr(self.request.user, "person") and hasattr(self.request.user.person, "studentprofile"):
                student_profile = self.request.user.person.studentprofile

            if student_profile:
                # Get current courses
                current_courses = ClassHeaderEnrollment.objects.filter(
                    student=student_profile, status="ENROLLED"
                ).count()

                # Get GPA from most recent GPA record
                latest_gpa = GPARecord.objects.filter(student=student_profile).order_by("-calculation_date").first()
                gpa = float(latest_gpa.gpa) if latest_gpa else 0.0

                # Calculate credits earned (completed courses)
                credits_earned = (
                    ClassHeaderEnrollment.objects.filter(student=student_profile, status="COMPLETED").aggregate(
                        total_credits=Sum("class_header__course__credit_hours")
                    )["total_credits"]
                    or 0
                )

                # Calculate account balance (unpaid invoices)
                account_balance = Invoice.objects.filter(
                    student=student_profile, status__in=["SENT", "PARTIALLY_PAID", "OVERDUE"]
                ).aggregate(balance=Sum("total_amount"))["balance"] or Decimal("0")
            else:
                current_courses = 0
                gpa = 0.0
                credits_earned = 0
                account_balance = Decimal("0")

            return {
                "stats": {
                    "current_courses": current_courses,
                    "gpa": gpa,
                    "credits_earned": credits_earned,
                    "account_balance": float(account_balance),
                }
            }
        except Exception:
            return {
                "stats": {
                    "current_courses": 0,
                    "gpa": 0.0,
                    "credits_earned": 0,
                    "account_balance": 0,
                }
            }
