import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.api import routes
from app.core.config import get_settings
from app.db.session import Base, engine
from app.services.embeddings import EmbeddingService
from app.observability import metrics

settings = get_settings()
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
        return response

    return app


app = create_app()
