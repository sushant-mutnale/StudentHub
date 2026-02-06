"""
Cache Service

Unified caching layer that supports both in-memory and Redis backends.
Auto-detects Redis availability via redis_client.
"""

import hashlib
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from functools import wraps

from ..redis_client import get_redis

logger = logging.getLogger(__name__)


class CacheService:
    """
    Hybrid cache service (Redis with In-Memory fallback).
    """
    
    def __init__(self):
        self._memory_cache: dict = {}
        self._memory_expiry: dict = {}
        self._use_redis = True
    
    async def _get_redis_conn(self):
        """Get Redis connection if available."""
        if not self._use_redis:
            return None
            
        try:
            return get_redis()
        except Exception:
            self._use_redis = False
            logger.warning("Redis unavailable, falling back to in-memory cache")
            return None

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments."""
        # Clean kwargs to remove objects that can't be serialized effectively
        clean_kwargs = {k: v for k, v in kwargs.items() if not k.startswith('_')}
        
        data = json.dumps({"args": args, "kwargs": clean_kwargs}, sort_keys=True, default=str)
        hash_val = hashlib.md5(data.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_val}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        # Try Redis first
        redis_conn = await self._get_redis_conn()
        if redis_conn:
            try:
                val = await redis_conn.get(key)
                if val:
                    return json.loads(val)
            except Exception as e:
                logger.error(f"Redis get failed: {e}")
        
        # Fallback to memory
        if key not in self._memory_cache:
            return None
        
        if datetime.utcnow() > self._memory_expiry.get(key, datetime.min):
            self.delete_local(key)
            return None
        
        return self._memory_cache[key]
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set item in cache."""
        # Redis
        redis_conn = await self._get_redis_conn()
        if redis_conn:
            try:
                # Serialize complex objects if needed
                val_json = json.dumps(value, default=str)
                await redis_conn.set(key, val_json, ex=ttl_seconds)
            except Exception as e:
                logger.error(f"Redis set failed: {e}")
        
        # Always update local memory too (L1 cache strategy could go here, 
        # but for now we just keep it as backup or for hybrid heavy read)
        self._memory_cache[key] = value
        self._memory_expiry[key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    async def delete(self, key: str) -> None:
        """Remove item from cache."""
        redis_conn = await self._get_redis_conn()
        if redis_conn:
            try:
                await redis_conn.delete(key)
            except Exception as e:
                logger.error(f"Redis delete failed: {e}")
        
        self.delete_local(key)
        
    def delete_local(self, key: str) -> None:
        """Remove from local memory only."""
        self._memory_cache.pop(key, None)
        self._memory_expiry.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cached items."""
        redis_conn = await self._get_redis_conn()
        if redis_conn:
            try:
                await redis_conn.flushdb()
            except Exception as e:
                logger.error(f"Redis flush failed: {e}")
                
        self._memory_cache.clear()
        self._memory_expiry.clear()


# Global cache instance
cache = CacheService()


# Cache key prefixes
class CacheKeys:
    JOBS_LIST = "jobs:list"
    POSTS_LIST = "posts:list"
    USER_PROFILE = "user:profile"
    RECOMMENDATIONS = "recommendations"
    USERNAME_CHECK = "auth:username"
    EMAIL_CHECK = "auth:email"
    PIPELINE_BOARD = "pipeline:board"


# Default TTL values (in seconds)
class CacheTTL:
    SHORT = 60          # 1 minute
    MEDIUM = 300        # 5 minutes
    LONG = 900          # 15 minutes
    HOUR = 3600         # 1 hour
    USERNAME_CHECK = 30 # 30 seconds


def cache_response(prefix: str, ttl_seconds: int = 300):
    """
    Decorator to cache async function responses.
    
    Supports both Pydantic models (via .dict()/.model_dump()) and standard dicts.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip caching if configured to skip (useful for testing)
            
            # Generate key
            # Filter out 'self' or 'request' args which usually cause serialization issues
            cache_args = [a for a in args if not hasattr(a, 'headers')] 
            key = cache._make_key(prefix, *cache_args, **kwargs)
            
            # Try get
            cached = await cache.get(key)
            if cached is not None:
                return cached
            
            # Execute
            result = await func(*args, **kwargs)
            
            # Prepare for caching
            to_cache = result
            if hasattr(result, "model_dump"):
                to_cache = result.model_dump()
            elif hasattr(result, "dict"):
                to_cache = result.dict()
                
            # Set
            await cache.set(key, to_cache, ttl_seconds)
            
            return result
        return wrapper
    return decorator
