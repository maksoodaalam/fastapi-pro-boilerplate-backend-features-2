from collections.abc import Iterable

from starlette.types import ASGIApp, Receive, Scope, Send

from configuration.BaseResponse import base_res

BLOCKED_HEADERS = frozenset(
    {"x-forwarded-for", "x-real-ip", "forwarded"}
)

# Incoming header names besides ALWAYS_ALLOWED_HEADERS must appear in EXTRA_ALLOWED_HEADERS.
ALWAYS_ALLOWED_HEADERS = frozenset({
    "host",
    "connection",
    "content-length",
    "content-type",
    "accept",
    "accept-encoding",
    "accept-language",
    "user-agent",
    "cookie",
    "authorization",
    "origin",
    "referer",
    "pragma",
    "cache-control",
    "upgrade-insecure-requests",
    "sec-fetch-site",
    "sec-fetch-mode",
    "sec-fetch-dest",
    "sec-fetch-user",
    "sec-ch-ua",
    "sec-ch-ua-mobile",
    "sec-ch-ua-platform",
    "prefer",
})

# Extend allowlist beyond ALWAYS_ALLOWED_HEADERS (app / client custom headers).
EXTRA_ALLOWED_HEADERS = frozenset(
    {
        "x-requested-with",
        "x-csrf-token",
        "accept-datetime",
        "x-api-key",
        "idempotency-key",
        "x-custom-header",
    }
)

# Presence required (lowercase names). OPTIONS stays exempt via exempt_methods_for_allow_required.
REQUIRED_HEADERS: frozenset[str] = frozenset({"content-type", "x-api-key"})

REQUIRED_HEADERS_METHODS: frozenset[str] | None = frozenset(
    {"POST", "PUT", "PATCH", "DELETE"}
)


ALLOWED_CONTENT_TYPE_MEDIA_TYPES: frozenset[str] = frozenset({"application/json"})


def _primary_media_type(content_type_raw: str) -> str:
    return content_type_raw.split(";", maxsplit=1)[0].strip().lower()


def _header_first_values(scope: Scope) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in scope.get("headers") or ():
        if isinstance(key, bytes):
            k = key.decode("latin1").strip().lower()
        else:
            k = str(key).strip().lower()
        if k in out:
            continue
        if isinstance(value, bytes):
            v = value.decode("latin1").strip()
        else:
            v = str(value).strip()
        out[k] = v
    return out


def _header_names(scope: Scope) -> set[str]:
    raw = scope.get("headers") or ()
    names: set[str] = set()
    for key, _value in raw:
        if isinstance(key, bytes):
            names.add(key.decode("latin1").strip().lower())
        else:
            names.add(str(key).strip().lower())
    return names


class InboundHeaderPolicyMiddleware:
    """Blocked / required / allowed policy for inbound request headers (not CORS)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        blocked: frozenset[str] | set[str],
        extra_allowed: frozenset[str] | set[str],
        required: frozenset[str] | set[str],
        required_methods: frozenset[str] | set[str] | None,
        exempt_methods_for_allow_required: Iterable[str],
    ) -> None:
        self.app = app
        self.blocked = frozenset(h.lower().strip() for h in blocked)
        self.required = frozenset(h.lower().strip() for h in required)
        self.required_methods = (
            frozenset(m.upper() for m in required_methods)
            if required_methods is not None
            else None
        )
        self.allowlist_allow = ALWAYS_ALLOWED_HEADERS | frozenset(
            h.lower().strip() for h in extra_allowed
        )
        self.exempt_allow_required = frozenset(
            m.upper() for m in exempt_methods_for_allow_required
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method") or ""
        incoming = _header_names(scope)

        banned_present = incoming & self.blocked
        if banned_present:
            resp = base_res(
                403,
                "Blocked header present",
                {"headers": sorted(banned_present)},
                False,
            )
            await resp(scope, receive, send)
            return

        enforce_allow_required = method not in self.exempt_allow_required

        if enforce_allow_required:
            meth = method.upper()
            applies_required = (
                self.required_methods is None or meth in self.required_methods
            )
            req_set = self.required if applies_required else frozenset()
            missing = sorted(req_set - incoming)
            if missing:
                resp = base_res(
                    400,
                    "Missing required headers",
                    {"missing": missing},
                    False,
                )
                await resp(scope, receive, send)
                return

            hdr_values = _header_first_values(scope)
            ct_raw = hdr_values.get("content-type")
            media = ""
            if ct_raw:
                media = _primary_media_type(ct_raw)
                if media not in ALLOWED_CONTENT_TYPE_MEDIA_TYPES:
                    resp = base_res(
                        415,
                        "Content-Type must be application/json",
                        {"content_type": ct_raw, "media_type": media},
                        False,
                    )
                    await resp(scope, receive, send)
                    return

            # disallowed = sorted(incoming - self.allowlist_allow)
            # if disallowed:
            #     resp = base_res(400,"Header not allowed",{"headers": sorted(disallowed)},False )
            #     await resp(scope, receive, send)
            #     return

        await self.app(scope, receive, send)


def inbound_header_policy_middleware(
    app: ASGIApp,
    /,
    *,
    blocked: frozenset[str] | set[str],
    extra_allowed: frozenset[str] | set[str],
    required: frozenset[str] | set[str],
    required_methods: frozenset[str] | set[str] | None,
    exempt_methods_for_allow_required: Iterable[str],
) -> ASGIApp:
    return InboundHeaderPolicyMiddleware(
        app,
        blocked=blocked,
        extra_allowed=extra_allowed,
        required=required,
        required_methods=required_methods,
        exempt_methods_for_allow_required=exempt_methods_for_allow_required,
    )
