"""
Redis Client Manager

Singleton wrapper for Redis connection to ensure only one connection pool
is created and reused across the application.
"""

import logging
from typing import Optional
import redis.asyncio as redis
from .config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client wrapper.
    """
    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_instance(cls) -> redis.Redis:
        """Get or create the Redis client instance."""
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
                logger.info("Redis initialized configured")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                raise

        return cls._instance

    @classmethod
    async def close(cls):
        """Close the Redis connection."""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
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
            if cls._instance is not None:
                cls._instance = None
            return False
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            if cls._instance is not None:
                cls._instance = None
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
        return False
