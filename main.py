from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from configuration.BaseResponse import base_res
from configuration.CorsOp import cors_config, allowed_methods
from configuration.OutboundHeadersOp import header_config
from configuration.InboundHeadersOp import (
    BLOCKED_HEADERS,
    EXTRA_ALLOWED_HEADERS,
    REQUIRED_HEADERS,
    REQUIRED_HEADERS_METHODS,
    InboundHeaderPolicyMiddleware,
)
from configuration.MethodOp import HttpMethodAllowlistMiddleware

app = FastAPI(
    title="DocSprint",
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

# Method Controls
app.add_middleware(HttpMethodAllowlistMiddleware, allowed_methods=allowed_methods)

# Header Controls
app.add_middleware(
    InboundHeaderPolicyMiddleware,
    blocked=BLOCKED_HEADERS,
    extra_allowed=EXTRA_ALLOWED_HEADERS,
    required=REQUIRED_HEADERS,
    required_methods=REQUIRED_HEADERS_METHODS,
    exempt_methods_for_allow_required=("OPTIONS",),
)

# Cors Controls
app.add_middleware(CORSMiddleware, **cors_config)




@app.middleware("http")
async def add_headers(request: Request, call_next):
    response = await call_next(request)
    response = header_config(response)
    return response


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return base_res(200, "Working", {}, True)


@app.put("/api/v1/putcheck", tags=["Health"])
def put_check():
    return base_res(200, "Working", {}, True)


@app.trace("/api/v1/trace", tags=["Docs"])
def docs():
    return base_res(200, "Working", {}, True)

# uvicorn.run(app, host="0.0.0.0", port=8000)


