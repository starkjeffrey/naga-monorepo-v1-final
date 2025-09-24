"""Migration environment settings.
Includes legacy import models for data migration.
"""

from .local import *

# Single database for migration environment - Uses DATABASE_URL from migration env
DATABASES = {
    "default": env.db("DATABASE_URL"),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# Remove database router - using single database
DATABASE_ROUTERS: list[str] = []

# Migration environment apps - includes legacy import capabilities
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
    # Add any legacy import apps here when needed
]

# Rebuild INSTALLED_APPS
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Migration-specific settings
MIGRATION_MODE = True

# Disable debug toolbar for admin access
DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: False}

# Remove debug toolbar from installed apps
if "debug_toolbar" in INSTALLED_APPS:
    INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]

# Remove debug toolbar middleware
if "debug_toolbar.middleware.DebugToolbarMiddleware" in MIDDLEWARE:
    MIDDLEWARE = [mw for mw in MIDDLEWARE if mw != "debug_toolbar.middleware.DebugToolbarMiddleware"]
