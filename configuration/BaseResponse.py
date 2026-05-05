from fastapi.responses import JSONResponse

# from typing import Any
from typing import Any


def base_res(status_code: int, message: str, data: Any, status: bool = True):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": status,
            "message": message,
            "data": data,
        }
    )

