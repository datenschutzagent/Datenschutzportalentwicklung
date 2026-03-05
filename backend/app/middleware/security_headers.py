from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds HTTP security headers to every response.
    Addresses OWASP A05:2021 – Security Misconfiguration.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing (CWE-16)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking (CWE-693)
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection in older browsers (defence-in-depth)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Restrict referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disable caching for API responses containing sensitive data
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"

        # Content-Security-Policy for the API (no HTML served directly)
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        return response
