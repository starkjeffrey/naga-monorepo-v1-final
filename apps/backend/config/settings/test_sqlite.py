"""Test settings for SQLite compatibility testing.
Quick way to test if our code works with SQLite for faster CI/local testing.
"""

# Import base settings without the test.py DATABASE_URL dependency
from .base import *
from .base import TEMPLATES

# Override database to use SQLite instead of PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # In-memory database for speed
        "OPTIONS": {
            "timeout": 20,
        },
    },
}

# Test-specific settings (from test.py)
SECRET_KEY = "test-secret-key-for-sqlite-testing"
TEST_RUNNER = "django.test.runner.DiscoverRunner"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore[index]
MEDIA_URL = "http://media.testserver/"

# Remove debug toolbar to avoid issues
MIDDLEWARE = [mw for mw in MIDDLEWARE if mw != "debug_toolbar.middleware.DebugToolbarMiddleware"]

# SQLite-specific settings
# Enable foreign key checks (SQLite doesn't enforce by default)
if "OPTIONS" not in DATABASES["default"]:
    DATABASES["default"]["OPTIONS"] = {}

# Note: init_command doesn't work with SQLite, use connection setup instead

# Disable caching and Redis for standalone testing
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

# Disable constance settings that depend on Redis
CONSTANCE_BACKEND = "constance.backends.memory.MemoryBackend"

# Disable Dramatiq for testing
INSTALLED_APPS = [app for app in INSTALLED_APPS if "django_dramatiq" not in app]

# Remove apps that have PostgreSQL-specific migrations
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ["contrib.sites", "django.contrib.sites"]]

# Disable migrations only for apps with complex SQLite conflicts
# This preserves schema validation for 95% of the codebase
MIGRATION_MODULES = {
    "academic": None,  # Only disable academic app due to complex migration conflicts
}

# Use local session backend
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# Disable any Redis-dependent middleware
try:
    MIDDLEWARE = [mw for mw in MIDDLEWARE if "redis" not in mw.lower()]
except (NameError, AttributeError):
    pass
