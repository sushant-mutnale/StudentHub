"""
Idempotency Middleware

Ensures that identical requests (retries) do not result in duplicate side effects.
Uses an idempotency key header (X-Idempotency-Key) to cache responses.

Key: idempotency:<user_id>:<key>
Value: {status_code, headers, body}
"""

import json
import logging
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp, Message
from starlette.concurrency import iterate_in_threadpool

from ..redis_client import get_redis

logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only idempotent methods need checking, but POST/PUT/PATCH are the main targets
        if request.method not in ["POST", "PUT", "PATCH"]:
            return await call_next(request)
            
        key = request.headers.get("X-Idempotency-Key")
        if not key:
            return await call_next(request)
            
        user_id = "anon"
        auth_header = request.headers.get("Authorization")
        if auth_header:
            user_id = str(hash(auth_header))
            
        cache_key = f"idempotency:{user_id}:{key}"
        
        # Check cache
        redis = None
        try:
            redis = get_redis()
        except:
            pass # Fallback to no idempotency if Redis down
        
        if redis:
            cached = await redis.get(cache_key)
            if cached:
                logger.info(f"Idempotency hit: {key}")
                data = json.loads(cached)
                return Response(
                    content=data["body"],
                    status_code=data["status_code"],
                    headers=data["headers"],
                    media_type=data["media_type"]
                )
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses
        if redis and 200 <= response.status_code < 300:
            response_body = [section async for section in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body))
            
            body_content = b"".join(response_body).decode()
            
            # Simple header serialization (convert to dict)
            headers = dict(response.headers)
            
            data = {
                "body": body_content,
                "status_code": response.status_code,
                "headers": headers,
                "media_type": response.media_type
            }
            
            # Expire after 24 hours
            await redis.set(cache_key, json.dumps(data), ex=86400)
            
        return response
