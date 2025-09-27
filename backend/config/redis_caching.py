"""Advanced Redis caching strategy with multi-level optimization."""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
import redis
import hashlib

logger = logging.getLogger(__name__)


class CacheTier:
    """Cache tier enumeration for different cache strategies."""
    L1_MEMORY = "l1_memory"  # In-memory, fastest, smallest
    L2_REDIS = "l2_redis"    # Redis, fast, medium size
    L3_DATABASE = "l3_database"  # Database cache table, slower, largest


class CacheCategory:
    """Cache categories with different TTL strategies."""
    STUDENT_DATA = "student_data"          # 15 minutes
    ACADEMIC_RECORDS = "academic_records"  # 30 minutes
    FINANCIAL_DATA = "financial_data"      # 10 minutes
    ANALYTICS = "analytics"                # 5 minutes
    DASHBOARD_METRICS = "dashboard"        # 2 minutes
    SEARCH_RESULTS = "search"              # 5 minutes
    USER_SESSIONS = "sessions"             # 24 hours
    COLLABORATION = "collaboration"        # 5 minutes
    STATIC_DATA = "static"                 # 1 hour


class AdvancedCacheManager:
    """Advanced caching manager with multi-tier strategy."""

    def __init__(self):
        """Initialize cache manager with Redis connection."""
        self.redis_client = redis.Redis.from_url(
            getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        )

        # Cache TTL configuration (in seconds)
        self.ttl_config = {
            CacheCategory.STUDENT_DATA: 900,      # 15 minutes
            CacheCategory.ACADEMIC_RECORDS: 1800,  # 30 minutes
            CacheCategory.FINANCIAL_DATA: 600,     # 10 minutes
            CacheCategory.ANALYTICS: 300,          # 5 minutes
            CacheCategory.DASHBOARD_METRICS: 120,  # 2 minutes
            CacheCategory.SEARCH_RESULTS: 300,     # 5 minutes
            CacheCategory.USER_SESSIONS: 86400,    # 24 hours
            CacheCategory.COLLABORATION: 300,      # 5 minutes
            CacheCategory.STATIC_DATA: 3600,       # 1 hour
        }

        # Cache size limits (in bytes)
        self.size_limits = {
            CacheCategory.ANALYTICS: 10 * 1024 * 1024,  # 10MB
            CacheCategory.SEARCH_RESULTS: 50 * 1024 * 1024,  # 50MB
            CacheCategory.STUDENT_DATA: 100 * 1024 * 1024,  # 100MB
        }

    def generate_key(self, category: str, identifier: str, params: Optional[Dict] = None) -> str:
        """Generate consistent cache key with category prefix."""
        base_key = f"{category}:{identifier}"

        if params:
            # Sort params for consistent key generation
            param_str = json.dumps(params, sort_keys=True, cls=DjangoJSONEncoder)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            base_key += f":{param_hash}"

        return base_key

    def set(
        self,
        category: str,
        identifier: str,
        data: Any,
        params: Optional[Dict] = None,
        ttl: Optional[int] = None,
        tier: str = CacheTier.L2_REDIS
    ) -> bool:
        """Set cache value with advanced options."""
        try:
            key = self.generate_key(category, identifier, params)
            ttl = ttl or self.ttl_config.get(category, 300)

            # Serialize data
            serialized_data = self._serialize_data(data)

            # Check size limits
            if category in self.size_limits:
                if len(serialized_data) > self.size_limits[category]:
                    logger.warning("Data too large for cache category %s", category)
                    return False

            # Store in specified tier
            if tier == CacheTier.L1_MEMORY:
                return self._set_memory_cache(key, serialized_data, ttl)
            elif tier == CacheTier.L2_REDIS:
                return self._set_redis_cache(key, serialized_data, ttl)
            else:
                logger.warning("Unsupported cache tier: %s", tier)
                return False

        except Exception as e:
            logger.error("Cache set error for %s:%s - %s", category, identifier, e)
            return False

    def get(
        self,
        category: str,
        identifier: str,
        params: Optional[Dict] = None,
        default: Any = None,
        tier: str = CacheTier.L2_REDIS
    ) -> Any:
        """Get cache value with tier fallback."""
        try:
            key = self.generate_key(category, identifier, params)

            # Try memory cache first (L1)
            if tier == CacheTier.L1_MEMORY or tier == CacheTier.L2_REDIS:
                data = self._get_memory_cache(key)
                if data is not None:
                    return self._deserialize_data(data)

            # Try Redis cache (L2)
            if tier == CacheTier.L2_REDIS:
                data = self._get_redis_cache(key)
                if data is not None:
                    # Promote to memory cache if found in Redis
                    self._set_memory_cache(key, data, 300)  # 5 min in memory
                    return self._deserialize_data(data)

            return default

        except Exception as e:
            logger.error("Cache get error for %s:%s - %s", category, identifier, e)
            return default

    def delete(
        self,
        category: str,
        identifier: str,
        params: Optional[Dict] = None
    ) -> bool:
        """Delete cache value from all tiers."""
        try:
            key = self.generate_key(category, identifier, params)

            # Delete from memory cache
            cache.delete(key)

            # Delete from Redis
            self.redis_client.delete(key)

            return True

        except Exception as e:
            logger.error("Cache delete error for %s:%s - %s", category, identifier, e)
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete cache entries matching pattern."""
        try:
            deleted_count = 0

            # Memory cache pattern deletion (limited support)
            # Django cache doesn't support pattern deletion well

            # Redis pattern deletion
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)

            return deleted_count

        except Exception as e:
            logger.error("Cache pattern delete error for %s - %s", pattern, e)
            return 0

    def invalidate_category(self, category: str) -> int:
        """Invalidate all cache entries in a category."""
        pattern = f"{category}:*"
        return self.delete_pattern(pattern)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health metrics."""
        try:
            redis_info = self.redis_client.info()

            return {
                'redis_connected': True,
                'redis_memory_used': redis_info.get('used_memory_human', 'N/A'),
                'redis_memory_peak': redis_info.get('used_memory_peak_human', 'N/A'),
                'redis_total_commands': redis_info.get('total_commands_processed', 0),
                'redis_keyspace_hits': redis_info.get('keyspace_hits', 0),
                'redis_keyspace_misses': redis_info.get('keyspace_misses', 0),
                'cache_hit_ratio': self._calculate_hit_ratio(redis_info),
                'last_checked': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to get cache stats: %s", e)
            return {
                'redis_connected': False,
                'error': str(e),
                'last_checked': datetime.now().isoformat()
            }

    def warm_cache(self, category: str, identifiers: List[str]) -> Dict[str, bool]:
        """Warm cache with multiple entries."""
        results = {}

        for identifier in identifiers:
            try:
                # This would typically call the actual data fetching function
                # For now, we'll just mark as attempted
                results[identifier] = True
            except Exception as e:
                logger.error("Cache warming failed for %s:%s - %s", category, identifier, e)
                results[identifier] = False

        return results

    def _serialize_data(self, data: Any) -> str:
        """Serialize data for caching."""
        if isinstance(data, str):
            return data
        return json.dumps(data, cls=DjangoJSONEncoder)

    def _deserialize_data(self, data: str) -> Any:
        """Deserialize data from cache."""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data

    def _set_memory_cache(self, key: str, data: str, ttl: int) -> bool:
        """Set data in Django memory cache."""
        try:
            cache.set(key, data, ttl)
            return True
        except Exception as e:
            logger.error("Memory cache set error: %s", e)
            return False

    def _get_memory_cache(self, key: str) -> Optional[str]:
        """Get data from Django memory cache."""
        try:
            return cache.get(key)
        except Exception as e:
            logger.error("Memory cache get error: %s", e)
            return None

    def _set_redis_cache(self, key: str, data: str, ttl: int) -> bool:
        """Set data in Redis cache."""
        try:
            self.redis_client.setex(key, ttl, data)
            return True
        except Exception as e:
            logger.error("Redis cache set error: %s", e)
            return False

    def _get_redis_cache(self, key: str) -> Optional[str]:
        """Get data from Redis cache."""
        try:
            result = self.redis_client.get(key)
            return result.decode('utf-8') if result else None
        except Exception as e:
            logger.error("Redis cache get error: %s", e)
            return None

    def _calculate_hit_ratio(self, redis_info: Dict) -> float:
        """Calculate cache hit ratio."""
        hits = redis_info.get('keyspace_hits', 0)
        misses = redis_info.get('keyspace_misses', 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0


class CacheDecorator:
    """Decorator for automatic caching of function results."""

    def __init__(
        self,
        category: str,
        ttl: Optional[int] = None,
        key_func: Optional[callable] = None,
        tier: str = CacheTier.L2_REDIS
    ):
        """Initialize cache decorator."""
        self.category = category
        self.ttl = ttl
        self.key_func = key_func
        self.tier = tier
        self.cache_manager = AdvancedCacheManager()

    def __call__(self, func):
        """Decorator implementation."""
        def wrapper(*args, **kwargs):
            # Generate cache key
            if self.key_func:
                cache_key = self.key_func(*args, **kwargs)
            else:
                # Default key generation
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try to get from cache
            cached_result = self.cache_manager.get(
                self.category,
                cache_key,
                tier=self.tier
            )

            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            self.cache_manager.set(
                self.category,
                cache_key,
                result,
                ttl=self.ttl,
                tier=self.tier
            )

            return result

        return wrapper


# Global cache manager instance
cache_manager = AdvancedCacheManager()


# Convenience functions
def cache_student_data(student_id: str, data: Any, ttl: Optional[int] = None) -> bool:
    """Cache student data with optimized settings."""
    return cache_manager.set(CacheCategory.STUDENT_DATA, student_id, data, ttl=ttl)


def get_student_data(student_id: str, default: Any = None) -> Any:
    """Get cached student data."""
    return cache_manager.get(CacheCategory.STUDENT_DATA, student_id, default=default)


def cache_analytics(key: str, data: Any, params: Optional[Dict] = None) -> bool:
    """Cache analytics data with short TTL."""
    return cache_manager.set(CacheCategory.ANALYTICS, key, data, params=params)


def get_analytics(key: str, params: Optional[Dict] = None, default: Any = None) -> Any:
    """Get cached analytics data."""
    return cache_manager.get(CacheCategory.ANALYTICS, key, params=params, default=default)


def invalidate_student_cache(student_id: str) -> bool:
    """Invalidate all cache entries for a student."""
    patterns = [
        f"{CacheCategory.STUDENT_DATA}:{student_id}*",
        f"{CacheCategory.ACADEMIC_RECORDS}:{student_id}*",
        f"{CacheCategory.FINANCIAL_DATA}:{student_id}*",
        f"{CacheCategory.ANALYTICS}:*{student_id}*"
    ]

    total_deleted = 0
    for pattern in patterns:
        total_deleted += cache_manager.delete_pattern(pattern)

    return total_deleted > 0


def cache_search_results(query: str, filters: Dict, results: Any) -> bool:
    """Cache search results with query and filter parameters."""
    return cache_manager.set(
        CacheCategory.SEARCH_RESULTS,
        query,
        results,
        params=filters
    )


def get_search_results(query: str, filters: Dict, default: Any = None) -> Any:
    """Get cached search results."""
    return cache_manager.get(
        CacheCategory.SEARCH_RESULTS,
        query,
        params=filters,
        default=default
    )


# Export public interface
__all__ = [
    'AdvancedCacheManager',
    'CacheDecorator',
    'CacheTier',
    'CacheCategory',
    'cache_manager',
    'cache_student_data',
    'get_student_data',
    'cache_analytics',
    'get_analytics',
    'invalidate_student_cache',
    'cache_search_results',
    'get_search_results',
]