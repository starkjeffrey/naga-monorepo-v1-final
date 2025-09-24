"""Performance optimization utilities for web_interface app.

This module provides caching, query optimization, and performance utilities
to improve loading times for the web interface.
"""

import functools
import hashlib
import logging

from django.core.cache import cache
from django.db.models import Q
from django.utils.functional import SimpleLazyObject

logger = logging.getLogger(__name__)


class CacheManager:
    """Centralized cache management for web_interface."""

    # Cache timeouts in seconds
    TIMEOUT_SHORT = 60  # 1 minute for rapidly changing data
    TIMEOUT_MEDIUM = 300  # 5 minutes for moderately stable data
    TIMEOUT_LONG = 3600  # 1 hour for stable data
    TIMEOUT_VERY_LONG = 86400  # 24 hours for very stable data

    @staticmethod
    def make_cache_key(prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key from prefix and arguments."""
        key_parts = [prefix]

        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))

        # Add keyword arguments in sorted order for consistency
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")

        # Create hash for long keys
        full_key = ":".join(key_parts)
        if len(full_key) > 250:  # Django cache key limit
            # Use a secure hash for shortening long keys
            hash_suffix = hashlib.sha256(full_key.encode()).hexdigest()[:8]
            full_key = f"{prefix}:{hash_suffix}"

        return full_key

    @classmethod
    def cached_result(cls, timeout=TIMEOUT_MEDIUM, key_prefix=None):
        """Decorator for caching function results."""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                prefix = key_prefix or f"{func.__module__}.{func.__name__}"
                cache_key = cls.make_cache_key(prefix, *args, **kwargs)

                # Try to get from cache
                result = cache.get(cache_key)
                if result is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return result

                # Calculate result and cache it
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                logger.debug(f"Cache miss for {cache_key}, cached for {timeout}s")

                return result

            # Add method to clear cache
            def clear_cache(*args, **kwargs):
                prefix = key_prefix or f"{func.__module__}.{func.__name__}"
                cache_key = cls.make_cache_key(prefix, *args, **kwargs)
                cache.delete(cache_key)
                logger.debug(f"Cleared cache for {cache_key}")

            wrapper.clear_cache = clear_cache
            return wrapper

        return decorator


class QueryOptimizer:
    """Database query optimization utilities."""

    @staticmethod
    def optimize_student_queryset(queryset, for_list=False, for_detail=False):
        """Optimize StudentProfile queryset based on usage context."""
        if for_list:
            # For list views, only select necessary fields
            queryset = queryset.select_related("person").only(
                "id",
                "student_id",
                "current_status",
                "study_time_preference",
                "last_enrollment_date",
                "person__id",
                "person__full_name",
                "person__family_name",
                "person__personal_name",
                "person__khmer_name",
                "person__school_email",
                "person__personal_email",
                "created_at",
                "is_deleted",
            )
        elif for_detail:
            # For detail views, prefetch related data
            queryset = queryset.select_related(
                "person",
                "program_enrollment__program",
                "program_enrollment__major",
                "program_enrollment__cycle",
                "program_enrollment__division",
            ).prefetch_related(
                "class_enrollments__class_header__course",
                "class_enrollments__class_header__term",
                "gpa_records",
                "invoices",
            )
        else:
            # Default optimization
            queryset = queryset.select_related("person")

        return queryset

    @staticmethod
    def optimize_enrollment_queryset(queryset, include_grades=False):
        """Optimize ClassHeaderEnrollment queryset."""
        queryset = queryset.select_related(
            "student__person",
            "class_header__course",
            "class_header__term",
            "class_header__teacher__person",
        )

        if include_grades:
            queryset = queryset.prefetch_related(
                "class_part_grades__class_part",
            )

        return queryset

    @staticmethod
    def optimize_invoice_queryset(queryset):
        """Optimize Invoice queryset."""
        return queryset.select_related(
            "student__person",
            "term",
        ).prefetch_related(
            "invoice_items",
            "payments",
        )


class LazyContextLoader:
    """Lazy loading for expensive context data."""

    @staticmethod
    def lazy_load(func):
        """Decorator to make a function lazy-evaluated."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return SimpleLazyObject(lambda: func(*args, **kwargs))

        return wrapper

    @staticmethod
    def get_dashboard_stats(user, role):
        """Lazy load dashboard statistics based on role."""
        from apps.web_interface.views.dashboard_views import DashboardView

        view = DashboardView()
        view.request = type("Request", (), {"user": user})()

        if role == "admin":
            return LazyContextLoader.lazy_load(view.get_admin_context)()
        elif role == "staff":
            return LazyContextLoader.lazy_load(view.get_staff_context)()
        elif role == "teacher":
            return LazyContextLoader.lazy_load(view.get_teacher_context)()
        elif role == "finance":
            return LazyContextLoader.lazy_load(view.get_finance_context)()
        else:
            return LazyContextLoader.lazy_load(view.get_student_context)()


class PerformanceMiddleware:
    """Middleware to add performance optimizations to requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add query count tracking in debug mode
        if hasattr(request, "user") and request.user.is_authenticated:
            # Cache user's role for the request
            if not hasattr(request, "_cached_role"):
                request._cached_role = request.session.get("current_role")

        response = self.get_response(request)
        return response


# Cached functions for commonly accessed data
@CacheManager.cached_result(timeout=CacheManager.TIMEOUT_LONG, key_prefix="current_term")
def get_cached_current_term():
    """Get current term with caching (backward compatibility)."""
    from apps.curriculum.services import TermService

    return TermService.get_current_term()


@CacheManager.cached_result(timeout=CacheManager.TIMEOUT_LONG, key_prefix="active_terms")
def get_cached_active_terms():
    """Get all active terms with caching.

    Returns all 4 typically active terms (ENG_A, ENG_B, BA, MA).
    """
    from apps.curriculum.services import TermService

    return TermService.get_all_active_terms()


@CacheManager.cached_result(timeout=CacheManager.TIMEOUT_LONG, key_prefix="active_terms_by_type")
def get_cached_active_terms_by_type():
    """Get active terms organized by type with caching.

    Returns dict with keys: ENG_A, ENG_B, BA, MA, SPECIAL
    """
    from apps.curriculum.services import TermService

    return TermService.get_active_terms_by_type()


@CacheManager.cached_result(timeout=CacheManager.TIMEOUT_MEDIUM, key_prefix="user_permissions")
def get_cached_user_permissions(user_id):
    """Get user permissions with caching."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        return list(user.get_all_permissions())
    except User.DoesNotExist:
        return []


@CacheManager.cached_result(timeout=CacheManager.TIMEOUT_MEDIUM, key_prefix="student_stats")
def get_cached_student_stats():
    """Get cached student statistics for dashboard."""
    from django.db.models import Count

    from apps.people.models import StudentProfile

    return StudentProfile.objects.aggregate(
        total_active=Count("id", filter=Q(current_status__in=["ACTIVE", "ENROLLED"])),
        total_graduated=Count("id", filter=Q(current_status="GRADUATED")),
        total_inactive=Count("id", filter=Q(current_status="INACTIVE")),
    )


# Database connection pooling configuration
DATABASE_CONNECTION_POOLING = {
    "max_connections": 100,
    "max_idle_time": 300,  # 5 minutes
    "max_lifetime": 3600,  # 1 hour
}


# Query optimization hints
QUERY_HINTS = {
    "student_list": {
        "select_related": ["person"],
        "only": [
            "id",
            "student_id",
            "current_status",
            "study_time_preference",
            "last_enrollment_date",
            "person__full_name",
            "person__school_email",
            "person__personal_email",
        ],
        "prefetch_related": [],
    },
    "enrollment_list": {
        "select_related": [
            "student__person",
            "class_header__course",
            "class_header__term",
        ],
        "prefetch_related": ["class_part_grades"],
    },
    "invoice_list": {
        "select_related": ["student__person", "term"],
        "prefetch_related": ["invoice_items", "payments"],
    },
}
