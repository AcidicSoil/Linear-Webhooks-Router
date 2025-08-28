from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import get_logger


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    get_logger().warning("http_error", status=exc.status_code, detail=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    get_logger().warning("validation_error", errors=exc.errors())
    return JSONResponse(status_code=422, content={"error": "validation error"})


async def unhandled_exception_handler(request: Request, exc: Exception):
    get_logger().error("unhandled_exception", error=str(exc))
    return JSONResponse(status_code=500, content={"error": "internal server error"})
