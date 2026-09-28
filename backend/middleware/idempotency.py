"""
Idempotency Middleware

Ensures that identical requests (retries) do not result in duplicate side effects.
Uses first-write-wins semantics: the first request with a given key is processed,
and all subsequent requests with the same key receive the same response.

Key: idempotency:<user_hash>:<key>
Value: {status_code, headers, body, media_type}
TTL: 24 hours
"""

import json
import logging
import hashlib

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from starlette.concurrency import iterate_in_threadpool

from ..redis_client import get_redis

logger = logging.getLogger(__name__)

# TTL for idempotency keys (24 hours)
IDEMPOTENCY_TTL_SECONDS = 86400
# Max wait for an in-flight request to complete (10 seconds)
INFLIGHT_WAIT_SECONDS = 10
INFLIGHT_POLL_INTERVAL = 0.1


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    First-write-wins idempotency middleware.

    Protocol:
    1. Check Redis for existing response under this key.
    2. If found → return it (idempotent replay).
    3. If not found → SETNX a "processing" marker (10s TTL).
       a. SETNX succeeds → we own the key → process request, store result.
       b. SETNX fails → another request is processing → poll until result appears
          or timeout (return 409 Conflict).
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in ["POST", "PUT", "PATCH"]:
            return await call_next(request)

        key = request.headers.get("X-Idempotency-Key")
        if not key:
            return await call_next(request)

        # Hash the bearer token for a stable per-user key (not the raw token)
        user_id = "anon"
        auth_header = request.headers.get("Authorization")
        if auth_header:
            user_id = hashlib.sha256(auth_header.encode("utf-8")).hexdigest()

        cache_key = f"idempotency:{user_id}:{key}"

        # --- Phase 1: Check if response already stored ---
        redis = None
        try:
            redis = get_redis()
        except Exception:
            pass

        if redis:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    # Check if this is a processing marker or a completed response
                    if "body" in data:
                        logger.info(f"Idempotency replay: key={key}")
                        return Response(
                            content=data["body"],
                            status_code=data["status_code"],
                            headers=data["headers"],
                            media_type=data["media_type"]
                        )
                    # "processing" marker — another request is handling this key
                    return await self._wait_for_inflight(redis, cache_key, key)
            except Exception as e:
                logger.warning(f"Idempotency Redis read failed, processing normally: {e}")

        # --- Phase 2: Try to claim the key (SETNX) ---
        if redis:
            try:
                # Set "processing" marker with short TTL (in-flight window)
                claimed = await redis.set(
                    cache_key,
                    json.dumps({"status": "processing"}),
                    nx=True,
                    ex=INFLIGHT_WAIT_SECONDS
                )
                if not claimed:
                    # Another request claimed it — wait for their result
                    return await self._wait_for_inflight(redis, cache_key, key)
            except Exception as e:
                logger.warning(f"Idempotency SETNX failed, processing normally: {e}")

        # --- Phase 3: Process the request (we own the key or Redis is down) ---
        response = await call_next(request)

        # --- Phase 4: Store the result (first-write-wins) ---
        if redis and 200 <= response.status_code < 300:
            try:
                # Consume the body iterator
                response_body = [section async for section in response.body_iterator]
                response.body_iterator = iterate_in_threadpool(iter(response_body))

                body_content = b"".join(response_body).decode()
                headers = dict(response.headers)

                stored_data = {
                    "body": body_content,
                    "status_code": response.status_code,
                    "headers": headers,
                    "media_type": response.media_type
                }

                # Store the result — overwrite the processing marker.
                # We own this key (claimed via SETNX in Phase 2), so overwriting
                # our own marker is safe. Using plain SET (not SETNX) because
                # the key already exists with the processing marker.
                await redis.set(
                    cache_key,
                    json.dumps(stored_data),
                    ex=IDEMPOTENCY_TTL_SECONDS
                )
            except Exception as e:
                logger.warning(f"Idempotency store failed: {e}")

        return response

    async def _wait_for_inflight(self, redis, cache_key: str, key: str) -> Response:
        """Poll Redis until the in-flight request completes or timeout."""
        import asyncio
        for _ in range(int(INFLIGHT_WAIT_SECONDS / INFLIGHT_POLL_INTERVAL)):
            await asyncio.sleep(INFLIGHT_POLL_INTERVAL)
            try:
                cached = await redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    if "body" in data:
                        logger.info(f"Idempotency replay (waited): key={key}")
                        return Response(
                            content=data["body"],
                            status_code=data["status_code"],
                            headers=data["headers"],
                            media_type=data["media_type"]
                        )
            except Exception:
                break

        # Timed out waiting for in-flight — return 409
        return Response(
            content=json.dumps({"detail": "Request is being processed. Please retry."}),
            status_code=409,
            media_type="application/json"
        )
