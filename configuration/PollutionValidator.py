from json import loads
from urllib.parse import parse_qs
from fastapi import Request

from configuration.BaseResponse import base_res


def no_duplicate_keys_object_pairs_hook(pairs):
    data = {}
    for k, v in pairs:
        if k in data:
            raise ValueError(f"Duplicate key: {k}")
        data[k] = v
    return data


async def validate_pollution(request: Request, call_next):
    # -------------------------
    # 1. Query validation (only if present)
    # -------------------------
    if request.url.query:
        parsed = parse_qs(request.url.query, keep_blank_values=True)

        polluted_query = {k: v for k, v in parsed.items() if len(v) > 1}

        if polluted_query:
            return base_res(400, "Query parameter pollution detected", {}, False)


    # -------------------------
    # 2. JSON body validation
    # -------------------------
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.body()

        if body:
            try:
                loads(
                    body,
                    object_pairs_hook=no_duplicate_keys_object_pairs_hook,
                )
            except ValueError:
                return base_res(400, "Incorrect JSON", {}, False)

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive

    return await call_next(request)
