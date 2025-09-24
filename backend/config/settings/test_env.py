"""Test environment settings.
Clean test environment with no legacy models.
"""

from .local import *

# Ensure SECRET_KEY is available for tests
SECRET_KEY = "test-secret-key-for-testing-only-not-for-production-use"

# Override for test environment
DATABASES = {
    "default": env.db("DATABASE_URL"),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# Remove database router for test environment
DATABASE_ROUTERS: list[str] = []

# Test environment apps - NO legacy import apps
LOCAL_APPS = [
    "users",
    "apps.accounts",
    "apps.common",
    "apps.people",
    "apps.curriculum",
    "apps.academic",
    "apps.language",
    "apps.enrollment",
    "apps.scheduling",
    "apps.attendance",
    "apps.grading",
    "apps.finance",
    "apps.scholarships",
    "apps.academic_records",
    "apps.level_testing",
]

# Rebuild INSTALLED_APPS with clean app list
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
