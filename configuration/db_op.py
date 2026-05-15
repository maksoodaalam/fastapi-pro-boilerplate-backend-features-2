"""
PostgreSQL engine utilities: URL from settings (`DB_URI` or composed `DB_*`), pooled engine, shared factory.

**Docker Compose:** set `DB_HOST=postgres`, `DB_PORT=5432`, and `DB_URI` with the same host/port (app on `dc_network`).
**Host machine (e.g. DBeaver / local uvicorn):** use `DB_HOST=127.0.0.1`, `DB_PORT=5433` to match `5433:5432` publish.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from configuration.config import global_settings


def _ensure_psycopg_driver(url: str) -> str:
    """Use psycopg (v3); bare `postgresql://` / `postgres://` avoid relying on psycopg2."""
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


def database_url() -> str:
    raw = (global_settings.db_uri or "").strip()
    if raw:
        return _ensure_psycopg_driver(raw)
    user = quote_plus(global_settings.db_user)
    password = quote_plus(global_settings.db_password)
    return (
        f"postgresql+psycopg://{user}:{password}"
        f"@{global_settings.db_host}:{global_settings.db_port}/{global_settings.db_name}"
    )


_engine_singleton: Optional[Engine] = None


def get_engine() -> Engine:
    """Long-lived SQLAlchemy engine (singleton per process)."""
    global _engine_singleton

    if _engine_singleton is None:
        _engine_singleton = create_engine(
            database_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine_singleton


def reset_db_engine_for_tests() -> None:
    """Dispose and clear singleton; use in test teardown only."""
    global _engine_singleton

    engine = _engine_singleton
    _engine_singleton = None

    if engine is not None:
        engine.dispose()
