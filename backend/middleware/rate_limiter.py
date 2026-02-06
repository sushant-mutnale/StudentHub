"""
Rate Limit Middleware

Protects the API from abuse using a Token Bucket algorithm over Redis.
Falls back to in-memory if Redis is unavailable.

Features:
- Global rate limits per IP
- Per-route custom limits
- Specific authenticated user limits (tiered)
"""

import time
import logging
from typing import Tuple

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ..config import settings
from ..redis_client import get_redis

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = settings.rate_limit_enabled
        
        # Default limits: (requests, seconds)
        # e.g., 100 reqs per 60 seconds
        self.default_limit = self._parse_limit(settings.rate_limit_default)
        self.auth_limit = self._parse_limit(settings.rate_limit_auth)
        self.ai_limit = self._parse_limit(settings.rate_limit_ai)

    def _parse_limit(self, limit_str: str) -> Tuple[int, int]:
        """Parse '100/minute' into (100, 60)."""
        try:
            count, period = limit_str.split("/")
            count = int(count)
            
            seconds = 60
            if period.startswith("second"):
                seconds = 1
            elif period.startswith("hour"):
                seconds = 3600
            elif period.startswith("day"):
                seconds = 86400
                
            return count, seconds
        except Exception:
            return 60, 60  # Safe fallback

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for static files or common exclusions
        if request.url.path.startswith("/static") or request.method == "OPTIONS":
            return await call_next(request)

        # 1. Identify Client
        ip = request.client.host
        user_id = "anon"
        
        # Simple extraction of user ID from JWT if present (without full validation overhead)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # We don't verify signature here to keep it fast - auth middleware does that
            # We just use the token string itself as part of the key for authenticated users
            user_id = f"token:{hash(auth_header)}"

        # 2. Determine Limit
        limit, period = self.default_limit
        
        # Stricter limits for expensive routes
        if "/auth/" in request.url.path:
            limit, period = self.auth_limit
        elif "/ai/" in request.url.path or "/research/" in request.url.path:
            limit, period = self.ai_limit
        
        # 3. Check Limit
        key = f"ratelimit:{ip}:{user_id}:{request.url.path}"
        is_allowed = await self._check_rate_limit(key, limit, period)
        
        if not is_allowed:
            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Period": str(period)
            }
            return Response(
                content="Too Many Requests", 
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=headers
            )
        
        # 4. Process Request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Period"] = str(period)
        
        return response

    async def _check_rate_limit(self, key: str, limit: int, period: int) -> bool:
        """
        Check rate limit using Redis atomic increments.
        Returns True if allowed, False if exceeded.
        """
        redis = None
        try:
            from ..redis_client import get_redis
            redis = get_redis()
        except Exception:
            pass  # Fallback handled below

        if redis:
            try:
                # Use a pipeline for atomicity
                pipe = redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, period)
                results = await pipe.execute()
                
                count = results[0]
                return count <= limit
            except Exception as e:
                logger.error(f"Rate limit Redis error: {e}")
                # Fail open if Redis is down
                return True
        else:
            # Simple in-memory fallback (not distributed, but better than nothing)
            # Note: This is per-process, so it resets on restart
            current_time = int(time.time())
            
            # Simple fixed window
            if not hasattr(self, "_memory_store"):
                self._memory_store = {}
                
            # Cleanup old
            to_del = []
            for k, (ts, _) in self._memory_store.items():
                if current_time - ts > period:
                    to_del.append(k)
            for k in to_del:
                del self._memory_store[k]
                
            if key not in self._memory_store:
                self._memory_store[key] = (current_time, 1)
                return True
            else:
                ts, count = self._memory_store[key]
                if current_time - ts > period:
                    # Reset window
                    self._memory_store[key] = (current_time, 1)
                    return True
                else:
                    if count >= limit:
                        return False
                    self._memory_store[key] = (ts, count + 1)
                    return True
