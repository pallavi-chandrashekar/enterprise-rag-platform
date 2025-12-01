import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.api import routes
from app.core.config import get_settings
from app.db.session import Base, engine

settings = get_settings()
logger = logging.getLogger("rag-app")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(routes.router)

    @app.middleware("http")
    async def add_request_context(request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())
        start_time = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = str(duration_ms)
        logger.info("%s %s status=%s duration_ms=%s request_id=%s", request.method, request.url.path, response.status_code, duration_ms, request_id)
        return response

    return app


app = create_app()


# Create tables in dev/local; in production, prefer migrations.
Base.metadata.create_all(bind=engine)
