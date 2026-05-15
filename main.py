import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from html import escape
from datetime import datetime, timezone
from sqlalchemy import text

from configuration.BaseResponse import base_res
from configuration.CorsOp import cors_config, allowed_methods
from configuration.InboundHeadersOp import (
    BLOCKED_HEADERS,
    EXTRA_ALLOWED_HEADERS,
    REQUIRED_HEADERS,
    REQUIRED_HEADERS_METHODS,
    inbound_header_policy_middleware,
)
from configuration.MethodOp import HttpMethodAllowlistMiddleware
from configuration.PayloadSizeValidator import LimitStreamingMiddleware
from configuration.OutboundHeadersOp import outbound_header_middleware
from configuration.PollutionValidator import validate_pollution
from configuration.GlobalOverloadMiddleware import global_overload_http_middleware
from configuration.RateLimitMiddleware import rate_limit_http_middleware
from configuration.logger_conf import get_file_logger
from configuration.redis_op import get_redis_client
from configuration.db_op import get_engine
from configuration.config import global_settings


_DateTimeUTC = datetime.now(timezone.utc)

try:
    logger = get_file_logger(f"{_DateTimeUTC.strftime('%d_%m_%Y_%H_%M')}_Initialize.log")
    logger.info("Initializing FastAPI app")
    print("Initializing FastAPI app")
except Exception:
    print("Something went wrong while logging.")
    raise sys.exit("Something went wrong while logging.")

app = FastAPI(
    title=global_settings.app_name,
    description="A backend service that provides high-performance document and image processing utilities via APIs, with support for async jobs, streaming, and scalable workflows.",
    version="1.0.0",
    contact={
        "name": "Maksood Aalam",
        "url": "https://maksood.com",
        "email": "maksoodaalam121@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },

    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas section
        "docExpansion": "none",          # Collapse endpoints
        "deepLinking": True,
        "showExtensions": True,
        "showCommonExtensions": True,
    }


    # redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    # swagger_ui_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.16.0/swagger-ui-bundle.js",

)

# Redis Connection.
redis_client = get_redis_client()
try:
    redis_client.ping()
    logger.info("Redis connection established")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    raise sys.exit("Redis Connection Failed.")

# PostgreSQL (Docker Compose / DBeaver — tune DB_HOST & DB_PORT in env).
try:
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("PostgreSQL connection established")
except Exception as e:
    logger.error(f"PostgreSQL connection failed: {e}")
    raise sys.exit("PostgreSQL Connection Failed.")

# Per-client, per-route sliding window (see RATE_LIMIT_MAX_REQUESTS / RATE_LIMIT_WINDOW)
app.middleware("http")(
    rate_limit_http_middleware(
        redis_client=redis_client,
        max_requests=global_settings.rate_limit_max_requests,
        window_seconds=global_settings.rate_limit_window_seconds,
    )
)

# Incoming Method Controls
app.add_middleware(HttpMethodAllowlistMiddleware, allowed_methods=allowed_methods)

# Incoming Header Controls
app.add_middleware(
    inbound_header_policy_middleware,
    blocked=BLOCKED_HEADERS,
    extra_allowed=EXTRA_ALLOWED_HEADERS,
    required=REQUIRED_HEADERS,
    required_methods=REQUIRED_HEADERS_METHODS,
    exempt_methods_for_allow_required=("OPTIONS",),
)

# Cors Controls
app.add_middleware(CORSMiddleware, **cors_config)

# Incoming JSON/text body size (streaming receive)
app.add_middleware(LimitStreamingMiddleware)

# Pollution validation
app.middleware("http")(validate_pollution)

# Outgoing header control
app.middleware("http")(outbound_header_middleware)

# Global cap: when total service traffic exceeds threshold in the window, all APIs
# return overload until the sliding window cools (registered last = outermost).
app.middleware("http")(
    global_overload_http_middleware(
        redis_client=redis_client,
        max_requests=global_settings.global_overload_max_requests,
        window_seconds=global_settings.global_overload_window_seconds,
        message=global_settings.global_overload_message,
    )
)




logger.info("Middleware added")




@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return base_res(200, "Working", {}, True)


@app.put("/api/v1/putcheck", tags=["Health"])
def put_check():
    return base_res(200, "Working", {}, True)


@app.trace("/api/v1/trace", tags=["Docs"])
def docs():
    return base_res(200, "Working", {}, True)


@app.get("/api/v1/xss-sample")
def home(name: str):
    safe_name = escape(name)
    return f"<h1>Hello {safe_name}</h1>"




