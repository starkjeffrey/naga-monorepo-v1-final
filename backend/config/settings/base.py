"""Base settings to build other settings files upon."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# naga_backend_v1/
APPS_DIR = BASE_DIR
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "Asia/Phnom_Penh"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#languages
# from django.utils.translation import gettext_lazy as _
# LANGUAGES = [
#     ('en', _('English')),
#     ('fr-fr', _('French')),
#     ('pt-br', _('Portuguese')),
# ]
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/
STATIC_URL = "/static/"
STATICFILES_DIRS = [str(BASE_DIR / "static")]
STATIC_ROOT = str(BASE_DIR / "staticfiles")

# Media files (User-uploaded files)
MEDIA_URL = "/media/"
MEDIA_ROOT = str(BASE_DIR / "media")

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3"),
}

DATABASES["default"]["ATOMIC_REQUESTS"] = True

# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CHANNELS
# ------------------------------------------------------------------------------
# https://channels.readthedocs.io/en/stable/topics/channel_layers.html
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL", default="redis://localhost:6379/0")],
        },
    },
}

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"
# https://channels.readthedocs.io/en/stable/installation.html#configure-django
ASGI_APPLICATION = "config.asgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # Handy template tags
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_tailwind",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.socialaccount",
    "compressor",
    "django_dramatiq",
    # "constance",  # Disabled due to User model field conflicts
    "widget_tweaks",
    # "channels",  # Temporarily disabled for testing
    "django_htmx",
]

LOCAL_APPS = [
    "users",  # Re-enabled - required for AUTH_USER_MODEL
    "apps.accounts",
    "apps.common",
    "apps.people",
    "apps.curriculum",
    "apps.academic",
    "apps.language",
    "apps.enrollment",
    "apps.scheduling",
    "apps.attendance",
    "apps.leave_management",  # Teacher leave and substitute management
    "apps.grading",
    "apps.finance",
    "apps.scholarships",
    "apps.academic_records",
    "apps.level_testing",
    "apps.mobile",
    "apps.web_interface",
    # "apps.moodle",  # Keep disabled - missing model references
    "apps.data_pipeline",  # Data pipeline for legacy data processing
    # Your stuff: custom apps go here
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "apps.common.auth_backends.EmailBackend",  # Custom backend for email authentication
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # Custom middleware for performance - TEMPORARILY DISABLED during troubleshooting
    # "apps.common.middleware.current_term.CurrentTermMiddleware",
    # "apps.web_interface.performance.PerformanceMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]

# Django Compressor settings
COMPRESS_ENABLED = True
COMPRESS_CSS_FILTERS = ["compressor.filters.css_default.CssAbsoluteFilter", "compressor.filters.cssmin.CSSMinFilter"]
COMPRESS_JS_FILTERS = ["compressor.filters.jsmin.JSMinFilter"]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [str(APPS_DIR / "templates")],
        # https://docs.djangoproject.com/en/dev/ref/settings/#app-dirs
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "users.context_processors.allauth_settings",
                "apps.common.context_processors.navigation_context",
                "apps.common.context_processors.system_context",
            ],
        },
    },
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "tailwind"
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5
PHOTO_ADMIN_EMAILS = ["admin@pucsr.edu.kh"]
# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""Jeffrey STARK""", "stark.jeffrey@pucsr.edu.kh")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
# https://cookiecutter-django.readthedocs.io/en/latest/settings.html#other-environment-settings
# Force the `admin` sign in process to go through the `django-allauth` workflow
DJANGO_ADMIN_FORCE_ALLAUTH = env.bool("DJANGO_ADMIN_FORCE_ALLAUTH", default=False)

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")
REDIS_SSL = REDIS_URL.startswith("rediss://")

# Dramatiq
# ------------------------------------------------------------------------------
# https://dramatiq.io/guide.html#configuration
DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.redis.RedisBroker",
    "OPTIONS": {
        "url": REDIS_URL,
    },
    "MIDDLEWARE": [
        "dramatiq.middleware.AgeLimit",
        "dramatiq.middleware.TimeLimit",
        "dramatiq.middleware.Retries",
        "django_dramatiq.middleware.DbConnectionsMiddleware",
        "django_dramatiq.middleware.AdminMiddleware",
    ],
}

# Task processing configuration
DRAMATIQ_TASK_TIME_LIMIT = 5 * 60 * 1000  # 5 minutes in milliseconds
DRAMATIQ_TASK_MAX_AGE = 60 * 60 * 1000  # 1 hour in milliseconds
DRAMATIQ_TASK_MAX_RETRIES = 3
# CACHING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

# Session configuration to use Redis
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_LOGIN_METHODS = {"email"}
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_ADAPTER = "users.adapters.AccountAdapter"
# https://docs.allauth.org/en/latest/account/forms.html
ACCOUNT_FORMS = {"signup": "users.forms.UserSignupForm"}
# https://docs.allauth.org/en/latest/socialaccount/configuration.html
SOCIALACCOUNT_ADAPTER = "users.adapters.SocialAccountAdapter"
# https://docs.allauth.org/en/latest/socialaccount/configuration.html
SOCIALACCOUNT_FORMS = {
    "signup": "users.forms.UserSocialSignupForm",
}

# Google OAuth Configuration for Mobile Apps
# ------------------------------------------------------------------------------
# Google OAuth Client ID for mobile authentication
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
# Google OAuth Client Secret (for server-side verification)
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
# Mobile API Configuration
MOBILE_API_MAX_REQUEST_SIZE = env.int("MOBILE_API_MAX_REQUEST_SIZE", default=1024 * 1024)  # 1MB
MOBILE_API_RATE_LIMIT_ATTEMPTS = env.int("MOBILE_API_RATE_LIMIT_ATTEMPTS", default=5)
MOBILE_API_RATE_LIMIT_WINDOW = env.int("MOBILE_API_RATE_LIMIT_WINDOW", default=300)  # 5 minutes


# Constance
# ------------------------------------------------------------------------------
# https://django-constance.readthedocs.io/en/latest/
CONSTANCE_BACKEND = "constance.backends.redisd.RedisBackend"
CONSTANCE_REDIS_CONNECTION = REDIS_URL

# Initial configuration - will be expanded when specific constants are identified
CONSTANCE_CONFIG = {
    "SYSTEM_SCHOOL_NAME": (
        "Naga University",
        "The name of the educational institution",
        str,
    ),
    "SYSTEM_ACADEMIC_YEAR": (
        "2024-2025",
        "Current academic year",
        str,
    ),
}

CONSTANCE_CONFIG_FIELDSETS = {
    "System Settings": {
        "fields": ("SYSTEM_SCHOOL_NAME", "SYSTEM_ACADEMIC_YEAR"),
        "collapse": False,
    },
}

# MOODLE INTEGRATION
# ------------------------------------------------------------------------------
# Moodle LMS integration configuration
MOODLE_INTEGRATION = {
    "ENABLED": env.bool("MOODLE_ENABLED", False),
    "BASE_URL": env("MOODLE_URL", default=""),
    "API_TOKEN": env("MOODLE_API_TOKEN", default=""),
    "AUTO_SYNC": env.bool("MOODLE_AUTO_SYNC", True),
    "DEFAULT_CATEGORY_ID": env.int("MOODLE_DEFAULT_CATEGORY_ID", 1),
    "USERNAME_PREFIX": env("MOODLE_USERNAME_PREFIX", default="sis_"),
}

# THERMAL PRINTER CONFIGURATION
# ------------------------------------------------------------------------------
# Thermal printer settings for level testing receipts
THERMAL_PRINTER = {
    "TYPE": env("THERMAL_PRINTER_TYPE", default="network"),  # 'network', 'usb', 'serial'
    "HOST": env("THERMAL_PRINTER_HOST", default="192.168.1.100"),  # For network printers
    "PORT": env.int("THERMAL_PRINTER_PORT", default=9100),  # For network printers
    "VENDOR_ID": env("THERMAL_PRINTER_VENDOR_ID", default="0x04b8"),  # For USB printers (hex string)
    "PRODUCT_ID": env("THERMAL_PRINTER_PRODUCT_ID", default="0x0202"),  # For USB printers (hex string)
    "DEVICE": env("THERMAL_PRINTER_DEVICE", default="/dev/ttyUSB0"),  # For serial printers
    "BAUDRATE": env.int("THERMAL_PRINTER_BAUDRATE", default=9600),  # For serial printers
}

# Application URLs for QR codes
BASE_URL = env("BASE_URL", default="http://localhost:8000")

# Your stuff...
# ------------------------------------------------------------------------------
