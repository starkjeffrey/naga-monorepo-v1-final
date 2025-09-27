import importlib.util
import logging

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# Import Dramatiq integration only if available (optional for evaluation)
try:
    if importlib.util.find_spec("dramatiq"):
        from sentry_sdk.integrations.dramatiq import DramatiqIntegration

        DRAMATIQ_AVAILABLE = True
    else:
        DRAMATIQ_AVAILABLE = False
        DramatiqIntegration = None
except Exception:  # Catch a broader exception just in case
    DRAMATIQ_AVAILABLE = False
    DramatiqIntegration = None

from .base import *
from .base import DATABASES, INSTALLED_APPS, REDIS_URL, env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["evaluation.pucsr.edu.kh", "localhost", "127.0.0.1"])

# CSRF Configuration
# ------------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = [
    "https://sis-eval.pucsr.edu.kh",
    "https://evaluation.pucsr.edu.kh",
    "http://localhost:8005",
    "http://127.0.0.1:8005",
]

# EVALUATION-SPECIFIC DEBUG SETTINGS
# ------------------------------------------------------------------------------
# Allow conditional debug mode for troubleshooting
DEBUG = env.bool("DJANGO_DEBUG", default=False)
DEBUG_PROPAGATE_EXCEPTIONS = env.bool("DJANGO_DEBUG_PROPAGATE_EXCEPTIONS", default=True)

# Enable Django Debug Toolbar conditionally for performance analysis
if env.bool("ENABLE_DEBUG_TOOLBAR", default=False):
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]  # Docker and local debugging

# Django Silk for SQL query profiling and performance monitoring
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["silk"]
MIDDLEWARE = ["silk.middleware.SilkyMiddleware", *MIDDLEWARE]  # Must be at the beginning

# Silk configuration
SILKY_PYTHON_PROFILER = env.bool("SILKY_PYTHON_PROFILER", default=False)
SILKY_PYTHON_PROFILER_BINARY = env.bool("SILKY_PYTHON_PROFILER_BINARY", default=False)
SILKY_AUTHENTICATION = True  # Require login to view
SILKY_AUTHORISATION = True  # Only superusers can access
SILKY_MAX_REQUEST_BODY_SIZE = -1  # No limit on request body size
SILKY_MAX_RESPONSE_BODY_SIZE = 1024  # Limit response body to 1KB
SILKY_INTERCEPT_PERCENT = env.int("SILKY_INTERCEPT_PERCENT", default=100)  # Profile all requests
SILKY_MAX_RECORDED_REQUESTS = env.int("SILKY_MAX_RECORDED_REQUESTS", default=10000)

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=300)

# Enable query logging for performance debugging when needed
if env.bool("LOG_SQL_QUERIES", default=False):
    DATABASES["default"]["OPTIONS"]["logging"] = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "loggers": {
            "django.db.backends": {
                "handlers": ["console"],
                "level": "DEBUG",
            },
        },
    }

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "evaluation",
        "TIMEOUT": 300,  # 5 minutes default cache
    },
}

# Session caching for performance
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# SECURITY
# ------------------------------------------------------------------------------
# Production security with some relaxation for evaluation
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-name
SESSION_COOKIE_NAME = "__Secure-sessionid"
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-name
CSRF_COOKIE_NAME = "__Secure-csrftoken"
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True,
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF",
    default=True,
)

# STATIC & MEDIA
# ------------------------------------------------------------------------------
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# EMAIL
# ------------------------------------------------------------------------------
# Hybrid email approach: use Mailpit for testing, real SMTP for notifications
USE_MAILPIT = env.bool("USE_MAILPIT", default=False)

if USE_MAILPIT:
    # Use Mailpit for email testing and development
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", default="mailpit")
    EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
    EMAIL_USE_TLS = False
    EMAIL_USE_SSL = False
else:
    # Use real email service for demonstration
    INSTALLED_APPS += ["anymail"]
    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
    ANYMAIL = {
        "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),
        "MAILGUN_SENDER_DOMAIN": env("MAILGUN_DOMAIN"),
        "MAILGUN_API_URL": env("MAILGUN_API_URL", default="https://api.mailgun.net/v3"),
    }

# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="Naga SIS Evaluation <noreply@evaluation.pucsr.edu.kh>",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[Naga SIS Evaluation] ",
)
ACCOUNT_EMAIL_SUBJECT_PREFIX = EMAIL_SUBJECT_PREFIX

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin-evaluation/")

# LOGGING
# ------------------------------------------------------------------------------
# Enhanced logging for evaluation environment with debugging capabilities
LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")

# Check if we should disable file logging (for permission issues)
DISABLE_FILE_LOGGING = env.bool("DJANGO_DISABLE_FILE_LOGGING", default=False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/naga-evaluation/django.log",
            "maxBytes": 1024 * 1024 * 15,  # 15MB
            "backupCount": 10,
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/naga-evaluation/django-errors.log",
            "maxBytes": 1024 * 1024 * 15,  # 15MB
            "backupCount": 10,
            "formatter": "verbose",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console", "file"],
    },
    "loggers": {
        "django": {
            "level": LOG_LEVEL,
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "django.db.backends": {
            "level": "ERROR" if not env.bool("LOG_SQL_QUERIES", default=False) else "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "django.request": {
            "level": "WARNING",
            "handlers": ["console", "error_file"],
            "propagate": False,
        },
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["console", "error_file"],
            "propagate": False,
        },
        # Application-specific logging
        "apps": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        # Sentry integration
        "sentry_sdk": {"level": "ERROR", "handlers": ["console"], "propagate": False},
    },
}

# Override logging handlers if file logging is disabled
if DISABLE_FILE_LOGGING:
    # Remove file handlers
    LOGGING["handlers"] = {"console": LOGGING["handlers"]["console"]}
    # Update all loggers to use only console
    LOGGING["root"]["handlers"] = ["console"]
    for logger_config in LOGGING["loggers"].values():
        if "handlers" in logger_config:
            logger_config["handlers"] = ["console"]

# PERFORMANCE MONITORING
# ------------------------------------------------------------------------------
# Enable Django's performance debugging
if env.bool("ENABLE_PERFORMANCE_LOGGING", default=False):
    LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"
    template_handlers = ["console"] if DISABLE_FILE_LOGGING else ["console", "file"]
    LOGGING["loggers"]["django.template"] = {
        "level": "DEBUG",
        "handlers": template_handlers,
        "propagate": False,
    }

# Sentry
# ------------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)

    sentry_logging = LoggingIntegration(
        level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )
    integrations = [
        sentry_logging,
        DjangoIntegration(),
        RedisIntegration(),
    ]

    # Add Dramatiq integration only if available
    if DRAMATIQ_AVAILABLE and DramatiqIntegration:
        integrations.append(DramatiqIntegration())
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=integrations,
        environment="evaluation",
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        profiles_sample_rate=env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0.1),
    )

# EVALUATION ENVIRONMENT SPECIFIC SETTINGS
# ------------------------------------------------------------------------------
# Allow iframe embedding for evaluation/demo purposes
X_FRAME_OPTIONS = "SAMEORIGIN"

# CORS settings for evaluation environment
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "https://evaluation.pucsr.edu.kh",
        "http://localhost:3000",  # Frontend development
        "http://127.0.0.1:3000",
    ],
)

# Demo and testing configurations
DEMO_MODE = env.bool("DEMO_MODE", default=True)
if DEMO_MODE:
    # Relaxed password validation for demo accounts
    AUTH_PASSWORD_VALIDATORS = [
        {
            "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
            "OPTIONS": {"min_length": 6},  # Reduced for demo
        },
    ]

    # Enable demo data fixtures auto-loading
    DEMO_FIXTURES = [
        "demo_users.json",
        "demo_courses.json",
        "demo_students.json",
        "demo_enrollments.json",
    ]

# File upload settings for evaluation
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Session settings for evaluation
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=86400 * 7)  # 7 days
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Cache settings for evaluation performance
CACHE_TTL = env.int("CACHE_TTL", default=300)  # 5 minutes

# Internationalization for evaluation
USE_I18N = True
USE_TZ = True
LANGUAGE_CODE = env("LANGUAGE_CODE", default="en-us")
TIME_ZONE = env("TIME_ZONE", default="Asia/Phnom_Penh")

# Your stuff...
# ------------------------------------------------------------------------------
