"""Local testing settings - SQLite without Docker.

This configuration allows running tests locally using SQLite for fast iteration
without requiring Docker or PostgreSQL setup. Ideal for TDD and unit testing.
"""

import os

from .base import *

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = os.environ.get("SECRET_KEY", "local-test-secret-key-change-in-production")

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# DATABASES
# ------------------------------------------------------------------------------
# Use SQLite for local testing - fast and no external dependencies
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # In-memory for fastest tests
        "OPTIONS": {
            "timeout": 20,
        },
    },
}

# If you need persistent SQLite database for debugging
if os.environ.get("SQLITE_PERSISTENT"):
    DATABASES["default"]["NAME"] = "local_test_naga.db"

# PASSWORDS
# ------------------------------------------------------------------------------
# Faster password hashing for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# Console backend for local testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CACHES
# ------------------------------------------------------------------------------
# Use local memory cache instead of Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "naga-local-test",
    },
}

# CELERY/DRAMATIQ
# ------------------------------------------------------------------------------
# Use synchronous execution for testing
DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.stub.StubBroker",
    "OPTIONS": {},
    "MIDDLEWARE": [
        "dramatiq.middleware.Retries",
        "dramatiq.middleware.AgeLimit",
        "dramatiq.middleware.TimeLimit",
    ],
}

# MEDIA
# ------------------------------------------------------------------------------
# Temporary media files for testing
MEDIA_URL = "/media/"
MEDIA_ROOT = "/tmp/naga_test_media"

# STATIC FILES
# ------------------------------------------------------------------------------
# Simplified static files for testing
STATIC_URL = "/static/"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# MIDDLEWARE
# ------------------------------------------------------------------------------
# Remove middleware that requires external services
MIDDLEWARE = [
    mw
    for mw in MIDDLEWARE
    if mw
    not in [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        # Add other middleware to exclude here
    ]
]

# LOGGING
# ------------------------------------------------------------------------------
# Simplified logging for local testing
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.db.backends": {
            "level": "WARNING",  # Reduce SQL query noise
            "handlers": ["console"],
            "propagate": False,
        },
        "apps": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# TEST RUNNER
# ------------------------------------------------------------------------------
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# INTERNATIONALIZATION
# ------------------------------------------------------------------------------
# English only for faster testing
LANGUAGE_CODE = "en-us"
USE_I18N = False
USE_TZ = True

# SECURITY
# ------------------------------------------------------------------------------
# Relaxed security for local testing
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# DEBUG TOOLBAR
# ------------------------------------------------------------------------------
# Disable debug toolbar for testing
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: False,
}

# Your local testing customizations
# ------------------------------------------------------------------------------
# Add any additional settings needed for your local testing environment
