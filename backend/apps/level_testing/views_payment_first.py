"""Payment-first workflow views for level testing.

This module implements the redesigned payment-first workflow where:
1. Payment is collected before application form access
2. QR codes are generated with access tokens
3. Telegram verification is optional but encouraged
4. Mobile-first responsive design throughout
"""

import base64
import logging
import secrets
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, TemplateView, View
from PIL import Image

from apps.level_testing.forms import QuickPaymentForm, TelegramVerificationForm
from apps.level_testing.models import TestAccessToken
from apps.level_testing.services_payment import TelegramService, ThermalPrinterService

logger = logging.getLogger(__name__)


class CashierPaymentView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Quick payment collection interface for cashiers.

    This is the entry point for the payment-first workflow. Cashiers
    collect payment and generate QR codes with access tokens.
    """

    template_name = "level_testing/cashier/collect_payment.html"
    form_class = QuickPaymentForm
    permission_required = "level_testing.add_testpayment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": _("Collect Level Test Payment"),
                "test_fee": getattr(settings, "LEVEL_TEST_FEE", 5.00),
            }
        )
        return context

    @transaction.atomic
    def form_valid(self, form):
        """Create access token and generate QR code."""
        try:
            # Create access token
            token = TestAccessToken.objects.create(
                student_name=form.cleaned_data["student_name"],
                student_phone=form.cleaned_data["student_phone"],
                payment_amount=form.cleaned_data["amount"],
                payment_method=form.cleaned_data["payment_method"],
                payment_received_at=timezone.now(),
                cashier=self.request.user,
            )

            # Generate QR code
            qr_service = QRCodeService()
            url, qr_image = qr_service.generate_access_qr(token)

            # Save QR data
            token.qr_code_url = url
            token.qr_code_data = {
                "generated_at": timezone.now().isoformat(),
                "cashier_id": self.request.user.id,
                "terminal": self.request.META.get("REMOTE_ADDR"),
            }
            token.save()

            # Print receipt with QR code if requested
            if form.cleaned_data.get("print_receipt"):
                printer_service = ThermalPrinterService()
                printer_success = printer_service.print_payment_receipt(token, qr_image)
            else:
                printer_success = False

            # Return success page with QR code display
            return render(
                self.request,
                "level_testing/cashier/payment_success.html",
                {
                    "token": token,
                    "qr_code_base64": base64.b64encode(qr_image).decode(),
                    "print_sent": form.cleaned_data.get("print_receipt"),
                    "print_success": printer_success,
                    "access_url": url,
                },
            )

        except Exception:
            logger.exception("Error processing payment")
            messages.error(self.request, _("Error processing payment. Please try again."))
            return self.form_invalid(form)


class QRCodeLandingView(TemplateView):
    """Mobile-optimized landing page for QR code scanning.

    This is where students land after scanning the QR code from their
    payment receipt. Validates the access token and provides options for
    Telegram verification and application form access.
    """

    template_name = "level_testing/mobile/qr_landing.html"

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        # Get access code from URL
        self.access_code = kwargs.get("access_code")

        # Validate access token
        try:
            self.token = TestAccessToken.objects.get(access_code=self.access_code)

            # Check if token is valid
            if not self.token.is_valid:
                if self.token.is_used:
                    messages.warning(
                        request,
                        _("This access code has already been used. Please contact staff if you need assistance."),
                    )
                elif self.token.is_expired:
                    messages.error(request, _("This access code has expired. Please contact the registration desk."))
                return redirect("level_testing:access_error")

        except TestAccessToken.DoesNotExist:
            messages.error(request, _("Invalid access code. Please check your receipt or contact staff."))
            return redirect("level_testing:access_error")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "token": self.token,
                "student_name": self.token.student_name,
                "access_code": self.access_code,
                "telegram_verified": self.token.telegram_verified,
                "application_url": reverse(
                    "level_testing:mobile_application", kwargs={"access_code": self.access_code}
                ),
                "telegram_verify_url": reverse(
                    "level_testing:telegram_verify", kwargs={"access_code": self.access_code}
                ),
            }
        )
        return context


class TelegramVerificationView(FormView):
    """Handle Telegram verification process.

    Sends verification code via Telegram bot and validates the code
    entered by the student to link their Telegram account.
    """

    template_name = "level_testing/mobile/telegram_verify.html"
    form_class = TelegramVerificationForm

    def dispatch(self, request, *args, **kwargs):
        self.access_code = kwargs.get("access_code")

        try:
            self.token = TestAccessToken.objects.get(access_code=self.access_code)
            if not self.token.is_valid:
                messages.error(request, _("Invalid or expired access code."))
                return redirect("level_testing:access_error")
        except TestAccessToken.DoesNotExist:
            messages.error(request, _("Access code not found."))
            return redirect("level_testing:access_error")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "token": self.token,
                "access_code": self.access_code,
            }
        )
        return context

    def form_valid(self, form):
        """Process Telegram verification."""
        action = form.cleaned_data.get("action")

        if action == "send_code":
            # Generate and send verification code
            verification_code = self.generate_verification_code()
            self.token.telegram_verification_code = verification_code
            self.token.save()

            # Send code via Telegram bot
            telegram_service = TelegramService()
            success = telegram_service.send_verification_code(
                phone=self.token.student_phone, code=verification_code, student_name=self.token.student_name
            )

            if success:
                messages.success(self.request, _("Verification code sent! Check your Telegram messages."))
            else:
                messages.error(
                    self.request, _("Failed to send code. Please ensure you've started a chat with our bot.")
                )

            return self.render_to_response(self.get_context_data(form=form, show_code_input=True))

        elif action == "verify_code":
            # Verify the entered code
            submitted_code = form.cleaned_data.get("verification_code")

            if submitted_code == self.token.telegram_verification_code:
                # Get Telegram user info
                telegram_service = TelegramService()
                telegram_info = telegram_service.get_user_info(self.token.student_phone)

                if telegram_info:
                    self.token.telegram_id = telegram_info.get("id")
                    self.token.telegram_username = telegram_info.get("username", "")
                    self.token.telegram_verified = True
                    self.token.telegram_verified_at = timezone.now()
                    self.token.save()

                    messages.success(
                        self.request, _("Telegram verified successfully! You'll receive test updates via Telegram.")
                    )

                    # Redirect to application form
                    return redirect("level_testing:mobile_application", access_code=self.access_code)
                else:
                    messages.error(
                        self.request,
                        _("Verification successful but couldn't retrieve Telegram info. Please continue."),
                    )
            else:
                messages.error(self.request, _("Invalid verification code. Please try again."))
                return self.form_invalid(form)

        return super().form_valid(form)

    @staticmethod
    def generate_verification_code():
        """Generate 6-digit verification code."""
        return "".join(secrets.choice("0123456789") for _ in range(6))


class MobileApplicationView(TemplateView):
    """Mobile-optimized application form.

    Progressive web app with offline capability and auto-save.
    Only accessible with valid access token.
    """

    template_name = "level_testing/mobile/application_wizard.html"

    def dispatch(self, request, *args, **kwargs):
        self.access_code = kwargs.get("access_code")

        try:
            self.token = TestAccessToken.objects.get(access_code=self.access_code)

            # Check if token is valid
            if not self.token.is_valid:
                if self.token.is_used:
                    # If already used, redirect to existing application
                    if self.token.application:
                        messages.info(request, _("Redirecting to your existing application."))
                        return redirect("level_testing:application_status", pk=self.token.application.id)
                    else:
                        messages.error(request, _("Access code already used."))
                        return redirect("level_testing:access_error")
                elif self.token.is_expired:
                    messages.error(request, _("Access code expired."))
                    return redirect("level_testing:access_error")

        except TestAccessToken.DoesNotExist:
            messages.error(request, _("Invalid access code."))
            return redirect("level_testing:access_error")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "token": self.token,
                "access_code": self.access_code,
                "student_name": self.token.student_name,
                "student_phone": self.token.student_phone,
                "telegram_connected": self.token.telegram_verified,
                "save_progress_url": reverse("level_testing:save_progress"),
            }
        )
        return context


class SaveProgressView(View):
    """AJAX endpoint for auto-saving application progress.

    Saves form data to session storage and syncs with server when online.
    """

    def post(self, request, *args, **kwargs):
        """Save application progress."""
        try:
            access_code = request.POST.get("access_code")

            # Validate access token
            token = TestAccessToken.objects.get(access_code=access_code)
            if not token.is_valid and not token.is_used:
                return JsonResponse({"error": "Invalid token"}, status=403)

            # Save progress to session
            session_key = f"application_progress_{access_code}"
            progress_data = {
                "access_code": access_code,
                "current_step": request.POST.get("current_step", 1),
                "form_data": request.POST.get("form_data", {}),
                "last_saved": timezone.now().isoformat(),
            }

            request.session[session_key] = progress_data
            request.session.modified = True

            return JsonResponse(
                {
                    "saved": True,
                    "last_saved": progress_data["last_saved"],
                }
            )

        except TestAccessToken.DoesNotExist:
            return JsonResponse({"error": "Token not found"}, status=404)
        except Exception as e:
            logger.exception("Error saving progress")
            return JsonResponse({"error": str(e)}, status=500)


class QRCodeService:
    """Service for generating and managing QR codes."""

    @staticmethod
    def generate_access_qr(token: TestAccessToken) -> tuple[str, bytes]:
        """Generate QR code for test access token.

        Returns:
            Tuple of (url, qr_code_image_bytes)
        """
        # Build URL with access code
        base_url = getattr(settings, "LEVEL_TESTING_BASE_URL", "https://naga.edu")
        access_url = f"{base_url}/level-testing/apply/{token.access_code}/"

        # Add query parameters
        from urllib.parse import urlencode

        params = {
            "name": token.student_name,
            "lang": "en",  # Default language
            "ts": token.created_at.timestamp(),
        }

        full_url = f"{access_url}?{urlencode(params)}"

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(full_url)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Add logo overlay if available
        try:
            logo_path = settings.STATIC_ROOT / "images" / "puc-logo.png"
            if logo_path.exists():
                logo = Image.open(logo_path)
                logo = logo.resize((60, 60))

                # Position logo in center
                pos = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)
                img.paste(logo, pos)
        except Exception:
            # Skip logo if not available
            pass

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")

        return full_url, buffer.getvalue()


class AccessErrorView(TemplateView):
    """Error page for invalid or expired access codes."""

    template_name = "level_testing/mobile/access_error.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "support_phone": getattr(settings, "SUPPORT_PHONE", "+855 23 123 456"),
                "support_email": getattr(settings, "SUPPORT_EMAIL", "info@naga.edu"),
            }
        )
        return context
