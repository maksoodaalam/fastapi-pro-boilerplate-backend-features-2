"""Keyword arguments for ``CORSMiddleware`` (``app.add_middleware(CORSMiddleware, **cors_config)``)."""


white_list_ip = [
    "127.0.0.1",
    "0.0.0.0",
    "localhost",
    "null"
]

allowed_methods = [
    "GET",
    "HEAD",
    "OPTIONS",
    "POST",
    "PUT",
    "PATCH",
    "DELETE"
]

allowed_headers = [
    "Content-Type",
    "Authorization",
    "Accept",
    "X-Requested-With",
    "X-CSRF-Token",
]

cors_config = {
    "allow_origins": white_list_ip,
    "allow_methods": allowed_methods,
    "allow_headers": allowed_headers,
}
