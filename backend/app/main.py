import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes
from app.core.config import settings
from app.core.exceptions import AppException
from app.db.session import Base, engine
from app.services.embeddings import EmbeddingService
from app.observability import http_request_latency_ms, http_requests_total, metrics

logger = logging.getLogger("rag-app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Load embedding model once at startup to avoid first-request latency.
        _ = EmbeddingService().model
        logger.info("Embedding model warm-up complete")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding warm-up failed: %s", exc)
    # Create tables in dev/local; in production, prefer migrations. Skipped when SKIP_DB_INIT=1.
    if os.getenv("SKIP_DB_INIT") != "1":
        Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(routes.router)

    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")

        @app.get("/", include_in_schema=False)
        async def serve_index() -> FileResponse:
            return FileResponse(static_dir / "index.html")

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"An unexpected error occurred: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())
        start_time = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = str(duration_ms)
        logger.info(
            "%s %s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        metrics.observe_latency("http_total_ms", duration_ms)
        http_requests_total.labels(request.method, request.url.path, str(response.status_code)).inc()
        http_request_latency_ms.labels(request.method, request.url.path).observe(duration_ms)
        return response

    return app


app = create_app()
