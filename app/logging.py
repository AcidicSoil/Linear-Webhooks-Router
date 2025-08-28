from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

import structlog
from fastapi import Request


request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def set_request_id(value: str | None) -> None:
    request_id_ctx.set(value)


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        cache_logger_on_first_use=True,
    )


def get_logger():
    return structlog.get_logger()


async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    set_request_id(rid)
    structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path, method=request.method)
    try:
        response = await call_next(request)
    finally:
        # Clear context to avoid leakage across requests
        structlog.contextvars.clear_contextvars()
        set_request_id(None)
    response.headers["x-request-id"] = rid
    return response
