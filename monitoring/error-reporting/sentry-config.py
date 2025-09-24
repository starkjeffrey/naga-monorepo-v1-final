# Sentry error reporting configuration for Naga SIS
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.dramatiq import DramatiqIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration


def configure_sentry():
    """Configure Sentry for comprehensive error reporting and performance monitoring."""

    # Sentry configuration
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")
    release = os.getenv("GIT_SHA", "unknown")

    if not sentry_dsn:
        print("Warning: SENTRY_DSN not configured. Error reporting will be limited.")
        return

    # Logging integration configuration
    logging_integration = LoggingIntegration(
        level=None,  # Capture all log levels
        event_level="ERROR",  # Only send ERROR and above as events
    )

    # Initialize Sentry SDK
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=release,
        # Integrations
        integrations=[
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=True,
                signals_spans=True,
                cache_spans=True,
                signals_denylist=[
                    # Exclude noisy signals
                    "django.db.models.signals.pre_save",
                    "django.db.models.signals.post_save",
                ],
            ),
            RedisIntegration(),
            SqlalchemyIntegration(),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
            DramatiqIntegration(),
            HttpxIntegration(),
            logging_integration,
        ],
        # Performance monitoring
        traces_sample_rate=get_traces_sample_rate(environment),
        profiles_sample_rate=get_profiles_sample_rate(environment),
        # Error sampling
        sample_rate=1.0,  # Capture 100% of errors
        # Advanced options
        attach_stacktrace=True,
        send_default_pii=False,  # Don't send PII for privacy
        max_breadcrumbs=100,
        # Custom configuration
        before_send=before_send_filter,
        before_send_transaction=before_send_transaction_filter,
        ignore_errors=get_ignored_errors(),
        # Tag configuration
        tags={
            "component": "naga-sis",
            "tier": "backend",
            "language": "python",
        },
        # Session tracking
        auto_session_tracking=True,
        session_mode="request",
    )

    # Set additional context
    sentry_sdk.set_context(
        "application",
        {
            "name": "Naga SIS",
            "version": release,
            "environment": environment,
            "component": "Django Backend",
        },
    )

    print(f"Sentry configured for environment: {environment}, release: {release}")


def get_traces_sample_rate(environment: str) -> float:
    """Get the trace sampling rate based on environment."""
    if environment == "production":
        return 0.1  # 10% sampling in production
    elif environment == "staging":
        return 0.25  # 25% sampling in staging
    else:
        return 1.0  # 100% sampling in development


def get_profiles_sample_rate(environment: str) -> float:
    """Get the profiling sampling rate based on environment."""
    if environment == "production":
        return 0.05  # 5% profiling in production
    elif environment == "staging":
        return 0.1  # 10% profiling in staging
    else:
        return 0.5  # 50% profiling in development


def before_send_filter(event, hint):
    """Filter events before sending to Sentry."""

    # Filter out sensitive information
    if "exception" in event:
        exception = event["exception"]
        if "values" in exception:
            for exc_value in exception["values"]:
                if "stacktrace" in exc_value and "frames" in exc_value["stacktrace"]:
                    for frame in exc_value["stacktrace"]["frames"]:
                        if "vars" in frame:
                            # Remove sensitive variables
                            sensitive_keys = [
                                "password",
                                "token",
                                "secret",
                                "key",
                                "auth",
                            ]
                            frame["vars"] = {
                                k: "[Filtered]"
                                if any(s in k.lower() for s in sensitive_keys)
                                else v
                                for k, v in frame["vars"].items()
                            }

    # Filter out health check and monitoring requests
    if "request" in event:
        url = event["request"].get("url", "")
        if any(path in url for path in ["/health/", "/metrics", "/status"]):
            return None

    # Filter out known non-critical errors
    if "exception" in event:
        exc_type = event["exception"]["values"][0]["type"]
        if exc_type in ["DisconnectedError", "ConnectionResetError"]:
            return None

    return event


def before_send_transaction_filter(event, hint):
    """Filter transaction events before sending to Sentry."""

    # Don't send health check transactions
    transaction_name = event.get("transaction", "")
    if any(path in transaction_name for path in ["/health/", "/metrics", "/status"]):
        return None

    # Only send slow transactions in production
    if os.getenv("ENVIRONMENT") == "production":
        duration = event.get("timestamp", 0) - event.get("start_timestamp", 0)
        if duration < 1.0:  # Less than 1 second
            return None

    return event


def get_ignored_errors():
    """Get list of errors to ignore in Sentry."""
    return [
        # Connection errors (usually network issues)
        "ConnectionError",
        "ConnectionResetError",
        "TimeoutError",
        "DisconnectedError",
        # Client-side errors
        "BrokenPipeError",
        "ConnectionAbortedError",
        # Development/test errors
        "ManagementCommandError",  # Django management command errors in dev
        # Third-party library noise
        "PIL.UnidentifiedImageError",
        "requests.exceptions.RequestException",
    ]


# Academic-specific error contexts
def set_academic_context(
    student_id=None, course_id=None, term_id=None, enrollment_id=None
):
    """Set academic context for error reporting."""
    context = {}

    if student_id:
        context["student_id"] = student_id
    if course_id:
        context["course_id"] = course_id
    if term_id:
        context["term_id"] = term_id
    if enrollment_id:
        context["enrollment_id"] = enrollment_id

    sentry_sdk.set_context("academic", context)


def set_financial_context(student_id=None, payment_id=None, fee_id=None, amount=None):
    """Set financial context for error reporting."""
    context = {}

    if student_id:
        context["student_id"] = student_id
    if payment_id:
        context["payment_id"] = payment_id
    if fee_id:
        context["fee_id"] = fee_id
    if amount:
        context["amount"] = str(amount)  # Convert to string to avoid PII concerns

    sentry_sdk.set_context("financial", context)


def set_user_context(user_id=None, username=None, email=None, role=None):
    """Set user context for error reporting (with PII filtering)."""
    context = {}

    if user_id:
        context["id"] = user_id
    if username:
        context["username"] = username
    if role:
        context["role"] = role
    # Don't include email to avoid PII

    sentry_sdk.set_user(context)


# Performance monitoring helpers
def monitor_database_query(query_type, table_name=None):
    """Monitor database query performance."""
    return sentry_sdk.start_transaction(
        op="db.query", name=f"{query_type} {table_name or 'unknown'}"
    )


def monitor_api_request(endpoint, method="GET"):
    """Monitor API request performance."""
    return sentry_sdk.start_transaction(op="http.server", name=f"{method} {endpoint}")


def monitor_business_operation(operation_name, component=None):
    """Monitor business operation performance."""
    return sentry_sdk.start_transaction(
        op="business.operation", name=f"{component or 'general'}.{operation_name}"
    )


# Error reporting helpers
def report_business_error(error_type, message, context=None, level="error"):
    """Report a business logic error to Sentry."""
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("error_category", "business_logic")
        scope.set_tag("error_type", error_type)

        if context:
            scope.set_context("business_context", context)

        if level == "warning":
            sentry_sdk.capture_message(message, level="warning")
        else:
            sentry_sdk.capture_exception()


def report_integration_error(service_name, operation, error, context=None):
    """Report an external service integration error."""
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("error_category", "integration")
        scope.set_tag("service", service_name)
        scope.set_tag("operation", operation)

        if context:
            scope.set_context("integration_context", context)

        sentry_sdk.capture_exception(error)


def report_performance_issue(operation, duration, threshold, context=None):
    """Report a performance issue to Sentry."""
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("issue_type", "performance")
        scope.set_tag("operation", operation)
        scope.set_extra("duration", duration)
        scope.set_extra("threshold", threshold)

        if context:
            scope.set_context("performance_context", context)

        sentry_sdk.capture_message(
            f"Performance issue: {operation} took {duration}s (threshold: {threshold}s)",
            level="warning",
        )
