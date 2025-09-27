from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel


class MobileAuthToken(AuditModel):
    """Mobile authentication token storage for JWT management.

    Stores active JWT tokens for mobile devices to enable proper
    token revocation and session management.
    """

    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mobile_tokens",
        verbose_name=_("User"),
    )

    device_id: models.CharField = models.CharField(
        _("Device ID"),
        max_length=255,
        help_text=_("Unique identifier for the mobile device"),
    )

    token_id: models.CharField = models.CharField(
        _("Token ID"),
        max_length=255,
        unique=True,
        help_text=_("JWT token ID (jti claim)"),
    )

    expires_at: models.DateTimeField = models.DateTimeField(_("Expires At"), help_text=_("When the token expires"))

    last_used: models.DateTimeField = models.DateTimeField(
        _("Last Used"),
        null=True,
        blank=True,
        help_text=_("When the token was last used for an API call"),
    )

    revoked: models.BooleanField = models.BooleanField(
        _("Revoked"), default=False, help_text=_("Whether the token has been revoked")
    )

    class Meta:
        db_table = "mobile_auth_tokens"
        verbose_name = _("Mobile Auth Token")
        verbose_name_plural = _("Mobile Auth Tokens")
        indexes = [
            models.Index(fields=["user", "device_id"]),
            models.Index(fields=["token_id"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Token for {self.user.email} on {self.device_id}"


class MobileAuthAttempt(AuditModel):
    """Log mobile authentication attempts for security monitoring.

    Tracks both successful and failed authentication attempts
    to detect potential security threats.
    """

    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", _("Success")
        FAILED_INVALID_TOKEN = "FAILED_INVALID_TOKEN", _("Failed - Invalid Google Token")
        FAILED_INVALID_EMAIL = "FAILED_INVALID_EMAIL", _("Failed - Invalid Email Domain")
        FAILED_STUDENT_NOT_FOUND = "FAILED_STUDENT_NOT_FOUND", _("Failed - Student Not Found")
        FAILED_RATE_LIMITED = "FAILED_RATE_LIMITED", _("Failed - Rate Limited")

    email: models.EmailField = models.EmailField(
        _("Email"), help_text=_("Email address used in authentication attempt")
    )

    device_id: models.CharField = models.CharField(
        _("Device ID"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Device identifier if available"),
    )

    ip_address: models.GenericIPAddressField = models.GenericIPAddressField(
        _("IP Address"),
        null=True,
        blank=True,
        help_text=_("IP address of the authentication attempt"),
    )

    user_agent: models.TextField = models.TextField(
        _("User Agent"),
        null=True,
        blank=True,
        help_text=_("Browser/app user agent string"),
    )

    status: models.CharField = models.CharField(
        _("Status"),
        max_length=30,
        choices=Status.choices,
        help_text=_("Result of the authentication attempt"),
    )

    student_id: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Student ID"),
        null=True,
        blank=True,
        help_text=_("Student ID if authentication was successful"),
    )

    error_message: models.TextField = models.TextField(
        _("Error Message"),
        null=True,
        blank=True,
        help_text=_("Detailed error message if authentication failed"),
    )

    class Meta:
        db_table = "mobile_auth_attempts"
        verbose_name = _("Mobile Auth Attempt")
        verbose_name_plural = _("Mobile Auth Attempts")
        indexes = [
            models.Index(fields=["email", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} - {self.status} at {self.created_at}"
