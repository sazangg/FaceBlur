import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Protocol

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from face_blur.api.errors import AppError
from face_blur.api.limiter import limiter
from face_blur.api.metrics import BLUR_ERRORS, REQUEST_COUNT, REQUEST_LATENCY
from face_blur.api.responses import ok
from face_blur.api.routes import router
from face_blur.core.config import settings
from face_blur.core.logging import configure_logging
from face_blur.stats.store import increment_stat_async, init_db_async
from face_blur.storage.cleanup import cleanup_loop
from face_blur.workers.taskiq_app import broker as default_broker
from face_blur.workers.tasks import blur_images, blur_videos

configure_logging()
logger = logging.getLogger("face_blur.api")


class BrokerProtocol(Protocol):
    result_backend: Any

    async def startup(self) -> None: ...

    async def shutdown(self) -> None: ...


TaskSubmitter = Callable[[list[dict[str, Any]]], Awaitable[Any]]


def create_app(
    broker_instance: BrokerProtocol = default_broker,
    task_submitter: TaskSubmitter | None = None,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await broker_instance.startup()
        await init_db_async(settings.stats_db_path)
        stop_event = asyncio.Event()
        app.state.cleanup_stop = stop_event
        if settings.storage_cleanup_interval_minutes > 0:
            interval = settings.storage_cleanup_interval_minutes * 60
            ttl = settings.storage_ttl_minutes * 60
            app.state.cleanup_task = asyncio.create_task(
                cleanup_loop(
                    storage_dir=settings.storage_dir,
                    ttl_seconds=ttl,
                    interval_seconds=interval,
                    stop_event=stop_event,
                    logger=logger,
                )
            )
        yield
        stop_event.set()
        cleanup_task = getattr(app.state, "cleanup_task", None)
        if cleanup_task is not None:
            await cleanup_task
        await broker_instance.shutdown()

    app = FastAPI(title="Face Blur API", lifespan=lifespan)
    app.state.limiter = limiter
    app.state.broker = broker_instance
    app.state.task_submitter = task_submitter or blur_images.kiq
    app.state.video_task_submitter = blur_videos.kiq
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(router)

    @app.middleware("http")
    async def request_logger(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request_path = request.url.path
        count_request = request_path in {"/blur", "/blur/video"}
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        route = request.scope.get("route")
        path = route.path if route is not None else request_path
        REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path).observe(
            duration_ms / 1000
        )
        if count_request:
            await increment_stat_async(settings.stats_db_path, "total_requests")
        logger.info(
            (
                "request_complete method=%s path=%s status=%s "
                "duration_ms=%.2f request_id=%s"
            ),
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        response.headers["X-Request-Id"] = request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        BLUR_ERRORS.labels(code=exc.code).inc()
        return exc.to_response()

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        payload = ok(message=exc.detail, status="error")
        payload["code"] = "http_error"
        BLUR_ERRORS.labels(code="http_error").inc()
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        payload = ok(message="Request validation failed.", status="error")
        payload["code"] = "validation_error"
        payload["details"] = {"errors": exc.errors()}
        BLUR_ERRORS.labels(code="validation_error").inc()
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        payload = ok(
            message="Rate limit exceeded. Please try again later.", status="error"
        )
        payload["code"] = "rate_limited"
        BLUR_ERRORS.labels(code="rate_limited").inc()
        return JSONResponse(status_code=429, content=payload)

    @app.get("/metrics")
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
