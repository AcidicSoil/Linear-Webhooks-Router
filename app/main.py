from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from .config import validate_settings_or_raise, get_settings
from .db.repository import MappingRepository
from .router.webhook import router as webhook_router
from .logging import configure_logging, request_id_middleware, get_logger
from .errors import http_exception_handler, validation_exception_handler, unhandled_exception_handler


app = FastAPI(title="Linear Webhook Router", version="0.1.0")
app.middleware("http")(request_id_middleware)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
async def _validate_config_on_startup() -> None:
    # Trigger config validation at startup for fail-fast behavior
    settings = validate_settings_or_raise()
    # Initialize DB (creates file and schema if needed)
    app.state.mapping_repo = MappingRepository(settings.db_url())
    configure_logging(settings.log_level)
    get_logger().info("startup_complete", db_url=settings.db_url())


app.include_router(webhook_router)

# Exception handlers
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[name-defined]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[name-defined]
