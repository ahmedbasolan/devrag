"""
Cache Manager

Redis-based caching layer with TTL support and cache invalidation strategies.
"""

import json
import hashlib
from functools import wraps
from typing import Any, Optional, Callable
import time


class CacheManager:
    """Distributed caching with Redis backend."""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes
        self.stats = {'hits': 0, 'misses': 0}

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        if not self.redis:
            return None
        data = self.redis.get(key)
        if data:
            self.stats['hits'] += 1
            return json.loads(data)
        self.stats['misses'] += 1
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        """Store value in cache with optional TTL."""
        if not self.redis:
            return
        ttl = ttl or self.default_ttl
        self.redis.setex(key, ttl, json.dumps(value, default=str))

    def delete(self, key: str):
        """Remove a specific key from cache."""
        if self.redis:
            self.redis.delete(key)

    def clear_pattern(self, pattern: str):
        """Clear all keys matching a pattern."""
        if not self.redis:
            return
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)

    def get_or_set(self, key: str, factory: Callable, ttl: int = None) -> Any:
        """Get from cache, or compute and store if missing."""
        value = self.get(key)
        if value is None:
            value = factory()
            self.set(key, value, ttl)
        return value

    def invalidate_user(self, user_id: int):
        """Clear all cached data for a specific user."""
        self.clear_pattern(f'user:{user_id}:*')
        self.clear_pattern(f'orders:{user_id}:*')

    def invalidate_product(self, product_id: int):
        """Clear cached data when product changes."""
        self.delete(f'product:{product_id}')
        self.clear_pattern('products:*')
        self.clear_pattern('search:*')

    def get_stats(self):
        """Return cache performance statistics."""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total if total > 0 else 0
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': f'{hit_rate:.1%}'
        }


def cached(ttl=300, key_prefix=''):
    """Decorator to cache function results."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            cache_key = f'{key_prefix}{f.__name__}:{hashlib.md5(str(args + tuple(sorted(kwargs.items()))).encode()).hexdigest()}'
            cache = CacheManager()
            result = cache.get(cache_key)
            if result is not None:
                return result
            result = f(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


class CacheWarmer:
    """Pre-populate cache with frequently accessed data."""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    def warm_products(self, product_ids: list):
        """Pre-cache product details."""
        for pid in product_ids:
            key = f'product:{pid}'
            # In real code, fetch from DB and cache
            print(f'Warming cache for product {pid}')

    def warm_user_sessions(self, user_ids: list):
        """Pre-cache user session data."""
        for uid in user_ids:
            key = f'user:{uid}:session'
            print(f'Warming cache for user {uid}')

    def warm_category_lists(self, categories: list):
        """Pre-cache product category listings."""
        for cat in categories:
            key = f'products:category:{cat}'
            print(f'Warming cache for category {cat}')


# Cache key patterns used in the application
CACHE_KEYS = {
    'product_detail': 'product:{product_id}',
    'product_list': 'products:page:{page}:category:{category}',
    'user_session': 'user:{user_id}:session',
    'user_orders': 'orders:{user_id}:list',
    'search_results': 'search:{query}:page:{page}',
    'admin_stats': 'admin:dashboard:stats',
    'category_products': 'products:category:{category}',
}
