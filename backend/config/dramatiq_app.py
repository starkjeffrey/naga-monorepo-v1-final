"""Dramatiq configuration for the Naga backend.

This module configures Dramatiq for async task processing, replacing Celery
with a simpler, more performant task queue system.
"""

import os
import ssl
from urllib.parse import urlparse

import dramatiq
from django.conf import settings
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, Retries, TimeLimit


def setup_dramatiq():
    """Set up Dramatiq with Redis broker and middleware.

    This function configures the Dramatiq task queue system with:
    - Redis broker for task distribution
    - Appropriate middleware for production use
    - SSL support when required
    """
    # Get Redis connection details from Django settings
    redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
    redis_ssl = getattr(settings, "REDIS_SSL", False)

    # Parse Redis URL for connection details
    parsed_url = urlparse(redis_url)

    # Configure Redis broker options
    broker_options = {
        "host": parsed_url.hostname or "localhost",
        "port": parsed_url.port or 6379,
        "db": int(parsed_url.path.lstrip("/")) if parsed_url.path else 0,
    }

    # Add password if present
    if parsed_url.password:
        broker_options["password"] = parsed_url.password

    # Add SSL configuration if required
    if redis_ssl:
        broker_options["connection_kwargs"] = {
            "ssl_cert_reqs": ssl.CERT_NONE,
        }

    # Create Redis broker
    redis_broker = RedisBroker(**broker_options)

    # Add middleware for production reliability
    redis_broker.add_middleware(AgeLimit(max_age=3600000))  # 1 hour max age
    redis_broker.add_middleware(TimeLimit(time_limit=300000))  # 5 minute timeout
    redis_broker.add_middleware(Retries(max_retries=3))  # Retry failed tasks up to 3 times

    # Set broker globally
    dramatiq.set_broker(redis_broker)

    return redis_broker


# Set up Dramatiq when module is imported
redis_broker = setup_dramatiq()


# Auto-discover tasks from Django apps
def autodiscover_tasks():
    """Auto-discover Dramatiq actors from all Django apps.

    Similar to Celery's autodiscover_tasks, this function imports
    task modules from all installed Django apps.
    """
    if hasattr(settings, "INSTALLED_APPS"):
        for app_name in settings.INSTALLED_APPS:
            try:
                # Try to import tasks module from each app
                __import__(f"{app_name}.tasks")
            except ImportError:
                # No tasks module in this app, continue
                pass
            except Exception as e:
                # Log other import errors but don't fail
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Error importing tasks from {app_name}: {e}")


# Auto-discover when not in Django setup
if os.environ.get("DJANGO_SETTINGS_MODULE"):
    try:
        import django

        if django.apps.apps.ready:
            autodiscover_tasks()
    except Exception:
        # During Django setup, apps might not be ready yet
        pass
