from collections.abc import Sequence

from starlette. types import ASGIApp, Receive, Scope, Send


from configuration.BaseResponse import base_res


def normalize_allowed_http_methods(allowed_methods: Sequence[str]) -> tuple[frozenset[str], str]:
    frozen = frozenset(m.upper() for m in allowed_methods)
    return frozen, ", ".join(sorted(frozen))


def is_http_method_allowed(method: str, allowed: frozenset[str]) -> bool:
    return method in allowed


def http_method_not_allowed_response(allow_header: str):
    return base_res(405, "Method Not Allowed", {}, False)



class HttpMethodAllowlistMiddleware:
    """Reject HTTP methods not in ``allowed_methods`` with 405 (before routing)."""

    def __init__(self, app: ASGIApp, allowed_methods: Sequence[str]) -> None:
        self.app = app
        self._allowed, self._allow_header = normalize_allowed_http_methods(
            allowed_methods
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "")
        if not is_http_method_allowed(method, self._allowed):
            resp = http_method_not_allowed_response(self._allow_header)
            await resp(scope, receive, send)
            return
        await self.app(scope, receive, send)
