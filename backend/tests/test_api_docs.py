import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

# Use an in-memory SQLite DB for this simple healthcheck test to avoid PG + pgvector.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SKIP_DB_INIT"] = "1"

from app.core.config import get_settings
from app.db.session import Base
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _setup_sqlite_db():
    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(bind=engine)
    yield


client = TestClient(app)


def test_healthcheck():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
