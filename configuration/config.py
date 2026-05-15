from __future__ import annotations

import sys
from pathlib import Path

from pydantic import AliasChoices, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application configuration loaded from the environment and optional env files (frozen)."""

    # Server
    app_name: str = Field(validation_alias=AliasChoices("APP_NAME"))
    app_port: int = Field(validation_alias=AliasChoices("APP_PORT"))
    node_env: str = Field(validation_alias=AliasChoices("NODE_ENV"))
    api_url: str = Field(validation_alias=AliasChoices("API_URL"))

    # Auth / crypto
    jwt_secret: str = Field(validation_alias=AliasChoices("JWT_SECRET"))
    jwt_expiry: str = Field(validation_alias=AliasChoices("JWT_EXPIRY"))
    jwt_refresh_secret: str = Field(validation_alias=AliasChoices("JWT_REFRESH_SECRET"))
    jwt_refresh_expiry: str = Field(validation_alias=AliasChoices("JWT_REFRESH_EXPIRY"))
    encryption_key: str = Field(validation_alias=AliasChoices("ENCRYPTION_KEY"))

    # Database
    db_host: str = Field(validation_alias=AliasChoices("DB_HOST"))
    db_port: int = Field(validation_alias=AliasChoices("DB_PORT"))
    db_name: str = Field(validation_alias=AliasChoices("DB_NAME"))
    db_user: str = Field(validation_alias=AliasChoices("DB_USER"))
    db_password: str = Field(validation_alias=AliasChoices("DB_PASSWORD"))
    db_uri: str = Field(validation_alias=AliasChoices("DB_URI"))

    # Redis
    redis_host: str = Field(validation_alias=AliasChoices("REDIS_HOST"))
    redis_port: int = Field(validation_alias=AliasChoices("REDIS_PORT"))
    redis_db: int = Field(validation_alias=AliasChoices("REDIS_DB"))
    redis_user: str | None = Field(default=None, validation_alias=AliasChoices("REDIS_USER"))
    redis_password: str | None = Field(default=None, validation_alias=AliasChoices("REDIS_PASSWORD"))
    redis_max_connections: int = Field(validation_alias=AliasChoices("REDIS_MAX_CONNECTIONS"))
    redis_socket_timeout: float | None = Field(default=5, validation_alias=AliasChoices("REDIS_SOCKET_TIMEOUT"))
    redis_socket_connect_timeout: float = Field(validation_alias=AliasChoices("REDIS_SOCKET_CONNECT_TIMEOUT"))
    redis_health_check_interval: int = Field(validation_alias=AliasChoices("REDIS_HEALTH_CHECK_INTERVAL"))
    redis_decode_responses: bool = Field(validation_alias=AliasChoices("REDIS_DECODE_RESPONSES"))
    redis_ssl: bool = Field(default=False, validation_alias=AliasChoices("REDIS_SSL"))
    redis_url: str | None = Field(default=None, validation_alias=AliasChoices("REDIS_URL"))

    # Azure storage
    azure_storage_account_name: str = Field(validation_alias=AliasChoices("AZURE_STORAGE_ACCOUNT_NAME"))
    azure_storage_account_key: str = Field(validation_alias=AliasChoices("AZURE_STORAGE_ACCOUNT_KEY"))
    azure_storage_connection_string: str = Field(validation_alias=AliasChoices("AZURE_STORAGE_CONNECTION_STRING"))

    # Logging
    log_level: str = Field(validation_alias=AliasChoices("LOG_LEVEL"))

    # Security / HTTP limits
    cors_origin: str = Field(validation_alias=AliasChoices("CORS_ORIGIN"))
    rate_limit_window_seconds: int = Field(validation_alias=AliasChoices("RATE_LIMIT_WINDOW"))
    rate_limit_max_requests: int = Field(validation_alias=AliasChoices("RATE_LIMIT_MAX_REQUESTS"))
    global_overload_max_requests: int = Field(validation_alias=AliasChoices("GLOBAL_OVERLOAD_MAX_REQUESTS"))
    global_overload_window_seconds: int = Field(validation_alias=AliasChoices("GLOBAL_OVERLOAD_WINDOW_SECONDS"))
    global_overload_message: str = Field(validation_alias=AliasChoices("GLOBAL_OVERLOAD_MESSAGE"))

    # SMTP
    smtp_host: str = Field(validation_alias=AliasChoices("SMTP_HOST"))
    smtp_user_email: str = Field(validation_alias=AliasChoices("SMTP_USER_EMAIL"))
    smtp_password: str = Field(validation_alias=AliasChoices("SMTP_PASSWORD"))
    smtp_port: int = Field(validation_alias=AliasChoices("SMTP_PORT"))
    smtp_user_id: str = Field(validation_alias=AliasChoices("SMTP_USER_ID"))

    @field_validator("redis_password", mode="before")
    @classmethod
    def _normalize_redis_password(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        return str(value)

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env.development",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        populate_by_name=True,
        **({"secrets_dir": "/run/secrets"} if Path("/run/secrets").is_dir() else {}),
    )


def _load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        print(
            "Configuration error: missing or invalid environment variables. "
            "Set them in the process environment or in .env.development (see configuration/config.py).",
            file=sys.stderr,
        )
        print(exc, file=sys.stderr)
        raise sys.exit("Something went wrong while loading configuration.") from exc


global_settings = _load_settings()
