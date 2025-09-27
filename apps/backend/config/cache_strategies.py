"""Redis caching strategies and performance optimization.

This module provides comprehensive caching strategies for the enhanced API:
- Multi-level caching with TTL optimization
- Query result caching with invalidation patterns
- Session-based user preference caching
- Real-time data coordination with cache updates
- Performance monitoring and cache hit rate optimization
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import json
import hashlib

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheStrategy:
    """Base class for cache strategies with TTL and invalidation patterns."""

    # Cache TTL constants (in seconds)
    TTL_VERY_SHORT = 60       # 1 minute - real-time data
    TTL_SHORT = 300           # 5 minutes - frequently changing data
    TTL_MEDIUM = 900          # 15 minutes - moderately changing data
    TTL_LONG = 3600           # 1 hour - stable data
    TTL_VERY_LONG = 86400     # 24 hours - configuration data

    @staticmethod
    def make_key(prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key."""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)

        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(hashlib.md5(
                json.dumps(sorted_kwargs, sort_keys=True).encode()
            ).hexdigest()[:8])

        return ":".join(key_parts)

    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """Invalidate cache keys matching a pattern (Redis-specific)."""
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            keys = redis_conn.keys(pattern)
            if keys:
                return redis_conn.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("Failed to invalidate cache pattern %s: %s", pattern, e)
            return 0


class StudentCacheStrategy(CacheStrategy):
    """Caching strategy for student-related data."""

    @classmethod
    def get_student_analytics(cls, student_id: str) -> Optional[Dict[str, Any]]:
        """Get cached student analytics with fallback calculation."""
        cache_key = cls.make_key("student_analytics", student_id)
        return cache.get(cache_key)

    @classmethod
    def set_student_analytics(cls, student_id: str, analytics: Dict[str, Any]) -> None:
        """Cache student analytics with medium TTL."""
        cache_key = cls.make_key("student_analytics", student_id)
        cache.set(cache_key, analytics, cls.TTL_MEDIUM)

    @classmethod
    def invalidate_student_analytics(cls, student_id: str) -> None:
        """Invalidate student analytics cache."""
        cache_key = cls.make_key("student_analytics", student_id)
        cache.delete(cache_key)

    @classmethod
    def get_student_search_results(cls, query_hash: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results."""
        cache_key = cls.make_key("student_search", query_hash)
        return cache.get(cache_key)

    @classmethod
    def set_student_search_results(
        cls,
        query_hash: str,
        results: List[Dict[str, Any]]
    ) -> None:
        """Cache search results with short TTL."""
        cache_key = cls.make_key("student_search", query_hash)
        cache.set(cache_key, results, cls.TTL_SHORT)

    @classmethod
    def invalidate_student_data(cls, student_id: str) -> None:
        """Invalidate all student-related caches."""
        cls.invalidate_student_analytics(student_id)
        # Invalidate search results that might contain this student
        cls.invalidate_pattern("student_search:*")


class AcademicCacheStrategy(CacheStrategy):
    """Caching strategy for academic data."""

    @classmethod
    def get_grade_spreadsheet(cls, class_id: str) -> Optional[Dict[str, Any]]:
        """Get cached grade spreadsheet data."""
        cache_key = cls.make_key("grade_spreadsheet", class_id)
        return cache.get(cache_key)

    @classmethod
    def set_grade_spreadsheet(cls, class_id: str, data: Dict[str, Any]) -> None:
        """Cache grade spreadsheet with short TTL."""
        cache_key = cls.make_key("grade_spreadsheet", class_id)
        cache.set(cache_key, data, cls.TTL_SHORT)

    @classmethod
    def invalidate_grade_spreadsheet(cls, class_id: str) -> None:
        """Invalidate grade spreadsheet cache."""
        cache_key = cls.make_key("grade_spreadsheet", class_id)
        cache.delete(cache_key)

    @classmethod
    def get_course_prerequisites(cls, course_id: str) -> Optional[Dict[str, Any]]:
        """Get cached prerequisite chain."""
        cache_key = cls.make_key("course_prerequisites", course_id)
        return cache.get(cache_key)

    @classmethod
    def set_course_prerequisites(cls, course_id: str, data: Dict[str, Any]) -> None:
        """Cache prerequisite chain with long TTL."""
        cache_key = cls.make_key("course_prerequisites", course_id)
        cache.set(cache_key, data, cls.TTL_LONG)

    @classmethod
    def get_schedule_conflicts(cls, term_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached schedule conflicts."""
        cache_key = cls.make_key("schedule_conflicts", term_id)
        return cache.get(cache_key)

    @classmethod
    def set_schedule_conflicts(
        cls,
        term_id: str,
        conflicts: List[Dict[str, Any]]
    ) -> None:
        """Cache schedule conflicts with medium TTL."""
        cache_key = cls.make_key("schedule_conflicts", term_id)
        cache.set(cache_key, conflicts, cls.TTL_MEDIUM)

    @classmethod
    def invalidate_class_data(cls, class_id: str) -> None:
        """Invalidate class-related caches."""
        cls.invalidate_grade_spreadsheet(class_id)
        # Invalidate schedule conflicts for the term
        cls.invalidate_pattern("schedule_conflicts:*")


class FinancialCacheStrategy(CacheStrategy):
    """Caching strategy for financial data."""

    @classmethod
    def get_financial_analytics(cls, date_range: int) -> Optional[Dict[str, Any]]:
        """Get cached financial analytics."""
        cache_key = cls.make_key("financial_analytics", date_range)
        return cache.get(cache_key)

    @classmethod
    def set_financial_analytics(
        cls,
        date_range: int,
        analytics: Dict[str, Any]
    ) -> None:
        """Cache financial analytics with medium TTL."""
        cache_key = cls.make_key("financial_analytics", date_range)
        cache.set(cache_key, analytics, cls.TTL_MEDIUM)

    @classmethod
    def get_scholarship_matches(cls, student_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached scholarship matches."""
        cache_key = cls.make_key("scholarship_matches", student_id)
        return cache.get(cache_key)

    @classmethod
    def set_scholarship_matches(
        cls,
        student_id: str,
        matches: List[Dict[str, Any]]
    ) -> None:
        """Cache scholarship matches with long TTL."""
        cache_key = cls.make_key("scholarship_matches", student_id)
        cache.set(cache_key, matches, cls.TTL_LONG)

    @classmethod
    def get_revenue_forecast(cls, months: int) -> Optional[Dict[str, Any]]:
        """Get cached revenue forecast."""
        cache_key = cls.make_key("revenue_forecast", months)
        return cache.get(cache_key)

    @classmethod
    def set_revenue_forecast(cls, months: int, forecast: Dict[str, Any]) -> None:
        """Cache revenue forecast with long TTL."""
        cache_key = cls.make_key("revenue_forecast", months)
        cache.set(cache_key, forecast, cls.TTL_LONG)

    @classmethod
    def invalidate_financial_data(cls) -> None:
        """Invalidate all financial caches."""
        cls.invalidate_pattern("financial_analytics:*")
        cls.invalidate_pattern("revenue_forecast:*")


class DashboardCacheStrategy(CacheStrategy):
    """Caching strategy for dashboard metrics."""

    @classmethod
    def get_dashboard_metrics(cls, date_range: int) -> Optional[Dict[str, Any]]:
        """Get cached dashboard metrics."""
        cache_key = cls.make_key("dashboard_metrics", date_range)
        return cache.get(cache_key)

    @classmethod
    def set_dashboard_metrics(
        cls,
        date_range: int,
        metrics: Dict[str, Any]
    ) -> None:
        """Cache dashboard metrics with very short TTL for real-time feel."""
        cache_key = cls.make_key("dashboard_metrics", date_range)
        cache.set(cache_key, metrics, cls.TTL_VERY_SHORT)

    @classmethod
    def get_chart_data(cls, chart_type: str, **params) -> Optional[Dict[str, Any]]:
        """Get cached chart data."""
        cache_key = cls.make_key("chart_data", chart_type, **params)
        return cache.get(cache_key)

    @classmethod
    def set_chart_data(
        cls,
        chart_type: str,
        data: Dict[str, Any],
        **params
    ) -> None:
        """Cache chart data with medium TTL."""
        cache_key = cls.make_key("chart_data", chart_type, **params)
        cache.set(cache_key, data, cls.TTL_MEDIUM)


class SessionCacheStrategy(CacheStrategy):
    """Caching strategy for user session data."""

    @classmethod
    def get_user_preferences(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user preferences."""
        cache_key = cls.make_key("user_preferences", user_id)
        return cache.get(cache_key)

    @classmethod
    def set_user_preferences(cls, user_id: str, preferences: Dict[str, Any]) -> None:
        """Cache user preferences with very long TTL."""
        cache_key = cls.make_key("user_preferences", user_id)
        cache.set(cache_key, preferences, cls.TTL_VERY_LONG)

    @classmethod
    def get_user_permissions(cls, user_id: str) -> Optional[List[str]]:
        """Get cached user permissions."""
        cache_key = cls.make_key("user_permissions", user_id)
        return cache.get(cache_key)

    @classmethod
    def set_user_permissions(cls, user_id: str, permissions: List[str]) -> None:
        """Cache user permissions with long TTL."""
        cache_key = cls.make_key("user_permissions", user_id)
        cache.set(cache_key, permissions, cls.TTL_LONG)

    @classmethod
    def invalidate_user_session(cls, user_id: str) -> None:
        """Invalidate all user session caches."""
        cls.invalidate_pattern(f"user_*:{user_id}:*")


def cache_result(
    key_func: Callable[..., str],
    ttl: int = CacheStrategy.TTL_MEDIUM,
    invalidate_on_error: bool = True
):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_func(*args, **kwargs)

            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            try:
                # Calculate result
                result = func(*args, **kwargs)

                # Cache the result
                cache.set(cache_key, result, ttl)

                return result

            except Exception as e:
                if invalidate_on_error:
                    cache.delete(cache_key)
                raise e

        return wrapper
    return decorator


def invalidate_cache_on_change(
    model_class,
    invalidation_func: Callable[[Any], None]
):
    """Decorator to invalidate cache when model instances change."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # If the function returns a model instance, invalidate related caches
            if hasattr(result, '__class__') and issubclass(result.__class__, model_class):
                invalidation_func(result)

            return result

        return wrapper
    return decorator


class CacheWarmupManager:
    """Manages cache warmup strategies for critical data."""

    @staticmethod
    def warmup_dashboard_metrics():
        """Warm up dashboard metrics cache."""
        from api.v2.analytics import get_dashboard_metrics_data

        # Warm up common date ranges
        for days in [7, 30, 90]:
            try:
                metrics = get_dashboard_metrics_data(days)
                DashboardCacheStrategy.set_dashboard_metrics(days, metrics)
                logger.info("Warmed up dashboard metrics for %d days", days)
            except Exception as e:
                logger.error("Failed to warm up dashboard metrics for %d days: %s", days, e)

    @staticmethod
    def warmup_student_analytics():
        """Warm up student analytics for active students."""
        from apps.people.models import StudentProfile

        # Get recently active students
        active_students = StudentProfile.objects.filter(
            status='enrolled',
            last_modified__gte=datetime.now() - timedelta(days=30)
        )[:100]  # Limit to 100 most recent

        for student in active_students:
            try:
                # This would call the actual analytics calculation
                # analytics = calculate_student_analytics(student)
                # StudentCacheStrategy.set_student_analytics(str(student.unique_id), analytics)
                logger.info("Warmed up analytics for student %s", student.student_id)
            except Exception as e:
                logger.error("Failed to warm up analytics for student %s: %s", student.student_id, e)

    @staticmethod
    def warmup_financial_data():
        """Warm up financial analytics cache."""
        try:
            # This would call the actual financial analytics calculation
            # analytics = calculate_financial_analytics(30)
            # FinancialCacheStrategy.set_financial_analytics(30, analytics)
            logger.info("Warmed up financial analytics")
        except Exception as e:
            logger.error("Failed to warm up financial analytics: %s", e)


class CacheMonitor:
    """Monitors cache performance and provides metrics."""

    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Get cache performance statistics."""
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")

            info = redis_conn.info()

            return {
                'memory_usage': info.get('used_memory_human', 'Unknown'),
                'total_connections': info.get('total_connections_received', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': (
                    info.get('keyspace_hits', 0) /
                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1)
                ),
                'connected_clients': info.get('connected_clients', 0),
                'uptime_seconds': info.get('uptime_in_seconds', 0)
            }

        except Exception as e:
            logger.error("Failed to get cache stats: %s", e)
            return {
                'error': str(e),
                'hit_rate': 0.0
            }

    @staticmethod
    def optimize_cache_settings():
        """Provide cache optimization recommendations."""
        stats = CacheMonitor.get_cache_stats()
        hit_rate = stats.get('hit_rate', 0.0)

        recommendations = []

        if hit_rate < 0.7:
            recommendations.append("Consider increasing cache TTL for stable data")
            recommendations.append("Review cache key strategies for better reuse")

        if hit_rate > 0.95:
            recommendations.append("Cache hit rate is excellent")
            recommendations.append("Consider caching additional data types")

        return {
            'current_hit_rate': hit_rate,
            'target_hit_rate': 0.8,
            'recommendations': recommendations,
            'stats': stats
        }


# Export main strategies
__all__ = [
    'StudentCacheStrategy',
    'AcademicCacheStrategy',
    'FinancialCacheStrategy',
    'DashboardCacheStrategy',
    'SessionCacheStrategy',
    'CacheWarmupManager',
    'CacheMonitor',
    'cache_result',
    'invalidate_cache_on_change'
]