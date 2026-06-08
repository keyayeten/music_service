import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.api.system.router import router as system_router
from backend.api.v1.router import router as api_v1_router
from backend.config.settings import get_settings
from backend.infrastructure.admin import init_admin
from backend.infrastructure.cache.redis_client import close_redis_client, init_redis_client
from backend.infrastructure.logging import configure_logging
from backend.infrastructure.persistence.database import close_database, init_database

load_dotenv()
logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("Initializing application resources.")
    init_database(settings)
    init_redis_client()
    try:
        logger.info("Application resources initialized.")
        yield
    finally:
        logger.info("Shutting down application resources.")
        await close_redis_client()
        await close_database()
        logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    application = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        openapi_url=settings.openapi_url if settings.docs_enabled else None,
        docs_url=settings.swagger_docs_url if settings.docs_enabled else None,
        redoc_url=settings.redoc_url if settings.docs_enabled else None,
    )
    if settings.admin_enabled:
        application.add_middleware(SessionMiddleware, secret_key=settings.admin_session_secret)
    application.include_router(system_router)
    application.include_router(api_v1_router)
    init_admin(application, settings)
    logger.info(
        "Application created: name=%s docs_enabled=%s",
        settings.app_name,
        settings.docs_enabled,
    )

    @application.middleware("http")
    async def _request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        started_at = time.perf_counter()
        client_ip = request.client.host if request.client is not None else "-"
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started_at) * 1000
            logger.exception(
                "HTTP %s %s failed in %.2fms rid=%s ip=%s",
                request.method,
                request.url.path,
                duration_ms,
                request_id,
                client_ip,
            )
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000
        status_code = response.status_code
        if status_code >= 500:
            log_method = logger.error
        elif status_code >= 400:
            log_method = logger.warning
        else:
            log_method = logger.info

        log_method(
            "HTTP %s %s -> %s in %.2fms rid=%s ip=%s",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            request_id,
            client_ip,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    @application.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        logger.warning(
            "Request validation failed path=%s errors=%s",
            request.url.path,
            len(details),
        )
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": "Request validation failed.",
                "details": details,
            },
        )

    return application


app = create_app()
