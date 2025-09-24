"""Views for level testing application process.

This module contains Django views for the level testing workflow, implementing
a mobile-first wizard-style application process. Views handle both student-facing
interfaces and staff administration tools.

Key features:
- Multi-step wizard for potential students
- Mobile-first responsive design
- HTMX integration for smooth UX
- Staff interfaces for administration
- Duplicate detection workflow
- Payment processing interface
"""

import logging
from datetime import date
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import models as django_models
from django.db import transaction
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.level_testing.constants import PricingTierCode, TestFeeCode
from apps.level_testing.fee_service import LevelTestingFeeService
from apps.level_testing.forms import (
    ApplicationReviewForm,
    ClerkPaymentForm,
    EducationBackgroundForm,
    PaymentInfoForm,
    PersonalInfoForm,
    ProgramPreferencesForm,
    StaffDuplicateReviewForm,
)
from apps.level_testing.models import (
    ApplicationStatus,
    DuplicateCandidate,
    DuplicateStatus,
    PaymentMethod,
    PotentialStudent,
    TestPayment,
)
from apps.level_testing.printing import print_application_receipt
from apps.level_testing.services import TestWorkflowService

logger = logging.getLogger(__name__)


class ApplicationWizardMixin:
    """Mixin for application wizard steps with common functionality."""

    # Hint to type checkers that views using this mixin are Django views
    # and will have a request attribute set.
    request: HttpRequest

    def get_session_key(self, key: str) -> str:
        """Get session key with prefix."""
        return f"level_testing_application_{key}"

    def get_application_data(self) -> dict[str, Any]:
        """Get application data from session."""
        return self.request.session.get(self.get_session_key("data"), {})

    def set_application_data(self, data: dict[str, Any]) -> None:
        """Set application data in session."""
        # Convert date objects to strings for JSON serialization
        serialized_data = {}
        for key, value in data.items():
            if hasattr(value, "isoformat"):  # date, datetime objects
                serialized_data[key] = value.isoformat()
            else:
                serialized_data[key] = value

        self.request.session[self.get_session_key("data")] = serialized_data
        self.request.session.modified = True

    def update_application_data(self, step_data: dict[str, Any]) -> None:
        """Update application data with step data."""
        current_data = self.get_application_data()
        current_data.update(step_data)
        self.set_application_data(current_data)

    def clear_application_data(self) -> None:
        """Clear application data from session."""
        session_keys = [
            self.get_session_key("data"),
            self.get_session_key("current_step"),
            self.get_session_key("application_id"),
        ]
        for key in session_keys:
            self.request.session.pop(key, None)
        self.request.session.modified = True

    def get_current_step(self) -> int:
        """Get current wizard step."""
        return self.request.session.get(self.get_session_key("current_step"), 1)

    def set_current_step(self, step: int) -> None:
        """Set current wizard step."""
        self.request.session[self.get_session_key("current_step")] = step
        self.request.session.modified = True


class ApplicationStartView(ApplicationWizardMixin, TemplateView):
    """Landing page for new test applications.

    Provides information about the testing process and starts the wizard.
    """

    template_name = "level_testing/application_start.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get dynamic test fee from fee service
        fee_service = LevelTestingFeeService()
        try:
            fee_info = fee_service.calculate_test_fee(
                fee_code=TestFeeCode.PLACEMENT_TEST,
                student_type=PricingTierCode.LOCAL_STUDENT,  # Default to local rate
            )
            test_fee_display = f"${fee_info['amount']} {fee_info['currency']}"
        except Exception:
            # Fallback to constants if fee service fails
            from apps.level_testing.constants import (
                DEFAULT_TEST_FEE_AMOUNT,
                TEST_FEE_CURRENCY,
            )

            test_fee_display = f"${DEFAULT_TEST_FEE_AMOUNT} {TEST_FEE_CURRENCY}"

        context.update(
            {
                "page_title": _("Level Testing Application"),
                "test_fee": test_fee_display,
                "estimated_time": _("10-15 minutes"),
            },
        )
        return context

    def post(self, request, *args, **kwargs):
        """Redirect to payment-first workflow."""
        return redirect("level_testing:cashier_payment")


class PersonalInfoStepView(ApplicationWizardMixin, FormView):
    """Step 1: Personal information collection."""

    template_name = "level_testing/wizard_step.html"
    form_class = PersonalInfoForm

    def get_initial(self):
        """Pre-populate form with session data."""
        data = self.get_application_data()

        # Convert date strings back to date objects for form fields
        if isinstance(data.get("date_of_birth"), str):
            try:
                data["date_of_birth"] = date.fromisoformat(data["date_of_birth"])
            except (ValueError, TypeError):
                data.pop("date_of_birth", None)

        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "step_number": 1,
                "step_title": _("Personal Information"),
                "step_description": _("Tell us about yourself"),
                "total_steps": 5,
                "progress_percent": 20,
                "next_step_url": reverse("level_testing:step_education"),
                "prev_step_url": reverse("level_testing:application_start"),
            },
        )
        return context

    def form_valid(self, form):
        """Save form data and proceed to next step."""
        self.update_application_data(form.cleaned_data)
        self.set_current_step(2)

        if self.request.headers.get("HX-Request"):
            # HTMX request - return next step
            return redirect("level_testing:step_education")

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("level_testing:step_education")


class EducationBackgroundStepView(ApplicationWizardMixin, FormView):
    """Step 2: Educational background information."""

    template_name = "level_testing/wizard_step.html"
    form_class = EducationBackgroundForm

    def get_initial(self):
        """Pre-populate form with session data."""
        data = self.get_application_data()

        # Convert date strings back to date objects for form fields
        if isinstance(data.get("date_of_birth"), str):
            try:
                data["date_of_birth"] = date.fromisoformat(data["date_of_birth"])
            except (ValueError, TypeError):
                data.pop("date_of_birth", None)

        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "step_number": 2,
                "step_title": _("Educational Background"),
                "step_description": _("Tell us about your education"),
                "total_steps": 5,
                "progress_percent": 40,
                "next_step_url": reverse("level_testing:step_preferences"),
                "prev_step_url": reverse("level_testing:step_personal_info"),
            },
        )
        return context

    def form_valid(self, form):
        self.update_application_data(form.cleaned_data)
        self.set_current_step(3)

        if self.request.headers.get("HX-Request"):
            return redirect("level_testing:step_preferences")

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("level_testing:step_preferences")


class ProgramPreferencesStepView(ApplicationWizardMixin, FormView):
    """Step 3: Program preferences and study plans."""

    template_name = "level_testing/wizard_step.html"
    form_class = ProgramPreferencesForm

    def get_initial(self):
        """Pre-populate form with session data."""
        data = self.get_application_data()

        # Convert date strings back to date objects for form fields
        if isinstance(data.get("date_of_birth"), str):
            try:
                data["date_of_birth"] = date.fromisoformat(data["date_of_birth"])
            except (ValueError, TypeError):
                data.pop("date_of_birth", None)

        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "step_number": 3,
                "step_title": _("Program Preferences"),
                "step_description": _("Choose your preferred program and schedule"),
                "total_steps": 5,
                "progress_percent": 60,
                "next_step_url": reverse("level_testing:step_review"),
                "prev_step_url": reverse("level_testing:step_education"),
            },
        )
        return context

    def form_valid(self, form):
        self.update_application_data(form.cleaned_data)
        self.set_current_step(4)

        if self.request.headers.get("HX-Request"):
            return redirect("level_testing:step_review")

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("level_testing:step_review")


class ApplicationReviewStepView(ApplicationWizardMixin, FormView):
    """Step 4: Application review and confirmation."""

    template_name = "level_testing/wizard_review_step.html"
    form_class = ApplicationReviewForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_data = self.get_application_data()

        context.update(
            {
                "step_number": 4,
                "step_title": _("Review Your Application"),
                "step_description": _(
                    "Please review your information before submitting",
                ),
                "total_steps": 5,
                "progress_percent": 80,
                "application_data": application_data,
                "prev_step_url": reverse("level_testing:step_preferences"),
            },
        )
        return context

    @transaction.atomic
    def form_valid(self, form):
        """Create potential student record and proceed to payment."""
        try:
            # Create potential student from session data
            application_data = self.get_application_data()

            # Convert date strings back to date objects if needed
            if isinstance(application_data.get("date_of_birth"), str):
                from datetime import date

                try:
                    year, month, day = application_data["date_of_birth"].split("-")
                    application_data["date_of_birth"] = date(int(year), int(month), int(day))
                except (ValueError, TypeError):
                    # Handle invalid date format gracefully
                    pass

            # Create potential student with INITIATED status
            potential_student = PotentialStudent.objects.create(
                status=ApplicationStatus.INITIATED,
                **application_data,
            )

            # Store application ID in session
            self.request.session[self.get_session_key("application_id")] = potential_student.id

            # Calculate dynamic test fee amount
            fee_service = LevelTestingFeeService()
            try:
                fee_info = fee_service.calculate_test_fee(
                    fee_code=TestFeeCode.PLACEMENT_TEST,
                    student_type=PricingTierCode.LOCAL_STUDENT,  # TODO: Determine from application data
                )
                fee_amount = fee_info["amount"]
            except Exception:
                # Fallback to default amount
                from apps.level_testing.constants import DEFAULT_TEST_FEE_AMOUNT

                fee_amount = DEFAULT_TEST_FEE_AMOUNT
                logger.warning("Fee service failed, using default amount: %s", fee_amount)

            # Create test payment record
            TestPayment.objects.create(
                potential_student=potential_student,
                amount=fee_amount,
                payment_method=PaymentMethod.CASH,  # Default, will be updated
                is_paid=False,
            )

            # Trigger registration workflow (includes duplicate detection)
            workflow_service = TestWorkflowService()
            success = workflow_service.process_registration(potential_student)

            if not success:
                logger.error(
                    "Registration workflow failed for %s",
                    potential_student.full_name_eng,
                )
                messages.error(
                    self.request,
                    _(
                        "There was an error processing your application. Please try again.",
                    ),
                )
                return self.form_invalid(form)

            # Check if duplicate concerns need staff review
            if potential_student.has_duplicate_concerns:
                messages.warning(
                    self.request,
                    _(
                        "Your application requires additional review. Our staff will contact you shortly.",
                    ),
                )
                return redirect(
                    "level_testing:application_pending",
                    pk=potential_student.id,
                )

            # Proceed to payment step
            self.set_current_step(5)
            messages.success(
                self.request,
                _("Application submitted successfully! Please proceed with payment."),
            )

            return redirect("level_testing:step_payment")

        except Exception:
            logger.exception("Error creating application")
            messages.error(
                self.request,
                _("There was an error submitting your application. Please try again."),
            )
            return self.form_invalid(form)


class PaymentStepView(ApplicationWizardMixin, FormView):
    """Step 5: Payment information and completion."""

    template_name = "level_testing/wizard_payment_step.html"
    form_class = PaymentInfoForm

    def dispatch(self, request, *args, **kwargs):
        """Ensure application exists before showing payment step."""
        application_id = self.request.session.get(
            self.get_session_key("application_id"),
        )
        if not application_id:
            messages.error(
                request,
                _("No active application found. Please start a new application."),
            )
            return redirect("level_testing:application_start")

        try:
            self.potential_student = PotentialStudent.objects.get(id=application_id)
            self.test_payment = TestPayment.objects.get(
                potential_student=self.potential_student,
            )
        except (PotentialStudent.DoesNotExist, TestPayment.DoesNotExist):
            messages.error(
                request,
                _("Application not found. Please start a new application."),
            )
            return redirect("level_testing:application_start")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Create dynamic payment description
        payment_description = _("Complete your ${amount} test fee payment").format(amount=self.test_payment.amount)

        context.update(
            {
                "step_number": 5,
                "step_title": _("Payment Information"),
                "step_description": payment_description,
                "total_steps": 5,
                "progress_percent": 100,
                "potential_student": self.potential_student,
                "test_payment": self.test_payment,
                "prev_step_url": reverse("level_testing:step_review"),
            },
        )
        return context

    def form_valid(self, form):
        """Update payment information and complete application."""
        try:
            # Update payment method and reference
            self.test_payment.payment_method = form.cleaned_data["payment_method"]
            if form.cleaned_data["payment_reference"]:
                self.test_payment.payment_reference = form.cleaned_data["payment_reference"]
            self.test_payment.save()

            # Print thermal receipt automatically
            print_success = print_application_receipt(self.potential_student)

            # Clear session data
            self.clear_application_data()

            # Show appropriate success message based on printing result
            if print_success:
                messages.success(
                    self.request,
                    _(
                        "Application completed successfully! Your receipt has been printed. "
                        "Please bring the receipt and $5 fee to our office."
                    ),
                )
            else:
                messages.success(
                    self.request,
                    _("Application completed successfully! Please bring your payment to our office."),
                )
                messages.warning(
                    self.request,
                    _(
                        "Receipt printing failed. Please take a screenshot of this confirmation "
                        "or write down your application number: #{}"
                    ).format(self.potential_student.id),
                )

            return redirect(
                "level_testing:application_complete",
                pk=self.potential_student.id,
            )

        except Exception:
            logger.exception("Error completing payment step")
            messages.error(
                self.request,
                _(
                    "There was an error processing your payment information. Please try again.",
                ),
            )
            return self.form_invalid(form)


class ApplicationCompleteView(DetailView):
    """Application completion confirmation page."""

    model = PotentialStudent
    template_name = "level_testing/application_complete.html"
    context_object_name = "application"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "test_payment": self.object.test_payment,
            },
        )
        return context


class ApplicationPendingView(DetailView):
    """Pending application page for duplicate review cases.

    Security: Only allows access to:
    - Students: Their own application (tracked by session)
    - Staff: Any application (with proper permissions)
    """

    model = PotentialStudent
    template_name = "level_testing/application_pending.html"
    context_object_name = "application"

    def dispatch(self, request, *args, **kwargs):
        """Check authorization before allowing access."""
        pk = kwargs.get("pk")

        # Authorization check
        has_access = False

        # Check if user is staff with proper permissions
        if request.user.is_authenticated and request.user.has_perm("level_testing.view_potentialstudent"):
            has_access = True
        else:
            # Check if this is the student's own application via session
            session_application_id = request.session.get("application_data_application_id")
            if session_application_id == pk:
                has_access = True

        if not has_access:
            logger.warning(
                "Unauthorized access attempt to pending application %s from IP %s",
                pk,
                request.META.get("REMOTE_ADDR", "unknown"),
            )
            messages.error(request, _("Access denied. You can only view your own application."))
            return redirect("level_testing:application_start")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "duplicate_candidates": self.object.duplicate_candidates.all(),
            },
        )
        return context


# Staff Views for Administration


class StaffDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Staff dashboard for level testing administration."""

    template_name = "level_testing/staff/dashboard.html"
    permission_required = "level_testing.view_potentialstudent"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get summary statistics
        pending_applications = PotentialStudent.objects.filter(
            status__in=[ApplicationStatus.INITIATED, ApplicationStatus.DUPLICATE_CHECK],
        )
        pending_payments = TestPayment.objects.filter(is_paid=False)
        duplicate_concerns = DuplicateCandidate.objects.filter(reviewed=False)

        context.update(
            {
                "pending_applications_count": pending_applications.count(),
                "pending_payments_count": pending_payments.count(),
                "duplicate_concerns_count": duplicate_concerns.count(),
                "recent_applications": pending_applications.order_by("-created_at")[:10],
                "pending_payments": pending_payments.order_by("-created_at")[:10],
                "high_risk_duplicates": duplicate_concerns.filter(
                    confidence_score__gte=0.8,
                ).order_by("-confidence_score")[:5],
            },
        )
        return context


class ApplicationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Staff view for listing and managing applications."""

    model = PotentialStudent
    template_name = "level_testing/staff/application_list.html"
    context_object_name = "applications"
    permission_required = "level_testing.view_potentialstudent"
    paginate_by = 25

    def get_queryset(self):
        queryset = PotentialStudent.objects.select_related("test_payment").order_by(
            "-created_at",
        )

        # Filter by status if specified
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                django_models.Q(personal_name_eng__icontains=search)
                | django_models.Q(family_name_eng__icontains=search)
                | django_models.Q(test_number__icontains=search)
                | django_models.Q(phone_number__icontains=search),
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "status_choices": ApplicationStatus.choices,
                "current_status": self.request.GET.get("status", ""),
                "current_search": self.request.GET.get("search", ""),
            },
        )
        return context


class DuplicateReviewView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Staff view for reviewing duplicate candidates."""

    template_name = "level_testing/staff/duplicate_review.html"
    form_class = StaffDuplicateReviewForm
    permission_required = "level_testing.change_potentialstudent"

    def dispatch(self, request, *args, **kwargs):
        self.potential_student = get_object_or_404(PotentialStudent, pk=kwargs["pk"])
        self.duplicate_candidates = self.potential_student.duplicate_candidates.all()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "potential_student": self.potential_student,
                "duplicate_candidates": self.duplicate_candidates,
            },
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "potential_student": self.potential_student,
                "duplicate_candidates": self.duplicate_candidates,
            },
        )
        return context

    @transaction.atomic
    def form_valid(self, form):
        """Process duplicate review decision."""
        action = form.cleaned_data["action"]
        notes = form.cleaned_data["review_notes"]

        try:
            if action == "confirm_new":
                # Clear duplicate concerns and allow to proceed
                workflow_service = TestWorkflowService()
                success = workflow_service.clear_duplicate_concerns(
                    self.potential_student,
                    cleared_by=self.request.user,
                    notes=notes,
                )

                if success:
                    # Mark all candidates as reviewed
                    self.duplicate_candidates.update(
                        reviewed=True,
                        is_confirmed_duplicate=False,
                        review_notes=notes,
                        reviewed_by=self.request.user,
                        reviewed_at=timezone.now(),
                    )

                    messages.success(
                        self.request,
                        _("Application approved. Student can proceed with testing."),
                    )
                else:
                    messages.error(
                        self.request,
                        _("Error processing approval. Please try again."),
                    )

            elif action == "confirm_duplicate":
                # Block application due to confirmed duplicate
                self.potential_student.duplicate_check_status = DuplicateStatus.CONFIRMED_DUPLICATE
                self.potential_student.duplicate_check_cleared_by = self.request.user
                self.potential_student.duplicate_check_cleared_at = timezone.now()
                self.potential_student.duplicate_check_notes = notes
                self.potential_student.save()

                # Mark candidates as confirmed duplicates
                self.duplicate_candidates.update(
                    reviewed=True,
                    is_confirmed_duplicate=True,
                    review_notes=notes,
                    reviewed_by=self.request.user,
                    reviewed_at=timezone.now(),
                )

                messages.warning(
                    self.request,
                    _("Application blocked due to confirmed duplicate."),
                )

            elif action == "needs_more_info":
                # Require manual review
                self.potential_student.duplicate_check_status = DuplicateStatus.MANUAL_REVIEW
                self.potential_student.duplicate_check_notes = notes
                self.potential_student.save()

                messages.info(self.request, _("Application marked for manual review."))

            return redirect("level_testing:staff_dashboard")

        except Exception:
            logger.exception("Error processing duplicate review")
            messages.error(
                self.request,
                _("Error processing review. Please try again."),
            )
            return self.form_invalid(form)


class PaymentProcessingView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Staff view for processing test fee payments."""

    model = TestPayment
    form_class = ClerkPaymentForm
    template_name = "level_testing/staff/payment_processing.html"
    permission_required = "level_testing.change_testpayment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "potential_student": self.object.potential_student,
            },
        )
        return context

    def form_valid(self, form):
        """Process payment and update student status."""
        try:
            # Save payment with received_by information
            payment = form.save(commit=False)
            if payment.is_paid:
                payment.received_by = self.request.user
                if not payment.paid_at:
                    payment.paid_at = timezone.now()
            payment.save()

            messages.success(self.request, _("Payment status updated successfully."))

            return redirect("level_testing:staff_dashboard")

        except Exception:
            logger.exception("Error processing payment")
            messages.error(
                self.request,
                _("Error updating payment status. Please try again."),
            )
            return self.form_invalid(form)


# HTMX and AJAX Views


@require_http_methods(["GET"])
def application_status_check(request, pk):
    """AJAX endpoint for checking application status.

    Security: Only allows access to:
    - Students: Their own application (tracked by session)
    - Staff: Any application (with proper permissions)
    """
    try:
        application = get_object_or_404(PotentialStudent, pk=pk)

        # Authorization check
        has_access = False

        # Check if user is staff with proper permissions
        if request.user.is_authenticated and request.user.has_perm("level_testing.view_potentialstudent"):
            has_access = True
        else:
            # Check if this is the student's own application via session
            session_application_id = request.session.get("application_data_application_id")
            if session_application_id == pk:
                has_access = True

        if not has_access:
            logger.warning(
                "Unauthorized access attempt to application %s from IP %s",
                pk,
                request.META.get("REMOTE_ADDR", "unknown"),
            )
            return JsonResponse({"error": "Access denied"}, status=403)

        data = {
            "status": application.get_status_display(),
            "test_number": application.test_number,
            "duplicate_check_status": application.get_duplicate_check_status_display(),
            "has_duplicate_concerns": application.has_duplicate_concerns,
            "can_proceed_to_payment": application.can_proceed_to_payment,
        }

        return JsonResponse(data)

    except Exception:
        logger.exception("Error checking application status")
        return JsonResponse({"error": "Application not found"}, status=404)


@method_decorator(never_cache, name="dispatch")
class WizardStepValidationView(ApplicationWizardMixin, FormView):
    """HTMX endpoint for real-time form validation during wizard steps."""

    def get_form_class(self):
        """Determine form class based on step parameter."""
        step = self.request.GET.get("step", "1")

        form_classes = {
            "1": PersonalInfoForm,
            "2": EducationBackgroundForm,
            "3": ProgramPreferencesForm,
            "4": ApplicationReviewForm,
            "5": PaymentInfoForm,
        }

        return form_classes.get(step, PersonalInfoForm)

    def post(self, request, *args, **kwargs):
        """Validate form and return errors via HTMX."""
        form_class = self.get_form_class()
        form = form_class(request.POST)

        if form.is_valid():
            return HttpResponse("")  # No errors
        return render(
            request,
            "level_testing/partials/form_errors.html",
            {
                "form": form,
            },
        )
