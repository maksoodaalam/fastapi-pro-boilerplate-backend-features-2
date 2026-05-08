from __future__ import annotations

import hashlib
import time
import uuid
from typing import Iterable

from fastapi import Request
from redis import Redis
from redis.commands.core import Script

from configuration.BaseResponse import base_res

# Sliding window: max N hits within window_seconds (per client, per route path).
DEFAULT_MAX_REQUESTS = 5
DEFAULT_WINDOW_SECONDS = 10

_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  return 0
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, math.ceil(window) + 1)
return 1
"""


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _stable_hash(part: str, length: int = 32) -> str:
    return hashlib.sha256(part.encode("utf-8")).hexdigest()[:length]


def rate_limit_http_middleware(
    redis_client: Redis,
    *,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    exempt_paths: Iterable[str] | None = None,
    key_prefix: str = "ratelimit:sliding:v1",
):

    lua: Script = redis_client.register_script(_SLIDING_WINDOW_LUA)
    window_f = float(window_seconds)
    exempt: frozenset[str] = frozenset(exempt_paths or ())

    def _rate_limit_key(request: Request) -> str:
        path = request.url.path or "/"
        ip = _client_ip(request)
        return f"{key_prefix}:{_stable_hash(ip)}:{_stable_hash(path)}"

    async def middleware(request: Request, call_next):
        
        if request.url.path in exempt:
            return await call_next(request)

        now = time.time()
        member = f"{now}:{uuid.uuid4().hex}"
        allowed = int(
            lua(
                keys=[_rate_limit_key(request)],
                args=[
                    str(window_f),
                    str(max_requests),
                    str(now),
                    member,
                ],
            )
        )

        if allowed == 0:
            return base_res(
                429,
                f"Rate limit exceeded: {max_requests} requests per "
                f"{int(window_f)} seconds for this route",
                {},
                False,
            )

        return await call_next(request)

    return middleware
