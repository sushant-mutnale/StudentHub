"""
Security Headers Middleware

Adds hardening HTTP response headers to every response.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Headers applied to every response.
SECURITY_HEADERS = {
    # Prevents clickjacking / UI redress attacks
    "X-Frame-Options": "DENY",
    # Prevents MIME-type sniffing
    "X-Content-Type-Options": "nosniff",
    # Controls referrer info leakage on cross-origin navigation
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Restricts browser features to reduce attack surface
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    # Content Security Policy — restrictive default; the SPA serves its own
    # API resources from the same origin. 'unsafe-inline' for styles is kept to
    # avoid breaking inline style usage; review before tightening further.
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply security headers to all responses."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request, call_next: RequestResponseEndpoint):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response
