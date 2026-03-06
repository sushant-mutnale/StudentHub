"""
Correlation ID Middleware

Adds a unique correlation ID to every request for end-to-end tracing.
Propagates the ID to logs and downstream events.

Header: X-Correlation-ID
"""

import uuid
import logging
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Context variable to store correlation ID for access in other modules (like loggers)
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default=None)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check for existing header (e.g., from frontend or upstream service)
        correlation_id = request.headers.get("X-Correlation-ID")
        
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            
        # Set context var for this request
        token = correlation_id_ctx.set(correlation_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add header to response so client can trace back
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
        finally:
            # Reset context
            correlation_id_ctx.reset(token)


def get_correlation_id() -> str:
    """Get the current correlation ID."""
    return correlation_id_ctx.get() or "unknown"
