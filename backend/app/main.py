from fastapi import FastAPI

from app.api import routes
from app.core.config import get_settings
from app.db.session import Base, engine

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(routes.router)
    return app


app = create_app()


# Create tables in dev/local; in production, prefer migrations.
Base.metadata.create_all(bind=engine)
