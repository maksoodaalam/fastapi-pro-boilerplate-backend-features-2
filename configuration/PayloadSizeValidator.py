from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from configuration.BaseResponse import base_res


MAX_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_TYPES = [
    # text/*
    "text/plain",
    "text/html",
    "text/css",
    "text/csv",
    "text/markdown",
    "text/xml",
    # JSON types
    "application/json",
    "application/ld+json",
    "application/vnd.api+json",
    "application/problem+json",
    "application/json-patch+json",
    "application/merge-patch+json",
    # XML types
    "application/xml",
    "application/rss+xml",
    "application/atom+xml",
    # Form / web
    "application/x-www-form-urlencoded",
    # Script / query
    "application/javascript",
    "application/graphql",
    # Config / data formats
    "application/yaml",
    "application/x-yaml",
    "application/toml",
    # Streaming text formats
    "application/x-ndjson",
]


def _matches_limited_payload_content_type(header_value: str) -> bool:
    v = header_value.lower()
    return any(marker in v for marker in ALLOWED_TYPES)


async def _discard_entire_request_body(recv: Receive) -> None:
    while True:
        message = await recv()
        mt = message["type"]
        if mt == "http.disconnect":
            return
        if mt == "http.request" and not message.get("more_body"):
            return


async def _drain_remainder(recv: Receive, more_body: bool) -> None:
    while more_body:
        message = await recv()
        mt = message["type"]
        if mt == "http.disconnect":
            return
        if mt != "http.request":
            continue
        more_body = message.get("more_body", False)


async def _read_body_under_cap(
    recv: Receive, limit: int
) -> tuple[bytes | None, bool]:
    """Return ``(body, too_large)``. ``too_large`` means body exceeded ``limit`` (drained)."""
    buf = bytearray()
    while True:
        message = await recv()
        mt = message["type"]
        if mt == "http.disconnect":
            return (bytes(buf), False) if buf else (b"", False)
        if mt != "http.request":
            continue
        chunk = message.get("body") or b""
        buf.extend(chunk)
        more_body = message.get("more_body", False)
        if len(buf) > limit:
            await _drain_remainder(recv, more_body)
            return None, True
        if not more_body:
            return bytes(buf), False


def _replay_receive_with_body(full_body: bytes) -> Receive:
    sent = False

    async def replay() -> dict:
        nonlocal sent
        if not sent:
            sent = True
            return {
                "type": "http.request",
                "body": bytes(full_body),
                "more_body": False,
            }
        return {"type": "http.disconnect"}

    return replay


def _too_large_response():
    return base_res(
        413,
        "Request body exceeds maximum allowed size",
        {"max_bytes": MAX_SIZE},
        False,
    )


class LimitStreamingMiddleware:
    """Enforce ``MAX_SIZE`` for allowed text/JSON-style ``Content-Type`` bodies.

    Endpoints that never read the request body would otherwise skip ASGI ``receive()`` calls,
    so this middleware fully reads (up to the cap), rejects oversize payloads, then replays
    the buffered body to the inner app.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_type_raw = Headers(scope=scope).get("content-type", "")
        if not _matches_limited_payload_content_type(content_type_raw):
            await self.app(scope, receive, send)
            return

        hdrs = Headers(scope=scope)
        cl_raw = hdrs.get("content-length")
        if cl_raw is not None:
            stripped = cl_raw.strip()
            if stripped.isdigit():
                cl_n = int(stripped)
                if cl_n > MAX_SIZE:
                    resp = _too_large_response()
                    await resp(scope, receive, send)
                    await _discard_entire_request_body(receive)
                    return

        body, too_large = await _read_body_under_cap(receive, MAX_SIZE)
        if too_large:
            resp = _too_large_response()
            await resp(scope, receive, send)
            return

        replay = _replay_receive_with_body(body if body is not None else b"")
        await self.app(scope, replay, send)
