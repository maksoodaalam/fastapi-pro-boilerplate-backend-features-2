from starlette.requests import Request


async def outbound_header_middleware(request: Request, call_next):
    response = await call_next(request)

    # Trust response type don't read mime type
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Do not embed api anywhere
    response.headers["X-Frame-Options"] = "DENY"

    # Do not cache this response
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    # HSTS Header
    response.headers["Strict-Transport-Security"] = (
        "max-age=60; includeSubDomains"
    )

    # h11 rejects header values with trailing SP/HTAB (RFC-style field-content).
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )

    return response
