"""
Redis client utilities: typed configuration, connection pool, and a shared client factory.

**Local Redis, no env file:** `RedisConnectionConfig()` and `get_redis_client()` connect to the
same defaults as a stock `redis-server` on your machine: `127.0.0.1:6379`, database `0`, no
password. Override any field via `RedisConnectionConfig(host=..., ...)` when you deploy.
"""

from typing import Optional
from pydantic import BaseModel

import redis
from redis.connection import ConnectionPool
from redis.exceptions import RedisError

from configuration.config import global_settings


# Matches a typical local `redis-server` install.
_DEFAULT_REDIS_HOST = global_settings.redis_host
_DEFAULT_REDIS_PORT = global_settings.redis_port
_DEFAULT_REDIS_DB = global_settings.redis_db


class RedisConnectionConfig(BaseModel):
    """
    Immutable connection settings for redis-py.
    Defaults suit localhost Redis; pass explicit kwargs for staging/production.
    """

    host: str = _DEFAULT_REDIS_HOST
    port: int = _DEFAULT_REDIS_PORT
    db: int = _DEFAULT_REDIS_DB
    username: Optional[str] = global_settings.redis_user
    password: Optional[str] = global_settings.redis_password

    # When set, used with ConnectionPool.from_url() instead of host/port/db/ssl below.
    # url: Optional[str] = None
    url: Optional[str] = global_settings.redis_url

    # ssl: bool = False
    ssl: bool = global_settings.redis_ssl

    # Upper bound on connections in the pool (per process).
    max_connections: int = global_settings.redis_max_connections

    # Max time to wait for a response on the socket; None = no socket read timeout.
    # socket_timeout: Optional[float] = None
    socket_timeout: Optional[float] = global_settings.redis_socket_timeout

    # Max time to establish the TCP connection.
    # socket_connect_timeout: float = 5.0
    socket_connect_timeout: float = global_settings.redis_socket_connect_timeout

    # Seconds between health checks on idle connections; 0 disables (redis-py 4+).
    # health_check_interval: int = 30
    health_check_interval: int = global_settings.redis_health_check_interval

    # If True, string payloads come back as str instead of bytes.
    # decode_responses: bool = True
    decode_responses: bool = global_settings.redis_decode_responses

    model_config = {"frozen": True}


def build_redis_pool(config: RedisConnectionConfig) -> ConnectionPool:
    """
    Create a ConnectionPool. Pools are thread-safe and should be long-lived (one per process).

    The pool is passed to redis.Redis(connection_pool=...) so each command borrows a connection
    and returns it automatically.
    """
    common_kwargs = dict(
        username=config.username,
        password=config.password,
        max_connections=config.max_connections,
        socket_timeout=config.socket_timeout,
        socket_connect_timeout=config.socket_connect_timeout,
        health_check_interval=config.health_check_interval,
        decode_responses=config.decode_responses,
    )

    if config.url:
        return ConnectionPool.from_url(config.url, **common_kwargs)

    return ConnectionPool(
        host=config.host,
        port=config.port,
        db=config.db,
        # ssl=config.ssl,
        **common_kwargs,
    )


_pool_singleton: Optional[ConnectionPool] = None


def get_redis_pool(config: RedisConnectionConfig) -> ConnectionPool:
    """
    Create a Redis connection pool if not already created. Otherwise, return the existing pool.
    """
    global _pool_singleton

    if _pool_singleton is None:
        _pool_singleton = build_redis_pool(config)
    return _pool_singleton


def get_redis_client() -> redis.Redis:
    """Convenience: pooled Redis client using get_redis_pool()."""
    pool = get_redis_pool(RedisConnectionConfig())
    return redis.Redis(connection_pool=pool)


def reset_redis_pool_for_tests() -> None:
    """Disconnect and clear singleton; use in test teardown only."""
    global _pool_singleton

    pool = _pool_singleton
    _pool_singleton = None

    if pool is not None:
        pool.disconnect(inuse_connections=True)



if __name__ == "__main__":
    reset_redis_pool_for_tests()
    try:
        client = get_redis_client()
        client.ping()

        #string
        client.set("foo", "bar")
        client.set("foo2", "bar", ex=20) #with expiry

        #list
        client.rpush("tasks", "task1")
        client.rpush("tasks", "task2")

        #set
        client.sadd("online_users", "u1", "u2")

        #sorted set
        client.zadd("leaderboard", {
            "alice": 100,
            "bob": 200
        })

        #hash
        client.hset("user:1", mapping={
            "name": "maksood",
            "age": 22
        })

        print("Redis ping OK.")
    except RuntimeError as err:
        print(f"Redis setup failed: {err}")
        raise SystemExit(1) from err
    except RedisError as err:
        print(f"Redis unreachable or error during ping: {err}")
        raise SystemExit(1) from err
