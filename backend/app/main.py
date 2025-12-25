import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from collections import deque
from pathlib import Path
from typing import Deque

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
_rate_limit_window_seconds = 60
_rate_limit_buckets: dict[str, Deque[float]] = {}


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
    app_title = getattr(settings, "app_name", "Enterprise RAG Platform")
    app = FastAPI(title=app_title, lifespan=lifespan)
    app.include_router(routes.router)

    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/ui/assets", StaticFiles(directory=assets_dir), name="ui-assets")

        @app.get("/", include_in_schema=False)
        async def serve_index() -> FileResponse:
            return FileResponse(static_dir / "index.html")

    def _build_error_payload(detail: str, request: Request) -> dict[str, str]:
        correlation_id = getattr(request.state, "correlation_id", None) or str(uuid.uuid4())
        error_id = str(uuid.uuid4())
        return {"detail": detail, "error_id": error_id, "correlation_id": correlation_id}

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        metrics.record_error(
            method=request.method,
            path=request.url.path,
            status=exc.status_code,
            error_code=str(exc.status_code),
            detail=exc.detail,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_payload(exc.detail, request),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        metrics.record_error(
            method=request.method,
            path=request.url.path,
            status=exc.status_code,
            error_code=str(exc.status_code),
            detail=str(exc.detail),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_payload(str(exc.detail), request),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        payload = _build_error_payload("Internal server error", request)
        metrics.record_error(
            method=request.method,
            path=request.url.path,
            status=500,
            error_code="500",
            detail="Internal server error",
            correlation_id=payload["correlation_id"],
        )
        logger.error(
            "Unexpected error: %s correlation_id=%s error_id=%s",
            exc,
            payload["correlation_id"],
            payload["error_id"],
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content=payload,
        )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next) -> Response:  # type: ignore[override]
        incoming_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id")
        request_id = incoming_id or str(uuid.uuid4())
        request.state.correlation_id = request_id

        if getattr(settings, "rate_limit_enabled", False):
            client_id = request.client.host if request.client else "unknown"
            limit = int(getattr(settings, "rate_limit_per_minute", 60))
            now = time.time()
            bucket = _rate_limit_buckets.setdefault(client_id, deque())
            while bucket and bucket[0] < now - _rate_limit_window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            bucket.append(now)

        start_time = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = request_id
        response.headers["X-Response-Time-ms"] = str(duration_ms)

        route = request.scope.get("route")
        path_label = getattr(route, "path", None) or request.url.path
        tenant_label = "auth" if request.headers.get("authorization") else "anon"
        status_code = str(response.status_code)
        error_code = status_code if response.status_code >= 400 else "ok"

        logger.info(
            "%s %s status=%s duration_ms=%s correlation_id=%s",
            request.method,
            path_label,
            response.status_code,
            duration_ms,
            request_id,
        )
        metrics.observe_latency("http_total_ms", duration_ms)
        http_requests_total.labels(request.method, path_label, status_code, tenant_label).inc()
        http_request_latency_ms.labels(request.method, path_label, error_code).observe(duration_ms)
        return response

    return app


app = create_app()
