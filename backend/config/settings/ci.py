"""Optimized settings for CI/CD environments (GitHub Actions)."""

from .test import *

# Override REDIS_URL before it's used by other settings
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

# GENERAL
# ------------------------------------------------------------------------------
# Use a fixed secret key for CI consistency
SECRET_KEY = "test-secret-key-for-ci-only-not-for-production"

# DATABASE
# ------------------------------------------------------------------------------
# Use PostgreSQL in CI (GitHub Actions services)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME", default="test_naga"),
        "USER": env("DATABASE_USER", default="postgres"),
        "PASSWORD": env("DATABASE_PASSWORD", default="postgres"),
        "HOST": env("DATABASE_HOST", default="localhost"),
        "PORT": env("DATABASE_PORT", default="5432"),
        "TEST": {
            "NAME": "test_naga_ci",
        },
    },
}

# CACHING
# ------------------------------------------------------------------------------
# Use Redis for caching in CI
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "KEY_PREFIX": "test",
        "TIMEOUT": 300,
    },
}

# DRAMATIQ
# ------------------------------------------------------------------------------
# Use Redis broker for Dramatiq in CI
DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.redis.RedisBroker",
    "OPTIONS": {
        "url": REDIS_URL,  # Use the REDIS_URL set above
    },
}

# CONSTANCE
# ------------------------------------------------------------------------------
# Override Constance Redis connection for CI
CONSTANCE_REDIS_CONNECTION = REDIS_URL


# TESTING OPTIMIZATIONS
# ------------------------------------------------------------------------------
# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


# Only disable migrations if explicitly requested
if env.bool("DISABLE_MIGRATIONS", default=False):
    MIGRATION_MODULES = DisableMigrations()  # type: ignore[assignment]

# LOGGING
# ------------------------------------------------------------------------------
# Reduce logging noise in CI
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "formatters": {
        "simple": {
            "format": "{levelname} {name} {message}",
            "style": "{",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# STATIC FILES
# ------------------------------------------------------------------------------
# Skip static file collection in CI tests
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# SECURITY
# ------------------------------------------------------------------------------
# Disable security checks for CI
SECURE_SSL_REDIRECT = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
