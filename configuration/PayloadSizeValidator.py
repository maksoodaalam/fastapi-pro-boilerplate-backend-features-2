from starlette.middleware.base import BaseHTTPMiddleware

class OutboundHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Trust response type don't read mime type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Do not embed api anywhere
        response.headers["X-Frame-Options"] = "DENY"

        # Do not cache this response
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        # HSTS Header
        # block who is trying to access without https for 5 minutes(300)
        hsts_value = "max-age=60; includeSubDomains"
        response.headers["Strict-Transport-Security"] = hsts_value

        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
        )

        return response

