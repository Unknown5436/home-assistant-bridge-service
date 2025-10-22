import time
from typing import Any, Dict, Optional, Union
from cachetools import TTLCache
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class CacheManager:
    """In-memory cache manager with TTL support."""

    def __init__(self, default_ttl: int = None):
        self.default_ttl = default_ttl or settings.CACHE_TTL
        self.caches: Dict[str, TTLCache] = {}
        self._create_default_caches()

    def _create_default_caches(self):
        """Create default cache instances."""
        # States cache
        self.caches["states"] = TTLCache(maxsize=1000, ttl=self.default_ttl)

        # Services cache
        self.caches["services"] = TTLCache(
            maxsize=100, ttl=self.default_ttl * 2  # Services change less frequently
        )

        # Config cache
        self.caches["config"] = TTLCache(
            maxsize=10, ttl=self.default_ttl * 10  # Config changes rarely
        )

    def get(self, cache_name: str, key: str) -> Optional[Any]:
        """Get value from cache."""
        if cache_name not in self.caches:
            logger.warning("Cache not found", cache_name=cache_name)
            return None

        cache = self.caches[cache_name]
        value = cache.get(key)

        if value is not None:
            logger.debug("Cache hit", cache_name=cache_name, key=key)
        else:
            logger.debug("Cache miss", cache_name=cache_name, key=key)

        return value

    def set(
        self, cache_name: str, key: str, value: Any, ttl: Optional[int] = None
    ) -> None:
        """Set value in cache."""
        if cache_name not in self.caches:
            logger.warning("Cache not found", cache_name=cache_name)
            return

        cache = self.caches[cache_name]
        cache[key] = value

        logger.debug(
            "Cache set", cache_name=cache_name, key=key, ttl=ttl or self.default_ttl
        )

    def delete(self, cache_name: str, key: str) -> bool:
        """Delete value from cache."""
        if cache_name not in self.caches:
            return False

        cache = self.caches[cache_name]
        if key in cache:
            del cache[key]
            logger.debug("Cache deleted", cache_name=cache_name, key=key)
            return True

        return False

    def clear(self, cache_name: Optional[str] = None) -> None:
        """Clear cache or all caches."""
        if cache_name:
            if cache_name in self.caches:
                self.caches[cache_name].clear()
                logger.info("Cache cleared", cache_name=cache_name)
        else:
            for name, cache in self.caches.items():
                cache.clear()
            logger.info("All caches cleared")

    def invalidate_pattern(self, cache_name: str, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        if cache_name not in self.caches:
            return 0

        cache = self.caches[cache_name]
        keys_to_delete = [key for key in cache.keys() if pattern in str(key)]

        for key in keys_to_delete:
            del cache[key]

        logger.info(
            "Cache pattern invalidated",
            cache_name=cache_name,
            pattern=pattern,
            count=len(keys_to_delete),
        )
        return len(keys_to_delete)

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get cache statistics."""
        stats = {}

        for name, cache in self.caches.items():
            stats[name] = {
                "size": len(cache),
                "maxsize": cache.maxsize,
                "ttl": cache.ttl,
                "hit_rate": getattr(cache, "hit_rate", 0),
                "miss_rate": getattr(cache, "miss_rate", 0),
            }

        return stats

    def create_cache(self, name: str, maxsize: int = 1000, ttl: int = None) -> None:
        """Create a new cache instance."""
        if name in self.caches:
            logger.warning("Cache already exists", cache_name=name)
            return

        self.caches[name] = TTLCache(maxsize=maxsize, ttl=ttl or self.default_ttl)

        logger.info("Cache created", cache_name=name, maxsize=maxsize, ttl=ttl)


# Global cache manager instance
cache_manager = CacheManager()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_parts = []

    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        elif isinstance(arg, dict):
            # Sort dict items for consistent keys
            sorted_items = sorted(arg.items())
            key_parts.append(str(sorted_items))
        else:
            key_parts.append(str(arg))

    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")

    return ":".join(key_parts)


def cached(cache_name: str, ttl: Optional[int] = None):
    """Decorator for caching function results."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_key(func.__name__, *args, **kwargs)

            # Try to get from cache
            cached_result = cache_manager.get(cache_name, key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_name, key, result, ttl)

            return result

        return wrapper

    return decorator
