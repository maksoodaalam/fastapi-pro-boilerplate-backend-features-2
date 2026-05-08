from __future__ import annotations

import time
import uuid
from typing import Iterable

from fastapi import Request
from redis import Redis
from redis.commands.core import Script

from configuration.BaseResponse import base_res

_DEFAULT_GLOBAL_MAX_REQUESTS = 5000
_DEFAULT_WINDOW_SECONDS = 60

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


def global_overload_http_middleware(
    redis_client: Redis,
    *,
    max_requests: int = _DEFAULT_GLOBAL_MAX_REQUESTS,
    window_seconds: int = _DEFAULT_WINDOW_SECONDS,
    exempt_paths: Iterable[str] | None = None,
    redis_key: str = "overload:global:sliding:v1",
    message: str = "System is down",
    status_code: int = 503,
):
    lua: Script = redis_client.register_script(_SLIDING_WINDOW_LUA)
    window_f = float(window_seconds)
    exempt: frozenset[str] = frozenset(exempt_paths or ())

    async def middleware(request: Request, call_next):
        if request.url.path in exempt:
            return await call_next(request)

        now = time.time()
        member = f"{now}:{uuid.uuid4().hex}"
        allowed = int(
            lua(
                keys=[redis_key],
                args=[
                    str(window_f),
                    str(max_requests),
                    str(now),
                    member,
                ],
            )
        )

        if allowed == 0:
            return base_res(status_code, message, {}, False)

        return await call_next(request)

    return middleware
