"""
Redis Client Manager

Singleton wrapper for Redis connection to ensure only one connection pool
is created and reused across the application.

The client is event-loop-bound (redis.asyncio pools connections to the running
loop). To remain correct in asynchronous frameworks where the running event
loop can change (multiple workers, test environments with multiple loops), the
singleton is REBUILT when the bound loop has closed or no longer matches the
current running loop.
"""

import logging
import asyncio
from typing import Optional
import redis.asyncio as redis
from .config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client wrapper (event-loop-safe singleton).
    """

    _instance: Optional[redis.Redis] = None
    _bound_loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def _current_loop(cls) -> Optional[asyncio.AbstractEventLoop]:
        """Return the currently running event loop, or None outside async context."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    @classmethod
    def get_instance(cls) -> redis.Redis:
        """Get or create a Redis client bound to the current event loop."""
        current_loop = cls._current_loop()

        # Rebuild the client if we are in an async context and the stored client
        # is bound to a different/closed/unknown loop. redis.asyncio pools
        # connections per-loop, so reusing a client across loops is unsafe.
        if cls._instance is not None and current_loop is not None:
            bound_loop = cls._bound_loop
            stale = (
                bound_loop is None
                or bound_loop.is_closed()
                or bound_loop is not current_loop
            )
            if stale:
                logger.info(
                    "Rebuilding Redis client for current event loop "
                    f"(current={current_loop!r}, bound={bound_loop!r})"
                )
                cls._instance = None
                cls._bound_loop = None

        if cls._instance is None:
            logger.info("Initializing Redis connection...")
            try:
                cls._instance = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    username=settings.redis_username,
                    password=settings.redis_password,
                    db=settings.redis_db,
                    ssl=settings.redis_ssl,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True
                )
                cls._bound_loop = cls._current_loop()
                logger.info("Redis initialized configured")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                cls._instance = None
                cls._bound_loop = None
                raise

        return cls._instance

    @classmethod
    async def close(cls):
        """Close the Redis connection."""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            cls._bound_loop = None
            logger.info("Redis connection closed")
            
    @classmethod
    async def ping(cls) -> bool:
        """Test connection to Redis."""
        try:
            client = cls.get_instance()
            return await client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    @classmethod
    async def health_check(cls) -> bool:
        """Check Redis health and reset instance on failure."""
        try:
            client = cls.get_instance()
            result = await client.ping()
            if result:
                return True
            cls._instance = None
            cls._bound_loop = None
            return False
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            cls._instance = None
            cls._bound_loop = None
            return False


# Global accessor
def get_redis() -> redis.Redis:
    return RedisClient.get_instance()


async def init_redis() -> bool:
    """Initialize and verify Redis at startup. Returns True if available."""
    try:
        client = RedisClient.get_instance()
        result = await client.ping()
        if result:
            logger.info("Redis connection verified at startup")
        return result
    except Exception as e:
        logger.warning(f"Redis unavailable at startup (will retry on use): {e}")
        RedisClient._instance = None  # Reset so it retries
        RedisClient._bound_loop = None
        return False
